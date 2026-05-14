from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import psutil

from .bam_collector import collect_bam_execution_paths, norm_exe_stem
from .file_intel import (
    batch_authenticode_status,
    fake_extension_flags,
    file_entropy_sample,
    is_pe_file,
    is_removable_path,
    is_tempish_path,
    packed_pe_heuristic,
    random_filename_score,
    sha256_file,
    yara_scan_file,
)
from .models import DetectionMetadata, ForensicFinding, RiskWeights, TimelineEvent, default_risk_weights
from .pca_collector import collect_pca_program_ids
from .prefetch_collector import collect_prefetch_records
from .saved_files_collector import collect_saved_files_viewer
from .sqlite_artifacts import collect_activity_cache_paths, collect_browser_sqlite_signals, probe_activity_cache_executables
from .usn_collector import collect_usn_journal_sample

RunCommand = Callable[..., str]


def _norm_path(p: str) -> str:
    return os.path.normcase(os.path.normpath(p.replace("/", "\\")))


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _session_anchor() -> datetime:
    """Conservative 'recent session' window for correlation (reduces stale FP)."""
    now = datetime.now(timezone.utc)
    try:
        boot = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
    except Exception:
        boot = now
    recent = now - timedelta(hours=6)
    return max(boot, recent)


def gather_forensic_context(run_command: RunCommand) -> dict[str, Any]:
    bam = collect_bam_execution_paths(run_command)
    usn = collect_usn_journal_sample(run_command)
    prefetch = collect_prefetch_records()
    pca = collect_pca_program_ids(run_command)
    saved = collect_saved_files_viewer()
    browser = collect_browser_sqlite_signals()
    activity = collect_activity_cache_paths()
    activity_paths = probe_activity_cache_executables()
    anchor = _session_anchor()
    bam_paths = [_norm_path(e["path"]) for e in bam.get("entries") or [] if e.get("path")]
    bam_set = set(bam_paths)
    bam_stems = {norm_exe_stem(p) for p in bam_paths}
    pf_stems: set[str] = set()
    for it in prefetch.get("items") or []:
        g = it.get("executable_guess")
        if g:
            pf_stems.add(g.lower())

    return {
        "bam": bam,
        "usn": usn,
        "prefetch": prefetch,
        "pca": pca,
        "saved_files": saved,
        "browser_sqlite": browser,
        "activity_cache": activity,
        "activity_cache_paths": activity_paths,
        "bam_paths_norm": bam_set,
        "bam_exe_stems": bam_stems,
        "prefetch_exe_stems": pf_stems,
        "session_anchor_utc": anchor.isoformat(),
    }


def _intel_for_paths(paths: list[str], run_command: RunCommand, yara_dir: Path | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    uniq: list[str] = []
    for p in paths:
        n = _norm_path(p)
        if n not in uniq and Path(n).is_file():
            uniq.append(n)
    sig = batch_authenticode_status(uniq, run_command)
    for p in uniq:
        path = Path(p)
        ent = file_entropy_sample(path)
        packed = packed_pe_heuristic(path, ent)
        ymatches, yok = yara_scan_file(path, yara_dir)
        st = sig.get(p, {})
        out[p] = {
            "sha256": sha256_file(path),
            "entropy": ent,
            "packed_pe_heuristic": packed,
            "signature": st,
            "yara_matches": ymatches,
            "yara_runtime": yok,
            "is_pe": is_pe_file(path),
        }
    return out


def _score_from_intel(
    intel: dict[str, Any],
    weights: RiskWeights,
    *,
    temp_path: bool = False,
    removable: bool = False,
    random_name: float = 0.0,
    fake_ext: list[str] | None = None,
    keyword_bonus: bool = False,
    deleted_bonus: bool = False,
) -> float:
    score = 0.0
    sig = intel.get("signature") or {}
    status = str(sig.get("status", ""))
    if status in {"NotSigned", "HashMismatch"}:
        score += weights.unsigned
    if intel.get("entropy") is not None and float(intel["entropy"]) >= 7.35 and intel.get("is_pe"):
        score += weights.high_entropy
    if intel.get("packed_pe_heuristic"):
        score += weights.packed_pe
    if intel.get("yara_matches"):
        score += weights.yara_positive
    if temp_path:
        score += weights.temp_execution
    if removable:
        score += weights.removable_drive
    if random_name >= 0.65:
        score += weights.random_filename
    if fake_ext:
        score += weights.double_extension
    if keyword_bonus:
        score += weights.cheat_keyword
    if deleted_bonus:
        score += weights.deleted_after_exec
    return round(min(score, 100.0), 2)


def build_unified_timeline(ctx: dict[str, Any], findings: list[ForensicFinding]) -> list[dict[str, Any]]:
    events: list[TimelineEvent] = []
    for it in ctx.get("prefetch", {}).get("items") or []:
        if it.get("modified"):
            events.append(
                TimelineEvent(
                    it["modified"],
                    "prefetch",
                    "prefetch_file_touch",
                    it.get("name"),
                    {"executable_guess": it.get("executable_guess")},
                )
            )
    for ev in ctx.get("usn", {}).get("events") or []:
        ts = ev.get("timestamp_iso") or ev.get("timestamp_raw")
        if ts and isinstance(ts, str):
            events.append(
                TimelineEvent(
                    ts if "T" in ts else ev.get("timestamp_raw", ts),
                    "usn",
                    ",".join(ev.get("reason_flags") or []) or "usn_record",
                    ev.get("name"),
                    {"reason_hex": ev.get("reason_hex"), "volume": ev.get("volume")},
                )
            )
    for row in ctx.get("pca", {}).get("events") or []:
        tc = row.get("time_created")
        if tc:
            events.append(
                TimelineEvent(
                    str(tc),
                    "pca",
                    "pca_program_compatibility",
                    row.get("program_id"),
                    {"event_id": row.get("id")},
                )
            )
    for f in findings:
        for ts in f.timestamps:
            if ts:
                events.append(
                    TimelineEvent(ts, "detection", f.title, f.primary_path, {"severity": f.severity, "tags": f.tags})
                )
    events.sort(key=lambda e: e.ts_iso or "")
    return [e.as_dict() for e in events[-400:]]


def cluster_suspicious_windows(events: list[dict[str, Any]], window_sec: int = 90) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    if not events:
        return clusters
    cur: list[dict[str, Any]] = []
    last_ts: datetime | None = None
    for ev in events:
        ts = _parse_iso(ev.get("timestamp"))
        if ts is None:
            continue
        if last_ts and abs((ts - last_ts).total_seconds()) > window_sec:
            if len(cur) >= 3:
                clusters.append({"window_seconds": window_sec, "count": len(cur), "events": cur[:]})
            cur = []
        cur.append(ev)
        last_ts = ts
    if len(cur) >= 3:
        clusters.append({"window_seconds": window_sec, "count": len(cur), "events": cur})
    return clusters[-20:]


def run_correlation_engine(
    ctx: dict[str, Any],
    run_command: RunCommand,
    *,
    weights: RiskWeights | None = None,
    filters: dict[str, Any] | None = None,
    max_file_intel: int = 28,
) -> dict[str, Any]:
    weights = weights or default_risk_weights()
    filters = filters or {}
    findings: list[ForensicFinding] = []
    yara_dir = Path(__file__).resolve().parent / "yara_rules"

    bam_entries = ctx.get("bam", {}).get("entries") or []
    bam_set: set[str] = ctx.get("bam_paths_norm") or set()
    usn_events: list[dict[str, Any]] = list(ctx.get("usn", {}).get("events") or [])
    exec_only = bool(filters.get("usn_executable_only"))
    unsigned_only = bool(filters.get("usn_unsigned_only"))
    ent_min = filters.get("usn_entropy_min")
    yara_only = bool(filters.get("usn_yara_positive_only"))

    if exec_only:
        usn_events = [e for e in usn_events if e.get("is_executable_name")]
    session_anchor = _parse_iso(ctx.get("session_anchor_utc")) or datetime.now(timezone.utc)

    # --- USN detections ---
    rename_pairs: list[tuple[str, str]] = []
    for ev in usn_events:
        flags = ev.get("reason_flags") or []
        name = ev.get("name") or ""
        if "FILE_RENAME_OLD_NAME" in flags or "FILE_RENAME_NEW_NAME" in flags:
            rename_pairs.append((str(flags), str(name)))

    delete_execs = [
        e
        for e in usn_events
        if e.get("is_executable_name") and "FILE_DELETE" in (e.get("reason_flags") or [])
    ]
    create_execs = [e for e in usn_events if e.get("is_executable_name") and "FILE_CREATE" in (e.get("reason_flags") or [])]

    for e in delete_execs[:35]:
        full = e.get("name", "")
        if not re.search(r"\.(exe|dll)\Z", full, re.I):
            continue
        np = _norm_path(full) if ":" in full else None
        evidence = [{"source": "usn", "record": e}]
        tags = ["usn", "executable_delete"]
        confidence = 0.55
        if np and is_tempish_path(np):
            tags.append("temp_path_delete")
            confidence += 0.12
        if "alternate_data_stream_in_path" in (e.get("reason_flags") or []):
            tags.append("alternate_data_stream")
            confidence += 0.08
        findings.append(
            ForensicFinding(
                severity="medium",
                confidence=min(confidence, 0.92),
                title="USN: executable delete event",
                reason="USN recorded a delete/close for an executable name; often aligns with anti-forensics or ephemeral loaders.",
                artifact_sources=["usn_journal"],
                correlated_evidence=evidence,
                timestamps=[t for t in [e.get("timestamp_iso"), e.get("timestamp_raw")] if t],
                primary_path=np or full,
                tags=tags,
                risk_score=22.0,
                metadata=DetectionMetadata("usn.exec_delete", "usn_journal_parser", fp_controls=["requires_executable_suffix"]),
            )
        )

    rapid_cd = 0
    for i, a in enumerate(create_execs):
        for b in delete_execs[i : i + 6]:
            if a.get("name") == b.get("name"):
                rapid_cd += 1
    if rapid_cd >= 2:
        findings.append(
            ForensicFinding(
                severity="low",
                confidence=0.42,
                title="USN: repeated create/delete churn on executables",
                reason="Multiple executable create/delete pairs observed in the sampled USN window (noisy on build machines).",
                artifact_sources=["usn_journal"],
                correlated_evidence=[{"create_samples": create_execs[:5], "delete_samples": delete_execs[:5]}],
                timestamps=[],
                tags=["usn", "anti_forensics_suspect"],
                risk_score=12.0,
                metadata=DetectionMetadata("usn.churn", "usn_journal_parser", fp_controls=["sample_limited"]),
            )
        )

    # --- Deleted / missing BAM targets & Prefetch divergence ---
    for entry in bam_entries:
        p = entry.get("path")
        if not isinstance(p, str) or not p.lower().endswith((".exe", ".dll")):
            continue
        np = _norm_path(p)
        exists = Path(np).is_file()
        if exists:
            continue
        evidence: list[dict[str, Any]] = [{"source": "bam", "entry": entry, "file_exists": False}]
        usn_hits = []
        for u in usn_events:
            un = str(u.get("name") or "").replace("/", "\\")
            if not un:
                continue
            nl, ul = np.lower(), un.lower()
            if nl.endswith(ul) or ul in nl:
                usn_hits.append(u)
        if usn_hits:
            evidence.append({"source": "usn_path_match", "hits": usn_hits[:4]})
        pf_base = norm_exe_stem(np)
        pf_match = [
            it
            for it in ctx.get("prefetch", {}).get("items") or []
            if (it.get("executable_guess") or "").lower() == pf_base
        ]
        if pf_match:
            evidence.append({"source": "prefetch_basename_match", "items": pf_match[:3]})
        findings.append(
            ForensicFinding(
                severity="high" if pf_match else "medium",
                confidence=0.72 if pf_match else 0.5,
                title="BAM path no longer on disk (possible cleanup)",
                reason="BAM recorded execution metadata for a path that is not currently a file; correlate with Prefetch/USN for deletion timing.",
                artifact_sources=["bam", "filesystem", "prefetch", "usn_journal"],
                correlated_evidence=evidence,
                timestamps=[],
                primary_path=np,
                tags=["bam", "deleted_or_moved_binary", "deleted_bam_parser"],
                risk_score=30.0 if pf_match else 20.0,
                metadata=DetectionMetadata("bam.missing_file", "deleted_bam_parser"),
            )
        )

    suspicious_stems: set[str] = set()
    for hit in ctx.get("browser_sqlite", {}).get("hits") or []:
        for dp in hit.get("recent_download_paths") or []:
            if isinstance(dp, str):
                suspicious_stems.add(norm_exe_stem(dp))
    for ap in ctx.get("activity_cache_paths") or []:
        suspicious_stems.add(norm_exe_stem(ap))

    pf_div_seen: set[str] = set()
    for it in ctx.get("prefetch", {}).get("items") or []:
        guess = (it.get("executable_guess") or "").lower()
        if not guess:
            continue
        if guess in ctx.get("bam_exe_stems", set()):
            continue
        if any(x in guess for x in ("SETUP", "INSTALL", "MSI", "UPDATE", "UNINS")):
            continue
        if guess not in suspicious_stems:
            continue
        if guess in pf_div_seen:
            continue
        pf_div_seen.add(guess)
        findings.append(
            ForensicFinding(
                severity="low",
                confidence=0.4,
                title="Prefetch stem correlated to download/history but absent from BAM snapshot",
                reason="Prefetch suggests execution of a binary also referenced in browser/activity paths, while BAM did not list the same executable stem—review for BAM cleanup or alternate SID.",
                artifact_sources=["prefetch", "bam", "windows_sqlite_parser", "activity_cache"],
                correlated_evidence=[{"prefetch": it, "note": "stem_correlation"}],
                timestamps=[it["modified"]] if it.get("modified") else [],
                tags=["prefetch", "bam_cleanup_suspect", "sqlite_correlation"],
                risk_score=14.0,
                metadata=DetectionMetadata("prefetch.bam_divergence_v2", "prefetch_parser", fp_controls=["stem_only"]),
            )
        )

    # --- PCA ---
    pca_programs = ctx.get("pca", {}).get("events") or []
    crash_loops: dict[str, int] = {}
    for row in pca_programs:
        pid = row.get("program_id") or ""
        crash_loops[pid] = crash_loops.get(pid, 0) + 1
    for pid, cnt in crash_loops.items():
        if cnt >= 6 and len(pid) > 8:
            findings.append(
                ForensicFinding(
                    severity="low",
                    confidence=min(0.45 + cnt * 0.02, 0.85),
                    title="PCA: repeated compatibility events for same program id",
                    reason="Crash-loop or repeated PCA touches can indicate unstable injectors or compatibility-shimmed cheats.",
                    artifact_sources=["pca"],
                    correlated_evidence=[{"program_id": pid, "count": cnt}],
                    timestamps=[row.get("time_created") for row in pca_programs if row.get("program_id") == pid][:8],
                    primary_path=pid if ":\\" in pid else None,
                    tags=["pca", "crash_loop"],
                    risk_score=14.0,
                    metadata=DetectionMetadata("pca.loop", "pcasvc_executed"),
                )
            )

    # --- SQLite browser ---
    sqlite_findings = 0
    for hit in ctx.get("browser_sqlite", {}).get("hits") or []:
        for u in hit.get("suspicious_url_hits") or []:
            if sqlite_findings >= 22:
                break
            findings.append(
                ForensicFinding(
                    severity="low",
                    confidence=0.48,
                    title="Browser history: suspicious cheat-related URL",
                    reason="Keyword hit in stored browser URL data.",
                    artifact_sources=["browser_sqlite"],
                    correlated_evidence=[{"hit": u, "database": hit.get("database")}],
                    timestamps=[],
                    primary_path=hit.get("database"),
                    tags=["sqlite", "browser", "keyword"],
                    risk_score=12.0,
                    metadata=DetectionMetadata("sqlite.url_keyword", "windows_sqlite_parser"),
                )
            )
            sqlite_findings += 1
        for d in hit.get("suspicious_download_hits") or []:
            if sqlite_findings >= 22:
                break
            findings.append(
                ForensicFinding(
                    severity="medium",
                    confidence=0.52,
                    title="Browser downloads: suspicious cheat-related path",
                    reason="Keyword hit in stored download target path.",
                    artifact_sources=["browser_sqlite"],
                    correlated_evidence=[{"hit": d, "database": hit.get("database")}],
                    timestamps=[],
                    primary_path=hit.get("database"),
                    tags=["sqlite", "browser", "download", "keyword"],
                    risk_score=16.0,
                    metadata=DetectionMetadata("sqlite.download_keyword", "windows_sqlite_parser"),
                )
            )
            sqlite_findings += 1

    # --- Saved files + correlation stubs ---
    recent_anchor = session_anchor - timedelta(days=2)
    for rec in ctx.get("saved_files", {}).get("records") or []:
        p = rec.get("path")
        if not p or not str(p).lower().endswith(".exe"):
            continue
        pt = Path(p)
        if not pt.is_file():
            continue
        if not rec.get("modified"):
            continue
        mod = _parse_iso(rec.get("modified"))
        if mod and mod < recent_anchor:
            continue
        intel = _intel_for_paths([str(pt)], run_command, yara_dir).get(_norm_path(str(pt)))
        if not intel:
            continue
        if unsigned_only and str((intel.get("signature") or {}).get("status")) not in {"NotSigned", "HashMismatch"}:
            continue
        if ent_min is not None and (intel.get("entropy") or 0) < float(ent_min):
            continue
        if yara_only and not intel.get("yara_matches"):
            continue
        temp_hit = is_tempish_path(str(pt))
        rem_hit = is_removable_path(str(pt))
        rnd = random_filename_score(pt.name)
        fake = fake_extension_flags(pt.name)
        score = _score_from_intel(
            intel,
            weights,
            temp_path=temp_hit,
            removable=rem_hit,
            random_name=rnd,
            fake_ext=fake,
        )
        chain: list[dict[str, Any]] = [{"stage": "saved_file", "detail": rec}]
        if _norm_path(str(pt)) in bam_set:
            chain.append({"stage": "bam_present", "detail": True})
        if norm_exe_stem(str(pt)) in ctx.get("prefetch_exe_stems", set()):
            chain.append({"stage": "prefetch_present", "detail": True})
        if any(str(pt).lower() == (u.get("name") or "").lower() for u in delete_execs):
            chain.append({"stage": "usn_delete_observed", "detail": True})
        if score < 18 and not fake and rnd < 0.5:
            continue
        tags = ["saved_files", "executable"] + (["unsigned"] if str((intel.get("signature") or {}).get("status")) == "NotSigned" else [])
        if any(x.get("stage") == "bam_present" for x in chain) and any(x.get("stage") == "prefetch_present" for x in chain):
            tags.append("flag_downloaded_and_executed")
        if fake:
            tags.append("flag_fake_extension_style")
        if any(x.get("stage") == "usn_delete_observed" for x in chain) and any(x.get("stage") == "bam_present" for x in chain):
            tags.append("flag_deleted_after_execution_context")
        findings.append(
            ForensicFinding(
                severity="high" if score >= 55 else "medium" if score >= 35 else "low",
                confidence=min(0.5 + rnd * 0.2 + (0.15 if fake else 0) + (0.1 if temp_hit else 0), 0.9),
                title="Saved file / drop zone: suspicious executable metadata",
                reason="Recent executable in user-visible save locations with elevated risk score from entropy/signature/name heuristics.",
                artifact_sources=["saved_files_viewer", "authenticode", "entropy", "yara_optional"],
                correlated_evidence=chain,
                timestamps=[rec["modified"]] if rec.get("modified") else [],
                primary_path=str(pt),
                sha256=intel.get("sha256"),
                signature_status=str((intel.get("signature") or {}).get("status")),
                entropy=intel.get("entropy"),
                yara_matches=list(intel.get("yara_matches") or []),
                risk_score=score,
                tags=tags,
                metadata=DetectionMetadata("saved.high_risk_exe", "saved_files_viewer"),
            )
        )

    # --- Chain: download -> rename -> execute -> delete (weak unless multiple signals) ---
    for e_del in delete_execs[:20]:
        name = e_del.get("name") or ""
        if not name.lower().endswith(".exe"):
            continue
        related_create = [c for c in create_execs if c.get("timestamp_raw") and e_del.get("timestamp_raw")]
        chain_evidence = [{"delete": e_del, "prior_creates_sample": related_create[:3]}]
        findings.append(
            ForensicFinding(
                severity="low",
                confidence=0.38,
                title="USN: sampled delete chain context for executable",
                reason="Executable delete present; combine with BAM/Prefetch/Saved Files for stronger 'download→execute→delete' conclusions.",
                artifact_sources=["usn_journal", "bam", "prefetch", "saved_files_viewer"],
                correlated_evidence=chain_evidence,
                timestamps=[t for t in [e_del.get("timestamp_iso"), e_del.get("timestamp_raw")] if t],
                primary_path=name if ":" in name else None,
                tags=["usn", "delete_chain_context"],
                risk_score=15.0,
                metadata=DetectionMetadata("usn.delete_chain", "usn_journal_parser", fp_controls=["sample_window_limited"]),
            )
        )

    # --- File intel enrichment on top risky paths ---
    priority_paths: list[str] = []
    for f in findings:
        if f.primary_path and Path(f.primary_path).is_file():
            priority_paths.append(f.primary_path)
    for rec in ctx.get("saved_files", {}).get("records") or []:
        p = rec.get("path")
        if p and str(p).lower().endswith(".exe") and Path(p).is_file():
            priority_paths.append(p)
    dedup: list[str] = []
    for p in priority_paths:
        np = _norm_path(p)
        if np not in dedup:
            dedup.append(np)
    intel_map = _intel_for_paths(dedup[:max_file_intel], run_command, yara_dir)
    for f in findings:
        if not f.primary_path:
            continue
        inf = intel_map.get(_norm_path(f.primary_path))
        if not inf:
            continue
        if not f.sha256:
            f.sha256 = inf.get("sha256")
        if f.entropy is None:
            f.entropy = inf.get("entropy")
        if not f.signature_status:
            f.signature_status = str((inf.get("signature") or {}).get("status"))
        if not f.yara_matches and inf.get("yara_matches"):
            f.yara_matches = list(inf["yara_matches"])

    timeline = build_unified_timeline(ctx, findings)
    clusters = cluster_suspicious_windows([e for e in timeline if e.get("source") == "usn"], window_sec=120)

    return {
        "findings": [f.as_dict() for f in findings],
        "timeline": timeline,
        "activity_clusters": clusters,
        "intel_samples": {k: {kk: vv for kk, vv in v.items() if kk != "signature"} | {"signature_status": (v.get("signature") or {}).get("status")} for k, v in intel_map.items()},
        "filters_applied": filters,
        "session_anchor_utc": ctx.get("session_anchor_utc"),
    }
