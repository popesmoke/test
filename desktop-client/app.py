from __future__ import annotations

import base64
import ctypes
import functools
import hashlib
import json
import os
import platform
import re
import socket
import string
import subprocess
import sys
import threading
import time
import webbrowser
import zlib
import math
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from tkinter import BOTH, BooleanVar, Frame, PhotoImage, StringVar, Tk, ttk, messagebox

import psutil
import requests

from runtime_config import get_api_url

API_URL = get_api_url()
CONSENT_VERSION = "2026-06-02.virello-scanner"

SCAN_STAGES = [
    "Preparing Scan",
    "Checking Device",
    "Reviewing App Data",
    "Collecting Diagnostics",
    "Finalizing Report",
    "Uploading Results",
]

# Progress bar uses 0–100; the long build_report() phase is animated slowly instead of jumping to ~67%.
PROGRESS_TICK_SEC = 0.55
PROGRESS_STEP = 0.25
PROGRESS_CAP_DURING_SCAN = 88.0
PRE_SCAN_STAGE_DELAY_SEC = 0.12

COLLECTED_CATEGORIES = [
    "Device and app diagnostic metadata needed for review.",
    "Recent activity and security signals relevant to the support case.",
    "No passwords, messages, or personal file contents are collected.",
]

DISCORD_URL = "https://discord.gg/wPZXKaPyWY"


EMBEDDED_LOGO_B85 = (
    "c-ri_^K%`J^TvB(t7&YfP12m$=4ou(Mo(<pP8y?WY~v(pY}>Z2`~Kd!|HPg7yk>Ux_r<gG%tk26OQ9hXA_D*bG?28oG5`Pz_"
    "`g7e|1bHGFa!YrP>5DyVu~O!F>*y`2XiZ1GXTK-w~3)4e-8kb5grw_)q_St<U$@9D?thQ3<DoO02B2~QWOflBTQbI!y>sg^X"
    "ZOK7>Z*_5iT9fF@|u3GHe5}Wf5XLQzE*NjsFq|vk5I+PhVLP+7!WmNrFOTLf92KzA_>9pS-9s9p2Y~xktb<XDd(fFrpjVRnb"
    "8RJd71Od8!e;Iij(ng(LJcSpl^l7EDmT20Z)$5@Kyp1}f^R4go&3J;gs&Tp;kO83?rHi^CKP28kFeQEG<6g=fsn;NuH2Sr~4"
    "`m>ObsK_CzuG!#T)dlf+Ycs2zY;w*tPzH$I%4yp(0Fsi3;Dpn9w5JeCHpkzTvNXm9g5dZ}MfW$>q-G860Bc$tTcrd?xUi=x)"
    "(5H!MV;rs1b?hU-Lk->$rbh=oiGrXhiq?Z=zEiAuVM8NP1b-2gCKo>HS0y5P)ZeEpe>{G_TVHtWu(@PoOWe1IBz_19nSj_VC"
    "ZgHBayu8>H=r@G{>T6LAOGWj{QrmdKqi;^vPIW<=9gD;%Kw9RC8PVu!T)I3lo5g9HO*Mgi!KNt{vUUNwIzRa?k(!At@0&YG}"
    "meh3SnRXcY(O=xaQ{OKt6#84t@1X`aJ?f@`Bx!vJH8cUPB=Rl!$O&5%sT8WkiZ5CcB7%0DZx*ze8M4F!_a07^<Ekt2NdkgsY"
    "8sbj&(Xe6h8UTl)V1qA2N+{ye08;^42RjkfcN!xX12z^_|e)};$JmgEc7F5^)Ra1i;=wdl1lK!F6A+icul2?qt-`$>G-WaV&"
    "jhbaSv4P2WphwDYVuIlH;f;+E>S)tKK;~_fwJepjofzkW}E}+T}Bjm_O5^=Dq4U8&^f0BAtPj<VTVdi52IC(oHJr-F8;4%-F"
    "wo`188#ehq*u9<q7t53lowg9O9eP9Y%QVXBiW$sEa6siN#)N?z0#phJZ>G-Db!L<A*mwhk_pSxdTjqaRU723o2#ED2%{lC`v"
    "l3~Fm&#WZrcDYkORurh`P3Jz+QAPsBEB&vrT9)R;(wrHOYMgnyGxEJ*4a+u&~;fjZJDQE-S-Id?#;H397;P-<F!Zr5Eo}uq%"
    "49YO!eL_?MTjjHjV)7f5o8W9bt4r!+Ax919ab?a2b~IhcRzDqCNb(83BRswxDFBLIj0}Q7&@dZ`4|j8fKjanYeaW7vJz#ry#"
    "PP^*p`18R5P?FU~wEwQ}j-B{gjz7)b)240@Pcc&~L{>_?eL4pu#emjLxUG{d|?Y=O#idR*=JUnKZSh=c42&35TI2%6}a40+o"
    "yT^J2GP&hD3u)#(*ACfSLfqOoU+I2V%na8Pb1u|XAh$A?fsc^F{ri~by>NhP151ssR-c=o&T6g&G&vlWxaCJO+jerJIs6qH0"
    "{CkKL6LO8&>yOS`A*Juzkbn5DF{mb&{}5?USx%-1bYHBZ*@2iPew?$mfuc50wMGT1<t80HbJ~<I{YRrK$c>m1R`O^tez)D9#"
    "O)8n|H3{Ff8is<pPoZ<roUDFJu2-9N{L0LyK5{T7-CO_cK;;u#ZIeQ4Hxiw*y+CPLNi$P#4tBYt5^ygJow395^;1`HOr|={J"
    "qmAS7x*0u2P0j!Ub%6J|n_-c{y13AqaMB$oJFotJ{k)fuzB;W2o8)SE9qlm?mtNQkAM=s+HB0spV;hl|6?C!c)R{){<~~ciJ"
    "#Vd0;(tZB(X_cp6cxzYCouGUrlVE{XuOjz(WmpIvvTQ6Q{`LRDl*ADR4VaDxr`j6?~i!XBLQ!;m2}L$i7yF;P>}{AOXwwP8a"
    "OGyz5oz4&r<A!!)>e0h2%!!~3H*mS-eWA}<~Oeqfy^UKOmqnC~YfP;jp2?76m#ie|C{_{Foet)U^!uob#Q}r)a&+Dr8QZMH6"
    "(j9i$8!Aq9q~o!u5E(<0*BVTuxQ^_8sD-yPa=~Fac>tVE8cZFb7Q8XY?Q<2c(XLxkFS~A`EjV0X+0Zx3qWw9`Ryt?nNhg%_<"
    "0gjP&QEQiCrX|hizt<O(9i|}*(o~57G0oH0y50Vc!g#B0<nj^Cp_6lesjigS`WJsD}{tb8k@5HP{ky-o^t_0A}CvGp_tV@S;"
    "+nc=(mh!$!{v)T__`yquiT+?|xg6eRqI|%k1V9>Plx#@(<wO+!>U1%p+ir$Mm;o3ztJlu%ZM848e-dirW%~8yyju^fhen*E!"
    "yJ{A+^Sgk=rEHRW6NkA`vo5kGn?8$^!?+~)%7mm8Jp_T~(O_&eM%I4{@ZuJKDtdi>2dVTN&lY^02X13h1Yy2bC_5^4RiZ&on"
    "2s{P*2-KQf{($`uMgjzoJ-}+Ktsc*k(E%poM68r>%w?!jjzjva~)d8Ne8u5%%PK}oT%ESwqG1+(R+P^KjEN-W2S+T-_zpk?I"
    "as?4^{-!KA6v4~;Ez$mR!wJ~Bo0oBV`IhC_yM<hFbSg%%nOJhn<^L0nJ}qFFz|b4D=O4TE>}=_1tZ!kgWFx%R_tD*ZXaRlI!"
    "rUJXS?v!uzC=H{klBl}{38wVPe9B&*99T(SY&QRp@1l2Qhe^aphObG;~c0L8>W}W<rEs-IVD8|4Abiz*DuLq{@z{;zeRCFnq"
    "0Z<?1ZI=rWTN;Ys7z|wDE!$06Uo2NwZ77hGeA6t=JfXFZ4|$_=EI`dBOrr6!C|oX+tnr)4v)B70a2nE;p`qxb6D>mVVrEMxS"
    "rQO?$!#Ej5xD+*s5GoznCEycPvXW#jmJqVadQyz`XGpa0|O1|!v6h$nx?@xIUTx@skRN9;S6Pe_<FELA>qk{4I7(vnfy7r=-"
    "aA^zDIS|#B&tLF=X(#sy+8oMWQ9C$&~TwM(^t7NKsPx@LhIRW^uLeX(1FI&K}B$e<oHEt2aQ4FIe!3tn7mQ>A5e+L|q`HF(U"
    "!(48QLAS?HRp(EQr4oJR!CQ{ou+OqsZUjTDcki&rccI?CoUQl7uq*ed?x22!FQ<7Tw~I^RN^vItQuDiIhKUttOvtkWw1z}HN"
    "XJA;nbz0oAMSh4&R`=eg+;U}Y0+RF<Wg$(w}AF-kMe6TOMNdc-8>0-$-bKz(P)F?hHa_?XGw!H;YZvHr%it!qQh!imEJu+BR"
    "NK|B0k>_Azc(tZgvAtL44rQnGbo4&z5r|TbP>M|F?$5(o)$jxN|dzPgyZ|`EGjv{(X~S9t+4y3lzR)=&5}>4%y2HUJW)R8cB"
    "8lsEtOy@rE^>z&LKEs#tj%($#@8W1w(+G7vGEwtMGdQ(N~3L*SX8vG3>1lZ6aqh#SZj7O`z4D;G^=4O@d+ER~uWn*R!=ndnP"
    "K7jmlp@=-)<KoN}#e<Gj;FuWeb!+jX0<g;6TY%$3F4U3+$%mmrKRnH6vr$Yv?zakTVd>m9KijY$w(x^~G<B0wPd3Muu!ZC`6"
    "{&l;Dp+WJ2vF8lp%m|!Xhm)y;ljp}evWBxI@~sR^xM6&dlik^<)T#AYRp;kqDbD)0Fza8F=2ZJ<LRF8_vjZojpl<XR@6qd@?"
    "zit9`!}Qh(@3%gzt{o=3Ki=GN8U-ElCs@)e*h3#LkkM=VF2JctpofrCPjC#CWLASJ1JLVWD%A)oIkn9Hhu7h<IZFA=GTqw_5"
    "+(fyVlv1E3?ay?@9IPdn^jzHJwD}vOHzUX!owrZZyc>^YxauXf~&V73`_pQ7VS@>;3QlZR)a?p)+yJHAprtI!}-@LR75h1}0"
    "dk6z{0&^yKTiqV<zmm_ggZuqYQv?H|8xODG3?(D}zs$n}oiYly_BC}3+!@BPn4rynZ_zUP(%pc!w<NZfU0fcaOk?8!w@f^_w"
    "a1+(~*HUJr1FQO9oV@8Ag+=)COgnZX{?q>S|Tws%jVfXG+!{_B6>q>5rJTEvhJIf8!=tX;64|CXbrgEiPphA?f8Wz?tz;KO;"
    "z83s%_!bdV%rH%O{Qcey`~s8O+Wl*lh@Xbh!XIMA)O`NQqck<7Kg}lCxhFp+f|GYc;$nZ6&oKHwx}fiX8KO>>k}nk3JI#6O@"
    "O~qqHc&DiIQFe$Y`q&iXOhlR7FK=NhkspWj67<Yv&a~UHWnBGr54Pr9j{@lZ_Thx43wBLOl2k1dM5HxyS%DEdSFV&WefRvB3"
    "9Pe3$#fj_xeJRq(E$fFrkrHMRv!w*-N>MWp=ZnWC*t?9`CvA3rXL++I+}y;o#Br$R`mHarFw~z5?O_1NAA<)XAhUac)obg44"
    "X8f1v>=ldgLJe=Ei}EiOD;b9U(@kz)sPDA;e<@k(J)9~Y@#<y*eM0)cp(TQWkhlR?=`z2k=omq#KcjcAfxfaZ3*qtp3fLWB{"
    "Tx4VFLr~4S8{@9;-LaVyGMuy3cV&a3vP{JU<liNfG;Ii!|rG^!KgzN3=?4zK+E{*V7IExvfWrbdppZgW=8mb|)0rL_4AOJwp"
    "xBxgw0c^~4qxWwUbeeFTrztX}Yx;g<II1&C5oa#x*lo!?ZiFz~`YLXo;jHl0_+;K{N5q<qu4*UaNLVJ9d4?IJW-1GGq0;L6O"
    "c%FoB`4JynRVMP!u+B!wEP;Aj|7{fVi_%0z$<{JGH?nPP_^oY>Jf|o9UZ*iWy9ks)wUcUWJDQFlOPak#~r70bt3;hutVs3i-"
    "h;0@D)*!cPXB+G<Wo)n?H#EGzkuH5QMIP53q!1&iM=e(nH}lNiA0JOp<=<x48FOgYIQpGz!;iy5moygo9FRMWqh^w&Y)pYO1"
    "|zgcns4SqbEgJkoDQ*6jL<=rgA3v*!ER*Ya@T<@h=m-^DpMJ00XPD_&BGL$!}Qu(Y0alzwp|gt!Ic@Wj!vbI0aC!#L8s7Cus"
    "?2N{B89T6u%|Jk|TBB^$@DfY^8rnNL1&sica#Y_qT&z%6~-~rvs&8TU7B)|u<U?YT@dRpjzj@qk+k9YaEzwxL}&U-X2JFs(~"
    "dfdQ=N1hY?AKz_6B4Q=#;x;oEu9=}6&E1&wollOrZ~tLW&#$EFJ_iz>WL=8!3xq7!g61p^3{`zJ69Qq;qv@ADQrFE1{#uMiv"
    "L~{Gm*?Y($-4Cevq~t?UK>pZwNp!xo91f&+@560?3ogjlP-#1#seT&1Gh}<pEf@dX8{mw-JaZn*3aHW&qx5I_wm_u%;Jh=H{"
    "1YZLB)82m!}#m4T=N6QN54;lVsDOe0K{kK7$5jgcw2MsL9Fqp>SnqLs=Q0M2cP!HJ4FErRv~`-7A?aPcKEx9pP$>IeL%3MJJ"
    "Cgv2aEck$D5$P%%Ju)fXh>`zDM;RJ;#h9>r%s%SklbwN&?u%~9%NLM0#2;~nkl@mxfgfnv9<Gz4ChE^J_h<7qeS5&|=0%AVC"
    "@88cpdd^GUi{NDf7u>d^PyI2@|v_@K5<CiIk_B4U%j@pvMIvdgK{^Z0~G5qN3`s?&|?&piUc)42W=1uF4j!AOA(BM|qdJO7}"
    "znh`;wYa<Anm^15OY-upRk!XnBl2>GosUpLJ>SIebN%xC6VA009Y?%I4qM%pJQeJW&l_TJIrpdWkabxh5UR<lCmanH(Qs&@9"
    "!}h-4(L*0n#+rxl+vA2(n54Id^`S(dzmRT{Y6(uCb5WF4sHhSbEnq(hX2OrC#LYi(6~WvRmcUj)W=Aa!22Ho#@+4s?$d1py%"
    "KV1yuc$T9}LwOlA-R};!&uX7r$q|Oximkn~E**VG|c}iH!_F`H!SSFcY50S4e{`i6Y{@4KF7&PG2+09z1;f@sYUEvT|M}iJ&"
    "NPIH9|vF>&+dW(b*Jiy8uSMMH$)gkyr0&7jF_VTap)4iBuU7z<rgK##FS)qQ>Xv>&ApeYO!cA{J+Ovw?t#ftJsdx_F70pCvN"
    "vgn5s;b=uy%Q?7j0SVWYC5qtagr;rrGnD?X-W=;m`ZTc9mz;O%kRtsY}YB5#1cyD+#HA+=)&J@Wkh{AoUD*fY<%kRqPZFaHi"
    "2b(TS@2&q)={y{LYeo{`M2sXlUXC;C5AJi-3WGLS$pskNfdBz7V7r^p_r5;F!-G6Rv?ZnBXnl5O{R>W;tE5mcXvXhGP~~8Q;"
    "qR)$#nNC{g&iLAL{`zNAEoabcL&wn6!XTr(2ZfY7?bz7DH2oe`WeU7zc`<Q>c^)?klP29Kp5jP-Uwo}MDF677mXI?@L=p$fT"
    "cW?^an}YT_?%QrK3A;u(#eiDG-fDnw;WW#1zk$8wW<AR&(=#x9)6hOLj~Aa7LLpN_IVrkS@W7N&^(>42ZCh;*im04$M-A30+"
    "m^zAHaJOQ4l-H;AeyfP=y5GIqTqjFK0*!jievu&rY7wew8k&yIuN<vKmA;MI`&)1yFSMpzRhJu8GHth5}yLlz}DOYCnaNnE4"
    "*(^cQ&uQM_d75D1`lY-DwYJh`Y8)4cq4>tmaa6hQN3bn`=1(DUR)UBbg<{B2<ePbr9Lqyv3Y43ey^BI(d9t~j$u$3Zek{`SJ"
    "P3{>$XltV+(iqrAcIxR%u-MRLxZ8`(wLOz0Kd3dT0V6MYc~}1KReL%eX2e;hnDRYZ8?EY+3Y)<_6p9GGSM&QY_IP6p<5O0*L"
    "He)mnkR>a2|5&AKA*Mxzt7_q+VLOy%(8gWAjr0ef5@Syw-sa?#f(8NONg4oSLxEfU+y86TC0@Vd!Y9Ta*!J{=!5a%U{ch*Xo"
    "4E|Ra*LmlCk4+Xj7_A(cnq{K<L%!8ZaCj9~u?LDUu8je#t(59PP?Rhc1HhziXGvnT)qW9p0?;IHk&^8aJUKS5e0rX@Ubc<hw"
    "kRYs0@J=rw)O>>{pVBwlJqSrlp`Slo2OApM=bkOW)gk+<!Rk51TOkJ$;RB-Jc<`-_yfF-7v>_vz9dZQ!x126^J{U3KU=>x&a"
    "TCk*7!2&JkfF9~t3z%+9X@1!(;X}?|$(z$-0A--AHb9eL(Jme+8b|;@za`5Pqcux5;0e@AS#4K(!NSbU@cr=V>sCH^uif=Y6"
    "+RusQ<<U^B6+00%0XM;obMH)$`!UgcHB6>oek!2zvU+`V#XgBrfR_%1G7_2R=BVBad8V_4FiZ%*Ftn{I+FnAJq5boEFmYb}F"
    "?KEx?r2S@kJ+P~z*v8u#kg1;kb8HMMsOFvdhh)VHY){b`0?8>w_SA|6tF&*{*spP`-POv&#T|C<>#$Pjzmq(1Fg^n)3ubZ0*"
    "&jsoI8}%oeXja>ZgHKE~|N(RQgJ?UC!+L&>!{I?-$o_w;fI<bMyfh28Vv&_Be|g(QlxYBhytaHVSvgM#4G;L;_HE&qBrC$*|"
    "J_*~zNo5Rl@<^M72%cmH+BKrH@Cg}Tm1zPS>*v!(1_o(j?A0igbX+d+(5_hGhQ?tnA!yb>Xneu0(tLcF`XGk&EXg$dV3<g5}"
    "BiLqOc<b?aZIUV!(exOrh{vH8&SjT_acr+T;T%5*o503}Ywfrjyni?s{8P1=ci3rn!AzQu$xRwZr9JJUMn84!kg2%X_6v>V>"
    "V>DctM1Zb<m<*#%O-Jeio6^03A5B22`eKCFX}1Hbq3j3Bb)1(lp%=l8&k$ylpXTE2kkZLtK}UF2pdJ-m=(*8a!MJ@pm4Uu$U"
    "2mQreEX=TX3gpx{?|%#7#IClT`;Bcvb|++Lvx}nzQG0ikVrh`1v8dXx9j`BNq^aV1=nXh+#}FT8zWSb5LuVIf@|77mw9GT&D"
    "5yxHR;PP-aCpGAdK1Z5O3t>qn`#kOb$v@SEbwi+D{r2lDzj+6fA;!1=4;q`ui4@<K}b>Nq~lpsz*6^T%DbJKX}dUu-e8}G3Q"
    "02@X@@zzBR*(5=H+hWRVCr{f0LM`i%PMobmI&yFR`JVT29JvBuj%!?7)F=Tf6mEq^_JETn>VLM3B?9+Yf6qOfHk=bH)&zzK3"
    "}O9S-FqbjIf&t~&oUkbh8K8SbyK$|iU*fsLY)`Al6rkClch$Q4_fN{TM&<|<uI5YF#6@B0HMBQ{D8yiN_oab4mUvM?^3>T$J"
    "UX(!y)q?1Dg)gfGJ%u4u4a)h$zO?8Um>^?V@|rUu%w^1AI=(+^a`Hs2&3zp!jh1e9U^QG~P189hYLny)(n4|c^sKo^j0(6v1"
    "@iJnf4=rl?zXKXu+S<T5#pz5DU09znl};Sp_s~8crch+4&c&rh2wl+g6hRAT?p8wh_>~`EL~KzQ&oB-0`}tP7*RN+zi1pCcq"
    "bC(oMDbqYCQNRsr%GD*)2Sg@%sLFmcBVW7)%^+2CaD33;E;7$cre4`4(xvAN(SIp``S)ztCh>{S!rfHszfo#smw68wYFqk@>"
    "dx*1~9cUoSm%i&$-VOM`yPcOmt`Q|j(?&?j2?>224^I5O)$G&^Z5Eu_JvCi`KBD~dASEwd9Ji1e)e^J6_z1e%;v?EN<VaxyP"
    ">Ys%0c9kyuv3tqQ@B;UxS)=!bWZp?gACVC^d!3HClE2?NkjjjoJ#bs1$PD3*RFxaK<{48Xe3-NL<hF;2rpI0zg!S9`+#Q`kJ"
    "g`R8(!Mv;u_pO3Q;W1mV0g8phGzD$??GiZ+M;V|-E97~eqv5Z<0kzFEW&Q?MBnK|jo_y&@l4Y3<i6k*qgorEP`L0>-P_14_4"
    "Z8sM5IXRR{=eRZ<a_2{WeM0gnl&MuV`D4cf5TVeXdQ3fr=1k$K*c2d5v_|WDHx<BW;FaaE57}XMmXR9a>JWS@M*vL$QIy{b>"
    "Ja-$2M<7^qqmPvJub<ZvGUX97s9*9VH{b7GBKSrf@RucG+`hq66gO40WukXn&_dJ#Z_xTU}^xQ^KT-rM@>vO?NJ?&x@vx(Nz"
    "yLUn#00K<4%i>u6<6TZ}0Q0SL392;*j#=zIT|JL3W=lCQ7J3%yPqI&fC<d2hGJi&me`-rw^3sv6#E;ql^A8{{to6h8&zU_|h"
    "#1LD}<-><ZN)|G^^6>F}<qpZ*H?lHOfv4z9b?gq{HH+we?w>MRA9~ZE)@Hjs!6Z;=`|DaMEWto4IxWz^v|1J#;xZZ^ZfE<nU"
    "VJT+J0LPnRG@a16e(%qIzd(SR#DOp+daq9k{#mi2K{P_3oRkGDyDZ#3cPSsP^Li%`S)#>9?}+=EI<FiJVWj?PgQR(PRHzkc_"
    "jpr6bgEKs9X}(hKYjALUR(&JT>G|6P-j|XchP>u|FLs>G5+)%hSclptFJp+;CcIfOLvV@2*a*uN;C?GVr=<~%R;SyFpp!s9z"
    "MxY&ua5}APIatk!D~e0)}&^_~2L4De#!){Cu%BHue(YmKeii|JE9@wThVKC}DURP4HEMQ$6V1K`b#4Ej=e@$^~eHZ>iP#CHp"
    "WJqe3fc*c0vZ)P$^WywA(U=MZ%gryw^&P#7o4;Q9vb&u-+b!XQ#-=a7pFU=};Q^;2K=Vgrgp07aw3OSNo>H>YYbnby-4RnrM"
    "oEY4pBw{!SLPdx<mvx8AGiR8LSBzw+z)!OK@yR}832u0e;wE2j2`OUrFRu~#?eEmwy`k3Z*E1uRXN@Y2V<ATMu5lFYCXmurw"
    "z%=6>a?tC0eG4)X{$<qTCq3?yY3%0?5826fWYbnv$o0M0f%pC*ZpFE2!$~nW{=T!fs2LJwD#(cbg`P(5V}J8y3N=715H^hCn"
    "=QO<CW@aJ(;YdtvX;p0<qT>s<45@q^zZC`oMDsHQ?sPh$rMf$?>;}3!l9&`=^2l)5=_1DmDnJZLP98Ab`-4pN7i}q<2|=G>B"
    "wSx@|rOZa&%DT>d+#=UKc*FLT%@+x_os~3K;ls)a}uadg7CXDV;uLoIL2kSe}56OS$U4>fbKtXU0Ud-B&bY0!<_fYs6#PFz3"
    "&x2jA<5G6~3ClNf<)KdaDgoRb_x8ka)(3J5>!!E^(x=nspnuL^^t`r$|EGly+ueUI1h4Lck%8inoZp*#YS(4wYx*lHkb_;?O"
    "}AF6L^S+z!#K)pFV3|}3-$WsO3L61WKUFD#gLkn*A=dr@E{p2pcL3j?=sE)R3tLjYqyYipsoY88?KAo*71|xSPZ^1QI^u<QR"
    "%pCsP2%~K`RJp#G1uaIQc8C!#qAi9|#a1YCto;R@%nkQ40oQm)e^n&<@lR$HK`mY0?^<goVMCOdaToyVl%w$p01^_>QGXdl#"
    "0F@$<2j|tmg<y_y*QfR$KC_X7P9%<ApV5Jak)6Pnkm;pJG|I@o!u<(8|v)B@!?JFQeuDCU$XMO$<PXxB*MoM?pT-g?v9Y-UL"
    "Dtlc_W89u-!#E7YxccS1T57TePs`UPg&;5-LhIOFTU6e;PAm!SvidB-HH9kf=^Z*LZ(Jy9}FJ)u;ia^2h~WM<qgnI{cK9L|i"
    "ma{j3Jk86T2(Kh5()_&-G#LnKTH$<jg+OurRPx(@AhKc|~o3nyBU`!Um@Ne^x6AVX6VlZ)UZ0f!XkLt_9eCofNt@r@?wM&Z%"
    "N1@JJwUMMAd-*|ba>TTgxII{yzdW>wV)0}2ENS@w&9*-*O;QfttNOjD=cOX!CqRSh!>Bf*QmD@Zc*lulpJiKde&LI8g@&2yb"
    "OL@G?8#=?=#a0@qyyfMyg(VyHMefz3YTkGv!x_k*2Ke%4x?LTgW9+zkj9WSkURZI4mY85L3xdbA&~$LHb}$t95e^spH~xa~e"
    "_=aP+!r9{&v_Em{YnSJM1h$~VfI@}vuMj&QCH;k!*-VcK;iw4SYIXW|9n2PxY}hxaLFxg3MgLk-U3XL6j&S;naRvoL?5Aubz"
    "Y^_%4+C2qU%5J+)iuR!jz0c3ge7TN7cpa*{&GOmf}@?VM_ABVnQ;wRi201xHEMttS<1vY}@*Rl+OYnTKD<^f#ph#FNpD9FYa"
    "Dz8S%dV9Oz@(fYR`^;M0QDDJc~C@psQTDV@E9%|$Z724w9MEseVYQt<9HsV={oy#f4XN?A;cPLnbvEQO;$T@~fr3?xUyT!#0"
    "?E?uQ1YzindDlmrTfVo1$rumnSM3`Q&$fC_;QlQ>jgzO@9GD0DCj{bf>We*$X+hKK`$Y)i%DBG=oJ6Lz5ryJM(#G?K}YllhW"
    "RoGWEWk6rRw;71e6%=TdXW2T`BfJ5qOAw_E--f05jW`s_!s=pRVFdeKJTFruN|PC)MogJDP97P^J}Zp7Wu-1j|G7~o>}KdSY"
    "|;x1wxeCgpq?ThH`w<`^p6juF(Y>#JE~52D<7W7&BQQdjP{-r!PR4;6cQUFGZ^=qg~)n}9M!}U>m)uKL8J8v(^t}g6_+I~HU"
    "Vu5l`!%=1oQ{B9)s%M=Ow33hZFBh2!@my<PaOAX*RI2LRcn#mMAF%8Q|c1-Rge3S|zFuT_DtkQ^>U$;_m&0z=LVpOw^yDTPn"
    "J&5>u4I!d&UTe25&QZ=ABG9{=?6AKhTn&dCh1s$kqZ4*c=a(mxaol3(&?_=>YCVwy->yL4T!L50|sx8<cNVM;Zur4nfP$_Ti"
    "Fj;8Pp8!3tH!a9GvCx*u@dnDFYV;^E{rhVtD0hJPOqe6bDxlhyM>GNEH=wrr250f#s#FU=Mf2xR85nM0DaHm{e*PZ)Zd-~n`"
    "mM!v`PN7uT(tVGNl3mY(GIIje$|(vT$C9$GJ4Xd_M|0*jP67IDmT7syb^J-Sz9>;k=Ao_Mbgo}$73~33B#6oVZPi7G^@VQ!n"
    "Y&M>8B4Y&cx8%{nQ8h^ph0h~r$0sjt-Nwx-Pur@eZ-$9;{iZ<yoiJVT^X#AYfK)_lNtO8&ihNBK4GzMbA|Y9^Q@ufe`<t&_e"
    "d+-2eampZB~#~7x`5cJE$n!u5{WP8Y)S=?Pk5t6W&ude#YNG8$Ld<dFk1}B){42o9p_z%xw9;@g#k$<fOWzw%8pdlLzePkB;"
    "^x0V3=X5xK3*gO{(cUeRFZS^4{>MBqE0;zYAW@`8jtX9AGSKqV5<(lp1fUjQ{=2;K0y<;B%$Y7p<dAH^(%`p27Uc!)h(qEqd"
    "a+w5kR_F4za0#sn%w_i#FqA&b24CL_>yOm6qI`xE1e{xXoz=n$(0xci4Oiyca%`%0;@3-UoC`&ruZaqcszE0@X>YlGAoxK<="
    "t;TNp4v#u5NZ>&?YN5VAX^TJFiWs#)GssIqIAQW{2r2!_G>6?4RWb)wcr+cAe(9>Vw>iov_6SAW_Py(pO|!(}5%HQ=Ld}ukr"
    "ftUronl@t2g#b@dh`hk{OAMgb-tQ|Zt2&dv|WQ3xnq-x0z;rqX!EphhN=j~2lw%y{@C>{NRjn<eIDmtP1z#Rq{3ke6zdNvGl"
    "{?|umS)b2Z1O~(-{_q5$qN#btLlwUcfdlW<qS0p-_st5r3i(&q0IX3x{7tSrrFnX`K3&#CSTO$Yy=akwI|UQ_;2_Tcu7IoN1"
    "Vw@4wtL`_V(tu>W71&U+rR=Qgk~ZcK^%uekWhuZq=+E@AHPvY|zLbnQ~9`+xxUk^1{ZIZ~6JF;grH{y8R;`QJfWvyc`XBT9S"
    "2Ql*}a3=nYz$K6FWI<j;P`Fmq4SIpg`Qd|0jxwB&(PjE><WfJpP-mZU|S`J0N(sOIb%Vu@ipf!^zs{3))T6h!?4SlE~jK;C1"
    "tQclgTYLI+f2s`iuARV?NU*~iP_Gn(?42z@nE{=OY&061!?<&g-yH%U;wh#7*^$H&*7i^I@{EBb&#L5=&x%KcZP&;NA<&%LF"
    "yBJ-%afJ7fHX9WGc1Rn{dK`X7?RH&;Sa*pkj!1knWfm^h)6@F9vUM7L>7OmEsU(!qT8);0x^EeIeFZ;h4z_D9Ne;R$MkbNc?"
    "xQaYmyh+!J~h4nzx16{f;Gi)0^m^=}g>6-t`{Gn+}QGqL11^rn}_lfVyXi_7~V_(=8SB##s5YBdeaUrnLwJ8uI1}42(;%Z4c"
    "=|M$$F#7$IP881QlP56@)Z7Ogb`$+QpPq#IP1M8v_y?h@&s2eK0W4gSI<tC<jJl#z}s6W&SuyQg@l${?mUr5Y*_UhpHPdS|n"
    "$Q=SVkIm?Y9tzSBY%T8QQrcSHan!~4X0cDFMO)pf#mKTmG2jvM3b={e$AOZBWs{(w(gc}VdkyKO?yR09{@v3LZEi$HSFCV_>"
    "?s5eA3*(wdX7)0>taxrW1CtfnKL23M?<owYcZ;)vndj_a?mwzbp*6plDz?Sy6C!ITnxpG1?#uA{kx%Zg0P8*2Wie`Zp;KYu{"
    "g;|tPCir>2U`sKva#Fmq^E1a8r_*6+A?^b3T||tnu}=k%i}g6Hu1gm1o;g*@;FjcV7h~Z#*Zl6!H{foB<|Wc-A?2}?a*@Sy8"
    "?f5X~|cDnRTKo6TdDk<1f;Q!g6)0X(lvTq%vQ^r=p<WXXCd-S&@4Adtt+AzY$2Meu9=k%C<F_fcQA>)F8>P!eR7`NU-TIPeT"
    "ojz2~RGhbuTW3l-2Ej9sp~F;7cqTt_Anb;3)G@s>Rx8~FLTocE#7p9+y4pDERSr$4%Y&szs!HT!?KdU%1c6N(fJS^^~jS_~P"
    "ONho`|auc^9Sf%icgCbvL98wrdUfZr>2JpMMU4;>LTyGmQVx2mk^Gwv!;N}UT(t3If96XWED)|yZFc_)|vBoGb%`u-@5mw|`"
    "0ekR@ZRRr4_*lAqpcxZ67@B1lYX)eB)V#-HJeVx`UM4Qxu<qBh!&<Tawpx|LI(_~ozvRQOB#ZE?+G=*@>dXi5P;Ubscsq%5b"
    "SBSrP=>a!zuY!su9;S+2(v85)bDr3lh(mj`UqsC#4WK=KNWK~Gh&LKL+9pB`@Lu8yS2`{f%eQ=H8e&+!NFLj+jK#TiA3E+2L"
    "9RbFnbkg`x*RE-=aKbr{v&@OAOqCxTv3XmHTH=VYyJ)b}50V(ON7&-+h*FRBJ4ZQQK*yfYHKkUJgHQ?$In>I)@&&GvIG3C9>"
    "_<HL6V<iam9^_3wDJQbs+8Op6@>rD_bNDF-uHKA``W*oHhQ6^pTPrN-QlK)tysuaiCOL7PNxL_!HYxfNNKz{irH&0A~)y6Cc"
    "R=M3YWEp?=tJCul~m~5Lu4zW1Q{|Elmrr3-w@Y(MsH8}&(YA4-Wk~h&wi9mvtLbQr`c=|ipVh@5!AP62>r-y#&|9*0O9@vh("
    "@T!E!pTBl1pLzwjPO$=2fWVs;9(3`+TvuTb()71h;*FO9uH75FT$t!+@|FiW{EZGc`*kT=R>Kf1U7somOU+RG66?{=osimUB"
    "p8>cp@a53-nMIhoE^V&4`GX)AtbKedn}S&ccXlh6;`~mQG|_6H`WOk9V~^jutoYl78vrI?SIZe4o7<4RvTu#P4@IOY=b0!7t"
    "x9h>gSNWN;6Wsj@{CjMJ|ttwsl=u3Y<xD-zJ)`BZwU4+P$1jG~GyKpNNUX2Gg*4SLW~L8aA>C09OzHnH>hM?8u8$TthHy62?"
    "YYt=;O@d|3^H8hA+ye`MxRr;a;`MngG?xxJP~b&EXL_0Yl9bCCy7Qxwa$?qxR-rSSbOgz-=!5jqDJkXZFnXTuQ1$8(yL`3oT"
    "d84OUI(0i8O8?RvlvXPc0h|*Uh#YPRe-VaSV;~SZJLa(0Iw~*3g!%<g%asH6enmSU^)zFzuhcH%mYhx+?Qn+%cHP176o+q>}"
    "PMjFBgoo~ExXxq$)P^zisUl;DBC+IRG&O-Fn2b0;V#Jn=D(Ixsoq)L&%-u<Ft$VK2GWXP3)CAM%uqZ`wkX~n_Yk5Cq^F(%W*"
    "%7G3_}b(mMr+`=7^+=()*Cg`#2|F>bRZLq2yuRyb&Z`^T9m3Cf~y5t>Tge6$KHtadmr!XlH8r{%Qh=PDsqi6lTTuz#OZ4@36"
    "?))ztq4`?z00)*M|;XVG~`w4<zYr7uw?OkG<(BHX)2xcHB+i?PSHQfVRJwoH9Yl$!|wFpP-C%u(R{8^jl(C*QVWDFVfz{EfW"
    "lbv}5ib0Dxo`9)%}`NyCZLUuYdnu<}SIY;OK#SvERPT~Z_tCRy5%S3vh9z$~XFa{FXsJ+v!tPK+#cKhK(=6d&1D2Wz8j|H%E"
    "gSojk_+Hp$ymizgH$~h{RXVZ6bGGHRs$KQRF-dt5K^Nfw{`HhB;-J$b}QWrb}(wtw0l9e^IzwN{K*;CRRjqyZNrpuW;P)wb("
    "BiP47a6}`D-S5SqArbPAV*G6jKkrGUWjq}11v*XMJROj~Y2OQF*7ELebIM}ep^hV8zD|K#>rEF*03W2G<OUO&PBZg0fQ*EdS"
    "+}5CiLLeFXK@wnhfni1b0pzb2c&8nIScVj>r9CMMEQbP7ww?+FkGl4|0)e)Gg%(DYRxWJn=W=Lf2X=T1Y-)<!R|?|@qfsVHE"
    "%b>>Q_uQQLu4FOiT&O;P)UAg^L+<&(H-?Ci!BBGX30gSa>=WV`3tTSBkFl2O2Mn$$Cj0O~(63dNeht_RG2wXX$3}ll!2|7>X"
    "({e4#<ZV-icFZ^=L<yvI-2hghEmT04kcM#;l0R7wh1ZbkhkwSL{_>OO0rddR}Y4_l(_t!s(Fka<p38^pJ39Ol02uIulHRnY_"
    "E&Bl*0TohbvF%O#1fhAqB>0e4?OrDf*;L80Yf9LZ0SAcQ-%j<_2*Mm6{XC{aI>s@i|8@;`sYQ1X7;<<8kz`9!j@`DZfqe@Il"
    ";gnxD8c*1DjZ71G908Ih$Z)IT#G#I8ct+ZrM6006+A-HuS|z7?V#vhFfPW1Wer!yuHXP2RNM|=fCtYrE6$&%l8?WHgJo7dRh"
    "F~ckqS22yAGM36samTVP1S4N#44uymFmp~q-ue8*@{uTEq20mk0X(>i}ff=Pr{7QxQ_kaSkq@JxjWSL_{t2|N<0lKlJ2vqA+"
    "#*U%Da|{19w3IXE}A#VMwPb0rRUMtE(IhmuKq5bXEKNXci-G(xF_Ah;)v>>FZEI6$MMTEUqIld(osYXPD<e|He-^9rFRF=3M"
    "XrnS$FR!?FG64xDe;e%W8?NYtal^W>c3ky_cYA<KUmR-HqsdBO^Ws4aCiG^yG@+DP!2ocZTYYhcJ?nKPg$q7`oh_QJo8hxqZ"
    "b&PZn>j5tv)B9I(J$So!0;}N4k0X&itl9eUN2i27A3y82nhfSf^oAU@FW)_o8qw|;qpnKu9e?yDH%@rU9m=tceI=1lv-9J1O"
    "TTw4^e?#Um*1|3wHuKr!@9LXyYu#K!2T4ehJfUdN6ct8zp0c<;cqe>^%^(wcOSii=N-J-OD<>}CpWoy(MSB>JAUZsEMkA`YJ"
    "ddV3QC75Qre@&MJGALVJgGEC4qJ?SU8sAtAotDpMVUpve<9EhDLfHDu^1ihQ!JGzisgLpKz@!Qq68oBbq`H09ZB{kGA+<Bdt"
    "#{KxcsiuFVqxWT1J^k#6_+^D+2R2sUkL5=+<j?G1a;s@-17?+zwsHLl)N|exGjM2ko1EB7k=H*l8AXJ&myMa`MNLGBY*jH~X"
    "Vk2O6D(e=7A6&er2j1RnDnTo8J%SvvX3%X3}IU9?uX+*Xs6Yy!UVJ=WDI;A%*#aAeugnE3MR{dXvqufB-JXV01Xh9#pEy|${"
    "~aA#o0Y0~~1t*Y6(8hUCr9YJ737^!nn5z!iZwX00OCRQcJ_Oh;Td4<^9s{MSti(h{SzN<aH+k7*2vx;3D!>b9<)i>LxQ~k>*"
    "t0+ARUqsfwyuQA)v=X(!t5`axi0Hj1r=sAA_{Qs8g(gOb^qq`nRgCE_pBP1r0F8*jT^>GFHW{%1JZHqJt_-cs%Sj_g=h7!4W"
    "|62h&XcS?Q{zlAMZQmegGyUqI$=07q(}n=4broBCyiv#$h%*=_1_<Ld}nIjniYDZAQdT!n~tTCxf<#T;-@`M*LjnnnktuH4S"
    "sz0a|jZsA#OPoJbSrG3#e7nJ4lMaVKvG_alVV~`cV&32x(xckVUi_Z!oM94EwDoOmmk|i=vp&`}@?WtQ;F--`3ml^_{myJuD"
    "=H3jLXy_u)$TkBK&yE=^2-(dq-Qa3?xXhu!?}5k5hXM)tf_`p;nrYAsvoBF!`aJ02;kHfoeB#{GrKizbz%C9LN)&_2^r=vbW"
    "5r;o_r<@D+ZjcX@q^O@GS!KS&Z2K?w^vO0wF%NuWcmL=XT<q!b~U2Id6Mg+O++A(W+n^W0ZCN;lk#ZbYp4PX%r2_(ytV2(`u"
    ">YI&~6nmYt?xsh^q_<K`kad<?lKmoQwNs>WhdrKrES^}h{?_?B0qx21eg*tu@vRgR5){3E92y8>hJq<!+(X4y8w||7RpczjZ"
    "Wo<fiIk$Hb9&s<Ka+NQIs~l$V{Y<~FlT_`wXP&QQ*D2cBkTu@P{_feSOE=_)czgIq~>wN#&a?5QIV_Mx<uCE%)3yr4Ay|vLD"
    "a`D2^d0m+nG(ie)!KrMJfYHuF1-uxeckwc`EfhW-7|Ylu-M3_zU~=t~0`lnUjPG7kq|gm{mFM6#F#DYR7W3(*a#_S%$W2{+^"
    "sc)$70L1YO@<ZVRaq(tZr;Aw1l;7Z)y+H3ep7e>?U6&n-PgeO_{1)una9r~l3ScqcPC%JE7dB9ai1WS4UJYPx1EaD2nOm}=>"
    "(EL)dBMPQgiit_#O7w5@$*fZj?{5bV;oRnBj{uM3Ar`MVNSu!aRL#okj&O3kDQA<xyc5Hd+jWxip?g6Z;%A$x*A{8FGan1tP"
    "tE~_>7C={|BRD1Z=jf(dmL*@18w7V+AP%yyXypba*@+Nvmg&P2>3{NWMWSrSq3vcZetac+Uubp`7UZzlHcXi|<9(^no2eQ>_"
    "~YW)IA-hjC}R+smg9`fd&_xsREY0q$#5cu?KmR1rrD!j=a?qGAL8*ajBb^vN2S8OKlueP_3ioinZ~BjoX+oAEmftiJ(vAOCb"
    "NE6HMXd|U6gY-U%#3%`0lJG!O0mB`j|2=o<%!P7Q<DFuS6E6uc=ovDh$C~%5nAzO7HU9rr3XysTm4aT?x1PCqvz*;+VsBUe8"
    "uyj|-^6a4PXjkc5wZF}Qx!v-WQ>N;wstKy8F5Ci(BI5UhoKRlPJMYMEDQvb;JzW)xo}+)<HAKINl+DPGqbCn&)3AK6}wTPVO"
    "YBMnsWK|!(B7wo>&Gboz4$NT7;Hmkfd9$+eJp4YCYX)05XBmQoA^F~OupnDp+HmEvKyQgpC%i#3Pw26d4+<(FdK{959xssu)"
    "9CYY7M$>GyhpF*Gd^%=Y^4OIdnk%=guLG)yZ8nEE0Y=BDMa(*tl8RoXzFQrAJ5-Pii`%y*PvWwL4GmgyOc?zNT-^+EfUkcV%"
    "VBC8JN=v4{Ds8E9Wv`=0!&jYU2w$p$Ef1P2ud=;pZ|t$gkxS`rOAbr1lOf2OC7^@PF$rDn?*H1y)IiYf)&^jC|U(~FBzUV=R"
    "o+wyq<JrVmbI@Q6H&=KsGjJ>)h`XYE1<hEPoPEbj&lYWK`3y?E6hr$bU5Tez%hOou=ZF1oq)#V6O>5aibn#0gUs!6hIM^UL="
    ">fO)(SDK&?reXk<M+5nZG(3Js!jEV-XazpURtg{JPNjq>v-VIN;f{(8#Jm`C}Z3f6XWkrV15-VsIlnHuw#Te9Ejdg&kR1(IZ"
    "qKt^?yo4iM#)HtN(4mG|R8|t?ahM}4p-b%8lQf#FsiT&S5TVisPj8X~K++HbK4dKR%$v7C<HVsV>xiCQ(2Z5}wop}u->Vpj1"
    "nCUcS&yQ?m?7oFvm}0+>-xSU{^ubMquM_{CQQP3t^39&D4VS;4mCs+*R{IbvDxjU#0otj8vQ=F4O^)CkW=CkOZ68HCPnnZUK"
    "DHtmt{9m8c&26|Z#Wi>&o;&p-7clvz80=uZ-rr5mqk}Fbg~7qGg>gO6oC$UsSou_Z-0pjc+dJDA50_4wp5ZJB1^0h&0lf#=>"
    "W~4<#mWivyHdXVwpRnr<{t{15cv-A6=^lah~lPVq$vB)3z9nQAudOWqRr+L5<d6^*i%`1_X_KEtKsaOu3Z53l&4DCLY=HX=&"
    "P{*T?XdHNmxaBgp7`(>g933tOOk91DGre7?-C-p5i|jLo2EHCr%z%ZczQCVCs57~?bW<@ur4Ny-$1_zOcY(9j+BKB1GIoAYF"
    "*QYd!Hc+cn?HkyE?TpN=N498e5pM5ge#$m!t0h@ic^NE^%sv^N2caz;sIqBrMC?YSX`9}soiPb^?1)*gBWFTvo2VqqpM9($Y"
    "#?5ZFoi9a#<2^M&MDePooqhC_%t(v#kF!WLeZ{HCtjs8^sfe@4=l2RXXHC3x%ZzV*Rci4pvas^Oi3TBNqhFEX*v83|GW|%#B"
    "4?db4zN;F6G_^x6td7x`nzF!aXk%&I3z#6FT*=I+a;Q80-4rFMQP=i&Pj$CwPMe1_J#d0F7Q`ky5C+jfT%}x^*b}@wtT>Tli"
    "&J|ynqxoni%Ed4`RHA#x0DEr}8Cm&od-|Vy^2}jM&?djriYCFw2TDk%(%59ru+QOzbhFjyU^#-gf4j7C`@ZLww3F8Qxz*R;n"
    "6M#8SAQSU2``BO&~fZ93O~E1P#Ekq~8=Gd1H@_F6>;aY(PgYg$mHE&#!|f;1DyPfTr#L&Z4j@Dz4GWN@0f0D?B1H?54XUia@"
    "DV50UxkxZKDUV3mm(^CL-R!AF4rO^sK#Xz)8!S3GuQR|uV*4V7mA`{nc=jYAj(z>)c-!EM5PRy*gaXHyzA~w*Y->S#q4ilbU"
    "pl&7nnLv1c`-KQU2U_)ZUko)OE*+O)Xui$U{=jG`+TyUGysH)UEKhcn{U9h2{L8Jo^-dx6?Ydz2M2=OE$?7p}4}ltuj{+^%m"
    "dIr>D20LiifT@ms8|-hIqssL<Kyc?F$%@s(@76p<bL#I^AUWcbV@me3a%`rMs1QxD@<W%L%c$`v<l6z2T#~${SXVS@G>*^@1"
    "a<nd7{gO3WM?^q5|i1_3;<XxP;KO-$uUxq^;8np8>)*_?=1Le7+aiYk6w?tX}~JTktxPAQ*k6m@%P~YZ2&lOnabkd!dyj#Oi"
    "W>t$do~yIfer^SF)lAWq+9Cw%EYtzk;xkQ4XK3$puS>9tslw;f~gJ0=H>C;)*JazXZn-<r?T5X=&|6t-!Z*FQoTPUvY`K7r5"
    "12<uc-Z(7tLOUOE^l@x)xbc`e6{Li`$w5zFD`#a-@vpwEG6wlkz_g!qURcaL3Opae9;)67#PyaQTVtnkop#HhbRyIuev=9e^"
    "T6GVqO%0`0d$R2Fg3KFOcS-c|lNvxi`qgJRL2po6d2FwQnLun|Z9Li*W}jYC*LHf>T)q3v3?hL?fltui?e}Qy{W4&~V!wp1O"
    "ff0uDWbWct$M%ABfzq2R=%)}VeqbvDs6EKBbM%C$yVZaE<DX?1nVL|(Z_1WZ;r@7GLKgZ?`)4g<LFn%8N|<@jo%r+l*{;<1?"
    "689qFo=6*)cn{JAE(;4IXYZU8BBTbnys)T|$MyS?pKU;gh^UC(R`3m)m^>M|QK{qRcw^$auci`WX`!VokDmzIdW)FdbhE^wb"
    "9NV$!}tQ_FeK_($=k?%rLPS>}E#w5bYC&CCCz^3PK=<ZR(j|M!^;-5Z$9!Ft(NOZe_PZdMP|FMxQP7+9#g2&%Bo3kLE<d?ae"
    "|A$N4|O{pU4DRK`B7FKh0=J+vP_^vDwb3*_L5f^m1y2<Mu^~b}n&j^I~I#Q!!oTw$XK_uL}sK$T4Ql_u&ZMvh6-)@^b;kv;m"
    "Ry8;05DedFy~TBajVH3iu^Se`kS9U%NWJA~qlkVlQP<tELS3gf38pl(?XW=RS{4V4W$lmI3I;M)+Nd@%s@!vb8{As9%N+-)i"
    "@x#1goVVxjW0naVDFvYpjbY=s$xc=US+_i_sz4WpkP>P>-U=&!ipsXRlPrVry=2M@x$ZV_3=FG(+Mp8FB&8csXDAMq1j(y@k"
    ";_z<gw#Jq)oL-iO^~DY7S<i5?XhVA)MEcs_dtjIB)4cwj;an8jOPn0%v=&LVgUqEAwk}4f;nzRfn&ePv#x6nLsoJ!=2dnyih"
    "5_RP)5;V<$c4RT`33EFDK;g_~roaz)MqtbxR@B$THu;m|yFA;oyy39#6PC$#=3YSYJGUBx7yIi#Fv3!$=?f+LfLp=!@5u5@9"
    "m!b0r~S4Ou=@`GA<GN;hq&7scZtF2DcFiP_~#p+%sZHNUN)S=2U2pl<A9H$}5U@0tT*7&;ZzQ3wQ@O8ih`1H`6FS8wBM%efy"
    "*iUK%h{B;Rb&vTl^ppzA4%oictPo4>P8_8*QyOv1RS#AKwokFf4%?+0iXlrvYbJM<H{O6HeBqubFBN_3^l>c$<MYYuWi4LVU"
    "$$?1Teurh09Tb0+8Hn*;3VMt9?9T1J)Gq~{O#=Z#SM6Sq+Y>lo5xDm$#UNa8xS0VhMyWi9xqu<pqUzDJ?C%H9^R+@g?e@o*J"
    ">i;w_2hV?P3xn-kTjIHcN`BDdAKn#O7e&s^_@UJ^2ut<j|cZZ+C%JI2&f`Q6o13O$95GjjcveEEwKgjX<BX5D!>~SZhX6;HI"
    "BgYsSm547_^{(e=K|`eyPQK=)HQ+vTKwms}YlttnEh3CWC_2=G}Bfn=&JeO^&Ljm>WkrrEd3EPiWdJRf*~A;yyy5@O)hN#@f"
    "DAR2HVuM_EbjOmU{4UN0$#4tSS35$<{b~l>ISc}eTe6iBFz59OvCqUT03L?jR^Y@baob2<*I%QMui^{oSOR&t+Wdg2F$&@i?"
    "vO}tL6Hd={QI8t%;{drr9zoTI9T~{DEr>HYovu07p2waH@QtkxNb06;<|kbRq)WQhlEdCv*7eiRPERJIG7(?|()=&hiy0{qc"
    "<taCoRVwDlF1s{OBH16HDrt!4b^~h3^XFi5QvepT^OMRe5Fh#saMu{08%nw+xjtaBqe5sw6&b?e33K{Y<9trb1exwn}(~KZA"
    "$L}$)2f%Ap*}q%kt%DUAGd>X{X}A+$=u!?Qh{nd-v%kfh`@~cx;N-82b5GQ*2k&@-zxDbXm=nC!d6O{?1#`-qj7<d=GHvz1a"
    "20V{jV*+8r0B9K%r(IF@rn=%8>qZA0>6l2**}JL$b4<ucN5#z0Nakd2WEk}QD0PzaQXY_0>-*(`Q<w&DM7y+e<EwFj19$IwB"
    "pf#|r!gP)FDOB_$N1`WLT#4~Zptb>8+68zd2JQJuoJ|daR9K^6<z*b4KGT%rVImzyfT%2SlQ|JYbxzOoc*E;KY=FRHn7_sSK"
    "+EW-&H56Ab#p;VL0M0%iDCF^pPkj=fxb`O9p**yJY0e<0pRtwg?W!_8trsy}0RHOLSK?KtoB{0Hhq=4%)#?5@sk77z|0r!_w"
    "vfi3&cjGDW#-?XbTm&AnI!-wIs6tv+dvR0-Ly}Z{+YBDpyUcT83&DeRR<KLe4rNiXs8gDmxEg<>N@{nKgLML!T%h57~7JaOz"
    "h(Ii(UZwEU1<USOVY`ZWqq$TZ+CQf>$cT@@p`H2C^AfFIy@#85V0H?_}TyGK^3<nM**xKx|1KnWe8AR-A;`noTj~F*;PBGte"
    "YEM!vH2IZw|a2^d(G4j?pCfXJ~CwiJ*XT!!wKTnw~z;)~Z`hfm#j9fknZ0648(*f%@DdqDb`S)OZE8NY!btm~|qzj(vzaK$g"
    "b7O0m|{oyqz-FO$=$vOC;567@!n-)}*G+}le2l0FcS#ugp`uq8NFu5yBLIDj^!PmV2Vt8R108k1>Hjh$lBV4l@fB(pBxKXZI"
    "*&=q-SQ10WH@^7OajhFrD**iGNta{A=q%j1Y1I5N<h(3ueg&RNZozaTKuK&)n*lm$0AT*+%m4yuc9xz|$xR&KS~gUeOhK0_W"
    "QkBWETHB9Wz#_4i6^1^sy6{AuEJeE`Vs#2lmCW?>kasxh1R|$7~4C9N&T5b&wnT8K>(-1#9#dO?_zbnh_QR_L1WKeV0;2jy#"
    "_a(r`+sfp2Vdj5xM#2P%m7h22<WI$Gl_-NB}@?)_h68bdm;vaTvjn`Q~zaXWF_0w7yA0GSAtvELgDxm@WdxL8Xw#{uUeel_&"
    "AN(Sv%?FKNt@DdQCi*jFy|yr5sWRmC<{o}1A<0&;0%vom1emj+M7Nr8*v%p9y*8LpfWj-mTx#G%wdOAsv$qnUso%h_b;^T1U"
    "WOgWd*M}+D1MVAN2@t-s}hwXR>!%+7Lka7UaH1(oMf&h}E;1)W7j&>9`oCxnlr{S)>yYR8AzlFPJr}g<X!FxdZ8EONRG?IPO"
    "x)bqxuYWyy&pZv-ycy*m--OcE9Z=KLy2plOurx<4OAt#*&^f)*JW&8Z?y;m9vjo6o14d_{rPryZjNxL=b`Y*uh8t_s_|X3C`"
    "WoW2cVW*ogI{!f;|&xY_tpaH?YSlRwZRk7IX(q*W(tlQqoH?e<g&9cqgigyB;7gLzmyv|X*QFj`ZqHGnsk%1SQ<J>_hwhuu{"
    "8o8hGPS^h3R??K_&~otrhEDeK~OXWr#;d@!>Ch5ud#ER^1*-zD}{b8xM^$Ws{yi0~S<Q1bpzaEAXnb&V|~u59NIaF}Gs}!if"
    "pkVFN8vudkv-4KXFcmF!C<Rm^hpl{7dDtz^&NiIVdpIWrU@UDKaDhXl-Ased+=v<!esyErSuhSgHURJ8`*u#sD`6vKg!dnd>"
    "6-TJuh<Uf|C`*(JAV%NkZuUqtj(F#Y+A~2S<wyH*>3bP*Q=^65NF<e~GwhXI14_>7NHx6J+pBcX{u>f5fpsyrW5@7aKq)TXA"
    "!-6AI0iq<QO!h=&oTdcY3?(HrNr{;(kYwQ#$>-_tTr!D3@(m=LK)RsEb{26*C;Z+{EWP|<%oRL*^1I)_S031`M`TK~OgrOXt"
    "S-waqUUDQs#WU1u3fsHObdYby!J}`_Bj^<-Mzr=x8Tuheu9>R(<n+4S?SO(<7Q=(L>B#~nUu3cizX~Ba(D)SlU`>UMlyNBRm"
    "t>?aDI-H0rV}!gPk5e_{crdBSsp<@;E1A0Dwr}sHx=uK6u(Cc+pIN%>ILLqdHtGMjR$xnwy>dn?3$@$8z2If8qU2azob41ds"
    "^<p6ku;etL$T)P+JJmo1{?`>5F#CQXH9=bnX@*SrGg?Zg9j--AE;@JDo=vovsO>ubl>k!fDI=s8&mC|7nZEd!tU{XfE5-#~o"
    "-X3P!`V{-3)bh$3#T2;3k^DG;Fl%y!j;=kF+Uz+nZ0{}?~KyI~?;eN)V+yGsrY?<&Q$pZ*sNs6;B(M)Hi>jX{*4G99|i>P(B"
    "Vz@1bn<s|w?V$s@Ii`Hgs+1_Sb>op42EpisZ;9KYa;}APc}8ah$U^AFmW7usTZxU4gZ8-!a*YN|-$ymB=>?1g)hsJ%WERDNU"
    "c~5gM9F!gXJ6=WaC0oJ?2pQO6dG`JCjl8KC}&xqKhH})o-r~gsX8JfgRr#)_3l=*ZCHoaP3v&S&h7X=U;3Jq(&%f9)z*rAGw"
    "h*3&poSBre(aSe<|L4<tuUCMHd6x_h9CSKgQI<ThJE7I!h+3HT293JwDb<t|?KJ1dHWLVoT%KwAr#cLI6PM&rzYi=aT+^jx_"
    "&Maat5(Bj>hbY)LmhH2M&}Tdn8`F=Gq>5NTXc&~Z=ZK6|w~HURke8NY<ieItm*hLDv8Gt!M*Zn@INW<vICl4gKO03g}%Ovjc"
    "jx<JXzoGgIk;-=FyqYznX?PNPZ7{b>H(oz~=A@V%Tcs9bpKCHduV&LLSfZ@G(@4tN<S3mHWPS><N14E7GrH|<8J7J(pm4+tt"
    "uH?JUJ0HJt{)Ol=9N@0IQQxu+<%vm1U?2|aC|DVUQ5|K};L2H`GhC$6QZm0h2>>+Dg`_CJSyUFFkAEEkkljcL5lApVG6m#jP"
    "0lC4GhCRtJmwq^L2D61QGgo`?7|K3b%Q3^?VsWGiH@P^0a9vqA%K^3ufz&B3v*@$t<uT7T1BAy0m!mGsq@!w`kEs_026i^1d"
    "uaI9_8!Y83~`sf?u)#4BhcOnUSva6anemA=fUs&g9K@OvF`GEgME>3wlpjgW`)$MaA>*;jexb-`u@dCT1XXvpC?_c#WZF<dl"
    "^w)yVGM`U)WZWd8aMZ^Y|f@k+q9fm?6K#NBse`r*g06fWFG12t8FZFn#&TaUbyAb`9{xn!V%G=D{|9_n!c0R1>g`A^>`0RUw"
    "tjWDHO4PrT0T*PJ$acdX0cIEIp+i%Ccyq*vpf-m%R-0OBSN^ZbbNxIsSjX2lIV_73WV|Z9+0hn>9oBbtIouzG)%qmYVN@f}W"
    "khf;zv!o48nk`_Nn2pNFAcJf+i=bB1H*OiYh~(xi<6^d6ksM5v<4BJ=lbxErO&d}8wbug$51;znzu}WtUypLy`0S*0tJNdhc"
    "Jkb%r==B8GILqRUjF5)UW<!PIvE%mMd|+gF}G_6+<G0ZX&?@K<gE-UQ5h{x5%r*vj_zC7aY+II$+0fyLfuM^|BRG3>%~d3@R"
    "xLDeJ;cS+;k69mi{v8%<w$j5OdtNG1OVaPe=CQ=GqkY0D2K3lc2l|Yy9chu%e}1p;1NXH*^>De%T$h^SF4)N-UeLqc;NFFhW"
    "$TNGmgari4-^BQrA6ntwYwGz%b*QUD30DfyH14$$p3bs)fytx#ze7%SM4L10-3!a%=Yxh|@WI?SAdl4aq<%U%lA+lTvyNAaO"
    "=e+73yp=MfW?drkyv0+|g=qa7nw?s{h97MYu*WJB%-@ASrYtJ|xxbJ@8-YqzA+Z{0d8k|}U*&v3eM<$z+<*&zH29aDblAIQ4"
    "kf|5=s=4rg@&JIclFS!rM5|}aga(}0LIycBTH3IuqZR+Q_kMgE0rqmeLv#qfz!Rkg0d*pP51sQ0^zI!+esUU!YkCo5E2V4Ib"
    "iH%)q9kc&X-|M=03hj)p3u#k<o}k1FiQ48Wj4B$1IWyD%d}99t8i>jUkpvt)}7Mpwt*SjgtvAOD_{3YV9g5L|Hwml?>~PO4_"
    "BHg(H+=1GsW|lp3u@_URCERdcpC_E7#$7uXs87@<rg0hq3?edm!DJ<9ZdQ3SdV`9dX{wAdHjxOH1!BCS%7A2>|Gn|74*bq){"
    "&!ji&4QVInY+0Dx}P6apF3({(X**}2RY5VRIB9EEtSUcpyp_v!lneMy5q9?x{lTGQUCqM(kTT+w9#(iQy*qZMa#^kP-M6`67"
    "s=FBWIlF|&>C9UZUGFi+^YO^#2l(HE)AAKpwF=X0Il2M};XP(KjNix@@@urLwR53D+hd7q;Y7M=}l5;hX5}%e<<d?5N$A*)z"
    "SH<|yPri@qCq{K&0HaXEt};8N(~+(3?p5a0G!Xgvcz*XUy&AtE9sZ@q(Zdg7*EQF|+_o3(fkGTL(3;P|uhx<>Fv~;`$}wuel"
    "!$NI{7+|68tLf2H2q&6*H4rIV4DcyV1E3v9ZDYn2N}B+v)!GzwZp^vAGuv$U)b=H=uo`jB9cA;maCk|M=yZa6?^eow+Aa~A>"
    "yE%ERbYJMrxVE2J&7Ol|}`gDMbPc834NJ-(dlOq;qXD46r#TeSTiLE)z&Ddd(X=iGuqkP;pF@Tmxup#p>5w0lfTDePR9AfBr"
    "Z=_Whse8#JlgY;Ehr-WfJUqsQw5l#C{O&x<d{Z(RN|pj3u`!ws0&z7<ALLloBMZ@y$~r75ZX`Z!)l<!??N*S*T6R#R6iC&#;"
    "x4gpE!zk;1M36wfyCEdt%LndiN79r<#q0v&rfvk;(!y3LcycGxZ=Uebi2M6OiuSImsYlW$@PF9!07=9Hw#B!eE743t#sAmw%"
    "%09fwNyPOz6muEOHD)0dV{zR_#x!;FKbe|g7#`{>L}(_9Az9E%!&wQ?9bSeeyQ9rTl}z-I?&*50r<4v@8PshX`Q?LXz3_aXv"
    "lE}c_J{byeRt^dQwkI8Y!;(6mIcs)4ZTa$+~`4_Rd#OgQe64ESK)$}TmsBi5q#@A*m27(DEa~NVFWJ<VM;Jcn)4ZQKa^Z&bS"
    "YUHP(EC9=YQePPtXIvG12gSNyS7QM{p$%%`PA|^B7**jo;dJyEOfS?d7n)QROv;Xc3+eM5z<II#pw0QU?M4@6yw7nsVXH%^)"
    "bxLK!}?8L8b55c)nG%SJ<XQw(qZM3Tt%;tYU8FJucrfM%0GeK9lA$hGY5EK04GQGpGa8ep3kj(seB$+_sg^3}k`lX2j-+wlA"
    "U@c(en*qqJ==<Z*NEyD+RE)!OFcc|&{DV=J(!Ex|cul-e=)xQiF8OP|&H=}lN4~nwpw<2ASAIO2IY<=v>4Vf$=l2qg7@hit|"
    "((ErGiwQM<tV?3DeAIGX)O_g~VC!8SIksyibj`8X-;dD{*pC=rJ-7vr>D?Fu`{!@th>q_P9ce<_1K`T+Qk>N{fPAThLg>S&l"
    "u&Rigw+yU9ZU}38IDftuSNmtcG?j=lGNukh?hQZ^LnF8c+6yEt-i)6DQimtc~WOxPt*R5j&>|P{dC~ejktd27W~~ezJdK|Sx"
    "&a44U^?6W|Yr!_BhsR7^=l|^sav!fOnjBCf@y~*TY=70=V-|jNE)DYFl?AGdqWF&xP+xkU6=xiBxh=qeI4el9G&l#j_3o$a4"
    "g!A@8=p4<$QOa@HIK*#cDG0KPe~AAdiy2U`K7-LRGP8ko}q1BpoRWFT6k+lJ~4flC3rbJaOmGC7B0t%lI_;rlgYZ3A_`svG%"
    "*VZ4yOcG#KJYz&CBd7usu=xWX6;-wA?8YIJ>nxrBQI*qy-2QczEOotI#R<A(c1!n;lpRb?yqyO<A_|#8s#I$^dYhl8dTRl3S"
    "Eis`AG4ST~8}Oc&zZ$KT0O7-rVQ$+FU~U?5T!o>07-j@WfGM=*0{{yd0D5?m)=V#!l7OTbAPE4VIR;Z1Qh^D}bP!3+v2-A}q"
    ";a4LznI5ZYZlw>5MSE<7`6bqnWZuuWb&QZRUYB-N~HS&SW3FW$kYHS+4+q%o3O#~FgRUDu~b9Ym_>vJ0y$A-LPxC7P&L3wve"
    "2y9gc-@?faZ>Bay3b^&!i+E$pp|JNmHxkk+za+je?WOp%O=^m<D=J-GtnxjW}qT_|G3*gRk!1rkir+2KupMh<yQ$_YVIZ($^"
    "we#BaXpm3ZST<xUB}9S>pnhu5HT;2>I+fm|5Ek*h{}t&nLJahmZJN-v6Z0q?~N*P6wWYt50~zaYuDjP&(pE~>+`i%_wRQn3Y"
    "_i#9&C??K!R$f!$RXNZn~CkD}BdeR-4KUsYmUK$rr7?J(T25PlwScZb7XPe7Sl?4?h7pnQ4mib!gbcZxb0szehfpWP^Zs8V6"
    "2K48r3$29<oP@?>7`6pJl%3iLzMH{JX8~QOZ9wNQ{SvTYJ#PQ;b@;u%`#X%L^PKya_F?k@F07761Avmb%YS<5C3x%E7Xtf7F"
    "?aX<DDB=0t5HHu>W3{!&yQfJ5VbIbY36hQKnJOG2Fl_aGPUS<ZH{A#baYGCaq1f5q+hcH0do0vlo~#QY!=g!!P4D<Z*0F8cO"
    "=a#Q8Iy!Wdqo?cZk;=q9bTCpo%I90!V4V@AjRHzG?#lwga<PfnkOySH{pPZDef|<<OsBOzF~`bm5;A<urrNi$>U{K>#6-kmj"
    "F}9@Cl3?C>oMQ8tU>idAUaa1z4)e*EVxH{oCIy$!Qc;giW?UzOzm$D<{Hl3M>OH*CaJm%SXPzW7XFW)w5u{~ktfz7K_pkBk9"
    "iVIZqy&`|?ndS4{h6+M$8mXeiZjAb(BGAV(4HUR*+caq69a(q{%fuP+2%WcKXKo|aXXbZkt9g~SNyw(ss0iGO0hgs9pt!Br@"
    "aSDJ>Y`h!;`^RC=O~G>vl!G~#w$dd4fy{E&DbSA(0O*rT*IK4M0@4M4bAM(&10Wrvmc+7wP%e&XS%4n%WB`8LK-OtNH3(30O"
    "_VY={I)#SUvU}COJ0J#yZ7MJpZ`3*_t;j*tyx&~uxGZxbNe{a=Rp|_K!R3(_og@EqJibW)?FC6=K)yLvnV<)s<jGgaS0h2Ln"
    "$}%aR>tr!ui&f3mGVjdsrlYmS9(U+)6V{-5@aev&>rd%na&r2smx1^>tu(-o&*N`*8Kdu#EE4yZ*gBZP+q4!()=@DGcOt%CA"
    "=SIJFFbOY<FgdCzjJsD$XAtD_M3deL6fQ_Uq9y>Qk_$WG4CX8)O_Y2f0H>dB1t<^-FDs-VTmA&6q#Q^0UN1c77}SnzuK(DC9"
    "kfOV^I!;Y=^z_-4Rod7Db6I^V;$Xtn|I*)Oy`a9I*@RU9lB_Q>V%P+%~XTKP&E7t?}-h=U<UWf9512Dr7d1*9RuE35%6b(-|"
    "m5pRPrER2BVNAGzq01d5Kqbeaw3|KBQoni3E?)2-&Pwl^BybhF1(cKnucHqSSONZe=sw)a^$pRJ;td(m6IchR-|_nJwza3i*"
    "}WHTt&GSH&<Ja=O$#at<^upCG9RC!CZm{y&fH8-xaQ(1{jB-N>I<2Xj9p6}8|%hTVOY~2b@f6kLfy8YI*Qnj5N)TOisirg7Q"
    "nLc<8OWqfBfaI=$cLWa{Vh;VCTLeOhv5QJeC{%$*#;GfKR>q_pwe{n7-?7MEeiGnJdApHxR|L!)L;F96c*p#*xX*lcY}8BR@"
    "TU7Yb35-TvgyawE35DPXd6NHPQDc!ew&OdFZjZj6`)?rT)=rK#;wcd5Jk&+r;U^sKc3N@}e)0eEfeAWk*1SZ=wfPfno4u@D5"
    "M`91!msy{tzb?r`ao-ULG9KM{2bx_-n0)3g1nd~|fEmX+Jb<Ocm>uH5K(1-4G&c;JyqxjrCx8r*|cO%q&0ow6sX`1(t$FN>N"
    "Nk5sBiWz+1w|)m3H=PDFB1GT(4tCsp8*=3mT5TJlolKl?<v0r@!z|J@{*ombn+E(e)lmlk=I@1?{binA06?x(a`4HhS~JszQ"
    "oe|(wsw4c=WX~NBI#ejW0UAf@B|@BwIQcwkaUXOc=CER`p{!I0l;6Ja28%%H(~EPh>R2K)V5k&hv#@uVRHvRarnjT@c4GKd%"
    "ASRO%kiq0D$h^oTO7rHbJ1rsKvVJpl4Xf$SA?Ekv^x5IW$mrJop`LC>K1O@~(FRD_3CXk%#fIuYVKYdGG-}B|vWCMgnF79E<"
    "uLSM>xw&dGJ)Z{PY3<R>Q3c=Rz;c5DNxlW4U(Y08g!(12w*I_=VrLS&5`vbKkEP==E(4CG_UUZT`z#)ze(e|r0sWUxrDfTYG"
    ")r*6u)Ki5XRwSW=N#4gXmcXn>W{mG(VAEQR51^eq<AP_xUE85zXRja^n_~=Xn0aq?P0qX)A9W@_zeGW3cMrY=vqiUNL=BY0P"
    "^z{4ZA0g+x460RdWK^dtsp1&6^tG{oYFLA7c?dEYw5(o<+}UU2U>M<B4?Tp>-gAo%@D1@E@|d;MhB89nJ+HV7@451|aJ>w$Y"
    "ahnH`b|{#>_cl9qs6dbL?J4X%!{z}V}c++5XZ=SIYbS~G)qe#bx<l=lr3rL49O!&j@!pu2t_9olmbJJc?)@`9ksqC_@+OFPm"
    "Vk$BV`!?AbJW601)X;%o#O{Lr0NynNY1Ua29~ST6-RrO_yOzPa@|6)mjOrwb1=9>2<TXdwO#wvvj9zetaPSpg+fuy_-na`b!"
    "fhNsE)N%(_{QWD`g!fP79IA!|AaqAG0IFdY~5pa#>+VIruansL$SXvK!hE`=ez0jgE}&3}9bU%BySog^wZcV2rt9-CxufMdl"
    "H%Tk#r!aGks4R3w%MaYeeqrPJos=If?u9eW@nh5+Vd_-{MMl4qFL%_B&a=0OiL!Au(70fRXnwbEL$A{@Y6>&2FAh&Tgl*}db"
    "GMLMI*q68Po!wh-51?l)OVFuza48<!$Eg%V&zBXQEvhnE(w)}_q%6Q}#YF>y=&4pwY}Da40vKT<4dO|2+VuJoCu2IB*QTUIE"
    "l#gTx++^gPWq?I6cBlADE~>X8{2>is>rx`%)~(3+I7fnIu(t+UVP#Hd-0DqU8B$U*mW`DGt2B)(PKeb5l{s1(LZ<>UUu>(pj"
    "<=!rdu&|`#s3bmEn{t$Uz~ao4-adC9}*h;Ku<>2|U{-8jS|B`i^CB$SKm<BcYY#k~OE#94P>B=rG#kPtEK|JypN}YDNqv+XB"
    "z&z@9=De|F#=+$UrITH3LP*(pR%iU9zkC(#Zl84LLS)#u>iOe?$t`{0%)VXFolOTm|>HnK3%<CmH#n90t6GJXk%j9;?Si=Cv"
    "cC1+r|D|1-DyE!R9G6iH;r`c4nNq?3!W3v@1QHYvlp`6d6??tDh_?D}H75%v9&b#rUzxoI4sLtt#_yL~pN3~V`18UdskRfUR"
    "vIzLo%Pzqi&pjXhgAZf&-bWFQj>3_d%hK6f`TBTCcKA*Bl5TlOc}da@JcJKh763}-iAhprIzCLsg4xngB7m(71j>hl93m%=s"
    "J#OROat3og^%ugSnmYtsTH1s;ReSn5&bNz?(0$Y$yp$1K=$iT1n{;Mo3LWGhQYdmQ!DAQXbJ&b*GAc|z%?>(EEhrO>p*bin3"
    "!wKAtR02ED0)0agc<b<v+>mF?B;g-%PU8q)A{XuK}hD-?V|QZuFgZE-*NN+lKbxufOs?I`Ah=XlHqSIjXJd?@}|v6MEr)*_t"
    "Kz!0-Mp`j;&ScJ2jkzZau--w%Iy94&^4oMA(S!F*o{(Oj}0-UsRMMMiUT<dAa7=6#XQJWKACk_j{+vYw}d2@=eXOi4>H;l>7"
    "Hc@o!yYVAP1(283d6?|~$A>F59j>jU=Q(^#s=qU`sP$xs-Z_a)dmLC{F=j=4f<pXGOJTxL%Y+332<z%O2Apj812LO^8%~Ca;"
    "?6fum0E=VePwogGm*9bF=#N-V1|`$LK{G~X{aUPh%`1Ql&PTL!A3pH$PvGmDAJn@w2YJpPmDVj;u0{{;)oH*d+Q1*Z@>RHG<"
    "tmgO*@D{kT?qG&AR9?4uYpDsKyJ-k*M$*C6Uv3glg%-da$}~<P^bDvfv=CtEHbcVu@EcNm9OhFB{<MfAqvGVR2&x*P6h`p3*"
    "R~Tu-^3_fi1l#cpV}7IqL`1dH|Ori%WY}VbCy<uUDWdbC?UK(BkFw!bukPlFA=N5hN$bF=bl1i7@t|%w+VZt#|*EZXa?zX_#"
    "?x{X(GAv|CIUfdZ!D5N2Bk2G2Mh=E)l{8u<9vAAS#C+qp{z0;hO=IqIzK=uv*XghsU{8y@(BD_@S^di@)KdL6ibvz{a~`S3R"
    "61BDJLdu#+cpp;~m96440>5J#50wmX^<OpmwL5>mVuOoA64BJK(lF1gqgN$Fc;1$|Y?drfoPK*z4zgL%_aifFi>EVqV(NpM1"
    "XW#zT(i8BGmSxE8+=VclgJp(@Bvnl=TJ!U47ZzK(!Ofx!faWf~-eFB6-3t-&XBPl4bZNGN5lLE|jaf6sR2ZRq`3m%$e>QN{s"
    "{zNt*Z%8^`1>z@MQSz?I|fFB#c_H%8jeBPnR%&~$Dh67O&H8LDDT{fnTH;MIX$O$WAdh>ckCKrfSRRXI4)Ea!HG;{V^iNU=>"
    "S0boYFrzkZOI?f*Z>bCd2$>E`a>!LRqG63^oS?mDU3GWnJ8FM)=yEotOsn+bFLgM86PSrm6CAEREV^bS-|lcLiR80=ni(hyu"
    "M-f@#GlH_EVN_g*O!kktWz>8PrwfJAmO(lZ;$>qBx4(*XcOAuwZDMx=LR%_xQ;>E5=BQV_z*716R{8QRWy5$3WUzPtHB{L4+"
    "(%h)vr0gfVPpKyZOvvn)FC9v$~@xed;6RbOVBQQCQ$~V7<navNwn3zV?XrN%*@Dvd1=EnvyP6my@f7V~SS(qZ%q=uCQ05W0n"
    "ehDc{FB+L)QI~#8hNnj&Hv;J?U?F38P?n3xD`J0l0iPP*imNLnz;!SkC`>B`rHP&j7Xd_1VMR-;s+DH33czPixfH$oMvw`rK"
    ")sxd@r#oNOp9yTk`A{qj5N2und0AEb~n@Io>KroE|ij{X}h{XpdN^m%_EE=1b(P*%*v;&!p7fuJJ2_Xz4zUZKltZ=!~??<s7"
    "lkrt`2OQnBr@|3)qT|c2%94);lwobavq%-}n|}W@a(@&;zIr9fUnoLC#1T_sI^QB~6t~6AcS`G@ohOuwxUs$j~#Bn_ZWi*#I"
    "@!;WJERbZ|<JN~sA>(t+!?je5QXbFF#ou?+n8u19b$fJrX=iCz%a^mnT9;Yr9O5E%pd5&*C3T#u!mjc9rTM!f{n4B%xw1l2l"
    ">IE0716#k%*&Zm_felM2&f9W6~*Cpu#5JOq=no`$w-f=9Q0b;mL0bwkS;6sE~261;gR$hEQFwl>0ZoVHM_{k43XIW_2E`}O1"
    "l$KtIx}A*5n<naws!sWT=eZZ)_uqIGjA9XZ-~sHr?ndC?D7@KOv{+V>Dds2HATk130svto4J7fL0{}_JNfH3?(jJz+C7G29o"
    "@pQm16ZboFiv^_xK>7&todFBVRt`niRSRWgO5VG&de$pML-qIRt&|nJpPED1Wyp6r=iO+RcjFA<uVoEyjLT?V;>Buxwa!H70"
    "!2IZk|+0Pk@C*d%UQwU;kMaS?ZYu0Ggw577uokC7U6m0?inqG~m%qpA>A{hVn9)w1Cl^jnn?%cY%#3VrF(0fA{In;Od+1WJ$"
    "ma+^WttRi2#Djlcfjlo#Q5F1QrN{sS1f>rP~<RYbG1dYqpv<GT#N52c}>f@`=?GJiRi?UZExlA&bZq&dbfISyryByueHp^OD"
    "o@Z`o$c6egIv-7BTv|?vl9zQy;6W5k!b$5RmF<I>I#UsO`ymk=1KrC;|tNKhuzg8>-@P|uJ#Oiv8-Y7scGXbbNa;}GlFSXPL"
    "oLn2KHQ8A;b<j{2bW*k^d%Mas;KVVUG!&o*gBk`xm0W|QiJNU^;O26et5;$7bffD<ry^J~fcvMX@xQ+E1?j*JKbys9jX{7H5"
    "?LI}&s7xCW93h;dOcqCl1pJ&F7WMZF?Q#DFlT4s1U_8b&|Usz<gp%KY?{(tQePutU8n#2Tn3WxQ}eo%mQNah6-BTu3vra(Ax"
    "STaSjttDjYdZYwih$_?4Ad34Pwl7*qE70cK(a7)f`LHh@KR0;)tF>&1D~eKiO~wF08od9G?RGIhayQDFJ|V=${_(r*EnjPOx"
    "U}b+ZXuv+2#kRDfp_05El9CqMR4vlUE7!IKoZC`rqc3#l?)j9I{e)(lR&@=D}i`AQ&P!1uoVC4BgEpU3VfhCDjoTEx!TIldm"
    "eK=kJ`Dz4P^4gLErehJ>Z_GH+@qnNt?egqSv@ES69DbS7iB#mG8Vr-q}E1mtN*MyAhvmllH^9?8E21?&##d^mjGGmygsiy(R"
    "_^(L%RJbmJY#tLZumdr^Jhe~yM(7**NE(90lH$wq5uz8Gb%RUQwtWYTRe)Ln;HuW8ILY&{N`k?|!^o--xm+Hz)v|6CXgdz9F"
    "qzAq?8F*qq%RfHvqsXdWwEG71xl8YG@Xr-MOvVHg9IqpS<Hq$GRu~t?ZkC3mJMQusql`^d{Q@K8{s|X3(AS@?W!_8jTQiB4h"
    "-Nge(hJW`qWc^$w_Sc!dFn(J%-Hq6pG0nKYU0~*??&z(;{TyFZVJ!N6fNx*4eYwYy_yA)u#7DbqO$;$>Luau{5HTuM@&Ca!{"
    "6oTBzU^TTvb8!S{j^KDu)=_OkIG(KE&yexj$L)i6|h&O^0Q#~^^Oo^vHK4{k$iSVbnRBUX}(FBh&f?f-EB05hF`n_TGZ`0$h"
    "O$pZiqTsZW^ZFX)p^d-7#$w0vX1!*{_<k1mA6R4Vi)6$0F$yqopo#<S>7VWQnHE_w<n0oXf{Gb2(G2FCgo7||edCm(+8=(3D"
    "eDI=6@XKpAAlk7L6AwR(XmS#r*$n(@ML*6kT{L28`Denh<aXVJib8$!E;}~Cq9aFV3+S*xj2TaIe--kz0IqJpltG-$!!H!E%"
    ">lkSa{xcBlu%1|{X4q)v1MYI*9)Q-uodk+sxdu-jC4;&j12(Zy5<y|6WG9By)Q30|ER|`n68X)lQEwrJbgWCHmF?~7Z@sEx("
    "4Xy_NAwQUii6)B<oB{j%2Z>WT|K%EELdw%1J1keI|C)>v-qCd{hSkq)^Vyw4feFm<%g?4fzG?PAAB`_56$Qp0~X%nelq#O&G"
    "cJK~(o0gfTaZfkHd{@)WYV5X{gci5qESW7lwWrkHeu^i|Rb@Y$9DBpV{Kn-ASvK-AOw7JdB5y_Aw*lm(>%WQ-Qn3>yvCf!*7"
    "Ud*S2H_dbMS0NIXqY@3?qu|@O@@Pr|HhE@RTk2}`k)x~}kMh~K;A+?phUTQ@~l-B)AhkkX)cpKUMmtSSqUrz-%WZD1h0|2Jw"
    "U=|HM`mJDFhy!1bZL=I#H`giG>*&jLp;`}6g^7AsEAkhej-EHY9vH9SdpF&PzxkgpNB{tl35+Kbc<2|P%e9p2N4n<!BUil<R"
    "}_1o9(fF7k3NEUR&MN()a6<^1d%M|O<l7uKQi5iLTV&o>4koXKxYQ%uF7cuK#mv*7?r%_N8Hko+d31-cc9YIfz727zBRKOKL"
    "zCGoyP&uQ5>}HPzomiczfqsoY&TYaQFZ`zY1Gk9m0kl_bKH<ay^p8o;0g%rujE71Fr2Lmd7Gar-VfCRSefndIQKc$c=zNPYD"
    "4!PT7d=b6<>UFN?qa{O9r0{d=S_ATq@^?3$b5Ys$~rvX&M#S1Rc~5i&*QlkfXuoHux)4hT)(dnfAq_o1?FFS^|v@}7%&xui="
    "#JljSf_Y%?&(zaljHmpbip=5^0HAXVbB*gqw*^5Uei~K<Mn}H5M$#EwcYZ3rxjz^XZ1J86}#0GL!5v53>(O$$vcM+f2b`QRb"
    "2)lTlB6?O9j}|AQr$KIxzA?28yYeQ&wpN6O1ydT+7!GXHK^TWHEK}D^Hs`7*^=%8Mo1|zbP1hDkik-Y2iE-F}3BBw?6#2-+3"
    "R!v9KptzuF>^2@8(tk);<f|zWOj7BW5b!8MD@lyF#T`;1>`Ke^3VPN|M+|F!iB9Z=#6zpX?5{Q>s6;^sn+K{=ZBuAZp%`pAL"
    ")+XAG+cdxMKMUh_^h3i7k&HoEn2?NZ0-lk>MaP<i=h0?q#VjN09^q<fcql?4pJkzG1+Zy*W#c*#<00+m#vNmV=f?jLy)NTX$"
    "H+Zj2WTxFf9MUuJgWM!nl-U|F_<KYOC1)T~lQ1qQYP_=m~u_~`IfjC8a?6+00`wjTSLj}2s$iJA>esw(V^14mN5QHL#K*<|q"
    "-$<DvLwm1l70SHqDhQjcbP6-#0ilF=&TB8VaTOPykO*f)_b_Rcc<?HeG6E^99W^GQoh|tf|*&ElZs8qrl0Ka$I>A2~O|AzC<"
    "I|mpZ!pzk_!rZO*z}P*EcH05M06{5P{3{iq8a7b1488c*rDai)?O__WzVndMGkrH=9Qp0((Dy&eOsCT%pC{8OY?Zua?F{O%4"
    "@0{CJ1(+D7Iv-`k49D8sdFB=gduvi7>y-*hI#=dHFQ_z`|<9T8&TMO07Yq#R4pOWNz>9n8L(^v%1^4?WanS+#Y!I?8M~C02u"
    "SK={4A#cG)oMcnFMLx!9x9<l0ZWY+i(yn*)29;WjvJpx^55`c6VY|djaRY`B#C<UkdEsgFpG;`|-nvwxXV91DLXFGs9h*pS5"
    "nsRnl}x7XKf4{Tpz}zzWoFxgB%6cfg+>(<zdk=b;fQL^9G(njuN5zZ_R`^PQ$r$}XOs-fc?bE*ayc5QTMgI5}8`g(<%R3l7?"
    "xHq1r=jQ(D1saNo5*ud9kNAO6R^55ImkL@!|`6oKsEiV++TzO8vw#bx#H};=^!9XE9JFBPJWNZ)PsKLp(2<D_d+=ZvF8OaoO"
    "xt`d~Ot$p;BG)k0yhi8?nXiM|v1MXTMKC+s(Xnz3TGniU>g>d)?ztJCy5n};OQf~81A9g}edcFrX)dRXMjb&EV;O)Cy!y3x*"
    ")P8aC|GFRaw|r@bsapJ9uZ2vm=LjP=<A0YCwU)I&?r0cq5N=717<AEB9lO~spPTgz(~DQ|M+{8W<%tsECJ8~Z0J#w@{H2_Pc"
    "$1S2Qmr3mB|w_1;9bBr3VK)@_66w8*vAKieX_wH9IR2(KEplhv*sVw;UBkfgZc`cN;Fi#)biRbOMDigsmEY5n#GL1J7|`q;q"
    "YP0DytmP|sTcKqSfENou#;oP|bmL6zvayk8cCaw+!F&=+;Mc2c6y2z2zk>J>1Z_pth<7a{Z3tK<{$&2M}SfBUchrKbe!=4-^"
    "y#Zo|Z0QjF@|1F%D$z$^78!@@<G2~PLQ-#Rbu1@v$16kC2uuNB%07!Etoe3hHk(=`*(iz^$NO}Qeq>FN+1{V%Y>HX|_s3{ZG"
    "o(|mU1o+;b$FLc|v>wOg;$ZCax<GUcIdx!}njYG(tNEq#`@2@3hV}IrD`sm@<#DKthl*c;;~0n<RpbrnwyyjA>+6b4ty!Ef+"
    "PoU2xkrdqBb`2DpdKcP;YOhiW@jh*&pHP|UoZaap4;(Hx8H^_2{86|<B{QUzRvs%ylBNzHNNM7E*HC?yAyx;_TR?xGhYPkKY"
    ";10zlVv<kH8z7LBEp&q-n6u8EbAIq(5IH3H(HIA7L1}lu`e%RI-sV-!}3H0f48o_&+=VAm4*-h^*`WlY1IHo5FEX3uLF?Mz("
    "V)X51_u&ct~C?mMyH04mDFoZeO;qGyUH4$-ryt(5diS+t!E;IB@)6x|bZu*YPlwu)jVi+WVk4FM5EdT}OomU5YlOu4MZ@S<3"
    "!x+Rz2L%RVS*^xi4n+~Q^1>|{j#9kS2(+hUeq(^px6&k96z>eWqCUO!o2o!?YM#Xh-zymTHR$=WQyb~xEFgH4mKmEu*;5(1("
    "WGCmJk%2;14V7!gO2<$wfx;Kw{!W}UQ%Ci|hfp8hkDR5@sFxAT3?%t!N(b)PfMa+tOa~1~%}oOUNw0|{*b~XFzYYMzx=EMiN"
    "65j3iyZ2(5Vdt+$TRRjRK;f}_Uc_ZS^SUldO&o{THn{NhDL^w1F#ann>tqGJh&JPV>q=M!k`R^AKQ+Ba%~bV(sf-WyZ(VGO>"
    "AWsI9d8N_gtl!tquU_E181lNT>KncWn<%8`CmLpuZ2@8%{#Jayh=fb1Ob_-Ss+8uCSyRn-6lF=<{ibYe;uKv;ug~%P+%kzxF"
    "CU^#?cKfIYX}fneJ%bSn$_P{9fp_Z3Pe80lb-{Bb^oKgldx2>vXL>(fd5&3;GEaPhw|1wca73k!egLDAe2kvpY^d=1H7%d}%"
    "Elf{Ad0{&^+Ex230lg<w8o@6Eo(X+(>0MWBF080%b!f&rQ4HxIT(K0lOT%`=#uOcv$<~Xtw->jmSICYQ)0Gvot@0wNo$?p!="
    "9Q&7k_7Og=XAUN#bR+<<sL7xuwR-yIEveJ9Y#Xr^p%zMVe+*Z~zv*U#HX4%lS7^bsp-{?tIN`T`6FB_@pe2W|eC~_*$1i;q`"
    "{e7nK<~gZY~CZWcY3zkO{kphz>B5MGS*WiK6TYwus#5SM;-x2Mo^s|g=g3ZZ3)sS*visx64;SU5^3ZYBGgCDp>vcC9b}T9v6"
    "KLqwgoeck&7JUGVPc(92{)T;hU8qe6KX7NBjl0iLsEoC`8ALE<p9l4ly!#<KTL%9j&7$2;s*SR8WHLNxi=hTY`>Cp<ySlFU{"
    "#Sdb73}0MKPfNf1DHBrz0XnM5N~Xk<E0E{9qsgC(b)26u23uHNzx{@)!pV^UtF@*ehA8oZu7Ph<q7EdJm3=3l|<U-~jgq$T*"
    "u*D(6%Ryg%KjB*793I0ppAS<IMIf!O2fB91~<}dk?G_Nm7a9|-QkUTn_c(lkf2>>K)9ZZtZe{uwQQBt-jxhJxjVP<luhH|aT"
    "qO_zRU#X4aOC!5bf`Nk^M@#ga@P(J?Sz6XoRCZ}jrUKxvR-S|P4WPSHL1T6dj%^}Vfu5UeHWy~|9d0AoaT4uLm*>wq03fw{&"
    "HC@eLYk(m0}ZA3|C1~M+khWOx@KH%(&Xc|W$DjVkwO3qRolW`YXR*SpM{Q>UJCRs!S>s3$7g>0eSGu5hx9lgC+naRD~vTlzJ"
    "5GIJ)W%!mJPpJhb!eI06zTYtFW<d!rrqFvs<^qsa0V`K3vB|DUv?^HY_Cp8)^9`b-5DOQLro%u>@~)?SGPt+pN)*-4tD`>pF"
    "V;R$F@y_LZxsb@t*52k*zt0QLaLwY6g3%q)M7M8}!-GzcK00{^i0G_0tE=#aS~ei_sL1U%b;87mz~l>L1n(*l~WEy*=U0@^l"
    "UTKcs}t~SYp8VPs@s4AK4Zo|msVHApJS-KJ}r)<J^4sOR^Uh`wgI+BtAzWzLipW!L%PQaFJTlK&B8WZ^F|NbMKe)1+@wvM^a"
    "{Ws<w-UhQ)Lq^5O*p40(>=-6$fy@N*9v1+>5dr{7W`NwqH1{*i=V9@mG%S`o8!1`S8zVZSBu)YmhN+v~`c4+klI3{Bv+##oZ"
    "q?I@GKCK8Epzvu=(*qvFVS<H*S-Y6pDjHV7iZd$9~y#JEg_S0P^r%9ZpqC6fVAP0nYytN>83Xl07!z^a=AV1V*0q|`$rA{L{"
    "`$FSDs52^hpo+B-=okx}HwWKVNf-fW+`)%Ybi&`o=A9c`!{I<wgjZ)LhGE;4NE%{)^8~8U!9ZfKPw<i}?KQH=~@~v|;)B)wu"
    "JqoqP>>2Kp>hy7=id+zoaHpM2}v(J?-O@Zdp|ckP6l7(>Cfb#uRZAf5a3I^7?U9x|zay83opcK4lh7Pm6tNRy^R=1L?t;&Lq"
    "1^H~fPve@62$3Jg<6nmw4lFUxdcVbs%l0QG9<Is{!QI+a*($rQ5vER1jB%Iy=I%nsQQxPiROtP>yl5z2-9y6L0tO<ENlJKOw"
    "=9s3Jgqd}QfP4ay0Jvnrg-Mt@gag&tgWQ_cXgOsgzP|lY{KZeN#SY$wK5Hi}S)!&69z-{QD^5HK|NFhakB*Ku1mF7!_FVH*M"
    "0@sQWqT)TwTkZYpLa8;Rm;d)9vYD}D3WP13yXPuPa@*<ej$CoEbbSAK0-dncutFd{rqVU00|uFlF8(Yr}r{aI_bgh>coNG4t"
    ")6G+i@SDvk|9w%n&_iy!j(~4p#Q}Dt~ws>j8Z5q?h2NnFhS^F$Ag#ONDSkxnW9{-xAf9_G-#d^IdOsk>zs?07#Dkxj~a?eY1"
    "WpOfRN#6Xr?Hcsi;{ngTYTUzU@;tq`gR*;vLF2JmcIaN4N*5h{+2iHwczlQ*LKRlfvuw&M2t?!tdw`+eN7bHA?REL$d~Bc_i"
    "(9o?3p^0EBvfpfe2@$SoChO=S=<;|Nhwr3}tAV7zt+BSUD;ySWc0e&QHlDwqBBc!I^(v2G7*JYA7Ai)7WM>(0N+-%DwN0bx@"
    "M424M+p@UR_VI5A_R7p;3<JjM);_g!c7(70M1(#-odDpi#TB@q(1GI247{+8awNONkxtE)Uy~OM2{R|t-<4_Ti89KtU@2M58"
    "R^0;MxcECs+E->btEllP1H;eMsE+CWlK;z_e^|w?@qk`Ti?<pO=ix;fhrr2K9gW_9L2gB@p~?N8Gh}Z?~-sYc6|Q7QNHzFbd"
    "~Dpv@H15GGG~ck?xun<iAE(hihi_riA<)4Jl33rGv>Lzqz275wd#m-~98U+ma*zAmty=c3NyR&mf_i8In>8pl@GXM982zIDo"
    "6oGCsX$tKR)Las}+KmU-<WdX9J!5j{s8uv7*SP6zOrjaQ&!cogN@6jZH@qG7_0Wv8S$rcZWDk_Edg!lgN%POf{xi|7+H|7(T"
    "_<O-dh$nsPR`@e@Wk8slK{p9q5E47^RtJG~KkC&lNCK`r?X~%%IZUvV9`kR1LH(>t*_u`YE`43#bZI4U|U<&8cu(GpLg;SII"
    "2J0jM|MJ#%V`;g9*}Lz7F*$)oxePOo;2B0597=w|Nz%WWG>g<dB$7;zTsp2vkLj`ugi!+-*G0{5z=5kr{i%FA4z%R)lbKO`r"
    "9P%p{v*f1co6V)pNI~z3{WyM?h3mDuUobjEz?s#c?uab*6HI>P={k=bZ2;Z-H~fVX!yE;o8GaNo-*n6MXoJ!eUb&HXS+Zs;Y"
    "+#R*_btBxXXL7<lJ+CH7DW+k35XO{MwgwIe^{Tirup;NqREfo~!Z=UnlRMwX7W<c=tQ8;?x%d_dSfgU;j3$+xMb4S3{5E0f7"
    "Wzl7;pB<c4NP|M{K$_>jf@As2^5yZnnEvmm))XpSC!BF#@*e4mq)6UcQed5+jjvJz#&k{cVatrj5Pg>9WJc+c+JalhPa_4Hx"
    "a7z5Wt&j;QJ5<O2g0qVo6&c+#$jp_Y6(dAn3B#m1)+DR7dvQr{gOT9~y3<lISmd`W*faWu%0f6}v`YD3(<`X<~GIv)308&$~"
    "t2UGG)AKOas9`3XLA9fZ6JB}=a<6+05XbobSHFt?_22)aJIG5mK<~08*uMWDUsDb<*xI4O*=gjUbgJzKUiSvP$jo8#&bwhvP"
    "Qt8~bzcU(H)BdhhxBQXCXq=PAZg4b6CRRrToOFW>R^w7njY{Nppb1rxmH2W%fpXMgxLb7TU+tnp?$bEo{=<L**)RUhKP=6MO"
    "T;dCnh8t05aX?t?SN0*USvMRE*mAs18NSRYC%ckzpfJa_tIrW`LBM$+blqxHYdW@|x9<>;WUAU(=)*&T?$bhE<e31KEKAw65"
    "KVmKU9YuitY!{_&b0==5&8y&Zd}r}<iSm<?-}tKsc?rR)%S0Kb0D+4$4ndk5fJz)x?*!$0^bvLmxt>g1qGCAjl-{jqMeCvVB"
    "Lm}a@4ZWa3+&xWTT066>}C(R##4<ELX0UQe@U#?+UxPgV5lYzfv1^#DvFFsn^FWGB6CWxL#JfVo5Co9sifPZ=NOR!{Y3c0xw"
    "BEJGlZhqosYQ8M$lEt-7`+v#|fTtP*Xg=!zK=VC%3UE5lSNA4JUl?S!xnju}o(x<oi|JAYalU}|Q#YXSD^~z#oQj8TxefpP#"
    "V_N!hqvgu^20~Tb(%Rf8CQ?%*O^sbLAi}GIsttAb#KNx!@%r)4<HyChTRBYs|b#61!+LqD$0#@It4i$<0#`Jlba~r>p>o?7V"
    "2<K!$wU-aNP{-$VMrj$ASKKe0uA>xF`9U=+9-dEh2g{C-?TNxzS-1)8>GGG<Yi7hQ_cwpGRYMG7U+_P%;)!XCXz0T%RHdX6s"
    "e}QU)MnOD$Luq>iP0K*2E`J-wt7*HJfZWCoUE@T{|eB};Mbp6&SKtG}Tqld#77@p=Iz!I@1hMZD{`-hp#2x)2yTi15eP;-MR"
    "ELB1NG$8?ctM2O-Va;Aq+Mlu?UGW(PXGc6YshYs=k`3C^xy5}Q+X*dWh1Ld%eLZ*ORoI$C*9XIBIf7-QKm#*#SdWGnDbzI+="
    "6Fr~$(+l*wmT$l-;#PD|&7$GY!HOGj^$k#rSjjC@5(JPMx@39xiw*$D&T=w_$JPOWq=B4o0(IAb<9KM4O30&t*s^dSYM{2d7"
    "aM=&)xb+G0~{Nl{nwA<qu>0FzImGljFVQbQjhH3b=<$c47eHP`E{%Y@V77j6`WCM!Nk3H!{56Pd1<O8O_<V=kU}bDWyeN0YD"
    "`BuHUj{dAH!v&r5k{4S_oy1x1B*n8BoP`O!Rf&{abFs=Hy0N|2&@J;36W@2HRRxd8Q<z0&%`%0`zUdV6}m+AVgFz!!QE)aV>"
    "pSNnWGmx02$o7n_Eucbj!{ImsoHprtgGOZ(nflEowqXc40%fz4tYR-bnPuzDrF`q*ZC;0NE;BLYYGx;1Z^Whys{@w?}|7=QS"
    "yzY6sA0}pP-!EaxU#-4+){Q#X_7Di1n4g=lgUxNCf&eB-i6gUY0IEQri|JeorbeX{s-mi}ZJtM+~bhN3<cj8GiNe5Z44HJEx"
    "c<;7bafcoW=-^<?(lw&z6K@QOo+l@_b*Yh=39OX4?yJtnx;Y<lc@lP1fgOdqDWIg+OFeg}JMS9$=1AAVspd|~&o=<D(9<~?!"
    ";_@t$?qjJ5u=1Ua&`_;q;&6sdK3e$jk1c+$Y*tf!2GXY1*~0y8?N~=KJ+jDjz`KBN##85Ut4-yPdR=Ag8=^ioXc^+;7W|$c`"
    "MwxS@_dKC>lBVFcBzO_$NO&U3!s@ceD%xb~>jy>9(CTdDOMFb~64k2m-X{+F(`zzoQ3_bY$?69e3%Sf2RBs(X-X>*vbn+oC@"
    "IG9UE~{sL%-?mAMfFC?k`}p&rO}$%LEEZ%>NafItUKon>2_UDvIHJG8jFyA`(<cPZ{pad!z)+}+*X-QB&oI}|AHki6W_{<8l"
    "-k~!9#W1Ms4$`Ode={PGko|I~wV#hftc8J3dFMR2+4oh<Gxmb{VDZpB>&z-mf4d}Rq#zs~f8jMXyn;NrWE!}%S$Nwu&6#t|9"
    "70crs{G^_z0#VZg`&QeDu<Zhqy_WT_UdeK5ATc-C@?5;Nwn(}v9@b=m`1>bsXMT`PbG&K60x}2)6fpsFT7Zzk-W7auo_0v95"
    "~M<Fz)EV#b-?(4|9pxrCX6w9iNr8JJ3%kf4MXHH`S+(%R*qN;I~+&Zsky&Xd-8~slQZSkquJ&R3m?FcSzD9K8j^}gZ`)!GHL"
    "wnH(rK>}KAvg=0g-obL{(E_c&4zv3C?=w(Yg<>6ygDw1Uw5K3hlYmQ?)g0;1zl0$(m(!&42=c_6sH*q<e_cp+wWx8j;l7q51"
    "9lf}qaoFJ;NAH}mjd3F%PgJ3-^X@wg(fq>`P#nS31Si5Cn|Ot#%&(a3J;)I#j9r2k;*5^FET?gcba%Qzsq3h%_KLVx6|2V!V"
    "^eOCKz&h9!C4v>6;kn-AqUT7SO>!B*iF*WX&7-=#5?etx$Veh_pqJ<4-`Kvdvb}CAN?-D+4X>Q=`jynNp_S=fFI(1f4v(e5}"
    "lw+5^=*+)=gFE2u&brt4JOAofqr>x^A1+Vkn8y>pn(yETy!h5NO1QMI3nkX|S=x7LsPIO9K=p}3_y?o-8>j+EnZ9#UQHY_26"
    "8^O%T3uNW1g`t>*O*Yl&(BUd3%-S)vMzkNf=e49GRJyYCYPgu5~bOq>Lj=FI}z3|i<Px#o9!)D_HLJ#@v|p>eEj3;t{8f;&S"
    "<y!r%vvVEd~mIyJzG*vW4u5_e5LiYQoISS7WUF=?QY2<++~~d)rSy_+&*8jUj=@6G=B*E^x=Yo?T{wJf;=O)U~FpC`26})NQ"
    "c@tE>A<TtF~lZ+?rl5VoMLrt|(hxR(&C<RWlPK0PULjNQNsQfjeEiW_8|cAImbt2_c2_>GfsO-`UtgCbfJ?A@XFesmhNTHwA"
    "E7M4R|UN1Up06rgQYO7}p($>JC4}rpM*tsBNC+KM}O6n`lX6Cfj`-@Gs90@*-Q^B(!KR7+aniJ`7U~4iVFqeER==mV)0!=Mm"
    "A4k)in!9swaEzLD1G)WM4O}34K;^L}50(}H;V$At@U0fKa5u`#Ca1Q}#{I(&P$Lme2va|{0n5jhjk<7bKGXzkm1f2$Gvo3@^"
    "GDruP;M(FG$jTV=3l40HdLF%VEfMJvr|940k_R9fiE9~MDEIJ1-Z@5!^BHz1dH-XpuMJ4W5ZvBYiD$(@32XDWHH4HI{kHWWl"
    "cO+j)H)Nd4an-cQk_0#$RQ#jWd8>C2usd)cjnZlW6yavE6cR_$0q4J(0HivOUdOb+?Txi#7T}hZ_GoV8goKWu*W9R^P_!!#b"
    "dG7J{D2=Xo-BG_>bcPpV<?)G-dFu4t}2DQYHg;5?<a&mhMQLYtb}!C|%#{=_`4@_B3sU8Vj@nN;jzg0k%Rtb8DolXcZ@-*P}"
    "s#MiS|dFgtr`YFd0xd8YwK4$Y*ZwKKYK5jcE9m*<a@X@&8VL6qbYY^nFs~ZFJKRl6oU5E-Qo`p%Vt6Q2#FsGt4TmuvWd#3bo"
    "J9NB!c0>**TGT=;K?80ylvu)=>R3UW7w_f~!`B-902Vt>Tp&1z<Xq0b-Q?ZXR@_@zUUBveHtP2A3V5TR<-8r-*RL%1e#(cu<"
    "3->lQ95UW&&n9=RhSQsrs7xpM~7b#fL#mYr?estM%Pq7V-6_#m~<^_Z)XKQ#hH@|eQhWHU}Ohm=s^@oiqTGklhF9zz>V(2yU"
    "F@X?S5dd3@<$S+DDH~hL(OVLjs$+=zd(etKVPH;Sng?5#kQ1ainMiexsv%Aqcv#4r6lLY`#U6YD9YpU)sM3S%XicGK6x3GCu"
    "Ih&Q4vTAGgnStbHp*YVs4C@p7MRdkkVf8aYsGsuiYAcRKqWn$q-*tXOeTA*@GUtFRfHiH9{vKv4EV9|G$U;!X)K@WX$pmlei"
    "%SwuCXt*Ch)Q0iM&mPQ^lzmXYgpel4Ll1Q%LoKEXxog6i07QsQk2!BM`#I~tde}Rd}%BG4*%uph|%f+x2JAqZx9)Lfumv@Qv"
    "jcnh5+goSwd;)vooEW&Ef}cph!S5b<TvOMgS<tu1>-LQnrg1bRz`(^H;w^+f>0tRhaOR5$hdt66hal7oTw10ogTc48g^b`Ir"
    "Z$P^=&&k;mWdB{&;cIQk@4y=R?Zw~=8PcUX?m|>FN*U8gLoZ0WZ1#{;qfDnF5MEs=!9rKp4zz~#*KV71=>{VuzjUim?V)!SG"
    "@ueOoL!1ZyDR(`NtA2uOv&W?-mE^%x(#%AIiyCdx;x$u;{Sd$aPKK(y>%Y8`0BqKG$6~K@r2}W-dS2!Cl7-NH2@rJps$ScSa"
    "8q2?if2yEWdY_#`w}=4F&$^)>t5^(qk7<&+D2LkW+RM%W{I<Ekacmq$UC^#;YZCbwJ@!ySmqQ^2R&mVY)ot@hsyNBazXg6?0"
    ";QxO2<5Oj<i1?U>%FIxM$0iYB@?pl2+*tm`a+dt4?*g>PgCIBvSXu#Jbwf^H})1<dT1XT-~iOGc393kYR1{66}>X^UYEO6hp"
    "WbJ4u-MqfcQDuhvXs$L3L2U__QSRfw8PQR>JglTN+z=_g!Hiwvqn}DaZboOWy%y#+ycB|AdqG601~0ljZ#S{GRf#zByn~gmE"
    "!c3?A<OEUU6W9S2UVyOHkfy#J{-{~wyX3|6T^-IGE3-ERN@IK&l=5)lvG)yiH(#&7_zRxnCo7=)PaaO*))mvW_fgz>#(U{{X"
    "1HM0EC_Vjn8s|_E_tybz1_fXbx7NuX<cJiIVZG><m|(!}Lg2rj2>=1kWS_Rgc!zcjXm($rivYp1`vwg<=H+Z6aOSTP5s$mh*"
    "Pc+h`(Wv9G>HV;X*UCR+r|jG4`bBbP*_Zf<n+R1HSyTG9i(J-23EPkL7cSfPJgdt_%%dZlJB-4loi^XS4HicnajP4gffo8Au"
    "lObvic&x+FB_<u_V8{8H3{7%a?82_GhIA0sQrRVq`gyAH_I{92Yx-CB=^s1U@&;7gj!aHQhO2{nNGG@plH#KgWlyp`N=<!%j"
    "W+X_<<J*kQPP!pf9>z$Z-S&m)V+NMLoh)_sG6A#$TFr#&OhFhIt1>}v<JM#TIj=VU<tK65z>jun9(B2*LkBpmwV`_2Q8sZ|w"
    "s_}y3-|hK-qikcyFk)iYl9DFlIMZcQ*2itY^|`Y#k5LskI;I6wX^)@YQ2B3iP}24xMP<j3GgnRamkAJGT0SktM_aqB8p15+2"
    "y5#hr)tgK1v-5e-rk7tZ;R`FQ{>MC)X!SO$Gma6?ydGyCQ5*zk|o=fJXLov|Lo|LYCNOn)N=+9nRu6RWf1a5&0j~18h}QidE"
    "!YA`+7&=Jp9!waac8j%W@<xl(jLx?R?G&1t7HCm%zQdm~4l7ZPLZh|0?v&a~@(hqhE@vRUhP9#nLlpFQ+`mtYb)K-ULdSTtU"
    "o;S7dE4+%dbY&~tp8lc4806n=Q?RCWRJ;sU>anJ=DG!FO56F}LrH|Hl1Uv(CA<XbUnfX!fMfLk@Z!{a(6=`35fp4V~QZZ9*u"
    "6n`f2W1|zyk5LPsGoS5`-Reyw%v%%zE%xHiLE1ANVJw3kte+^)19kbrtbCi!_jJLvw!xi^4lAr+2B#oj3-KaDijX@8X8#tW%"
    "kEc%@xQN&>wqe<1uULm{E4w@t}RaaUa~BEtbNx0ka!ndT)XIo8!7tgOpG$y6DMBli{-*(yhwp|x9{GaIBgVY-|o>4nJH7qVa"
    "KG+*C~tgbT6|6H4CdRcqMnNUg1I&Vd{d+E$ysxyPeFzPRu@{hM<pmaBk2V#)&tQK#$@FCtlw1%f{?y;p7|F)@<Uf&>OR00No"
    "q+ryb-{D?RA@IF_fzw{m}TcTigtz)m91s{aZ<DTZgs5a|G!4o7+^U-QT}A5tQ%ZF#)Pj3FJBX-oQe_w0O9r!VgFG49=-9Hx)"
    "-`nX--r|Z<e$y?Ft-RWmQ`3!uMwcCxY?SWnA-)rGtyFSQG*lEZfVI@7_v+T3+wB!;@>96OSn9fUprirfsCH-+XLNoTiAmYE+"
    "I?M8Z{gX>U1{ix00Sd|k!hCWQt}t5MZ>6xeyKnu}Guws?dB~^QhL;R^meXMVV(ya6c4pj3KxWBjh9x-O@}gDbV*`rtccqX3f"
    "z0DsEr_RD{ms_n$NKKMimfl@$bn&yD!imK4_@f1-J6PF)sgk$Le%0eXMq^nZ=CzgI%8cpLTEF5MEHpBN8USwXjk58QWhb3<="
    "x5Of(AM4<TEZ;=?Q2Uq4YO<{4F?J>VFjl3bGe%&{RNooa{Uv65)tef4=qWhr2+5rnwZS%Guw;8uQ55svboRB}_rwIp)CsrsO"
    "dFJde-V<L8|~&eEUZta@~L<vs^Tf87zuVKPU`@7CJ4v575x<FuP1Ym|O5W#z$bm5JUFqCP$!6gHI)z*)}4US^zc{2GQXy6^t"
    "G6GxNnAl}rQO`LA{WgGF2W3CRMH^JlF7u)ox)xN)mT0RCUZ$jgbk#Xc0n2h^8e|p#+y4!mmO5dDqRpy#T6=lJT-CaGgrR05k"
    "7=V%rg2jtoKfiV81#;|Mc$QhEp8?g*>(9HQy(b7?BhB6Gdn6A@K8xUC1DbxOiv&BB3L=QHH2o>di3}-p6n^wIY{JB&A)Q1Vf"
    ";5}C*ZS-3p*hpapMt)au}!aN#OC=}=!ORw*mOJ6gLAPj*F>rDhRC_FAw!q$<GKo+kG$7YllRhxGv5CW?1k>hIw*?KeD83k_X"
    "6ZMs?+}#FyV2em-{YWU}Z%~ns<fi(S4<a2**0#aZZ5dnOOd}W_(t3E3f)N&DC`HlKJo?74n;`(TxB(#KeC%F9mYNjL)-wld3"
    "5?76a`u(KQcUx>INUvUZ<yQx$#amAF_pC49tuWL^6OMDcXPFH;2pYq7h|C49xuiMhMd0J85s#s@tYvjmJVR_TiGu=tHWPq<D"
    "or`#}LF-_^jL{fZrqE*Ah&cVHvIJ@2*O5hOHB`Is0B%pQ*xS02{&wV#4koPNYVX=L{P=rOT1h7&;%HcsS!}t%)D!KT`Ok&>#"
    "gXDb*-3bD+jbv4_9eaU6dzwRO0DR=o^p{3#nZ6Oh8``ZN@!Vu31X29W%_e`n^E>Yz47SU){y!&5@x)|V>yjT|Rlvf&f97BV0"
    "+?pNXOgC+>A>s{cS2u5I!R0heqN>DPIHl%j#XttPOH~rtEln_O^>KIV>rFzkFg(c_oxoz!8q5Kion2=T)%{WsaI=F*}*XOBk"
    "6(&wv8RDi0|mnK*7p3K^*pkn=y05rdJfsFy6eG$4<WI)H9?79R4K7w%)=0?(?hpR_^}ZenTGYQwOJtVrS-a|6J9#m+3JsE-e"
    "T@lf)c;mi%1X&bFG`AfYvr1`pG0LZh0#jub-R+nDY9?}VB6*`Zx<5wG3^s@ZzC2W{Wz&dbUBO)dyejP3pTqzXKRlh$@chFD0"
    "kt|94(+9J2?s24~|F2k5GL>(bklRA!wkV6bU`NF5<hVg@+EWuY3iSew5=>WTUTJiFpEcMd<rg!~J*t!(#h7JAbLc(9z4bUYh"
    "ZI6f0xk=o%jgq<oR&q|^A%{@(N9ow0gqTE|>wc3ll`c8N>+99`K&iIoIzU4!xcEcl=@n>@I=aLxrRQz!>$03*3y|V|*h+$)n"
    "9A$$Vp)Ww>^JcCIor8EXewn*G8WxfPJ~j~0kp%>3CrD68^}|JqVRHyenV_7bWR#)HH1;+)3)q96~NZN(>?ulq9gn+^qJe-#r"
    "GIA2TBhdHbg919QEX44I+^Ny%&7p92mJX&<Qun33*W`r6!FM3DDM$HveKLeLUX0vWXg<g}RRnN4jY~!RfhZX{OB6nICVfL#>"
    "s!+jU!77u~`#lUA8Ny0r60L1@pO8Gc@Ix*uAO1G-Sd8N%iBHovI65zaU6N(UEJ?*jqrd0n9o_p9Q$1ylm=yXTeO@Mb$GB4x3"
    "}%Y>v#<EXr8BZedL`unF1%Xpx+QR<BHTnjKoR11dEu4ARcF=GvfB=;-_5U#qvG=sX{#2xReGxT<^z4+maYKpuYb3Du?T|L|D"
    "XFeZGM%~|1989W5Mf)>^G1b@vs{793E}!P#u{-Ia&3!hvvXTj=#bz(e=X4Cd$KxSO)<Nr<<M&=QMYh|}mN<7wm9NL1Xp1Ey^"
    "2+i-+0s`;T)wFWviDF?JX)oD=q;q;-!IAgE--%d!$T#C23hS~%IJBN0hbHJs+scqKF&g8w%8u-ngm6JWOC%|<BVp8Pn125B8"
    "}FJi9y@3&$+qVQ!K<fOlzd$h|^==Dz==}L~+A~p;s{Z+8RuRh)fQeq!E5$vN7AOGgWV<2G2fKo!sDM5OLrlbA<BdDL{eDm$k"
    "CYUNGM}=rp<HQzQ?)ky|+%dJJ!(QDPk|2uXt+ByDwuX7Jiun943+fG&$j&xI@9s1sk`pUpe$-vp1Qx0+U&(}xy5K>Qc;3)r;"
    "%%~L^J{nNdV2d@@-JhW>d7w#PVt5LfI*q<wviZFBO9=sYCoE7%KI7BEN4azaw;qDQtGC>2$@J$LK5w`q@CI`Lh--p=(MwoM1"
    "*~7~z0y`7IK3;<|)aGS-h5ZhUCZOHVIT%_<!5$t9BSv~IU#u-K(Lqx;gI5fOUP2Ti?#Wy#k*2EPS%AWo1skxpuUQA{t*tgkg"
    "OuO_p^1Xun50HXoeZ<W!bb>`VTiK4F27yBTN@e1fnR55ug7)#3Uz4SO9Ti;&Go7L=Mby{rrKcjzX4%NrKv5d#CG{@raXOGys"
    "_Maq6RbKYj+G;rx+C=sk}E07~A7MDa3sIH6mT_Clt56?(|cE5LbVctGBS3TPgm<*~$m#qy_8wq_sEOIroLp<M3;Up99BWtbo"
    "LzX1F?ws7f?V&|}BdOaSx&T$JFql&f-z?)S4KIN5NcI$2c=fUa-uf)H*z5Br{kDlEaygvpu~{e;m$mfLpA8S%f2d@$-~wh-N"
    "gTCfrttsKtaZl~oAMk6T{80l~aTcu0AzEqeMy$PDEsj7vYuda)0JzYp&8z7ZZJ+F|QVSC3_Lr5wD;#Me4;3W(F^WtcJS((mr"
    "<ivmr&W%8Xem9r)*ZJW0sw7zUJrM(eyX8tOqU;LxIYpst?EcJ7?8dV4>^iDhnyc>Y(8a0Vd&!x$6+2d3b7DQN358wVUHQ9NQ"
    "_oRGE|o)Pw5@5@I#2EPCpnYvKNWaQ%<xjj<WF)(b9+CSIHxjDo`e;yT6<?tLr^#;h-+!OHF@?-Tep;rfHSDx)DM_aS7Y)Yzg"
    "5?fNgn{{kE!ruX3o&b^jtz~KRTnTsWP}DNgi$Y5{q;27@+ZxNBNG?W(|1;7^~X*!MTadyZaT<J1dH&!>jZmR`HCeH79Xm0d7"
    ";tLV|SZsr6pv>oNb@b1yc8XQ2JZg?=#fKiYh5fC?>rZMJNGU)qpP>MyWZg70RG4##O;c5!<9xQV^Ol;ld+wbz6M2J-mY3McD"
    "F0=o*GiZx{<JlEQB?m9#N9T{P991o`SRW1JKeEH4OYX6jm76U40{P1@?p7qO(7l>I=ocT1HeGMh5cP2OZR6T!*;0#XUgMbDv"
    "^f_-`m1I{xLF3al?Jw$^{YDvr^&V=pY=9^V_6b2d7{Eu<Lz{u1fk-c^qFD60E}0_~qG?RD?Ewuj8>)0ma*t1lYqqD*t0~{Sd"
    "33laa!BDol=g3wkb~f#BH1YKlMxndmB6U_etmonR8O?PeV(4fH!LyqciEE7lzO3pI$5Be(<VG%fuya`an1!IuPVZ{8#4busY"
    "-R+6ftS|@s~Oc(QFrPO)n(h#>)bY&|qmVSab`W^Z=4TM@N%GfW2_J7RJ-SOf~=%EhSW(Wj<;C$C?utnFe(_@7AjzDy{#!tPX"
    "=UY^cSbjFzJ6pD>~y3p2yPjmOt3_I?zT%zS9XK56l}?-@60)^!nP+6{OKGI<+hKC?72CbnfdJDKjBfB1!<0hT0j&eAqPiJGP"
    "^S3tgM5oo~d9c?HU{uUSd5u4T9?^32CC<frHVvr-7U(wEmBkZ8Ekp$Ba?BLCh&ghKPKK|RtHpe}us!PG4LMYB}9lwW_FDNNZ"
    "I)8`DK}!XJ&)B*u$$cG^zO8JTXaS^zbvm&Cn^lVS0usi&URBD3<A3~-F(}0vJEfR4`vX(EzI0&My|%XA1m}W&lL&&!n5nWGT"
    "_DhEc0To}L*3D+X&Cb&Zn<jkGc^w<`~-2<pQjFbR3+6ax8R05mVMt^pKmjPo(@k$Rh=)Xhs$=w-+nyx(@6g=CG^oShaA)FJs"
    "o>|yMi5GRD2@wsE{JdQ3VX81Xp9Gum35Si*Sj|wUDKvcs_*Zh*n*<xPhDKs(t&O{gE4<NP--40CP9`X%bY&0UZF3l?4lj{0V"
    "fs^{@u&>x(bkh%R%)(%-XZ-b;gB8`kJ$_rj`UwmV}DAV}*ml4M5V6NWT%WOubX{^qMx8JgXS`C(i1>za4JQfoG(^}C)w@9^6"
    "lU<iX@wn(ucUT63|vi_n?aF`2PQx{5<&!nxGuzp5Q_!{a&q>(4t?8f%Bw*LF($#*Ks=Mnca@JF}i2b8Ir7}>#jeUEg)E<-47"
    "5|KhYm8@7+$IX>%*Y+L`096cHN)l7H&Hn2WDsE50N{W)}g5$ux+99v!{v5T9U1@J+B3f-v@($o!?%jx$P_1a;k0C1|4CJV>Z"
    "PoL1OElxD_DI*VI{g8bjb!E>Iy99atdwqGwsszind?KG9<qlU@td=5zKt;z^H>Too#`+_fSj0=G5#IQz6=((6s~@A3>^4!hx"
    "g?5{8#Tqde>1g3l%eu&%U?tphj6#Zef07G{|-%jV^8XGaYbanAUY=kEkx9(cf|Po%VRUE=yADuZt3mrt!J_u1b@L^~bA>lO@"
    "&~KN#~7!wNMm-t;EPDVFr=#c9iL&IX?6(;!(<JU2_}A$h*V8^8({jsLzMR6(Q)#T_jq9Bo^J-G9XXM~8Y1uf(UzGGNGh!A(7"
    "A%1S719;6NJW4LCP#Z>Ghx^YuPsjqgUm#L{6*jyhIwWiExkoWdjrE1yQ^!D$Q64P=5()?)C{CMKeFBnAYSv-Ge#XRyk+~0-4"
    "+a@Ctkh^Gdg`cpg*BHOR?EiquKFJDr>PQ`w&fau9xAi%N$~9JV+{8t|L;iHQx|^m(^|I*Lssed|U;e$mlLVeO&bbIE(GHVWS"
    "}&I*@s|X}YP?^P#w;3C3o5o}U21{TE2SW^P7~jTS?0HWKXt%`rM(b3F~F(hy6&N!GT~!Gy-j-kt=8Rnr6e$NaW3K(e{D7Gz<"
    "zmWGSO+{2SsM&0X67TY4T&VIYXX_tboE9>SOzvwm_JmLCTHRxErQ{Jh_>P-J-9(JvG>XLx<g==I1Rw8z#Ua)H~F)!i657Zul"
    "QdH_#UoU0GCLqu>ML2Lbucprb&Q)4(r6_TyJm1%r`y96f~DZp0SkTd>drUXRbo6)p}F<?rJbb#=69#zMNF{?9HWQpi}Wk!VG"
    ";D(oeg5sc;TeWqgcTW_zkW!mU@kPrFi8K@N?o1buc<5zQ~f=WN6V6~K~aFzbb80b&>@5S2~2>lpTjnAVA(N`m=$eSuflWPYr"
    "H3=c5n~SiKukvdsqczR|_30+xwo=n_A2nz%t&cDPC8SV}ffkSGepGg5*Q+)-<?=&pkH?NMA$;heS4g!q1#iwv<Ti;56!ZY#n"
    "Ufpr`7}$rxhE|aqNMuo&1^pkY%$e>t8yi&xY~&859+Hq6&B_PHZ63;4kis?OKWyla^DESCyBWWKOrkb-2C9qTV|@1e|~zFA<"
    "r!%>^IrR)AQQB=voh^HkfD7)9Pd26`k$2nDhR^#UXrzxGtlU0@QcH(=YmuY=ZQPBijkEV11R1UPrWvV9Cd$AWJ-+RilnGlhR"
    "s|Ce$s7JQ@fd$`r*k2G-5>DGC%W5}#YL><<!F$IyNUIYZPj*g-ZC{<6gYApe~cHj2E`<(5LF$w4TD8#;!z3Vtp1k}D-?YXSu"
    "|fbds~kpZN?4hslJRD_pQIz`Mv%8DwkCsYL?nU+$OU3yhqi#fn{KGl&n+Y9|<>mHrwN`N}YBMJDtY4LnkSox6TFVxuczm^7Q"
    "ZZDO1d4--f?QI@I0>LA#4##&j0ZZ0rZ|h(c-9~JSyiB)Q@nM<Pzen9&Ik7mB`P(~`m?;@8V>RB7MUeiLsL=q2rcuBI9woMYP"
    ")B-R0zP2PL(iBYa&c`qqiYgq;}fS7wr2Wh`gx@N@PN-M2OyPdXI*YXe$G<tYz1v`i$pTPMaIo3xYTA-EZscdbrnEd*u#R;Fa"
    "blss$D2~e@nE`B}wAYbv?7a5PyiLet%U^=cfoU`c2UTffuWc<mHp8qJwcF0B+Y@F@P#&1Klwg954t!^P2Rj$IY5&f35_ugMR"
    "gORE6{uYLw^T4h!9(Ono<s>d2J7S$ne&G<#}7y!^GmW7eU>s8*9gW2pko%>A`zuN|4lgGDya25YMT9pN9^dn0~c&xDJRfZGg"
    "fu3_odzh)!f)k>bHa)!6mgL}80NjHdaQ!4R4Q5EuT^cO23g^NEQ+H+$f%i#sOi+qwY#vl*07`sFmE=>i@UbCU@#O2>hfTRq-"
    "gPy$avvb=ezXIs(yl~_D3@oJ3Z{X%)i%7UDqH%5s(Xb-tm7<({0)0aM<^ABP3|_;@mfV;$K$Nep>V9ArdJSf|Ilt5~TV{<hv"
    "pm^T#?!T7{jX+)tWLw8^$xSjZEwnF@FBs@SYu5$ss!9Ac>4+O<72Q%jl!o~J(9djsbr<d475;UA<MPt)~snDEn_-<`j#xH03"
    "Gn^mlkt}6|^(RJ!}D7heEaEu2N(B)tmEYc2t&-$!b*}$^-?5tCjn<{+qi4(wxaY%I7%`5QcoN^1sESVUD73Jn^sV7jq?z2F*"
    "7eAa!6U)dA8`#fz{D(rKWx67di?W`GpwhpIV>@Dja$H;Mhi3DXf+O~Z=Pwjn-AGJ@N`4Jqi9$c{@?i3x+6Y%MBPT|~9gR2S_"
    "?J4!tw$u`!QO!Bx1i_vHC+-Q%`x8r33=o`%P{<+Qku(bETG@t(8>D&E+Oopq`ZSYs@IT37fap@=dXLk7n{Jp*`Z}Meve~q%3"
    "9dDK<LboVeSbbm5WUmc-xGXBDfOki(T_FEy`xSRbOndv{b;iPkCV@rxe)Rfds}yYpnzh<ItonC^bs=M{9HqP$UX>h$@8$Hn6"
    "3X3+Z6&S)5tk&nH|}RYz}&%EvJ#3m1!$wbZ(TUI^-UxY5mDl(Q|>Pfx|xcuWVXn}qU<9$)Is`#UWiiyv$Ml;t+4ufZVAG%&M"
    "v}DzZ|afvI+iam4Wd`kDtlpxpmelmXKMX{=%>&c{YJ`*Qi=)HlYx*S0!m+5|UU0B)&}5MbxK=-EtSc0<Yt=SJs9i#@XAN4c4"
    "Wje+D-)4PSP8)a`Ic3w|8Tw(lZJ*Ch;hpGW*e_fx}5%ueFgvZO3>50tbL*;RYer15R)d=96|7z>uyzGWrHm7`Re>J4KnH30s"
    "R6M}RLPaGg+@lM!L_ze0t?-Y{;`e}`J68!pLnwxSHynbd7d4EffnQvwZA)=p2@TRE_n{01nt$}2(^Tv-iFMIfQ4-*j1{izZB"
    "|I>)k+FoO3my`wy?6JKxwZSfSev0eH8gMQ;kJ{Af5OkC`052;<^M<-j)0?x*Od1*#G%X~Dc3nzh{MR{Z?R>U4rl0&PRNuPbk"
    "|65BddU4;emAPBwiS=3fm0benMfvMu^O@rs+sgaT?D*&Yl5IB-CYe3Lid>ym*}7tv`6wX{(;7hnpAI@DVW-ma~X9ODED9dWl"
    "3eRb;_dL-~avb@e@f4w3GXRcVcko({=&@>vv5NLgF1*VkJiwb)BHyXQMNu&g37vsAqffK}XeJ19O1RBm0z|b7*p@XuVz2|K8"
    ")ay9M*sSqWWsHNEb$A`SdUn?9P@f?O0R-a%0s9jfGN8mq8zr;<zD?TjI{dS(9bri_5mkWRhtgCtlp3Vy6T0^%MaU|8THk5V4"
    "*TC)<GNZokBU1z+M-gd+sJzI0dp~;H%;~o+Xl!@s>?vM^Od_bWC?!WGqApxA$0%BQZu4uY7vZKq?5HJhr#a9XzHv6PRQ`&J1"
    "q((EhA=d~EKvTfG_*$TRB!HstB4$m1cg|$_`+vC@pt%tDb6!jf4qWT^D*ismzYSpr>j!dP{&-YRVA45jB5a6HTbK|^#@`%H;"
    "n`e)woc}IBau1S+}iS+UG?q;Z@mEiJn6rHSEa=f+HoX(+^v3wTxLT9Y=2bAhc2#M&^SfoPTt|7$R1X~684G=-<G?$Tq~&@9c"
    "-bUUw~o%|Dva6Pq2y;<Y0E~PjV(<^aG~m054@Sgi(o(j0JgtCX?`j=R7q49v%o00v4?np~F?jv=$Bz)O-}9tS=Lo5JxJuc7Z"
    "=r8lJbV{CSBs!F}Cbmqb@3lKsc)__W=*=Gy+B2R~(l&B;~a<d~&f5bgdlmfM}oz}!hV5)lR39kuCsBgT&uU$?>GE?W+KZ`xw"
    "sx+&TPE=&SzB|6?rhTK_C5&NLpz~diUu{a6_0o68}8Gtx_$tk2o>t!0WaURi2(>!@E44EX$nPzkiOb?ie7uXhe&b#_%_d9QN"
    "+rG}FA-vDP9N%js{f3JSH?*uWF4IsmqXevc`|hR9u6oCdzA@P1L-f+I+Lm&^$IEYuaCq)(fntv8RS|daS4b|si*U$E^XDN`s"
    "vEzoh4CW0Hl>#j$`klfxG%f+<b6@$2yN#DAL#a>HU&%7-;0*Du<iD&VD&!&s>s?}Dz3V5yhX@bS(|AE?RD!q9wj^MbPK%Nla"
    "!v!c&F*f|B58aQZaKPtj6ps)dH)syIYaG@rjVk?1Byd^)ioiPAt?a3z^2`zo*WuO4DGSM$*{-w4VRjg1vL}@oR?jC!I!E@-#"
    "FyMlkF$v>7o~K3W>j@7kqL+SFFalKT7%GifjtL>`L;iS2Y8sRJdpoL*lPqT*&fhL#erVO)$0Bm@h4tk-sG?7;j4??ka!0H^C"
    "ZBFRiBZTjWz$RQ`)$U3H2sqewiD=bPAX1KRZ$GT3$)3rSieCzF3|KL1U-h{_GZW`1fI-nY<@jr7yu8`rRQkQp*3S8T9jn{P|"
    "Z{PPQvgO5~xb4WTumkUWZRA6k3ccebrJ4jg@Q?$h%vL&Bw)r66*T(9*Ngb3uLgs}klISzGq+N1GU+rwRWmW%446$#b1Z=8nN"
    "$!+^hWcfbEg73@=DK_!%)K?}+oz3T@Y&Fu5`a(2S59$nD$frfo52+AE5>nlTN=Q_>tl{hY(!UO48@>vJ*$R!UssiycvS#Ehz"
    "R@H9y_T80%hZyb;CrnN8=<TZ8avyU5bZ(=~B8m$#GiHve+ECuz72H@l9oqmi9d3fe!eEjpcp^Bj2k{umAeYfl+?h%#5YyRa*"
    "A#T8QVNjqQ=6*>3C>Ta$Omo#MCr&@uHN4M%Cm@C^;_uXykbl=PPYu@`^t^yRKiS>g@bdTNP(Jp+HOLtO-QfL-z&_!30|Un>$"
    "*UMA0z<iM&MqOaY$%zt3M?ld?!N86yGQ)AB@&<vCH{Ar9ZVr(J)6Zh#T4sC3}yw4t&iww5Xa7bL7AkfH?wRi#q-zW$E3XD35"
    "rwn()QQ&@U(oj}P98EAq>+jL)ydZ_TE@T8q5&S0P7!Y$}LtJrd{$eQ2;7_PxD&a`pjsnM>YSyN`VEnzMUZhur(d+mKGY5#pX"
    "fQF@3X17{O9h%aSFJ)a3Z1JG`<WJNQJ{RHFi$boAKhI~n%t=keGp<wjw7|eE9H65i*47QepbD*Q;IBVXqD+lr5a?#Gy7~$3Q"
    "20!^S=SDH$Wjc=o?(tBQokU$aO#O7=g0T6$SycxBzy+_m>lj>ocffxC(fe%OHK%1nmqo=neP;d}kT0NP)asb3m&U|259Npoh"
    "=xUE1$}YyuMb1gA8!Y$Ey#k~}1jw*ii}dPh{N2Us5lv0=*$ZLXJcME}Fz=zt%P4Q}cr9{W5wgr_I8<p8PP@GyrDWQu<1mP_R"
    "^GdzZvI9Gx*H@%COyI;a@oZ9+e{8N(ML4z0cT+mi^2av6SNdi4_{Idx{4x-JK?);y+FR1lF38?`GY>&k(jkhT}!{A_>b}4UW"
    "QKg!{<vcZ)yKlS$GFm(O5qswczo=+y2#%NBe|Jds{WR*3oZb5ZczgmKeUr<0J(~!*C(LJQU1;%tH3htsUsT7R|N2f!Fi!kW>"
    "0XywJ7aBobE>!Y1F98rLtfX2l@JFPqR)^g#PTZ%V3Z~XDg}x}{}CA*E#-OwgGU)A!KF~a*88{Dt^rzI@eh%K%hxB%t9{IIqp"
    "yI+TqvNAFKy#u1sreKQU@o^DE<;k)FIykB7!eUd(X^YO*vZewFlax21f7sZ`TnxK^AwBBp*pnz+2%n<p>c!v^(tU>lP;SZqE"
    "NOElU9@S-Ea35bOmOc6{YM5!oSKs`ZVn2DZWV>gEr--UNwszROB`7hu-g5H4KlTbIgCeiX~~*g>bAp8p9pH{eZF19TF!y4Nw"
    "ec^lIY0(YNk8BXpo0kTMdvnHss(-nJ&iTZLeHmzC7d%%h-of^Zlwgb+haA^23b&GrRt?-7%-CexV50*&}V-C#JDg93(I!F^%"
    "3EIQ8P_FqNokBB&8P}WLoW<Zo)Px*s6fKRdQ?T2HeK<;!0x+cE3nGK#WNC5#0{Hz(CZ8K$lsYfta?NrT{*%C_2u)>;Fz5);7"
    "ccZe+@kUDh`YbM^ru#H2Aa>~ozHoIcbN=VQF;7>NlDfGe|J0L=4Lj<72(8JPZ<m>2lo0O5*Ol;dnpDthl;?Mk3(uclVGO(cE"
    "n$lrS>!r#tjBzp$YR1=<l*hjQl0r91Hru@~Xvjhx$QDnZxe#md?S8XCM!>ze__v6Z=p{lL0JJsfr{$s^%Kwuv2`C4aboT%<Q"
    "z145=l(l9lCQ{{j#9lkKs&F<0P{<y%F@YLqfteQ>`+lnF=*CFGz8D{nzK4+Ub!^HyA-`eK2PQwB4cw0wCTU`%vqm9TEXhNNm"
    "Kyz@^MHr5_Oq?fUhD^+tGf{94E2noMbFq=pK-PG7$NQ7!gI`0h^W3=#ZTa-A0kv9WP_wLJeM5>7Dk*vYH0QhnG>Ti9N&Qylw"
    "e^!affX$-RP0;!)-Y59vj>g^>N<;XGmsOSgW!kpt{iW6sF639M&8@oJvb^4<IHS@x0s+A%{quoui~NFr6?MiHCMNcub6cQ`c"
    "62-vXZJiX01Nz1F6TjlmgrRr6CE8dWY}6Pl3&!v)?uo2bHYOyGYNKk45RGr*QW6E;O{fK=M8ykSRwuU9kS+ND!zJPGXs0BEw"
    "fY=>PA8x4y>k;>(n9gB=?Iyd{Xr8;L@_Nc(58s6wv%XPDmwbmr#u@=W-DNR;8kws2a82l$t-U63_WnO~k(;)3u?<wQ>0dBd;"
    "wg7|&Z9Kty6U+-`e&yuE?Lmx?tb0i`VI)x<lW0I2vM7DQxiE*DjZnk-z+PAUi|wr+YrWk=%ljYK1FJ;D1v3CSJ&isxFx*r#_"
    "S@2`^OrTZ!3_UF%@!Kx>>9L_T*gWXk=L9xL&{5l1}JBbQJ-|~Eq8=n*kTJga5b+U!T0PDA*h2vd|a3@{~C+2Q>p&h?lp?_la"
    "sHbd>zxy3@jZy1h2OS5b<(Votxe6KyuX3DWQ_V6g@$ktt=q#ZG(zR^PFx>@n$^N|VoWmt)8)mIv$@gyG&;fXwy~{drR%S&l!"
    "N-4A5>w@4*kp#G&hpAe)Y#VqmUzgKO&Em>Q2-3as7uRJbhVyTSwQ?DHj?+#(dXOjr!V7ezX)FG%~3u<EQDfOx^aEUV~14Bkn"
    "B3<M0Z-&u1&qw#qnIv=Ho*!>Fsq~4T|rkTwU_|y59EMRu*pFC@rRaV`C=S4zC=oZ^k=EmwwSAhBLGZrcat-k6qaclGYXQ)y?"
    "WLG!%z_NIynJXjI7?%ALx@$86BV_`Z~3KWZ<x-{IXD8t@rZ#^1>byNr_){eeQ~Ym8e$Qj=owJjl&}yjaSGPK`;ID;<Co8ep^"
    "%pac~A3RuV)xqowsam+}MpS7erX*yp)watm*QekU3`68y~TYlgT{as|=jMkIcw`SOqTR+nMCb(`NnYinvv<nnOvJjf5^r~Rt"
    "-q2CHQ&s%mgEi1ZART{(WB1$HS|5r#1z{xWkW=tpEUi#e!lq_;6y~)?M3W|O_oGgWJR9?VSbOfJTuMwaDm(hj%B9I7n|m{Lq"
    "uyirs~x$T3!K)Vn<|X|n8GaJj5DZ-T8Yq!Tv+zv1v*7?b$Nh~;kYxCcwZeIHUOQ~bRRBguWf`-`_llzm`BxvdFF#7S#rPSu9"
    ")+ub8vpgg&lI#WC&LjDGuoUNpi`-OYLBe0NCHI$_;hlJq=a7@0W0QoseDri2gZio55I++ihXdZ1AJX7SuPss#-}U$X7S_M}i"
    "I>556LaAoDtv*?c^62T+<bH8=9`KL55oc)0=FRAT%_?3+ASRr)_2(qR79)_9^``3*DV%|Z9RqUiW}!&P*KPG|}{H%>o0LK^+"
    "Hw{RIEC|81Ov*Vf+EB<X?Y}BJaR9!wBBQxz(YVowF$zPpb3Ad|mi#Qv9Jl6ym1F>LyS)hkw6aG`XaTAu!Nb!Q~dl|i{hQDvU"
    "MKF9A>u5MNgaSJl)kmoLDMVB$lYSnT&E^1IpM?StHu8<yA(E<!RAly?j9i%=k8~s%&`u2)8!bA&GIj6~Kmxc9_TE4IVT`g;r"
    "2h6^=}kCxuF8)9NVs&ocB#8MGY<@7H*?Zg$RMFhksMp~B%d^9bS!J)n%~Ge3MA0?cU^KOJGmt>c!nf-zvX`Loowq{u5nv_Ld"
    "|gfgmzq1vPnMerPDrEl;(-b*^jNA>#jw`P>>%N=&%%7;2u}c1R~n#hv+s<jk;8Ue^zQKdP>u%?}#-iJe1h}^s`nK>n7Q3Z7V"
    "7hVo}*T?9bT7hZsvOuN~>9IggC~fAKhgztISZiSSnB&#Fkef_;kJj(-(k*EuzSIF|9EvEQ2n9DFO%8O4Psmw$wS*WXzyMV?;"
    "KGCcYX)0ESKDn5<ViM@;)>)7ESi)!j`b{<`LIK7GLzN7B!JQhTZnGsFFMJWZ4-p)(Pfg(7Y_9BB+sZ@x|;Uq|c2(Mj(gpQWh"
    "@oNndVyIDmx{z!;s2%itcB0z1y7IAt#P8nibDPG=t1JS{@DWr|HpJLhy0wwe6aRMN{CD_dFnXmQkEYRR5f*fF1q$b1wpsFxF"
    "X3GHPctHC0;h>|+C@ZN_rHjsQ~6qpo7*FY(JhB_qAG*-3_0Az0>Vw&g%LOQb%n>^vjd}Z1@MD9n}%C*>6gB%EQj2G3>==>rH"
    "2T02Q{3Q5^Z-qx}B5dvSy<R=zi@(5{gtw;lj;`BHZzU%6mN6Smnqry7b1FS(6xQ7>ElywWKO)wnZkx#L^`JGNKeg)AF0VY-1"
    "W;8jWfVpcr|3-PHBZZj<YOS0+FnrE_-t!*0CoJz|!{kC}M(ueiLQiZ=R-Rsd!FVvrJJextnU_hH#s!ZjtY0~5wc-wDV*)bGz"
    "m*nr3Bd^{7{Clz5#g<9IUK*f*kaQ+5s3@<K<C3MH-VQtP>7#44c<)c|>{>f6|S2m&dpiEa_Q5VaH)vF->fA`eo?4x(d7_f%{"
    "Px`)CwVs2S`PxSNZ^D#aU@}#EVd*akt^!1JG>+QyNA1MYlvH542Siqc{qumXfA_*+$e@3Z-KFG!q9wTUlRi5be{I=;7)TLc%"
    "KWGS`P!d5zl<4}&QpEY=LJ6&HnI0Sc+q!?34<yHm;lgA>=P~Fjl>Gh1Sai-*85>sHeSEq0)z~^!@nYj;6?K0;eX1Kjc0IF32"
    "_1-;rpOJenc*mc)dvgh-1w**A3p+ebL5_xBV&=nX6*@;|4CS=Y<FkA}0(|M35utLIN;XJL49f2;h~W-zhbwN;-(Mq8`jMbN&"
    "}uGwgYUGPl|n)Z3Me27WqeuXOLcmswbt?|%(|Xq@?PS^c?NwC23Do?}-D^=DBh<7KsTXSyL#A&^G>XV=kFl)x*GompU&OdS*"
    "5b!!tK?+2Y#Z1eoieejbAw7+lk)5gtL)EY>UD`6{pEP$)0;pok8OSPb+XW7o&?m_)*N6OP$rRL$Ck--{mkBNa+0rU+jC!Y`k"
    "cAK*?#|=%Eoy{J-%=d9#vKyZchJdxsPdOr94!Ce*OteLq03e%XME%ufT<d8s?L>H%6BRrnQU>P;W$0!$&xh?{Io&I?%}zjFB"
    "fLWq44_<Zwf+!TfkpbE<s${-|Jtu4Lw_`x_GM?ns`vMo^khntc$*&#4?pW{V{IM%y|)n+{I;xj53%M}Mh$!~3Vp87o|J03pD"
    "$IU{=3`^>0U76t;l19B=^}(p6&Pz^f;>=JH+43hx52i?Hx8)kuR;9w<}=Sy8n|xNqzFnrx}v~@4oKQo8A3hiUjaJkb(#BW3F"
    "5&1Ek!_0A)x3<J(F-piQLMc%vhAZE^%GTgy=aJD1Uy#Q0n~B!<-D!xu~)ZBG@L_orh?O{7<o)gc(zL4*L_Bz$C!J`~ULD44E"
    "mtC>rt`MT;<Qv5=;gYj`G5~&LHbq?ACzmmXh?F?`H<->fMwQ6`)!MW6p$}L?#0R({SBPHMu4ZKu(2|Qhbnv6{(JzD@FyKQQ}"
    "X;#T&@Vy5%gIyOfb1(F<>rEuddmIov2CSotc^DIMu4DgHL9nr^SuHs<^b8<)c6_yc%~#WY%%|Co`p-Koxphauyg-hhi+3Ymn"
    "`yt(uERpQGt)M4s9wLC!!AVZ9q_2a(&8Mv5swW>$T*Sn;x~Hg2D_@z1eGHK1dmG1MKbX*y}o_zmzhQ$u4DZgKUA2ZN@uErM`"
    "7I6Z=utF!ab~PhqpRX@@FeIWJY57DK@k1bHRgP1)hGwn?h%>m68J;9_Z$etQIHF_xjpQ<gZ$S(4^E&i*x|5ZTk$IGCbIFC~U"
    "y*Gv@bE6QsTzX#bA(L~H&sF+u?4Ik_ERA(8GOiTzDc8CB-c2?aS>vV7eWmLK1;``YHX`$FRMS8-c&DDd@==4B_8B=r?y$k_|"
    "hOoHye-=T2w`AW8bm*c-KxSKi31s~eRP4@@Is&v2kac%huS92XQhEgWgSAW%#bXw>C$81FSw{Epjkm!AVGyuTr8u@_*D9J(*"
    "ON()(%I(6)@sqHm@-H4;RIgOSZ?IJ@3^N)f&)FH*uADeo5t@R^8$Mf3fnAQ4OY``wKY$f@{aOD^!=sj!VO?x+U+JtLGt!%cB"
    "`#6^T8q*Wc{rk#31FCzwmUirgtR<!1nMO8O2A_RT$ID)F#~AHiJm(>NMk0yv5C~MKqU>~iB!C0I>{#$gaxn~4!B$D^+fTqbf"
    "eA)AUNUqy?1B6e7=4<F)!z_GcEVzalKI^2p>5FBZK2)`sdb03z=I}LumJvA~+1E>lmxf>D&7;F|40Ej)~4P+luu_gt&yfi(%"
    "!yrqzeEY6tZS->YL0({xLi30wPC{U~tsT6_7ekP&cU-q7b#0{M~sw07^5?wltG_-pRZ{ver?>U961jxlDAPpbyC*}{82YkN?"
    "-v3&io$8=wcVV%}!N*8OdY5zzbv<E%-K2Lzm;jh(Gs~zZHItlSN(AskQPqZ-4@00Kipj5)|j#yu>ydM6$LO}$;tA$e=&j4g!"
    "&j{e(siA|zPe4f|;NfYc(Pm3gyEjL`+=`j15CSR*DY-1d;*GXFpQ%KaE#Q1^XLsMgjf)}2n~ISy_#swk<gMo!#!jbIE7fMbM"
    "v+$~3O&Ph)sQvIA!~g#kNyDTcV93P-^;VX$2X)D#-QrVHt?N6f#aoHh6Ht5@;HVn%^05+xvX-u%HFp^jxCv1<6-F^VnyEDOr"
    "s_EYL3=F?c9h9OP|`;a~fJ9+(Ul?RyD4BSs+O3ZP3l+w?lKF%V1D+glkuw(&{kntO<_fa!}~^8aIfsEP#UB_KCb;0%RJ_<6T"
    "SEDZudw;sgWE*?)I}7S5jIr6#6XtK}-?F^g%FN=&Jw(qk6RV#N`tro$|rk{Er0$x_R5VJ_-Ef3e{XAXvM5fhUvhqyNy<`PFG"
    "JuKK6f%OQ<VqydZK{;y*GdJJ$@%v0<d>oq&uIbFFGCg)ZF_i@PM-uqyOX*E{%A#b7U?>(NASLLTg@+p08xKR=2OkB9gG|-B|"
    "51h?zM;QACq8!&5sd}?I24FA82hooU4S~nR%p0#)%UC8S<==%W2mCbki{CoTh0ZA#9}Bvnm*MCE7m=@^`n#OwMuX{paihuF4"
    "QJldhkh-KLdojamrbSPvo<u<PGL;OSO+h>Kfb<hF&@y5WN!^uv<(r>)9$SG==uDjh1@#6uxHJ>P7^KdXBE}_YnFsqnT7g(-Y"
    "|Lkmw@_;vIB**EGF@W$Tk8~@@uqTj8s<QL(v<C2B6M*<>%WMh`$#~-`Um@(@(<z^-Q_$U3R#mn7+9=Gt|fWAQ$uQeJs|_$Xw"
    "scNuOPgToYg3`5%2<yht84Z`h5*1fN+qy`UR}IDx?lu=s}a+-CrSnapwJt<sg=VX@DD%YplKfmbl;=tyqaj~=f^zsAS}I8|G"
    "zk<XPbg3s}d0C=MV9+w~;nqd65*m>zhbbW~`jMAw~5g0Npx-_XLj&LWvpfBaCGH{P11+CjLa9#6twiW*S9tsNpJ2+J^Dc&r3"
    "9dk^z$!bAYwbNG>CE3gqXhzdkBVVl2|3s)qi!0IL;J|LU-CpE((x*KFm@$R$-wFfpZ`yeYmnWdlt)Gh77&Bl24!Ml~Q3}tlG"
    "n*Kt&rP!FkA0mwGkn?DLA1ynD1js14KjG<YZZ8AJ$OZBdMzqh{LEK#(ri?E5>aB0%i+`;9D6Uk^q0H67&tu8-t6f{175F6K1"
    "Iv;a6DICvbe@A*pey*ewiyj@v*H_xoXAG=qcKo|5jBHfT|8yCFrbHU42Pk3G`hfD5+bF0Nmu)8#nl&vN)BAA*BC+6J?4PSg^"
    "T!paJ!X4y|t)jLh4yX#s=!Sy7x<IdRQ#BSn}Xgl?No>TNdQQM!XxRn2fo>zl;ZBZ~0%y>oI<1bp%4$X=RuJxh=P{F$WxV&UV"
    "q?N*lk$1f7IGoX#Bo}K)rO~Wh9Cfbls^hPr7rn(P(*7fi3f7$G5^uB)spBM<0p;-l)>*jrK5Jp+-t)dU^XmgN^aW{UoKqL)4"
    "FFMY*>&4u9P-yFJEav!$PZw>8a_Oi^f>_0$GBx!zo(g6_5koD;q(G(~uRgT@J@3WmVqW|6t>aN^8-wBeD^&z*-FWk?IZx`zo"
    "?)QkgTMe+-fTb)Q6%Lj@_skLh7B@;Z2<gHa|=+^_hI_mBk353;4^D1m+Z36XVE_Ny=;=+9o1%WFmgQzQ0I)~&sPHjXy2X*9X"
    "KQR2l;U;O6p&^1c+z@pb?(4Gx$aRqLab~;0bamO+g$)&1zy6I^hkhHEO<hX!P+~{BR6>@;epvx$6lHBTB0?5;2GUk1-wPN~0"
    "$zSxMUVrW!q#)MhQVc~1sR6u-Pby59@ErlCF-GfmTLj13{^+hSJZen{tKrc6cxNWE39oM?u^{JR-CF<}0C@H`$J;ASzV1N7t"
    "DVA*CjelBHcthdeVYe5jqjkx;yjf-P-VaS4{JCvV}!u2Z@tryzF-v5zwRbg$k-8Q&Gf#O!6NO38yrMNo;cXy|_ySr1|-JRlI"
    "T!Onp@nAW8|GCLrCeNO=m*m~Er_X?8(qwY?<5O`O>K<a2H`L5{8{TR|O&6PggMM%d>$x08yLKSzLV^6@m8f9PpNLB<V2c==1"
    "#NjhRQj_2rg*#{eD7tj;}<mbA1t8L=Ubi*&<#WHsgu);H}&^@@G4{PKC|F0oOHfW=p>;n3w|v7nvO=qk*rR|sgoblJLF+F&0"
    "z|R_vbal;p__k*Awf4vBIwUu+l1nA%0>EPK;hIZSrLA_o~kFiAX(T)4T*Fziq1>-dXGqcClUG`b|LCNw1O%t)L4i6Uy^J0Vw"
    "0K;Ji*05nux7d_!js#Y1m+S~{=EDlZLV?w+;d8NWBU8m(tveIzbYR+QimTH`@l@a%h;>CA+KF^0`*om+`7Rwlp$@e=dMew8A"
    ";TV^MqNe9HsnmM?A50@shf2KUQ^fq{&Z;H)-XT4uHs(3~}=qni<(-Nw=Yg~)QR<gM!aAG7(%Ng9|>czxm+KxaV+pdN@<^i?Q"
    "ntyCpc}96Sfv6kRKL~Cw5Li=rBNd$27d68d)~a(0oywqzIE1yRzb-OkO#dx;!bF;?>#NlAh@_#EYqFjiW5X)(4>5Sy63P6kD"
    "w5?FlC?z_SK;U8sy|+A2vu7eZ=4d^fR&9mIbFf(^R1S7%&?ju+fGzmC;m;H?bHA}U)B!YK_h4sx|#_C{EWB%=KXLQCGk<&lX"
    ">z@7`BPb8TW>5@Nx!>H5aiW{UxbqN04fWb&G19G6C@&Yo!#zT2|je-A;apvTe>!9GWKr>iE)*NytpyGm1}y>Ro?SbV;1NP(c"
    "ebBxQbyz2=Xz(j0R4QO*9uqgan4CZjaDU)IFwJd9EscBEhZ2J?R2eRXj7LTXa<pyL!m-4SJMHuWKVBQ9fpoB`0+8qD5MTmpN"
    "_gbiqQPB=d9kbr(QYs)mY2d9j{E2AMKDdGfY_OD8^qJdX<>4=dYscFyE3zyo_>aN3GEmx9m-oL&Gy>)nD1JH3)L<SZL$DV~2"
    "3F~S{6dog__V49hfWNrdPG>0He6VJUGp7{)>Hf+@_I9`zsDka5Xq!T_A;@8Q`H+JZ=1C(%mPrFG;W5oV1x7Di^AL2Hjk9kij"
    "1>n;PCaqhvb+o@08kA{12hdu<Pi;0tSXW$A;v1NMd}xy(`)DLk&32#=Ph6o%v9Ziee3Q0BWLb6AHDl}e=kg0tJSg`I0UeChw"
    "8zR3iLqDRl)<>weD~wmCrUwEX=r^r@ZG-%=OLLZ}I_VziXIHumTxgyEq?D>tyZ}wt#@y#((wtEOX>iw)+6(y?sX=26;618wM"
    "Zg0JLAWF)-%*M##!+u6_^A>;lmjZ(s=~mVS73m-;#J=heVShOC|J-b|BR@S${j(Y<YvAkf1vJodWOO2W7^#xFB1`@*da39Ca"
    "oxNQ`A;60~0ihm5js$LW4#fP)Rj+!-!{*axXQc0NcW&hD4Tzkc`v^u#l<lEEaN%e;H3SxST7<>8vd1)w*<VQ%$R{7E0=*gqO"
    "<;qHrtYi!m{4W^&oV`9KWnlza4hf)!31A3eR)eO1E^-BkI{7F3jFBENI6_1Mc%d9(>~kVG>GN%IzEQ7U{BUuns^Fs(N(j^t$"
    "_iqkZZI5Fa?vK&P1EZ;7y3oQkTLVrasN8?A~aYXS7Z3u!ouoc?8BG;@6owHFt{pG2FIySyS5`*sOLT8dvnX5aaY;bOY~otUg"
    "@D$B2gYQ!3lcq&Kbmp&9BL@n=m+m7-5L<$N<g;%914Hl7>fDL!F1QXVSFT$dtG{Yfyuv>x1H!hG+-EN^XoP&)0f6V(Ra$Gln"
    "dR$$V?8$@Sp%3XmrS$=QgTb0`-+DndAqC?P6MpD2I;<!N)Cc`q;^{%}@l{B!*|ek);V>;rFE+T8t}B+e);pUh5~OKx{*EsWZ"
    "Tc&xo1MK#QchY<mqM;olaKr_<$nfZLJa}_cmkeEbZq!3GEpS~*<{+XU?Jc6Rvh866rPzsi-ogEpN`S0-QFl%eM2f)TuXZ-H1"
    "Zo6T%<Pg;Fu#j&3+X*?<OVIEAaM|(RITuFTt8CMW2<A~RSc3smV`6PpD6SCB^xI1sv0rz?xdDCG!(h+l(RKyk>r-v>@ECf<W"
    "8j+a7k%wW&EKH&Y*Dw4a?W~1eheF#t6D>yf`0qIULhusls&9a))xJ~@k4w^frT-dHqQyIp1<9p5iY6>ArI<HsD$Jnsel;&@Y"
    ">>|&oYIZ`OxWNJ>jo^A84@HGvxEnDqtmFCn2h4Pk)wYSpO=(BG#-Y!y_UERhU(j1MTFHP}Q84YhTCMJo63-!U3RD`wK0>0SE"
    "|aGss3B?)qy#!#y|dc|;Fl!th`~l8dW6Ce94NPNd*P#@A){o&np+WtJ}@F=s5Fht#oC2|<PhP5;f}{#ql}M;kKYLTLQK0mCe"
    "CM7-&6;mV-vi_CwG*zLY4*WgHh`InZbSW@T0uykTKN7Ha*tckO-lp1hOf4sHz!t)v0pOXHmh{teBQ3C<8TNsr4O5v5Awel<P"
    "Gv=36Y2IqMqD3f2)gfm#(Rx_{hwEE3Rh>MiVVZLbQ(M)8TkFeZAVkohk*D<oxj+4RSUzBbXzu@fU4YUyX-$54LPeyZG|R1N)"
    "K%odkQLE%ueesrJ+)uEnMDAyY%N5Dp7-L4(||J2Kc6qUHh=?c1=UHH6;0^hNYy;RAu>h{K1dezHfm8>S?}!Q>7dzr@W`Ux)W"
    "><J*KRq{faZ*87=2;h`r8PIELiZ-iKg=TR}qMj_6-THpXr%)s_lKTxp~^a>hOMET>l>Q*7HTInIwvJzLF1ObE!&<uTc`)*oG"
    "2{mrp=)Vf{<7&dEHXgqOfgNHuzJT$ZGKavy@~mvds&{tzMcIo0H~z6o(#6kTn(bY*F<Byb?7*!SK2g*xY7T1D;Gv%lKq84v$"
    "W82&K8#rnvyhU8_p0e;*U$nw>^$xF2~M{4us0QEKK?J!Fsz`g&LGT-F4B_1=JWz^W<0cHU4G_HRkBOn~CGCeVdrWi2U6FOMm"
    "bV4>hEX6<pUSqCXjG)zV;zZfJqqDF-c;9-D?S;(DG+LR+3Kbs40{L0~nlHJ0bc-f;XZ24sG_+%mll|x^zpe`f?w5k7d{v`?<"
    "z5-^bXbONKv(40vtY47a@C%3CzI4?rI^B|M_nGisu~0ez$js7?ftz23ZUV=G~=xU>NhuZk-+;Jo^WnJ&gJiN)hs>z2hE8Fr3"
    "i_V`jlCxj7Zxg+q0s%g~{%p0^YU;&6l_O%v@8ecggN8!vCG5!;CP{!Ve%NcVja9A89gnS@r`Nm?XX$gX+{mG||6F?}%AS^{Q"
    "FJg<A(y;R2{9-ipJO;<W%r`8MhDF4)3cS%w8{6)&QV@~IV1!XvD)d&mEx=a9d=<=@b{agG>Zsbp^qe!KFfWYC9KkM)D>mxAx"
    "6djA&mi#L{h0CM1%CJ8~$acAD+imVr|w2;6Kj0W;`<~oquXwoM2EDonBQW5x?XZxi>y{t?!3XognlJM|2Qcq0L{D|xiLxk1|"
    "`HDdFimgB-Ksz&A&GRlpqTBIP8qU87PE&f)g_0QQz1XPF3F(4g>|mRdQ{~iVXL=6Md#pEdx@IB7>f@S42o&P9n?8jP+KD&9#"
    "rY2wj@peCs4-3rs!-WC#Hk9Z7Q}1vf=t-JdUW-Rud6=*@e5+z(8B0EmThFq==u`!0B#*)KwJwzk^GOdfVV035R@{^7pA{+T9"
    "_j@d<k=kcsOHTc6(sYjwGzgE;bt7e>S+?Pt>DNuTPgCaHoQ=d|Ko<N6s*OOH5YA-;dw1ZRxJ$3#;4Lsdpoy_tu5i-(vfj%*("
    "&puPx7ehBl^NjA^g%4`4a;Yh=V8V8SVaL}q3*X^HhDOTisuEd0t$ZezyP(~qtX{pvHo^Znke-Gy2>Ix6vB&3KL4#F&|upRJS"
    "6$t_-lFy@*db_TU{2(|dFVDH81Xk5jB&EFSj6D`8k??%vm|81}M-yt^i?B!|&l`J>f(>C04qrp6`Q_$N=jTlu`{FujABV_#G"
    "=j%k$rPHvM@3rIz=`I%A{V0GD2(-(#gyaXr2hr9j1n_B84wVveF{s>Yn}V83)$qgm5|Gd$3(&-7e%~jn9Jigox9!{P?)(sZs"
    "Lk7!Y26C(_~|}TJO1CPOXBSh0YC7!u0y$612FKYFDI_<0<=}w;6nta{hFou#OmSL5lSU(S=dRtA$X1D2uVvVSwO56WKj@#3I"
    "hJbPzNX`^@Dpr&2Hj)A=cWWQj!!0uPtI?CC8e_(g>DGGKq*}7zlBS*`JDv<u@^wscb9?TI(~^<OfSR`6(#hno1}7WLI!MoIY"
    "zD&;m6SI~v%5)3-CD(3?y@EMkU+hMhY6k3UP9CH8Z+j2l(n7#5roqfA~0eks_LXK;a?tQmU~sS`jlxx;}2fc3OL=%Wpj&Y)o"
    "oI}&|NE4k_<T`YqOx@)08hHaU$STfYrIRsvLqwv3ED5|bI-cG&#GZ&%{^_L8|C@7xrFnH_OgH(UmHHmD~{7p!gwa01<b4Z|s"
    "!`X$+`)uv?F9gea##d45;i8|HO@J?FvC(~v<O^fIMEW0$5nJ3jmOL?8PY&Q;+}4j@rl)AD5pz&6hp-^I-lx&10hDyupOYZ%+"
    "h&r4g!tIxU($@*$R}Et_y=_ddC%<ET0h7$VUQRZ?V|>q%S!T}ovE*zOS|J=vCk}$qy01~nkqa9!oI{J4#Y<@=FW($&C|mBvk"
    "?fFdo-|Z8w>-aIr{%i^$S8=I9;p=)Z7zNcUN4plcPhh>cu9DV8MQ@vrZ|+6ILU-=?;wI3`3DJ%tO7GTAB^vmx~J5ad}|W)>^"
    "GnFDaCE{yn;qT4fIFo)2G5Nzc2c=I9bmtE$6R8-&sGmXq!B;8}Mg6)Dt}G3CA$rJBH@&1si-41Bnc_9X$fiq^?8x6)`ARCVM"
    "7wWm%~Oe9nQ-0|B&VoSEbJVpu$%n>z)il?=$zLElwbsd;utLP)nPv%7UGe-nAcH8eB*)!EXs;xE=ilEuWaqMp8R#TRb+X3IW"
    "jgLx0Tk8Kj!ej0%R+5ss!&+5u$iOGE8o+6u_%o}T23_iRNi{pK2;u8Q-yXgKiQb2*+Pxuo0r=OT{i6rg=HE_VH7~XqsG93>N"
    "(sJatmKctj`yq3!4C=vvr_0n%iuN~cU112D8Qs#-(UIVDfsR2-IX=fHk}nw@z=Qp0Utjw$~4)^cpweJyiTpm9n<gKiR+)~v-"
    "h3o*jg9&RbdWMP8qgIl{U?`vHet4rM`CG)6&qkb|9qNdvAhWc}b;$2RIEpoc(Y=cK5hYee>9uqD9S3v-&B~M@Flh0g(h~Mpc"
    "KnfjZbqBMg^Bg!>~K^qz=f%#y3Uz^IQeSL$aF{1B7#V+J(<#Hk;}0tk}xs+XLOqD>18uL`fq>qn;g+v-yO>&<~CjD*10<SeM"
    "b6xKh;U>QF0mmPyZ_7Yrt)B1M~=w#fO3i`B?RW4Q=RJG`oF_lSE{E3c90SNI;nh=USaQw>mRmJydAgjIEz4Ma&0;&>cp$-T^"
    "gNJdLYY4Hr=$Kk6&)4!7@;Qm}Sd6j{HX1zE=$&3Uy>A;Z-ltO|B#yJvp}u<VnCw<hE7B<SSnEiYhPh|*lhJ@ZZnnXL^50Vj#"
    "1A8s1LD6ijVmRq2?zgi^<fwpn&worwBIv?zGR5GzPOy?y?!)-_CK1%OP(TF|1f(vle@+&*?pq{R|nNH9&gzy7Mn{l<lit;B>"
    "E%51L=796^#UGp#6h?CmtwTZhza0wnFHDIS{pnO3w_^eN3o{i_3fl{+i4dK~Kk_St5nfBTi~2sj|t<=bq-qOhAMpz%ZLJ+Br"
    "zu?%AiR>kfl}FWtdUalTa;`JO1}q44UNQcxe|mqAI*1kH}M1PE#c%-;e9pQqiO#yyYvQ!nnk!PcrvHYFVD+$jwn%k#&$WzyQ"
    "p#HU~MyJSxP9JoMzDeiG9c7;B9oY!a#;tM2|hw594djL#G>zAj$578M0hW~x6M@AFn0fssAe;1tOf?xWFST~&A{vSIAVgf$c"
    "F&&6&l^dv#^N(1b2qV9jsFOc14F|jM6LW*hs+k2J2NdA^>o5+~_9x;#c@rpMI=VlZpk90v%cQEc0G=kB9M&Y5GU5h-3~Dt#&"
    "NJDpbXcrCPju`>Oeb!WY~p&xO#pg=DSP&y?01}W=aZrD-C&OGm)Ct~{k>QOvYn;HxO%v<XF-@B1`kjlVqT1*N^^ZGlQ#w0y3"
    "@J=^S_>QcKG?w@1)u`c?qW6;4|uxF3+$j5sP<hkj%(U$(RO4R4F8NzcqjAZK)VNXb1()!vZ$g48|_9jg<i_wX8L47k%YOyAg"
    "5KI_I(hMa40>RU>pb*Lzb6H(qqR=L$+ot{}6o<;x=f8O_-N2GNiEG3~851ND9yJ&~~?B<gFE{DBaeq7k7fxe;|b!02xY@%ad"
    "_N_X_F0SmNn0mdIT5t;0_1McjHIe8?&bG!hfd+Kzrd?_q!g*15@C7s57J@1}rnK*fBuGj&4=nyU*JYLIfcCR1C_nCs%C+t@c"
    "M$Z`6RfobF)HO0(3tp5NGYh`_mqT;*3a#=vc<<eN`~7weemwYJC+%-;!&hx_-Vns<*r+T~-cCkFN%R`@&C1xAgOxJP*Nb8b*"
    "+6g;p@EfnG%Ym6mna%xIzW+IDN=&Y=!eF;BIT2gmI}h~Es+$>6!rXCs#qye(?XgLLCFEvs&y{H`R5Fwy{*a@rRHgpeost%C$"
    "1<@*%=nMBRf4Xr#u4!i7w37sz2&fAIft_fJ(!i2xSGo+4G93SCyH*$QP{3s8k-C;K=s;sc6uZR4gBXXITqS0J}Ulb^Ky7V+%"
    "cIsM}YPg-9wt(3dlX{CHG<`osI}Ekp0P_F>O;$zFe^$<ndJO*6#`nx{crQ?)^GLo`|IHrs1MZDpnt3%BVOMD`Yp@%n=2;nX$"
    "QhDK?r6xMH$-tY1hI}Xq4x!rEgunpt)?v{zm5T<=)x`E*<+SML5t(bs<)uolruqb`PYh3!$Z}O$vIMt7r!a%+QLSv=1og=H4"
    "do0an-3oN~OzzI;TMC^&B@q?BE}p5UR;2$YQI2py!BZ5MrCDy@TWHmqL{p=@!;#abTv?;M3yl9%DS71zoS{LSFu7L#`E#V0F"
    "2j#`!h@=$zA(x*cBrCj2x8+AJo3Z*t+Hi6QQ3Wl^}lIYghrPC>SsO)%!hw&VG#<Q5xS5*v_CH_R;D5*8*;S05N1YbE20LB;`"
    "c4Ue3{a^nxQa)^&gP<Wg&-gB9a*+gVC3oR*03Vw90Qx5EWA)`@%!deR9Cn2d7X7=~sK5IO-jAziLnW8+7q|6&p1)WAujVR`n"
    "{>wrN6BaobiycT9Wh#>&C=&lMz4!tcS_EX8=u2tkds)ZjpgF5Bf%;e268zm;n2d*a%tvY|r2bFTDBDN}7HJTd;gY!B?k$#Yu"
    "j{@K6a<}=ABAz*jOzS!539#desg<_>ndKa_Qan$RV<;M9_INKXM8ZE_?Q~yDyh*#9T)F>`<&MbOUQjB5nRsfof?8ciIfZOWm"
    "%-n@h@xUmezv$0lV)-Q-K5FNG^LYLFK=@NCy8tdGp|IE(pQa(!gk(P~qoI4J(Qhy`KH;Dlf^l&GH~)e)ya}6sZl`W%pL&Gv3"
    "^tW%CxMScjBc2tw$cOfZYb)6T^nw$JKSW}Kpf<yu?y0uUy|pdW3ZRa!{6@Hxk`o_O7O=<5oPGOwmxCG_r00__Qrf*8xckyOs"
    "7reo1OZJFfdprJHAzi<W&Z}hx8SN0w5WxJDj%E34U~oUe8L<du|NE2DmND)q34n>rdRqF|f*}aJE=70&aM%Mm3bD@-pj6Na@"
    "-1)V4H;cTdLwV#BsZvcYgdVK^XFA|m|UjqwfR?pKR5tEJN7_vd=57a@<&)5}rj9JJOZfy2V0q*0_3MnP=3Fz`W!8k0~n1}ql"
    "5KNtb;c0*tt%>6OjixfKrNs;WY!^$VWB_E3?%)PFtrRLcMys!Z1f-o+xEdXNVl4oVtk&A_Zwk7oKPT-$>Wxf)=(FDOX`;yWH"
    "h2r{@e=0{#51@BMT;}4ZCv5NSDE-6EM}d5_%H%VZV;l1rOlZ{5y~IXbW_1vk9Yv7HT9=;JA+YOgv33a9gZdE#we8wdc2Cioo"
    "`E--CRCr$hc@(;cX1P>UEF-e|IWzEK}v9z$tI=EfmUIOem<*Bss26}%pDlLJ-rJRSju6^Ycq~6-+B=N6tJ>LfO&7|yX6yZZQ"
    "Vr!Dp9vUTi}Z06s$(g5r^WmS^2(GGI5;V*5O&!<q^37HVb?cml*+3t;LR^!;LQAYxeSN$uN9q_@JWtt9P!uK+qnx_u=$b-D>"
    "vjhw|C|7n2NDe!y~LJnd&_u$sRhDp?|ORc%Y0{8lv2XofP7ra)-xW}tP2%AcMV@y7(9$LfYz%4w;d?3KRu6nyO;8FKaB<-Qn"
    "5G4?uMjW(m`$VtC_-_3DY9SWv|@qSruz1~sq14aRSPWqS5vEc_ChXcK%B4w~WM3py&@;0xH^j=Rjgg;^W9%S9EdopK4AXn?b"
    "E0lz)!dtp(e~Bpjifz&jAJ~>z18$D)WfU*wH4ub{1u#0vgL4<0z|AjG6JW7BSs(QxS8^PH$$e!OOi7U-?EM&QxsAaIreDfei"
    "X$#;Y9{QKpiGV|InT7M&t6YEEzKPZ`mLCs8*FmRi2u3XL{mknLPF&_s*RagXwr6EYyB7#8o*&QuXqAILnYgzNSObv9_eR5{e"
    "WDWy8q)OPf%r6hs7~jA9L&nS=fx_OTt+sS||W~EY`vRb?lw$(AjO&{s=PNk7|E6qn|yr$!5}VkLZ?%-H4^t#-ypfbEADWW^K"
    "Ir*Hphqdmxe;Ly$IYt~a^9+)a4n$tn2CO$NEq0MG6zu)s!VcK<QpwzGhyqV@xBKda2_GS0Lo&gZ@8tTY5P>pvsMSaZ$uYmr;"
    "Oz$yXvf8_8ez!;8EE|(@0LG|2q%cSZw?98LdoRI=Le?mW<Q2X&EWxkRO@>)t!3vm?7C0$_MEyMXQWOL@E7r15cvQz07Q3T>5"
    "D~dMfO}zYOK%mbuW~eVaBr0oaZlFd6PnRIHM~Qa6kWIPP<EUa6rI651@2nTgXf}8VGNK$^w?f{&`L_5HNo|^GkNvl;G*p-MK"
    "ZvF87loiK4jxW1AiRUSjvO|HLqY?7jQ5xANB=uOOeq?n?)E<~?{ya1niuebA<kqCWCsHNnyEG4=-B=$mT@i>*O%(4jP&59Wm"
    "_d~*~5f|a;zFPcm6Cxxlf$-R~lbIgf3<ZmV_kxbv$jLktv{rSm^ax1KigO!7IeQqhfI%QzqT2+dL=waC_%Bc}PYl;3L<W&P<"
    "{9f7I(Os}3VMHm^&qqv+`Q6=J-v@PEF1&9e+-`6^rSYvX1kx+m{Tg{=0n%aafe?-{FS`SR#x`sGb;>-|3iSbvu)gHtJN>z_i"
    "b&oXkz7lVs4O@ivpoXK?$y4BEq%CPEHd6j7^%~D)WC<qgd;Uswt2L{a96UKDgsku|H-bVg*jGwp%!Nl6q*v~bYV`WMe5+=IY"
    "DN_|z#Rcr|rF+-zT-}*q-`MOuL$1T8q0=z1Q12_8VdGG!QqmjOhdzuD?|)bk^vQ|+WNk)gI6=s-;YLf)l0-3gc#7)v*VO`5T"
    "W{slEFGc~Z()?Ej~3Pgd}=y_$V2<TYC#*Zwet_<i%``hJ`y$gV~az<2_evZjit0bR~s%kKg72gP4FA$Vd&gd=7#XM2)dA6LF"
    "UrHV*`~)E{NNI*Effgg5Jy^EcmgQ9Sy0G^vFnC8v7)IZ;z0)gQ!#y4#V3tNZ7j<nSte}d909NBb3vXua1OI@D;KuB@tH5)X?"
    "0VO2j91`th%RnYDNb-bn2i<zI9z+Apm2p@q9&--U+(R$P85k+TW5rHhKYF!^x)E=~H~YK&E2I7vSLCK5@aAbyeL;FXrB!u^5"
    "yAxJ_J`RLPUXCQSZVViwhnmvZSk!>|q1z8o3ubwT2w1mx@_S{Mp-Cp4nhf<-^@PnR@KrPP;L)8?hK8hR%WM=Cc*b4!>w_}Kw"
    "v79yjm(tAwK2kE@Uo)?9cM1WNXXA<7;nm{w*C#}~_FzVMDWxJf0H`J<=yGmZ$Ta}}8;LyBmy0|82liJl`XGV7BYAeuG#PE>u"
    "f+2=dMfaGeCztvR-A5DKDFb^0sfzOS#s+M#yqph1qL((vCX({xAI=U>O*ea3FPNkHFR(B{;e#@nPITv$5NEKOe!m&-vOP4o1"
    "tpE_W9pWnKuK{Yy-V=^N+N*jE&xS*GS@QXoua5;I#Vh1)wvcX$*aB3Fa6@IoSCzKhwnASkYJSue;8?6n)$7uh~IZhNh<Qf8a"
    "@&_2yvZB?-!u{%oX<4@45fF~s4gTcnG%H4I^eTc$$)*<hC{8X;E@mSa-C2GXoG;^gvrt+HqA&B33oc~@fvpPg?<ya!OW9Om%"
    "aw<r%GMN(qBjAo*AZ3oJDY_c;OTRNjG3a!hyg4_sENNgfSd^zW)j?{%FEo5NMB<4<G|2t$P`Cpm6?x5QcJ!UM^8uIOvhpqYs"
    "J(zize|{<Pk1aH(yo&8W{OGp<8o;?^!^qWz0K=0b<BEa}f=v5L{hvjG&fr0%&+O=+MpC(>y#6jB9~1_l<Uzj#_$3a4u;q8`D"
    "8R(xz;-tzQF6Cvz;ZsC;e1$8zbQB_HK;susJq<jpVswSyzLe3^AdKq=|t1sgSke6pztk_n>s7Ozg2{)Y@3&WWMO$V3Ba<*VS"
    "n|NpY+^*e;XFyNm@_E2sn9M%V&YARnPg7f<Er_Z8afUboND=bMGgQa0n*Q(!GwKS|qA(BH=1~U`;xubNCtTxiXd17Z2m}FF}"
    "ZYra?(B(d>mUAS>5RkeT<9;!s9y<UvomQe*b<??4l0^BmsSyXNMbIE;;9I)h3c5D{vqj{&;fhall)GRnB-kJ5X*B+j?7+WoG"
    "!54SQ+4n}U5P31<9*cHeF9Mq{XpYao;#1IRfQB@%5LB$id;s8X}V6qb31};ZcW%_CcSAutKY=Lcb!}2BKY}74c`*e}Me;lxq"
    "&d!bA>Gf)8;Now=(;B_Qz25))T&VmJp&AdT_Qq^MlfFhQ#88JOY|<6JiNfB%Z8SWg91VR}s)=bHJWgA)eWESX{rVA0M4Sxn-"
    "`fY_1L0r3?X2m^-6bi5zgy%ojBb6a+X7?ok`!n_td{Q&C6NIqE`i_hpcu6l=zibf4`^knS`4Y$qHH}z&_lK4M(%DO5Yc|<t9"
    "L-r-$_N|T!aBSNau-RZduC9#Mk5iN)LHG-cA`c3HW+COru?H6puyr+~E}S+_ABoMni+ooHhlI^)$3-=(9_!{i2)`4~J%gE?Y"
    "TO@PxQ|e{zWOzFXISppo7z;RB7GrafnL-yVg~p0>MCxErfR;XYC}`D<0_5MV5qcsj)Fh&7Op5?F!#1F(YKi47<r+dYHsyOSv"
    "263H?<u@){#1;<$x))9|YtRg{?kGn=dNBv8sMo!ZgdEuA|2)QNDY)p;we(Cf+aBn@c3Osx;TSAT0&F?qh*3sej%U$bm)t>qY"
    "wVoRsuVX1QLpgk8q~7Txz0X3Eg!si&v5x%OM1EME9;rc2Mg`o|s+<JN0}(}MK32*4KDH}{-F0rCVXYqgl9n|j<N$S2R^5o@<"
    "oR7>u1P|yaKXZ2+%<O(ptYAll~_(5+1>Qnum4TI#UHU{PB`8^(}1PEYhB%zwigD)z(|y=`>mdXEBOD0QEf6%TmzUp_l@)%W<"
    "w_Jul##{Xm+RWELw*ngeg)Qujs+^n$Iq8R!t#6%m>Wg)@erBCKJe{EIt&1d6L4A1>a4k(v*Hg+CpkOjtJLrKJcK)=A`5ss?;"
    "u$5zgt)#XHj54FYJ=$v|UR|2HAwtJfukN7!__4LM1ZWaA4bnwF-*=E?5V2@yVVU_vfkzD?Pn5#_PL3+bMtNc_|`qgLN*C3Bc"
    "e9(p^mKIF0$+{)}7v#G@)yu91a-%}4dXM`UhCw<{$&MH<dKmO;dk=qs6+I32m?Kljq^NBxI@EvR6yDX^JNkwMb<<1XIetq#+"
    "gHt#RcrxH=#{6ZWvV7uKX2oS>)X`JATpJasQaR&-mrBVDuz)}_x=9PD(7_Jg{Ek6(#mMx<G`gYL0zJ`!hNkz^Ehg)0w(I7Q!"
    "Q;;(D*#loooGnpYNMK^!6zDNdLG<S$zGY<v7u6iqkZsgercM?p4sqHEe#>TM+zRPfHyHwE!>he?H5sZ|9*2Rv@RY8*M4ZW6p"
    "fF$^uc6A&XVjO+-Zv0!kZB+r0aw^Q^ouJ?jBpLa34jGE!LvrWa~FB;30%h&L=$r2XGI%@a`_3*b{(<@CnLKb!#8~I_p`@1g7"
    "4-oq64sAOUvIb2?1D?BtISWDE&LT+3licfDb{(F8;0(;A;lx%zp`8&4iUo>#p->0T`u?66O8d6z~84|qX4pIErg=sK}Zd>zI"
    "<K@Mc}hbHoz;ncO+`Ck#wdR~mHY`a~O>Ap)XCRdkHW2$K<+_NiI6x=<jD=7SPASS{IduH~t`n#pttf&k4WbV`5qS^chqBYSs"
    "{byIH5>TfM^HX9dY1Qw-wtxg;>pdb7g4^R1u}|0zPt6}@B>2;PdMAu1cb}75Gmeu};QUMt<yfn7DOH?WeAu$`O)$$pP0t%ME"
    "zbqHbS491Z?Ddkp7M-~t=^R0t-h#~FMRv5la#=eHIwmgs|8Y?_pY6<1j7NuteXQL^(6+#^5L=cEC-a}jB@QcZWT%ef)3@fkj"
    "4i*jH-&}SQT9{`w#&V>VUr^x;ax>cK0;0KD|d0@r7k=+7TK-r4kln+l-h9bDV*&^brwAqpJiJQXw|K6K0JPlte-snHJ%0+pb"
    "H}{y68sfLi|rKwcGk96=k=&{WGtENsqYXrVzn3n9*n*N1i_w9_!}2OEA<^R>SO`P*^r-bl3VI)fZ6!o`WT7!q!=o(Bxqh}Oz"
    "wlkX9G)58Pj{jEDie?P63!h5FXNNM|81^5VbGAsAHK;>_$fA?8Gp2Y<ifv8hhz9cPZ6JUwZlQ-Gw3Z#l6#mG}~!;L$Nlvl=F"
    "298`5f}T9La7msNM$g7M>UzANKFmogXZg)Fesyy@@~zlp`z1KL+k~JI1&u}N>snnx1e!L%W)o5`p`jQ#*d~@cJR&i?Drv-x|"
    "2d1Wojq;mR-4o?Ct753^)C6W_rLXDD|}}4AFTUQwBfk0&V2}j!nA*~3SU)kxN!U_gZ6KjNDdHpUTBQttYL2L)!dfF^r~Tdl;"
    "aE{6tYfD!q|3;)x5{uSq_pq`Ss>_hhK(W1^s2p{lboXYq7}sS4rHMc9j2@-rp`(EyerzwwR~%-*irrnr&6F3|5&^iYi8gc2_"
    "=A_04$Pb>f!tznwI7Kd7;|qhoA5Yi~X%KqgbAWp}+?5Pq+kqlUudZ-})kWm5UR150mOYkdW74;cd`G#Z`{^|x#EB#hfdoSD)"
    "Hw}&DtOdc8q51cXrbNZV}0$GL=dO@P%fZ->%RN9D$^CmXQz~=?gTD!Zn^S{t6rcLf1aQ-<1%Q>Z}vXFZIN9l_Pu;{w%+@c~;"
    "`uN!&YGd<sM5Fa#xAAI5e)&EOE}>yv*tNa|C-%V%;*Ft%fevw97QdcTP=}fVO}y+oIEJz7W}LqLylCii5p}+O{O;04aL`X1{"
    "YLm&!r5J~Hbarm8jkUnXt*sYKiUNY&RF^V(8+W=6ZsYq?VRbeB*F;T&3^^;*X5-LW&Ae>mg=v?P@+=Gp9RLz443mQigR%J1a"
    "g-=mpsbUK_a0y<p&KllKc_<9B?;E3$NO7zL1(b*<|0Sr)M<=#VPeudrWJwb7h|2^_OA_>4S@^8skcBIkc<$sn1b&QfU+5lF1"
    ">DH2Uhp4}ffQPcPhP1dkv8Hn>^zuH=nuyu2v+J)VX=FDUVKi;4t3`;>%B8JufJQ(+pj$r-%c$a@Z0Z{JMhw`V+dy=-`29B#2"
    "d9~xM(@WaXLbqH4jdxv<3M5I2wrq%vpwfEgPGwebX>I`WXdc%?5`g9==FC-6<KNEOX@p<9PEJE(A;!UKg&3G+_zKks!@UW=z"
    "N<2O)N7<t)Q^@PYjWv}HFf|-|SMpL_#XCJSGyx{(;LEHL8=c%rv<igt=ux5mdlSEQPDVz%Yx#a-&^(&PDLBYUa6uE`VT__Zj"
    "A6gsThJ&24EpIIRTlF$ZE3YPH?Mx(ghPLPdhB11d3<SRv*#8G@~Rh?)^wCSkEG3#cNpy;HKcthQ8?dMjG6jsTm34?@UK;yv|"
    "uaR=)bis{+NLO7LYwMkMr-MJ2Ixus?g~6Ls#rqnpRoC2_Y%&VVmrRXWyAghklEln+$oS`C(-HJ%5^F`4=HgTn5(q@-T7<T;d"
    "H7o;RY3#Z){cwM&7o>at{fT`(Hj-*<HFjSK?a*Z-wJ7-zyYf}P+wF?jAAJ#$(hiH8D~L3hwy@R4T|k_QoUrxHhw!(-H(EY#-"
    "A^cgW&fsyIpRjY5+Cwj}-jNglbJTtrKItaeLKiWWM6$rW>$=4>xNt)juavJv$I(kSpn~gN)aDy_Rw6)XRYc%K1vJ&%q-;=&U"
    "3A4RLWPJ)HmxkLP{Y@M<%bovsQ%oP9En$jvCH;u#jC3FBuTc^A0a=7B7@DgvyKLNM8<l28%{+UU15ZcTP@U%PF`-I#MDmfdp"
    "dQHx>6Jb}^YbYUu8det^)*8lH?qY)ZCW@ax1W5V6eACH_PjL*veuv`*7W-Y0~UVM$v+?7<spkI291t5?=Mxkkt7G6$5^>}{U"
    "6JG<0|PriwJe3>4A7BPt@gGCAy`6p6FDWID2Hi)Ed>01Cu-2(mOzU3+5=RqPw%SWra!cJrqmzr!vn~1^AnYgG-+P5S8$z5<v"
    "3G(;lVhJ~{BVTi4z1>d^xeaA!Xj@+DDTM?1?V23uwFz_RxodQJaXgxi%B#ASbww{`o&x6!bAy6Zmczj9MHT8o^4YJM@<zeTw"
    "V<74?gj@WeW*&UM&=FrY&{&P)9u{VwLf)eI?SZ;W?n~KVheV{B4fi#ef-k;qAIy%TBuCK3ih!@)euQ-#MxNc2!%skxqS}|<*"
    "yf(D)5h9J+mgoLdBn)KT>nBc>mFX<P`^nU|J*=a&?<AW4U0N^DeXF!yW@)e_I_QV0`qGDH+$EZjFpSI?Jz*_7rRhjgU?sXVU"
    "civ|b$)PgUEY@z{aQauV?J-Ju3U@b$Rnu#I++zEtlz+6oFQYQBJ@{iGh#fc%XTPFse`yNpInN+Y`JXZ9_uDZBIs-vWFW=ikL"
    ";p&DYaUDh7F%MR;~u4smz$~{Km(i*n$YVreV<0D=c7~%=_aiLKkBstOR<yoQ)k0K)_tn)JAFAL6AYS{VQ2=B|ce+hS6Y0ZKm"
    "L)<1D}8Y26RP1$itL`n}&5ui8Y23O^Ou?!0jPaPg}f%ec)Ck|cCk5XC&JblKP1Gx7K0aaOe|F=qb?RrjH0S+u#)d_0zT!q4Q"
    "_Tl{aImbQmdU#5)FB}S9`ys&wG#KCx$CL>1J(R5{+`hUq`m0~7g4Yt_dIaxM0Cv^`Dds<wnvQ+vLWXXTBA`+lt<VkHxO`%or"
    "^8S7tObSR7I77B;J7;S!gdHe^CE{Z1a%At{W^v;gjG1$+Z1H7et5>w_r<4~}Ofd}o#DgAtu@i!x;Z0QR9Uzwjx7m90xQ=m04"
    "C*xs`fm{oF2={DFPp=>g>YlDuy+~?t?$73&{^up8&|{DEDp9wosu>s{11iO@Nk3it`z}a>W;IKoe4It(@I3RZ3HUzYnz#D@r"
    "%&>yI;4#BCLN0Fon}+ZGx`lY{x^QK40%w2Te4f&V0Wbtw>>UVtbI)P<eP@ws)eTkQT^!V3S(Xs8IYy;)jaH<NH3L|1S;l@C}"
    "~$n2W-{pC#ko9$wFN7Ov~Lf*$C!w0hn5)5Y&-q>K?{nR@QfToAOc(<0o=_IsIH8#I1l`^MWcn_;&xlh^U!g@t&Qw;;N6A`$@"
    "iJ4rrgHh`TpHHpfhp-d<D_b`Jsp?6Qm4U_IA^P>2iTe7{S;jQ81GqbI|(m_Aw{v!=3&vKqC=M3-L_te(r9rX%P?M?z<YlM?u"
    "FZ!$LT}4iKdiCf@CZ|}@R#?+NxlL@{qwTifnxG`^?_WK4ZD0zW&Htq^#@%L&f60n{)35yqbD^v#;U5>;H5&yqDi!&wTVY1P^"
    "uQrbsqT2eAT^izQm8~t+gMa(eI%_1!LBmlZwYx36N$CY<I0HyQWHN?8myep<}qDQCe6WRs|$;=MGvAr(tV%#)KJP6#2^k)0Q"
    "N@cKI#TW0sVD3Tf%w<F)_7KbL7vJIMPlo_7^4w{}`s93c3116lgR%LyvlItNB@3ekgpu-_;_~MjJ7UPT3hWP^Ye~SWLu~FHS"
    "kF)xW{gd)UQ06ZU%w+cMt{2(#D_6jz~5QJQ0+8oG{sSGd{VEyTJq4j&7s(vfIj%+EbZRnznuShz5thVw7SORr&3rebE7VK4#"
    "}XWJJntoK<M=YoE<-YoXVp!&b#^G+Ut%oO$H?sBPA2vZr4aMA>mRMxb~BMheq;d6E5zVk|d=Z(dq_cq;=l*uA(r>&*1bw}Ax"
    "Sw*HvaMzJqCW`Q=Y!g&JpZjze&d1k2f%0^`6z1_AV?d5aTEO)Gr;LMv{2y{iZVWzWQX@Q;5Q~@&mux?6%rti#$}Y~n{G6_VZ"
    "s-s`K1iEud*Y<9aa%58drt%T_UG<Pna#zW4#xXDtE);}G0b!myusSRgCHH$!#YzP*S<psXu|q(k){Cfr56wUR`zu%)HF8blP"
    "38OWvaZfldYoVmBGURsC8LN%65j*jVI`~hjy0MoH*~}pWY{4TxVDtf{l0t@+^mKsfmg2r88&S%zBVtOx)n_E9*ZYkaz#x(EE"
    "<%UV^Bqr0MN=X(BZ#^Zvc(&xLHB^zNhDfY>4ci%)cU@E@adn!wsF>Wxb^FOLNLd4axVTk+UEmei@gp!GguyTPMnp-FfHMfIm"
    "D3HyWV7*g9j6~!P>R4U@eT#e%Zfw|Kn99~0La}IRm%^QZwT3x{IQgug<T$jCxO$BbD>9|~UO|o<~nk~ueS$1#w_USVHJ>cd}"
    "mo8O?d`m=dOeI?&3d7bTo{VMKs!@*+H8f}t5%Aw6Vq;UaTne>#c%Wzr!e1)N_&N{0k@D=#r2v)c-DDY$6t;F+3T$c*M?^YlI"
    "T$hII;w$eWT@1{b49CFjVpu{<KKmIsR09wfO9EW?gTghPuDmrsNO^vM^q{#9&zh7eD@3ErK`ZMVuBJW70CD}?mA8s&uuev5D"
    "xuHha-F5+YZLlC1bCV7vg}K0^6iPM?)@F&;qx-cFCsC22R)85LYB7^7;!Rk>7)L*QVjQK`<v@tsEy6OEff)2)jY~GFKCpuHT"
    "t|gTl278DM$h$Ik<=SkZ1oqq{Rt$6R;dGpk%HAsf1Ki_{3DCS*h9Jbe21Oar$3J}GYSVyMIS6|}XuCJea_#^t;1b5;QU$;x|"
    "Yn9kxLvhErj&Ak5$lJJ~RFG%>oyG|^nx^z|MK|HuNxYXaupFKz+LdVD7Z8m<Tx#XPTS@=k6T4<Ao%w+c)r?ouhg>J9QZ<}=~"
    "Fq-YVx%&rcE2fM6_vSIqHQ}i#4i$#DQ<z$lS5Sa8Uhbchm}-VtMnVaiYl(^d!tg+1KvKB0&d`l+pdxC*-&{bhizKxrtIaX3%"
    "}j`us}p7t%z{ZgQ*m;0LJ*(w8H<|N^r-?y#iL73DIMVa-@^;$AQ`GxmTH}l3hDz6U^GFkQ+;BEP9T%jN9c5~d;iTX*`$+Lny"
    "y4^bT$vxL-&HgXBF+bz?!_~W--n$vep|CR+Y#a4~#loz4h?kQ*RU^F#CM_BSO<n*&JIR{22GQ*#Le07Vx$O;dpx#l($AC$&D"
    "ik?nt42AkM*j9K;qYu6Y`7Q1MI7q#1ul1ax9!#);PT((I_r1STx+itr>8djwOi`f2Q(F5@MI^Ytvm0|`V9j1IK$XG~74C!Cq"
    "Zdb-|~kb+(F{I)?h80bDPe;Kwk8VQ}F(PG(3)i3>k%OW*xuNgYOo-I$j1Jx?=eN1q$wOjV&lm8WHwu%;0S|5CqyTDv)Qu3ox"
    "QJI_bGu7sv6F=Y{bd0ubH(}!$Pf3^UNvZeFy|4BZ>^Wp2P04C${kOjz4<tf^ANXO2i}~O1wB?9~^1`vXPELJmkYp5Kj=~``S"
    "uxj}6lH7<ci3b&vV*rznY=zaO~z=0Zd+oGjNpW__+SlIU6do%L9Kd1Ka-j&iUO+q0n;E4+FuXwNDfVG2es|s+y)2md^{6Gy~"
    "$lXqd&deXc0`J=LZ$i^$Km3Rv5t#ASKo?CElt#+??s5M5WEXW$EAM&iIDv+pko_P1-rLXNgNpk(zQ}X5`$ewJ<cE?#QL-k9W"
    "SmUm1eT3SO=Z2kh;JwB`rAOZ_z>k@gBuTL#8V@MWNVyfB4L<+3Wg*W9oDs*nJkf(S^Pm2EX~dwju;!sS}S&41rnS}p<)*fr5"
    "do2JbAChCUV!K<l@uaQWOeanS!!{`G%Eil^6znC2HkMs4lR&#~Sp_qAZEwjC*Jx?ef?2PaFg+4tzsu180pita!H-Cd?TmDOt"
    "eQ5Nhm-mgY(uWz^UzLA>9ilu%enG-1*pf!2iatK3qT3Na^B_3(7}{cK9~3cgm-%rIB0_+oA98?cnwqBqYpN^#EsW9<lUp~~-"
    "xROz&o~=R%k@Z<=H8x%@~Lz*J;Cp?0(K@gF@Uzt(ZT2Qlf;$pdTIXpkErLS0U%ZbJjxP*dM_wL3Hks2LGdDolKSPhyZ>bqKm"
    "pKPX%WMR+s{G$p)+e*>*>fEM@cP-?`Bg4Zsa*J<@$4wCW3X-&g_#B=l#~HD$J+L3}n%;U753epc`-;Ni>yN40SzY9DB`6nYi"
    "BR^~NjB@q^;;$(#~;(vQ?$N~%sC!^3u}|5=za)Sy%FReWC_ICH13DQA-OC$mYmOA!8k<-dRVjQL=t#EvF(m&qNKRrvpzp;3q"
    "#nO`4HnL8V&3MGq!*N4?yV1QgQ$rBBBuYWsVm~E|8i|ZY=tSRkkb?cJN^PJHYgzixhu~#<3emOA;SgY@e?Uj`!$~QT_Hc2xk"
    "x+{ZlPLa5jn-dn234u(_{k9ixxB<di#iDnLbhFbRbqIC~rOo=;Jhdyxw{6cUln)}lS!EDNi3Fnj*AK?HSpPkG1N<V8dLQXOg"
    "jY8@HIGaE`Ol|P&9B&SZAv&>k&=PPEj0nn;n*4#Z}XN=y9kOXEAyy5e{ymAO4BZS0d+#zqtL>qLtoVJkn||tQL(DR0sgt@`4"
    "S#L3n71MAq+>+Pic;}5?MY}v0_*t)UV_|jGohNmsV^VI_M~ejhFQjo@ZOVaU<eU$+E)}4#W**&1x|i81t8Zv}?T4uiD<>U#F"
    "R#?ypvE8ub%!+@IzUr&du@VN(}_v(tWx;i}>6M(%8w)OyoFd(6Z7KU+OFY>ES*001e`AF3tjA^>i}b4?sY?T|r5)#3}?mNfE"
    "j`?SAE7fYzsLrevGJ&P}Ww&)_<>;Ct82lN~mU+l7^PBYdOP-(~sHPWksZhsWBH+(6VyU{8xD!PhpW9lqg*0qF;W(q|v)r{t^"
    "C)4QPN$Leume<V1uL;WK07b77wr7Pw<<^Has;Amd7C(i7LSiC{sS>m}D%BTvP2X=;n;&llD#8}``V3gIJ<{QZKGefC)zz({{"
    "@vHMMpg32$a!Gw$RTn|Qi9b;K7TYCT_s-He;l?Z?cs@@M|bSEvb-h-C6y0%YTlTkj0S8`IUXf|SPM#c^LaFtIPD|gc31y4Js"
    "YU;E(#(x2{on=t6qt?Yn5K2FQ}rhSuUQPQbPSHUGtOmEGa`EtDQ>^L4!Xhq2KrY#aaI_s`nYKa#GKfTV8W>sRlj_-u273J;g"
    "2Xc$UYiwLVNxA*}v8b+@|^z&L2~0mUPB%EOa*!fnj#2KGSMJnmK*=}UoGb+C>ohw0+vzq>nZvtU3z+RYvB{`Lxi&H>h;6Dp_"
    "as-nY_)Qr|8ZS092#L$xH%*NCha!t<D+QQRA7ztx7rV&L*LP$<l^8Q_8I%7obC}+mBG$$5YHQznnVgOfKyR#e}12ctsbZ<`^"
    "HzIK>jnqi9bGgarCy;4{DFPS9Dwq9)ILq=XNEY$aPYKK0Pf-2Tv&Qy5=Q`}hjeOvC!UJrg-1u$%ambYC#z*nlCIgLF@M8&ZX"
    "U<dyK+mqVRUWV|fV4GR9iQ=&Ney%orC>s03Zf9vAtW{|xABkQui5M*Q;wL<?{M)0@HYwWLFv$sn;!76MCs*?2#~#}U1pm9(c"
    "3jo0h@oVi=l=Vp%#Kln!1O@z3ss?Fa*Wha3QNI9n3A7fjThdd8p?{6~o*G{~QLsd+Zq)@qL$B64yMc<(As$wW?liMIHG{!@*"
    "TvKg*i)!}lcQ=sKXahs10qK>szH#@7)=PGI1BbehGOX}Ns#&dv#&<Jh$f6A;p^8H+oqignUE;}U{d8*|5c7v8nDWvhkYU;*b"
    "(xr+PgQ{osWRyzSTMTo8ixrOb{L%@Z%wFyU@KPfh^3;uKk4Nj)2j;x;sxx;Lg`sUqvCAaw!F>(z8s8!|S#L#5|mrlEN4~~3F"
    "PaNZGbV0b{&{GW}M{~DWw7J-o>d6%=<ApoT%lka?H-RQjU7BX|$nU?3sy~W=DURgfxejauZl&+oYrN&s>~qF=w#24Qc9^r^q"
    "Z63@V8urrAue@mqObg{NEdVFB*jz2II{aJX71$HlTxe}R#ci+g<NMuP>GZDl}$vEAG(B0>uluco05UV9O8qpsK1N+{cmi*-7"
    "WW^%*~EHlw@yBXCg{!IAdz`eV~;N)s@M-zgX|RWsmG8$JnbU7}dC#Rf|1FROyc>vEsdeG?+ooye9wF);@3=R}h>5+12lTF%}"
    "sq;S#*F+kzkXo&U2W7jWfyLEm=Lady9+6aaZ;7AMt}YEd1o4Q-?QLq&dMRtJ+|d8HHqL&E>eljqbfSvCHB6>hhq?c1uEE>Pt"
    "$-rdFE+pyzE1E7vMVBV1}dc?E>Z3?!r(}R}b--O(mr+>rruej4Hh|bajSsQ|6REip<)p8FQn2!rntK&<UmgCAK16s2jGn3-9"
    "Em`l5*?q7p_-&ZY(wCZwYI@>Uvf#Evadv?8XW>zFt6l9eS_)LK?_MahTnX*sl`O+hZN1j0ZmG1;s(WF+=Se`Uq?!f7&s`j!d"
    "2YSV8`y|G(&bEc!4B{LUvCur*Be0jOb(eCRMcZ-X-l+t7!bv_C-{KhcvA#<5tD5ZS-w3|4XJ(?(VT5wpD(=pTVqGj<)wZnge"
    "10fPV7smgG}+|eKSb5^wOiZ5b;`7FM)V_o^<xRpSw2-APFi$dLnV?LE4=0ti&|-XS3PnG05|6?tX7g&=8AFUUc};Ay8O<<X!"
    "+8M+KD<-aBhM8z=kMz`X|z<I$hAo@`fTb)VC6{w}BD)lSqA*eE`;$`}}dC1OQ-E#%ji&dsTe(mb@*&EdVR7tHEnfV)FD{6zn"
    "Qjn39@O(x@^c(FlNjW~Z4HBqYaZ60)jW%78}>PrH@Xk<Y7s_t{Nn|WKu*)ugdJlme0x>;Bx>=4P6js11Iaa$T0#^a5NZByRz"
    "`t<Yck2A%)$BCnsQ1M9Yy|sHW!BnWL&SyfVtlseGqWv%lg3YFY)4!jLwOi(Pc{~h*t)tS*>uj~n-`Q&<@Wr`PqjH`)AVPCEW"
    "|*mwu2JF}m{f1fK7LIAgJQCRhvP^2kf;A6>MNt_YMN$o2?2sT1b2r(aCdiicXv%7xVs+Q-QC^Y;o$Br2e`@eerw(NGyi+0tE"
    ";AW*Y2A3P#AK@yScz$oYLf3FuA!&dXhXtlN3k8gBhCe`j<Y`W{UsP2O8lPag0ILb-5(c6m`A_i_P89aarduF^4|XQVyRczkk"
    "3GdOA4rUgHl2i(j;Y%y9woX49xCf(*L2BmU2x(LmYgHF!0f6X8sJ;AyXoE=8!TqIvpiw#&g1L_mSF8v#d&ILfJaI+x0FyZeD"
    "t7V}#Fi<djYCif@Z`%ACsF`2O{k!MTuQSA|688AF`PL+5(p<xT-rsTb~i}h{I30;0<z{w#x^g@H%Y@FDWZIAg!b;N=HWAV(-"
    "5PQ(^8|YxUn_;heqRW(%!or=NoK&h%>LiQN3*7(Zb-C9A$L@_c!_SE|EmsjY4_kk%Q*{%se`(dPH)>wN(Tj;UNi-W*JpDtb1"
    "UYWqdF5S2;>;20zR6<wW5IrKj#TsDWuaehT`E+igfdVfLygWX*A1<Zj3mL*sPBgQ2gi*APcP$8`-^L9$@qH`Y*k8rv5SSw2N"
    "$nAM%|Ack0eia|1_*@M?wxgH~7g(L?$knGmiPE<GskI$GHC7?Urv)oL=dYwv&LZaeeKl!Dsn~-wH+3Wl;R__@9aVzX^A#j6e"
    "3<w6GhM?bFx1iO{|?KxFHFcf2L@L*T7nfA)CF2X*iWCElG-!<u!nVt)<6udn&%+8qC)QHEGp4pC*3-9LXwpXW)EqpQhA4!`)"
    "}x4|@2-3XPqi;5#(H^ZX9O_DOI99FJO`f25x>7<gtGVSHSgJBXutlp6ima}<v;B9^zt3gX5k(FbO(>5xz#gJR;H3rcW&95G^"
    "=)SG+0CvRyNiFC{HnqA-92*MuEmk9!&tW*aKj^4dmOS&N56iIgR8{8Q_NcD;9R*p{dMXB{Us0^?Bf|E1#T(c!I^BWa=B@b_C"
    "XZUJBQM=3C0%jdh>}@BVEL%dJ#;oojtY1AiuJ6*a=kQ*4z_>QaCk?2mLsEr!YteYI$(L3cjL`aGW}JN)O+Kkk|@0~GqS`<mc"
    "|kC_6qyF)q_iz#OIH<hUHpkC;UnL@@5CKc=)Q4C(s-lM!Y9I&6#06%?I#wJ`$8?ytgqkdDr^W^bo6#Bx@&jh#VheNK>UzN=I"
    "tlR&h0VS^&M7{w>z*K@?1)eDYRNOZR(oSWW3tkfC|{GqnUl=!UZZ#`ujRbq?+t_5{bx*&GuQp{{YH{9o>DIEY{H&o5=PugL5"
    "mGU}AH&P2CBblYaTZP47QNjIlbqnA-#aS@(}n*eZdDu70_7>~YnY6UiWc1EYxS?pVE^Pw^%P7D27*EZR+&rT`r;_efzl&8&c"
    "vBvD4Qb!3J=nD__aCR;Yw&F;)8~xN-{RSj@RR6w`1@=9}oEmcJ7d&%Q;*6Hja8fz~OqKNL_^pZ3K^oEf_e_62{paK1mm_;$V"
    "KbwQ&T$8o*d8bJ3O9viy6oYU&zE<NV6m19WFF83(Tpbi4F!e8x8V=60Te)Nx}c6md61*4n8y>umLn<HLL}cAj;$wyQ(Crd^)"
    "SYY7lZ`rIM+cSP$1DZr<r^l5;0t!|AvW_WMV9<aesx$>3HasK6^1&$``U>VQomSWtXms^GHWdj|mF~#-Rz3sn!y$b2CF>kwx"
    "z-^ty1_PgIQEomfW}D9IXqhyb4vt3%2YZ<Hmd0F|<a8*6eRqx+J#&jVmk(stVqM-#=72Ikb!nzs5d`HEKY3?j94tyNAJ3kt%"
    "2V=_~zga3H+vWpo@S+~}r^{QmfA=uFv{!yzr6J-iHk;+ZDX%@7T80Cm2yLJ(o7<qh(w7Bi4jn|265@fmu(ujp13S1Esm?d&7"
    "<kdo5+F|v<k`j3A@$cORqO-J_+sdhX-e8m04>+(!SP!YI#rwCd?l<7)+ZtZ`m0&VZX!1a(`{yn&)=c`q{hKC3;6;t9)GtPFT"
    "-uLag0_y=)8+0!ap^sqWnXld{y5XXy>ch~V`}p5=WhS$x;wzov3hrJ6A&oBE|CUvLmCFb5}oKh?h)xiS4wzOr2X55XVXZ<{f"
    "3{DboTe2fvn8Docnu<4fQ4hBXK>P2g}+_I03{s#XNfm@wlOO#q+@<;>H9vo{8>+`7w2&^;52ar+P-X_z;yE>HC}Kq~_7>Ika"
    "?(Nv~3<aY-a|gA;ku<fcc`mjk7^KQ?0Wx}o71Hja<-g@zD$rK1$>C}5}6{$AbzGH^K*U?X2~SLH>Z9`Cs*ar{F!7syoIk~w8"
    "YUJ*6y0^?S*e5~$_L3A`$h9-3Ef^62Ay#}0g61x-s9LBXzdp|dX5>U~4DwE<Pqjs||hh1QfhZ58r>Hy}3-x)Uf+{j7dM!^*|"
    "r=5}^TZJpiUk`d10LsqvKPw`_3_8U**msna*kgYj8&Q_R<z(eFa>nu%x500j+zF&#O2>ed6X55WgF+nVmM(w2_cPmF_mrd&%"
    "kgC`(6@hRZn-*c>#fZ689(vCJ@G@S^JL)Zc_7kuf6!|QB4$9=?S!IPGT%%C-tm*OJYj?ZujptoRr!W*-=kJcjDpWvf@)Ls*9"
    "J&vq_|Nq?MRaSOKC@<X$NjXJ1{kW7G_b-`Pal@a?i0VBM|rne%If2TsAC3yIXvSsl#vySl^f(T?_n8`-JtoJJNoZh^l;E47y"
    "X;YqERf!DD?~e+nd%EgB4ijZf}(4?pDH);J1?$ArR5@1Rp77ZQcfzTZ7lPYlN;S-Z5J*sWSLaLQ0YmoTv}RgYa%Got^tEDC+"
    "Wlh8Z%Bd($GZe{?iSzPpnlQ`i9r!sx(-vIXWf0G5NC@xsa#rsIhs(5)L@k*O&+w<1ywF+Yb+K0}D%R;w%<aH=)BGBh^P<r?$"
    "GQOE325t92W)WxgQ)^c)V2R)LVV{h^k}w08Za-g#EkDhFsr1M_jZ_hVPJ6rYzmb1kF*Mo%=XxN5dsqrES;OwnC;m#6MVsJ0x"
    "nvZ|P_THVss$h0tRog8emwT#@_CDS$oHnC_qu!bys+F|7?BbZ^UV4q^Eh!&gnLBaf64RuS*mH%7deZ3@LY&=u+~qfI*kf{xZ"
    "a24{VC~7D5^#g@24esKxohjuCn#~PozOGT|#~B<=ymnY9ty$LJW>!4{6qndO`s3`aAM3q>neNTBpwdjSm8R=M03%Xw1S1eGF"
    "7i){LD8b^YObIZZ(|8MvV#s?8@bWBICK976I8k%lqnB+0LfG-^7F#Qvvxv0Qh>X4SVe1<L&CJ{6l)i(2ee&CbWxi$S~T_&L0"
    "$MIfzx{a+Q@2{5&O*^1+a8_h3ELya~GPoh;?i;sc-45U~7cMytSMNTG6r~wl{OZZAbP<%h?k`Ci4b<R1QS9j+%@M#WdERaZi"
    "V<YxrslF(NO`NECpoWH<3sjyfN86wtkEhAQzOqABv{n1^`cx4;D^XtETPJarb_b+8fdTcALf~q+k3Khfr*^(d&4qpOVlc2Jo"
    "%`wUSzq9%(d{2tHgkA%Q^st4<r&+Gyea<{d~}Od?T`2gDy*J^u^LeU$BzDfYyYsAqTio4wW{Lx&dNnrUo8}lMv7i1Ys3`)$1"
    "56Ev4nM}3zV=VXqc{=%%uEjNkBWu2`i93D%W{_mgdCV?wlAQpFC?5__prD_wfwLRnE)6M^9gGP;eDMR8OG(!nvQGk&1mmiBE"
    "5({y870uH(o)-F9q=e(TvMuFlft23gpc;XpYwI*P4y;h{jTNYd5987(Sy%3OdhP}q%8Iu$#^Pf{cTy}b60vbv`Etx7da)YUw"
    "B)Um$troIu_rZb-8kKm;H@}xjz;Ocr)9_VUQDv$WjE0*+sA7?}sic`FTzf>Wy&+rS_L-6)exmR~Z)Q>pK*VUiEq2U&|aD+OH"
    "o1RNS_kl@^!Du1H(UVtNt_>~CLy*bHPS)Rpj@B#{o~p0V8J9!gPWKFzSaDRiAL9t+P_|d7pMVHzl_nl_bX=1Oqi=f=$O24)q"
    "?%gB9w1o$!+V73qo``XpMaM!^)$}(i}^oj;m&fpc|R)GdVCPFoiAHwI<o>Pv&mQ$DUQr*Y$P|-t_kE}`xdEYT20j#zY3T>OH"
    "_imC&7rWK0W4Z)G|uOUJJ%E@e{KQ`xs}I6=r%raZkeBb-V^IF2Dc!Y_$`ce7u!O3>l4nw4Ps<+eVyji#(J68B*jK0Z-%^5Jj"
    "uryUjFp4L2z$q$bu|R_0gbNh_=>nn+{HVi!#o4-ADmoSXVySG_=1m}H<yDIQx;RFFWgJ<nIXi0oK-QBJs33=vbw5!@zOzEQ3"
    "gFlTL%FTf0N#ctMZ;tmHO+0JIe(U=Rrczn7W{w)HqkzoHk1$nH!U@1rqhwl~-nGEn${n{@H4<Q(}9SO}FnwZ=>0yPid{Ec)F"
    "zz-aRkQ?jj8JhCpq%c@8_dC7@5wqxhhl6BkDwhvlEGZ)>uw51xedssdq#Ey&I~BAG$N&0N1bKdy+Qn;n`Q-Zc`~4*_4<XkYX"
    "ZHSWK`u_RRs?C>Ndn2i_GC(xZ3PJuxhhEe>d%qR7yxu~_B<@_gX3sS#8c&5`e!dNM9r?IU;)Ia_iBWx`}mcD?+!XMjK=dIE{"
    "Ft5i!55WV!UhKfBvL<ml~DZwJOp7b&i5f7iwb@xHg5sIbTic&p)s25&eaRBIAZyZG1)Tk48|8PIP4@bXUs(G4<1O+NUD?2l6"
    "kBh{Lj6*-a=#RWU{<7{2MBdl1=Azi3AeeU1r>K=}X*K??n<_#~k`&Y?QA`y6#$MX10>H%BTBXk7~vYvj~>-{gvJF~6TIwStl"
    "_{#v!FpS+8kpU})Pi?l75Px7L%Z4h)20ilB=FCy%My^BSmBvxKpu{F;0U(IywfK8GqALCzx0&l0BP5wD=UmN_JadZ%><=vRo"
    "v4mO>SLe;~h0u%D9|^8MWS+Jzn6wf~`a)L742qQYG=c(7A1kOLb#&n$qXt`Rw?zLYg|8W@j6#utwFyIT@iIw-+);V7C@VG4N"
    "9~!Q;MFL;617TJ1(YgaG1=HG=VGhW&@k&ZNdsg2dn*v+j#N21Vyi!<n^%}ri1%{agh?T=k&w-^edA9(jp(IqJq{xDA!2x^(%"
    "&vk6`}k{$oEQ_E!Gh9GjLfdRXVn4`CqPd@D48C9M8c0b>UL=;2YY1WRpt1z8cXivPAD0w`%IpPAlXFK1}|+T-8GOKvu{^``z"
    "t1Y5O$>DbD7!2%*Kp4R4zJ;A@p$%P%2utglf_O-|&SG5lftN_n)k)CMSnaYz&7SB$Fab3=ve)%U#1ATgKnSruq?f{SPVi?i1"
    "&%NRd;u4nlu{dsES?NXPv$cq(`S|7P1NQri+u|neIUN=Tz`KbdeUc5$XqrJ=@Fl~cfOaClN`2YPA>MJE%l&&+*<&`O0*s9Lj"
    "#PScjL)7lzBYOVd(0bXJ>wU;VU)Z+ISrw?yY~nITza@^F?9X7GMY|EyoZ7?}O0Y20%HYYs!W>5eGRhztg*$XUx1G+pVd1#-{"
    "bcgr%+6NlxGafnUsZ*IV>2%dTM0FFv@Yo6`K~$ZFFO!EUyp8<{qMy=58Zyh0>7zESSgpk{)zsLWyiVYalg~J1fg){F>d``-{"
    "8Ee{d$PvIw>S&#S1rdzr_@kg~Wtra_c*(CMUH$FH?K(zZ~3CEM$e>QV!?PfWo|hMcPh9tn{Pm0HvwnE^gRAU;2}mA6f8(8hB"
    "M##enhnILE^^z_We&Q@Uk46N65d4-kAo&!m*+vRsX=*_mXLCqpb}ajgSd$-`HJFUZiVyH2hII;VBTs-YK>2yBKbc4st((Q~V"
    "qEmAfvFl=bftP(Vqecr#G(1D@ie3tMUpz16SNAc=(_c&zcBu^ZsloQT&e)<iW3pZ=F|MMj2|F3NxWaeuBwBIT>QPxna!_=o6"
    "v)SvkP3}CkpO`Ghh5JP#-&mtoR#_P<X$~8wI;Y<AFCjEE^$LjWliJnb7PMBTqUKLJH>ea+;cIV0cRf|`?{KQ=mFN^`BV3b-T"
    "N3q<OO_Za)2zx)s|+{&VmDEy4@$={2lU=eb;kk#&RqPy$BunrVZZ%&|4JI28kbt!t(G_jXvU65u9dbhO8f38XpLt{E3mT4y?"
    "uLa|BPe8D@n+ibi-qnK#zA|r-Y8T_!y}8>wz0Ocr>)lcrj|wwuvMQbe?AY%k1g!F$Sxe=a@Y6^HqcH0U65u;~3Wj24a?u_u;"
    "Be1BfiMBV=JFX2X?3xO^$cOWcx9la2Fd4L(g0$sW}6Ex?1N1<9~bYkWhV-KZe19OPHDY%0U-D^vbxpQiSxZyo~7sJoZwZA00"
    "<PmcL6sht}CIlblIqv@8loOS#;kU^ua?kbXxhw~kx7wQ+v#CLcxNitEXJc-eGa!upu<JD|)?`**PkbUMwt(dWPoeAygSb;=1"
    "I+{cPc-Tnp>`(Ut9oK$IZ$IGHk;-OS6%rViitEK<OG#PA75tl@p|3S{2%93*0TQOjLwEVu)*(-fDQjQscj=3b?%?3T!eDwZj"
    "lZiQSFLmhhOpSo{Nd{vg77p89B5#%+3BcBu&DvvQrOZu&}(TyvU`uBMN?`!{5-|OaM+8dXBK^)#{$c%raV&KjnA9r$8W|)yc"
    "XQGgx}Je1U?7V)<TB|zMPJ5u`OH0go`H*W6yRHiG>S1fUu*-K4bZQ*vmcRD-T$p=c(t=DGIlD+hXlWTH`EXV+)DH^9;%l@Xv"
    "kwkB$bbw2sep8%N%zMB%ztGr1s+;Yt8tzU@tWX7uj`sU3G_Qx-7mjUegq3iiofaZFWa);+*QXvCf7M(i3Wk*ijhu2Rn%c2%X"
    "P%lCmj#5zXJ;M<nvg#>Mc@bx`Pg)vMApI9yg8p{xIkKK==xx5mxHwRs{mZ<1pp=a5Jo~20CC90vviKb<@bJ)?t#7`i=_N+9~"
    "D5*|dHg~QYZRulyC#y9s@+-z&;vvktjgSUkAGCI1vS!7gk>FG4h8#}Wf<BCab4{Uw?pVX-k-?S0{{sK({{p|`VceTrd;dgML"
    "VQ!h_lmy^_T;KNT*;fU>bPk3ON@ZuYG)8$4?jOoq8<D>Iw%c?CW2j9KqL<nQehL3&By?&F3!ExvX?Oi(cqUEX*W433WW;e4{"
    "2H}6s10ApF}4(pO~_<IiLme{a|(d!xFdWoA=gu2$5G1zt1x>Z@i(QV{VQ2T~1j{q?5Nj@>SPSmcubNtp79ia+8+Gq$W?X6y1"
    "^6Rv{Lq!0hUBmcRNJUlwP(Y<bF0PxGJJMP9XBYe%5<_78L1_twM_{1gqr#x?PAL`xTy=LAUPv%HgM&yH$6h2Mf{Et<uURPgJ"
    "0^&#>d4}^BWhOlh9{;aIPFvp?C3rZY70TzJ8G+qLV9~FY*JGIgsT`mT#5&7$D-mX50?7U8j;A7b8l5`vCVY(5Tb!+kux-XxV"
    "9zbcpMB>kTdn0-ci!_U&fC`f|GbT|>Asl&aQVKbV7F$|<F28_cQ(v^DG}#Y&IyweO8}OdKzP??$R2XrQbdfI0FPxm-0b8q(8"
    "$z&8x~>G;yvNmUGxTwXku9(d4s%fP$xE<Im<ogSX$C;5?TBxSgPZq9Qr{TtXAMg482xr{)e1aFx~;73bjJLkfsAoKPDNN0;;"
    "`GR==FMfu^!{zZvZv#pLfX5waC7q{C>~Or}Sq9wvIbBOzf3M8~mRyfZ#5_I!3>w%M&g^e3U=L4=T;KQO)i6&0Y(X^O8p-Njl"
    "p5X(ozn0{bmf4~I8Fye@>+JyxTiS^-B;WPUv|+qa+zsOebA-o!2X-!e#m)mwY_qa3NjA_r|($D3`^3^&KCtm=dG%8cX6;F4O"
    "yA|%2AJU}k{k3fKFVq(7ykGSN=i)ws9DUM*BzmlPvg{FT>9olYTI9t?>srK2s(bBfjSK&+TMEwpURlUK!2bph%g8kd^5HZaa"
    "_y&(L)I6zsf>Ic}$uqL`bEBza&*M7J)y6eMVw4OcT{VA~2XzfJ7y<%9#9faAA=*>`>Q0gJ#NF;qaf>FGdWPM0Q6T;OOP0&hx"
    "C@7I=F3lrq-~mMvL>?ejrzuAUpWHZbZ%Wjx5I<q^ND2<1-YGPcHv*7b^FI>348`2OueFi^iS#tZ^|m|w&XSok)JQ{ofY8d#m"
    "{2>>A3C>S^Zc+>v(0aKFn&~oJh&u>_1eJjB3!brj)MJNLkUTqF&V5uA<LqwLNn4*ztVizlP*GMIo;iK`o}5o)@zByS&Xs>)O"
    "o|2cIaB4=f!0yvzRtjKf?D{RBt9G8+YUd2~V)l_;hzU^qW$9-?}Z54~|c_rJ%S7Pv_ey8YSz9Qxo>1*8rD@Cv_lbS(|acU}-"
    "~HJ*vpss+{({~_8O2CaPCWFcc_mlmfuD~Nq0D3gPqW}FQ-wk<xQX10|5CW(>uvi$aaR;qk0S~XEK{E5~&6y2x*`}-bNIfh>H"
    "($2vhsC5UpE2e1#i~T5gGY^N1YYx8p7Dbk)bQ-J0L{p(~b-MilIekhp>gd_>zZ5|GzZ4)h_z@Gq&E39$;9QRn-Sx98Ch*30W"
    "3x7i1L=JGj}z?s0ZW$TujU#7_Ap1E&<thHY#~n^Nqn?#hf)hhI<`9f5mSkQC|HR|>bYw4y%h>k2YjNGiZxm+4ma(=mzw%VHq"
    "e2EC)zJ0@u92ZSG4?hY3n{P%f#O!NO-jrzYpYd%?F?rZx30&47_bkJ^?oSRmultwP6<{g!7x=3~uV;*s&TOHW-0#eogkkzMI"
    "cy{bLOcgP!U*au#vDJ}ejkX5sAeH|{AVC(G!4^0Jn=kHjg@DJU&sh2_W7BOZT7kz4yM{hPOVf?~|Zgr^)<YsDIO%~+w#J;k!"
    "bFic#pCf)E1O?51PzulkNtb?<vj^k5VR-hGTP?%&DMCJKsZF5(ceAj#BP`tfO`gxC@*b@;+MpmJ`X^^9oBr9d4Q#S*gR0=<)"
    "SyJ*62YlCY>2WhHd`m?BvQlUS7MAu<(?bDoul`1tr=zflHngB(=tQIHK(b1GqSJ464s{pyLipN%hx-o+lkbA99?xF3NTqY(z"
    "MyQqKRSTXy78yf!@@U`e?>w^V+A7MU)31zxoJJ<lSN}8Vd5VUz7yVn@VR_^s_jQU$+Dlp#m(KQKuatexcQYWTd7h`<{B3~Mh"
    "SGTrC~&tTjvgn2VreCKVq?qshtr?Z*sa1x{g;)Pk<Vh4wo9v1Sz+#)w_l+x$Sqdp1Lx;yKm^bJ|+mGk+ahLYz!S4Hd>sU)4A"
    "MIt)*4B?k?SX1N$40@bkF1#Svnra$?xzZd^!OCIqI)8U~qtVBVh>qo1T>WUw&Fd)--x$1|Rc4|h#F<4m+F&ROy}bJZ>knly_"
    "Q?G+Kn8dze~8i$CJt|g2GX+KkFkwOKmqP45r<g)(a_F=8@IgH({&zAGi#m3zl_p09>VvRZDY~b&&7yL3@Kc&TYXA1HARxApz"
    ">letef_HtfsG!uKF9_a~BB^zQsFxC&-s?-26(VhpNh(^m?(ZApBf3Vom8#Go3$EjE)B@3B%OW|^WFb<V6ey&F3&`ZY5!W(dm"
    "1SkR=)`ZXzuZR1pZu!TM#^c`$oq$6E&Kl=S;TzJs&f(%Os0(n&BKe4!8}FL@NlDFj*RQ2@8Ma;(Ahq#dq<qLciS~3>xP=pb`"
    "X@HfU)798EVG4KM0|D9>ln60#7IiYo(VTSb{d(u-jw(s}<8i2Qvge&;1RFAd&e+hUG!nM4rpu&zG#;$G5rm<2hVDeRW`TdR&"
    "i$+~?;I4=>ZcUz%*qZaF?!@d@&q*F;lO3%W&rqxRm$Z=_-DE#WJn46_c9@|?ue!rg9YVT-LTDHL}S)}kYjwDNw3lX^}YPCRq"
    "0$R9|FzF5|Kyq$?BnvpJO<EEvXV3&v{GQe`c1Lyx}a(8%(YF}-2hK-bEdc*Rc?3<z1LQ^gYrpT(27o~c2RPNSWrAH~%u<v6t"
    "|3J46xIDIAjlHAKK^Oh)rYK5HmujA9YslAJ>zr8nvD<2jFrX!&U_~BHfg6ex#$#MSQmKqe15m?FfQuM)c4UPWZ&EHD6OxY_I"
    "@J5P+k3jBifc-z_wEDL{TKFeSZ%Psr=T&=q*W3h9NNW}KWh>8o`uWXP8cs5?Yp<<#cf-eq{?c?Lewk6HJnY^HOk-mV%t&1CB"
    "X@GV<Xb4L@WYz7A|YeWp}F_p%mui!RJ|4P2bXQ8w_?=LhFCjfCau*J<qmLBC4;k+giOjjR$nVvVT7g@mxplng;N_Lfs`p8{D"
    "usj28*AbMTG15%Ku|VYfq&nLjr8V6s?pv%O=&;yugsG+8~D7za89yw;7>DFOY9=+Av&{Tuyco8TB)k|Lv}ziusys1@ZoU}^Y"
    "(Mr!35I`z&0az16w!UfKVwny#+3;>@qZVw=0^9*wf&Y$RcpKanIWP-w<EYVoaB~(=0;DSZhb1E&ouaPN1?Z+Qj@NG-C?E#_~"
    "`RlPK1^Rl!w)O9{Ed(rZ-yfsIIC7}OtSrUL7Lg9|5U7%rkZ8O>ImFO;QaHuMDT>oOu~>KQG5!&}IRvOfCNEkVEe=F||Ehy&4"
    "<;BL9UYsS3WTc>v6CIxL#sA$AST;8(OlF(@;(9-t1RhKc$AI>C5$jRc!3@muW&_l?iu@e@@Ls$+JN6MU)0(!P^mGcf*~BjcF"
    "8>&-iIK~Rkc+$$EB!_JXaus917{aAbbd6c;^iGTmPL70D76eP7(+7$Qo*EC>4{88`X09M@GlY!Ga?6-!Ux6y#@+M6&E%FO16"
    "5OO@_3m<R!hAuOv%dMdrv2`EgiLUEd0|jQ>>Q8x=N0>57`XW&RC@;LPl_Me6`o%q6?tV`IQgF7s(^)6;xk3ID^Eck9I=-s-|"
    "CcrnFJ;1wzWmpl!77@%z+T_{9TMc7uKeL~izAQSuat&n-l6)V9X(zsM361D?1JlGQ{MIiojBYl>tN}!;*e-0Pls?eV|$i$C}"
    "u=I#&Gg84$Kzt>Pk46h8>C(>3n|nn(p*n`(;LRD$3vYCGZh5wUq(g#S>mRi1{Ri#Px;brQrZBj*UYn}i9#;>|*F(|ZA20p>r"
    "C4DvWV@=mzNas%qYrpDdN7fAOC?s+&y~LN*K5mu0ohY>eMRD(e4?V1Xl6q$wcm2cRyhJKW-qi%!1wRUj+T(SoodoE0(B@i+v"
    "1Pn8%dgW>W^skj}DQ$(%LWmcmaM#>o0e2L<Vm3&NcK)_^&$Zt|mD4?N+Szeizm|v%{(0H{W>`!!x*4Ky`*^CNpE{&vKrPfp@"
    "OKB)Q3lP3T}y!P_NdKsyTOOQU9Wib;Ib=HIVPd|j=do_aaaHYo1IOMO1}=jS^|KySwCGlCf;ss=4Oo;SKmQc4NA==lV$!~_w"
    "EhnW$VYW)G&Mu<SP<GgT<LmXzldR+u}=$Dhj=&~V?>5ik6_7~YcdmW9h>thwPVdz5l8p)1`*P>8NXzfG4=yMxV4U)YQ`@e)m"
    "N(2#GenWi-ns7<>^sox;#^xR{+#~ES3M4F|G)rq3{U>~J1OL-s$C685s?<9D-lMaa*!tM*!u}HS?rE%Sk5r(?F1XyJoRqt`Y"
    "~@kYvT2XW*2oo@E19K}u{tbGG!-nn%G_LoQd%#@1Jwniu7=$#gOsV?sgR&{fM4NJbNLH^QLk7@0=2SP_W?p|h{BTRgDokG`z"
    "1-<|4;SSCm3m5q^5>OCLV`=r*sqnFUb*g_oFjE!k%#^=+OPxl0rrICexu2x^Tj`m;^?hCT?(C+-V7I-<C3)nk77^NUp42$A("
    "S5!g#qiWxt7hj4VFcTck6~r`0dKTgBN+_7r?e4|kuH=ozft9ZA7@0bWeZ&?NFic{r7TkV1vp@Qdup{dm0x@t7->w`sgt0!$q"
    "emzHv`Gvqs;3H<_uk5)#GgE(`<Nxbfk6k@;~ebgB4*_@MZ$Hc51<Pi1u$%v{UbVVK1AZX$}F|j8gI)x6b4<nfamt;RGYa@%e"
    "G&Ax<=DxOY@k$0aNg_mvT3H9v58H0mzw~nn{XhCCByyH%TbaBh-c>X=n7m?a_-S}}Xzn@ObaB7+hVpS$?H?vA1&^W<OhAq_t"
    "!?!nEr|BKSKK`fY(LZ6XoX2KgOFOtC)iw7sw$2E(@J{#x~mra0L&v5*y?PbtDX4lkVWeuUnFRwvz^2E!*dJkKgPQZ9O*gJAE"
    ")GZBKia|c01t!8wb7mj!P3%0-m<K5IA(b=_{}NVorQvTctdqSe7f%nVEC-&G;%4D427bZgc=MO<qn&jr8Bsj~QeFbW+(8L^2"
    "bl6pV-!*=We4-<bVfcT?4vP9Xeti`4I0+kv8$#jq5AQh9v>g7YaIiYUU4j*bz?qSV%4RNbdoHGwR<oD|U+iCJGvoAVyfML^S"
    "|k%A>uC+*Rx=k(0E;rrd4aMyMG{!>NqLc;N1&~hcN3QH1bYet$zk|#8i_7akWcC{qbPIGc;CX&W@czi<b*<!3|2Z&kE?3>Dt"
    "L4!;8(|vtL7rp<(af(yfDimCs%-(%;UXnMSA7edBe3!n9l^qY!+Arm>UBg#=pzp9p+BV?q9n81W2oUg80P@}5Tw$M@4Oleim"
    "h{Im*CI#OV4`QXe6E8U8Qf7BoAwZoj9;$Aa8y6^M1?`7GvN5co}+%d<L$SXnt(SO`x6_&qoX!?=7_VO;Av8!z9)n<Rq2u2+%"
    "Y|q95)I4Z<2m{jNN$|X-eB%M-iGf7KuDDR`_>2&E1Gzud7d;A=uw@GDB%YBoTR~L?pw{ULw>St#Qn`hskO&9l3Qy=*+;JOkO"
    "N6%%$v8f?IlB3McA&>GW}N7ENOS8(mq`AN$3B#eA>O*SANOhYjZmWJG1#CaPAXY^?7EA3_bvDv!Roi{?rJ*O5Jd=j`J?bH0@"
    "7WnuLeFj~5|@LherI)kl~x^?v`Q`%*YPKpC#wOcN~<T#V?6-UKvbfaLm*psK?ELafOLAyxY9A=f}w{K6bP7@KFs0BWzzyu!Q"
    "0lH&^T;axcgrR~@dqYFRS~o)kFicELTuZ($Gl9Z0Rtl16r+4!*yl-r)E0VAFZQ1f2H<KH_7mc8sn7@SMa<jS-@-Xn@Lohq5C"
    "fV9t__N6G&k*JFZ{z8k!_BJ#dk5OteaQ~8K4;%dwjs$0oxd6^rOx~)(oD@<dTW}p*ROQ+bG70{t!r!C^D-qoIUHWflr?`N{5"
    "aa+_zk)K;kUi%dR6)J`P=2rQ`d*C?YM=ZBZW@AX}uL<%=H?9w&z>tQ=dEGcW!n$dK6c$I1t)xtK^qLN(O@6#%vG(+2t1Kmfq"
    "w~p=oV$o=eE#(2u(prI~Fv;oNz2Gw$A<p<TTi#mX)J+DBOQNKoi#g<hTXm#~-3?WGhDh7{DyCuqV?YOomj2j6y;T;m15F9OB"
    "Eg?l+>=t_K4PAdS6^3SX&s`S|f7wnlbD~MgSA~I;5W|Fgg*GM|JwRsD(qH~IQisek0ZJ92{U7i;F$OR~*J#mlCc+?pnZ4HeI"
    "g#YQLKS7ox`{;?fyCrhsm^*Bk4s{f>=U<iQ=kN9W3Dj*j`xv`k5j(2fX=4D`M`x6J1{OvttPrnNYZC~=;#EN_&%gFo?hDj@V"
    "W!`(-ta71MManV;$F`?=PF@a+N6Z%C;vu|YQ-95^|dt|wP%igN?PufF_|5>8V-&HDYR)D)|Y1!LX}G)83Y*;Ls<CO^K|@rZv"
    "H&%f2RI2UhS`rRW@M1lh;ih;Tl4JkRCov;lgy!@B3kX9|zk1e0FXkCp4uOtd`)BG$D4Ji1eUhy=#N3=|ZM{q0`c_zgd{X5GO"
    "Nq%Q+xh@bXSeP0O!VI=I^M<Osr`kdLlqx@B|p4YII<U?);cQXRv{?&kR|K1#h~7UsqjCSolheSv5CUN~1&yUiLLNG{m7n`J^"
    "v|Dq%LmXb3J9=^}#KcvcUj@R2w^<~7mxU8@e_Mr2GeUdS5#9U(E*+b>mm$H07*d?kwc|GW1#xJ{U+QP6~je8OJmq8k3{U7p>"
    "@!%#xskZ4TB4BX97d&B@lPN|7_dBx<Q5<h|q)lCDx0>HAZa5!lzif|ef_k62N8QC^9Cx4LGI$q4EpIg%3|SPXssioU*?;u=b"
    "KX#`109H#pQ#N|XTx#Rrx?rTtKh)R(#)U>JRNMfVu#ALm1Cx7bW*-Q&0&Jebzc^47j^(iY&F`tBk&R}n$lHn;B;fyq>rDZ@I"
    "M}(TJ|2Qe`hV<%oBO>e}cyKS<!V7A~04qW(UuozY(>3Xl*_JSx(sW=g$zi=}y~$?m8UCy1SK@EXMKEJbU#w$3sB<B_~*uGTm"
    "GO$#@o<ph%OXk(yClTpm%QmhZVurAS+t=vm;1MwwNV$%Ya(z;quLd<zVZG{}i(382n7KI~Sz<yd$Fsit%uN-+;6jdsHUFrDA"
    "TAj#*~sLkI&7x$l!`}&_QaQHw_6*WA#W~mf@qC`K9oj8_k_XO#1%=P4sFb@JgbnSgT(DpC5oDsSa*Voj{V1qq0|FAt&xAWy)"
    "t!Gq7%NmqN#VwQE=X@3nQ$SnrRcQ@cUzJ>27r!_yPy4=eQfv4zE#95~yFhWB;3sL*FVwS&_CBPKQCoYnyBTaNukf11f;`odK"
    "{L9(2k8N=Z{xk=1!}a=0e$2GPyH@AeoY3SyI7D@72wym@vnE?)l6VY%j9w-T)xOj<PCK&maV_@2R3e%`N6NexaS!<j+6lhiN"
    "Bomi9#qUlL`k>n*vdv61qPqKNEX(*F9eW?+CBak*ulV(3$27*Nrea6E%#kndFW<li&uTrkD3Zx^CG=(=Vgzo%owEg~Ma!3K7"
    "5ZNM_X0v0c^m?3U>=QhR83JQ(O}g%b-_ku3&f`>e#0#h&T&F99uqTMXo#7ZXQlha$qPrx*uNK8{x-{Ci6Lz(|eEF5WM{`GlV"
    "s&tJZ13v}|YH6_vTP3+$7NB-ftVPu02zrdW&Q#+m0{cNkC)7_-Ice@ob&L)zLx?Qd()tc;1(l=t<7s0J;({NQ*V`a0IvHc7C"
    "3<fy=!9K~ki|sNPL1p3#*?ieVRe8gwtHQ0KP*P-JBT<})>zrDGg;}_VS7ue9;8y*c)n&^KR?Fu;%16vwH*s!?6*e~+9{Ry?@"
    "^hokp+o&i&};`6C%2$}W1cuYOPZi;QnvIWab?p)JVQJDufij$`H?kdhf#{RiUyGLj!wgS$~ct<>N;2VlXKOwCPhFhaCs8HlR"
    "#*Ac~eXg3wblZtbQs0%i)%r-{g&*`^0mY*XOYd`R1w%WQtp_mN{+&znMM)xOINo=-;O2=vVI+n%2=h%L&SsPsiSqm6U&QEN("
    "w!ajE-AVKaABjbqah>Ls_2+C^*24ne2QqMIEHP?gQVT8@hBk+odPNcY^6deT{VA5>EKLK>ZRvb^^*q5|F!BDGN_1q`26%uvr"
    "?blLx4EgA5U&GOcdPBmrENJsHmTuF+QwaJZb&lWnaIu}S7&2|bhxT@!=IQ$9aHRO*osUPGx4fa3qr|hVEjQUIUF@D<_gsA5)"
    "D78oyz2^o^;7FH?##eF@V<4NK+>Xq}i9k7KwW7gVAQG5Az8pzpulM_ESMTuqTo1R3;zI{y5iB-NC3c#`8jX~i&9Cmmmcj6Je"
    "L`avAgD9My=E%{-SByG>!n-L=VR1i2ArDn-b&U!I#DxEZp;f&04K~WN8a!vV7jYJWAhMtZKP+gT8$ltJsUS@_^*%127J3Iey"
    "{cSJ9ARum-)fL7TG3VQC`d3KqLfKeDCWJPT@Tjd~qy+Lb#*Q@8)K6O9Rr9I;^qAnczztWO0uya1BMhN=4<BH#(_NSPe5~Wep"
    "I&ny8{ml&8&Zd{ee+BI=Zvet3mB!6k~9_*9+)b4n4wlp4Mk800h?itP%J1{B$Iy#{ZT64sCCs}Eov<f(P3n{HXh(mrJL^?07"
    "co`8<h5$l>@{6e)aO_ty_j)4<_m$=>jr{6xGpX))<=||MFHYjQv(Un-1<J$jU&j$agVH1W=6e*VcrMEoGdTe>PZDQ0)aTi~u"
    "<{VAVE6ZB9#Pco~*1D6wAdgSV?Hay+t+>^6CdTJ>cjo$3f?lCteI5~PRhdA&?Y;05m$QKegN1RS{-bV_fWH|>yMUnHg0|9i6"
    "mt+vz4#sLlL3876{<x+G?dl#a>|1UMLw|>es~$e#BpH;nkI?tJ{V&t+Y7Vnjkm*A`*|Y9SA{5s*V^A@eHYb$>1&dP_{V}bu>"
    "W#O&f^{)RO<PfiAp0SQOC)jEnB>*naR%)X0jvR?KdlzuuO|w6+dmYgqgdR0z$0{jUQ>tM`cM;x*1pLXOUc3SR?O)iG738;?="
    "i!j$@EZ=KZ-YGsmdKqGS;ZAtboNAv&444bZ3Lf8ZVqhR32;Xngy%L)+5I9jNp5tF#nDaqp;of>7C6!gHXWHC7vU8t$>7y*z9"
    ";M?;Li?>_v8k6+|b;QKZ{w0L;qGyq!**uL`brRMAZ`YVWOj`wd|mJ3IgWpK+k*YG7=7?~<~?71pZi4B;)tLwB$Bb2>1Q1$91"
    "dDtb{_@k8JOF6Lao#m#qUmBA*f3Ti3NMY!Kee5Cd=grPax8}nhyeuSODz44-)+y)>maoM+<sJymt44@|B^-K>GyLS=?qFa%s"
    "5Qekd@*hGXM{HQ$|Tc^Skf)ukhhaB#5)-<$wnPz-VDA!30R?Yu?}K(S-@lB`dVN7+&cZya{2h>?ym|IMS1Tz0)8?``6cDP5s"
    "_;s1nI%6hbO0x+09Am>-;1mp5);n=b{qy>q@<MzKO>=Q(HTuM{ZqXWCSER6NlUOvCPSkc6O!i>xYA7SNxnaO!-p7X&Z_iV9~"
    "uDSAavK2vrrrSpOW2{T{aFA9<ZD^DA2r_l&JmL;D^R^=4qAFfoTQ+f0#)MRPt#Gq)Xt(=`US@4LT-;N(X;8P1Xp(YH6dMr9Y"
    "wcIWsWtCH6F?Uh`)1_ecx8Xt<!Zw6d2xL`@x*@4x&eH=6jg6nqMNAXM1+`J*WlMd3&(y?qQGftrQ(E2O%VamY`3=MOM=cC44"
    "C2mJl&A6hhocS=ys$-%o61yVcj|W&aA;f@^*9B-~9OTTh)No*EH+d`xqIhzRxL)l%lG2?kW%KKb`T3gpr@|@#aye2d7GU;MS"
    "2$A2Nn+Z|>RrMY?-z}TALi0puoQ+&;wdM?>3l_ToGH=9vb}L3L}ts{`m#q4%eODcT_M2da(lf)c>~8*V!Cf9@}Co(_PPGc49"
    "|V<1;s<ujV$zTDFw{gElzMKQpH0?%qKW%V=Utx=i!{6YOHhfqffhywl1I_>jJe0tVg*o*-XiW#r#9)ILQVYvPBh|J^%@K{p|"
    "h~+NN%fdI+)TNI-5QfB0_xSVYh*FM3PhlA<KqY$?1#mApdLoQrN<v|W*IiXr3P%}%~gIdf4ZNH6iKc$butJ~b)+;dM~;K%j6"
    "kwTz*U^LCY!kH6~?)A8SHFw*#cufY{CUP3omxW}F|)zF&j_!ZeNk2=O#7@{)MjQhMS5%r$2(i~^NE8p0-$t<=$R7c^qRfS47"
    "G;XBYiNVukwW9Z7X)UTAm*yX*s8!S}B%H}<5tw2VXG(RvQOUoAyaE%3<(O_KVRPbcm9JjF)I&_Y)H1SaR=%~EuKyqx9h2>0{"
    "8*thG>b-y;T2?2FFt>Uil+2&*9BwO@XNM*ePw}ui$K<lSzq2~S5BQTdsQM~M)x7rXamJFU^1#Rh2y6T#MKsm<3OM;<m)n1Pd"
    "$pW>t=#v<L()i=!m3JcqKV%MlZnAMB~37-KDTgSE6=BZ81$`Vguo7u1IchkKCyOfH>SEK>k;<?k(&+$r%#=h|y1sUuvvoSl9"
    "MfUi{rIo7U{+{r?C#yUoP$?B9J6LSXyt&mU?>#a^hH&CkW(n>u*hS92D8RCd%kTUIRW9L89w&N;I-ao?DrKnGps*Y1~OD{KP"
    "a+~%#Yn?wzLRacxn)5_Zoggk&FOv*jcTNL9LD^3?s)XAKLx?@NC`SSgvjxcsz!S0>!lf~=Jnl{)n$bfi36u+A;WaZ7;jMZwt"
    "tf3hy_S~3up=!mpZ&q|aCQUta5~phzlQS8zn})^)x(TeS;9^-5?!Cz2J20OUP#_`ef8o$YiF<HLIgi|{F*G%7)xEgOZMQsU{"
    "{Re*(nA$~k8O=!qN0K}m6C%#_%lH}Xi_QkeoFAwo@k$$<52z&@*N{G&k&Z@JP$03+W|g=`SBOY4}ITvJNDz8DhOA!YlP~y1b"
    "6$@p^P8)95y`vde*8nwWJb%cTtI&?TFX968$qWDO^M8IjOlF`<PUjX4PLRXi!omlue3q-&lx5jUpPbL7ElOIH;7@kc(2=(xl"
    "=ZPmgDws`88nWV!4NU%%uM9<A%zfA)RKS6oHH^oT7ru#(w0s~iRy-FX+q>KXmKhCfB5$#=f~Exu#UKRV3+!u)ZZ0mP&STfCK"
    "uEUKg>L8;;7m(Xh^c)nQ%B6=e`?Z3s;mEtI)^|r84#Ai2Rb|u`#mkb{rdaxjE(~}pI&=pUQN;|yjei4sSXCSl42}ZpG+%`P`"
    "%R78?Um2MpSO!2UUtogw!e$jm;P4%>zO{9eOxc354zsHLE|pHF!mpNEQZ%gFWoBKOoIm05zXk1Oj^PO2&LjE`kxUl0<vBQg8"
    "oI&Ni-v18Z;ARRD#+mtOhF`#zaRb;e@k?9kUf8|Tq)RhBP+)WQVs%_?A$y39Nk1&Gm{%gm2JfstqJ{m_*GiSJ;{o8MV9Ip{%"
    "nt+1XKMO2$gc*HrB(lP|kkGC>8a~yiVfeD`)tuN-v+$3I{zXhxkYuLV|fjJ<yQ5p;2Ono;NK2UEtH{c1vQoRPdmf_L1L7SIj"
    "(+zh@$)Tgucd&?;WRHAva0Xk2vB&vdS{;`u~p!?>fRYE$mch|@N6+M9cwKkeO~5dwYPv=MNzK0)P1r<*(FVTMNxG3hnu#oC2"
    "g^pF)hfG8=YOXu>yQdbHPhTQZ4hCP4s-+lYMeKGgcvQg{x{F15Y@TWRwzdNPu6tWR-0dsp^eY2<g<=DK{j5v>nMd$~wpgZ~h"
    "T8XT?V=>?9>FB1y%iG#j`KcsBeR7>BYAsjyZSgiIX9X=7RucQ~v$F<&%BOv*ca<ld<5`vwfQi(u?t*H-K(U(HvUqG(1Y}j`h"
    ">8R$qhD4(M&m`*`MhdT93F$rgOPrfG#$C8*kTOJdX1^J75?Vr8QOUA2aAIC+u0*BcJ>1h);rQyIh?P}RyPIeJm0@v1^*8D`S"
    "Cn|Z-%7$GleCMizEHPELpcsE#FdKKuo%U=#QMmBCTA`G#2fZcPRq6`S03uYszP=ukg;)BcF4V`bscNK+4h&bC-7l)`#jV^Xz"
    "<sw4b2>0kQ+j;z&G~UD&JwLk{ImNc_#(D1OCy5F;$%fj<#f&r<*j^}UO(ryr4Sj@|LOqUve-pc5A1=S4nXR~`5&HwXEa#^(s"
    "fScN7ZxyP=RylZV}=qR>=0)`NQ7_Ic3VbbEjKwl*pab0IRo1qSD>YH`?%L2*X?Z`mcsIvt%{CTq1BIc1;zw6I5Q_x2}@@?C)"
    "Pw44BouBj8F*6;^vY7dL&_d~@ncf6TPiuUnG<%567(sFO5~}VBCnWl4cM)0yS#V_SLWYXNiL6dG=#KHON!vd6%(eOu?Wrrl|"
    "7H2<NX-OOor^+V#sY6d|7At|yBxOXK1$neB9j!{JB?&r0PSx2AS4@tfu-K&u~azuR$=ZtU<k&78*6zC<gXZuZXq7c^OAC5?0"
    "0xht}CJWvc;<6*B8EJ<jo;PNP!Cx{YB8zM5;?&N2O3ot8@mAm*RH-Y)saEdw)!we5%U#v5(i$W|i{O?eo616$vc3b(*SMJe-"
    "}42EOResdl~*N_%fa89CP5<NOICej#e>TqX4wK1t?rmg~QnItBHwySlRdt*n78e%aMNH(!T1TpOyYPm{T&HT@*Xqp`gTj?I&"
    "<AgpQT^z!QHInH=ZZAK|_ifCT*Q055JG$scB=z<_C5szGoCVw@R(uKFfDY#&jg|#NIL?6$vCn9(}&Y~kzL>%?cZdabPB3yh}"
    "S<7=$yQUa2Qbx=q)1A0}(c6{nUIO3^-tR2qX}(Ui3=y2#VGFyjnE%1j<6Lt{e`Eac>i`myEjwGMPTNP@StfU`1*Dv<A|+h_-"
    "4O&f=@_{#y7LBxk?%#~dy4l*1HawPi#lyU7A1ngfwBJOo*JLpSr^@hT~iW{GU~`uB8gPlyc4xa(U{DuHBC3=7fPoL;dt_vXk"
    "qNcQgK9|?jm}VBz=nT+~RUT+b?Ehxnzu(=AoDJ1j^L8$3`ScjUW0yCja;y?0CJ0OMO7wks5z{-go72nl8WEcU^aj|2T%<MWY"
    "NG7IVbAQxQrL%RJuWI6uzuYy~#_6{hL`eSB%-0L8`mTQ)1}*@&BxH6{9(+1wWWWARWWMWI9$;az_SERU}CYd}hv<SYc|3wm|"
    "if$q7IFPU*ZR3VKVW`Zb*VsdUrq?t<b?yGtxOpavr)Nj2k$`=SrGE7~~VONPk3Oe;~_GHd3oLSF`6Kc!GJFSo|{4Y?D?i+p8"
    "J|D`UdEhIlm!PaJaoILzvG8Lx+3V*z<2$`Z3G2gg3>+qIPz1bRt|<wu^16)|U%Op&rH+#l)m6lkMf;UyI=K4B&Vt@{(iOs_{"
    "1`Q;%_EN^Q^PG>y;yh~x~L{zYMGy0iC)SOXZkL59-Ut?v6DuY!{Eob0s(tnwA>%%RF~~Q(l?KwpGa2Vs@U_~0)i%}pR|b0Hn"
    "=K#d-<=N80%yHkG;s(OXbytN;ItZmG;VfKmYLSQ%aDKe#sDwFC;UH!%bv(T5tZ#1pEI%Y6K!ul9?Cr%2GT0ZX#XSeWV!;gk|"
    "&(eXIPA?84$J&NXPT>Edj%HV*^pP(}hn>TL<y!<$z!?$;k^vT{4{7)wc0CgEpZYj0Y=tQ0A_Q60NP10Ep)KBx!de0)S{8_pQ"
    "2B>94<6(^O3VgM%3>&P_+OWM!DfDfFHcl-A^Ub$)m9U!oLVIRGn*W)hBy>EV+xyu}xKv8HLHX{4p36B263L8d%*;olbOit0p"
    "3XQ*!X}w&a7Wx5mQUq6w4!m$25MNlk<@QH0w<MVTFdv%6FUqMh#3eTvOT~ePpn;1v^PJ{JsI3QZ<@txSCzI`k+yN1?Zzkl0m"
    "h}ef>uy==jbat_)*R~yqwjtH`DFzva@KASGEpuMFo%y@IABHX4^+1FF7@01dGzE;Fyi&U>I2oz_wOba)S@8Z9$!*KXpt$}lw"
    "{@!R6>JKfiwu<&M?!`9uhD4yTnQDRtru|Np6JAw3xg7_a*h7)}HEZ4Prg$$R$L~h(%3NG#6~n7_0OWJ;~Ac8v~p>pMD*7JJF"
    "8Ro}FX@XOolJi;JMQ_FsbL=Ln!8d0rs22|d4T-5~kh4D<JVzL@J5;w?m)g6lYz$ji^>ZrdX~0IMBA?fhh^x;f1%Ls1E$$lg&"
    "tmGj2ztrw+B@fLSg_WU$hu1ag+;1{Ie)`MMFMi?|}=wNcRPh+6&>mHLXqS|w369!$s@bO>OS(xdH2~MR%%ZO<)%36yw2N&x<"
    "Q5!kqML|2x^2Y<8oDO-u^W!=JI#mKTRVs;AY{w+?kAD20f12-3)Vq<2yL$SRr<vXM!9Moc?C=$*HfdCdL&^pS6;XznX=EQfq"
    "^tMJtEOb}vk3IM^<gkEF|qKQzzhs)dx_z@kICKDt;n2ZS(nRxvrW6)+@S<Q{8=dVHhkHzu3D==fMJ2zuA8x1+gceP7!8INcL"
    "6hT{21FhdRcgAMqN5Gq#$?J^2kP><Ra(SS=3)Y&u@(L(6K4`e?(kkcV%0%jymqxwvCRnW1~B^osP{NcWm3XZQHhO^Y%IK8RM"
    "=Wus+OL^`K@|vF4K$O2e5KUQ3~)a1m%HC7vlT{BevNpMG8iSF-Mi(|wsYeeMIim3jwlZZbF-Su8@1sv-qgd&{zK`(Jq?o^wf"
    "9ZXrYRA}ZTp@5~wmlt_Fw9GZLc9_)cgi-IVcXq01`CA>x0RaQXWh)_*-EWpO*U`|UZ#@pYtBQ4#rqY{l8K?tanz{*XBz|t0H"
    "A`H3<bprVM2?;mG%r-BQOwZ0vO}w4OWNm!FwCiTJF}C}bHV31+4l1-%D|<%tXFC{KXoZ00ah%r4yHY<%r12HFOa^F}?Wm1+_"
    "v28SBf~p?D!_auNTJtNSG%tKFUKRPFf=GMjO3O<ie;j{m50}>z!9?zXh7M!%~EF&OciWe9J)W0NkVC)!=W5o!;PJm-3_@~x$"
    "`wWecx_CQPM^mGalTSP{%yuc>xyCeWT_Mab1>DeiVw)(rhJH7-T^+s@jiZPrIi;h?}}He5+&J-g>k4K8YjT%lf*(OwLO2Iv^"
    "Z1kQF$`FJd)Ze3AxysM`t+e%+Qiic%M>2TjKRaA^1v#SAGB1aY(NK~S57U^>(A`18e<)4@Ld0hlZ9Wts3-1<8B8Vwe+UnhiN"
    "*OyF{r6F6)pOCganj1Nu;B44*iP-*bLu}@f`JIGP|^L(45kFX#5Sp&BQ1<A$5BE?OM`lb5l5~6l9Dn<U74}2m843@p)EEyx*"
    "I519g+C~S)D9+zUD@tL-*H7zW6g5X8>LlCPa0TJVk`X)NH7fJ0C}xpLSKwv;r6PN^80&wIm8=Rv>PVU!>YI}WZ`IT{VSo~CK"
    "L}qg6|;V}VN!BZ*iJEZy($47zg(S0-t3BSF<82ZOlkq!9<AZ$!vO{znfl!TKb;k@9hn3bS>Qy@-POq48s@k;-XL%*7}>47Ug"
    "zkg%2PC~*Xz>evle4z^kIx{k;|P={si03jsyFAU-+pV?(y98v7fp$mT16fG$HilxXf>aY|y;WEMJ`r4c6D<7yNW~vy)+!RZ8"
    "ZqZfm}K1xFX=T2X<B_+TG;#Ww&E)l#vui{j<6UZ<9Uyy|cl-#tW^=kcHSwL_*T9DP8mhsX80&ykoIKJroeLeise7A;~e#Rl~"
    "I_yfmXVn$oBoILW?+R%C!BMZPj)ZW`ujBK@JXiQ5gAYMr#+O7F^BU>9Qyv#4ppz`D*k7OX;XvZG-*D8jw2St2*H~FW;^8p_7"
    "cBh^6lj;zx>G&LLwo8YBOl>j{G=DCSJ~I?z^2YJ$FRN>q8xS}JF*FRc5DV7c=XLS7Mtw|h!yS}9_NZh+>m^Vrj~Zpxk#NQ6l"
    "KHAzwJ{nujS<#)hk+c<H3D=XHugjPN-vK4bzznDk)p|&jXAm{b4WI}a_n{)y(K9rv%bbDPv&<u&w_>YYiJ5*=Os0mH3dFCvR"
    ">4^jsZ6Vj3^YjHo3>Pv?391URwqcH0d&l6E~RBnrUMJ-QmziWoUpkEl`F&{d(SPRO0aW*e=}@!mQ8WM-lHAwTR0@9%;axDf<"
    "X;?Undj(>yb#A{Ns(&Lox)T>~9Q*-_=f9}o7mT}g!f-@UKq@807u33ho_z^1@Fy0Ia}<3FC{WqI}_+k;e!rNLhgJ92=ubx@H"
    "=lQOIgUmz>@WI3K3JP63l<V`{;sRTB+4^53E$}lux4>y#Nu&LMyg}+aVPkMz=)T<Q#p8LUnh``nr;OkmcP_IGH_g3l{VEVgC"
    "#@3R%6lD=zKabKE#sEJ#hLgJTYA%=*r{>wBuP`%n?BiyUUT$KFM|gXf?%W3OB`fA`DU$YTu2M!PGJAR>Y1B4mJ(p8Ev$QCr+"
    "4^SX=ZIRIw!K9LGK)MVu|b!m?@gYh3Mn~xaBDvZQoo$Fi0X2yZhZ$6CRbSr&KX;3{2VEb5w_%-EjpsrB*N|l6NQMHj^{h0=y"
    "|wDxO-Y#1b&$IL)SPA<P6J23s^DPWkcQL<+Aa83m9A(0wa~r*(sb(Ez~4jr5n4>y(&act|)3z1qF6rVNLPFIk2*Sw#H^MgG4"
    "{^!Jg{^_+a?Do35(!Idyz?<X0YvW@hMRCwVWr*;R9<_+lDQzil4c>3DrmR8Ia{b6c?;>{_UW5+7S~rv_B*S2&LLt4i0*<W(("
    "Sifav3%ML+(7STX!^gBH++yo2{KU#TGI==AyHEM(tcsni<4H;X_M|$*}g3ns0-JOc0&v3}vy($XGnQ^}yggPo|w@4qynN=ys"
    "oJ1DcCc44~I#m}3&^RQaXTzDs!WRmRf2gaemHYfp{Gt(;K|h<O)O3w1oX{li15Y9^L#r2$A(AawHeN6xeR%mtj1-VFT-DoIW"
    "I#QBc^>tH9+nc{l?b=wNy7nRY-~nuRpnkP3GPzlHd9YOb+gq^oK=Klsw=z!`VgEDDPwv+4Yphe0}REfU7YUfp1gt)a)_gbuL"
    "B3%2j<=oxxKmpuLrt*RQk6w;w6)e+iW<TDJ0M|`5Kuz(eykjp$x8XJBn!W<Al;1whn6tTq*l%x~HvG-i>E>IabJw@ra4(h>5"
    "^i(bvxM2L+`#WX6jiqPlkiU(9Wf%ILoPv&P^Ml)U?_d|1kIB*zC<Z3fo0t)XE(#387*m&tdsuls?kyR$!;MgV?5JOhAJyoW2"
    "LvS8u(Rxp%EXg<rj@!l*h=Y8xk$&Pm=V)Xn>D=hb?h#Fe?_){H2xJB4<{PZ1LnO=cdXyD&3Vv?Tj2dAS?HXH~6&Dgb<Fzq~j"
    "1>R{niM8~-YK=3Bgh25haC>yCu%sw@%_hrV<yGnKiGkfkbwJc-@?4Qt{@EklT!N-2B&X`F#+R_mX6!vRT)~|K45>IjRW`o9P"
    "e$)=r}W;pn~3&rhoJ3x-+$wUC500dmFv{G6|I7v23_J@HDB?&UaCi)uZVLw9QPL)u@RfcwC|SOj+xg{U-3QGzLVs-DL_&Qwe"
    "p5csl%Jk>~Q$&n8--5;sl^0?Uag8MjXx!e}Lt?oO81X5}bMzNX6vCs3!)i!JA|31+mv=3sE2EYMg>siOup1hjcO^oUe{2mC="
    "7Lh9TbA6d}|An(p$ZYI`Rk)SW0yi=1`>iI{MBQWFejJ*jojg%ZZ#l#1Yfj;>-r_<q0rD|}V{vtYv{*(d&)MgBb05b57(74w|"
    "CEU7^x0F;)r@M`TWyc~`S0o9z4o|az@Y#ux%v`Iwg(>iMk#WSF~{E&Kn!la%}%~P=CcLrIQ@rUf0M;L(xtlE>9qC_3=voM1N"
    "fZ}L;e$c6_ffjEL!nbFrozZ%%u3hGe)XAC{Lr3YSFH>)VAXB$X+^qr{eC4I0eMyA`^B9FCm?cl>{K-do?mp3$s)(3swPV^KZ"
    ";UwLi}|HuaRBs$t~s{aofdb?d{`hF5+2J0-L1sU!~je;%=L!PG~>*;R;qsBuPI}b?5LNs%AFRCVH-j(U*Pkz@cW_f2QTGfAw"
    "zxRBPr`Aqg><~V<4+Q=%L|+`Nu~IyKBF`I4omrSKwyXxHa=uQdzlw?0Z<W&33A9G<)Z`rka`-Wch^+;4l12`}t86qollPof9"
    "&4&8b7eIE|)6A)<W)#dll=>;5LVlnBa4_*!&FiFH}EdvDbXR~qf^`VwAC6z8TT{~K(rI0r`|nHlqC16B93UHEyF;S6rfw4PW"
    "3k6R-&Qc)59>p+z#^ML-!lQhe7!f74U!V+n9*$sc^)Uwf1eRj!at!JaE1^4sy4T3RUZ<=wh6~R1TkvikC)wioqOkanF_nSU!"
    "0h-@@b91`vwmdB809V_+CNomC<By{!26&W-l-<{S9f5s!kz1>n*JubwC-`Wm2Ug&RHNl$FK~m-i1Mn_T{J9nR!4T`uXrbUBO"
    "FFnP>Y1yhF3xZbk92N>cA|Ec;+HWY=9_wkuV6t~YYK}TztuR?KgDC`@-FDf-rik5At4B4epHR3*q+<@pMpseLDB}QVVTPpQA"
    "q)StDnO%t?O0LdUW91z1zdr$)t8oGKF8CQQpInE1UQk+ut-E$E?nRagXlOV`^$oIyfnHo4=J?p=G@Njj<;#75~j2=3+&<g&c"
    "NfcwDe=Pjw%u8}AW_Uc=8iWV84UYK)xj$N7riydUPWf?l}e5czu>=ld$8S5J{pEr}&2oI`bAI=xC{;^DsQmNTv0Gt}dBr9Is"
    "}tg%$mOK0r)9qN{!n22O!;m-O6xA11G3y)is*pIA(D4+UF^6zd6V*Ic<>=!_kPu$k!dn5X~A0fPkXWAul1e$8;#yc2!&Qp9I"
    "`D**8^|QrDJO&aJC?2*c4<3ueyV!LC4>UFpjbgS6mxjo+@kTVy&f5POjr^mHN%t4W$Q-AQmggk|j6(vV#^U-GxQ&A-_59F2c"
    "*od4?A2+e7??3(3pA2UK-U4Rqd&z%LhM88m2_ypiW5RYG*TZ_Mb&J)E1|T4`%kq*!3d+8b&BXPG)Ym<U+NfpwEWjLZ7~U3-V"
    "iRV^=tTT`w~GLQ0L`49v9jVzgL-Fu5FoIKHG8MP{Hs}$5b{JEm2XTx6Z-F%&Gc}sY66ZA+_Z~MSnTs*Ltov-382GT4AQZVA^"
    "rA&Qt}08?zDFc^NE`|ESpWv=vB330ahs;Dy>kq)upsq463|Xj@ifxVcamoVxfT_&Ofm^VFSx_tj{LlcHitwZvTGDYJ}Sa4>R"
    "QPhoI%zU?Rpzl$U_2yfXaqdaTXxX+o6(xiJowA9YoiaT)UKQnA-s;+LHubycM9Dp3G>;XkT2J>02Ny*m*gE6FPa6hir04ur5"
    "zy!%>C5Bz&j;<l`!Gt$tt<#`>CA-eb{6N^tP)<#Ng~&OX9BHqlaz0au!5&hRCEqe*E4R`b4=C-RLYg6g9(7;)o@mLIxe2cOO"
    "mqKm`}x#`$i)HK-cT8@N1TjDkO%ob&vz9xf*lEXK~uK+8LL3O6ugTe(OcG^Lsp0v&v+cvh9?SQwNpBE(%WnE;z9NMD>R>f?2"
    "BA3mwq3%MxbS(8gx|~OlwvlL`6K|MYbc{>eN7<eLL+g?)`9D@%=1M{*L6Dlk=AglzN4~;slpm{o#_)WXk~JymBnz)WV7Onc<"
    "BBh#74;T>aRj`noLqR9*xq(KnE#=6~mG%LBA={{|IPWOyW3o4`XN_sPkr34f$hkwhpct#JNaTgk3Wy7`WPe1A|r$o6xq;f%!"
    "qH=cQ8z_ghiG1FS%SG{~csDJWjC&7DQP^0EOUQE5TZF)FWNXawHat;RSH&R%W(oPfDS4Y8;20yq1glUGKEw?WP>&k^vtk$Q7"
    "jp^K4e7LN)8RE<DIZqBtZC5)^U!Q<l7kh-R)smo72TLah^?gGbz-KB?^TXs)HwR%p3#&A_t>j)Z-Q=|vVFI>Ao47#ia7(R`k"
    "vsp;#({H%*`JiNsTK9s>!h<cODEv3up|Pza*vN!?K6hj*>Vgo*+Zn#pLKc~G@@<<6>NFufeNfW^a;>y+{q_&4om@W@_74c4y"
    "dVt`+H}RUuK;Fcxmb$lEA94(~C-lJ6@bUhxpiJ4yP-k<I7#f$c}D}0k&x~_8g^I?RQand@IeA15#a<SmL);;xPr!nWmp5#cg"
    "IgT@uvV;h2~pJ*!+6|1^8U{`34}0B-04%u4i|tM8R5&Ph>8vc~)~Yi8-!$cS@6=j%*kV8IT;fHS%vH|V1ad|#vceM)h9Nk*L"
    "zBD&8Qcm4CdRayh0bXj^pXKn*nLD6xz`w$kiz+ET3t2Q{Sa4U4PSt$l{6Qck8*@vX`@&J79GG}H>d#|$k{rF3W_pATyYC(fS"
    "F$y4QTqzix8rh`ZDFL?L=zfCmtZ~$vjyRs)<rwrKvjgKVt@)a=&m6ZO9d5EZ8z?vffPP1*#6${X)@$**N*wM-&uPo5kqX@L<"
    "&U&JIf@auNrTGT&boB-17xIaS678aO~R4M#k}jv-E-!w?lV4}uP@ByU7lYk@?keCI_2JQSwrx94B<Y%Q}XxBFBh9UmMb5}#v"
    "h#^qjQ-|iH|Eqxeu3ilFV_u@?!k`iuzbU{s~#fB^@ZFluIToOHM=91`%kdhSKX%*QsSFoS5SG5y$KdBkGV#6}9g^VZJx7cnj"
    "6zGV}YseQ$2MUn(72y>#T3WJczGn85{xzd+RZ6uQo5-pKn)Rn%XUXD8wf`E44ICziObm$r^tc`gr2d9L<5Rkub<iZT^hyzNG"
    "|ng_UQDm0WA+%ujwZNE2le#*HX|1yarFeZ}yt4s?=EPwHer*2bGyR{l*xVZN^Rz`lA8?q<GAZN3y9@Ih8d#=!%yi0}Ez^?T;"
    "+;|}Z;B5D^qr76*rTL3h%!04W(!mdK?l!dX5YVUE=sT;gB;^k9&10m;E%^K3MpC(<3YGUA$&0NHetx&!8drph;$fYeb4N4!g"
    "NNH)1h^KwY<@IxZ?fL0dg7fjjJQePDO|J#6^O@6QhH}!lVjzX?05-d2IcwzCrj`TAt(ILD~3OUG;jPc8v)I}=o~B0Re|WS^0"
    "mvE_9nkyTqH5+j@j20`eH=r=(f^y39d$0H}qAQ>%qLC;$uBUUk64AAx*=Bp}ncr<1RuSya+{t9It8Fl_9<U_DQ0OrR#m*<JO"
    "Lf;S=BfB<vR7?Av;MnYw8Mo-HxFcr<YWTq`KRyBUGohD>eUcU$dQot%ZIf$r0ySOj66k1cqe(0kf2qX-wqE4gU2v{gTvZAGE"
    "_3y4>tjN++~6=uMZQqJN62qGp?>eQvw&P*tvpC@NXJ^64%9mV?XjLJKX8>%1in5{Qv%VJlsbKONgw(Tk*8}OgECz`Go&#Vsz"
    "dnS~$q7cxppB1NWzuw}u77Rkv)qKS=8lWenW2D?GKN)QuLA|*`AKqpD)T|%26^8%YxQ_B~71NivZd=H1v9zbfDmn!Lz>!EIj"
    "A~1BaI#hFXHnVDKbi>2fI-#-faK+L42ZJsB4B5i#Y+4oiF!bzlxhK6;@A|?Y{)?5q|y5&mFj-R(=Jn>mLR4vAygEaB430WJu"
    "VjRdDo`YN5RAI$Ow3NRlOUE;wxykAC57pFKo@m#g|OInY6UtE!5P7i{keM+Da&X#dVXS;57RY#ndK|*sZnYn-t7B+@GEcc^{"
    "P_+fwVt{{7)`qpKB+kv<gFk0kc0petn~43Go?xFoTbQ6bfonbKXK(z}hgsT*6gu*qO=Pw?Z@mHy>=nb#^lt+o<H*{CUIKHdQ"
    "g>~GNq0;(J?Th356%`Ya9qv%p_^c0VT6i#F3S=!q<dr&d)U&Ygci)OdF<!3b*`bbbd?I6?EH%VLaTh2j!HO*Dw9{&;%<iF2s"
    "-P0SdKOhB);XtHIdru6e+t7mP1cgo;C%d50xD2ol(z;2dCB84s?~-Jj>e0>_3VWKH5!$q!ayviXZx>?UIBFY+%YLBGu=YVk>"
    "wgdNyp!rC0rY8?$t=V9)sg?U*W7ODmy|i>c1IIf-)W~R*m~gf-lsZ!mgDwE`I;-@?{OjU2;G|qw)}xuEKF+H2we?1{jC)7xh"
    "3lzt(jorif{a|zgolSaKo-oG_;-ao79k5`f*H=>M#-Wy5E=w79G&kjrhmaXPKu+w=ADhDp7jQa@ox3nSOm;e+Y}`P9UL$;0$"
    ">84f@#IFpl)6i(}BJW^g@*j=3ko$-NEOrpwSpyVa9Z`(bHDfI%2HpRnULl4OUZvuApYObtNRRqs5Tz*r4&dMJIoZ2w1VF9_3"
    "yxB9?@i}Ty$Y-5#z)08+aEJkKCh*r;7+h5H{`@d>}UhrsjHZ+z>8a6MgawD{N#F1xZ`6Z`@o0?}{2r5GO_cf6dlAVDXVpGNK"
    "(jCsdoDPrWnmg|GK$MzgCMiGC`(H!xW}#kYbYL8ruV)r@>+Xd=el=%`3x)3mHpkS<5#K3{=F9LukZ5*3L91?j;PAirHr-rxy"
    "%PO+(d9XY;Qu^qs(WkH+?gR{wm*gjmn=jrB9ntb4a}0Fo=eV8Kp};sT68;HXIkn?NBBCB`<(C?PDIyZ_wtN6*hXpXTm*}`P1"
    "HOy&Mh0vyJ6GicMKqmsV0)67Z7h5KUB#Tn_o@6VXTHx8qx}Y=6eLY+N??ASa-**YTcoLbobD6hApJf+X~Ci+hYr&G+Wf9Dw1"
    "h0NdoY`(#cB+=C?tz-j*ye<eOG?{b`UHpk2csczQ`)FZoL~N$CH}@0m#uDwOAhrYtVc=xvg|1fn@f_Ny&B5y#OyvR=jRg^rH"
    "X<N5dq00YY4-uMZ~119Sqw~V$l1?qgIikw);5GwDpl_LWcwOF0HCODq%2&Qa13S0rnk9<a)R`yiMe5-n?Seh38ih4QmlHT!Y"
    "&bcUFu_;{Z9ZG&r#;%tIC?}TLCM&2nxs2+e2V;>g|I=UB9Dqk;EPVZ`rmnv1eEEvxenkjDm@ada(%oPVc&xholY0OoM8!O>`"
    "nw0Z@`LeH+xdM;UDiO2S(}2GavOFjgs0azm9EU7tDWc&u$|i2ry;P+Pk`J`rb*xZ`qfvq{h~0<ZDIR|^*Ld8RDpX;Ebk{>-w"
    "*<lm{aYDWO4?j8O?h2;O}ob$tj0aOefG>diq}Jb>1MqtT#*B-cqplG|H9G@4hs8Re3Zdn1_qClMQE;rAZ<FA#mD%r+sj-Ix$"
    "nTiLcOxv3!msR?UiQNk|G7K2(t>Vu{o#<hAh=ByvlB3Kcl#R4EasXPJ766-v=FP(&sR=zNqFT^#}1A9dPW+&pVI!y>vfmL)@"
    "Qn&0QZe0Pa2f{!y`Xc!rF)P3Cfg{;e*EG8CzLO|r(i5w?}%ceu;mxPBZ_JpAGb&{mv{3#+ZT{_e0WAwhpe;?|4MX+$bMDMT("
    "Q$?7;a@#tyHd?b<>LK(_8J%JF3k(j`EI7#LY@N_08ybWY_|nA#sdvh><DYr(F<5kG*4H>l9#L0#eIgm*t{}2qZR0&N<y^z+u"
    "@EY!B|cA}!uWEj3!+Vk(&r+WAe)0_oUjiu8>1l5P2NY0Wv;-T-RMH62vRF+CYV3uJT%eT^gOd_e`%;XJe~M}sO`YS&@+m6bd"
    "7cOObjeBUpI?nvy7Q!+@?f8?@BZ8>OC)%_1xLcQ#jXa_0qBWE<6u|v5WNz^>dUs!a&M9Sc(-7dqz6pnhV}z%FYfyi!%boNP7"
    "vRvt?1bFgYuuNwD)TT9p1L1N=aVdPI6asQLp{-~h6B<q_;epp~&)!qg~6tzk5RHrt_u9pl+Lmk29^)L=>id`rm(-@!ZP5oKx"
    "$v`8%n+<8go(D7EbN*V!E_mjvGKD5H$KMI6mD-U229aq+WIQu}Cf!;ZZ=`2fMJf2Z&dwmDq4e|G6y)U?Mas&GCIo69aH=A6v"
    "$<S3%thbyRxZU@QF@SHnz|W)YY41ToV5+Tq<j?bSUcv;je7RCoa{qJ!#v`Bb?&Ef?*rGa1k#u!5+k+biw`CA@5^juK9Z+=~)"
    "H$I7g2+s8TNrMSWI8Bb7QTKPd4l;yZ%60b-u~%SPHU+3p9^4FD=HZvRN!g8PdX0YU9=m*madvpC-jNzA8jr0D29@8@$>lkCA"
    "s<J3rgy@^Xy4x*%ps}mnapWw{e2|^KK*?S1}ReA>Qu0R*=&E2Jw=od@B551ABX`O^XAf(8#gXQux;OK69bNm(<m7`By*u_%9"
    "U#wRK~0?x;>kI@mOtsj(!|%l!{zcDNW4Vxvpw8Jv!eU38v_+jO1?DmU8$e>*Br^2|aj&(e=7Phk?{fa2;yZo@~DF<42%8t+M"
    "H_uofMB%YQzp|GdQ@IOOnx@<}eT{PX?yj>pXdL2~NjC>vRu!=`=w+VbOK6wTBuIb8uaCpa!^ieMF20rKRQdy>!i)V%fmtfwT"
    "gP**oA(ZH3rQZ=^tA{*Je$YyOsv3f(%Rg<kTZ?21@wt<WS1`h346$DR&5{?+0`}!8AmF+E^8M-Q{<i;q6>DU5W+o?qT*XTC9"
    "OUv8XTK8H#$YLNLaWPzk`LU=)&hEva{C$jWSO&K#5_09ZR5tdR>@^}pr`Kv&AjkB1Lc`m-4v0sJ^n9TlaLrM*BR214h<~ZUg"
    "YUHY`eW4u~=?4?v116s9@ZoN78N$nOqy6)ck`oWB)r^?3StO`^bQAM83kv<C#<M*>fr&NXJLE+EN9v2u42)Twd%kKpw%PCc|"
    "s<JWwyS!l+W`Nc1XcF<gT3==MO=DYUJD!s0=zrL|U-&M8>wazzU5^9A!#$zGpKnuzH>8%wvoE?se7Hy1X$YzhZ~=wf+;sS?F"
    "MU>l!{%TS*~mb$PB+!EuW_+{CpPH3E>7jg5|>4HE~394#cvFW?Kbk9;w;kL=_TJ-q+m8ukK$B)<Eyah^mcV*DNyfnZ&c)55+"
    "B=umiG84aa3GV$?`Id)z=i%Y(q|Ci_T;8^Ta}VuDtC}r_wonI?1khk+6FsbqOpf<REB$Ca$M8L#aRSBxyC%Dwt~wIQ#;-i$y"
    "mEMy+516k?<@{!ZO@B2UhtS2P-kQ>m}d4W{O+b07eWia9vjYY(o0mU6K;_^a)Z^gz3K=4X_F=YXF%BiT-XK6Cs<@EU<|&i5q"
    "p$+??`B-1SO4R<WVt28$t+1gz+)0Ni9f2JOcF&?tSvJ$Zf3Rsvxf^%2jK;3nd)_Eap$FS3U|oQo)f32dB*RIZi7u=2=>wD5?"
    "eXw9XL<ox2ZZsM8L>vt`TE)OBjY|CIT32lPInWm9ly*VGasyFO`ZPrB@}s_%S03Ls^5EJP^XoL(hgO`o@ORM2Y9E;@?o&Z-2"
    "rJwbVQ#^`=={`%&d-zjy%uF2mLUPD%b20ogvpJ1p>?tSze<!D#EzBVvCe{MViJ;3dtZxo&~BT0Yy6j|NhVbhV8X49T1d%)sV"
    "f*9jB6K87>ym*ZS$2!MZ0jU#fhTEs6i91>xi7hN07u=72(k2stfBy*Q2m1>M0Q{D@OBh7UD+dG&z;`jJ-_Eq>_UeQm*`@N?t"
    "TCT)zvcpM+Wy^h)`#)0nPpQ}VFe*uX40<vt1=E|R&_@E$%N{ZHHsxNYfx5^eWW8u@5FXqIg9^L{yC<4LJlH6FbODPU4_>VYE"
    "20a#6BF9mi$pkmP|I~YSQHL85ZLM#@C>83g=*CC&qi(o!MdgpzQfRVY3sa`$;o(YBaX1kOMbQbPbpFDVdyZ{5)cM62eNuO)V"
    "4fRMj96@UZ)>vp6-=iJsNe$6+$%i#=-nif=R@YkT(%J@-<s)7~gbrP~IQSe()B7Jw8`8XuDE6~M|eD7P)E*>wHMbGa?6sw-`"
    "3!y)28q63mwR7}V%$jcj<nn{_aOC+oLtZ}rt<W6pvNOI8F{opvH8z6(L9;WbfMgy7!1X;CoT#3f><YkD9?h^8B8dM$@M68%x"
    "n}WAw#clRwX%gYZDX>8F?a8fjFApx|1-9$*hu>fJ68-Z(t&4}9W?Kn~ezftk<~lBVjEzWy`0_j|X)<nWlMfZq8j41+TB5F@x"
    "gKdNaEtGO&ZYf@^tTl|v<7k{Dt)7`V>DI#%y;gut;~J&AGRnG($#dmcD3rfGqpcM7klB+t3;%^G_uddfiLVjE`1T_o)>4&-8"
    "`Fv4o|?RTJOY&03FPQgdX5K@B_zj9_#B02#Lx%kB6yCHP`!=6hO(Ep{UD-e@p&bvfl9}c9CDagOl+CrS;QP@djAp$~Dj|vdq"
    "`(fmDI`D?F)dRQXgtC6DGX4K6MfQuhWdn3Ms%pQa8^{5}|+?%G$==7@c*YIhNTt>odMZyoHU6WsMqaUAhGD-XA?1sgP3Oce*"
    "4LtfjgVBJi&6aKmkGR>XWo>^gPQ6OlZh}b9J$4ZGK^PKt)R8izD-gGQup_58h9CL_*{sATW%fOyOXk%(x)9@tgDW99Z-oRb`"
    "SH(~|!;a}c(*=b8^_0ONIcCXlLuHz_LTU7Tc@m_>LT70Cu~5!Q&1=ZWo`*2>{B`&Evk%;0r;G@^eNzt?g$|vdcHr`Jk_9dML"
    ">lHKc#Y{-H8rt7d=*U5nD%4i)_$RaA5CGQ?TyNDmZqk~fqz|>ch)UE$IT96XWExEEC@sC>aU&W@&&MFwdD?vvQ$o9vJi3?T?"
    "c$Tp2_o>Jor~)Z`w&#z7#Kx3?Sp=aIV@FpwCMke?^_@>nLqqcbKGGI?$7Q=3W9{G(8l=Qb3{7p3e4VrWehy8=jMOA~5Wg-`T"
    "~Ps$rUJ1Vx()RrJfMTfXZqV|{vNWMj=)h|jNu;@l&>Zzyti0QqtpO+VF)99WZ${@p)Yfy7*l4d>4NcL*J`5U|<314TTJ41EK"
    "<PBo8>RFPjtJR)Y21?ctOYyvAIWo3lFliKOsz{KUt0CEg#Rhu4@d)wR20EYIXUEy;CPMsF^u@^%PPOR!Ln^~g%*DuBFAMj^_"
    "bCw%~1U{K!m&nQwp~W8=pXDy;;sXNJmFgmc0NR5{vcbJZgsPCRNpNjE2^+Puk1z`Fkgr2^W^ToIsWgsV6QTe`(lV2%{Mbj+S"
    ")Q1}NhRXX-8D@YmgKaQ)FW-i2>->6P~619HaqxWdol7Z4JVz#v=r+r%*k&mF+yNaMxS`|3BAp>!<9R2*Vn}rv!+dZ?vt^d$-"
    "R3fx2Nmy%4POv($ojp<e}i<*SpKj5Jhow5CMbImr}sBR+304NH6rXbL8Rk%%0?|(t^W&;P4)HWXOOpX_E*aF0677-0}q=%b~"
    "&t6N0Yafm0592=02$Cx-K2TA-Wo3g9g1sMb1=Zf&hI$QpeU{-gy2ziNJCs9bA|n5-m7PW6w=3r5-+-!UAINbij@w8#`smIOP"
    "C<|c?e9D`7&m4>--w555IMFG}z8Nnqxs=~tO8luGgLa;FM9yU_j%^5`Vu*aBp_b=zTO)0admc|Cz<y>47A8|(M0DsX*utW3;"
    "PrI!s-xHfw5L4sL<s7I8P_ksliFj4;{b#;A_xt~@>K8<x)STJGc{aCjb{iYB=1;hZyt;Pqq+n>hLaG-Md1E`S=`)piky+c)U"
    "NF}iyT&bh%#R8=sZM!rK%VfKlCg-n%s|Y~*MmI;XMV;)qO@vNds(N8oXi6tZNhfZtZ5uF2qs2qex9KS;1zji@#$s-adQZ>^M"
    "fz7anfnVwy&~`%kw&Vb>ZM{<f$D|E^~iBPQH#j#z;Z|w?Gtk4Ih7fF8HfuOt>;JQ%YMAmgk5wf3gtHmJ1&Qc7D&Twe(}0BTe"
    "DEPqlx2RT^OP3nJGeYuE`>t=QfYsg%D+gf(^U?liV~^XJ9>1;<uzo3#h}(nUKgFJWP!-qoHA0Z)z<&cZnzeu{7sLp4{kxu3j"
    "Vtb5K=lltKC6_M3eaSKQ5T*WGidfYX)l0VLair?DYm=e}C=3CZmBvcwy6ALeQzq_BO>1fk&VYQ6<V;ZSw+2j1ib3$lzS++Lb"
    "PrZ2;SbUH>R=Gez1NMIg>gE3Y*E-P>=J*vs+bu1*;czCv!po73EeT4Lm!~xoHg<p*!$DBUA}pFjc9iqmmxIEgy<=69X>A&{F"
    "NYH0J9dISwgzS=ha<BZC?@MlEHg;PC9QDrf`J7|B9(4*NjjVu#ZL$p<9_mrC9d0U#Fm|gs)N)u>jO;wckj=Qq|U*}N`Z{zh$"
    "Zw3S3W)0<K|5Aua+lokSZ<X+cn*MN=a&RW*Yc<tn~1DH1o)Ey~;`mw6<KUbK#NVS%sW!-U&Gd+{psCpWnIb6$43#ocU54aO9"
    "UvU6DB{2rs}WzjFJ2hLXO9)Te%>aa<hAR&~W`w>j5ZWh2USFYTe)ZWFP3=;V8!qFJx!{*7}yRn7ib_hyLaNcq^Qh9dW@;(-{"
    "vjPo<?WAiZuF4l)9rAlj??cER$fs)+7uTF>kY`IU(?zuc+OSh)V(CNE-kFC`uaV*zpIv6Yo7REI(Lc|tZb35KNdPS}AVFkO8"
    "S)&>zJ$-%s8H9f~kTHQKL7;kP`_qv|CS+`W*Q}|)OL@Q?1fH6$TH!PiNuHEDslDZlh4(*jrIULe42QKp9yV>uPRwAtH{1EMs"
    "ctQ@HezBOF1IkjycL|*;t&hO-50sth(IiO>PwJ?FeDq%4A4S3a#EvuM0Mv)b$e_M6!G5+e%>W@it*ysc~r~e6J*riJbvq);L"
    "xp*yWkqdNASGdMC_YJqa<)ouXy+-r4Wrw==w{Fk^4(D)(HB&ERhKAuSTqW`s-=R124PU{aai!W7j}+5?+Y5MUJmcix5H)hQI"
    "X)1fRl#X}~cXub5!Bo6mtf={#BJ@KvX%ZaDJA^A<1ZyT&J0vt|M_f4hc9s)+mvb>dP#J{xstP|Lc%W95}SVT5F<rybcX!&wM"
    "Y>XZ*3$zniA&R2QNvV0^aC{Z26T^|<&>{#BA-R+{yEDi1NlbwB6w-~&9<!OTv*0oXO>U4scwM(LY#TD*fs4@E}3M3XSI2y;n"
    "`b!PCnE&BTKrM^3nj=CuL+kV4QO_XF2#^PMq>D{X0IVw#;iG9HfPrw943+TrQH+@!A2VP;JI&pef&!Ync>eUMiZ_HSPOSR?M"
    "bv|usgL&1>y*qmVNFqzNjpV$(#)7S^GMN|_lGQdaMuS?&*jGN)(48uuB<oe&mQ0hc<xBb*sXe{5+1-!i82#-bO!+6058`4vT"
    "`3fEJ^SpQLnP^tov*^ZysB!>=mMy_l0fzBS*ES27ZQ4-X(V4+Ak?q-;!n{lQqqHjhS2C)DcRvl*1TW0&26>6829auSv&&-b*"
    "kf(jJ|HQg4g;P#%HV`58%OYL+nZrof|ug+?ckOxDcY6f&+qO*`S#PXpP<;xJ;F<MfwL0hnxRl#9eHqa0$T#5@&hvsCN3HO_W"
    "5RF~Jaq(1NTuQQ{m{a3o~frr9Pn~VaKf@$#voH0@Af@$)t(N&kFc+l0S`p->_paA~)1OA|iCI*h6{}-FKXg>r)Agm&tiGK(O"
    "q*}RJN0y@@7(oj_fIK*eAa7)l!2Csd=9oXLv)|w2{1F`{%B}`<sgN6agV6=KMA!pK-baP|$4UY|rK*>|>HLC2e&f^!6;T(Xz"
    "K%doxgL*8{%I1GFw_tCcI>$gHE-RXN%*$y_1^aN3Uw~8V7=8K&F8Q`{JMr^3D043szNzrdhE2l*|r5sDUJoSMohz>dBm(~#s"
    "XYH^2`cO(&NLKDL8gw8ZCBV!A{fpCaJwynEn&?Ku|Y%I7y*uFI=cv3?Mt8G~r8nL9TeJBmd~s`KSLz23z4#{jg3&BtggXy>`"
    "{n1;=_XeOi-n0f{m*r+56xj^eyLp5g8^aw}dG!B8J2`PX3j<;5SlKoguD6pN1-8Sd9ra<Rcdk*=NvZJRn}S?Wpnb+o%rH~TZ"
    "RN){3!+Np9ri(n~Y#hkG|MbdV?bp+dhkZQRZGX^5#yGbeKGf=iP*^dpH^I+DCH&*;m4Pn81&;FN#-A*ewxG*Q!f5B%O>EZnG"
    "=8L>{XC;TP$#|VD%&xXpW&iT@lu2sBc}>R|dg9BCg&+g_FfI+Uge{FNZO$m7aM8w<ym?vjYk-c<?8@=zo>6FpM4#r-0z2jkr"
    "42zp_t+L(p(g!KYr{;@uD8TAbMN)&vD?!6$N{)#`ux`Q;IX{_)vIUi83ejb=y`~$<g7h0Z1av8`{LG7wX1@P9k<AUA$7hJ@J"
    "%mLJkQ;ld#D!pz<|-yHGaNkK=GOm`(+7oG&_fMC_KF}5N7QU;OtB?m;7ww#?JCOX#{rq-QK4+UU_JKDYu_Qt~KAWH`TaR6Q0"
    "t`-W-LPs&U$<mz2Pymy04TVN0YcwWD;7Lk+v5Dm7%E3!x#uqSum<OQpU9M@UnpGS8l<Qis&v-+{^g%D)jkmeU+L95~?xP24D"
    ";M;v%%f;WFu;!;w4U#T$^5!h-Je9Xepe&cz7mq5J{M8XhOw!C3Wm7RNFto5|prykU-mpD;RC%ZM&guPXPnEq#k_Mi0z1CZj#"
    "D!~iUBEz@B0S&MT=Q1rul`x`ru2v^CZkXbl=+r5y@l^E2imHKfZQbQC@oyZ=0OrvweD6?>4M#*(C<4I(|N0d*vS5syeQccFq"
    "Mqs^2ls~7W)dIFH0_^wUl-FM28SrY5CZ9DK!>d|I@obZ)Ow6(8GQbckt*+ui>9q{DE?=i&y}lp0#xeu&!Dsg!?(xsHKTp|y`"
    "Tv%3w@*5v@uY?+vQVVjxg_6AE9j+%jZ>rMT%HQB;z2t)y7AGxhbo-wbrbBme1nQ$Cw_d*6;Km3Du+07^;%u9hoNcW$cfyF@>"
    "M<C+ysYCNXc-tya1)Q8bzNGY>TkF!jN&ANOUtQ)^W%zC2J(dkdr7LP}E|-NSH<C>c08EXqTcKTgnkT1B)#6h>z^qFDU8#mSh"
    "CcDc!`g3chwLZHXo0|JQ+7ZayXwTa$8%P$;4Z-JM(S->nb)(fHTm>gfF-`At)haNmHWu$NQ*IABVLyLB|j7*S!e$ppAI0xrK"
    "i<^+Z9$%0dx(^clQezY&s9E;p!WE<Z62r_(DbN7#*40Mn`+HyD|EoK2hIZ#Elp=A2TR5JYa7V*KJFQn|*YTd*pH0g^8O$Dx)"
    "GNn9a~sEJpg2TegomR(TJ0=Kad_Z5Q@q;mZTA<mB0-!g;oVU(@=sQEURKOM{aBt?&*cIb#!@Y@hbWOaG-HQQYEvW;p|4gTXQ"
    "K?;#LAJk08@DfsVbZHdIxrnq~50%2KY2*DX#dYH^dwWPjGNgx`Z&hiNg-?kbsvzF<bXF_|W%W;}x;OQ8fNU_4G4ox?JsFeXb"
    "Y1V0OK1E%boD=`0>KFePK9%{v}vxqf+MH=%y+@|-6kcw@v#f+f2uy(6%Uz~UD~tvv1~m=K_U8~MT0J<wS)$rVxN$)iI<yFLD"
    "A>1Cu620e3qPNxpTNOnQUMXX662p_G+<g{K%y6D^+X*O6hU+#O82P;%wJb<$$OW1(8sU?e#6xH+{smW?1*CZ$?uu2q@y3Lov"
    "YHLJU^=g~FsWTMUrXBh8I~Kv8ydiAh&bQqV$=MS1UaH04B-B{Ljb%aT?II?|M)&LF2{0@N3Wa`B5w004Xouso8OK_>gVP@m+"
    "gMayh4dH*aX;GB-S}4Oaw8e-{aVF!&hi)35A<kv*CMzI`=V>8G?qrXh!SgHUMjVd=d58<JF{Bj*98c-3?y+lQx+AFmY_<$Kf"
    "k0Nv~-$W7nC$7G;?+e9}4fkwt`G+p6QwCkfG5370~ei7Wn-0@&{^(q!cosVe6se(oPEfC6CEC6Sh>j!Rx;*OYIDnz_VK5gPf"
    "qO6!xtOEOisX70KNaIjpk-M$($Dvh8*uIth1+lhxWU745!7uV_Wh+etLYHw7fqvVVN%5jlyRr^O|1PFK4R)P1)tsw0M{cYAq"
    "oJ5vawT8!`8zlqBSxWn4qfn<IBWxBJi_bZ4TxCuC$nr39%kM8VLLfnG}aK86(aei3wDCWoOy#UlYM`cUb6zSFR;93l0N-er="
    "I)E5!9#r+XxYvu<<UWdRN!#Z|>o>5IbBrtLutRFmaswLjoAxTyA!PEZ-f%*uwYdR~DBg)*CqDkHKUiu`E!!<@+d>D2lJRjC{"
    "k%1OU9>##ZB|?TT{d4Vu$GN<?v^EU`50Ne&aobLm`8ufEQepSib@_{iy|q)2E;y}8F?E+s|Pb2W*yL7!i<%i1e)dP|4z2a35"
    "P`X)$Dx$Tc6L#TOGJ57M*7uz5;w9)pZ}EN58|Zzbi0&Yjq`u_lZTZ6G8rz9!VFeQY{2w49pQ_7~W+awj#NvAxY}pO)KSyiS4"
    "{v{rT5!8gQML{;U2<Re~{bWY}?@@wKfIffT*~Md;tHN{|;%V;V6C7Hw^9l7~xK_;U%tk|)QKwlMEWn1qLkYnubg4Ggm?iZ0j"
    "(04wkksQiIXIk55YWusqVi<+V!r_z_eZ_`p!iQ6d--CTJ@>E1?E_eT_fXMezfRaI-kX~fdq6Y!?!dEo0EN>xO`o{NcxIVeA`"
    ">-rK=up(_xwQHa^h8Pl`TBU`qK2>QQWkCVcJg>)HEan|^9OBN!BbII?D=H6VSM7M6z_==0UZC&JHTGNQ0G_O#s*N&!N+~1Hr"
    "SsEM*-HqFiMYIlVAq*%RL3QQj#FR5dbJ_$M+e{Fn$4GBss|z~@EM|F24<8dFHtl=6!d30B=5-zk5S01Wl&Mu9U~BwDHVjm4S"
    "ftC`4++NU-kgOb~NsiESWmL4k9jsuTgEjWc^vsHOe~6j@i~O!3nMkX_V%uV%bVU7#7qU`d}^@zl6sen2>v3u!|MjFcP=hrT{"
    "-Bb9#dy4uSqRcj#92{(W!2(=W+~1KESCYv${Km<3(D@SZcA7F5rCu7D>UH!>yg<lOckFh?_wso(6hj)ynX(E8!1s1h1bQhu;"
    "*|Db#tm^U<VB=|jnkDHc!ROn7#3!mt<)4z<m!(b;6fn;ypP#dB*kvn0vUOG%6Lp$_zG>{sP^I2y&F_NXC#BJ6F5ZvSzE$?~X"
    "_nroL2XC+;IC}l`ZUF9%$NvtSBX*d&+H6c~(se*R=NT_4(#@s~Dh*~Dm1(gLt_@&Q7Q^Sq%;M4g2sYL}87n_#yqZcEmd?0yU"
    "hqRZdF2k!NqMOcJWCjEk9JR=IWNA^jp8ji`h4?fb#=FJzVW|!<RvGi?dgZm^eOX+>in=;?{I=@(rG{)B^IHNEy^^xU524}#3"
    "xCvm_w)K9x3KBjz^m1L+*<Y3s<MA@FHH@!UXHuLpHsMjT@8}3nC5aGz<+pY!mV3&=hWzAqkXR!BH1#Sr;u+(jWE(a6gj>=ei"
    "-0tB$uQUsJb^8du~Ar=MOZnw1YH2WK{!`ExlNWebPK_F^!R$|`hQ8DSgVv9@w5E$jWWUl{Gb`Xwc_Q#2DVK=$ym_sJ`^eeP!"
    "fu1TTu3A4H;Q-%5b%a#xz97h(c;P~W39l26X%VK=m5z^n99e0Xoq)UsEYzKI=%<-J$vN4pHf}Na6EZM*3Eh$DnK|=qd;5KE$"
    "`I}Q1UP|s}a$lIV2G>V-6XE`#OM6TvuFDPL*P#4e)YryU*+|F&^$JE&-jZE>c=kM+=f12>!TL(z>kguwob2oglzX{EJGOMCS"
    ")@b^%fi_NZO;nTX%g7LE7gNaMbV6N5c+_sq)%Bcm#_3bRCoi963-hJf>s7Z6qvu1ogy#^CnIG*T8~I}1-{)$kCH>jgMDe!j<"
    "0I90~H55ol~;*iwX4)BC7njK%FFGXrzLuh`?}e{BVeEznI+bw_CT5pO~8Y_er$lrn7Fk+D11rYYs1u470QF@-G(!qA23XZ3-"
    "yCCp5}-n%L?{EUeQbgcly^ielH-p^~2-eDWo13pgMROaUrzs#<Qa$NNC8J2@NmlKLZ|5EEcZZ#m;YEt@e-h2=+pq9Uv6cw=p"
    "Kbu-g{lS^cZ6cWj4$R4gjfc#%*Agg4v@`@gqb3Tpxx{7&o;VOo{sZuAG7p?Xr^-ke4uGG(K4aNfOK|`Eiyk)7sFRup7#f%~#"
    "D1RB{LR0N;jyt{^;R*Cgqn5T61-{|dyy*%=wZwbWH?`n$B;%(UJZo<0k4;Wp&s}*jc75o2XZbtinsv!u;Bpzu2RdXIX;E0PH"
    "CL?mWGtNrg_z6nKcekuWz<gRisp&*OF81MQqrkPXehMuvQDz~*0{bIuhVkROpvqnYa82H>mce1mRrF`Xz8$8BfA<a?Pg0UA2"
    "vDOZG21}g9)v;Kp*1dtLK`3uK8vG_cUGCDlJzUJ}jW|jvvi=KgjAl5aSRcV!~x-_MRPwa_>M>&SKe4hx?n!b}B7l+gR=x!{I"
    "w1kE;R<xOH7cNphcI;g~4GwBI$Qcy3dSytO^g574!?NXLZ^X^jcW<gbM>t~+S*ohs2F1bxszM4oF&=vu|J*C@F!wkoVbzH%L"
    "+I{l0AJ=wqoq^YEcH_0W@@2IGsR~v?Udw1FX)A@WB#Buec5!f2)LaJ0=oXE&58Q)|-rjEMQV?c0ZT|>|!VzYk^=LH5KaJ6zg"
    "FfcGJ{XSLwGf0pAS2qq{C)f3TpD&?1)a84nw{CkNpjn_1jLnIq2%##1LdaC|o>iNAW$by+aVjDgw7vE64pagSz1){R0c%Qy<"
    "8H0|rra8r9CO9no497v*K)+*{mKgH*?N-)j!LGzXQ67+qBl&NnU%gWel8FF&0M4XFx>(+o~UF-3u!i0WKMpa(`aMr2@~n5;w"
    "&qm&S~VQv~Rk>ugtf^g2I|*)Tt<8D1)i+T`KD70vPfe<CBa1vpLG=A2B*jZzu!GWa~<&M;lk}v`so~VHtcKOdQ}dV0T*{!6h"
    "~Nvn%S{sL)4e`Q{mNU6$te0+#Na^Sv|>1ixr0q%<7A;cJ{L7MLvZ#@uV6eLXa?pM1R-C6!%#qox?<2-lIXuPjuGgW~|fei$|"
    "@z?PlLncWz26i=xla7*30%}8KHt;`4WS^GVE^g8e7^V=B`T|CV4^2DC@kTYgaGn71t&tO#Betirps~K8t1NhGtm7f2pd>p%6"
    "agf3hGs&hQT?OZ*(ec2IwNWS<aj1aR1T~jX13ubJa^?VrhD(OhZl6D;<~D|54L(78$CW<;#s21DmG;Ah^^gwO6ZMtf3XH(i4"
    ")elDbG)|Tw7KTy6<IN=Giz4EpI_Eh1YWHgvV|~~P8gDsaWnJnz7UJo?NABbwmROgzFy>06s}7zcoyy`qgLeBv8%nRvqJJHn>"
    "+LTT{hf#WTu!M?xFoFDDd4ysM%HAN`|*vAiTc;koW5E%Lme(M_)z_d?eWzGbi?61QwSP#%XQ?)ENB8LQA-aQ(%KFjVUCa50l"
    "kiQmnr;T{imLDqB*THoc*WA>QMUQ;I?;DY1ZdgyW3c4XKW>Y2uj3o~43_5w5<|75hq`N<2NqRKyVmA1$p?8TA^n^iP!O5MB("
    "yYFTH|+=ZmFi5<DfVSc}&aoVtra&-Y!q;*#ezM6y7PAqt@yr}foB8j$0=@Z`B(N`(7#UMnM=Bfo^e~$Ks-+`$->g9gDDFd8$"
    "<?X+)@CK_@lfC|FPAL2DV&oPg?C;Y9q9S|mgtc5=`dvJtTW6)D-GA&RSo7v;7an5jImc#~jjBMIC|+Bg)|oKH;H=S6zrHVK{"
    "&^PX=uEMI$JZBHfD6W{BQqD-P9REPQ1XDuo`zupY&e4k|DX#=%^>x4FCaWbr_j5&y1L)rKfluUyRuL-EM%8<na+`9(zXi=F@"
    "3DwTSfwJ+8pkB*99i%egM2TD87!mr)N;_LBH-yfvMS5Nhge68Me-HQzAp=e$d@xn>S%zvB~p;Zr^yl`PS_t_m0phpG~=X59V"
    "Q3Pccn~2dB?8Uyi=-%J2|~l!~fU-1zYfVGjOr)PE4p=x9H)y4rrd;BoqsUSiH^AKVf*q#hmlbq~)+vYirQ;8&H!w6IvtFhSO"
    "5N5gg>;M)wJY{xJ|bPXHoCLP-5TN8ku!}UVVe{Z_NPmAhphoOF<MT4S-sf&rauUJGg^XRl|$jC^85SgQDut{s@sYv;ClR|j9"
    "0_>5fUBA%lAcf99hh5TgLN^}D;cD`s1oJTfr`FW65oblIF>0Xtrcq<bE*=T}6{44yjyU_l*o^l7mqy1%mLFLFj{4l1#|RVAk"
    "Iw?$iYM(25_@af--=8|{6{M-q}35`W{!P$LK6y`hrP5-3d0f(8<aA{jbB^Obc;y+u$GBEmq$J!QYZHXS;+6bb1diXla>Yo=w"
    "{YvFlrq^7I|YR%1AtMqHfZ8C*10yJLaMLfz$Yk6r`-Y+8*Km2XVQg5p3xS>*q=cv-hr3)y{VtcUIo6q#De}X<YK>QYsOg8?K"
    "tLIaG1(4`vFp+ou-p2TNq@Oh?Qv%%4_A$&6@MY!uo3^`Xfc$vck<luhfdw5m2;p_LardiJ6FD@Vz^c7BWVWZv^+G72>6GXKZ"
    "YH3inyb=wm+XxP}c?KHM++cuh{v2EM7ZM(5;<J|W9@6&!Cd(E+?))-5-XnI1bW_9-o)3p*LQ_Yh&5^qtLCC-~sh<P9U_^%fG"
    "IaWG=*JutoR(Z9j6)FfYB}DtEoUV9ahkJF&=T*`;%f`>J*eorw)%rlY7<|JTBpz))?l&F+Vmik{w+JwSqVSaBQVvM5`}1i{D"
    "%M56;Bn)bc8ZY&Vk`yI|D?gqhAk>}|1w$>^y#DI>`v17@APuiFQ@Y3{KMHhQlV`zbpY23Vty$DGcnqc*=d=p{Xj3<W>tC?S_"
    "4%?6ZoMN2*CHcR|)4{(NqYbryyar2609XCD{w@xntE~jK}e(RC1x<1Bhw?y&cInSb>ucPizT9ycc(c@iHj9kP`U$1`B_^x5="
    "0W`I?ObAl#~-p>zo+|JRk<fMC|xJANVCO704DV@9ZJj@mr5%aj8}_JeG*I}Ob8T_tc$-n@cl4VX5_^P?qjk@R7L#4zMoi1en"
    "dXnDq~raf+>+^6t8I@bFf#Pq5sXAb`}^k9)vQXz153~?byvCX(S#np*%(}@56aY(^5<1MW~Zvq90v+CwLo`Wtf6!Zwaq24TA"
    "0?`z+h@~JASPcc1Srl;r#ha3?2NNo@X_<nCRE;k03fB3ficm>`)Y2D~zck;It&TtJwLnQsxb-1i`U^s=q}T<zqC+vxGA|pb_"
    "8K}6zf|rZuI^emF`DgLsO<QFw@i#xcRed^B0T(W7s%!R<xIiRqB!~~A-L)k@&z-YN+ynaSV>ucTEhFr@k%u$Z7~h|4D6g$OY"
    "Kn9S)OraT9CczLV?P|d>kM=?swnrKQ|jCNlCnJKEoSZWM<PkeqzAbZ?*l<61aq({w;cf>U4_NeQtGlnT{=wmz{UJ^lp&XXU6"
    "|V==w7I{Ve+2)#irQmFrEQ%VC6oecKxrhhzL9ATTjrIAWWYY&5!ro+De<UYJl<b8Zb)9^8CIO`}n1ias73#z$|EQwb?d3YW@"
    "=dGd-=;QWNq6aiOQCVC-`<l&W0WzI0nXiqglm3n;RS;WJD^3Ot}FXi1)O@sEN-DB<SOCZL&`R&(qa6W<j2OUK?grExjD{DLp"
    "adN((`oKL`>KKzLu}H=8RM|AsHitu~L$&wlQ&pl+TE=WN++CL^U#tz~c?@1f?B!Vpi9xS76{*C(R~SqGQ^Ajj=o4%JG4MZsr"
    "8qor%7ZjTYwQAx+YmZ@*bpWG(J9cxm6;J_&hJrNa_U60LfDs>NP`f|JOg^a5r|D-K59ZUu2_;W`D-oX7C!xw3m`IRHPmvX2M"
    "Nm-n@Pxo>t8i+I&#<(lVbo@*(p5ne0`Dgjpa_#;Uj{HMt}y=mE*ts8S#aaB*lv15#(qQ*l8QA3N{?wR+m2-66ZBdoGGX=JCS"
    "S3@3l<4m8q{@x;61x0;R&F3b!A^vo(b=GyMfZ$>IT@jdma<t`&zCL*0?*T2vY)Z+NsvDMXwi>+8T5;ppwa2<ko0J6-4}oh$9"
    "8hrt(2=P$tjgnHt7Qpco3sf&Xj&*?^)2@T@QBboXnl(}{34#u5&a<$iIo!z6(;Q?7TLXCjS1R6UyI7KE~om1<$IR2w+lD)1O"
    "%DK^@fKSz!g6vUezJA8p>3^I({q27<g4k9=PXk#u#Ln4C-<sru)9Ps=N(G|ZU-N0FvPmy&<jk<M;wMyUQBwY!!&Yd5EVvL~8"
    "%Ep3TMGG1vvNmJ#%ZCBb!QH>ojI+Hd20w3g1HG;NQ_dqpU4*J@*)aIT<`bqtUh}qTaGPs0C91@4HvbI;Y<?XVLS|TtJMU+&h"
    "Jy_W-kKA_s(KGjELsdvry3dfNKm17dfvCc8W70%^^*V-zTS%9j$k~sfnZHfFrJO<-4SCKd3w=>1ir;X*(b3k12CaJ-sJhDg*"
    "JI*Yu=)lGq{2sn((h=(`$sQ%q>_P3t*RIdAPd!kp$Gde!WQpb~<IS3}LR_Yt?>Is8uQ07%6X^&+bN+L{)yYQv`O+~RMZsT(}"
    "KC&|9qaHx9N+(Ul+cRz^dF|V(VBttIpqAkA*3zeW|HFsxAJZ|IMdl-mBQ*M*fzQWB&TP6=rU&)-G7ydH=BdI0w|EK1StR+1)"
    "*$0oV2LqVb7!`u5Gt-=^mplS0p_KnRN8&6)1Gk=n0V60bS+*#xbj7aGkj5^fd?aBs8dOd|+f4FrO*8MK=Y%Z8rkEY;J@g&0`"
    "qnOV)@H0BT<J$2M+(hB*_AyJhkqGx93$U-59#~1e|@O;F~siv)T__|Z6agQ9D4=a{-~3)Xda8Z<`r(ipI30TU^y;LmMTrQ3O"
    "cQSVp*Q#%aI7HKMAiU|Dg?e{~9@!P2y#Nl@LEmIGjmEm>-ssG^QP=_ZU_WX>hdHD!PeJn_hbJhbjBpO;J7DF|M~53_x=!DZU"
    "lL5-g@@W71B_qGXkht^qjNF?Xj!urJ`rB4j$dq@fMCqkGK9$?`54^-58Ih{H>~hC|PvE!kQa!y`Wo5qfv`_7pb#YGSY<rD0^"
    "IACOdI8>DEVa&3ckiC0~?=;;r4W5wS3Xl6laf!rq|c%S<YRs~{j>8)I|WP%j*&v{KfAZlx{uC{iRP$%oOH5h}2l6^6JgA-bT"
    "oJ*5L66y~VdUqiMO_m?@*{|F}GbEEIehoxOfxyeGtkA^FDwb-S$UtJJX5ir(ltlHqAWpJ_v%JP^jm(IAzK_wm2}?h_qrpfm5"
    "mO?C>p8e&dp)fWp83yeRpA-$!2`8!`0RlgzYD(4)=RvzC#&kU(F|M0-8QcY)vb@=4t?+RG<1Z#V)Rh7bY*JXN%jn~fW@+^6P"
    "n7^C+d^?^EBw%k4?I&Do-7kK#`7#*(w4L17fXS2UOM?V;rP<Wqc>!t=kk?ulTWL<}6R4&l%d+bsC`gIaN!H`zdX84LdP3M1n"
    "v!7z=mb7zF73$f!?~=(h<m=Emqi@@OW$Xzfl!G0})}To$hm49p7?^JCTQo1K<tV5nciwL~`uZ~p=jJaly7r&xY6b5ix0yPt@"
    "@+qORz_|pC_dhX(G0i2Q-+uG6qLUVj~Myr~+{@E+|=t{m=k8qX;a}U0Psp9UO{j3<xz~JB^(ZK&algwHC#mquD>SlYd&j?+3"
    "HZS9p<pe|Jl?#T#w1QfNgEwTtLT`EVc)2;^0&}>W-SgO>j4gki9k4vZT{Xi_aS0p@p!BYc$i*wSH^TalgWAAimL(2KIDn;0$"
    "}}Nr9i`J9TIRLg{zeQAZ9s?CKK<6Lv)%-esbb52`4ybIiYZ^Hcqw^!8ROAbqt)5GT22~G6c1l{jlz|!%9Jv|KUkD(GPqBCv*"
    "+|+hk2m)IX|N)YjAO6z()1vvj}+WkLfw4jb%&wEZ{HktC!7DB984>Izw_->GFZCiu+ZpOHwcL=2!gb%J<&*iTA4fSpV$##+Z"
    "<GeE2~S=DJ&{_+z;dH>da{Fh%lqiFhGcEr$h#igz&+Mz-93UKm}iXry9A+i>o7#nqDuHn!DqO!`<an=nuS1FXGpkDl_A`^bm"
    "l^;G=Mj!xnVk04m54(8!7Zm%;{Ql@_n=F1Tula}D&(fw!Ukg+5rha!&#_k1J)4N@Z4xAIMrLpm%S-cEJ8`{4Qs`fH!a9`??Z"
    "9?*lzR1~u)+1u!VvhM;MXOG_P{%(J~!8%;8^_{K1CACo)ScD1%9z9~uNd+b4ZDNs}u6P48O$d29Lq}yK#t91^gZ5wJTHPK7Q"
    "G34A($MH~{m-CDC?6atNQ#Tw{FFhlw6r*|kp+y7Wq~N0K?jO?#=`dvnL@IFLnfCm1RvbGOx20qBcdrX4*WRr8z`RVZ^}Hql<"
    "{^g^0Hv{&DZWp6Y}<R5;(-XY+dorKh>9OcxLmxOV>_>=6k=lIu%WHo;RIaSd=N9$bYALd~kj%_ddzG&L!Kl6LUCzT&byHdxQ"
    "|QD+(e3;`=?~cAgHOKVJBGU;N;eDWxK8elJug?-+)Ff$k_e0QN)Ci_D!lGC`wp11(>RT5S$5Bl>+So<dVnh#SNG_+;yxJI6h"
    "BKN5cuG!%V5A6a5?ULzyRVuwIB0R6@;-iUz~uOXQibL~mfcoh2ge?ml}cTETq=NH(;s+yrIZR+5hpYF^Gus_pF-(E-a&e&c0"
    "WsmqPRgXBEkv}r*6!vp+lJhi11-Sd_q63;k!KBhp_9T9Yq=V@HK}#M4Y?_F5Gu#<J#@!+?da^_U4m((M)FRrjh=2Y|j1~;i+"
    "Wxy)Old~{nC$F=2jsbqoA-Q77K{$*D?&y6G8|4AqD%jh83ve|-qvi1UKi_nQ~P$)5y)B*Q}XmMj0vdG7nS}>w?P&+n++sm%q"
    "GV>{Ebn0Swe4A`lX26=!#tr3n3?wZ-?a^Vf~G_!^StcpQ(!v&hOfxUGLGdpM7f#_)(E_jQ{m^ZSM{AWg|LsqSXPsyt?_tUUg"
    "SV^WBi5iISI{vWlF_Hb@%jI6D?@c7e8kwGv8^PY~*OWlf;BL%pUZ_s$L%IrZQ;`qVj2*w~sbd-z<0r&{?Igu<TH(Pw>_X&#G"
    "&_YG;cm+&4lb9KT<D6c>S@b!pZc(9-t5WFl}W*L`-ls`F8lsQ#i++4;9@hqh-Y%?$Hu@O04AJ#X|^YD>(0i#0NhH)~A0J9qi"
    "3ct!*LJLA?EB1=V6mPq9tO$WxMVQ&OG4;wdR^63iwgQEd%{tqBnEw>{{@XA$$RpeYg~lr0gY2+m)yxN{#|_hdk+8Bo+^{U8K"
    "0MI*CL~2ujaq)%e*m}19`x|=sQ)bs%?eisEU@vn*z0~?N!#nvb3OAZS%%iEvmP{4lGz|0Z`O`yVVlYlb>GlMy=D4W_%Xfko@"
    "&SCq2Piuy58c)ERn5)^t|MaCM}|v|H^hBubn3`Z_gL^V79SNHI|y`x@UpF@~;?OKkU!^ba&^_Fdwl~S-2=2_nGQ_<aQ=V{lu"
    "@77g4E$0;x10`pCq%(V-w7KmEDSX`9zVUCMmL>5qxbFRGCPs@RdRl}_J8-3^uQ>WoX<PMyY{VA-!j_vDq^`|O4bn9~<ngvtx"
    "mFrAoJj=uAYzSBzs?Y7Ax`&PawcJk+YmT<7&%QMp4O+A#`T-fMD&J?O`YL5>;yCkekmupXqeawa4>xv`pJUp*Es`0)%;GpX{"
    "qkY7_7K${E`qwWp{dbbZ{%axp>Rss@mG@Ega_q>KD^CW`Ha_Zz#n&W?ZHA!KWYR^ZjuGHoG%I!y*q&1;+79N!4y*LQ!NGGmY"
    "rO!$%j6RIvm`XT2^$a^6Z|3@nnAT$*MZpK)D_lL6@)R5sn|Gq*4}=T6r*Jo$|q3uqh8__=WY2}-#Jr9?Q#bnc(zR-i`osRWJ"
    "h2P(FEbXjjbzIrdf1*qU65cu!xh!IAd{6HAi(z#jJBey6(hRk`1gz*+yl4yF_z3cCyZj`d&|$366I9ZiAk+ioWMlqUDZ;7I;"
    ")&_>%yLZU$%@T~1=mnN-kpo_)rVZ2Rr+3<Trc%L0&B#=YvW{9<xwOBg@G75)t5x$aw8!~vd%k-vB)yuW}-)==7tt=t`K3);C"
    "ca{gJKgJpKvOY^AuQ)8ok?<YHbV=l(%PBK!4Ih<hVA882@xpeFTLO`=N|L>ve+5fyA{w)C0g1cKg!W??O__nefcbcOV)o9fD"
    "i$C}Mkqe=bR8Xax)7Ci$C|jCTue0Qu<+wdQR$oWjf%TrBClh3CbHBmO%*f4^E{Xq&l|BqVAaX20QA5Jg+UU5qZUELazUcp0U"
    "fL6xQAf{GbC9xU^4=~wcui!6a<j}%tJy?wqUF2YeQ))#s*&w)R;ei8(AdYm1N~_Y<ojG_w;!3#V(^YH^MNXBQv6T{|1#bW<H"
    "%AEGxg+ef}%(<0z(~;v8t0dS^U85oYZi(po|y%$vCwg{Y%7v287U6(QvZ8OPe+KrQ#+v#SEptG<5oPP*(gPCCvd8&GQZO`rO"
    "1_iQdb~<m=%D<ZG#~<fSM2@|bW3b4;ZL!5%qN=)QsNRS$x@6FD#mOL``rmIb=8>E!gHJV_JbYOn6pViV$0V9z}>6=wwkP@~x"
    "<ACmFUB?j{Ux2xza2#v0|9kiiP^7NSU6>L<6sa5J_Ld~laNJ_uS2!rreu`Ar)J1<gQY;^`pUVYlsH9HtPj&njzliVZ`)7$4C"
    "%u=a{H==ixTn@7|JrEsNmf%~_f2ZbdJ$8h1f3;8P(%Vd$m`N*LA__CiuM|NYimTxVKt&5xjnDWVB{+v)iFV1dcHWiTvV|>S-"
    "sE*${ho#)$Mb`8vrML=q&clpt0lylVqknP*U_%So!~vwgI47xn||g{IDT<sBs{NoJ`hrPN--4B^=G>7tUcAf+nZgk%4WL4eV"
    "rLq684omC>qRmfQvmBk(SM&_k0*3o&Z&3CxI?EKD3>eM6a@>KRv3z+-4ayGRfKI=uXk&zM%lR@r*SX(w+&e5{q%*aB-TV0GS"
    "2YCSACz`)O51O^=}$tQqU<S~Qo~qC5z@yI2U0!@o9MZoT)%?VY`)(eI0LP5-F~U{!yV4)pi$b;{d?mEq%9Ozwb_g7yfLB+B_"
    "zqy@6}paue%+}e3&X>mYE7*r$#7tQ6rgEhOlT5MmhwVR`8RYHY|uYgV7M8oIEI6&Ch;*BterB#rQE~U$TMTr8>!u%LFKI`=g"
    "Xus2bEJxUD4K9+Xqf@z_cqU4bD&x#CFBHBu*(q!_g~e<>>vn$);NPP2e<<*U`IrdB1HD{zCYqzMF4ly&m?WDp6&%KQxJyZhP"
    "|TobgbpD9l=RId3`1M(iEG9Va8<0S`!kb!=wdM%DH}jd1#lG49<+}I7=Poo-y!Nm<G0k40A9Xa9mq+H0AEz{S(@BNMZ)Sti("
    "o#dqFD0Z!!Jj5J~#<YI*T8qxAeNo;<yV=Db5*{?AlI`XsEcjrW?gF1Q+F^!V=c5%nqIEZ`D)N1i#99e4H|RCm(we%-i6NB&5"
    "*qO)~#y>#%y48yp-wT(?H)5VQPn9c&um*p`n82)O$;6r&{;1*0Y$;tWpYYESfyw4sGeKe6YrpU4OhEmomXvN$)^98E`iXM&#"
    "T5+qp)_71E&W<27icHhiuJixdCL#eckd18Jo(!-EyPGa7qrZ@AP8rs;f2F$SG`!+xOHLt96pTu`d0j@CkA66CKh#Jqz)ri8+"
    ")*HH#xgJ<ihI2eYqH|^?uH}4hK0R5Am)h%_0IqG_@tAjVK6^&3YBr`vZM^?>Tg2z%hhv4gY$7+67v_tcD9axz`Vi%$9le_Oc"
    "fDCard>WQm;EoF9j0%u_XY|>6u&W8)0}>o6-Kuiw-?ZdI}%-_q_b)dq83fyl#~{VRB6vA`x;z*Fr_rgCsBQ`1BbS3{fVA*25"
    "@K#$&-vCpTGlJd@%I9>><1yGrzkFl7G^bH_WV0cM0Qgab1k&ZYFp0jWX>8L&S5;_mHQ-4W#xPHm`oFMWEBJr*<&4R@b<AeiJ"
    "&%53SQ)e4ZUVS+CIkr)mhT4(b1wO)NkakcF)g1X1)UPWw66&m=0oj-P)>TFhNgrXxdqu4$*trKaUkPpm4J&%!c6S=Pxi{0V)"
    "S_MysF^U`z*Ld~&UC>Ve>XE7^Fq&8OY)+oZIf3kjR%h{%=Ie(XoC-v)qFCz{=8!q8atXW%>mRB3az{fVb%L_T(Xv%8oIa=zx"
    "Z^nLoYw&7QoP(vBME1SP_G<OmP+j$l9UfD9*x5A`A!J0yno7X!64_w$nFC?XIwifGV?O1q97_9)2+rK8QQ0-Y9(O2h$s;=r&"
    "Ga*vKf~mn`EZxXOeCnBOVyk0uhPhjBblA63tN4(P?4OS6QZUd+!q*G2))kY8GKGPrf7-eZ94D(adM=ONP*Enx6E?}Vi#5wy8"
    ";**xeJKrZJXA!r_SSJkc%T%e}?N61ePbJjVaO|ahnXG{gb2y-H2`YTlfp-&GPW@3#nG@1m#J*KK^m5rpSUK@jU9Gon_k^YzM"
    "D(-~7b^GD%<CRT86fD2scc-C$zBFMO;9D9m{9!}m^Y!_A;TuqFyu>~st^rQ*Gc+R%?bP;xuLQK*=CSe0UYr?15LDV2D!i7Yv"
    "`MpTwkV&)x!=Yt%b2~NMGbnO+hJaW=4sKW%wMXmYsYu~L0q9x6KFW@>sW-^{s#)v&dDQhayDbLtWUOpF{@>+5bBqemt%qT<q"
    "0`p_ydjo2t1U_S0_I8RCO@=(WBGc4zd_<iEYoeb<!}qia@~NOHRCyTgQWdXK_bhPR?>+NU%^ut{$~<2rSo_yFenCAxXA)o73"
    "7r)5c*{4Es`^(+`B2K}vny*5j~-`CL@DUVCOw$A{tK9N`E$ASujbho+sb$<6-=5rEB_@55e@%q45HOp=~p11?ex_lX&wSpU}"
    "W?O1Kb#qs3fAnx0s}<aA6h(xTkC-_a20U0AgZmjJ3hoEqYa-(d>$DSK<C(Apv%oJiW?0C=a&zyDx=Ips^9bO-2P5dasFsuk@"
    "X#q~`3F7an=ipe}8M43d~g&}rB68fA#^Grb7e{$mzf_vtG)UmG<ms`@K%&bkiRb_UgbHJ#U++FdRcbe_T?a`H~vmMX7<BK7O"
    "l);)tnR7bh6qm}KZ*oTQH4Y*cT4z@r+p?Dz~B=mB>>Z_WX6@DG!VhZ>lFYftG0-?z5t@!!BVqYl={xpRJD@G~M=lU+GinhSt"
    "IDZ44?ht=u48+`Ti^AV>)S}}k+~Gr*`8Dp~*s)fBeD{tc+z#QUB4vAiJ_QwMsI$kKD9Q!GhJzLaL;?<AcqQYw;1x&@P8J9AG"
    "mHO{>`<Ei|C-kvOl$|C(%Y~`<f*VfG*}ne6y^=6ka=Hwu0uc4@~+SV0mG0}bA1t*2(g?CLBVqpCszhmdO6+KyGRw^y0Yb~Ft"
    "vJtz8@mLsrkx#VuHaF)pWP2c;&7isX;VzWz`uxR+>@=k|RnIi*F@~sI&iAkm>Lw1c}^b{Q4?3Jm?eK2?)uph?()ZA=V_Z^Su"
    "~HlG(Uuv&1e1+4*$ql0}Ct>3P-RGRyGXXdEQ`Stzm|kA2Ck_X8xEcf*mArOG_VOwg>svva=A{5%EU2cnY=i9hd)S`NmQk9Ng"
    "u>oLtm=P1j6y86;xCy->LX78mL<cllvrNgUdrUut9o}X+NNk6|>48S%F*%fqx;7y7Xj$N}ZVP@8{8W1}QC#oy{!za#_7glai"
    "%>+j-6_BQ36--L-D?pO-<q+ok%<j%h?Xun<)>aQAn&H1_(!;9$=MsZS;?5zNwbq;0QXomBDrk{DLyU#yf2H`tsQoq5kP%P*2"
    "gHMngCq-k3|xxs*;zg6h|6z0P*!F=v36g=((4?q{^TrnL|2#H$*~``I1njvecibpHOrT@!aH<l=je@pP@SEa;f=VKC2-E;bZ"
    "<|hGgB+q3O5ii`8cQRLhy}_Gqy*w>^!JzHeaE<FIO2>?68&J<*Mv%t8IByB$a%eKlVblrlz-aS6gDrj7C=XUcj@(a7H+?Pxa"
    "As<hnZ6+kr!Jn@CH|&SbB8G*|}(5*53O7r-V^AGEXnunuKF?}9`DNr(d#XhgU=hE5UUxJkZa*y*${{N(gq|145BlTQ$escR<"
    "j#8E3v-iM(+k!&W2e9Kigns-XuE9N{4V_3JfFK4q0p;S{88m*5Q`bcwRfH)yR>G+4=Am!2`_1)ZDoJ-g5e@=Yb|GSEq#BUh#"
    "9s!1>N#dYt)R_~L285i4Cj!jq{90vTvykL6;^^rNT+=FAEtcsGLvMX7bqgd%ziBfb@qh)lLOd(!gcNQHMV;bGU4L3}?ze_Rb"
    "aoHBHzB2l5O3wl6~Hz57Ocrn&rYXx<L7omNQ_W!x<c|4_nG-`Q9M<BeVu<z9j>=eYs1RDP4#xv^gvi<UAzyof1BW=Mb=bEa3"
    "laXS7KN+60wOvq2@Z(&)J$wnFh|U_G+*K*aYtAd1xfwHYbN>=nYIWwGKQbzFaVe>33b7cbwf&+*}wid!1|}fX@xvyLR|KK|l"
    "tdATxiYHCx`Sly@VWZ_WX(!>zXOvgVDc+1a`@6lbi0G+4~1FUQAX3dZzw9syE|A`eFW{%aKT)>Tb)RR2sPP5ztr4c&?K-KL@"
    "InVkv*so=1apg7RcdM3w;i>Hb0NG&S8_I!{Uo1wT%kq=0rN>oVja85ScXsxa-3=ouJLslW~c=pk7y#E%%Ifau2^ZWXUQ9rpT"
    "+zqoyJ(W1!--lDjjMSyHNRw4}YWGy|pFI}hE3`dwN42Fe;1hO0Ay-fy#A2{gZ~^NKvp9ms3%WJfdW`mRe|K5gA*0+VGU}F{6"
    "Dj3MaJ^Hq^I~4v{Gf7wpsbIRm=}#uEE6Uzoe$S+7q4eo=)@6yurrD8dFYT0oz~|r8&RO^i&LF6MW>hsy|j#txV13(8k)Cwzq"
    "K3260Wp63>EUqSL10&yLEfKFMgdV8c7?$f>xbk|0yX~r<JF0YM9p(Gu8(J@22We%Qxl6{lx=(o4xl=5w`xwJnnOVVz*EM7A!"
    "ci`E`OLYH4GFtZuF49Rmy2JU)HObO6qJ+mT?YMr#;A)TemQKeG7GrakAH1^diNq@&+*T1HX->+<8eg8xSY$~z0;$fla`KWAm"
    "mTo5a`>d+V`oS*B1Y64?NZyh$JVP#MS{qsYs;{-`>!U_S1R7~`{$y*@N(sInagg!74k3ng4shLBRNEPH--><gnlkAB|)2hyM"
    "8<oqDS<${_2}FoCXNbatZ^KAFugzAoJE&$JdQ6vqc~`$@PMFGa)edc_<9LmY7==G)i$wiF?G=*!o@5e~s8AI&)je^r<>QRU4"
    "Y=+MiTU$Mmd#}!dYgx0eO_9obPsz@huL8<q8gpaAqjOehw!JOA>mXkJHMp5lmk^cao3YDZ&_#*CCS?hE!kBHy2_c;B!kYz>@"
    "-qxj?^#LfaFk10@Z3}@2O|@$=@cJuFgyO_h((A?U)1oSgOQ_jvR8^VHR3kB*QiT!k!P)e5~ovWOt{X8)F=LFmMl7DojODFag"
    "cfJ-YCPvS^lELXj6%m)dR4(lk+0<*ZC<eQ7|MbjLVkX27WA<?P_+@B8Ce!!7j<N>_Jh?@e5*^DaQ`W^i9TYzbKzD@s1ckXvB"
    "Uz9yYbgh_f0?K+51%%pH)7jm7pR+Xc>r7leKjv7H6Q+M!xZ3(!4ZdN7~NfYa$Cnt+6(Q0|x<-6{5bs6!klJ8>lt}BV5d9)D6"
    "hLR>+nxd##B&4>i=8b0$&Z?~*4VYl!iri}LTd~vW#s)Yq0|VPemB{jLKI1x{g?q%=l>NEV`9y;Ry$=K5Va8n<JACLWNq_dG-"
    "1ALyq;$JyoO*jXM5bpSFFxZ3><f8+F!PUX*mX;gM`bJ%qH0ybg~;M8Edt+l@2Om!o%<5xnEeb>9Scj1f7jy;(I!6N8{6x6&C"
    "}+cIHI+~moS2pC`>0DPJ|6%THA!R;{+E6bgKElA3#K!G=~f;k<$N4h40y=O>NX`RsAhQv=Vw&-0y}9x-#-ybaS>3LFjN4>uI"
    "7~m2k>noL@42lI$COd9wfhGh&<Xl?6Dmb$u(A0L2L|tx9zPRl@t)()th!lFDt@{#%igAR~3Lz)|pX#S>m*8h|L(+gaMg@mBu"
    "=cf`(V+i98fd;e~)j8HgjXiP)w-<pouFOz@c7@9zJG3cn9-9Y-gw5^I0XzEE0I*D{7aW(2|x3pKKDL-8}F=v85XsVI~3BruG"
    "lQeW7E7t3k*G3D#M_6e2m@(3-1udAeNii1fQ^R59h{maeuOjhIbO}Y-s2OfG2<G0n^ZR4os)_CsdWTng#t1~gUD*!+`BbWpH"
    "~og~HW+?eirdz+Y<K6e2%4xE<_!;PvLwBS&(0aHmU$*dG5*Vk);3sFqEQU5EDyU_&+)z#@;(>Kd?Lfc*dCl8X^b!KPx8BH=i"
    "8|~yaQZKHw_&l3Hl=U$X5JsozjYY0Y4N)wgoW21>dJ5N^K=iUP~7Vr_)FC<Q;=J;AN6_AaNHLB5C04J>M{3nWIDCV<vHrwMu"
    ">$4b+(Rldk<pdSQ{pv`~NVZUS(EUv)mZmMW*ErO(3yOm<<y213mvP8g#X>Mpouiqc4(m8pfRCnBPdbO83ujQ34{8Ht1WzgdV"
    "O=25zf!Y|h+k_F37zL8=}Ol^ErZVq4D05U@nK}8#>*oV#vcxxvR;*p^^c+vDZjGW(XTq{rCEjyUoHlB2}md1#M&e`9#b4$NJ"
    "F|u-v`E9=AejQe92@yv_2ikTPiZn7vktPO_&Ov+sv_$(+_}b5!Zy(2@6z@~?-g+)9Pu9d7G9AYCi2oIOX0zh3{k}D%_i?Cqy"
    "XhlFU(nM(F>o?wfW*GP@7DR-svT-4jkgg#D|ZCphD0h_Nqc)CMVL}>_p0W5{>a2HQ_e%DFI(BU<U4ahb9MFmG)BOFYF(q;;Y"
    "F+h)xx2h$}dM=BfHcEym*r0B-U>f3Qtx$?u~ou=Z)Z5ywb@P!a6#_-4k<1INKZ_I5Y8*A$qWHQ;lk~=}}VMJ~Y!b0E)h6mB5"
    "Tg&N>G69IM}{`E9+=-h0-hEymE2;U)c(Qp}eZ@@`3{W)f%oTbW(;=yHFFLk*4_RNug$4o=BqL_r+@RWc&MO_eB#3OX|4;KL+"
    "02#8`(h}%M46y6W&PF(fKE>)o38^cV^G`Nq>`m@}nqK0R4*TYw5<~$!K;Dmqk8D})<<`Vmwm%Sugc(X6T-k`HMsZ(gvlL+sX"
    "=jhWs@%H=Msz+j?kQlMS!`SgoFUUv0Pv0Xj{Kc>b&;IG?dMfHw$d7}N>%ccqSOk8NZRIRm4fOcb&>)JaZ`ug)?k*rb&3?!I<"
    "NJA=?4Q=~An2f?5d;GZ&|0Er<3qK%lUx+>rHEDmZ1)YbVBeUWC>x2wb7Yh0e9<t$zg3`8E!ln>pDd!hkAHA^%=ct-C|5PQUJ"
    "CrMwTkTNdj9Eqd6MvfL>U7;<!5qdS655`{)xq~ItR_nEd0ntmEfo^nhvWjNhrV_MqzYlj)S{C4bLf>7^qi<m;xF-DN96(*JF"
    "u6^dCk1Z(>^s1KpFu;gQNI$Ms5Ay$Io`YlW1aak``(vTl)c&(@`fN&d}5S)cG%9;1v~r@=E_$IuF=XkQ%3KJ301W?8a$Ka2+"
    "WPj#|zqlH5~UC_~t^h-U?-&dW;DMTJxu(6lB)G75SI~A#pU1N22{D60ayDPVzgcZFOBOOM-o~P1Z61tdjTOg0j0}HXh<Nw(r"
    "4J|^;OSC6-%OE2HJ@=B8Q+(I+G^d-(5Y~Z2x_JM|2}`9z6WYuxyYPP4OnT_c3`1<8(^>jp>x_hxIce0qRhZ-<oCJ^7?v=W=I"
    "CG=VFQ>-Sy_tHH^Kqi}@fFs^1LN5Z{KnyE8@+MhCsP3PN4~7CtpeNlt7lFikwE7)+vTuB37kyr`l|(B?d`p(Aw!kYcqR-*xY"
    "vF&+WjwLnb`jgiR!3~lW*3Xf1L{KdIqF@tVpVm2_T)7D}1pBTpHG|pgnSp%V%bZCZwT||0KQm(;QsCd325!Vj>Oh?(K`*)1e"
    "k20$CJ}#2|&tltiPMhnjdo`m;rl;tmeY_B?k0D2bw$^&twKJ=wQErvsDbenRPf0=>%BJLC6Ng02Bras6I-8s+fW{8MKlZVed"
    "IeQ49FFh1BP#Gw#$?Lm=5hr9)bi90Wh<hJzLnJmVyT8|vgD#sU-(=_v9R><@vESf8P+{*wFL>lX!*3IjHVpt*~8IijB?Nfpg"
    "Bt||sQ8}r5T-C57VNH=d0Zhxi@&Q=;jKAZO_3A_Z<ssLFidz{^QEs)!nqE$sUTl$$Dbq4yG8}C*Vl^^m8^3AH9=1Qlp8-r5%"
    "rM(Gwi&^DUd5bQoo<!ARkm0Zi8F+PMkevJLvP7!pSk9J1|=9G3j;u(eC}|9yE}mV@sex1uJP%C?_pXU;m7re12Xu96FX+9a&"
    "oPE)iru{8W1-ErJ}y7YC6EYbJhoq*{}-gqd6T?5VIna2gD<oQ6$&;$VS4Q4{6ufe4;e601Oy#zoq&}0C124oMmQ7x@Se8s(C"
    ">XC8(WRXxeKmR;o?$M*!$2XZZ!?ljW-F<iK#^_#)C|Q?ov&R?}nEDzI7?Avquxc-@cp@zbtI4NBN%5n5S$969nZ9CD?6-Kr0"
    "IkU2}0=P1p~9-J5r-@phV#FblIHCU4?X&kidHL%YS_nW+y`)V&+ql_Q374gv>o@v-=v)M=d_jw2lR_}vi(Tq+Xg|-$c{-QCU"
    "VOruO%P#p}2*;H6mZ}{9?Nn+vXbn6UOIPkwI{%|*%^WRU&@~2uWr$p-(s@E+To6@ZYq2#Tt%#x5pl`Nj-JrG>_Q2&OoZb1Z1"
    "@&PM-o^xdj&}gR-J~Oc<V9_$YK0+jS!Mg9FkQxYwAa3=ARQO*tm6j;&X`nYp-dv`8?H>5#S@j#x(02(E7ESmy;u<Bkz~PVT^"
    "LOm*k^CT2o3oAxrzu>Tvu{uDMfn2YtC4)374fI2GO|W*D9RoCw<4%0G~+KQBNQHMNxdxN;4@vFe>4C-TwP|vs3ClX#3BaK|B"
    "B(qYfEG%)jKAT>n{?Xl2Dk*9LInJ`vzZt*#0G(zL3v%<b5u_BJzA<Vumro8bFIHlv4Z<p__en4!q4fBOP>zz-44%JDrYco6s"
    "UAqmG(Bj=tdQbzWyaq`CVI3e^lQMlxvN?x1`i~2puRx*D@e@QTPF4D*ao0#dAAn|f<TVeX8rEMD(+Ccqfrujp2P_?-!@yo?5"
    "kfN2GQ5NfbM^Ez$%rMamX%I<L^W)GdGuJx!u<hVZgr-H{0=2BkjcI*zXzL1D&!PNdAVKb4ZUo`3M41zuW|gijKebG7`z03oj"
    "U5B|L&|KX+L3#5nwgy^8kO{=Is>;QEefU%uf+;atBPG+YD`4LuZ-0-v0xMTtS$4~^BEp;V4r^L4{6X|eTK{gZMvGvx3^=nFe"
    "eYi89PltxV(b2_(Obn;1iqPp<8w#GEDg-w7vowcZtKs#GmC17m!7Ck|F)oQE4zgjt9_?d9JPH%R<%cOuc;FinE_cMT)dA6d5"
    "#{MN-0iR?uVLtwG#8YV8YMxWkRd<bJl*whoRm(+kk<&?0n2v|M+CSX_0tJ)hx#mC~!8fct*U$t}=+?GG49<8el-ASAosGl7V"
    "g1xCbbJT;MktGWeR3omNS^ywBw5Cyf%Ng@}bJqoZOIu4danH<;Mk?wh?X;zQ69y4mvF?1Fsba7_zV{!KN@YaO@xttTbdL85g"
    "a|g3bh~Sq_Ny}cb*r-~LC#>m{^&KHAwt8idD@ml>B|^ldp!8Wa@~s}@b*_x|(InyMrmaAFGrJWr{>J#w{|>0E_QaCqyxb#x-"
    "qkwA%!sS^rQ8K4UiM`c<9kjVt)?a`BlNvBC8SpJ7Z0bmrW&K|cDoQcV6cC*wk|9wAOGdr=RKA7Ak2wWQSOb~8~4CM&Y5~H0}"
    "pd<X>F3}vMD;$*TfeKnaos=J1REK48AvDzqYk^gzo{baEqIrQ({GhgN^tTwk3(n{ro$7->HLW_O=*ZxCM3MgLbEN^ND{UTb#"
    "+M4RO}vu_JNphNcaW3C*RswMZ41QjvFECy+(b<WR+<keN?|uX16?Q=jSzGx=a`qHl%nS77<k(f9eWut0yuJ(t;hm(jwbT_Zr"
    "grP8wfy#@|5$>Zb^VP^vmE=Hg$nsi0DPIgI$TE<F3G3{oi(N)!@%{ZKU>WXM3P%sW1O71+aOHiV^1M)9o4ueq>`V1Jlf{5Ur"
    "3Ug{{q|?XpMWDO!G|t2qi-chrP7zb%eiJLa#2q=d&q;n&iS@?~9K5hfN`JbY$UA5=3eayj*{tD;7nCK?1*+K+eA(bfn_BXyV"
    "wI^C&sL<?;L5(tT&gNzGB=+zMX7uqTg$VUYHiLOqT*8u*t&%GGh+6)UC^)nPA)&jR(i%-q7mfR=LaT(QW<n{AE@T1fAGB=u`"
    "66%26VlbA!M3HG=8Zaj};0v5Qv7bjxU2mMw_t>Rog+BR*^5jY>}KoB#CBau0+EeupuN-BQ+&qJ|d&FG%_QJ;9%nKo(40P-9@"
    "<IJF!WRKKOsR1ZaoW%sMe^+j0@og1Jf6S1Op<8pBbCj!H1lw_{i=Kq^L*m@0Nu8A*v2*PmOUVDgT6EaFB4G8bqzwvarf|HBV"
    "D75=}2XK5hB0$3zrzz&fgN8t$1B{g3v7p|=LNO&4rBJ67HCUccUT&~N<u=0hLjgjAS;eGDDVoM14BRtA5g8uB6vUcT4)duRC"
    "mnGivTC)CK5Eej(&#btixk>Z6PJ$gAt3O8+PXIvRuUkWIlkT<;eWeFNCrWuAbzO^shMZPVylh`_S-8R2om=nAxNSi`k{;!FC"
    "eIrtfl_v7XjQA4s=>ipfI6fb;d_!4TA;s5vi_(RMi)3gSGBBg>9WEdtJ>jLPD3<B9Bh>ho29H>T^^fVw(ZuD|5(_kznOu2y0"
    "?Ng;(>>oU~Ng&gZ}!S5w6v2EfGPGpY43WQ%b|c&l!ed29Fs}ln|8bJerkfmFJ>3z1TL3#S<+;gG)v=2kM`X%%s-SJ|y@Za$s"
    "q|%IndD0b_c?Td79}t<h&+NLU1cIt6TEZV5_^k39=eIHk32(1hJverT0xdbW)GvSuJ&jn{ud^5gE0{lKGWqdAHL)*_)HJlS_"
    "No|MshXMO4jl@5!*V)Qn}wRnh1k`Ud2ylC4e86xkEl^PKYk(X*Y<REt<7}YXnr&75dnV#pa>!WEa&&M^_nXB{a@bxy_VQVNp"
    "=MmnEEf3m%l6t2<*Bi|>gfYgI9Vf_*Rr>V8wqI3lf6yV6vku<Q8;izk3j1bTx^b6G@Xesy)I9rz02f<wJ{_k^rKj|c-o*~?<"
    "8SS^D;LqJLg~lB*tdn%$|mPuf|h&djF>c1dvIQ;NulRcba5JpX~vNCi3HM|Fe)a`9TGewmZ6Sb7%|{deoFxUW-<4ULUM9c24"
    "4Y6<fWc$s&oymRzcsfBx*ZL?Vy20GTZ{HVfrHZ&bAvb<78^E8dzEWubkDJF0`EY>vmXI>kcwppdZ^_-O){5DYHr70>zqDyww"
    "c`h(6m(s8uUWacJU`RGUP#WzJ7Du&F*82MCe#F9S6KoHOXYNB3`Lzo7=*b}b1GX|uH4pQBp(CW!*&_`*=x#Bu8&q9j~mx8XD"
    "%Tz*<#r+*zz<(d)WLTH3G$G47h<)q`n&!5bDH?MCo#!dA*^6Xu~XE&dHygh(?T@Hd|r%3YC5wa~{pOZ3l!jwOj%K|!go4Iej"
    "W5R9~<{A2vNy_*lRgnQ<XyDdl5YBHOI9xyGL3Y}4@VKf_0DlAT#*yJa#@8*}l+Oe_DVV8(PuxKyW-QnWcOSB#_fe-HRY4FG0"
    "M@@G*D-1LIEG|xypcd*&y|PC4SbWat9wMP0c$X)RU6f^!A=834SvSrtmy>+J$^_3A;*Ar<wjccqNOriTwDo#imGj<>o-lYHN"
    "#u<vt>QCHDL)bxx-rP5SCDTQ|d{ai@+k7YoCq4P6ID8C^w-LmTf)G<_%jaM<ct=OVja7o0~ntUwzQ)!qkI~sR+q8cZTj{EYB"
    "^r&vNqfsEeJd*2dGmFB1~cNnEtwHx8YV?~~>Vcpx=b=`Su0!1L0%3e?7H*W##i)je%f=-PuJ^2dM4{_+^Nm3<qT=<`b)eK)i"
    "67L6_h*TPX|y8e+x6KNeHNjUP=##psv^fwKrhf4UD4IdvKJT%4w^nSH#P|NML7<h2vkg9ab8&{<-`>!dt<P^5QkxHeBLwP0Z"
    "VseK?WoZ7OsBL9{x?gBD2n?}n3qBXNx0g<Ygu~9NuEs+PpqIlnE#(#avn6Diq7i>Wu_9~D*)BBbpd?SInqIcu(u@iWjbzpwQ"
    "S(uws;N3Vx759ie3|%sjhHIUxs>v&o@z#wATf&!4y>_536v>=LrcnMWP|tl%+>xnj`7yc1f*smtqoBR$P6_%lEc6DXSv-*L*"
    "XOh3;fR66cRJv-A^D1kJe^?v=q|Ae(+UfTE(-fV5W{k)acJr!v{9&4%{bb+b4)Q?9y^xlkww+jt46S5p9tf;ZT&%-yf_7u`S"
    "+nz752dh_69e!Yr1pX`sCH47cvKXT1@0)hte9UweVw&Qey66N%ITWE$zqeSwi8RwMOHZptR-@LV3irGTE!Z8FMu*O>T3ij`s"
    "eYKoDhx%t0QOOO2@+~|YTsEu5YUvo(D-f^C>h~$jj9fm~nnu;ynwM_!ajci8y6k;K6jukYz#={=2?ilRRq^YxergxjPUq`bL"
    "ezeTY{9-{x5K~{SFW~pDI6td{E?s6zp=gF#c{`}85fzu(|7deybiU2*g-%stzE+~(P2I>>_El2!S1YHzUZF5_j0)L#VaNP&L"
    "%&p;z2er^jIGAi-CmRNLacY+Bbhb~6s!~v1ZRBuHlX_HC_<pj>LPdmj7P9+nzB=7`V2n`jVR<y4{10yarI+eF&UM8Svd6-ZF"
    "@TrsJH+9xHEWaK-%2$yzPpuj2?D;6n2c>NKvd_B-y1mtBXmcu`Ft#LrA(y2hDPtU-$4{CUo`+2MK~|L+%Md{|z$GK*$jJZxr"
    "wTD)i7J2jKDh#*!TGqf1e2kVY19&S}DHJ}g&8pMw7Ws2yKNXHKhBp9!d7Fy0%qFemxbaxPlkw=|Ix_B$<P^F(?i&e9!i0j8V"
    "JGw~<ZAg%~jbFdPPB2}Z6!l-6fzLuWed67J6bLiBLx>{jIKpi+FG7Wcf6bfl%mpvjpexS{!_W?8h0Bqhf%;3yQOH&cvO_&b*"
    "{gw{9k<5|?*Q{JOQUVIZ{gHY|^IHOtJub~}jSa@kEj#m`Pcup<NOtI)Xvs)Hm1qo*qU-@4jO>*FLtZl<yo|GJ_4%NM&Q-fWC"
    "oXb*RJ>ugd@OF{3Qv!Sy{UZeKg%T=@BFGASD4!^F%M{VPALqML>e>Bve|d%j7ESzdj*a%Kl%Md=+J?+n;sMHcSY!a!-C{`dr"
    "ZCXQWJ&UDPf)Uo@s@j)T<s8eTA<q8iV3%jFH9D6c(n5hK@Y^<1J>Yrm@+z>s8w+niJu=a3n-ry0}7#zuq|zWPmSd2vq73a;e"
    "-so!U_q{!dexrcNjA$C<#)U2{2bYD4o_&ecm0YvceW;=?=eZGXo6GP0%n_L0YX`|_MFcP&gZ1r4q74#;iS{{5)j-V?{lJ6W6"
    "PxYhYZd?$zPa?<&-rwqAXlagd<=5n%PX!r+M;xQ&!zIWUSRh4%O(%@i`>#$A;e-@U=?~M6k_p_vf;j1fWF}f7n+pG%U!K$!x"
    "vXuBEP;<u2$_;%nxl~qG2^l0-_<^x8Cc3+Z<Wn;PM^^DXCc_eNXP2vZ=4f-z(}kPKk;e_dB1`(qdAej|Ab*oux^Q*4F!<iEH"
    "0a7^<bZFW;qqzT%YA-=o#P8yGc@6k*x~Y~hAx~!=@`U!&4F5F3E4P73`fzM9b*|jwWsFlX(ww7b8xP9=;KrSt4#M)pvY(n1>"
    "M>fU5VipH;(<okK&-(*4@Cv*x+%)GD;n0WD==5hCKbXMpoqC*&7JtBvqimoe^JYE`Yh-2%WzbS38nM55gZ0a^8Fm2A=XJXi1"
    "B3azY1WV^BYbRG($Zqhk%*(u>!zi~FJz67A@fXUAEXk3)>fqsEN>-$X9)B&{4I%_D+l*m9GyOskC}nWcJdh?m8eT^1!GT>QK"
    ";X2gYmLaW7}N3BrhG`K)+w!E&*)Z7r3@|2X#iX9GeEpVmYDx{%?WVOn<^dq7}3jrjU=A0z?%!JMDLqt*(kWKIqk&EYK5dR7S"
    "wEsZ}t$^kGaq|=F700$MOSDt*(Qb;SIdbb^&tz#P95q+HUxW!VR*>!&CA6t&Nt?qvn=K88HFLzg%#iV~__JfXEcdvAB#3!O%"
    "%0g|ZZYA0Igk3>uKAd|Gr<_J%D0~Da8`X`LX}k~SUB%@Mhv|D;*RT`zr59@il&FaC4c(xC-KXxrsIjL{}lowC!dS)r>?|Ahq"
    "|w6z6V#N1d|O|Rb&l{U)r9K)kOC3aP&{oF~Ys5=t54B8@cp4k%RiGs6dBacI<`4O=>THsa!qmtU~qxEqU+VxR}{I8f&MmDr{"
    "KThPSSpyp8L5n|Ee%xt~AcNs!9GUo@?ie}f#9x88k~H8IUg+bT}eY&6#mdW=lPHMckzIwYre&b$pvujn&$djD6mYa=7wcykP"
    "77Tj=iL#H>X(`qjkHci^8Fc@zsP~qms<DQKdkAtRTP#K{plMk=1t&MHCZcDP)E_?&Ar7DMShj>$0COokyAyP3oL_9T~rH&EQ"
    "3^-`}sAET?l?zO|FENQJ5xLt7s-5d~vgV=*8E1yt)#uM|e14trk%TpGt`gd-ET~YL!HT#zK3ynrY4WOTF4T%ACNHubDdZ}bz"
    "M;h?wFDyXQAem(3eZYjJ307|3d7e_KLI0L@{PkHlb?X&*(fq7Qk0*cv-RJ2Vl1|IvG+?jNNQA8<DIqrT-OV;dIO_Ju6^FfU+"
    "Hsz9+^d4C>Dag72YGYc%%NKbUVq>wj7MYEL_26l*p%87A{Dq1+vdTmIc7tdr50R=t<63kGbriA>^JC<r@z-ORnFu`+zd=Z#^"
    "(E@?WElln~~tVcr%4YA`zF{6{kBgxU<FRt5hEbo2Sy4u1oillVM1yGr2_*1ggGflf$A%cZdQkdVe42HW=q1vaj`jshr5d*pm"
    "WkQ(`7EO9~cBR#!Otyxhy&=Ub5Pxy-hvIU_)pM~%PP4J}eJ9KKQzL{4Vz4wmJc|JrfgC3z7cl+MUXCPE+OdeU1)V3LA_`_>f"
    "XqG{`zC^BE>4=|t5fU<WL?I?k4GBE^a5wjJYd|5#;29&CEKR<4bl9&6X!654`=78S)#xkeu&1)(HCDFlf^R3hE%y=Ee*8Ue2"
    "ta5z7rVZ)rI)*wp5nma1f$__`z~`Zylx=v%PUWmkeK{^M4?2X)<I*eak|IBw_D6IMvE^wd0Epst05RMS&|L2VYjsey0iPae<"
    "2F}zYu+OBsBD&fzKitLmfRPHExj)n;#3HfvzQbTM`roC_y1}>s*1>7Ad9{gGbyW>)iBKW4CpC{A~YP&yGSu{Tt#YYmtEMbdK"
    "PKjfi?)dmhEZGqe?x5tqx-;)mu+->wg-MNF*;7eTi~ZBhDw2D3@6m}Bpa@qv!UjhQXYF<1rAlr#5x1>+fdnK3QAuu$`LG|rJ"
    "CT5)xbbp)^HIQrz5H90>~^64N!F)8+sJ7yH9^4T>J6=wnefZTwNd#riy0D`DGAN-N0dY?Fwm(gxsA>@b1?UlFf2_GGL7e8$("
    "^o4BkBE^aXX6k3l&#X#ffu}qv;&6)>h~etfJ$^V`Lo5=FcDf~?jtI34jfxBVXjHG<mN$ytM_SH~p5I-Fd&RcsykEK*!sTwt*"
    "9$vlisVC8OXbJ_6HDB~CiYbu7*5992}dxZW42r-iRZB1FRxejq^bBS7Zs(|W+9C6R)Jp?){e3P-d<4T`CR#sL^_=RN)XBal^"
    "_aS%5+mH>v5J>O61XXBv^WTyqTsA5%rR2=k-g}x*7yEx``v6*^IDHOb`!=ZE;AcIR$1bbX!g<U7E($`u5|}rM5&DPi)2h{Mg"
    "*n1dLK`II7i=*XX^j)8DpKBRZ;NiELCgn|hMR-72QEYe@;jd)4p^hzX($X>%>;moU7pAk@p}J4|5p+-JB~VJuv1ZBS98Wo1H"
    "(1LJp|q(-vM>eNYUwa0^H=K;S&!B!rj<K@YHthMAA={M5Cw%e4s)k-L*$&a2TLEoAXA$Z<zv*I!ZhSdv)v=mOZL>r4T=y5kk"
    "N=c;ExtrgDAD*IV+xPyDg|m!`V_TvyE<qBU;DI5yC%6P>aCZsr?oMzC4ueB*cXtRfxVzin8eHe)-ur&_-(Gc2@BLNPUhOYX5"
    "K<^cqaftF$n;V?>HovvCC4w@eZ!M0%NehU5pmAE$aCL?JS=0KFqZs`V{y^dh_8T4r>3$JeK%jVs3_v(Yh@6XvVWyx4#fJ~s8"
    "aDGlmgR%Kjn*D_yFaUBhbk+o8MEHW|xTrYXA49e_D2k@BJ&W0j&*HD>FXyOkrV(ab?!^o%M;*uCRDt8`9lJ_Z8wsG(iS7l@1"
    "knvCivs-**eQxQNE?atf}Wh?g3T85aDOj>0Viz~4zyLykXh&Dkv2{e^&T*UQzHoeXkn?zUi^D3>^fG%78WW;iAwZK-<Ad|Rb"
    "fw7qYqVB>t0^Pn*=_>6!CEl%gUCw?7wNJjj<u2o=+U`T-=ZIc&e!I2T0>lWea6VlclWsdh=pU<t%Cc%%chNacv>ETA(3;fku"
    "*k3FqS4A;QdqH#}({57Aj9k{I@0sFXahL*%O49t~m+^$*4#w_m)atLxUcJB8Fj}pwRUaI)$1~`Q?#Vfu4w5YC=xpgkhdUw;7"
    "^N*o23w@0=w*>w`ntswC_#|6FuS9X$y*ZJFIt1z-7f-{LVxVaUI>k8Lg~EF1o#DA5~>+vIFMX!-F^q7JAGV8Uq6F<5$Yalx9"
    "bkF6<80R<d<nw&y6Oexph^{$%0GM3B`Z5-sewjxjk=nda)G15Rz17ygFS=A_HfzUqk=mDc*k^pTOOjgowW$N0yVd-=>W0fhn"
    "eaF0)BveV#JlU-U9rm+olI)|vOp1S<?16;i9jOR(Q+x9V0E-;LAT#3aBd_p^wDDIT^jRB{DuK(Res2qZf^AIxb)B>;FP`TD!"
    "|Y(7DgYrJ$6_Qv8N-7b>_>_}4$Z`cLe%)<VeUmO4(&5WR(03$YqN@c?%Zv~Y#PYkXNH)5gtANSXz2G6|7kBvF}Irut!Qr!&)"
    "j_0lS>)gh(9wT6UtPTl0@O5||ij2;yX|D6=!OK|UvPhOF{EiRa{dKKAcxZW;Y}r0rBX4E7*G1!>->-FKKj(m6=1no*+>=fl^"
    "dpAHCxB{c$knZB_v`LL_U(@nk))5Z{H7MTq2M$jx4?mE)Kg8iV>M43$IOU*zYNY^Xq!@wfk{*ebkmV*W`u)}EtKhrt0}|vH("
    "<Gy#e_<6#x~)#VvV`;TQ=ka0xS=hs!sQ}Q4Ag5{O>Xq4LPE@@2oar{}M+BqsjT@Dvkc$#`A`7)z<FUGJs=)?nTN-YB+(VoU<"
    "il9&e1X2`AQAtFZwzC6CJ{B#;k=vHSaq8=fajFGtgYD8`+%>^7LZNhuPRJ#1SV_d<iv=Y54K&5{lPj1A)J0rs5^>0u);kQ4q"
    "1&qBZ)YuGwQ=+K#F_>IO~kwhYxz89$6c9pu~kDKimW0c$feBmiz@V2t(`AL)9)%PPj_qU#U<39eS>4>jinO;YN0ef>Jn&6Ru"
    "zO+e=QK%(G*mb@^Y}EN~qX5c;{I?3sH}N?|$U9l>OR<)cSlcU;Zr#(iqD+a|sE4nICH-DqP=Wi7Y_2s|0<Luz_*Ot~x!TqZV"
    "7iCyIN!J*XLd|Z-Z<jR-kttk36g^TAlRhEWskcXv*jXmot3+P=a4(bWkd_p5}-v{?8z*3ne#ygUopX`9Me+AfE=e1W6A+f$v"
    "i@Us<@H5`mfk@5OG4|3VXk|R7fQ|31LN1zgJ`YrCYuHJC%pfx|~tzrAeIx?i8W&Ws?Zq!mvE}m%5>uiKe$jx8ov{_Pmdan{J"
    "t9(eGMdstml^@v#}9YBxeG$1Xx4r3V?vv@>tyd_}&a`n}iHCO-|y`d#%zP1Y#U5#(o0LsTfuj$tE`U#fD6xGec`kVJpXs{Jm"
    "Ny?=4n!JU!axC)iBTy~<^){;_Lr>$5ad%UUPvfwSNh*qB6M%nYIu5$&Lgk9V2VCG{|rt^e8=LtKvn6A8b1f4)0WdxB78xEr8"
    "YV&1bmmrgi)~S!_otF`$MSSkrm!)&Menwv^KUaLk`f}rJ{l(tiKMwkkC^RtX^HjeEZCkZ0XYL)w`6+buC1~@NOjJRruY&|Fk"
    ")wejcH&&02!idu<gSVaZ9N;jvlnRX%BQ+5c!CyjZQr@!pkpMCF>igA*726$RcOw8V>xJ-Pa94Bxz`D@g*D<QVJaYQ!$cELAx"
    "9_W{Kr%;%h*W&5f)R!)f&RSA4galdLy}Jq$Q(CPNOt@Dqx9-Nu{+@7)`BH6Fs=)JcAW7=j_p)8+5(;>$Qd2XyPkwS1oJH(DE"
    "NR9J5a!;*RIZ?_UE>?7e9g@qABPgi{gBRl7LfjdJW9l;Rpxgy^lj)w86#`h7&K$uRoP#D!4{D+@?%a%@;KEBdG}Ym0PGy1hb"
    "^BkX%@+;Jv)v8_S&OeQ1aYIm}pO_oNYH;WtbrS*bptF#nrL(2|acA)4O{to`t!}P8Daqh;(d6c~1>vg6$&v=0L>XDv4X+TBP"
    "9)wiYoF-YF=Ck^Jq2^5KPTQWF9pnUzX+7QTsJL5SZPV4&*%|%a4|X2q5bj*^s%X90Vewp#|7A<(S0&1f>9l*magXKaCxw~Rw"
    "7w|i4nWaf_@H!|-q+umqnRmx9u9v2)&Oj|sa(#`6LDgB?W_z@W#;!?XL3^|%A`2}jaXV~Wd`|(q?x>yO2iiYH<c}bxjSbBX8"
    "4j-;Oex5zaFm~XWLcj-}_J0(x!a+_bkdJSM*J<pj=`4fDt^YfihX|<m#?WsS|(viYXG*aMv2Ds8>d%UzHOkjW{%8n3#P-gj}"
    "afgQD)6vHplTIfl0JBUi%93B1uFsF|5=NmF`MyfC9<^8hLeUhF#Vi7s;{a${{N<zQ+~ZgV#tsrmM!qFe<$OM+0Zx`JmrU7I}"
    "CegYa8)A$9V(+2(+A1Jc6;Y*eG#SVDmSum1vj;kKTdn4x*(?t0^o9inJAt6GH{ielTRRSu0YGo9vcQM^$vJQ~46V>w4X%e?_"
    "gO@VzN#hJ;iIu^KR|h{Y*QN+esDJqE^|^Gyq(M0&%`_vKcTO)BmH|?|PjjO=hoRHX@)%$PmaiTsm?f=Bv<sTcG5Ah%IngBVx"
    "BsL0a+2&306pBz+1cjmWXd>!u5hKjZMgGXRob6ebqnxI+cOpL1sY{;QKw1!obHEvd2xg4AEO3jX(wvBP7jY}sO&r0;ihIqov"
    "h+k_88>}t=rd5NtJjZdxr`B8KkU~d1+DyvUgBfpyYJi?(*=qtDAF$V0EHgmFdQ(zdclWpUXenf|P+CWi?k3FND+z@aZ@Hb=#"
    "!K#!e;m^^}qB=%{?1loPwW1Cs0bG1jQA)|5tp&!_{Lv1LfCZ1C=z15ArIGq-v8(K3beOQ+f6A*U+u`CcJi#jOWT_wn^q%A12"
    "g_`KuHFC9kh%u0kmb`P!6ZenFzeLRE3;QG-@E)AHO@4P3~YP+T;GhYStuu>YKBcyeX0Sl-8L`V2rr^|VyFf-icX`>as%B3n9"
    "X(4@*TTgl~LF8}f29K-u>`78fHBIP?RMeFx-T`lbf;sii3R#6|;!NkIIe{C-n0^UNU;A%`kp<N&4A3NR;M9+Nn)D~@)$Un3$"
    "o11{HP>xjKK0jsE3a-&knuv#e?*xHml}BJl2NQyR1_x-56MNaB+Ff#aCQTYB_Q<tZlR^p&0N><nh6=En^{S~7r;a7MqX*UTz"
    "Ed;2esQ5HP@2{egNTb^%Kg<Vn<`vvwn@%uvL_v1_zT3N>c;z^BE<ZA6b^kj34>C=bKYR6Y?!L-(9mKeAi?#EB;IiEA(>Ne(2"
    "&uL^aD8EjvSf;K;bsk}FTKTuG%i?3r7?{dD?)k~%{?RU4sH)P7PPN#wz5lPzoRXk!DdPt>fK2t8Ee=f4}ElyMtQ_{_V>31?e"
    "(u3$A)ra3e#1D@czI1r4uB<wP!4!xyUla~9N*`2v3i^7KiO~dHr+2W(jjO`fW>Vxw;_NeP9ms{K!V->YTge8-o*yZd6$RK(b"
    "*QRZzf;n@BBpF*pJpd|k8#|+93?M=Khwdn|b-n|ecaJk-lhb=(f!;%!bU?bYn=XF2E7D)5Ke=d26j9(3dOVbTD1=@SR3M}M0"
    "w~>Q_{LtbTzC@bq>!w1P}&h;A%BVp_bXZ!p+c)DOye1DgEpS@l|P<Ta~{<jsnf^OU(*g-H0sG9OB8lVg=u_7{e^{8;1*G~%N"
    "BqCkR>`9MZ`ziO5)fl&!^7okLem|J!)G@9J&IpFDGkB4Ly4&=(d=(wm3gZ+^ic!wK$!LI6I3_EMMzjl<MGt-A;xjhGA0F5f{"
    "m3vH+x(l<b{6iI37I6dlgpm>tKNH71F}!WcEO)0aiXIEg^GJL}=I>%cIhXT*%z0+uQ03eITK^a3pNWA&3mUYtndoZn8flDT&"
    "xPG&Bh=X}UfAH%+3q-|~f<pk;fV2siP_Ihau>%8Mk&c%Z#q3|6lR#hG9Y%q7ULwX9KLTG?EVg;Q;fldqLgkmPAu#QJS0C@0%"
    "t8?BR>%QqnBbnosu&ZK3X1??jVd>?3D{<|vhw8L~t07reGv3X;cEqV+DVW&odS@q%N#&B)6M)CDj^O|?&R{q)U^$rfQ5~prW"
    "+Xcg>kQixxY%01@a8gjIqCj}Sb%dfB}@hT^CuiX57!9z+IA2BL^TC8<Vlu`zz>Wh1)B?atV8|PXn95)lg>n6=j-qa?d}v9|E"
    "R|lvH~uWYvIJ>COI_k9#)o6*Rz?_ZQ*adt|Kz}EEAcT4;gZoey{KDd0u2}j@T|5j54*m?+kBdYX_?YF-Bvkq@_`&X6Eas<z^"
    "^@xNE6Ds3vexCpZf;7nTnA<d>0~mrhL>l}6*pk7*PQh8IY$Ef1_U6wsib3{=JVtZ-`V);F(BWUcdk{~nj75`=35G#Ug@9-9M"
    "=bT=?L!ZPuBc{b+Y9K}d*N<u!lX&|dj?mxZ>u3H+h5~8QT=l?Ss(Z|BGMZ}*WS9Mrjt+nOK=xnUt$*xOk;!FsM&d}seK$sGM"
    "8|Sfmq*3F2U|A(os{GxPE2>!TbTE<C7Oh;SA36?PuRVnC;&V)p-WXtM-hJ}4flP&)hOAXgNxN2f?nx0uoWr&JaonX=dt~_%^"
    ";U+1TuNz9K<CNhR4*gTUoV+bXYapm>+_aRJ`)3DEr;xu&f;!?_#!0W8Z7-up>I;f;^ebU+k@#MjBVy(MdPS*%0vJ|H_m`ntt"
    "nj^sr7OrL&n%d|C{P@ob$UeWVJs7%=FokImB07(-kh?SmUMo?$UHO)ur1hIwg``KXu|i47u_>YFt1mpy$PY=?b0KpUzK@d&^"
    "aSK@obh1;$R-!Kd5CV#R}WY9dvQyma&g;1L_V!VKxTEozS>Gsi4IUtYd3noQ|HV9tRI^8E?E<EryvPIlWLmP_lO$GURG0c2f"
    "J4AxGmDWPw)$I!NA@hWq<6cSH+n|IKxlP^<17^d5_ga^z<rx^QjjHCVuj8$*Wu7`-f9I^9nRN^vHam0`@+QZK)aM8XSYx4?a"
    "7l9#0Ddwj=AA)djR-}zOCmLh&+Pqqw>@N2_$D}yge%Ro5yC29KFJ2q|4=_PtF|1~HlSL+s@6-^EQWVJdNbmgulnX<<O}4!dI"
    "~A)2KD9!4{YM#D(B8zEo|WhB7Nv>5SGKC!!lM=>T7B~-;qX2r)VUKxw)aQN@!foW2&#VhTD<t+IDy6B?f5CVMt@@V;GlT9)t"
    "f-(^|eIm=p+E(pp3_*Hpx*gI&JU6bLB5XacR`tN#f#^XL*#eoMZ-0<(FT#%p))5Ux?E^R_QVA!vA2iK4OsLq3kXomW|w-7DK"
    "&iGqWQSQrT0f+3{M{-g>f-;jw;hO-B&P+79z-w9GZG31zdYcUCOjDaQA-#8bcqB-2-`GDSC%O9SxBq<{Mzfkw!xJHmOI`(-Q"
    "Tr)Ec|S+^{wp4TubZJB7Ph^ikD**h5Rh9D~C`n#Mmj=l=-f5xzT|7idWJ0t?i-*!KIMlEF`WsU1k)7u|eQkcc8Nu#BGGPTl="
    "5ym^b^9Qym{7mnU>HY3;n~D(d_aUC-)t;70cu@L?CAiTZbrNN|V-e3<g>7ZZRC?PkCw?~eHYzO+qd279MtVdPK7iH{n$sq>o"
    "A^b4EfzWz)Nwv|Qj19%?>XYK!Dzxot?~<r;&tI0c~0j({?6k^r|1vmr}1B~m5<=0G*}`yLhcq$@8<K69qwqqF>rTIrT%^lTu"
    "hn$Nb$*vxzS>D_@~!c{Dn{0>Ul?qt@~Q<d;i0A^q1Ra70+lb(V~o3!n~u)RZ--YuJS12KZst8VaLBsIOSMKVX!YP4v=g;mTd"
    "g}OubpXqxEf_BrC2PklKCbJD8pshf!<i5*<GSl@{^?e8BQWGfBSlJa=)2$54?EhX)(G+NGqQSAOIQgg&qGKCZQI40Lv`9<4M"
    "XlB6xBhP=U+y@JyOc%)c4B(b8D89@=t=q+RS=Ke~|IkjX#Sfp?|ZMZkL*fvaXAFUA|Y2{1yeey_k9?#67>Ij^T%zfoPhUnD+"
    "nd*;W3LV$$E)B_P%g>aJN0x0iQGgji?t->gA(f{T%+yn&Prcol!^)eJAHa#Kbh=<F`sBy+TKE-#fyre>A?wV+f20o94B=lJd"
    "ip$=JVq!(ZBwHz+St6EEUg)10UZtGoX()g-dBbun#Qc_+R4b65JpYwe72yT-^lJaI_jqg{(9cAtA5VdWNC1^es)G&pJd&_{j"
    "Teadtko2l;a{Z(TG_s{^6ZX<-`WM`CdtFgGWI@jJge^N?jiq1s#3-NXjk6nkp82i)2+Q0qObVaqdY9_IrRQpW-;!S*mR}KS<"
    "9OA_XOTRgF4s$$<3%XJ>|1c5Et~i%p@ZO_BAj{>#B?3jry=wJn%B8W8!2)#A1cK7;xrnWkY|!C$a;`9^&_Pq#kSFLlP<g`!r"
    "&`xQKE`#t)SLkxUg5<8w<tMjdOxMZVyRVI}mk2hKW6#EbN&$1}yq!q+D*8~#zk!&yHuK*j<0*CsURT8)X81Rfo>?m+~+<>t?"
    "RA91#96S7K)1R#2Px2#U52pSh=qbPDY_lwhke@n_t4R4!_Gvy6lZy=eI6wR#iOTer(ys{$k;e8tADL!}U|qhgl#4sjFIYYF5"
    "rb?;ENgv+_%>zV7X6b=EQcKH3;(mi&Gy{VG|i@4ovAO0*I%ObS=G0*w<&FImTl4=dL_YXNmv-7?MEXT!^jS-MQv(qyq@4YpN"
    "bs0^?YOq9Ut<EylZ+3>Wt+u0=IOo7c@mFH&q3ij_#qCzBTi&aKSP8KiB)7>#UYj%ZvKx>aG@kUv}XV2_=7ql~r&$k!ydvlH4"
    "dSpOLBm^RAlI8JPFmC)*RPOC=*;sASi6StKchdpx}<jv8UMK<ic3z;DWb-?q9AS&SDO8~Dxa9io;H%xG*aJ~HiM@ww+19%&b"
    "wi`a>}l+Ih$y6xJ#BlxCqg$>8|P-v_V2zo|EzN>e?F<EtoIb#e?eOqYec``SE%-xe2AMMe-n-9?El2kfXDpxy8rHrWLephcS"
    "5>fa|s#H27>O6<Cn$Za)Di0^wTAk3Hquh)a?GzEw(dSP*BvHuQeCFd?9kz|Pt+{-4y|K>aINEeJM^jXD?CKPw`53|ctpbNX@"
    "2y&g7f?Be`+IyM4#XZqF#!`fRVO7Qj)Z^Ua_e8o=lS<gtkM3BX;i<nG<tb@0h&qk(1L1{VlN&F;#CFeyc@7#<WO0CqkJs5tV"
    "^xv#7!9fRLOA*_3d2Y>@mi=Z@6$QR@NP`+Xyz<ujlHd+)w?Qj6i9=+w!1Z>!*?~AX-RzOW7T?vXc&MQq#sZM_fo@=;<OX4|;"
    "ZXtO7e%<-}JPvbQ`PU<0%Dw%pM$1u>4FP6F#_#}+MaazfvBr%JAdo4fQT^KhztZ69ua2d2v^Qi|O7FIgsJ>EtQ`7MLbM=jaI"
    "s)bw{v`RRss6|TY)&D6tbn~RGH5U7C<G%~rs=D6a$@LRGzHCC2vMbeP8%Vi}Zj85h9lB(L64Q7nWwmm^n!%#K~<9;#015NYB"
    "K({wk^3h=9-fzR>Sq@hKQSyD=!_xgn&r=}&J?XD68o7j#0%b3pQQYBIR8b;3=9~^A!dmRNEbJ+NdPpk8QUyXk&_rLFhVqwM>"
    "*49a-;w;z1l#Cjn-_yWrT|K99i42Jbm<q<<RJwr&dy$JuZNO?0ro*0UqyL2OWU1I$cvSyQ?8dMDjfAH_h71iA|D#YAWYufXy"
    "nN#jWip2^ME3GvPpPL|BZh+@UZ<iCW>>@RDu;ETO6`q4?QCY&odov0-ZbVyLV(FSTOb2l0f352?7{HRj{N3)82$rGY>*1+%}"
    "vS1@;Q(7w$O~&lVj@Psz!Z3T*}20v{Qk$#;_yKeP$fh7U!MXgiasPnw>*vnUe<%NF}yJ5&YSiA11RqQ_>kP<DNc3x>5V4H9S"
    "{dPr0drP?aev4@cR9OJO(R5yNE*tR@`d1To~;x+_}g-||<(9mm8*obLXh1sqmDE&H{T1da{^ee}Kb<zbYcDA)@&p`{VKV3X>"
    ">&HBnOe}`Qo>(t3F~5{cl0js;FDD=P$X@~O8xA-NbGWzW*@lO!{-eX>J~@wlzDqc>E^|~P!htkZ_)qqx#_#2Kw!%{koRh>Gl"
    "=_`mt<UTQ$ryU$x8jqKzOFdgKDj1JUhK;RhmgPn$H?EmKZJ4Q>`L!o)8|Wy;#tAv_n2+GX~HwK%YNLYp$n!AU;st$=qHTdqE"
    "()xk_AR-gvuVXpMRorgd92#Fu1dyYw_nW9x?O%lU&dIj~mpIR(T5q;=7OdhBR?i<VYz^jd>m+zl5wEWk2*)fPOdW`oIOsM)1"
    "Xlv<-z6;_~MV;PkPw154v}UE8a3MI-g214wzyoyC2T<e*DQ2~!dYFv$7T2@`HMLb3U}stH<yz-Bj-!r&RZ@_y}ek<Z@5IcTU"
    "TO>J;Dz5rp7@JeO=+KTc*S^jo{n4GD%s|$}USUZOO#>#y!ioh)Ro|N|&hQrBw!Qx*-#eLnP5;_qUOZiVnDfaG1rqAxiO|The"
    "g4?Wt+V!^{B1x<|AM@4qw)*t=9(Rg``cnMfaxP2xHomztg$j5}`Ck%VZ+d4w65Q>g#~eobOHvhq{|w1AHb3G*S|vfch_<#@`"
    "#^tTBTHCr4bG2oR*~3;A05z+>D$eut0kGxYm#Mp8KzN;D(>tszk&#p#jJX}jjDI8v#c5eI~Y2l=Zmwuo@4JZl*uy+M6EYWBF"
    "I1LU^AfuB?iV%G(lDI2-zV{Bt!`l^)}d}pCgqkl+(-)J|Cv!xL4oQe<4KA!1zz$B9}uv^>RJhYI_<?Rl3XwA~b$|cCM5wJj2"
    "5a;1F+ixi%&;MYF5?P<077EN7l3<Sy)tuiBg$KJjk9VZ6TUc(Gpk*%Cq$)N^s_ANk#ytI;Q>|Eh7_gkdg4+*w_&eJ1wKO4#P"
    "a$OhQ5jNPW)u<ZG67LCydip<JCQnhM-P%QLT5)NBM9EI=W?U<>xS*%Yx<-qUs7z4@0Sgk|JZzPwIntalXCJ|NQfTh6mV6a53"
    "H8m!fL8MqLAS(|-wrk6}=YKJ@i*!!He9!utvT3qc{TA8^kDPkMCt>V?;BFZ2gsT!cZTsw~Yw(db?p^noH%<9h#=6LE?JN&&Y"
    "al-0(+D1mct#<2&(-x8n~a*uAS#(CA6K6^@h#Ox!-;T)V1zp^n2Rn5W<?<q$19B^70`q0E3??P(0BshpH|mXAU4NIoJzkD1}"
    "!S(bp8juaHBNw$?bMgu#4olm_^anUq68i{2O5?Z-T`+p{pJ6@-xcxGDlV`z0~PapOFU<@UqX+M-DBEXjr$7`c#>2M{cQE85a"
    "ry3ut%QJa+(BJ(hMWof%;ltzmXR&asL5@eL_<hfo>um@s;Z`CTxLd~Hi%7VBna;=-t9tyH48%S?kzyJEDDvx6W;fV#E!f;8j"
    "xPNb%{J+DVZUb7*`^KYe@AmrS(q4mYnsTdf(J%BE95l)f|qObiSLOq1ib&|%>Iav8^ZnE68v$;zmraTcwi@~i4A>o@r*`;~+"
    "413j<&O7reI3W+vfW6?vse8_EBJKzwo*x1Nu?85Ix0B|^@a)C*5uK%HQ*mNp)ZXITg^@n=#tLch(iC_Gs0bRb0_)@yZUMliV"
    "Jc~C3jkY}MqbQ#UXHPu3=PzHuLgh8X0^#SOJAU`H7>sK{ras}o6Nd{Q}B12cVPTmB%ob$0|`6nyDS8&!oJ(Cl#Q%#36)J@B#"
    "04s@ceAYB!5Jyr@-xR$+f@#yMnBvU|KUE=j*W`+D%&hCf4mTpl(J{4+yXe(Zvfi896M!X;vY|qhBG3eH!}`mA|{?sjD;OXsg"
    "1t6-r#NVYFoPQ?<OzTBjJ)@Vs*+AlvkaFaYPlv(CxH3!}{?Lf^>CZS}Fp)@LGHtvmH0=k4RVFwU-rK1f?e#Rjz@KTZVYQF>_"
    "aEl9E4@l|JYESCQXmNcMAc*RZW^;ILbCEY)tt^d2caBVa#uBk6pXAmHwW*v02{8YDw5hn!^y8fO5(|McP2a?H^M%h6DH=^R>"
    "YZCFxwJPUV>i21<_eH^}&P_3`d9H%7lHWA3z;sHPim_CrTPIb?knRm!b{jvF;pqh?E%t8`It?LKaM?~4Vi+W=k^nW)QOR37N"
    "JeqYb%%>KjO5@Tr#IPYSt0xknG)20H{-iu`~Vf0ZcapsGAV=fq)n!{)gICvL*lMYsFDfGh|NIkn`n|4E*2?2=+kRF`9L9)AU"
    "k?Pi}6p%|6Bgn>B%<`Zq4x9t~RNl6(G%2xLABDP=|1eY6vGtF?h+~iJfQtHR0^gWKT0fp@sKBI2~6ptDYA+=kvhOw_cTolM5"
    "nFVj8en@|Vz2+8z!x<6sDX#6bdgT7p|SJ3Z`-nJ!+A0?K6vw=xF^McC>mr<7v+Ev%v}iP=4Qpm{bd!~Qwf8rUu5ykNQ2^m#="
    "POKIfZXMOx?YzE*~E0&?sZ^;Y$3wuX%Vt;gX$3GVYt&bNoVOH|0Plwg+`_Y!DW(ILY5}WG_kgf?pM-#Km5)1jFDe{OaogF)7"
    "YtAz^cC5PG62qOl=jtRph_?4cppE*&LbF7QkAl`VA(a|t4{VD2sZON<|GTpzi24U3$z*XhK(mljA`r>Hmi2eAi_2--qgr=ps"
    "D?!B?%@`+&wXP+ZqWd(es(U5W++M!K2m~&35}Q2#)T%lqdMX(WOD`~?s^flx`$cY<a-lE9lAp_sWG_FD)hI}>j3?iI?)<(cR"
    "2>l3GuuDqCj~|(~T8A9WzfkwpvP5)~(3}0Te%es<MShs4jLb4%>vZ65NS+^DWwMN>?+2PChkXteD=dd@h`tmzV3kAYBHF3>R"
    "m+N0@Z!?bo?Z8;tF0cb+l`oE<!O#J9%5e`^wEit9y1h1%xTlu_^3kjzK~-BE1!<0$k@QM_OCrOEM}6rF+XISej1UcfwJPkj$"
    "(t8j1LC&|51!fr66lnnAf?LvF3&zb&nP=vWbUl}(_j8rNA!K4gzynCi>q1tO)V3S6kQrb^R<DqbuQWk#1FS{n5nzdkurF(uF"
    "6j=2}owq<P4jYsGtpE6085013G4NODAgP-OVl-SK!H8puaAeGp5D-Zo9dp@xTq(_$9eEYV5h#wa9pqmM?TI!%tGdeOyBMroh"
    "!`A1!7rqtqDZ+8S3aTvy41;7kRmU$e&a-<0ma38WNAlwVeinsZ(bWjsl|utcqgO(#Z2x0)ZNtZyPfu2_q?Bx{9@VC*%|F5RU"
    "~ES2mHQot4`^aaqK*FpY8LKGS!AjWL{cK-?8@-1ohD7RxlFPJG1hRyf&{-nCttq@C`V>%(2xka?-(bTpzncCQuyI=Bh9@rC5"
    "4k>URYc-oo_UIU`VJ&o?a2kR2!3V6T1|)qh(f!q(jA=b=#9ADK~1nX>Yyt9(9Kow$8An7G$bJ53JohrB&KEB!P#&E83a3*er"
    "Mx|9emwi)3LHl8ggR*(T^=RjX#>*oXW5V`cboyVO3d8q92Wzt!Cyr`GZOs~M)EWJ5CzEZj{D=LK1*%1mY+PU;@f@#I5C3P<e"
    "eRjb#Z7FM=_z7!ywQ7{J$|sLuKZC}~f=`9F+ErX>;-!F;jwQ+zDSGPXS4+Y}ghC(n%Hys-H6l?R5JRw*xW-%F3uu8mF`T_^W"
    "O|tXu~Qp?H69ZmP12p`Yl{AO42C6q%1C#@o+#rw+zcHBxU7-`X~2nZUL>2~9hN_6%+jz$`|_BN7QLE;Pp-ASGrD=*jp1i3$D"
    "%uW0*nlg7%<!#NH4$r`JE7wf;FtvW|(}~iSZ&(Pt_`sw~Ne`zR6t~$n<u4h{l_yf4Xet7T^0_6X(C&raFDkCfTYC^+Djt&ay"
    "s!i$$X`Q}kSB)Ob;gmT5b6V~sjwQks!y-qQ>@3>92_)a2Z89hxyPsq5S~u`#Z=_car_^bd4+$uRU?TvLjcW*N>Pn_ZO{;Q(z"
    "r9%hxQ+T`t{Q4B1BO>H;2?&-b3;WI%Zj}0}vw(~x=d{fa#V~|f}Os8hyj5}PmKbGs6o8WV)q-)c6M^*H_1yEu=hcsLoPLE1d"
    "q8J2Qze|oGi>o0#H+Z7bR0<zorsrkmbzu&r6@eMzSMCqBqDE~mWcg%dJ8nI5TzSh){VU}}MP}|y<WRr(W{jy_FWVkurP)>ek"
    "_8cqjka!G(vLv|o0S#^8LU75lrO<uZBG;EQy8epwrLcv!tc7gl5}LuSm~i?9R9ejl(+h}t2PspH$E-vT1oq@;^#1TO9JxDoq"
    "rUl&w}vqDu(Bydj=8L^U`<LivLFw8R~{S)9J5CscpK0i+ws@EahxvmRPbOGeb;YD;(wrr2Nz~;Y~h45~hxlhb8GmCp%H<zix"
    "D#;BRzYYj+0lvhiEuOJ)!%DG}hE3N1mu2)D}WXs~Ds8g|B5^HEad&hJrA+1k=aOfIP->n^j5dyS^7j#ck$L6t93Tsen46FtF"
    "UZVQ6UQmbBJe+Zv8t{t3kL7<02FuAbH?wQ1I+fJQD{)i@H@K<zr1A)5=c}3h;N~H=Zk}%EvGbZ4(DP?Y&4oX{Hwkw9I^eYo-"
    "L$bH2^An3N6Z6Gvt7e$wNo|L6I^BDwcL)8;jY{rZ7Ng%BC9Z%kaL#&XKF){S33VTlT}}K}bf2qW&LVG`jCgK$g4_R?lC?eGv"
    "U2qOUIHi;rjyni9nm~14?4IIOdez69vxfgg<_ip@hE{PXhyi?vwyWmAAAmNsI-%BgF{COGK~Je0bqTivfT7Da|$k)3Z+KN;L"
    "dPvNEeaHOE1)M&B%gj+iq%gBT(vD*wNR{TqisZGIp>+cqd-j;u9V10+)&zASbI<*oJX8TrxPlLMg*T?&PV<r9hGJr`l0n0+~"
    "I>Q+U;`s?0$qufHrL$;^7JYYF)}>c++W3Qg!qs}hlwhwgT-5i$_}=_{<XDl+D{yodsqoepsm0{0GFp4bC3T9KAsguUMTbal_"
    "VN(=Y~k+NupM36vGGBd3V-8wt-q|O>bKNht*vtenpAPYpH2s|eHfM+HsJ`ciQhJAUF6oQ>cn%{*FuCLb={&k;)9>>l87C*$6"
    "72RM0&&X8Q5TBVNUM)6pTZ1i5IuQQepgP*hJ*;V>is4BY1F3I+@IS>KxV>)ky_%FKDN?81#^-a@rm(gj-#5L@JS`iI#qZaiM"
    "`!p0{GloXU@cjs3qh?9iv>yqwA-zXi!SOG`;L2e%ohcQj`xe<mTIvJJqnR7fn^o=;&YI>Bq??*vfI}(n80%(O(_mVBWs}z@5"
    "b!L#P(eVT6mhP?Ck`_r#C;S1ys7ll=?~n?@0r^dSd<eXKfl6?O`28tIkTL@ZNgogrCj=td75rzSJvg-^i~9TVe6nN?MOUnTz"
    "Dsj_?wjB-;Jpc!p8$#3g1WFG+@GWON{Dfu)<sO=W+dotl15*=>G*HXZYhioq%(l%XeDXGNJOhs<WRw{w7*FvrC3dw@w-;E+y"
    "R>F-7{^qB++7~hwsLFYPWr(3p+DHJON!*J8*hKn^|cjT>~-7ju-9;>^?ztYI@e`(zB3(yKtXCp%q`R&Blq%o&9BBgO(_(UG1"
    "?pg1Y76N4`TUr(os>9}=%-?!kDYKRi9*ZH(_dem=@CRpw$EOigrZ;}Ekp_IcL1$wLl>uaBG0qb$`3X0-+IPfVKpa2)_&r|_x"
    "hpGsJm$Iu0BQH4N+hzJ2pu1YH-8LUTCiM~N(vQB_A>Ffj~fhjspLzqq(27`?1;Z)@%4`9t8yY%uO7KNG+<Ly`jO2nQ>^mXVz"
    "c!Av1hVDFktffDQqeN!X|7QB-#_LP*mZXEWuz=-M^(BD?xp$=1z`4^quh8A-(w3?v9qp4K%iaYgZ}`FK^%MUs1PC3jc6aW|B"
    "!}Z`mez2+(-fbz;FVJmvaPj`Ga}TJQBHv`Kel8}zqQeE+XhXriKA0d3j^^!%HUaaFVitz|8hW6#2LWH!<S(RU8d9`yCM^eV="
    "5{PHO7cRs7Vn4(YF-tv>WT?g6Eo)@l*yIi{=^3Okk_I;o8I^8qK=pNTa6<9AGmmqE;i@6Io%Yt0yNQnn$2rV$xgQQzdFK^er"
    "{;nS~=OZDu{5Xk;JWfiai}#6K9^lXDL|zLW!Qy@vMA;k2(TH7_I6`^;bxQA-=auxYuMa}4-7J^_pdJsNF<-5M_2qv~IjW;xn"
    "4Z0*CA`tk3&e>TrbnZiE{2^7YUs>EPX`m`;eslN#)kr-73IR50=&%lLG<-4H_6B$aNtqqZXQoDnqG7bvLn;y!>aW)_mgN=uk"
    "`7BNkhj7xX8fdRzV9soz{A8kQ7b8hPqx<x?2nAa7&ENFZbKZ>cCr?CFaoMp*Bg{*B$@A+GhLjSg+>u5Mj@KJ`ia(9H0SEtFk"
    "-5i*-VM95`3d><l;P)C7en4^JxDt2)|-qzsnSY9+je8G<>_yI((__4zOr)L#uWY+w*42PGO?$!i<^@I_OZ;~foNd799>i|t-"
    "pf6=hM^uP0+K=<c>6{ys&hT7-aq)6a?=fhMdjL*?BxfwqA{yo5{_kcj~76tLUqkd7$A}C0dsx49g=~OGz=(js6iR9|9tXx>9"
    ">>j_?-CRrLmiPncr2Y@niKOLl$qE~h$^04ho!UpGP!nkC1e8IZrogGH1G@1{SCX{6J^Q7|d?>2ZAmPL3T>Km7s|N2Nm(9%Rj"
    "*}xhQh{S5tYTExQL`~MANQx=C3AMt^n3QdCAs@|yr!8E6_q@D_S1X6D7T)tcu9g*hJ1AzjT%d4WUf=EYn}Z*y%b=sCTvL+K1"
    ">%Yp;(L&%hZ@!YkuE*h`RB7$@h3!rFX+QpEho{)^TIA4upT`j2A#}@&@Q<2PT5mV;0~)<T6<n+P1dofC?Fg%OTC$UTaK3?#s"
    "-a_M3Gk?Q5B@&yyS4fTOaJ?XrvENeN&Fzk!b#Ye$|ki<?PWwgjiVN{mXvwj*Ii;J~{a&%<@y6SJL6>v10r7A532hZkC^b@4p"
    "qkEYL*8AW}R>-!hnX{_Ig5~V*-b6T+zbZ0IN-G~5eFRhda9zDJ`++DQV8N59^1~a$=MSVtRb!@yDU2vBOCa#JTgW8_OZ*b5x"
    "@LRRl;5r`fbmID44fnpxm1{b^#v3<kJ-#29rHns`IfPy6cT9C{{_@J`<i_Dx3f|<mus$G!oy>T(VI^F^`gclZ9dvNS9MGM`J"
    "8?Av=jcr%Uz#P|DcsAv&9m`GuTjW}<6)9MO{)+9I{)!S80cNdn7tF{;uiDx=I6rz5vXpLS%VoWu5mRV2EcOC`R<B(h3dA!Wb"
    "334o}YgHX_GKFSZ70u&Lt8*QRis#qY}`0GXn!nMsT&Z#q;>YeB+_ROynilrNuSb@J9z8_FXdVJ9&8;xCGh-H)Hw2!44N#*>T"
    "6$v*zp8_r56Bq=jGh*ksh6%YBh8!i$1TgADrX)=kxXWEkNxY~Oe<?d^z7hi7=rm|aeXI2`vjX>+&mZ>v;FWs<Hx+Fd`?PYYH"
    "e3Bg<0<<qI#QS#dIt*a|ql09s-Z~oYv$Mp4`lL)=qC2ZF^vd65dXyN_xm78R`wT5~*%Qv`|WSRZg(6HIHPL=Vp@vSd>$x=sQ"
    "63@2^DQLT~Z_tD5D<L{@%=A-WWUVVfPuB=ZVwYs!@b)7$B`(^uk;+>v#8kyvu+B9K0U<Arv?cPJDO&ND61Fxdg)GZuw)Z(?`"
    "^0VvWVYLfS1+~E?_#%FWj@rs2BkEP_?e80GQc~2>l!FExp5rnA&os6pHMo~ys=+3u_e^GCwIzbYW-?ZaV^F#-_K6P_q_H_#A"
    "M$9$rj*&FT*age~=+`L`|1C*?}@i796i6csa=B<iEU_|Ap_`ngu2Nz$)kZV(v5dOvwi~7v)7aOXd+!k3lvu!|z|#4~qJgC|i"
    "-m&m)8*Ru}j6=FrKKx6v-3QGvZU_E*quep2jweaHoi+*N^UVxgu@OWw^sn#X(+*DdIwr|)7$4LTeoX{qz>a$rOKt{Je?;3o>"
    "|TF{eFzEz+UIALjOmP^LWx&u0dzmfp$S&9o~VpMZ*;8j%i1;+k@G}^x)z3>y&sMcvWqyBZQA;sc>Cn=+tEG(&`$t-+98`u17"
    "g%Sny`kr)Yc<39|J5(Dju_(bNxi8$pPM3tZQT#5O>nkaqGzISVN7AcY-P|wM2~@`UR@ifNM<^&(-0f9Ve|#vHSDS)%ANuJKM"
    "th<2TJzny4JItEKGRA4v+FRGwJ^1S#HJ_KshmRWWeUoRr@ezRS^hg*5}uLD`}I+whq?FG0vLg^DaK46ZG*jpqzA4~;3d;8j="
    "oi4{WuKb76g`|?4qpJYeev5=VH#FPgZwn9zn=7*vs;0`Vy0*S_{_oGNnY`%uEzDf=>ttRoE)tE1AYKZzWdyGw5`X;7kgD*Lq"
    "-DX?v&V{cCG&BKWGZ#Yekn^k9?{hPin`i~M$^uln4wBL-v}G<sxp-PK+2E8kgdwEy+y3cBQ?*TwCc(D`LiBk#7?S}Y`%PKqP"
    "UfQ2zPXJJ#mG~Hjj%I-a`dc63?W;uKaG*6zdm0VZLTx+p}H1nU$8op#2Iy;FfnA1y++oKDD^+8g+D_Ar`Qk4EWW!8CBwubFH"
    "Z1yZ+u?)U284Rct+qv1<i`V-ffRX`By(UGl6o*PMJh26umdj6f%#ivyp`p{-T}7=Oz2?n<*Fv`)R}#dyxWi}0D;wLGmg2C`v"
    "*Rs;6Rylg`-zg8`YQ`d_KrO_od$YFpK96pE5eJjt@7e$?oUPz2>?_;mT^nM(CvQi9n;HHr~Qvv97a+e`QC*4PwO+eoArQ)6o"
    "L7fJqy<=sTsM5?2zmW#V-lr=^ooH%u1z09y-}Hs6Pk)ff)Dy7s^&It1bQZ8JWynfASf>Mz{OOdp&_=bpK5UYR&X3P;4bzr9+"
    "h-im!y5JClSRS(uBpGi|swAus3y&1fL}1$ftVv1WI7_!-haS5e0po7l542xr+Ez6-gTrUJqo5!RAS!+dxRmrb=6n15ZwDSeS"
    "?{;6r+bjm?J6!%Tc-U)m7URB=zlW=3ks8Y4Y)lM)cL{UHh-FWvwVEyHiMyM(g^+eptGn}f2OP-ASkoLqbCJtApji+M2m6<$Y"
    "tY#*e;w1AZ^ZF(F+BcJi!e4FjKo|B6Q34f^JN*HxM<l+duC}e+)5<S_rsVk7tOMjIM0G>M?_v9WKnBf{cdCa4iDduRUG-+!@"
    "-VqUO>GcnnvQsaS+c+BGVLnm)SqU2{aRT~`pcXC5`b5Y9*-o(UuJpzw;!u1LLVC|qfVPnDN~>7VR8Qepc792%a9OhH3bdDBw"
    "49EhDU7x!_Q%Ad_RF+9Pvw96&-x>0377IzS><~?=$AE%L(^g_~$T5E`=m>4^(w`zNjv+{hh#Q5<-0le^(AoOyU?3i<~9G&PN"
    "AMD{(m}`xvNNl6_mmUsNde%L4tLTl%3~f`ztYhZb83Za4~MBzK-&x`LP*6`DHQh|!aj5Qz|M*G@Lq2DmD7QeDdae7$Ku<nC*"
    "9awZHc3=B|ASXCn3Dt^km#L2@aX>PKCL_OQtx+eEgHyv+*5p_x$L6@{+%|ztnaZc=l;y|VG`-J=B(<Ph4-U^7IkEbuW09iSH"
    "@A*c+ekb~V4cXXORUT6blloKEv3$b<*3yixW~Fg{tPu~hs+(Rya3)E;UsbRkBddPppM$<vUf8V%Gk;?A&|Ao{C-Pq#$pG<80"
    "Rs$#p15&5qhd%GEk5;B7|mEcPSShRyQW8v;%8I+h(e(SQhcy-<baq!N4*8DYDc!5y}z5JHgEdJx*;5f-h|rfa2XZXY-4lt@|"
    "1=W{a65bm^r4GD#zDo0+OhkEhGw@3J|=0OwgnDxTv{iY8+AdQ}d!usLAR3W@NHyKPb>}r{|^rNeBEmNB^J^T(UuN;h~+(U-k"
    "9SrvInlEs5;UTIYM$mvu>@+(wxF&xM@bO|pf#*dg9&{%`xL<g>OsdAix$jS*Bw2oCkXj!0N;mnpridkaZO+m_m;Zxj+z>awD"
    "Bo7JE2)%OQUxxl(49GhxplQZZn*cNOp)7tX@wrW=DI1@s0|J{sSZNsO_Psbb_xJjZUp@3Y~`}$7$l`nNd^*jF7i&|bJKy0U-"
    "-=B2o(@6&4jAO=~XI0v64JLl5B!8^${@W3^{X4BU)cYV)?w9sl8N-o5>ov;fAoj|Og=Z==3FU2R8JT6O!JYyVJKzrjJB4x$s"
    "a0_vV}fP_d>UiYvqB1as+K#W{I7CjoibDjz=N%&<)eRbhfNK)o6|S&U`1e`kGJNXDUo5;7t~>E??$91tIlyC<?tufCO1qAPb"
    "ULaPk*fd=GD3ufAM&OH~-wTosl<!P3_Dxx$5p>l1|e<X<89$F)Ep2H(%22U`H#5P^(NW2Rx^luao86Kjeo>l#rYSvF>r$dow"
    "hzkhQv^OIrOp_;rt`OrJ0o!K7RK?ZfB(k(uLTdTEDUO(B+#?o(MX2NqRAd~Clap5g#;Hf`Q{kBv5!+xhdWk4bMST%;3PytN7"
    "1kwZY#fe2x0z&IcP;xQWexiVi-0*r%q^o-ldnczb#xytY7ddivraCI7R^_a&v$Y-#AR)F{(Z0p$VHj(NWx`dlp1^%l0_F=9u"
    "H78%v+9XyQ?%SQEo7}JoF~qHwE}5A$D&Zh^2ccULU~{pBNZh5IF-6MyPmY25Kk;C0us>SRhA|Ly45nKgA%SI-WXa=5tYa*R*"
    "D~!a(Z)MH6!#px)~)=bg-QISsQ4q_46-lSbMNe8>n}1TF~f)e(Fr-3FcuAA9<m5>Oh%fd(0E>)(!^puVXa8_sZIYPQ5awLaD"
    "Ci>VfpIOy;gxxqm}3*L!nR>UCu=ZEE<>V((lrn;CbY=+ZxkIUG*oF01vynU&r5fXPA(xnCq=~%8vN0LE-l!c>;~%(*dkW#W*"
    "n7zoL@Use0#ReqU=$hTN%~xOOJxSgtP|YsO99mgK5!`T{kNe<|K+?W0|I@f01y%0M{ZUJj$Y#LD))e=erTetmf7bhe;x%fOI"
    "VCv<fcYn2=QG>pR-9WC{$pX08Spcp~z>bhTLMVeNbFM8oRy@GPQ7il^KNvqw?pm}n+ByZnn6B7DsU?2YTFElVsk=k)C!816I"
    "dVlpAAv>oL97)3&85bVFiZ<gS1Udc^@Do`IvBtD1X@`$zMq+FxLO9`*rH=e#{G_jXGaH}fNOY$_5!&}ecGA!?%%527#9S!4u"
    "^|)ykV(L9LYp$Fd22$qHqbBMp{fZwzl&V`d6)v$3UE6@L3z%H_#E@CwWp8#`NQH$jdvEpJ-CR*b@e&!FhuO@j_tZw9`dh{Y3"
    "<5uIks=>lT*@F9Z!%^2G3V*Au6b}MuO@~Wf4Vw@<?OFZA-dS$dfDPjVqHfXFSSpam?GP-<!S|-~@W_ytebWglUk*YXN$7Wc("
    "Gd0D0HncTcHF&t2duA`zYJghsz2p;^yn^mnZ<fAXvztrNdlL?fdX_1~LZl5k(5C^&;M$rQgNsFd69LgJKJ*3^}WKK{l@h^~S"
    "3ZzpszC>4+pa!!s(T9kuSrc0@W`9pt6X18ELe!+A^s*!(Kdj*Ce@<2;~>ysR=pH;l<IGeu@j6`TlZFAJ5(9H*BowUrPZ1_Gi"
    "YV}B^Ee5dPx0=R8U5#c;64A7Fyw&!F*9sfKc52X~@^M#3<6fho>nap7@Y~I2O*KBFn(g-Hn)U0zxsKgVkiB0g{+#Z6{BMoTc"
    "rIHv#J-abx`_P{_S~QJ{iTB7MtLdc(JI`9<Y_~02E$)E-5Kj-*f7%V?$=W@nxLN%1z#H8+J7R2n-+>&K_Z-~pLXMfjyH>gpc"
    "b9_4t?UD&XQdA-H+<2sb;5JhBJ?z??x7~h<DcFzN}l;VdWO2y=Wb&j!Fn(`+#Q+TK#?uaGMUgKaApdH(nZ;7t=2Mlk7|W?+2"
    "r8*t`}wCw-1tC6yTMOA^1zq02rMR5GSArwKdz6=#v(ekGc$!&L(HG_+bG3Yo_D6|&6UmXuO6w!_H$Sejcv=LoDe`ew7L5gSm"
    "Io@|Twn$*SVu9H1Q`i#MGdZ^ar;UKDhN8aadtRUzpkI|NNqLa~fD4Pn6yz*+Z2JYxX?R!7P=5Ov5Dg-^lA!Yce0+e?#Wx^}#"
    "(M|x$iO?XxkR3Hb#(Aih^<$NREG}!tbk_}dmZ-92%Qt-lz#tNW@3yj12QbZ?b0yXEpS=5qfJqHhw4gaZGqpF456X+(>CrSEX"
    "BP-f5e{p3^MBfP@xmk#ly`Cp7h&oF;$)S8axs^4(&(c}sI`j2I(-66d%H=5=Szx${FUFUo$t9!KtdRg21N9pQqcc)iX-3uGo"
    "p_%ipsE$K|lJ?M?2hFgCSpS<7Nm$7;iG>yY_!;o0(ISj089AwWqB#siKI_|Lvz=Bzg|JURn8Nc@C~{V*OMno$P{c(wjIr-qi"
    "pd`PyzYhc7Pt11%?etu6}4=owL4)PJ_A^GZ$BWOne^KOC&;Gg)gv7Vt)C0p>h=N_)hxK?*|fG{{S@Ag=4$`z}42Dc&<iNYlc"
    "DUX~Z`)_cse!s;e5Rpuz66?)$|S>0;t9d|lom`be3l>F(bHmHo9(4y^AuIVmy<%2?%awY2LTDD{`sWf|!x+VzTFaA;Y2Ye&-"
    "+w&Bg$&SAwqY}DC5?R!Zgp~hN=X*yP1r}L(w%0M|lG2ZVYF#`4ZGWnhf^3JgT|w2K%-xDjFBJa7yI*s+!l{{Zq>NrC2YJT{H"
    "~M@6J5(Cpwf25*G5T*F<Srqs7I1<2p7ng?0m4aAt6^p39p%-&z=RV9qvxpQXlF0)a#AUcr?WgaBYsNz+n|E=@}|CqbrigDr|"
    "$O>!*`Utyb^*~zqC?7l9MqF3J5c?X2h~v6+xuVKkFZ7hS5spi%{LK+ue6Ug{x>p*(!e|O-bjEa~`YJU9pXo>i?4CiNpize;6"
    "j%XNM@BR;Y>mWM($cP5bePd#!|BhdIv6^9oT*9ZJynIyW)%qt2WKl<v`*@S`#&A8q`#`kd3E@wvH!QoTw=D<_bpH!mA4HbMm"
    "`4WZbS5W@2R>h%+~^<LdEgG(2cSIyDWebi)%bBoG-LsBDm=%rSWzF6S|kUA7$@kzRNQp%X9R=rH?{B0;k60Ml7Zn<M5PK*vs"
    "1|zVFIaD{}0EH0iH6iqd>El12Zr{J3E}k&{)25v)$1h6NuHby1yrQRW2Is^Bt=8t3CdewO9kR?eHjk6`je;6||1J)?@BOnP#"
    "zSs%M;0-=xcMw>O+@RtD;Jf_vB8CZwz0a@;%)o?m^#PyI=F5N$9B@#$&PKOadvE*jT_sxZL6_uG`7vgwoae7U(R2c*P3J9V@"
    ")hzQtFGNG+7sUBFEt1S8+Iq-mifjr9j_l2Mcn<J+1<j(j;2dl1CyxV~N$eGu+SFV_%sTQCD5Ig>J7f&R1U|?%rBEbT>kc9Kz"
    "$#SKs>M6#fhu@_Pq|^5m~`f0L?h2kR;)5R=%trs)8-8J3XlWU?mR)09b_t-|fVQVWx%GGk>5Zuj6c+0=z<VNaSuhB^92MxXn"
    "UR%UghlQt}_CRavxrQ2pPlttKm6#3NydgMmlp@@}20emfBdC9vmoiR~L==$oA!PHSp41aO**RhbS6vwCm6LvN6{~jZ%Vaks!"
    "@LDKKN6OX-ed@A#F!LQ?1N;K^O;5Kg->0>ueJ)ym<)K2gl0KPJqkS{?8IO!yc#|La6w%r4h@S3x(Dle^oBvCW^l!)n^SU4oe"
    "Ef=;hN3aKkG7kjDD*8+l<fn92@W}7)y1T|Pq${*j4e&uLtyUGnjW5Q#*nFN{=_b3-2j_MY8UKT|AE2yLMASRWH=)Cv%n2a%R"
    "<qyN#1JhRB}IZkRjBan{twbW|#hzeg}BAgBNnR>2Y+W5!FlXw<ExFOy>H~5B7k@<_7)a2HG$4!o_WEpr2DQYq_&8(2~YFOLT"
    "468#ntRD%s)v@!H2G+%gr=Wz?GRY%z$m<IP*W`(fvfQmR(y@J{||B-`?#zR#0lx<C3Xj&T-)Bc%SBOe$yO9W#cCg?>uzckT!"
    "TaSL_{Pztw`MZ77{NX-Bu|K-2rf89$FOsEh%Ki=d_Bf9g3vnK3P*X+9jQWUi!2F=^3ca|De$Iicsn%3ts54noer05)*fpnEW"
    "-(h~;;85glBP%C%zFl@auOPP6E}kFD%GP!1T7kYl)?uYH9BE$jWhvpMTv+M9mDoW5@lS(07(owIXRsWEh+f$VnSTJdbWG7D5"
    "XrwO#L$Hhd7>TBmMP`Pd;bYMkW44wp7dZ6tEhqZWp@t%E|XrK8vxk^I$3~5vl<l%Sg`@pZl5(Ok-JKI+KTVf0)c>iz$<nl`F"
    "zCB@}R(I2(Oy&11{;-<2RloK6$i#;CUgK$1;Gw&}S@fu2n@(B7*((E+K%->L_#J8Go`*c|wojoEjPy+&smpSO%P)nTgX@VLc"
    "(M04YEuwgn{|qh&E(jXLK4^e_v<0dh3D>isUY`im^%|C7R2BT<euv=di}C+4N~5asitr5_5nJhi`1aHP9Hlvm$fjv(Wj^iQ="
    "-6jMqdXeL!Ql_NVFEuc^%Ddka-vkOXFGUYeC8JE);{A4G0-a9iO0Pq*vysun~7n=(@u?jKBuz&E?DWi&5I(-l?u#OyDF*<eb"
    "2isMctIT#XG?I)WUydIK;NM7qZf}8hN9Zlv<$*=oEf3Y>;F#`g<#E1te<0><+$*XjtlwI5*i1{cV3;VlTGqbWa?C3WwpE_&Y"
    "_QfTu^g~8F62n>wp}XU^4#g+l7p3L(0K$NR)#n0qXXI8GE}Dh@v8Zv%Qg9*zG4NRsg_?M3qGLB5s{P?sGCj;1f~wU#3?<MB1"
    "eVo>PrbQVw_xeEJGt!regS+y^=VqM<?rAn=-cr?=c39fbgda?@_>KY=n?Xu>Y~2dQ>_#Kv=_56k;N@Y(sA9v<P=dbWXh7+$v"
    "Eu`b%??rLtRd(0=Kh_H-@fLaH+$Sp(yGbmZszs=47c+f&aj;`=q;7P&EqQ-?UR0V^5nfv2RKhkbwtN$BluyEb_fosqVdV*`7"
    "uX1KXGJKDE#uZAo40=p1AZKowNik>^{ES|{}qa5U(n}?)>rtFkjuZwhfMYOFiXYU|^Z$j#n(n0};M|E`iv39@i!F971g+79L"
    "!1UyVONyt6fqsiU%x4-2<B5|xO-Ms5O-kwEStE8t-g=ZAYc1(MMYPea17Y%`nXb0`WOnYXQSu20v5MT>l3F#1)27RatAo=*)"
    "z}tu4!Lnp#O{LibyeryQVAfWk5m#A)$$5-j>Nxi!HkH0{1+yye>zB&t=&S*qVZ+8jUGh~8(g(sMzM2rn?94!3?Aj=S;eLufu"
    "EMmQ>J1lZT?-^U9%BH#R!#xIvh~dLw%_e98Q@Nv<fTm8Uy_@=)7DH2s(p%sVsuBZrxaU3Am(r$u^#@*O=IMb~1S34j?a)lac"
    "iRIe4zs3h}FvEz+u{T}&^4Qlq=XLz2syvwfQ&A~JX{Hz(HLvvJ+}&0Dh$#IN4AAnPU=5ra2y398+Y+dI-outm~Vc~Hh5(JOz"
    "gso&L}yloxSEJ4P?Lu~zdDEKx*4TMEW1$?ob%`IJ}LWmXMS5(VCv{$_kl^13~lz&#D8}CzmIR*czm2A<VNsjx}+Bp_@WQL(x"
    "kdSBX{$kRm3+0%#Dhu`a5+9q(ZIFwdh!%cyJi?CGR4lQ`LiD8yzBp36xS&gd^Rha}VBy;TmdViq_5VcB!P-kWx~Pn&*40JWv"
    "+a1zqiiYAx?Al%Jwq3So*jg;>8CQD_8Mz(I;UJM`YdeAL%+6l(>&F%G@4mxhz3t>Y;}x_z+FlUndP*alRYTcz_3Z9nyR-fZy"
    "Q#Lc)AOQ#nilEb+I)aEgk_-jCGGahWvK|`I3>d5dN+f2aO!?3~|j~lgkZ5Ts*Hd+qLUXD1LpxD1+BAn0*>Trl`z)N86DMUt6"
    "d5@?>#QW7Q_5I81fp9EnG;%HTtZ<}KAJmvs&-h0T+b7d2y<G8sT!tg8bZWgAnba8UN`hBFye(T`Kd&<l1iQN=az;{%y*!e+e"
    "%9TAC{mFasYQ|PzgB4Cp9;GbXdUBA93mcLV$k+c3<e2kTi_M0#zCwag>^2!`Y=6+l}(gcyCSC#D_F<{bB{il6<Iz7dd$-#4}"
    "=5O5DEw$rfw`y|g+KrXX)q4Ool>)5IdX&2+!1oOqurN~P2&Fyzo&6tQu8M|_z<nsPH>BS1`Oe*H&*y~?J94;w+K(hetI;VV>"
    "Tmf?b~5-!T&e|Gp;m1e$s#1lkls>hW~!Z)$?BwfPYyFYFct-0az@-92jXBv7chPz)b>Cq3C-8bmOh}{a_H9dh;2u(ZTXM2^u"
    "&HG^y4H<m-nd|)FbcAPW?GtqH-HW`GUyH9#iCa)tbXLQ4IZR%s`~~j7%rR#^%M8pDZON)Ul0K6TVwd*ds-+or__;x<C(60dY"
    "|rf7fki&e+boi}nXWF7^p0eZd%|ph>CjWG$}n{&4M6)&w0)$c*G062;e8<!i}?!2l<OXO7YYo><v?i`|}V-a+Hu|8kh&U-{l"
    "1ilRhiYm&?Zq{s6Bmg3v9&BbbfH0Ipo=T;Fl3{@A%t(~Z!O(cZ+QUqS9(I5tcI%lAVDkWThx@HLgR-y97Rp1rXRwYG4u$W+J"
    "F%R6XbpwG>H3=V*QSzZ`N8vXXjJ;&yM3MB?OH!5It$0~wTc!2x)R9+<zHN%w8N=;O1&~a~A~)8UZ=Fo4ekv_%TU?{2e#jnY)"
    "z>etCs)`LkH~#T_8!bpI-y$IbNH<M65&<g8`2PazYgI!e*OhYc+Nn@M?5UAS@P4j-!tDb1xVt1zs^&4&;q|4d$wq$sb26BYM"
    "nBmfddY}X6xOP-}Xg#rZ5XPH>;Ighm9{MqlfnX7rn9FPn*y1kxT-8CtZwl6hb|nS6qZH6=4G*F0Mb?WJf*aG2hMK_^jSi$&;"
    "e;S6k(B78n&KQ%_uXElfJa?F~!@&mI5f^P=JZ^0~r5psA7P(J=u<0X8xi{~$u6JhITi%|fol#xqAG5Q=><PK#U!gOkxz)98C"
    "Q+~8?61fyd6X(qA~Ma*N}^MbO|E8*AatVEmMul<CiH<t?*pr5Ry0)su=^R$GXLG?m-hjS^?*r|iH26J<w85xCUmztf&(Xx`q"
    "I8D3ecuiBqPzSq}Ps#oIVX<mHrtb~B4G&lRqwz_S`>J+9AW1R=*X_H}N!ay0CWJHJcwe|u|BdDm5@A4_`_|oW`P)BuTea2jp"
    "$=CZ{1PAI;M2-y7bUw`Fz5K;XXs|E!jn7trqko~K)Sk}@zW*`+Yair5_*xUZy&y}ds<+H=C<Yu077lqtx8*Y^b6rVjp|Q4xr"
    "{$Mib+x_x7<jWbUw!KwQ|<D)pRXSwz8=e?3;bJJzq1F?mI_khPM9m^8A6yx}>QzeB7x<C&94PR9MT+4>y3{rb4cTCpC0QHt{"
    "QnMvJ{J{FZg_HtRSy5$~z<-Uu{Y_Nq_VI0zxjEdMSkIPpS&>PE9zi|prepSO$)28<5T2>lPd7F<w*HV)kAit2amoNW3D=O#w"
    "}25xl#4^^C|>>|v~e3CGj2sBb(-vFP}wzt>gl6En?->h<}o32DD5X_n-1dDbJQ-SX=H<Q3z1)!2dnrlZEWn4ft^U?cz)h^Tm"
    "^Rj1<(!hO-509Yr`u^q6(7EHatyw*i@2!Y^`Iq@JtEqRDBgIJ*cJrGU=F>yp-5W{SO}T`i6xP|u=y`zJ6cKbc|H8BkwLDo<I"
    "37#40VAbxN(a~d8L7W-gOy~9B_(+Rqs8T%+F0oWjSk$gN0(_Q@$vJ*9svJvYzB4gcYM-1jH~r7G7^7bqQbXqLM9zx#e72}cy"
    "8;li-6ZQ|Ic%-Xm4oA(j)r<jo6+acu{68p)MI==)X(=pk)#QYOtbf%~2p>E+MhXe+(8}U#=)~MXI@t=j2TOLjdZ3(Zz)trbx"
    "P4!~e$k)Qwf^(TqBXq}E+_R@;<EA#HujQjE_536_d=&8V9v4LS2I^83pP6-Ac*&a<Ou9^rMcguw8d%XSpD!{pTOgvr{~RzoY"
    "hb{H><A4G|pkQ<LK_}cd%Ui=-IFCOMbdJa*4FfYm1i!!{#^B4=MDv_8iK6I^?93Z~uXq%XB9j)GBQ6iQbwV17lkrMao{W8kV"
    "$n*KbB@^v15NLPM@U%64M!aeEyK6b+cUeXCW}OJ~<NM{k;;@H9(i$)IAYqK?gRGXZP=OWkUhb_<kfhLn|M%_1emON~$W9ZSq"
    "-Yc!gltI#*lJ_NaI=#MXC?XKhCxc2B<$(cPL0fcZm<fD=eCVQA58?tL~*pAu~#?9L?7fdGU@I&Ok|`EnpSa+^@U=wNh@>wq%"
    "Qeu&+>R6Jaf?^QUg*=NYQc5nXOzdptLUG@a{QfQ71?ob)@Y7aVgF}F8%fmj{?Js(ekH8#fR=Dn>F<M(+_fXYxrBa7_N8@->J"
    ">!b*0_m;i0~f0a$b%>(rO|fhgZA`!$}9=Y`DeimE)(-jk#1f)lV6lPv69l^iRpx2BqGfvB}L5rCY9XoOc?_6n&LtR2)H4=nN"
    "Tf|8~pVzs0-p}e*~sq5O!j#isHl?=D`+}0q6FQ#|5w5)f{Zds+U+=8*GG|lDs59nkn^4TG)nm*^*SF_=)rR6xaOEPjYBw8TG"
    "z4P$<bTncN`Ux8Pk-lRR(pmIphNDjF0BV%nrW&oquViyi+bPMWtkU%YR8?v%_ftb%^)GbZ5hpO^%?q!?``uq?_=Uq~(j~ZF!"
    "L7%yR{!mj_PNRZT98+C;Y-O`A2^TqSrCp!W8em&Nq?`gCI##ZMu=*?XZ9362#_sDNLn=Ec>D4`0Fy=nj#=UzUx-*mw65~KrA"
    "LxI+W&(u;6H+>z^)mw<PrOA^c5S5#MICg*>0LoN~OVl3iNJk-!=lE#?dcmM|x{k1OsK{+761S-O7cy<<c+CC_QYEpDs4~V)>"
    "srn!^m{C(v9k){GKBGNVGQ&gv3s<YIpY@GLdcyA8Rd(D);rJ16VMg8gdkX{i{{G=7&Fr6MZ0%!vm5HG<N+=2&e$3s+*gA--L"
    ">WzhVEaWVrDCF?k@>v}VKb~#%!uO`@XbUfjPQD$V$JJ5TT%QL0q30yw|LI-Lz0poITnoV7-QJM3<C2D9o)F#hpwh3odo-&5V"
    "{hIAq)U|i9ypchbe3A3ZY|xCd+Bq(#h$!pGw3{|h-nsuZ_0>EfwpAMwg^YA+viNm7v)*<Wl4<ZGDcw6%u@F5;8D5|IoOn3Gn"
    "Eo|YeC{*Xl2-GCa8@mL5+a|VRMS;q{*c6`Xyrw&qNDltjWX95q^#qoo6!`x7Xs9PYV`m1_*9}<Z2ANQ)x>6zw>W1mfl0=>_@"
    "r8@EazN$pjLy|(aC6g3(fasUxL=c&V>*X{0yfKf?X00PMj8CRJ!)sx%7Pg4SiWk6*;6VUTxLDtb(|}RTcpe>)A6cI!j5@vVS"
    "xtyW5()`WbaM^ut^(#?Gm+L)_Akv%|Dr^Mw^$Z{*>+i;vq>Sqkk)pReG8?J&#p034aD#$c|jVe)Rt2P3bZ%E&`1f%~lzKB^7"
    "VjhpW9&ufnkXnm{-rIXWP&r5?X>DJZia=NXgi#JzhDzDn^3J3h6d&CPz%3PATIi*O<q`CyO^Mfy!z@49_MoJ3XFDw^?tM%1!"
    "dH!1%nQ5lai91oU{Uo$T@Q}uM(QvkpahRw=F?KO!Qp>d<3Kr7FbGCQ_b}h$#2PzEDG*|wdUsKmXFsoypl9kMp|H-Y<KUzzs^"
    "Gk3U6U^iplFZm^dP1Rr9-ksRv(znDp46OB6-=G9iOkM~3FP+3Pf`6uix?Y_Bi#@W{OJ)fTl0Zv)2019+tQsqz2)_ByHRU+M-"
    "q8QDamaFJ@H29ui-j`sn_Yz{3QeY4jZSvxZ6N`h`0G&iLfU#Y}x(DJTK5F*(~RA@@sj(uh;<S%G>D4ozN}BH3My*ti9#HN#r"
    "$vcU^=;2x0Z<R@zU8kQi}}C4XUR>&a<R9cJu4sP!PIe6s9~Ki5wmF4Uy8Od{<zC`BitJ#9b4QfrFmW_H*^{pk{8kIXMjQt@R"
    "3#2(ftcA?;j@GAa-BzT{;EwP@368oh$ba9ybc_1&;B=mgWKu35nfGl>RkNaZGd^`V?`~-&@gF!9P^3o)S$qvb>jYRCw{On+N"
    "sHn&wy}9Xiqe4XK=hada|KAAL>A%g(s^bV$7H=Qpp93<kNeVW)Y(<FklV>j%i;XhvDf~T|7oEwXM@|jFnpsdD7<pvJiSWV|r"
    "O@HIUKs_s`^v~&k$Ch)x@=wf{5^dGyaTI^&Z%h-KIYrVY4lj-hj;CTMXI27u%D*w&*@BgwF&qd*$^7JEmKVxpcv<-;FENDi@"
    "wV2=Git1G112!9#It4%T$n{iAJzoJTUfwL?3_1tgSxZFP81}Qys;X5RKrUQ%4@rF(ZrQVrE=m&nMdLoAL^C&X!Jk7r{j)$@?"
    "_B2x|@=?gt|j*Z@hgD~rR4j_7={1Aol}r1jH<3Xh7<4ScR?$JxNF00k00`Sy<;^19|(87G5Wj^a;p>Y@+Q+WQ~C3SAQ?2|p+"
    "Bq6GYgu)zTI*wOL7=5>cLmSAoTV<0a^9<K^Iu&<W+UpKz$Jjf?$)peDDzjzz?v_&bdcu;-s@<k8adi_HHL(=tkfLnJate@r&"
    "*j_EPKZji^&PjB4xX!m@r1}<2tyds)6Ao`5PdCV0PXaE|hmPIDmo}Reu(jc7S=E2)62N=&YlVvoWfI0uq-t$C$j3+(U}=u$e"
    "prsx1ck49xvA-<h{yy4I!$(fFi?QCY9U-F10XYcgiL!x2EPutAzex`?AAF9S9%pObLy!z82UEoKDK>zAi!EZpKL#G<liCO4f"
    "Y!E&wlYAP9fny?$}{Uq>mq#9p4V>>Cv`CQuq;r<wKgDc$52Qs<=BBt3x}c9}P&c`aA{`5-O}NNkImSzH-GaOF;V-aOPQeopi"
    "7f=UP!((>n51+!dGaYuW9!S9L5MHZf%pb)epr^V%JHyKcc3D$880%5(9H$cgKd$H|L<sOXT^V}AWeeid86Xi4hr$-{R@NsUh"
    "Utr$;ROMXSFyZN5SF|fQ(ZPNMQb2JCqKL)c@*;?Gw*XMKhGv-j??f4mSQ8q{+$GTc0c|N9qk%SFFgBvZr)V$j05;1Liwpi5%"
    "Ynv6vpn~o735kuni+<&WoZIoH$G?s*FRy=6YTFtmDedBE7fJ~ETqBW_*WQ#^v2TRM0~}Nr0NUR{o+_3}@6TZq-yP5ky6dVh#"
    "egWuPc={a2{3B0PEE#y{&L8foQymTK?(<O$BAkzLY-W5ooszD@l27~dB)-CT%)%-dR}EvPQIEQFOZK8yN1Z2Sf2#zpstS@uI"
    "30V!|VAo!KEgDrp|Ls9w#^5o6~QaH)!2#H}Gde%-ZbG`_Gz5yHRleF-YYpcXGZy24`eh#%Jf|5oldv4BX{&%A3<B_WrT%@_8"
    "u#&Ni`}?(wQ=IWTZA#K983<O={psubs~cZGs|W1a0eZ<Z0HAdZjmUl>Lo3DwB2ZVM??n@Amr`SU~pl=`nqBHsT`9%PF#6Rc="
    "Yf|tIo4jK^7twWVU(>M(+h|KgoKpKCbTR>PuNf~$j#JVSyU;fbE)0bucsS7Fdvmh-PE4J?W!#po;e}w1*CU?b|U<k#7MV@(p"
    "V)ywV%fUvQNIF&)p-zQvHjLh~j%tL~hPJc`KnHk@V>EoAdtSUbO7E<o=S8mHCR>yf%4sGN5`dshfcVaeM>?&kiGfBHHPLW=E"
    "|ivA8nox@bFVB3!^THr`0|PZ=Br9{nD-5ZI+mj&46a@%PYdHr?IL9+R}QS=$dT(TDh2b}RC~niy2nFs#6AnQpWao9Dx3ts?`"
    "QL^+#T|9NVQwOf)~By`(!R_lYxen3&#2!J~dz`)%WOXcapB|c|wn-RDO5iObcEZ?0qnyS3vI)%)<Fr6f<bjSm?^rdsGrmA>&"
    "gQE<W@k`Q*vw^T##un^4l%;?A!kpZ}(K_J2D6GW@R`$~WPUt5Npj;R<y}{n014+zV-~qpURDyn!67NEi#{4_xkXD-UWMw|@<"
    "rL(Phx>1b3#U;(yhRF7NOi`_f@g>LqHf2qKvceR){-15;h5)J|$PBNoqe6t`=UFgp@wZCTbTo{kLM`j`HCtW5J5)2@{@tm4*"
    "L@8qup@t`*`jK-6J{qDiK*u7~PIXwDYmz?MBtxZL8;Cq!V8D$*3)=Uaq<=n;iF=B2>s8Knf#&o~;^2rI&dbWpudy(4<+j!uT"
    "Dxsfsp&~HM?vs3^_&{^Sxx<Q+B}S^&({Sq{`fNQe#4D5{|9ebbyXA>QjhN*(;TD9pOl&TpMcilD*C1r%s-GmAEiDa^bdYJ*Q"
    "iHtF}o_K<o;3q#asz&F8KW#O8r^0WTeKV1+UvYm=(X#iXGBv5b1a&7`9_h{}}q>UK1D*ythDDP3m!CBjANsdVl=411`f|A@u"
    "tNWR9Im`Taf05&S}dXp7zY*vRl=LuZW2dqQp7%5+wjenhc3xJuT}I;IZ_)BC~v^~9a^x-+8S$1d^>MP6x2?SK=QHEszlJRN%"
    "?Fg7~dsGY1v0+jC1LYj#)IY@~Dj!KtQv(>d4#NN2mTTc@2`{1XR9Ig_ho%b)Q{dEJ=SD1DO+>sT<h+NSkR``irK3E|tAAhgM"
    "F66VZGmrQKFZ$Ex=poeC0vh-nk%O1PggHn4)BGUERRJ`i@4S;Lo6a;65L;7jK$iHHWbYi3Y~rv#+6|t>a`oyG38eYQtZGv?2"
    "mNf6#mc{f_vgQ%!|0J<Vq&f!z0Y|H_JZ@epdv=2W(ky|tH_C<X_CSin}>HX<x`Q7X|X#zylgr_{D_c9=|n@1oKL#joERc$h?"
    "xwtx_P5SsuzgB`fCqrIjp0;MfDjlv899g*xjRyWG8Jb*|hoywSd!VM`ab|<f2(+mdXs4i;bU`H=WQJpebJSRXv`MHP?=w5WR"
    "n=74Nz0Yq@bG@)A`~BKK>x@r*rzSRoH5FJA%1JqwB>F~vKUYZXv}b{{5+GpC%zRaZcmh1g3$2WdfE@=^O&raJ;a=TtMWEA6y"
    "x5=-r@)W!itDa5NIB$VMTbwDn6sjrwPfqNu=s2S=dD*^&5pK1j9DWG~>g6LE(0-wCIIkI$4VIpd@C4u@?={G~p4;kmU?OTWG"
    "VZx$u!(zOh3H}N@c`;PI_^`aZpwF?Pr`y3HFiM^0xeZ{pLI%_4m3kC|Bz$k|rY8}R?>ruCY%VdEcgE}ov?L9@TZ)rM8`U^z$"
    "_IT0GcckMU4&NGa1u23@J>h!*0i+Ot14oCeL%%Ed|Tk9$R(eNBld6NlNtZ7{Xv9zvk~guH%6dO6n8f@qSYsdX^vg0%P$gkl="
    "=i}v?6o0-xh%J12+3Ne-TUBuOz05c=U(6S!T;vepnG>zUSAs=Qd<-4a~HOD5=xFTFo?g@DRViNM$a93oQ_Zwl=d`EY$Fa>>n"
    "Z7loP3BHUkYb*Qs|UrcNtA^N!etSQBNqx79f6tWK^B*ChkJxp;n0%o^8n0qY6}k$a8}tNRMNYkk`PI4lW@XP3@#S7Zauz2rR"
    "GTDaYHA8Zz#)guX-t0BkxeauxqQxAnRH$_-rh%=qQB;Q({!sxW9^-ny7ToW_^H$qH0u+2wZDl&T8bL*4Gf*;fxTBNvqzn^oC"
    "Ed~m9o<(UEkeKKC64V9U2LUD3v4%j5aeG4QpNXPp5RGg`zl!|H2pHS=B2826#1h}XZ~LNWz5NwU_J58FafBIFFX3f79(4GQ&"
    "?3L6YF)HwylxPeso~NxKLc^H3es2le!PwkGXPTe@QyAv>rg?G&J6i!{`nHwz&`$I(~(l}Ev982+$oou#9(Fgxx3l=?ey9(L^"
    "th0H)T#^VzW*Oe%ryxvo_~LznGMf<S?RraCq;W0VEsWYKuJADf7O9r!`B&;j(c9<-jF98!0i3Es6>PweJ~1IxsK^PK>bo$(G"
    "OEJ0UF7<w7UbQLOP3!2T2(nq!v#ry-8Y;e{nx9033BY{2MAH}_^+{LpiVI@2ha#81<om*O?mO-Uezb}xO%6~8RJ%0`zegcnn"
    "mMp@1rxMxyqM%qu?>#{Aosnu)K%lJ9Colh@Qo{MeZwyl>{T+#ea76IH3>&zvKR>rl^&FvuEaxik!Br{voYpkssMdczClIMKG"
    "m42U9=&}7k-oz)MG2ep!d)J5j8+8vcnR0oyi^l2B4N{Q;tgScyD8ABCTCUnKB(2J7#=Jx`@vo@|n(>dUODbDh<UM4Y9-0TkR"
    "aRe<K{GaD^KVGpzYE+Z&c9ED3ig`YbpX*oSkMeGeKP%ii;Hj<Gi*-1(T;SFtg!1&w4^q*W<}6-D(s%bqoHO54a(K2EMe4Sse"
    "JVSVq8Dl-b|ufzNy^p>$FsTYJBFXJfKTc@;YU9H1o&Z4GqgDZyjX)o+FZK8SAjGuuElt#R(skfQ`;)Hq+-rc;IpE*?sWZ+v;"
    "e<-nmg8I77pTO{A*ZO5}e340g}D&`yT|qwC2V;j;dgsDbt_(P|Mi8f-Q#lari=FXic$0ugpDO51m)=&!Q&LEq0NdWf%xIppF"
    "M5QFsUdbJ}M^Hf)cUoz#1fxVP)QJve&DJ)QLL)-J}=$o6l-Vy$IZo2ap``0T)<Vaw!-P@lQG1!X?_bch(gOQ#<=Lz{0lh4>a"
    "x@(lXK*v3SZ!^TT0s^+^@0(uUkFJ@$qkgaa*3eLPwAeg%{j0-<|0d%|aH7cADLg>PMz}-=bv$7sOfM$8lGtj!&D)eRgPH41E"
    "kG<>rYbyWt9sBdMva(Ry}<<KaQNL|hKCKTvvNOH3cX%qmKB$PAo~clIDcv;sLBb6AYz`GqaQiY808bFRA{ovWqG*(poR^|-v"
    "P%c@#|^7E<xhRzt?ABk2WtU<^Vu5T578EC}G=}h6ywMDRYB|+<nfKiO>l^Ht8Kln$8L{XFD7#sp{^u1K)6niyEErQZCLM1yU"
    ";g$U!rXU!)vLn%))7Pl!ym6Dz;REm=&bhKv1CScPcApNGud=DQ~UNN|!Yw%@4TI={S>tE%mL=-vLBA=_}9bgum(W`#!DV^md"
    "q;4xIN+2X}}AFDo1-|E2(T+l)hXlfLqx`Ig&!-%Aik)!;inUkGa8Wt@dB_i<f7XaeoHu?UIAn;$uts#&v)P83hnQ-U(YOxm8"
    "{8k;oIet^CPz9Kx!<^nWbF&&us#ad|+Mignvl^sRr`j1b!Nj)Xpw|sBiCmA6*PFz9n#f%Dd-S!-U!wg;)7uavc_jLOb|9|pa"
    "-S&_J;PTVuEz)@3xEF5ZYQN138+S?oZ#*JMr;>C-b)LRj*?95lx1QY6aE5`k^gzIPIN%I^?}LH!phYu(2nChurD>GJqzV-?G"
    "rWg7^f^KTXdPL89dxP=eU)gZ@lzQ->^Yyjct5l70C7>EfM5`NSrSjZ&{V#4A~}DL2z+iGi7lRws^4@^02?=#ZV<L-+=x+lKV"
    ">DvhCV~X~X}#VmyI>sMKiV#m$g>KArsdX&ncU{$%LT(Wp<Q7sk{5cmn<gBtW>-j+q{Hti4PfpiIZ1q-9(GbzP|cb6p&C#zI9"
    "$87a0sE`Quh*4EPFn|&Em7q63kfDX2|2LgPK*6=_8k?&^g4aHE^$G!mU8AV-+8#Nc*G<~CkUZIjFf*q}q-R-Y;##(8<>A>M+"
    "pVyG_-rtrb6pS7q+uW-XT^)fL^*6Vs!n6%B^O*J)6d|R995V3I&1|<d_{R-Tp4@`IQ?W;PUD(aX`|Aw0WO)J{Q}_8~Of18(J"
    "y+ms{DpL->pV00S!~NoB{kss*<3@y%n}Mz2^tJVn#5G(DG(oM@8zrkB0#vYX9XACA3Q{1*rcG4QjKjFgDyFVNM082*y!K8OT"
    "E2wvUa1=zZ%t+N0tP?@~3ZeIJ;qyh|G4%OKXpgsDO#Sh4~%MI@;u)CXImg?JDn0T&TpIo}8doTe%*=u<r&_H|1g^&+dOtjtt"
    "gzVvog}HchHK5?xq7P5%ZGR^8)&xLULJ?Yk)G6R598ee8`9tf2mIG<ol`p09@eua8Xv-50FrYp1rc<$Ab@wXPv7{yXuOL<m9"
    "P?_kiVX@xT)Vy?Amej9@K)ZAB39eAZ+55#3ZPOJj$uQyi8^!Ad_)&;qlQM#R?2koN|fDrkJ6a@s8;UJG#3zlJVvA1_Tx#Ub)"
    "{$5bQzG8YBF(JY7B~F*?M&Gp0LEwr~iazwwoa6&NU0JUp57*b4f}kTm!C-YMJv^Yy&e`f06_sQJ6Yo>82(coEi?uOel`4qOX"
    "`4QQD%27i^;xW&leOPI8`}>(@va2gAX_my?#xgBb%OG_m!5N=mpbJ0ah**xh((Hu0=Am`6h%E%L4RbQ4bR{=9|Ji_T)4KB()"
    "TM@?cL!Wa@dp$v{fVvb4qB;qnEuKEYv#9o{mi8`Gx}a|20LfVEpebdj*3o|M~1kN|!~TM;my}Oto0I$-VmY*O|-LuRX@HMJ%"
    "DV!~_OE)~f!3GC9yp9TY_zuF2~=PlKOn%S|meL;`OE9?UdAzfIi>3e?&@9B6jL_ZF<2rHbu}uE2!^nu4*l&8n0?x%h(S6^Ht"
    "WI^pDgFcpUc$loN&iUF41A8a|^NJmHR&wVYYQdMq^HOu?yF-q+4Ugazk2ahfZMw-0dEA3T+nV?wpD0L4RzygVUQJBW^V@g>N"
    "mRChYJeB#R_n0$op?>{|=pQ5gis&%aw4Amb6q{fcu+I{?pX9Myj*PY_OkW#>G~lJzR)}-Mq-q%ZHESbvFlssZ=edAtt*4*5s"
    "p5t47oL3m3ltVs$4PcKrSl`)a4eVkucf83J9d9h-nW053|ZW4OF!{|Hz480{0lv)!+z66=XUZmmK>xAl&ccDDQaU1X-{qZ?Z"
    "vHKzc&IbqFn6Zo|sHtuy8$V+iBYSJ$3qvZQXw@>Q5XV2Mec*Ybhzs%jBw|oEEHdjI>ExyOn6tUht^YJzZO4LT1Z!l;{S>TpE"
    "2_fXjpip92O3<w@JF_~+2Ek0>SR+L9uh^3kiQ;OA$bd0A?N7Q&1aLDpb@{CE9|ZrM6PdKAfDA3I%3cZv}+3DqFANrCJ0L-{%"
    "rS20)dwqz$vOno~%4xZDGPKMTDVApm6Zx#YB(_OV1#gBumGUtMl%u#<H9h|hpyi>#rHc1HdVhRJl)P&WwzbE{l1UW%)G=ZRt"
    "sZ-(x!${GF=;-~me{)z4+6~@l0`cFRSHu6R+J?$M9So%^e5JIUe2oua-fYCWs_@=9j1D;<dk@Ga{&LRx<}VCjWy{2u*5veR@"
    "$B5`j1pjCRlo&1AysXsPVwmJGPpGNuzL#W^X~X7W(i`&Y#5Y-P3bUkU&5=qr}c?<;vuOCx)o-iDF*f?)DH5Sdg05uhb!plc4"
    "PsRd#PVVXzL<w-!-<hydbh+{{S*yFB0&t+($nc2B=hno@zU?PNX`j@W;EL+r?Uk0>Sc<K_>9OlT#&KOpNNWfs&4xa+u%A)b|"
    "P~VJ=^2Vh3q^HW%F~7p}P<j_CU`=DO|U)nQ?#e@yKo2(+XMrztq#_rIc9kS_V8S5=mJohr6UmDK@2(;j@vO3KX9pbzMXq_>D"
    "107pD)+&_xn7v};90XVF`3IDrl|1nE>9NZ?MqB9ZqDDyf6opbyVe7l3TDxxsulun-V>=)(@qXe`|0tAXK2tRF>8H=BkyOvld"
    "11?yM^j33S1)}AEvCO$|{Mw1nmebYddnU3^(&pL5rL_j0=*61_Sj-!&T4~y9n?`t5*C794L6R&P62tRlc?J<y=Coic$ae9@)"
    "p^f6oGs(wlm59~7e4+v3HbyBr}8K-($XB7@$^+_x6kb%n&4Yu?tmQNq`7;+&n}y1*h?POK}=_yQm+2^oOcgOiBe94PCW~(z7"
    "FZ+kp%JKN8sV1<eJp|2%?YG4oK<2`&PTnX6}ep@|jezlc5I~)^j-Y<*xq6=y7dA(95yDfzy?c6iF+~*0(WL9Xj4(<&jdMis{"
    "|Kda>?6D%hW*V<OW0A#PG@AI9`3v>&<_2|FYO@qkCy!x#De5$93~PrIjNAK3q1jwb&B%n28ylvn20`X3Ux1N;IbJVZqZs)NQ"
    "fZPBnRH%+mYRnQrSNIlr%`j=T5cAb={gm03Hijtig`2x&9E<Ty}d*#mKt+(e?WI<A05bMd|NJKo0o<i_+vad<3Zi&`n>B`^Q"
    "w&7GjdnIUEHMeF76p7BIaAW4>Mxb*1L}EonG*&T}^1LYHdEg7Tz<af;gH?Id#LpgE>8ti^yn5GeHJszJZ%Xlgf_3(rd}A&eQ"
    "JB<+aP1$0b!fPQVR)TIG7%WHq;-f+I8I8R4)<k9pJHTtf1X!VSDxy)fvGfZ)bFF<uD8=Y*T!Y!`L`EWEcY7%@8aJXrV`|2iL"
    "kQE7HyH*J;}~y!i$Ck@4$Ze$SGJvb%L8@FhzK^MLM0S$-OarUGA`YL`~4QurgU3eg3x;=AXAIDKcvFiVWMv5s;Z#6!Y|CgqL"
    ">4Q7@UdDnwOnO7NsWTv=1|5NP7pAZ_+r4PddDLhdNQWZ2fJVD`C2`MrW2g>dWtc6rDt_{m)@&*Y+rmp1R{SYb2(+_}kDR_Wj"
    "ggEO^;MNn2RfWu$!t{?|dSHD|!MEL%hLJnedQZjpbilleG$Ebp{)&OnE4kvZ<B=BgMjjx@70o(OJ;;;jAJwk~T=km1kjmKiJ"
    "{tYd{Hl7$kag0>b2v@B@?8}7iJKv7ubD1!2Xm-$uiM&2R2yzW9&(Ha-Bg6N^r|qGy*E$J9d;hgW`JeA^@;lRvbBEHxa%?&*Z"
    "{olMGdRZddfy6N0?`4X-LN5j(n9??teH88pS2hGIoc+(4(=(qJuV)x<nB)EU%dtPZhy%n^WT@&nF;CS3l*30%E#-4fiedUjZ"
    "c^4a&&{InkPqd))ZWs@B$J{03lgvRvuuZRwIOO&c%+juSL`F&L@^8-x4&dW2fnp?E7Aa;6$_si4_kh2TcRB)KS-$i8T=!WNd"
    "p>92a+jsAWhqA-X+1`nR!zs4OT_2rA)lwY?o0iP$lShK31&4(KDSmuGOh0~_8Jv|?&bYu#K1zkHaconF@7**u|Q1wSuX&Q!`"
    "UVQUFPPX?h4C&)S*BU5En>WZpJoaz1X0ZP%ET%%N(e7vO$!mI_dh5mTEv(p_SpL6ua5tPo_Tz>sGsB8_VR&E<XYJTm#TN+EG"
    "y3Y+K*O}jb2spCwj_iP>e55L5lwuB4B>#Pd--kGihtF#(z#M3bNd}I;6o>l15~a14=z<OC5Ed5H>e)J5CyUJsJ)7w5_>FUMn"
    "KNn<{&x<XY}hZ0T`I-M=K6{rI&#2FcwrKiKb7og8)4rBe#0BmK;1qQ@6_96Po(c%eyly~sPIx0xV1uxA9$}T1+*p|MpzdZd$"
    "=2cJba9))~$Ls{Ep7IuZKTiGyBYwYF6&_eD>0k80F+ZJ|IMIf4nghU$83O^(&sM72pYdKk;lyTo66K=y<2HFf{$tw(zu-%Ql"
    "BAy3S@c(A5b#P{Vu8Ug}^~1&)w4TP!Dwu&~AgoRi!5;A<(Ps=G$S5%%+{e_!zPV0y-k_pgbWt?>>e2(Qe>ZEVfO_gzc5D;{w"
    "lKbp3Tc#jufDLBn@(89_iAp?t<R;uoGvO}I0ckUL+3;c2?do^dm)+74|Z3}F-+*N<xzj9V2dd^VpZS#*jifEKwTbvP6Ep7ak"
    "QXpOG#WXw~wRcaBc4VlDljqRm8u)G#WHhvlcG}F#b1z3UwRXT=H>Mc9uTd|Mh#RH}#IXzpn8Bqc2zq!HN7BBbyEdV^Aw95_5"
    "K6zb;y}wMlxcprW}q)62t)$=gF06(C#U*$2bg$AC<%Si^Z=@QbGjD<XJwFi&!C8pLErixU1%P7+*`iSg#imx;6KA%JEchRN5"
    "~jbS29(e$4|?a0)99L{aW7lu1es*eWhwIEe+NG68uDNra^urIvmvZ4t(?oP_>F<6VCowuN%sx>zzG?R63ExI=kdkfJ{sPLW)"
    "S0Tg;kAVho-Vx;!g1GuzkQI&~FAB#|Jh%L{lg_|GLE{ySfmAy({*qleD4S3Lx7Iam=9wHk95?^+MO55WrR$@S#lk8tRPl}T+"
    "W{Dqs-lGfv@LB;{)kV%^Xwt>~0nB1=i$YFB$q2j^F-6x=*HPb#ZReQ`nhwwuo>b(icO^|{dGt<J<5*icpwe%NMsM_ht2gwIU"
    "NZ?lC8s(bhVZVUzer&dp1|@8U+FT?UWSJ(mDSZQ^P+Vdoj~DM75`q=9op*N$TAD;s!3=WXzCZUM6RM|vffFNKE5kFYaRJRfs"
    "E=KcGBXOF$IC%;SUG;4NlgW3I&gfwVtoo+zy*9j<2<jq+DjbQ4Fpv`G6Yb~082Fh3-i_``f@@z!|^^yHpgiNiS4)CR&UcATt"
    "!y2DKW81;WLliT>L{=@)zbHE8X7k-UDaL>Hm2vb=-dnmQ&{;JE?_9S%kiG-GK1e*f29MGT?9@^(BQ^uE{<JHye%_moQ{3Sya"
    "`3AaYQ&M@|u4d|M6^@LfGHvRRe{hWm3ckqwC;WY%!Y^G^0%Kh{Ud70jA_9|SLE6#{UH>Pwijmqvhgbm!KF-+VQT!hT~0|89B"
    "kb>eOtTV>rb7alm?^mFFXmu9G5G+3AIp|6=h$9faAmR-MynR{rkf$=-a?dP&!@55MuSIp8y)1I5N7Q0SrplBx(XH2^puUvJs"
    "IH{>OED}2Xb^5bA=B;}Oe&mRiYKScFb9?Pjz4A%In*ZMRm%QLeHF=1CVwT&H#d~oDAs%(BK*L>wTXW>GyGkHj&f{Yu`N9}g4"
    "8H2CR`qdPy_IXl6EoF_(6<Pcanna}#BL>=qt;d*>x-l3wDeETzsHXL-zP^DX+X3^g<5?c(3p$EnI>&ui|xF#&-f!uA{+c^Vp"
    "sv-;WLOT9QIpKir9cuxYG`Wl2W=2@tQo}5Rf>RD~Sx+w{Gk{CvbxQ3Cz+dO=9Z?^YbeA8I1QkM<Hx&9|{SuocOCnWZJMP**;"
    "0$npbp;RE32nVUw|v&8%v;K$M|{69Dd<S8zd@X?eFgt@FBG!*jN;bmiHd+p}_|h_&K0v+bo9<73G@h}vB5Y%ZFo4|&li-l<S"
    "X=9K2K3v!P<_Yng9JR9qsCJbkD=EjgD1t7rw9PZVVYj%$^Ry<vaxzKKP&&*JoXoZxsyEs&bdQ{e|fquk2_7Gc38GJw3biF?Q"
    "I%d2HxmZTK5|rHL?Dp^AicN-SC!>wReRhz=6zZW`AWc*w?f02;L_<@eB%avNDq@vxd&NhrJ5b{r0bgF)C!plZ^yT!{>EKn-2"
    "}R$Zx8&ITL(Lu7XW-`kZ;AS(LW2#ap9uN;n&Y-{Z%AWhX8YkEa=!%zZwHlx2qecwNCQ@b#9HxD6%dx)2CkIh;|cAt@YyMl0$"
    "7ykDOS&-+?&!|fACPZb(@yEO2Ic)CvZ;o%}PYPKuslQgazdj(vbkTMWvV_k1$hrDqeKgQ4f(KD^auGVtfgv*<os~zfVyHq?V"
    "tmT<M2F4^BoM7cv(<hxC=PjGbk5w^LfYvpggXsq@<H1pk8h^k2qpE#H}i+^DxYYtMo&H8WonW=+4_yqT}H!JAL6cnrsi2I=V"
    "tz0a`mGB*oSPRGtNL|oOhTvqda!T9{--5Trp=<rS5(ux05Ui#;4>8aMt%tC!q?$;4&0>kt}P2+PYFmDLodwd|-QGSXSxJE&e"
    "PhQ;k$2i{dRKe=ZB=67N8Re5jq&%u?7E(h}^?#ptF8vRZuQLoOB2=f)-voz1sC}6iMt;ciHhF=Lj~UX2hCGYW=7z-Fi+ya*o"
    "gR5Kt5`veW;H-~vKZ5t1*{fXph&m)_1AkRNrk7<sJzNC-vl0q$K2nPbX@MX_<mxo2=%*2@<uc5gb0I;er-HqH1P8NxY~^QCi"
    "T`)i7qO9)*3g~Dxl`X2_otuOdd`VoWuFFch04C#kuVW0G(RK`AMA(g`;KX?T)mb*k%RWf8Z{CEQ7D$;OHhK{I&JL#13Eud*6"
    "tCFSEVK;ijKDI}`DAEzNoQoGUjT)b5ZRH^uLeoV7CsibG(QJQvRHYtfoW*HF1)F9lfH&v}{VWcLbsJaxPT$9kjTqCODu4fI_"
    "J#B`{Xrmd9`_s^~&pj~UP+%{p_IM*seD@lYj_TJW_<M4o{V#wR7qB^9<?qgRfP*`3a2Bq!`X04RkkjRFH{ymyi|0`eZvWwA2"
    "{k(%rs((R3{IopBa2!IjD3^u4LNuZqnNLwf+xYF(1M!Ns(pd4uaz^JYmmDFM7Ywl3rYiV~?RxS{Jfpe#^lg#Z)@wXfOQnAze"
    "cD1C#4x5T3I0y(zOA67m(cme35m7^ajOIl3xq+@`h#7I$gnc3nvzNPyWT@T`NDgR{`kv%D!YNFy_>Zop?EWW@ov$at-<xO%W"
    "<6hIH&Z@U)pU>DsNVfME9P#(HrYg;07VWDrX>AI(1)~=mTa-I-~5)-|Rcx4{L*1Kipo(TFBmpLVhZ<Q$tEzs_j;5BB2UqO9F"
    "pEKa9xYW63xw1xD<$(4Ofa=-S)Jd|&dQcs;8POKDZEEc{br`$0!BC)*8(bHOlehIWYKCJr((zn7DPq{gocZ*Xz>^7?_q&_|="
    "9V$_)Iem^p%nK{2uB->P}9ERSNx%r`#-NfDm6Y+(<<gr|29s6%vU(GG!a5ROng5ikBf&nspLR}!IlUxuH_4EY5p`T8~5i&RC"
    "#Ux(RM?dm!(u5oKpioMg@xjVvz@aX%k)|yN1h4dCoevO&Q+%hcdYLAur)1K6nGgnKa3h}Z$4uiZr4<VpHv~6=Q{fA_WR%BMz"
    "_osHVBkaNQ10OLVI=9u2Riu&F*YbDyMcIfKtMvLvAm=kYWf|6$H31QXU&5>l!V{=+d2unbBX8pfE_n-?9mc^GF|Gh$hQk=4-"
    "9BvQ$BzxPhvj^asRIAeueW$uuq$`xu)_BVlu#%Viy&zfu6oL$-cd@ekl&6rw&aT>2>;PBmxQ+FE|Q?av+%JTLhPnfXi$siDi"
    "v8wc}aF>X)zHECuP8F0<ES*A0ooQ({e6h4~^XgNOljJ?Wh}yBaqvSx?wj!oe5G%m?OQSI!frjKL{L@z$5S>BK7Fwjcfd*vC!"
    "2TIe{V>4!7_phQC%E8RhsP*GgcI*e=;<~?~7Em)A<z=PzA6g&Q&P&HzFAPGK>neh_4L2DI(Z^I$A#S7)GuNEW70Fz8|FC0jS"
    "p&U09Nt7;Gq4@lq*b3}U&zp;(z6jh0A`U`2hmknJUVqB(4=LqIrD#VFA-J!4!X`R_!vS=LAPLhl1RR#Uf*y-8Tt|YzJIJ&y{"
    "*|};d2EkMu`DQbBHy>o=liRTU~xEFs&<WGDZh#mM{>J3=d>h{=|`7BO4L9ivdlt&h@jU%9QE%qtsq*RRSHSs_{-0Q7|}eCxE"
    "c$-SYp=Ka8-yu%HcaTc@g4MlVr(~eNXsd@pQNnk)z$u5sj}~K8uTPZ*5pWfZs{H{NzHMrOa6SmA>8+6%zZR;g3r?FROVd1SO"
    "^RVwIXeZk$Gt0;FEbt51T?xArrW;N%VEX@lhq_AunwK72ee0>GtXeORjXbDy-k4uK*>nJcdE@4E<bBc(A+F*%>qD9+v=)_q9"
    "xgHO%2apC$;wb#>32&_o7AlM<?rmKyPv2`XlESiMZ^Pc*{WNkiCli7%5dZ7qtlAcg#gl+a6KV`A15Br#@3q1{@X%2ZAy>AWN"
    "1n8vnOjnpp1pEVJl*H_JxLq;Qck#vbR{Ulqa)iCNh6u2J4GVUk>8g;TJcwbH#tZnDTT)%@b0XOY%S)g~Iq}o6`Ue;q$fP`z)"
    "v1q8940l&P|)7_Yn)`~H7g^A0pByjzE21i;NJx_5PeZfgTD$Gl>q2FZu*#8-;hA2yFl1D_SPDvXja`zW4uM&jfu_nO+oO^Y~"
    "DR~YGvLfOuzJ2+gzn8(X(i>pu&PdJ}*RkgVq`OkVDi(r)w@pKAjm!;wMS;=nB#kKs+GR95(LbL#0<W6xc{;&1bMr)7ziE0q="
    "z_5T|by*|LefXmg<Es<<%Zci+0+uHjAMvoGO$nGlpsRYqij46)5J+{~Vk3f*sn({WxqK0ND|rlsUTICb@DUeqhtZCY7M@Jgg"
    "&&BlWK*<fX{O&aRK@xEz#SSZm@QLCaMd1<nCGix%U>u`r6ll3?w4-<OAaV<oTn@<lPZ@<V<!z{Yz9cUQ&fQw16F2cZ~A3*;6"
    "dYt@umbo*c{8I+L+M>S&q5PUz7ELCm`EJ}K;Wl{r0J2O>1spLqkcY8;i((IWkd;LTn^tG^qj4X5t%oR(*9EM@b-(?rW<-qsB"
    "25hVTB2|*H({BG`Q_{WV!zQ~%nDUT+PCL!1e0e8dQS1lV-ZN5vdkXw;zzvei{tn8oJ-WNI-WX!PdF6w^(i3UawWXxtccZM!Y"
    "#;|n|Szo+aGKQFquMBWl<h2LMzgM*Bis?#ZqyqhnYuVqKEI7A=TE8%|78GoQ~Ov-=jKo0y*^IVx|xM8%nc(>1~mLsQhcYYq~"
    "6VktVUz+vCfubH>0(Uj)p>J28qucE}oL+F$l&D+gIyfxuGgUL3ZJ4+A3n1>=s$M6?v{=K&IfjIx%Hp*9Pd^G4&0A4F6g9~8$"
    "$@2)<7&~TrjPPYSh_uUB5FmDP2xaL^IfDjvtHd$q)cv^q`Jhor7=c|i>U^w;UBvYbA`8A1u%bzwTM3EG5gkO99>{*1(%&|0}"
    "_`e}h05^n@kb3sk>2LD*-4>F;*s!K1;Q(k%4_8_6Y65)t<fS46tQ_e+RHs`)D3=Q;m&=r5aNjT2OJT6@^B9CrIpCqxNdv^i+"
    "tsbHD!NeXE<^?-HxSHLYP=DJA{rn&BDB*(>H_zMzijQmn=g8=YY2ty&uoh%9K(3QeER%N6~>tr?;&MaK_#A1O6bSmhm0`k#^"
    "V6$!B=Ccl=#?C)EfM_vc;jY8&e?ZW=@OjI|5O=l_J^L^+rs;p2K<QLk!b!zy+_dLk!uDa8Vi{um6u@tBh;HYoi-6YIKbr-Hn"
    "9Q=u}}K-OXQ8T55FnD5V=jS~|yQ6a<w{NkK`G=Ee8Z^ZoqJJ#p`IyFM_qb1%dOT(QIlo2#?C*b!{a6e8KDxI1#K;fXcWNW4g"
    "HN<htTX}o(B%SJ4^->RXU%%kZwz+NpTtT+de^DTaR&JsH>fTL*z^Ky8Qc=Iu&^YJ6uxORR)uIXb&e)1F#X~u^Ly7S?n1E*t&"
    "Yr9Dd{3K>NWRyeHO+;O5VmM`Rvqd&>8pk_7uW;i%R4^$EW!tiZS#aZxfAF)hy&JqC;%gZ=%Koo8d-G!gk|5)?9R#EI2b8@Ye"
    "|^LSOec5hiTP=_Any8o9oA>FsJ^?(P;{t!(91Ul4cNV{#tUDVhdVp%!e`~59+7pQ{d}L6yMoc(M7ko_8;QDCinS+bva?K;5z"
    "$G}MZK)4QaF-x*3rUyVqO>ogl1MEB>=sLQt*MD0Tq-s)OZdNGK;d(5@p<zjywYU=*Hrt<bnr<?5&6&DGbTi#>XLCe;;gqIUe"
    "RZ|HT5QrL|N?h@=@VB=fd~N+-sj1n7#i(bqx|Gruy-mdgO-ct2w^BTsf7_dl`OUy_WXI=`@9yGwz|++xk(5rm#ExsOn<zQ)<"
    "fmccW+tQSzfto)1NA``~koyruR`=7EInnaXL<SclA;8YpLRUD0F!>?O_TeAC#5kIcjaO}j=<Wg&w{XJu9Hn@72ixb4}6>L}a"
    "23CitW00QyXpIRC>OR{swF`9Lq|x}~RrQ{r8F>5aL)(x1wv|Y2FNTH?%<F<c;KHviYx|flBnhk>@70|&*ti2~+($`hs&&X<9"
    "0f?KdoUlHddE+yjT<8EYAll2f$)57Yjm^l{Cs@<?}c!8uus~A{NST>0z;NXz=KZo^q**AuoDX)#}I^|TLAWr<43Eqa+)C{O_"
    "TTGokzej0F+A}w*LErauJ+NlI%27udN939cB#Es@6B@PE~VpqPQsxB^}C^0Nh2izy6I8bl-L~EJDr(iF-_!Kb<za0WXyW9LB"
    "diiT!>@JGn;LvRk3a;nS7bS_{lzGN(zXvmMuOOT4Ea6Tu_jS6^bXZ#-j%mHF1gG1D8Es6pvjc!_qx+SUNU?pR94f+$k~Nz>?"
    "W-X1KIZ|!|CDE_9%cWfJU|2ox5)u`0*KM8ON+_O$RT!?u(tC&~gAgQu1RgV9jF*hFc#IR~5HM};5i8s^o&&G|4)X&A(L9rhs"
    "TZ@*4DQ-)OYkA^9en%jg!`*V~xD}a9Ap0YeKH~gyX=|3MdUwToLK%Yf2bT~U)7{p=JXzwR$k4{8TRKRT44%B0a5))5SqERh!"
    "##<BSa>bs)#WL>?aMpp{kv`uyn>KUE`3b0yHWQr*oH7~caE8{*<-9E>T>SkB&Ho5t)1@h2W(?3%?qrFVytwc2Q>^IjO?Irmo"
    "GTL1Ys;u5$H`Ju$IY_L4h;xqv}tosb&YGt%6lwt=I9O%`NZ3)?aiGg-^%8m|67GwNsD)4!AcVD0=#CW&)vyHkVjQR8dXE_3C"
    "~0le8i$=au3lH{iiz<kw|BT^&Zeu^rP5;hO?e;#ZP56B22nTr%i%<NGmF)u<|Z${NK0Kv_87D5v#=yN0n9)U6zlK!#1rg@${"
    "WJe{5uCSY1S!3Y6S2b@w=y&qW(8!(ysAPgSN(>DS>x-<De^1Z^327=NFfOrOHKd+!w#{Ph%7<C7P9Y*lIG!nr!8ReK~_g7!s"
    "avT%Jh++4wMB{^kz&eHp1M#0mkX^HJ*`Xx-ibY)h3JX*a0^0jMkQ?_V=tl6KmZ^I^NbCwRD;kSEhDD(E5@YB+6UOlmS3#@xQ"
    "W}e3Py^qk0DFAdEwKUtuIWwneia(=k$@6ahEFqKIeaN~t>)69kFQ%$4xD9qnH^PfG^+eo!xCB`XytFo*$~K-#b=z{Ro7)u19"
    "ou-MXKdt)VjEm{zBwv<=#JAUt7Hq=)Ovyu=4fUIId?xZR}b^&aEUkNXNBPW-~JjadQ`953-b}${B!G^~X!&i^h3c75-y`*Ta"
    "{9r;OX_v4gLihd%4mKDggZ_~XGW!SmQtd-M#}8-<VVi{W2n2Z^qRnRdUt98#E!R%5?D{z5t7dEvxZT_Bf3v~aHhe#(-8Q-~2"
    "}iLZ2S(S-Fbytb(2nb3K<hgc-@*O7PDXcw@(8nX=*J}7m654MC-Q7;S-pI$~-cHfHJ--X?r@R)7!k()D0Ws1&zqKDXsW8M4j"
    "ceF3mDBTSR<diDK>b~dF7_qx68~I>(y>wx(DYHQJJhDn!Rs)cNe&BTn!SPZ7yEMN0-4R<kc75e?aIxTal!_v5F159ogB4o_s"
    "^nFj@?ku0!`ZZT_k-61o7U^!Kdv;sH3LXK0NgAZ>5sauIBH$o02fTkN31D>Qu7hu&8F)(ccU3mbSViJv)z@PlEX3aB3{%)>e"
    "ETC?Xd<sGT2Yn<d*v-b;TU2re0uI9jU5FlHs#;y%kf>{@7wu$-V6h)MKi4{%;8|AO!YG-{-%exjRk_$(hGoUu$z6dAiiUx7;"
    "zhs335#P6_kn&n50Z-!MX+$dbf|8+n+pj^e>0+=19FY$j=fJGxvHsfi2fOX5F+!cg}Sdlqe^T}Kb>4UY0|eVdxMD>tD`b5m~"
    "<IHuG_D84^)9Jd{w-NQMa%|H0UAfcnpX;nU3RO08Ionj;w)sjV^@MTJE7qdzwxr$y>V_6?Ap}AABjfpGLqxT6+jS{mmrs5k!"
    "UI`wSU`oFmtlPE3c=M*gdsU`;H~O7U3iR)gcRrn7t|~0`cugDs3!U4rWzSt(W0Py^`PN?0C8^|%^cOz+ON{grNtq2r|2lA3J"
    "YJZ-3}Ht6W!g|*%T&KD+cB+f&!G6|E3C)pmu$~U{i0}oHTpwVl)JC{&~rdN{)p8-?(NK5VL$e}NxRskrl2KNK;cpw@e6VBlI"
    "br%`GUw78D_8VIOwWqkhtDpVwDKKd^=#$thWIV&}sYtrSOGs)a3hu4H4)YypncKUtHh_x{Z+(jpyZp`+X1K+t&cPZ#DGT=y2"
    "Sq{~aW~y8P7i4Qm6L)in)2l@PwVb(ts#{FPmpwk_4gDc#_OURJ#K#z2~D#J%tO#0438m?<Fa6f`<V8Z~3bRh}bLP4zHGX6II"
    "E$PIz@ma!C35Wy@kh-5nQ?v3jRCjM-sv0!0v=Qx$|&@AvxKck_<Z@<WU*=~PfMkdlIqc@_7;Ia93D`i6kUBtj9yuXq?8V;=Q"
    "0RJgSShh{EK9~x{J116muTaoM3O@`!??rZ}bSs$YywRQ;(>Q|shZCI%@%#HiBb3x61|343%+)W#M<GM)&<Tv%@$LR^@lt#4y"
    "^#{L<X6K-=g6^*Hdm*Kw&u`y=Nu1Br8EMruk0I`&CMtKyMY_csFJdh23)A60<>Onx@b~a^<RX`0K;67W;Q)ANj^NC*Fscb*q"
    "Ihc+<YXS)RtX`REyYvyBn%j^t1BdlR4lZ>*e3TqapdeZUd9TXVOH14kf(Q$ST{4EOv%psJ)*9EC43?8+hK6pUl2h1Qpq8%VH"
    "aWM3GuUOs?F^vptnrR><)J?kYPggrIqO(i{zuM-wH+_C;N|-X8r{;NH=UNmHhtVmt6sy|5A7eDsDORpUpD{2gWQ>7m}df+l4"
    "_r9L(iAvPx(3wnJe?~1qTw?yah`BbI9z#L-IMI`&K4Zs>vRk}{C#ogc{Rj0eDNA``IB=V~QlH}zDa7}SWbM!PdS$pGAz+K=e"
    "s4&c>_=)uDkQ&B8!e{e_mMK&2!OwT>Hb_Vxf&398`_GCwH0qD&>J+F#M#((ZCNDN{B34E}whpM5PZu&Ma%jAK|4aw_Acsx~m"
    "B6Y>Go^)+$8*YRu)gxuxRkJ-WupPv%xL;5duWZ!4ERQ{ave&?=D(0n7_gMXm1MkMH$NJ7JbELMHT%Ym)IlIc<qy&{KleXhpF"
    "fbnuW|qx>BX2vJN(=o-^<v+6U|}(M~5iR$*C|L%U^_Ykvp*2&Pbb&Xd=0IOw-EBkn{CBaZF$O?8hj+GpHE-ny*Z1-~NfvcTs"
    "glwaeyj*_(oE*W!82-gw6|pmUjPaHqJ7qDvX#!XJ|?D+zKHc&S?S6}iZid5=^Tr3<&Yt0q%siPrUly#d*gWEh0v=a=}04n8k"
    "gHzwKV0E>y)Xw9G>mage7%559xPp5>yXKy5Z9GM<7%!o#YbL@^bh?TVziAx|cfM!U@vdzj+3$nsB$Rab$Br{E_d{gRepwJ1^"
    "r04nuEGNwo8J<NNJbP7*gyJP^J!MQ`*Eu%dsyfefwM7ek@m^Hq>pCa1+Qz5fI~w@Q6o@4su#bH{-TU@ugS`iG<bvBFL`l^yW"
    "~2dms+<>ynRSsgu=gu0jVa9ax?z9kX@LuAh4bJELr%00^5w1mDIoRN+PUtzIol6s@Vox$T8_MsU55TzqT40nz7)ak%WiNzg!"
    "`qLWHsktcl7LAI;<vJ4*~^@uT!hR5_M+X;4SR!$NrEn=!RIDO-V#(AF5y7oym3Fj+CWSfC2zmW6x7sT$l<JEOg`|U;HS84Qu"
    "wFoWeD%j5Ru3R~ty(-A0_eSS?<AUACFmThRqZ3OxoGl6g$Tqas3R&Z8Ow?esYcOV9}U$dswy3-NW=2L8F?=vhMeGBL{ocSUB"
    "T6xj{GG1Dq9-j%}4dzdb)#F~_XDa6jBLVID0k?!lWzxJ>D4akW8`q=!K3JF_wXB?54K&jPr0Yls0e9S9*7g6d2M9%~?FVI=x"
    "@6$7iUIX83^nI@%*y~;pn)#zY3JxdR(KG9FMX_&;_?7b`e}_`2b&XG%anV3O-iPZcj|*8J9YsB$RJngzhMYthWoj^E7Y(r-2"
    "#J16Bm}eS9v|0TC3rqOTx*$i*kB9I6C90=G#;gmkkUbv$N!{?yFz+XHTmIBjidRa?xBa=RY=7|&fAOvpcu~^^$K#xxoTQWg7"
    "Q=LA9oDI>S7;D-&d3NF*2aDwNRm1@BTRkUf7eLk3{1HjK>GlAW~|Lk`^Kc_qaMqBJ`yZGev1!FTU3oiFa#Jg(y^i(X^kj8*Y"
    "IM0IJ1sYp_zk<dA{V9}w0irx{u&Ee7C_$>@ydMb2L^#LT;Cot*j$P>}nxFv|@`)3(x-TBowwb<YsZ;?BJ-%G2s^5<fP7%g_="
    "rMeEUrS*Hg!^M0uGoC<e_9INOs3LXMsnHb@%IxCET>qe%YTc_~=07QHU2;u77I)Po0fD^?ftbXUaNA|e@e+T>yxc!w9$}?ee"
    "LC0|&ED#*fBo+Lb?@M5n>C>$#;IW#-a^zq0VDfc}uoctBqy0)moxpqthK+$q)>Y{=`#Z&4ZOnofep$mj)tmHfqIjP$VXfM;Q"
    "O?)LQ8*)BX~~s#&jBOq{Z7t<7PI{knC9(*@__Lg5vt}dyE*`>!GFhfV*vR`Ijm`LY!-|ZK|Cc-PTjBU^@1rqs<y=q+a_q8K&"
    "Onvh}r7>^?n7gkL@<?<@^OEHlTc%g_rwTxkhaKkd2TmaEh>E&e)#|?IJc=kYwywfX!!tTmONf&*TQ<{#Wr$BSU{G@T*^o?bH"
    "S%<54BTIIg8AFhty5!_xZ+)!&qUUU0vU>iT>c{wb*+*Ba(FmJUXrBs(R*c9hkc(<*R_&>HH7_MG=1?b|eK={s>al<~$5y&V#"
    "q7^ibmw>lE4#>mOgpo4PdZokX=fHtk~0PXS_6M?}+4Hr`9-KRWg4|$itjK+JA)LkHgmD~)pO0T+quZPm=S+<`Bg_Bi_oRlk!"
    "Ps-RBfPGHH@B@gA$5VtInOn>FZ>@G!Wq=C!+GVtF8*Kekk7WNbFC0hz(HqD|>0x;U>kO`19-e&36&uz$9m4%nT3vE@!M!xfH"
    "}7UlRD~PQ)kyH6+1XocugN*vOvaO+y}O)Q1hIX{Y3ZiqBbNI%av`&oq0v(4!?E~TirC3@@O!UC&`DU}$@{yTa!v$Y+q9{^F-"
    "}g#Cn?0`?dF6>$ake+U)<k&0DNJbEPg9$nfU_lL4`6nmm&~`x=9<|&#eR$W$hVbgv+o5g|%pO2;h&J;CZ)|H*U7lA+FAj&kV"
    ")a1w(zAKmhNvyzR1vrjIJ;fB#HmiPH6RuAMq8x1WQ{XlW5EH($;Un;|QGOw}$x?xw|e1^Te3$th*|(FZdSN`2wDT=7#mY|&~"
    "R&hbAwrvRZK2#b28#s_rCg#d4{(J`5ikmJ<QFbdM^=}%yRQMTRZe9w1yc(~)4@Q-e&2%dj9+WGRal07F%IzCwq(DHZ|EW6|L"
    "m-&fEIH{vH$FOD&w<IIwrRe&oVyL(a_o&_pFH;sxhCLRyY3nu)KJdMmCkKIuf-}Y^WgXUcW@EC0(XZadPQ8ul$hN>bODEW%H"
    "V?W<v;1Mn7)*gPw)r0*VkFx%SxR*WxcL<DuonNmq3Aua&y_IP7Tl{FX?~t6#FwLwr`Vy+RF1_JH$9R@ux>;FxbDnY+1c|+k;"
    "j8_1L#>tBS@%;Hbvy4ldLz2r;%YjTVgFMz6_m&#GzMAmP7SjIE{t7e4NOIF{G0ifBS;&SIqVUl-J3sL^sgu=WPFmh1KkHa8D"
    ";;#0@bNh`A5pW@Om93wM#G*k?lj#X&u!eOJcQ2Cj+Nw`csIv^L_{Y{hPaExoCdIM6vKAZgiEX1)G-&``>p<o^4O2L6K-f%>Q"
    "ahLV+nWi0+xU@NDKfqzZ{C6Z=yz&x|TJNbjz)eyJoWLOZ9tV|!L2pZj4-y%>?z2VdNYoUWNjYOqIL7t61BM)e*8QO&BuwVn&"
    "Kfy(<b>B#-yug2%<qTC7_^5)@ftf$wT!B#DwV3R>2HpO4b?;A?@;V89xRIXcpu{DKvm=W+3n(xuRHmQp=diSTG2VZ><FIv+g"
    "o<4_j+a6|Bj?CeBzQOeg4yn!IM}EaJC{}g_p!Pu^+P_hECm2MJ}e16!sPkO*m0v=t*|5>V1vj6a7H#$^N|JL{2djxXGZv02J"
    "(j-eP4oY^WYy841Rtx#q#AzqFrk&1=gnOy3f|NoQ*0*oHE9h%oP>31lux_`}^7-`wv=1Weg;8d5WYoyfl%0Is)WhwWi8fz3~"
    "GN(l2M~vSAu8all0>CH6$R9OTiD+*BSUhdmzd3}qbXPXHgzaZF`lR6-Mo%v@F|Kb&Hb!SLy>R<YV$DVa%w%a$y$kgKy?CLR!"
    "T!#w_8#1Z<e!<C@G!y1B7;XID_X4Pw*j%wMC>{$X;@m&dlT}S`tH0ImeYRBV`m4#^LMLCC}3EfuX9p&bhQl+h~P7e^Gp05W)"
    "a1*`01G0*z=j($GO1T(I{`z_jD0(3f&}d|LRXLgCEz4Ea4<mwwY6G;Wt@iWX2Vjk{@^>krBbb<_l3++u!w`ui^YY0IRSH3~5"
    "jqIa_c4fl^)5@ocK>#vf545RAdpeIAe3>;hSYN^8((7<7t42+|Kk@=b~_JSpKo>~M=$IJxf*R#u@T638oYS^iqWFFmxvg)yz"
    "4jTZDJdZC_rz3Kk<qw&Dj(?(__zgE+BJd3yGGBYZ>7u6?`Mf(EpIrgF($c6HEMu#n>Bqsv;#t#4#=)BMIj!T?B;TLNX|^lJ#"
    "BK37k_kQ%Rx`yy{M;;fG;VDy#VWZx3iVRG*QD=#f*^_Trv+eNNBBC|GG^2>ny|kepwx5wwc6=|gkKL?lC<Lp~9JxSTL{{P8_"
    "&p@GO-G4Z@az!}B8RW3wf03a!w=H|~M!|p%X!Ivb(2j~PS!vUB2cPOPqzE4?U3WG{1{0+CA@6$T3K(~iqVou^LWdJ<QId0A)"
    "Ss~B=3#hGic}1qw6LDHMg?)VWx0~9K-x7#RJ>N`iF8E<^`Xb-yBG@RIRo1{M$kVL<Y}8mjI+7-01Bg9-=B@*mKi$D~YY<%eV"
    "A;7Q2cF8Le71QSY66MTDm85)8ma&tiicS;EGMa@4q5<k{GX2tfkoMmBU2t3$kq&9VLLp8R%!Ori9Yk+EwOiEfG9LNl4R`;P^"
    "&;xb?#GsI%hzYH32Vrxn3ZQ$!fx701CM<%jXrD5Y>f`!CLCCc<f(N%NfI?mc?-h_<6I7?`8-{OoM233I`-YPDF#wPB_b9+cO"
    "uQn0Ixs6wPN-c_cfSHr$9lsk{HoHjEmc{$;k@Q+i4oa|HTp>WL<>`i}xopFQ^;0F9#Th|9o$@w5j0_XQN`+Aj>=s{Ymb#QFq"
    "hEy<!SHYNCiz@OO?_97LUytL0|yqrn}`8@tA57f|EN*Ma*p4i5dkLYj($MHeIyZ4mmb+GJcD(q-0ReW<)Yr6z{sfZ<%%Ia-c"
    "f$n#9%F&F>!rHrXvI@;(PA)?YMV*@pbh+o&I;+84vVv0oD<@QOr)2NPKlZg@G0Z%tLT#Auh<#6F?IF>*82%0a28#)>F^6Lvu"
    "-b9#?VZ?J<rVL7YJB;e2#@EFn(!Ue&&d>jhf$jwTn#a8y4O?ehwf9cZ{Vk6wQmtZ_1v*HFhqtITXc_Q%Jc~LCJ9lw-{P~j6B"
    ">{6n!~UO8l0EJm%AJY8J9b;d&(16N~(!WL26eE9vD&tS?#nwm!l=kjUFDj25ux=4%T#PJOC0kIbLRbQ4=8SAT3tI@zpy8l-3"
    "K1@`QGpghAFQ<hJc+_Z39vgur0ND+{#c@);|AEBNq2GRR&e@5^_-;Ws#`zy@%?+EF*boVkbG<Ob=bbgQl1t{eSoJGSSXT3(Z"
    ")lmKl8x8^t^Tx(SWS@i|^Qgh3nEmN#_(z^IJ^EM~5T@ooAf0UkB!3T#nbCGVRgwqn{HyPb$C2#?e>+QZ$alzEl&K0ud_HM!<"
    "do*a|K!(ht7INDR)f(G0beU!?mdr6p2o4*cP{5;c9G$pG@MYDWzl|6*iH|2z4rc$&C1H9Bh`l;DU&kYfy=Q5tcw12`WJN$=E"
    "KfjyXEcU&eaadu@s)L9F|qUNY}#XgduF`b;fCsVubT5%-;#;zm%(QMk>^JQxhg9(3vf9}GiPP|05t*OSW!olNc>PE7_UslKz"
    "LN;>-FO2Y87Y#7msCY5;po<tJllpLX@D=eVDxNUDy`0e77l~_ZT5ki&MWh$s3#uVn#1~OEun50FPw;(s%zDf8WS83pl^9b(-"
    "Y>|C$H6dyq65Y4cFJYVxx1ZJCdMCH`7Wq<@@3ks#KqUR*ey_SP*m=<9$#A;2<8lN}rIOYnIJrUQm;FG1x;hMr~<kF{0Tc1~$"
    "Ft=q<b?;Mlo|9{TRakgTH3Y4&!<pxN;^2HG;Egc0Dv;N)!^x<9>P_Z&<H{iYQ;D<Z70?VS<52`Z80TtLwWy?TC4otRzg0C1p"
    "V_?vkZLIN@p4BK@m~ngT6LIF|b+NC7t$;X{%8dp~wAM<@$sK2C#FLe~(V2RVQ9{TbKh>4-$x~yZSOUQ9ii$*W@KT6aN|NHGO"
    "74gP-mu-3K`Qo3^K;lI(U16m{doC-i~2dt{^FbmBYNx@6QRs#EzRr`zIc%n`po15KL#-SW=`k=yHn>nM)%Lejby>QW=+V*FA"
    ";Q;aWh)|1rvB<Y$k-4O#FU};Ry9}!Rw2VOn91MtChzR(WPv#dfJmUKl`UD3F*Rbwmu75%_AF9(l0xjOz;9|(=0)Er6)teRoA"
    "fziF~W-e?=gL`abCZeA<T8@~yI8zxMu9-*~@dIs6o`0?78Zdpypnmm6b`GWl#Wg83)ZgG#%5H}RWfuocDrDkCI>$a7Eyp9<f"
    "CkqA+isW8B+p0LklhW?>%pp&_dFM|bE&^v+N8*FGK<Z*jprq00doa(Gu9COttfA=50oUpDp!f$zEt=!)3_eu1!9)~gG8wQu0"
    "M1h9Yu2EPab$x^}qNw&Dv|$h2U2c?eQ2^{`2p6Q!F#spO;D)B)+LQr`%!s*GruvUqq3shH0f-l6;yPpODJlH{4<F;BkLy)=0"
    "N^5{aUWRS1Dm?Z;)UHa0Ug<ZS;bZA*r~#Z&Toz^UW410*FEy+N~WOXrlE-%K>Y!m0||i$_eRq8G>JZR;Ksd^O2X1Z?&;!U82"
    "{4r9cqH>@UazmPzf*eCNGEfZ7C_c-D2ylP?NVp6$-l3)JG-48<lusWad#(_K?wdmd!@2)8`h$H<g>*iIfSk_HTukXJV6tiPs"
    "kY@K|6AVHDY)IQ!fGwdi$!?A5ba#Qp!qBz}$!RnT&-)8MyeM^;%$glZ*j8iQ(&cQL!JI@E0_?XMZ`M0#A?rrb6F7fYDzt)^~"
    "AdC#>PUn51O)~vr&Ju$~!OV%sBa2T;_Feq1w!O6T4>w<<Cp^c9Nx;YtC3ylc0Tt-Bc#|4^e@wWc?d*by&(r9s+FE0#OgO7Na"
    "4IwgM1y())Tm%Iv0Z3ALEe%F~Ee=mH`&`(|(?)Ok5&0<!Yy{_$9n?;-ndKdvBvW`>NcWsUGLCK2QDCU{Kv1PkB3l0DZ~aCiU"
    "soDAfe6h;V$v8}DRS$GxUL7}Zqh^B?D!FgL(F{h)8X7@0o2z;e9|2OPGX40cD(gPHvP>$MNriCQxB1q0fb1%%K)jsd#)_91b"
    "B(&xUtAiN>N86LyuC#C|U&K$+g9m<UhhkA8+hGG_fI1{7aP+;R2S_j(Yy@Ue-AZ$L8N~Xtl?mJ=0Yy?*!a#(@@(!KN6ZLWo>"
    "v}DrB>@bA&3jS?&!>#BF-r#hzwKNm!<gusiuX*&nU>yW4Jvm3czQiC>hfgCpF?d{$i7<J1F7>aR&`n^>{)zO$3bM~obKCY9O"
    "#>z<nv^u)o*AmM?q!6~kKYm1dysJy&<GArH|3m|l+n_{labXsgWLR*eg^nG9!EDJ5D2ju`mk~#D1<5<J{6r*r*o|FP`2_8<("
    "u~Y=cP<)hd_JOtRU)fo7uca*^5ONF)FHtJ<AfU(o)#YkLAIegu>jLS=Ug)myH82(R@X&tBk=N(KZIB=Q)Z-X>+jH}!&t5v(_"
    "jh>y1gnAt%%RBWB$z4Me&U2p^&3QG-y(gp+&coCF-%<Zl#Gk|6Wlkw+j{hZ#|(~*H6Es4OQbRqk?*G1Dv;FUOt3cJ3={-Fir"
    "7+;G!E&<&vG7%j~@21)#Sgy_ik3em;R@47KV)!g7~vEId8fK`Z`c2dure{0o=%a^6LPtSDCD2RUTve^NhRCPq>+jAk;-%)zr"
    "_{ozn$A)VvOVv4O!J_})@^hQmG_IC7RoDbN%REd5BD+i@oJke(1$!I9X(`2E*P1kU%K*cjg<WI5)Ue&_o}yqK66A*dwljj|Y"
    "^q=Px^(gR41aXC7Z(D)x)%5|}|WE4H0UXfFWM^r+)bH4{SH(i_sTSF#=EIe9(+iwfATbu$A=4!lDCw5jO`Nt}7yNiqqK>y!k"
    "B-v;eNtQ`dXFkF#Er_eI*V6S{i1K&#2l%a>$&Ryyj(@U!{>p`7P)W%NV;Z!MX=oAkJ}W<Lc6TzHS#ka&LyUyG%GyPKtmByzA"
    "}-N+T!@^OPG(8@i&r^375T!uW5hIEGW{kDEATo&Kjs|1s;Z*ZUrZRufAnINA0=`?>i$ZtwHR2xqjqAMUvFj0z1mmzkumUE^?"
    "An)`VsRF$B2K>tBC2c_rk2uFaHp>-?dO0Ej)>@*wCG?NEk3<`k92JSWIB?_{Kib$1_$Q$xCC%pKQ0!QHBA-M<R(~&}bGLp)^"
    "j?PhwU>He8*IGVuy8%5)Psg?95^#^yJY8Ho|cbQ0UH)G-*H%}n@jtuq@x6;c!K;r}#0D-RQ1xYf=@EFhdXU;VnxyyS1jW>6{"
    "}CH%{5?H_9_5dWO2*R`Jl<dQ-G5H}NTueGZtM7#QR-@esV!AFeY-{Zpp)8Z<|maEEUsVx0!pE(4n40!;fbS$py>u;!<kcJ_j"
    "%^(xhKe92+FAtJlH5^d<=S4s_%OZhPX`=Y?&^k-Ck^HJ&Rf!{Mf&W*(2Ne!u2>srnq6;5qJp=nebM1O3mF)O$ccf<G8xmEIh"
    "w2Zc<L~XvfUp7#xW*5y?9dEF@iK`R978}|ZsabVIvedqYpa!EeiG+R=kbqKOt{A0h>K(+7Lmiq^W4CHfD;@S{R6x_&q9;_Z}"
    "x-$dL}R7>mKgmA%t%Vj|UsMiDKBlu8)*@eU;tpo%^Q{bk*NWOR{xBL^d&0P8=4N2NuG84Njdw@DQlKE6hj7+V{J=E6+9!IT?"
    "3i<$MD<^2JbJ91gH{`Td}#lTc?zoZ~wES2iX`M9p0<sh5mhu7gPN%S#}rr4X8qP!>+02mny1ZKPgAhsy-<kUI@N3BM&2uAV+"
    "whv>^q#q7_nynl%eu+OdZ)e5&O0;p$=o9xu4V<5;r1(aPDMIt~pzS8&%4D)keVqf%};}(>7Ah9d0ckgrG>C}yhsp#><H8$2J"
    "9#skziyr(uY3%wvtn$YPCQK|DaA?v;sw90;EU;Vh5f>fY83H=x0*$fTzsSZ`+4e6Y;|Gl?eUl_D8jnw(e!&_B{w5T4`)-(Us"
    "geT0ajPw=Itl5nP(A<Zcs%s%RU;)V1xUXmQu1hhFDDX%okYNcUqvQ%KT%@h5ZQ=>*_b_oOMpiv?f6MCfx4EXgMvg*-6oJ8Tb"
    "+B(ag}<TH<<YFo+n(U3ZI1HAf5br=DaZSK9Vv!u2+4Jm;xWUH4)Qb3$KQfN99tf=CO$UYM$=B6tgoBz@(bQnQ@kBb(8(xdyE"
    "m%>=>g>rGC=O;<^D7SKk;$8vb4m<5=$5)1G8vP^zt`bMC_3u-h=IOAKtou6EjF$3}3Aw#~|VgLfmj0LgvoR{ruMb$}vzin4Y"
    "VzNf^wxI!KxeuUI@Dq{lNoAeFzbf_0abs^%{4j(s`So1Gc|61%@tV#^-3iBhNuR^0yk=g`Dfd>rjPTy$Mi3pj$tt2&mSQ1{I"
    "OV}s~LCa`PI-<BJ?9%%n+jqy@ee&BTLR)JElU-IQ5tl9OxN9{Yp{myz6hDsMDy)LIFEijeJg;PoqPZth-ZZj-Y<;-+-o^xW`"
    "EACS$Jm9C)J#r`4j$nR3Tb~Bj1c>`>?^{#!Ub+a1PP~f06v3`3l`oBt%-dx8D*85jxefDZcCib#0O+HO2=*xjt64nBVeS^W-"
    "N8<#EJ(B9G9!GmpZDqaIm=XJr_~_DKM4L#K=R|#DQ6@4&54ckvZ|jcVXKjDuuZ+R-ir>N1}Fw*usJn8wkfLJAgxcWX>t#Z)@"
    "Xlv5i3Mf(B;MTFoGv{J^x<Ga(hm=naLRw#v0zm81kVAGcT7cU{$nU(dB*AY=?Dp*XPRQW**bg0kR%XkJ;sYgN){XO?Izn=uD"
    "SuK1x_%}9)dd|bXAgJnBO{qH4-(nSMua9RT&o5q(PS5<=Spu5q0zl|Eo%0YSv%E*$q35Uq)_}eF^C$3vJATCJ^#mfe50&Mw|"
    "$b7^uRa#RzyhE*neNXdk1>RhxF!UH3TD+EZFQ+VILcz~kg@R>rO+sv1qK_u<0TwbK(M-j<V&Dy!Zf&)T^Z=u{P)p<=vvEa#4"
    "*ZMM<i<K{Y(gT5Z!Sgd|DJYoEYAxQzgMIGN=U?fASJ}rBVoV6VR!;B_a7%&?@v1tF_qZHFRJ|svcD_AvQl^ryS|BSs34oX5="
    "lYa@@0T#F4%Ewn025)=1f$rXcnv2z(W6_FNF+~DG?KT@Kxc6poAMz3WJMEGE2i|3gQSLZYCkor#gQ4)JIQ%6SFRL2c=BV9c6"
    "YKS`VNK8qA6ZbQVTe0HDMGO;q$8C5DF$u81x&<xl7{O2B^+=V3@~k(RK<OlHwZy;%H@di%iCmNY-}{zk;GI9Q@}Gc3$4$g6?"
    ";z;XT7-dL|xC|b3ALUtP<)zygSw-O|}>aov`_yLgiwRV~?0RP&L6cxiA^dvb8Lia$^3Om<o1bLaDo%cNQxF4*idy2?Hed+7;"
    "QeES}pKHJVMg3UG#a%CnxIy726dYt<(}cex2a;P-996GRe%v!AW>IMP1~Z7KBz|rW{I@DXzA^CD8d3pr5(5jfMJkkUjq<dU^"
    "v6hN+2rz0)4mv>rBm{3XYzs*j&4WW-L|~F)N^`bd{iziWPg;N+f#i>i<hHdEX2bEVaqzR@9to~g^Cr~t!1tP%4;`TY{^8_tw"
    "v2id0AjuYC(mO8d1b76|gSFJh<m_|81qmL#L0VjwY2+_H&eaWkZJ_qEMDy0DxZe%}e05b-uj2Nqg<p5FdcHYf_~{jt!7)(ZA"
    "rKhkx}~V+ZEBVFNxUS2cyIF{!94=)eJ3C%a$q?eoU`pS;oKvDa|htFs<VcGPhxOv<*Alk0PpwE*gbE}9)K270Krl(Hw$q%qK"
    "zilohug}SjM5%>Q2)qdLT6{ZN3Y-cimXE`+bTb2Y<Nj-Vnj_k!?2|cMoG8WH|%Gyh{-*G3j8<rmwbeg6hahJ%2l)4UjOsvS="
    "fiqdV$)}RNu*uq(ciN>BV$&}R`(<M+hG^lxhivEdyumddq;0l)KKV4B@{ifu;i-&~=p*GJzZ~G`yKV}IKy=t&KFg#I%z&1iC"
    "KB5_5-t`-oYSF3`1eqrdexIYwtl)QC3;V^U9G&anZ3Ek{;d|4aG(A~0$=PKjfVdEB7I&n9>_8*00tUT#*f=^DBJz4FxWKIUl"
    "Il5h!|YpWAs0DzP+s;X{@AR)gJrx7o<9(S0IIG$Le3p55-)(@GkLmQa5mf@=BHmAR8Y-bdFz`INNuOK*b9p9pT@#voWA9S1E"
    "8nY6Fu2u0OjwU|dnKFPnd&2o`gK&T4Vzp5cHWXC&>pd>G;M?TMx4wks+JF5Seu>b=Vou2(r{*u!DJX4|;SVxKsUo~TD(B|KM"
    "3myv%;Y-Kk>bpCrj$|jW9WlCij0GAs((8oq21be)yf^qlnY@P7|HAI`4-pXGqUz&2i4SPYtZSFFgJ}x)tqbUagnMs3k#D|>v"
    "+tRr>L?KSD!zQc=M@I{MvVmNaIE0_(B__xJT^pH{?l2WS`e-GOD~ECqF(2^wexdRQ${UmHZbe<v_PB{vom1QSkDn~r(HPii@"
    "RXlzw1zJjOCJs+yUCQKE;}MhkEmu>2m$1V*V$<xvz&C5QLR?j6o!1M5&c{p9&O^K)*Bct{KoN@<CJigL;juPz3A+dl^CXBHv"
    "lUI=JNmyhmSUaerwz}d~X@rRBXQtF$u~N_!&JLJ(Pu>0k+~<8-7Jnd?sTw9>d%#7{hWE!L#z=1t6C~kr;@`2WUBSRJlLgqg>"
    "MWO=YVlO8(>5FGd*mc^&>Jn&CD2#c+O6tJN8*w#b*~)9Qu5WuN___MOCLkDbGS*bcerxr8sWfx_*ti1Alsg}kKfv^B9bzR55"
    "5ODkV!Y7*0O0dSkovwu$L|IU!%_QpnN@2OqMbCrfpsx}%SE#$e;sp2lVL9Zvp(^5t@IA@McOdHooE-x;qPw1ghp>PHYLIT-v"
    "^5B0e&hq2|Y7dE)%5(-P+s;I1`guwr{0f7asm_T?KkW6>(Sc;B<ub9zVP<IiI2c*Cc`8&vc#AC>n|&pjiW-xY4|<G=`x94vu"
    "*h4gRfXgu|Bq<vL2b?rT;i(|0v$?Vj+03@?layjfY+j~i>qR&aEgzhd%xa0@r?l`a}hB_ZJcj@++Aszh2)bXW_GOG-%=7Kww"
    "4mhjli-W9Pv@Y^C%@00UtWju=C!#oa=YjTM7WV@%^_iSTx(u{ImGwM`ZkD6xgw)b-GHYaj3bs-kNwiDd61qC8cbZ(>@n#YvJ"
    "ba{=$bZ!1cDE>E=gDeJ`0|-BSiHQ&Up9PpCttsK9j+kl*hCCqHWKsR%BRW-HQpke@2zG+)(h=XNxssfaBVN8>KJ{qO7>9!jn"
    "NU}{yJVqjGs+lMC{USSaRONGohD5)*I`giLx?x;I{n%ho4rr*EhwCBuMi?3V7T@HSI7z^wd0uN#xLq9)ixRT@`!iltB`lm@_"
    "XCuR(AsG=Qq`?Sb&Zl|6f(LTb(9wyS(`ljwiKAH+OMS}3Vb1w5V9|2CMru){^~?lpxE$x>$~S{7(!m^Nq4but90{CH6Imtp3"
    "-F>k($DKcj7yE!DK5*1N@AvAD{h(oRv>HUaK94~CJUe9XR|EK&7+-yI8(Y^E2kR+F`cm|8z?FwGK-?Jw7G)ious)=A0|sm#J"
    "CSY|4E#!E`UDsus-}Tp#aPxTo%ekAEPlLp>Z&yu)=sLR+9s0^_2bc^9IA^XB|!=Q&@_(eKq0pS2fgsvf>(hnFFTv$K8n#UGD"
    "8Ph60vx_WKm;(vX#2LRNG0QD4UBrP-KBL*;x8O6cC}OCiFVbZF88yLI6$Ta_Trhwy9XRJ{QRaXqf0s-_0;*|!J{Ab@R)N$#}"
    "eYx1MF4A}N-+v#Y3D_;8B_)T#AfK{P-C_A8T^bz3Fs$3lIf9v8jnk4Fqs)5`Z>+ei=ZKZ6C>=vtdDVR?OJrazoF;X?|u-Hin"
    "u*Un7UsT+&3JkXDiadGsm<Ab0WS)j^hVzI5@Z1?)l=>^+wkV|mK~yrk@Fs=z&_U`SS;&}}L0%wH;*NvWZ?i-PuRZ$1k?Xsgl"
    "i5F0W5)<#$X<BP$&*zd1B`#KB4%&!3@EY4R#t?%YxM#1Y*#=o9R&c-&Q97v9~@7=<n(V?zd7T7teGUtF-Z*=(7f9z`TzPVCN"
    "&iJ$0Jz}UZ#?1<bbqA<AP)`+kA*F#J+7ziOYorQwWGuVoDSHeA9lHgB{CZyhz;6^)0eZH|PPy?xayE+--~V^NbZT--W}vA{("
    "o>9nnatvpAy7!kqcvsR=D8UWB_4Z$ewW{Otx!6S(X^FIU-Jh8j(3ZviV3$FFPC$3^z)^hh|+a$O4qovv29EA*CQn=WH8K5e0"
    "XacSEWu2!9{_Q}jE+8W|u<FDfgiOyBvJIY~K?dnRS=$8S!2bwK)119unzEU<fG?m6uzK%`v*vJ@l(@c<i36fV#^|Xk_y$m~("
    "XMPVv#)o4Y5Ak#Fjc99fa6p$8x%B`#%A{G8YG1rkh0>w6ay0JFNqh@_bZ@6c{1_AU$>N3`&{P8GFdM2VKflf1PX{OHVz>QjA"
    "qPMJa}Q=>ZUH#;_nhfF>dpL51Uhp808haL2sc1E_0O7cM0>zEo(KB$$S?_G{Ub)GJvIXAuC>5k)xsQ5JX+@4D5fgn12Ga}Dq"
    "J`gE5K>^IDYhCtVNaZTQ<<@CQLDr$HyDc{(JIeyY-N<WS=b~{H_$X22g#|sZ0NJaDD@GMwHWb={S#mQ{O&f^X!i0YIgL3shO"
    "-vy^s@}V}L>7D`@8sLavgA1IB-cTjQ0=E>H3&qW5Ri@6sBYVhZ5btZsj@5IszgD4xvhToO)9R|9E30QUW%rg!Jj4ku3rBBUP"
    "&*zP$G|E-w;K8qL7tYCD#;!10JQ9e95FUC%ecj%<u)pqog=G>_fAFy71p<hGa!~O#TN(!YcC_VRLv)2*pBwiE5^M~(2=}O>)"
    "^a_zYIMZ!mbkdoe<gr6Gkk5{3HSVfQP3*CSflnJY#h|vE5`wZZH*+#6H*E~ct60A8Q+H^zZMmuYsi`azMMq9!?Qb?5aMCJnH"
    "YJaP$xn<hl9dF`IHKIMDS#upctX0k{pi4#EEUGWctuUhYIkzn@o-=GPW5pxaaLM*!_1!ZD>N$&vE_0{ri?<3+(jQY$yPvfdi"
    "u4w4|kpHk=dlPYn0Sm%r`OXOnVA$ew@)n4640CJd_TtM_SoI#;6zg#|m{gnL~vXE<^z!of)-#UR|Ddd)bPZeAK=ATWJ!+e@y"
    "Txb$Bvi9g6mMswza)%Cst{{U<?e+~;fB1FkM=hAd%*ce=OTft>6{$i{nhQ%U4DR_G(*qM0=zMUO@)R9`3#%QJvuEwA)qO(>H"
    "!%M$<TAWhs3oX+`Ab-**#r&-;Y`?7%d$7O_~ivso=vU!bps5_ACc1&eK>{F@Dmxw-O1GO?UueA<dhMHNLMo?Lq14p6}t<)0Q"
    "X(oE*3t~IFkeDwoMJYn*@???vWa!C3>NB)QmC)Hiq96eM0dRkv$ea4Kf%wz0eTA<kAiHsvi-O>XP1m!!l_#|TToE;Y_0-HIu"
    "e65Q<4H+;U$Q`H+7s%oIo(^Sj$*^R;6mcq(4Yyr<LL5<Y4{xO;em2-B|$_?pwP?$HaNLR;6<E7FzzfXp3I(78H~5%2<PO^#!"
    "Q!rYa*PBzO$mHFs%g9%g-WsQ(-@hAqdz{)BTxIWLGF~%2iZejj2@1I(mh1qEFjOsV0y)z`G#xJ&_)z$E7~dw}t`wk81?uQIW"
    "lZbnu=22?j_BLw`6L;u9A7Yaxmf;P$SKewXt=SKf~09YY3j#G5Xnx?T16@;##^>WT$wzwh8Vyc(=X?a4A_SH&z6J!BJ((-39"
    "~nsvgpMP7Zt3Qi_DF<hmm{H55=L%eAzrZG@5;d*w*`g1w;kIvbtq0o9`HI#hTWC5!$gPfQxHnP<yUtKD|1(87L3#1;N?LX#<"
    "uOpcHTSlh3V<v=I?0FqWb;zl>jSnqMZ>Nb##jk{zO{g-Hju<InTG0L+D4->|-~ILk|CKi`_1w1~H46!;`}8o+2VTkJpH#WlY"
    "h$}sTMT8v<TS=1vk^ZC{Ml}`67JH-*@oVF|E(m8E02P&b0!2kGu+vrwZ|_vv<3=a`_pUe7;D};j-)ogA+)sVK-pYx@?p4!cb"
    "mlKm(Tg_er22_w=eTTw_{2E0T`|Gjo9Gd!U@{*KF?R!qY8(xJaNkq;6J-;pX1JMosx)RoEUh0TGi$vX~9@w-A~!;tyCdtGeO"
    "LkG4tPxg}tFP)F#^`X;`cY53IuRy`Zeexe&1F-sD8G>3J$bDF68&_l~YNJ{OxyOP(JQnPXv8%=PsN_21j$*dmb#<6JkAg~JB"
    "E{mYJ*hQ;<%%(!V0#|*fYv63rvBVo>qVRJ(*Zve{f4~upPH41En8{Dj?9y;0TtcF~u*4fc34*XxP^9!l{*{$^%KD*NIZ$qX;"
    "p(fbJ<$m2bh7v8-9-q8Mj}{5+M%Hx#lxCG@TB_R_wdc|-1Vto=8#cz3leaEjXo`~EW1g6I-e#ku_v~Nc-Jg$xTioH`fY(||S"
    "=-P``dQ9$fX;CcGz-n;GSB~u>$`;Q3QRs^vCW)gY1tGLpX&ek4Kf1$wG7+?qCb!tnT4<c(sRJ&p8<yU;zm-#w#mU7JN)KhdP"
    "!EySmxwB-1M}x%)+LWjO~Rof7_;~_?k>ksBBapcMq_v>-Bz{9c36?+e=acrXvgR;L1iEus9fb1XF*W7fM$J6UGjRZbDX8<G!"
    "m@{%|!kPY_%^Q!?i8sF(q0fd@rf9b&d+7ja`h%C59GRRiO!iSgDlXqJ+4uqU#}T9IT*0hh^f4b)-sVc}LRl@Xo;mRcfy=l3b"
    "Am>-$`!wef*LeOZH8f6dEclvFz1Ek&-V_}ojB!eI&Jsm_tVWehH92x5*UAa%E>LQwtgvd$*jKV)pgtG?WW{WWBSVDzmxjxb$"
    "4+wr2g4;>AHgr$xn8Per!I=uI>#=PxZe|esCRZjlAFaX+49?Cb%Tw-T?OUP2amG9OYNXSK%5tsI0RJA_`1LI8=oS8xe|lMoQ"
    "46qoEEYra(vmEk_rc|8FL?%96t9v}`+!UTH-<CeJ~tv49*rH!v}5`rqsSvYW#Ks5t#<lW6;Me5#S!x0^;ob}6}}ZC`(?t6qo"
    "$Ku2adW%YU8HJEtI1Q6#xub4cn#}JzB<mU&?UQv!8VNb@1=tXSSh%#@j@4Gxf{42M*?6oU*2kE<>4n5W0wG8gyeStNc*6p^Y"
    "w!Z?Y(#_YcbIL)e+^UJOQ!V)zt8t242|r~yo+J4lJY_i0Q$oEGk!2u`#TM*Lm%7OlN!reEwNgzTv-#^aP<YX&2bbXf`(q64k"
    "HYLvtn%msD1ldTF=q18y;{d>(2GUQ?X7B`9in$w*Y$6Cus&+B!(O9yaNCma44*7XNTqJhEs)}F)>AbpXq1Mp7db03e5`v0H#"
    "iaH&L|5-h9=KFM5@rGMBIL!QBD8zH`Wp{Be_T1##l;l<GmIMgjQlu%?sfcr7YL;dV5#%ejj`%oh?qrI(s{)GxoSv(=5N&4f="
    "e+`(XQtk>a%ED<b(vP;$qM@+y|>VXLzu9$@yXCKu3jcc{>{i~r7}VB^?`o!uUwSS>i6Zu_T7^88xIERRxO{6godQKzqo~?L!"
    "ly64^@PytOpNu1dE4R8woWBel-PAnXAm#4nn1>dpqx~21}gvw$JjI?@dgE+TBEj#PPLi>f=3hQtfZ-lzWe~j*`~Lb7JYDyZt"
    "~ffvIz0GXI4a=)>tod)G&G5O4=VAUcA;xU)bZlkjI$7O7fKX0$!05J_7jFW#Z%ReR`zfeYV?9Xxl4R#d221%Z6?4=8Se|9^R"
    "WZtY9tmqcJ<9%hKxquU>On-<djWHy=7m!2VxB3+o=Agw9s#v_<G*$|P6QKfmOmZeE%p6m}w<+luGQAekt62@_$Sn0m>1-r%T"
    "+vTqZ;yKd<?W_r?Ri>2Oydf9Gm`=u>0H%<MrQ<pI8}3a{J$iv&#@)X^D?5DTh%S6KV*(}CH`%jMu}dB!GG7-w_Zgov)3Q+*O"
    "uVeJyGyxFUc`tBW+V4(PX>OOM;IpYG4do9QK9uD4EtFCNA0Ko<=}Kp_qj?R7F(Br$qP0HGfu7sa#OL_S`SZZXgnAsLv*PY^f"
    "!dZcj{#@k&65}dDxo3eOAQ+tQt&Xs`xUBcuwdH&6X{V%jcxcxs|{Ziujq$wbFCXmQU;R=jK9>dROtEWG_YUKg<#%(+>$NZH#"
    "c%^=xG?za9f+;5aU?>LMfpiOhHj$;`E-`J-k^HWbl>6kzHQ6f!iU62Q(u(1e-#t||5Evu!k<DHcA)#!U-#E+%5L7<(w}9q9E"
    "Cy$fq{_ijJuS(T;o+UI<AyEFfZ4(d^SkinOc66|J&7UHvl-sgjw;x_V#hxtEz(K{{7j_m8wY(^m6^(Gm5b7=(&^4=hB>v!qm"
    "HAmw;DD~~ci?@4$*GV27^7ePcLGl={KFUxzi*g3~aC4zsNHfH72|`5TdfUU?59j%sXXfTITzlT+(xu>OmRtp9o5v1~Jxz35B"
    "5Do=aF3^1!+2W25sTe0Gc3V(SyGJaZ-lU}WR18+#bOnhnB{3s>A2o9cEdXok${<A7^)JV21F0E3&v5|U`d;Vq4kbU9j&dN(-"
    "mmmT!t!1AD?XeYR6I0EWqW}m0!t@w}wPlEB^l%MzmBsrj(=E?EwyY^)9fHtpC%#cx|n_a$q-&O*_-Rjl~YL7DSv(m>^1#Q5="
    "l^#kStnpiO{c9YA8q3zEROO>!xK2HL|K8O_aN&U9O#;B!y33%T%Ggs@0_fn%Z44Zp-@kHkuNU(lt(;li3Zd+Sk#nqf$+vWvo"
    "aj^QMW!Bj!S);gE!O;>7(3-~Qby`!DvcmLZT_9A`E<MgcjFNO|;)fW?upBWW0AQ`!EfTh-U`eG;wrI$a}JR-duKE@UQw&24$"
    "ZY2-|UNFFX*MMkzBC;&(Ij{1Y(8cGN*oK{#vk9s901;&lkMk5`&wUL&uA$Qr+g9xg4a@YIGN>7vG=nEoxtplqczuB?_4#Jea"
    "oV%W2I<0~>y?{Es(@}<^c7QwLsZ&+r}iTqwJ8Vx?L0v$`1CnyKewXK>SCTPSWJ#xY(`&cHNIJ;uiax(7%{?(@8C0AQ^;7sT@"
    "n{gucZIMG0gQ!_E)6l_uTT4BtBi$?a%6x@nb48>rw)onwc;wHGy{Z0fg%nWT}Hdayg3b^HTyX#(>n*{J4mk)pc;i$7;+QoUY"
    "@cq^TbX?*$_EiI{2XBRm*z;mOL%KQlZ&)ShMLaN*o4uN{29Klbf(gZ+=4zY2>g?B0O!p{14X?v|8pP`bNYq`L-&2BidslI||"
    "0JEWyc8Ubk-8U|+g)c1XV|NrTC{$1BT*av&htmj^NuV+82#{S^(2BD0_f?vSW*OS70y<U+G5M$YPBu9!-8Vx@)`-XH+oo*Iu"
    "$DZ)nS=1sSUUMD8kE)^t>+q-4JF<%FyvneGm2VU1Qp#AE@~&8~$D=HVZQd(x7D&AElh<g*7S)UH{D3^lZ%Qt|8L?!LIQcDf{"
    "WY=Va+_{|N|JR*LNhPN#MFH3<V*qSCO65yGiHQ;3m6so+g9l)sJ}PsjAYh8_hgPAR_}VOUiRj6*zY037-DfhYhi;(F^UX_#^"
    "dc6M3axvOulY-O02bp7?K3U&fvAdM1!}9Iv6i5^H)m|#(iloi()jxdQC;A-5(sECU5k2=6Zq=RY4@#ecluHnK!?-EU3XAd|3"
    "z$!A{6aUK3&NTRan1uU@yOGD?e{B!o1I19su#40qab(X`W)0!m|ugpC%18k@7B1!*EdzyZEl+pY$I$TJB%+p3h3uSbzf;$h="
    "ftR^cB0Qh1K$&nZ+Lb?K`l61N$Xg!NmYA``1@LlU2Ph{x|4NAs2W~;nDo60W*nE;d*o2jFe9tj|DZMgN%kzp%{aaR5C)OL?="
    "&9IM@+1D@x27Ey*`Y5Mb5CRdL^bcU@|Bj4e@v-8>{f+};JNJ*;Hmr~S%EJVXTwibVipG-@)%AB8;CY(ndo!T%<*~~H(X1qX-"
    "q=q14kXEZpdrHJ&FUgRqa+X_S6AP8oL$H%Ec)bvgXZfrP{^mhRm)!2=Nke;whIskxk$1swOU=s%zO=`?(V)LtZuy~;us~e{E"
    "Y!}Q`*K4r3T@RF(0G6B-&tZzK=GA%06OpzKmiVknkFpWDR?<)a*9G+b}b_{awqyJ-6FLm)+B2ojwD5>&L!%Or*E>$muG!D}S"
    "^}cTBP6K(qFUD9Yg8{KvHi-F{`QFa$2!n<XvopG@Fx2IC%-@%rr-p<%~#u?(|%l)R$^0aip&zgw)rg~FaUo;Z9)DiNgLNRL<"
    "hTqnf+vPh^U=d}H6T(Oq_!RmdxLey)Pk6Ie5%3MdF1NX0fc8{2EQhpWg=YE>oZ|OTfk~SKAb@g%fBW@+xmIw$k<owkA4MY2#"
    "bmoRhcfziGG)I{N*FvgvPBOx8XkgNM6DFs!Yk#0?H#&95!M66VN$1rrb+dC+DY0*^<iSE4p+h?2ool_{hMp1w$=@zaGRWX49"
    "cv2)F_R8Rd7^HvL-|ozje+2Fm}m_bmsOE`r}s}h6MkQW>{HR#0T3EI-s}=Dmr?{`Dl47YDZ1lsG+HG>o}sCPc@seu%aQubh|"
    "FYt?(;xM4atNTDhhjo88weFS$(kA%T3^(yHn9@43pbIj06f=M_}opBhTNd3RwS2jEr|h5h3!_7T4fp6fLZ~6tt!BO9!DJnTc"
    "~LHyNiS4(vloqoh0vtTTDcb6J|zo@Rc$KfY*xM5q_nLP&B1Js|+-bB8S4U${@9l`zH)4EJtyz4fIUG_LJI&wC?J02quMpL{9"
    "m>oin^=DQRBm7Iq=7i3&-anBHpN@1ImCx-*FZg|pP>yE>dYI{zJ4#OhOcS>pu$U%|J8N8wwUsg)<&WhD(L+Ic!8bkyvaT>-F"
    "k&qly_ZsNq9-WZj`N-J8ne~Gmmv{$58?DpEZY$W!$85AFF&!_%=1o)A&DrGfc*x0lW|M{%fAN@69S(Efo%A|Pw`kOZ<Vs0Ns"
    "HE_DtzKH|*6{qvah8?DdVs&!)RC9GU;z^4M2pP44Pyt5ul}~yHO4o}%Cf+X?<E}{xD4YBEe1eF<4w^EXRXLmTiM^p8*<W+ez"
    "ka{`e^O%b-ETm@mqf;;78N_fvW4EJyo|k0Tw<|A(VG0@2%NdgJJF_f>ib4xs2i?qK${3Rs#EX<*AoiZFu+U6zKKSk%1UpFFa"
    "7ocY%tjX!x)8ETtUDGB-nmX8=x?V@b$kB(GY#Qyi2psJ!G-ulhjNSu9LiB;`|Exs=DYzk1ql4G)Cp;~kmgg}En%soBZ1cslL"
    "58@r;D-Z9W%{HcXBLZ;hRqR_XK>9%5I<eF40wbYQcqon=5MVUr()GQ>0E@kwkZ3l}r+au)`L2w)IjeDi{NTpjG-$3sF9a4|-"
    "7q3VBR}>Uv#PTboyr!TaOAebT>dJXj(}Lf#&`na6m8Fp=wt`K4qd+w2#{G*x(izd(MU6@O(|0Wv5#iz=$PxQAd&9*o0GRV2-"
    "g3vbJb#Wa)rQXs##;2_h0^GcfKt!JwKglrmh_YU1rJdZ*YI~2J~C9)*C#fX-#G?ZOT{EniBSgQkWCDIKBpqt00m#AbQ6X~qZ"
    "G^|vwgN`qd_z>W^@v3j8j@dfgi|!NftAzFXk3Qe~=KHlTNk?sf+RAh|k`UCV6*%6Ms;nyj>8E)_|MOaf@1Ma_@>HhxQ$A9!y"
    "GxbC+LNhN(u2Id{X7DM?YsQs=mq@NPS=R&^yt*)~lF%K$yD4J8BJ<3gP-Z)zacmM7V%Pf9Fwpfo(tw<jhi^it(EGq~4aZHCS"
    "*>Es#fZ_DV{f5Nq=%psQzHbK~w%~z)e8U^t!w<(tiL^moYlNL8ZqhIa}#~j5TILY$F?)2z$p0-Z>dx$imtmwHq&)G-C!$H)M"
    "4HQm|9OvtwzOzpasD7FnELi_iZn7P>KV2Z}@UGacK4}0~ux7x&%sirDTa&~N<NH&FilCxCryWyqPuuqA5vmuDvvd7r6qt(1)"
    "2eB1nLYGLAZ6a32^alKi8m{Iy@E~zrf9J?^d9o~-)%6W$#`4OrEnGY8gyDN?F>D;VsPWOke1A&{SO1MPR*l(Lb$d1!<B8HRq"
    "#js=<1IixvZLFixo$4O^Z+Xqt+>~_)z)ncx*^nihqsRC6n+wpO8>}r(ZuFt&+un%cf#VkJq$5T0F<yI{tOUQndd#A~QG`SD}"
    ")N7V3cljazqff9}REM{@g~{j;^RgtBZ8YvPA+OngHB-B6Os676x^y9a@N%om%VSrPgAK_pzirmv29_OHRMr$2<Y0?n7@wowa"
    "#hcYM2qzn^ZVz1FH`3F_D2|@aunojI-R=Uba)9at!U@=Uz#<lozQa@M`p%2=2w(&S0MyV?S>Igz=>Bn9??e<eOKe0O)&hV7@"
    "BAgn0Z<@<{J(X(vY@(TZtQ900IarpWdeD+`5B=RVJC>uqEJbTjW;BW&XTb&fuu2RF#O)PcjufGO>5rzWN0zYP>x&{br?}y1u"
    "_7qPfl&7Xs{=<1`>V!VyJ^hO@XR;Odx{r>1vxuEpI8yBn7~q|#+W`QlKj@ITz~h2{^y2=6eJ}d_Y`Gi9=BzqFF0^^#0K4!hc"
    "P%z-%yWW_jz2h#I=uTh_$i5^fWoNa)HXQ;V86sOh1o}8#F<KI-gg@AtjsDnKS)8g|1#$nHlk&JHK)%xh=Q-mkNRz660KD?u7"
    "|ph!H$Vam=(IcVAibUyibhxAIr=&>J3&qr>;$5=WwV5ZfS03v~RnH_3=RFG%ZOep>3om+(ly)o^|s3OKpBoV^JlKg9UsUd+j"
    "WjfP7Vj`z;8+ik>2)MPS4JetLH=~OUoi+jZ8`XrtdEmq!_E!#r;bZD4nKyjbMI4fsYX2Bws8dx+SbIn!5@UfzJC)jB0pN&xe"
    "$5!V0vu}k-P7enJ2^!Gk#inmCR@y;VM`Z3lpX3cTHc$iI2rl|GNnBpJk1NiMqv#zvQH6hLDcFnSgNW{%$DxIMMWxqChBWOR+"
    "7k?bUZ1qaX!1(kw>o;gT(Zg9!XmaHMRgkcV$sUmAr|`(T24I(SN;I3VCqWRBVoscg0rt|T@dC{Gf(k#8fzKu153`|N+)rP)W"
    "^Ru;&UcZVyLHQg`BRFe_%2x%Is7Em^50UPp?L9<PMB<pcpieB;R0<B*qnR<;qPo&|o1cv?GMGlA~!81!NsTuD5}H0e3E}5N$"
    "aXJvIxh;^VB>Z^q7GSpRplg2c{fdDe5pA&hZ|vjF53zac5Ykh|VURfg2cFN{e%m6>QarP#GEy{kx@jkra)b%TQ>dTV|A9`nL"
    "@KQFQCc(G4_7WJFaAs^UeO~!X-046H9-A|ZK|2j2H(<`YSFm?6W_p1ICb>f&lokS!;k|e0Q>E-92A&t|`3{T{#59Trjh|(h<"
    "y0o`N8rPqx#|Pej81{?|uEzbf_94s;;F}$Snr1`B)9gvT_L<{X19EmDt|i7BABwl7G|7UOdRUQAkrNLLKbuV)v9D9;yboyHH"
    "R2c+srZkt|0?!B^Pe)_Ti4s9FTPu9%Kz{!uX=qs`+R81$5+|%r194OO-B*ZX+pG4Gsv$QG$}y-I^?^d->S1~|J_o}Koagm&H"
    "|U9_uYg8qm=p#Ul!m3?{YbVydUgoWa*Pos4=1}>N%@cco49Y_8`TP-t7OQ*_=&VpBAlGb6i(g^c6vu^2l^p@6q|FdMK|HJlB"
    ";*pQW%CD2OVK`MA@Yc<VAO4LJR3Z+Y+LZ4b{wiIE4mWOU%&49H{M#nI^TC-EN9av+SorOnbNaf&JGkci!X#N8<XlGj(+oR%T"
    "RWO^a}o?o)g|3vXj`j;|_WX#|*{Jjx;-!f-4S{V7p&w?7Gt(t&swcJh&fH%QabKG0#hcW7fxER*fdI3BC-g5qcBH{V0UJUqM"
    "dQ{IRB(js|UWV{X2@v8lv}Z6Q5Hl~ueMyHo$GhdvP_7M&kkari#{)?d9+<xGDl<U{mF#`xg&F+sJCCi7-WJdaoHseoheaHTg"
    "<2}fv$qM4M6ERGix8Um&t}v+1cGPR`7v+U;1N6IwxlX)wGj#Sc&98MO{(6@XH9Y`er?!WCn98}UE#I)n@m{fZ(Djk>fhv$jL"
    "M?nA7tX9&2i6NetKUH$Vg<$c19RH)DwLQ5Tvvv-HuO~ykNWgZ(6L;;dgtkL)=T^(E@F<25Yk{K6ki3917xojR_?|NZGAiCS>"
    "SXl3#pLy2^}F(IB=#%9lh@F*?D#4;u`A6j%(&d@x6czS5uMiF0QJfZrFdJ<IPV#V~8KXiy;<>mldw=|uL9*wnM?4SJUF`Zo1"
    "CWfT%hOgfpxgu;L^wny7sS&8cpube242Ci}f8<1q|AnET2Rmn3AIi<jX0)Hb8R^NXp{?X6%by2Q_<gF5BN73tkqs$uE?;%FN"
    "aq^9b<1F6gy93}G1KLk870a{tpWNKesh;+uh~2)oEfr|6(4A$BBw*9pX?lo^%~HoaL_ta*waE8M@8GHV>gOVg5g~ZN?+UgC2"
    "n2&Rqh0UoIeQ_T26l*Mbg@>lNM}F4q2`1l<};<fMhyx&n7r#JcK?%B2Y-vNLQb}GblLzgMtOzwV6N`*{(s}<`2LeGDh!XlWW"
    "D@QEjzV6aNjr0C3f8vlIC;hB@({9{d&S{@qC>gWrj*h%*_q0*43e}S{g0WkJ7^oq5BYJ4}ZIlregi7!i_Qr@8tVT15ER6WN0"
    "a}1{>i@>091<RtqSq7~7nKLH&;mEP99vW}6C`=z6x-XGs(K{*X_k_+NKO36AmZ%{QM=QJ)G4?o0F|Q3j8+56C7K2HXCEszUJ"
    "e()#ZQYFNZ|CQLYIYmtS=NTVd}R|F3dUk$}tRCjT1tr$V-=0TKcJ~+J+^C(ju7B7fjPeo%RU`m)6B7nw_P&J>x1OTuYidcB#"
    "7WwR@Iu&X^^KnmnD`B)bf0DAmHl)+%=_;Yg519rRl+}i-Z1D-vBvZMNm}kYF@w<UU;)&a7Hqsx&22#VR?fz<7duO5nd*%S6v"
    "!Q~L+QI0fe|XVI{7v8GB~N5@#P&d{;Uh4!Z-d9_zMs<fF0r3on<<IosWA=ozK`|>zzDcT!OKSm2|DqGcN;q2N51|TBHD^XpB"
    "4+FBBZIt76C}NVc}r3*d=8CEq<6jv2Bh2gCgEzgm8!!ppJcO!7WB`bZq%E6>mC?D44C8CFOB+xSKKpz=8|XG6UFNBv!t7X=X"
    "Rw+?`0mF<AY^X`mDj$t@CnUZ{}S?$<Dy@5sr0!*8N_Jc7-sf40D<{U0VgFahA08)N}J-gd_IK?(3;v1S!ahTt7M8vLrQ^~H$"
    "2*W+b?OM#YW7DiCm7=UT?mpSCs6;=fnWXJuw7-ZjZYuUOh(^GZ#7Ev+kU+MN=4mE+5-(;P@fq5@R;lyIIU3`onif)+!iNGDc"
    "-a-|CCVYIJLkZR*nr3tKp!r6DU}*~gV_`M>+PstE%axHx8BB->MZ@fR<9Dh450nh+h<|M%EIy>=-~-TSKCNZ6EoIR>c~?{VM"
    "m>xM1BGC70-T7`0T6o?V$$1lc7#oaGB}MU4N%b^sTkx+b{SYnX^{q>xuluv2}O7vmO&Vv^OnYyjKtZgSLn7gOdrAH+5X>D#s"
    "MADfBQU^8KnJ|pZRbQQCShp$j%fCY6um08F#KzDhMbxSq)F#p}&kuMoxC%)&)RVC-N>)<rt8P8HFXITVJJ9p$^ES!B{cLhfo"
    "_(dI9oe|Kf$V_kSGF(vCzPuqpB+hSO5^nV1OgEnPZ$FEOHbtjIENym=Dd^h>4)nyPMEl;^PbN*{ug_-Nh|z5P(75!&kuaCke"
    "9)E|D1c=1~=jw3tX{Q3mk@cctnbq<J5@>c<|p#S1Dz_auI1Of7;cAZ3-G1LH~!baSQFRC*o8ciMJB8updTluk1Zsw)iD75aj"
    "WDhxs3ZZ1mI+C{7>OBEArYWLd`!kOjf(=!eNiz?&{f~btmHR*O13wvJp!BMXw)Fl<3bOSyVwkTt<z~3wN}CNmr+Wa9Yo8r65"
    "yl7rmi+{%9LU@~I%?B=LHALKs2w;(Y6!O{IB`DTwmTm0G#5kon+3NuxP~wOu_Nus|NR9G5~zW?x9IV<H*+0fQ%R~7MEGeS9="
    "$b+8zq4CDSgnphyc%GjM(DAvG64W*0stWF@V67Sg#$Y>yY8>=Ou4DfC4d&6By3%#P`>g!2SPXbyQ|S5<R>nuqFTN>)7_&wix"
    "pFnbb7L!frKE`OKdrB9W0101{T+xW@POz{DriVu(5dQZY+D1!CzdKV-isbZb3w!H*odQkw9;^I`^g7O?--CM0%I$!NvKaNw%"
    ">_sNFWeic|JHW*Q_NDfOLpIf_f2>`n&QvD&U()n1}ERkp=ygY!k^KpT7FS2OWQ0mhFLRhgA5B{8g<zEN}R1p8?K_xZ*IH;Ce"
    "=|yPnG|two5|KfD(R*Y(;t2PMGRTV|0iPkRU^8BP(EGv{Y?Lg;3!4zJK?_=LlWRsNr;Crvs1`{wI8TTj@c$q%@IM5cNZ;7-P"
    "Z~=-03c1`+*=kRQJwGU6`mtdz9c`fx&jP;acdwa{m7H(fY^?Jlx-1%klwMghNHxJi3jk$3ko?GWPNJ+@kMC8>|gyo!C>*<NM"
    "d0oUO(k#xuXl1B8;LTGft`}vzU{#?7y9$DeWl+XmF3c;$bprEvBe<I)tAGqKdKO^pp@j&Y_>s?EyeYXgI2O?|J{(F8aUOl><"
    "C{*>awI0f497Ewx?aRUR^R8IpGfG<_QpFH`5aN6@5l0bCVGPJC`~=Iza5FHoAw^}e9MFN?MQmX_`?+D7<PR=6c+3gADg!u+4"
    "A=0xAf*+Oj$dlhlc`lLMRFE5ahtx^}&yID@DZEy7%5h%B1Gf+9^qV}iB++%FSql~^l<fafP06d6WduOu$wW#>s|Khog^|6p("
    "R(@hoJUq}Xe^Nmr1=$LnBnAxyfX#;JfJm1?c3&IaN~pLNH+mWJnjNXCf>cxvAu;ZHeBzn1tS0+R`)|G@`Aza)9JA@LL?mtje"
    "g_aPo8#jxW^Jjsen53Tlf`>0i@pfPD<mmBtQdOKIW?LO!xw|0>%6z-B=4OzI>0smaUt3Nx{%r{vegxvMR;^n;Pj?J^tK9KE@"
    "iYO$)&B*aS!ViA_E70_dY@{E`4sl1#f6hcX(N&Ar{iXE5m<XWs=gN{}bor@KoUMJS=u{s$sYdg_%ffhAoZV^myt5KxG+Xs#u"
    "D|K_b6<WVJj;Fwlb29p?h@Vd7ga>;GpR?*D~J`1=UCprDLJ^yz>qvxUKHzud&IbL4G6TC4#bx+s<GYrBHw>^}VPoMo($iRb8"
    "{p=IdQ-yaZo@gKGQCMZ&FRbU1^uUz0MaQxj&_+a>UacLlyl;jGN#ZTg6zf5HbWmj{oITmGF=Cl3O9|Mh^`i}_z^?hNKLxeak"
    "05{fcf1V_9>~Fp6c&z?AQwD8TlKN0D@hI{m2&C3|_9jmW-9^j|^j|oO{s*Tf6cA+XhASvwMAE?dtu$*U>22>6Ax#iwtf6N;q"
    "sz9LJys+MkE?q}#+kL<KaubMn`5&JDNy5pfZ+8u;(=0h1HqtSMX}Ey!zB<>Zf{7}rI;byeI(S~!WY;0KLjA^|K8&;=QqDjLd"
    "?ITnO?zR{@h=FY-MoI(#&5V1n$KFs7(wN{&a%b{|o&8vSgMWAq||2wZZxOgO$2$^zyohd8gkZ;V&PlYQXYo-oMED;^aThRmS"
    "6)tV)Nr^?tX$rcWW@!ivJfMC`R6Ne4pQrB3L-N3s5!2(>eU`ubR~PLLrxHQd&9FG*Y+28(h!Y)*P~mw4BsNB+T#-Y=mkYV}u"
    ";(p!?3);qDVTvGSJ9L^skuQ@wcSj(^TLT5G(#ijm9sz#FiBmJM$Hb%~tH*KveG4w9XkW@ZAmVfGw%6tt8&-u3|_Z0-`i_lz3"
    "*}7whSg7UyE!K|CKF=S={{MgZ+MyXUBT9g%|KCIZ-}V3Ma(rpsj%&f>`O`KXed=oKu{#Kz)`A38WiIvnNPhfK{$Tvj){ux|_"
    ";X$!@Yb-~e7LVtw@QvTQ;vfuWhrH3|H{F|C2gr0@8;%a#O|w`>0No?!saITT}v<w`o4>q*vzlM>5W&={NjP1qN3twr4k#_qC"
    "E`nlS=2AyKfRTvP(q;1=45Xlj-o_hrRR<-Ca4p8~$OF%v6cvA7u6wr|nmpHCYG}j3n1^56LQe4n@1D=ae_qoU2^x7BeUAG&K"
    "SjLX4>;=Nlmn$HT;MiJ;)4M@VZ?!l#utO(+2~O=Ei=%Wa<aKUzL54UB==QJR<?^*K2?>)L#w0xAr6il)9W=<&JcX7p-?%qe$"
    "}<juK`Xo<V}rkX1*^h)vBnevE!+sFLO?|Ldg6uS<8;jE~ZR@yrGC_EaMTEWzmk}BlsqS7^l*wpK@6FvWiPWv5{k5NqG<)IfD"
    "5)#rJJlis1;!r_B!A7*${zZIjfH6+uRHlkTLgsZ`NrQ!h!&{f4+%9!V82{!HY5!qa9@l~YyK?^!ZSA@HJI$TEfbOdE1rbea`"
    "}rqnbM<%uDDO?}(7Do7Jd1;<W5;(Z&F-qDTGNi!^*?DeJMgS+rf45)E8BB2vtfUzQzDJSkgm4t*2w*Lro9KbWoasVU1#zt1s"
    "`L!`w%H}P0f$pwgHvBS!HfQp$$L!O`#g>6k5lJ%e^2~N36wP*>XhOW*q&C!6mx%&g*CE9r5y?h(^`E+D}n+6Epkwzj^b9MIh"
    "5=L2E_d_7zhhNB$V5?0cC}I{EQ=iP8ZwdE7knXXw&SPvFIOVr6ywOFJ6XS`p?(jbs!V=ITS>&4RwU=M%%Usn1W_`>E$A^@sJ"
    "nbaSp;|KFrVY2s1`8=t>NRrAcF9t0;xas`R^8~GRs#ce1!<Y|%x0L4v_>VjoC^{L4AI6z);P>C1o{lzVt<vaSDiiQOXB9_NB"
    "!PQ@cTqQ~$gJCyIpK^1loYq<!>{gW-%Uw-^F20kHlhfmp@(T)f+ff2frq8{XFRNIVf(vgeT#HuJ?{g2+XaklwW!i_M&uDdOV"
    "c;tr?MH^GB$f}!D?N=$;46T}Dc{l4LCFxamSAL!+Vx3w>HhD)jVrE;8du=3M&2K-h{Cg{XX@S;xP3!2YOSI8@NBI{mG`vE{9"
    "RjJJhH~PWvuN>BUIsr^X9JEc{Pru1lnjj4w=h?r=B~<PwXtfB=p|0EDo!~NY%Kr5<AWMHxMlo`^p<kI57jIDuFBs`@(7%2)7"
    "26*nR*J^q@U<^H=AAn~%jE#BCqt+fLciolT`M)d$h>qz?Gd3;2H)`r_FTbDK@v)gmsLc*bk=KTJ<2<%jB_hwPThyIgMf35h+"
    ">9dyqK?kXwY#h)Q?7WIq@TzxWsqLa9YRVUFtjcT>~L1sObD{ggr^7B$`UM_1T8bd$dT6dqsr$ZMJ$rMvW(kOj0cCqY(wquLH"
    "=1@0uq3+`*Y<&~F|88GpUuh|3GG{W=#EHFag|#rE#bXQ!X4=NBc;oC1yMd+S&;Gf&gF$2^f}W1<1|G36oh|3@=9yAg^TPVg7"
    "i)|aT}J)(!1|D`b0D_|GqH(Vs8{-WH!$!=3%z`SMpEs1v6J?;+{bbse4jSlB6f@Z)e3h>$5oHN)Wk^bRD3K)M?7WzLbW*PMT"
    "@#=X#P3(Sl73;hG;^-UaIC1*)+VO=c(@brUw$q9n@#g70~1df7q|8bry$Rr&!$_E!eKR-(2~cK9`>t)e^=J6VwXg5A7J)+1S"
    "XDc^za*k9j+OfnLetrf53r;}&QtIRu<(^f);=@uw!eNf{c+L=^8a3pgxUT1)RZYgc9q<?g!HGI9S-___8bKs1JooDiJbvq#X"
    "ledG00#=KTCu<*8y+J4@5dq>APV}(1iDe2O}&yQqE{EkB6@#mD)Z~|qWFe$H^_}!Z4T5}aa_iN^)Ro5QVr(eW9NlV|#$`m!?"
    "h*b>=kx>Nv(}kpuLEG=bvYcka<<L1wZgxK|h@e*z!Eel;b%P+`)Tv8ZsGNjowM@C~cr;4)TB|cajecJ2FfVGZ_5->KTA(=Du"
    "bp^q;C3YO?m6tlUJ}1$Gq{5y?wvtVEP76n%g;}ZyN5)wBHWBDl~+Z!&k)>aP-4i_&ZVzQ>o)4e2z}zbiKwXC7AQm1mkSDo7H"
    "fq=KWib%8GabR^;i!hZjNBvX6VGFQ+hd@UZtN3Dhn~645)%Ha&~S98jt=mKf4>)mvYWaO=TlSKQ+D~g_<=HwwJE2ug|NQS>G"
    "5nSVhJ(Ml8_%iHE;aY1C<sJRQU8wAB!bLh6iXy}ia;@o2`HIJ<yyO+S=Q)nC~ba0ww`wJ-xSB}R4ip6hQ|gRnFaJ?4cg1<P*"
    "lCVjiL*>W7{-~-g~ddHQ8U*F4O*E{aW62)(0uJa2e3fL`TA+Xr*VOMOv@rRjpE5;%@f~hF}15wzzo*QKtx%=o^L(>LtVG69%"
    "{Yqw$m)FHN3u0=d1P&^D!Y1B$xAi)05#2X6uG`gLCzC_8Me`rTZ`9X&iE}r#MPs!9M^l?DwzY7qx?-B*TSBwap;tGi!aHFup"
    "coMen9z-X)Jn@`p-$fWhmEeli-trXmgMupRDAvZTB+(6zllm-Gf`2?1aihF{LROWyP=dG4Kz(X{;sbt`2ppVB|Y=9Q6{SIfd"
    "OTE{E+F0t?2?;4>XP^{oj9_>ioV*FYGl;6|uANNIzf(m>(@rQ&k<jd%L>2DtbmG|Cpnc3Q_Oe<8-A}2VK}$v%M$JVQ!Ly^%Y"
    "N}d95TMlV+tR3F@1YufXfzM|BY6o*U!KUkim0b+L;<{2dJP^_<)dFoY_2qykRd3^_W$_rICN53ZD`O{>zsf2`jkvSrkWU<S1"
    "J);+7~%+8d1ej*F(-&ahb2+)tE1rvgxh@A8e!tuJEzbE?AIE@cn8{Bt>E>bl5pTBHemu4lt3VOO2-V;FYn2oM;HF&LkSQ6v-"
    ">7$3U46`F8V|m1R*GkKVUcZb`Q%OCjHjnz%LfW;h=6+=!J!M{ZS2t%@>Xv%m=+4KLji-mJz2E~09sFVoh7nnHR-uEZLNk7~s"
    "*7@yKn+-WM99L@i*@qoOp#Pt5ESLdz(J<r;ZJF9aGd_l>xHuG=^7SBT0Y=G|8siJldZJa?XtB&yH|x15<hX7gbK#F(xSi2x+"
    "m;sbz+^Sb)5ui6)>V@X1@&jl}RZ|<J@sVv##FPA+=DNmFK|seQtR&Le;JEQaBU=rka<|ZLX%knnnF7G5ES@2bX~eUWHHPuf{"
    "{bt$I%VFrtWshv%)V=+~&@(mO3GhR$_eE5hylHlY0Ar~D}9mR#Pj%GPH^s#jh$so&FUg<&-W2uiYK!EVR+0y60HN-65AUC*#"
    "{YTx0+k42I{5771DPgBo9Yeveaa;hRa-H3D?CY4uuOHpRuB&3l#wHP{2on6VFe+YGMV+$-zj)=!k#uL2RO;FpfArNHijEcz`"
    "0e{JeTvcI2F*A5G8_B|$4GshxFNQ+SkB{Xj!?{56lr7M82r@%w$c<Z>k2)f;siJ`33@?~kHZOmAU$;u{-6zsW*^14c^X^A1a"
    "0-F|25aiU3TsJpVYXWx<}$P$3S=&<zQt!n>ksS9qQJYRyxDf^z-aji@gok7B-GQ?n`GHbfp*o?N#*zoqZqexRyHf9xM+3G-d"
    "+ny@0bb{NOB*nRN1Q-0BHI@O3Jswk_uI)zDku}*_RS!ePZ2C{B6G7z`s^^bD_I#EaOkhW!kP2{92Qd?)R?e?N57ZfqK~H^J7"
    "Tl&YNGj@Gab3K8<z08x{R2S)dc9@u@dT*@grg>(;=|>v;NWt&r%J8QWM7&y4!$e0V21J5K+jJ}O^HTuFMs89v*SP9$HIn-+#"
    "4w4b<JYCD9EEtan3@CZZ*U?veaTzQ6XK9loHes#ugqcFUD7gPMsJGWHr@;tU$X8xgkfVHLpnk&MD-uewE5JArKhrm+Y@KaS^"
    "CRH;Vy2<i7zZ0y?mH}%n+#K73AJTO_tL(QGingm-Xb_}=6fm*%Cs<qWY)4b4okpapDNXBgtwIOoB+Uit*`>8vg;T$WQN8h9_"
    "g=bpg<q!kRFiT8z?s22L-9LlWbKK&d-)yv@@;E}&eG>8P>-7=+&b!#1?GO4j1|E#_WW!V8V>&QQ*UW{j-<md+4+m(eL|wM)L"
    "&X{KH7m=i;4mjnq%)^2D%=qMz^83L7=qQsi5C{JEF{yKmSySrrIf>RhJG`s`Jff*ycF-yQR=-&{05T;LGlfb~@G|*PB2JZ`U"
    "G%LCb!OE)NXJt{;c1saIN>n^n#?v3A1hgr+|!&$z)We!?hW-R5MgIxZ=blWJ{GatzZV1^0b7B5qqRRZ^Ia3E+z36Bp?`Dt?G"
    "=K!jmYUWCL(47~Z412J!X(~@%AQX<C?Hv1GUP~}uW2o8InPE3y0*k>U$PW?Td)s>ZdJvF|7#*W%rE@_vOquk0s#W7cJ$@gts"
    "YsWx6;(Tz4NeIq?GyT}H(k7E*_5wOPu6JU%(rU%N{BpSFrkXxU`HtRj?PN4uPYD6`q^sqq<dZqRH@Gix*LFdvDSTz@(pFNM`"
    "^-nE2gsIt%d^_zns@S|m{X^A5!pLwRK-H)0F?Ezl7V8^<*j?vN2BJ-94w!+HC8W7?d2{uM}HC{g>VVOtoea2wa<*{CRXLkb}"
    "D>hHPA(4SAlZX3h1EMi6-d@GhKB|VKjy9mO^}in9WFzI%5dKF*Ym0d~qOe?KkjBG#u!+u7s$i^Z4a}q;RojH-LmuL+$rnKjJ"
    "T&h-oDj+f_wLsAkqZhSKD_@jSm@=tXH`sI0!~GJ7_$?ah`#KRixlnH?pefhAMmat4cIrF@UoqfJH1Il0x`7lo6eM+TLl9<cg"
    "ZsOFt1kXR5|4ro`JIJy>HU&yZX6B;mV@cZ7d&7)*m{5`tX$g~N!i6!$#$X8x5v#2HUw1!8675%mc<M|+lYMWe#xQ_v-Dn4cf"
    "9t=;Tc~7wupGwmt@3+E-IyP>&s76Xj|KMozCyCIayad~tzTZfdr&n^A7G-j-`WB~zU(rl2eSR@aou1<$vNm0n8Hq`(q#D?Uo"
    "@PbYmk^<#wJ}|sNA*GyI+HlGgl=3}inOPv8g!(cmpm*-1(;X3&hV8lK`<v~(G4u}ghQew<BVimGFXX~OS<%HpDQJ!YDyi~%h"
    "4R#f-7TI^chQfZCG1?25-w5I@1F!^xILPcVGgXJ&jT2g<xvnwPw&=$0k@(Lpig~Jm^ARRv%Skb*6?2pVfpdo^SgumH<U$@67"
    "$4DoQx_(a@z(_~%WLM0$td_MWD-pFmuX$llP35{8Jpj`@6-$QUb9Muj3Z`}q2%$5ldk;4lX0Fw|tG#buq%b>k0vp&HZUKF8f"
    "7%RB*A@Gq*B=Be3H<V>8a^K%QQJw$iAywPbhVKKPRzP<rJ$tsX;-hKZew8<d^|5Gzrn|O>eie;$MR|7H-;m1Aj4`NYo4Rv*8"
    "YGU(mUWo5Bf3z$+_u>ZeO}+^i#Rsq@mi_w1H0u)ejKe*rj5h0g?l&yDi;?;uS$Q(*<u**|JMyST`dFd*xj&3!T_;MbEcv@y$"
    "Wr<o(pG}#nN&@|S_FEfa$TwmTV@(pr!HP6Q-IX*SaNx>t7DGRs+t}WwZx**W9>D$ri|5maA8EEbxwJ?7}Gb(n|DXbzMDXyNU"
    "QlZgAyyB=Udn3TLD@_&9vnDNd2-|Z)|om0!?SW&Kk8g!NQiG<<9;1qp=wi$Ubzm4!k|D;3m#t5E}vjbXP1$ZI1wDJBWdUM-6"
    "w6fOk7ktJajN4i79WoWw5Dl_CXgsspM@R2@9budJ|bGN*hfnr#)#v=1zSDf}2NynQ8*dvFHDM?W4e1aOssxP;OR?0b}QYh+r"
    "3AI8nK68PJSnm#O%=`7f2q4j3F86ddfX^wJj+;wjX=>!RQqY~=Z8nccU;CYv~(i0ZRa+kba?g{C6%K7m{=t>&}00z=ab5{;#"
    "2GlVWACBwN5kMcQpD(C~momp1L+~$B@}35#@e#GY6!<8_8jNYabC@<)y3qV^Fh;6{IxSqTmB98udm~FX#%4B2r>{mLsb^U{i"
    ">$TjTC&M*Z;Nr>vc^E`*yS<o**P6tF0K`#^KMV)1%4!Qe$<;kjAZX|sryzSe3Dj7I=edG{7|Ha3ZWpG5m=~Sa%zr?Z+Oo<=g"
    "UOTqK{-5sid=s9U}Spr5ne1W=bMiN}}(CJ&KgK`&rxmM>OgnNV(G;o0rxPT((zwPf=IL2P%uJtVbQAMrX_-Lpzpq18;>(ND3"
    "-5UhN7f5^6b^!M}3{e`fO<rSy0=cNk6x(9XAHfbTy)<u!&U0c0paOi2MmmmcMQE&&x90I)^4gm#&h?dKRwuGX#8FO&zlxU#a"
    "cGXC$TEwtZl#X>2}6cdS`J9-{P+kP2uLKiDLhV)In!D6L#e+V}!y77GTHOZaFVhPK2UoI-7g3Hsdknd4T&?roXJ{2$FtZK|5"
    "L=0C)zHK(-2<AsU=(rx6aPG%csJV|<0*P69Zh#Y+y6O&_z*J!=myXlji?ybr-LiXR1~n&ZZJtk8>~)>Ixo9+Ob0Lf$MjKuV9"
    "AZ2V*{r=DH!K>btXi?-4TIXOShT@Zii2W|T2{tODL>>@%ya$WI(A3sEtbF_+&gWczfS))BslZ%4|g+5nsUoxPwuV5bD3=%oe"
    "UgXpYkxHO*tG-$zf0R99>Ge>&|Tm<mGw>54kC2Ra8>4mI#~LXXyv;kZ)!{o-$IDy(Qn-1Jca`8cqn!VU898T1}!i6Ww5u^vb"
    "%5R1`<V8YbyVt}?cki&<rE-7^1OhC(swayxN!GB#AR1s>)x!!9PM8W`4gH7PorzV10CuIn407j!v#VO`iPL$o-`)K*n|ufb?"
    "au#j{QF?jf6?DiVeg}3=^h~;Rra;fa0rI-g`s)Lj!P}*E=^w+}Znup=WXOEOA4<MaMWd3Y;H$^3p;0=8k6fa)i5vvo@k2%Vy"
    "aRw=frmAcYF8LY^gI?@BPS{I$>LjZIXN5BH>cD5l^MM5TstoM@V!A78o3{o-W97hzRn@jB@T7a;2VKqx@cZqlVGoypXZz3wk"
    "?HdVxgA$w1hw<%Pehz}3(E=iyaB%q$8PJA=e2^`&k&@hDn?UDu_eC{rgW91kSa2NO~fCS+X#cYM#WQa!={^x9fglF%j39?I?"
    "m3{F5+9WALa)zKq(VnrzGsNg9B*zP5t-4JB%<L){Iz@29Ia`*W>*DdJScj1lX#z#N1|L-SK1JfNXAaszUL3$9Fx?unPzV_#r"
    "E!dJ9j0WDc~jxhZLec)s$Xt_J#{!+Ev&0y$<_$-p50LxsImo{HU?Bgg60&#7RaAYt*fQA`?&F#Mb8Pi&^8b&@kT>@CjAA_UE"
    "35zHBT!7W;=dXI^0HAEXBso>W~1;N!CqB^l4oxI{H{@RMhu$FZna`>J(yyWPS(EYfkWo+kZ8#lyZ8kvdhJUkcomjMCaUc~dC"
    "6a|iWF6Rx}PF5eLvq{&+idc%h)QN$1tV#6m-vuy_YOBs)sHfF`xtFt~pO}BSFw9(NBJR_KTbQ=uT~mZN1)r0IrSKC~?Bo3)z"
    "X>eHb5WNwp!KR&0(p$}j|Kozjkz5+cxOEK4GK=j#AUCo3y-VW_RIZ=f$AYC1xIsv@Na7|<C*H>e{<8w<=blWo|)xt;G^GrtV"
    "W%5S#Kt=sMHjSRQbwjgh#{S$w?~a-?px{T@(Z|fIIF9E0ToLOZT^*S-v7nAr;7+^+ZXMk;m2>>n}5Y4!QcWsdL)Y^>jJD2Q%"
    ";RsrlA^v~T_%g4^+lwNHaFXI>n@bfr<vbk=z_d4U|ObgY8Gx0j`MXJm>*XeE2FBx6dgi)k8iFRu!@MsxF%d6j#8xT%P)s)?`"
    "IMA@aoY1MQN3BI<TyQ`tj+rUko4b#X~@XEb5G(5in>MGeN^%QlC9y=?m0uFM{`u;F}iAquq9TTR?R5U6-i>F`kr+rE49y6u<"
    "(qq~EvSigGft&&SkS?lk!JABYN!}%@!t-~Qq4G_#3uf2NbuIGVL6tyxbg}Kxy6%MFpg$)2C}rSZc&^+vCs4ejF(nKR3{6d0h"
    "`997+z7Bdw$OQw!y~(XS;$g{XcsVj^@jDl-6JejV(4f}+w`I|w<O554E6G*Zl2_ALn7r3)_fie%BRsYtQm4FTsSXYW*Z=EAd"
    "sllQ?#gk6%ENKyL<2$n;*qE+lECCKX@o{ddD3tFHlJ3rIh=7_~FQvUlqY-CFTV*&4?V$`O}^c^WcZ~7iR9?3B{&WY5yuWHv}"
    "%f6UP@8P{gj6?UIyVDbi=N=FBD?#`S*2VODzdT*q|IF;^}xj;uECaczHBN;Zt!6jQ5qdP@hLad5^*iSM0@`4})4wQPHP+x-q"
    "Y&ec&}S$7y)kEJ{7utfK-<WmQUk(L7wl&J9NbUZ{%ztpftd4;k&H7p%h;X8`1lm#3_*I638oDY$G&hc>H(;UVVVAa4~^%yRL"
    "MvEu_tt#_6E_t;!1lk+l)@UcxTM$bSuP}Exs02X|%Z5!)!GTT!9=|i~$E*X-12;cRzmZ*vuI0`_G9|C<E>KVFzms&dBDTHIO"
    "<{tWRqa&*!N+ymx38L?qIZ(V{V`Z96`SJS9`#m_Q;c9O0~j3M)s`h$5{J6@>Nj7!Ouc<g7#;MLJVYo{zb;3kJi3|J*gS~7GJ"
    "7)-ORMzC`0T;JWsSWhTliru@Vx6XOuMz(;|dr5?9=vnKTs3BEn;k39;mkm)%xfO6%Uw!ve9?L<FFHdXcmMViC3${Ici(V%lM"
    "tW)O%TV(?5k4u#wW2oB$p&6`>9=n-hdy+4FjavN)KOeVAEVVix+l;5KcQzlx)~j++U*JEP2#Q<a-9HhfMHdFicD^7-*kloFJ"
    "P)gx-k{8+gS{gc`?r*9T^np0m&&dBPa%P^1}A?4r&+5O03^sRSXU~BkuS4ovUhE9<3lZnGY&F9fbiZT6*cwn;_E#uZ~cmhY$"
    "7`_y+tU7_sTx#BXfitUp&%{{~_no8qQK*u$W>>03(XH+wA$)yQjcP$;K1z4<#fSZci*k2)PVE#V0n369MaiElt@SZf<lE3f<"
    "{6ZtZ>3|y-p(w}&W5#g?s0lV{^1IRMl&h0P2awaJmFOiGMMfU4Gk5EeT!i!iPvhEQ-#k%w;vVmWSY1G4)3%=>QYndvjs#dVF"
    "!o-29}l3xbA1Sjs(ZY_Ci(3je5n1#@Y(r>WIr+dKUhw#p&~|_EHt+mnE$={6t^3%yVK3(>V-zyG_ochv$eFC~}7w1GvhyTCP"
    ">{VQli@WXfPfP`M3-#&I-Zucl1Uz3!weO*O?dHnJnu;;Im*_L!cL!oDJgtAIYvK2Ozd=F4ENa$B2ToiP*ew+AHZdjRf7?ZH7"
    "j7Ec+PyXS=}Zh~FxdYe&R*%#{5#X{f!V2jiek5;q@?0Rmvrz%b4hWSfk&@R2AZS@jgf*OB0`}bH6PThVA=axUZy|}p^b!ozD"
    "W>HV`2)|X)1RRX+adqEYRU5asJcZVrHF237;<9xSXr%gxn_!wn!xv5EZ}yJ1slnx%n~7Rhly%?V`qC$?s4okc6AvD^3iK5m7"
    "e+{DAtxnOA)7_6B&xN&i-8L<qHB$YvLvDbgMY;`S2kaC{V4%Z+fvv*X_=Z*g8jj?Z=p7CRpI@k1c{O5YuL~ZjMp!WKh3kRb@"
    "w~dvXw<|D0s1JrXo5P$`wIvxGQ07q1|h6@OV>Ywk*(RvD)xbl+aGo`C$Jc>y0bDmnnaVq965MEh#&8X*7hSb~Dc-ZD$lieqx"
    "^CW2p(>kzrjly?g=tLI0QzEO&;&BtD#9p<*8p|2)Pn6*=|UN{ZDPoJ^zSUiqvyzhCY{3{RNO+i$1SuTey7tp&UYBr5+<{9FE"
    "dP2ZD>ECg(+t?#5jsVICvmXwZA^EkmbHR5(y7kpE-MqBzq51>NJ@KiPRH%7TVp0@Oy0okgAuw@*3NvWtxk(tZnm{;07%QV7?"
    "4PozTG?!$l55`opQf-y|5jBKK#$G6M7&gk84G47|s{ZPJJgdq)_UFJK^a#IJ`C_AW6ZWT!Am#3PYMem%yGNyC;`7t?GE`P3@"
    "}sw2tv^1aU*&c0B6Y-=X*Y$Yix<X9GzLCf^v4EV>Ls~hN^hzo*Y!)4o!Bgrq<po-fOfO7Js=%IeKMg;PEY&q06idhOMCCWTr"
    "d?<SMR*K{MA0u!PPZAWNz^79l;B8^GGc%1$1ICaxY}Lw1pP<r97K*Z*id~uUZ3dVZ-YjNqksNM^yj8y??kwLVGn|uq?I1OJb"
    "K*E1n9l2VHD<nY*k%*43-RscC8W(Ze&YT#)ich)-Y*c(;CO%D5BUbq7k_PTf@lw`dPB2Qc@g4RL@`%>93{MuM_@(>@4Y&l1L"
    "H9)pz`DkSa4{V7@ZL|GAZ;2ex=$Cjb|x0Tjqo;v;r{Zr47ui_seChx@Wz^}N(%tfP&`zX-<#5OCgHk&4cj$8ko+Kynw0EE`F"
    "SH~I|5WvfY&*ieSG_sVRQ7H&Jg7?7sAIowB92I=>ucjo;|G0%(?rNd@ry(@cJ*`SBkJwQao5Ob279+;Br{R#N;rqKLh9`U|$"
    "b6EwpicDX`FM>sW&|~pYvAfCmM&4u+SCCpmCtHvvm9<4%ZG#jR_xX+idn(-MN@ShBA@L!lwOb8KuZ+q`#@8qx}M|B<20CC9Q"
    "7Wyrk+Jt*K{!`0rt0{$@1G&;^`ekix!8UHQ&46Qe~J<43Dkviv+3BpHioFH(5E(kq}P!iI|(HWg~#S`x0DN-r(@$S7G{@m!="
    "wd`n;*JHzJ+&z|~f@P=DD}8%SLO(z+8h85dbw)Onm8#)KJM-{Qlao4UBZ9rdW@-JsXPyP(x8>N=Z+#H`-$otWkOa>WCSqgT~"
    "KpxO`NJ<x@^%0}RU8CKmZDATf9jsAO5%!E0`l7`k~-kMqQss($;8n=t@#Gm$a1J%rIw3w3jj94EAz#y+NaqR`(c2|DieER||"
    "t=SG}u!RN4YSq@|i)n|CX0l6LoW~%`9#Rc;35Aw5Lwty%;rvC!ReeMv__i*Z0uQ>@+SKGNMv(lwhkr8HeTcO6pzsq5Yn_;6B"
    "Xo|>936gims)Uo^Ub;o0||Efch@tv=iy7wYqoXbsLWSS_rsC|2|IB;AHV<7tdl9wxD{<$yAo@o>hfsI4tn*6bMl#Wby^Of`g"
    "ePsA-8SYeKqt49^|AQFYzAjJ$93jl72p(zP(l}-}E~+-ZbJ{x;Uz;OB+_Q)h&0PZi;o}+fIj5nj!^M>^%gTb<ewI2SX19JjI"
    "z(uro5n{(?5Ryqs}DJ@2YR{V6~`-gbMhvTH^{cT+oW!F5sQr)ri(<sfLHV%)GQOb}9`4ph2*<v3nP`eA)b*X`qF$z3>PS(!U"
    "Pa3&ZP4Q+T;zlpghr=onHbsbk=Q|nGS<Zyf*rfW^}V@W|#aj#=+rr2Yihgk^zoRasn>(|5JV1}Pd9+_th{+)0XxIi`Ed4->M"
    "KN#1ZNAN{`Uw%p1R7k}9W}^0b0yjhtCd*j_{9G-g(X-t2VJWWNX8|V=pn~KYeB~OO_xxnGbL!eNo{w`8a9hH`$M!S*<7>L(b"
    "u`I)>5ISJ4L+r=paorhbTIh&<m*)0I7@n1u7<pAx!zADcIhnj*~Vmcg7=Z5R=0cHA^uN~foE-HcD3dPvJ`}g;-3Q-<rY6?f;"
    "=`$WBZO4s)kc;SntGUeb|Nk)@8_=&nh@h!JUl#uNN(agl%c#q1be6!D4Jf9oc13XTM4I5-K@H#sa0Kx%}rtyw21AHm!rtj*j"
    "rya5^Zqn~4Z9YsGwYHn727pW#fQ0du9QsQz|3qGRpFohiS6d=a8reLGAIb~jI~o3G-J;QLi|r{pZx(q09OP!>5nI8|)9t#S)"
    ">GmG)q`M4tC*yBhkK3cqD-*!vxojdmB6PyW?JpSgxQf<xAYr`IiZHcYuAOKrV%!Xd!?UV}Vwj<GYFy(@)cRw&ZbLIXSH)soK"
    "$Nl(vBGIFVo4Ar7@{Ci_dS9sf0-MeLG3!g<4}qnagoK2P*IA2Y4RN`+Y{N+sf(qa`PG1hk;8(YDGc9xMtq0EPKd^PwkaaI2`"
    "^m0f`|J$Gqf)Z7Qc(v%`rHj=by2446qm`J=(u&DUv5=*L`(;a{5JR|(07<6A4XgC;=egXH14LPwPq7(Etx31=UnjRYwG^p7m"
    "hZb+XB~GQ8LA>t6sUzykty5ZS3g@S^JW&$N7B>Y3uwMer~&pZk*qr7F&PA+L_zvaj+!E-8C{1l*VPs=78uq%9u{!z4=EDX<@"
    "yJZh0z%G4gkYLxr7cg+qKRYR*-i?o_~QO&5C=Rrf_h`%yt<m+E=ygP(=Q-Tg4BJIJR-y17rc(!j8dg>w_%b?-Hy($JvX>ioV"
    "cg9*%G^r2dhjW7Je8fIBX{z{uOLE-Sy2Jr1T6+m0IASvZ8;fx%3+qspi6Hwv*23Y!#+TJtYv%nkBb2TZNc$8ujBzoR?<=CCK"
    "5pY}+*8lU`R$N^C@~3*qqeEPwPpu810JFwY?b>~5PpS}Y*TL0w&S?c&Izl#6s+<2Xr7wxi16>Wx`?<HW70DhEDOQxYyEqc~#"
    "~-u`yGIQwZzjq#iTHILBWs0#e>wA9V{Er$q{pbi*!Q%wuif&_!`VhBYi)CWPZz`3jW4Rrx&k_B*F45KheF`{A!AegY84a|Y?"
    "k?K{yMd$hZ{`okzpK|{5V|Z-9Z6r8I}q7;@brQbp!+E?}HXCtK7YLGAV=|yI9T>As-6mzD~p{`V*)&t5*#AdgbZTiGlmf87J"
    "ryXQ*KZiaVmljW)5@oh1<iO~JU-ep?9EkGH2o&MoVL8`G<+tJq_<`C_CxXAFenb<B8iY}(~L2LZ|Zp=@a71D4**)KsCR=%%e"
    "tyUdcTo4Q1rM<ly=MR-A7R1$xPr6rRA&ZPL=+J*J`$qB)3CADrpn@VbjnGTayiQ7YZ$OG|1$;YWG-LbZUsHNDf)B`SuYAg$a"
    "Daq%~f_}FH*q=fdBwfJACfcD?S-gfcfP2G&0wO!VzEyIGNzK-9pA_Do_cFIp!|uP?E^53}U#xla<a?j_T?JPYU5K3(VT^O12"
    "UKDCaM?Q^rZGiIn5OgYReto_&q+#CyekP<UP_v(Q{q`=&p-2EKQ%@Fgf;yinDGCHrtk1)!~5Phs%n)|)F^G$Uae7kbx^Tq>^"
    "+L2R_#%vs+7J<tlGo~V($^9sJ%t4AP7=o$4c_$^ZNb%f#l}id+vFjbDrnKmTy&nyTd5FslNV!FU^3XHN}CeqBcBcllbCFUO-"
    "+bYyW%R*iK*-{Ub46+G}jb1t>qoh7+)#YhRX6vZi$S6wsR|f8yEV#P7#$U~Zbsl5)=~tzlLim!5=EPb&Jm?^d!CNFHe#{u5G"
    "R(i{wd%+=V(>Y-B!faC<eRajO`6mM2S;@~fp`o>092bz3}d%brdSx+HB-8Fr^kanWh{d${UB%Q>XBY{L)=j;WgPp8#3G<CNE"
    "nbWTcQsEuc$QQGu+%kh#hMFz<vgqe%TThx3Xu_i)rV#GM$=bhl&hSO~gMhys!A<$GlK*RBsA_<KpX|;-vC)IO;u97I8&>+~;"
    "akfVp(itka))9z+9KC*N%dGv6?WMM3pS+D+o9uKd#sYZbItQ}`v{%*3$)v4NS@t7+;uwmIobLat}0q%oah}_H|;O+R`2|tz("
    "}p*P--T}a8gM}DY~%DaeJe$yLuy%;;7sj2WVu>d_S@NrGj|6cuN7Y^g4!Y%N-cA!N)T-#!@^lZKYy~p$fXQfL;>y@s>7@@5B"
    "!~YKsK1SO-D3!2fs{BJ<mcj$bcGsPQHdg<hIv0Xb=dOnNx+tDLNm`_)0q<<XJ89ft3e!D*B|GoTWID^ZKq44H#!5}QoDf%DF"
    "zY|H}(6|O%8s-*C^FZT+6C7zyuMMKr`qlHO|W<J?FalAR-`>)i(kJTcf6xp;CyS~{x1s3gKyaNCI&EX9D;otNc$qmY{UAkDD"
    "#M*JYo>HYF<G<g1_^>ZIO8{&^Q!k>^dFcM9xGa*_b8@9v%5M0f|FITP!)$!=Y@#E5D{v^4P{wTmetjJb+QgNjg{bef7v=lJj"
    "t>G?K9Tn|mGuUmp!tK#6)_7<Is$LDS|R&){3^Ra<b$Eca1)lh%}JUMuTRM7cs-<P>EqAo&t;SL{m3<r&lVd4TBui?7vpDQk~"
    "L5=kM@JU1N$4DkYE)JKVU1XfIgNzenCl?Yj>k=Oi`|LFH_RZHS7^>8>ew*N;J76h%{n8e{#6?WklS|rXbzi0(By8RFPLa$0n"
    "e<YCWbfbsHh*uM8rM=}v!8Jg?_2%})8uRKqJEOGGM65N_t=Dq{@9?>84O%g}aB=a1zZ{gtC%+veC(ckS6?+WC+r8-w~$ds)b"
    "dE4{khYr{Y@&X40nf-h0mub#IE6!2~;#Ek#w#6sVe)WGDR3W|yQ9+*DRLm45UOtC&Df0Qt>uplUR&$LPBcT`Ta!;WE5wgI@o"
    "D&(Ly^PYD&4sAVTk829QlybrGuEJVcOs&|KdYjo-Dbf_b3)*7)*gR7NEqy26NGf~>27L#aLuorf^sGh~G@H|}nTN|PbtgG8A"
    "LzlRD~UkuAG-avjHvU2c%_-Xm%Sm2pqCyDG%@=67_JlxNB%pQQfslG`3fMxJ9zIs<7JuwYAc1tWGM*{`_+cNz2<dtK@;+scp"
    "gzH&_7SHoKkTbP|D>sIQm3Qs_UaJ$xF+&cwDU?wC$q}daXOc!pg>0f?d~sY(lI{_FWme=qducIy|`hGKwaD@O!B?_&({NBM)"
    "VRh|7jy+%Gh=?QVl1(rWBCAsB`YK4jmr*b1U^UC~29+U^OizM>f&?EP{(Y(B9f!S`YKX<hC&!ZMX;yY7^Z!-=lJU-y}FZ9_^"
    "ug1KeSheek&sRyb}w@TGPwabFsPAzdBbCh`(&-v-zdA}KQ8p{!e8)2voMoK?Ib95x|lj6k|mq2@$0Qp&AXV-^2I;#lVVkSqK"
    "yFlT%+C9NvyjScqF`NQbeb}S*g3UolR_<4glJmU1jnciSOwsL}Bmj$+Xr@l=E2^;TWo3Im{2`CK57Cbd+x-))vq3zbCWx8*p"
    "p<`^f1zP+zEGdDP<Cr<v;5ZASG=eH{@NcOA164^6vf`{5d4&A<r<kU;iSi>k~EtiI{rJWG5GYa^P9@)W?;ryIQ}S?idB<Ok2"
    "5=o)y7aBm=auLrW!Yp;-v4w<|5~q-EzH!>$l-n!R|AHueF~hXTSdZifE2BLT}6Q({w;#tw{2rzE*0%mqTjZWJu}w{m*3|yLX"
    "MSMCqDuXJ21B7N=E5n25;lndJU=rKxZpy);pHVKZG@>P(02FU)U|9C*+w7Y@GSWoYn!A*OX5sHOBT+~*zIPbxh@3ihkrF`wx"
    "_fIcV4J}`yy<KKdw^E11Z7S_8Kz0TVeZQt)cz#RYJm>K>iwagbo;Z372X)%Bc5R)N#OQ#1<vPjwXoX<JM(h~M*k!ake6s+vr"
    ")Hr3xb{f%tNJORMeYV=qXPBUv|AXkiA9@WL1D~I51LT(Mitm$T-TGce<_izEd(yk@a7)QJ(ukIUpPRRE&K6E6dxOpVcKA7Kx"
    "N$>1K-;n4KDRCR(18`#sF#>uHA&vrxq6qWGgK5gEg(PJYS8_2v`MB-d3xrD$V%^dncAS_u8JQy|CZW-(HcR9g0zZfd3kQis7"
    "m=qZ})Z8EqD%zbO+SmwbTLxu<I~98ur3fn19Wobebp8Pj~Z{p{9&6)ItWIaRJiT)+ZE%so85c>!_Nl6y7J2XymWr)29ACO~T"
    "vb%_#YwQ~bek9wNRvrp{t7%fM1M%fr``{p5Wdr6;vgp>HBEP%4>%mwSdm6*zb<KGE5|sy#dq!$@RwYo?=pBh}o&GhHdXQ-#5"
    "LqqS;niC;B!aiuJo&n+OuJU{5H^l8LXi7D)~9<z|iv(9A@(8|=0>+cQmPl`Ka+9HWKOwetx;ElY^4R}&~o1gLa{wi&FKuES3"
    ";Hybo^&#@LregQTUlX|@K0e#B$i646KMk8{PUQ3{HH-2LyTh7krfTtcJi}}v%ccWE;}!bcrGUOmtJpI3sJ;{@c1@k1C3<7|2"
    "jBk63hAbhnF-Cqez?Z|oy%wnL`GS3mC78>nif^=+fmT2VM_e$=2!;j>YT^UP}dCG!{P(*rKss&L;7z6ChRFga=U7QwBwz(Z{"
    "K#P3fU<uf$X@{+x1ea1k!CCeIg}~2Fw=J#~(v$qsxorK^%>%hfe_?&M)9FMJ_RdTK?@N0K>Nd?bqFuM2TZ|_YE7Omtj{MqEw"
    "8SDjs71#WR-UBD0_?*r6_Dmf{FvRPMAmr{_Lk?Pf$wXWYjrD&%V@y81M+Ke);?FRN9tESM-d4P?+*L*C^^5i7MF7gBgX3v{1"
    "&6=U-Me@3fcxfd$ie{lIjFC*}QgAo^VK&Eav^};%<IW$GRIl1gs<ocoZAgTVH@sB}FW3Kd(15}aA;VAzwwc%_zAcrV7!2sI("
    "^f*~RB84b9a1Nq5Jc!FZ^}(IMhcGwddsl@c*ysRV3dHEl4if7RyIk_t)TfjM-80#Emhtw>ghEIPi3;Ze#67a&76E7-3X<zr2"
    "jC&WpJocG?}6U`3y40iCP~duOq66t2EgpK+4XFl^e`8)7mXX#-14Hb7qVsO2cvZ#gi77#hJ1HcY~lsh)s!wK&b}O7Q}0{;%Y"
    "mo>QyLI$gvF(LDYtF&kIz4NHtT8lN!|rFC<c<UD~6a1=O`>ZdK|DZ2#QRhO;;6ZS*Nf0xN8<jjX3L*>SN&4H+{y+Za5phK}M"
    "J3@W%As_M6Lmv>H6#icQKRMew7qudXnBTYdu)i`2<@mQrz?6TJ6d=$1X_WqRH)VY<ptUs>T^-X7Qh8X7}ZR810bs;9;GD;Ln"
    "DA2=!Fv-zjy^@f|CjM>)WO<|!a{?PbIZw2J}!;c2shUvh7U`H>#bKOBxi*9b{^vUcs$Q=0DP02Qh%xg@l-5Wo%;15fke`zQt"
    "+>perk@|;D*hnF=4|k&<`+P`JzVS2ylwy)hGc{@HlCjO*n$5XXTzG4!RF}@lm5({-9#op4!7?RS_Glh`Z^H|c^NE4tNbf7js"
    "aUq`bw&iYUn92r2;83kH~$W_<!#d*kfiV+L^)+jU%;Q0TfY3RdUi!agI~zfHWPketuUI<1jFsVG`;LGW|XzIe54Dw2fjbf+Y"
    "z*6CF|LGdv|yDPznme2OVq`CXJTrS!OrUQx+V)jOL60JR2vw?Ke^&q?`49cY5=iX9%)+Uq_dl2K3JG+w*8waofjySJk||#DQ"
    "EBZItf%IodbEh-%l1Z5dP+_lx%dZ#c%T0Wlwa99KTA-b*u?@_diy6KSzZY7}F7h}b6J>s@PW(F)(vqWy9Q3aYA-)bfLZEV)u"
    "vpOlx#8#O&Yk#0OSE$xv1($O1QPYQ!kK(RIF4#RX)X%aurPr_%J8ou6)9Rn2)a918ZQ{-UFkMggtj}wZ;AZ`Ab7Z9yqGRbdw"
    "rVf{$ZT+QxI(c_f{zY_vJ2-P+n$eF_@MPP744285WTEifY3`Mjt0HR-Zz&q!L+s>gL#7OR*$unUOfK*Yzg+O9S7u_VmH2O_s"
    "HG(^#Ex#y1kwX4M?!gAUcGu%P*bA^y@}H=CAnciW~z;Kqq1)DgkNwN-cRPi_YLb@%`&7h>Yn2XJRhc}s#+AGl3IEVhHbCfGI"
    "*|X`MTlHuOb{Yrpx-TH;qeMZdc-_#np$yB9xY;-~CH}AI#UpaZLu2h+W-|Gg7aa6vxaLk&ypvRQokj81TG;D{7%7;o(AFe^$"
    "L}77xmBY6^0LyS!JX1RS4+vkca+fwnbAf*-i-B9QjG?4?Yv2ACcue_Mxk@H-vTVIj4c-s`}wXS`{p2O7?`*m(YM_wJcL-OEl"
    "OsC!Cx#;cs-yT(L@&;1dhO=mZ%hY*w;;<+N>d@MOnG3S1DXQ!3Zk_gI<q48PS=mW`#fU)3Zt{V|K%M|w&19r(j_iFb>a9;q0"
    "YIE>vLAS3`7|r~ZX2`R>JuGfniZZ5!>^8s$LB>^9!a3pia~7r6+%M!NDQ;fEukuA8Bi}E@_{XPZc23YU8gNy$7M0{k0I;?!H"
    "qE1js?7*}slO_G(b%fX*m!rlAF!3G68i82+6eC_#pUP|@<RE5KJ?vhf4x0_`St<V8)UMMqRaca>ebT0$2yAV>&^S-adGqU5Z"
    "{+DFa$JS6SC)%n~ccy>SM7x+8j}p6d)q8?Gh0DvyDu-kZWIl9caPh9Xs6*E49Bv^&|Nn--&u%4!;~=JWgME>oQMKw~U5wh<3"
    "@xEUgc3;L=V*#is}Ow=b6SNJmMpTdO7T?X-f^s`t*`)N5?v;+&CsgkvJzh6`kqueJZ(^c)kJ^-)>Wb!w)jAnY9NHX*c4o515"
    "bUWG-}y4@NwQZG+9z-7im@49ilqG9(C7qd<4hc_*emlQ~YUM;DmryOBtwu}by9JvrGv(>ojy;cq@Xl~m)9Hm4!Kk##c?1vZd"
    "Fm6<YHr$Cx-8%R^^>9ZY{cpL$T*$2cZQ?6HbFhMY^u;rNw&Qe7*5tR_>fu!uE%ZO7JXIU=1T8@OW-i`^v!W;`PDzSy-r3Xe3"
    "Et9;TOZz>o$-jPzBU!;8T-$ha-%fV=uk{|)f}Mr1|ZWr3D)Qx&6aa(glTV@r5RLjUEZ;FHYU=fT@91V@Di;^FZZp=U>I}gZ}"
    "a9b9A1ZdaVJH1M>E=OY+eixL{<5Mjy_AZtDOFjbenyUqWe|ov%p_tX~oXP-);rWrj|G6pFfBU*VSC1TEJQO`hRK;f0b&5CS`"
    "U~!<WFN79llwQ<^ov+w*wX8Pz%4HM-qR2;Ip^h)w;v3o&wio?#-Xf;;M0!q;q}(OhE`{8!1nRz}=<hTb*Qf}DlAj-=`~d;k8"
    "iTX%*N!VDQ~lgdjk`UQx8?8xm{60}3_n$Pr9m4<E&b;Ak?l^CTEi`A2YQwBV{-|$5(0A8>tDMO#k#z*Yh!ag16eURw=JXhVy"
    "q(Qr-Mib__ddUfv=R=+R$_g0dSLSU64%b*B_UnWOqkP43+J>if&2{DszFXrD(~v9|KY#wD$&8-*{l#v9S58Gh%2wCo)Zx?Rk"
    "rKh@Y8QbQHl*+5B%JjdOp5zG#;?VTawzdatds}uf_&AO@gO(I*Z%m)>T;M%crO09q(AKjBWKibjXGFXB*s+lTWgS>W;o~Y-y"
    "rg<WehGS&%tkcRQ=B*v?PD}pP6inD?c)Z{HDkHZ?|cmTjo(J{V`ksBgR37tLmRSA2zJ+_vluYv4wqyI07Oloj<|Jo?mE&e&O"
    "?{-ob)C6knw7q^)OGE!Oc9?o<|blWxgs&(atZtYS|!u*w^kd7*?=PJI5ANAFk0wO(fH3drpeEV&=9V4Q3nfY5Q+O)rH#9K#n"
    "bO7aROXddHUN9qM|4!$uAG}!7lM-S}rh#T)<MR#Pk^F1kVE>`kAi|!%8B|&5D+>m20U7h<18Rzuax<gF~jyHi}My)wP2#8~p"
    "LFF&X2v(cr_Q3U4Atg@f56bw;H6$<6$-pJA5W`;-!LzJ%KA`jaq5q<-CTL%$^lbSW0vTOLH42#ehVizpw!PIrZE3VDy%~Pf6"
    "R+y=;TIY6mo%%OGRUp3u8(#uMsA^_UDe8sE4%;wt?L&~6j;t0tpS4_LqbpXCwM7rAHRlw5S)H$$xq~~V%G8^_A<+=PYdg<cR"
    "6)gskm(@(gXMdTvop5JV`TC`sY-Vm@9;lNE{D@(B}glEB9+73_kim9u%Zd-1^4i`_LNGlX+S-`ih&_Fz)u497g{ALL<#gG{@"
    "8fi;^umq7&Tf)Rj1hYf7EP8;Uc%(2q~X;`e1Y!b%opG*5#=ABJY^kyITz@oD!4jq4#_x4iBgo)%*%$Gu)=y?9UoA<A0sQ3Ox"
    ")tA}32vBsw}1do77>L&f1L?gDZd4yy{PE8p8>ije2a*|3}RK1Wvl9-w{V8^q8v$nhA;G1Vc!cZ<H-)ve1Uc%<PV`^d&p64;w"
    ")k<YinGu5j8)gB4KRv*hob{vinPylQnmp6UbtuHu$DigKHE<ezjZ58*zKn%Zf2qw9aDxTS@vmm+f`xh*=tAjBf85%!y0hBs&"
    "V6SKvAs8An{+GGd`a-p)xrhVm%UZeSjkEM2VZa2PEycS@brlcQxcK>m7aA;=<;=PMIvzfu}T#?eastP_fJBnCDSX&yK3%WE@"
    "}r_>s2e66|3U-N{a4qYNXh_9!kMdoG{~prp*Q>kSu~jmf|>Zogd{<-u5Vm`=l5CuAJ=Xki#-x>*+a$PO0IVd?nFi{|;-zAnn"
    "gI_ZLNPvgh<81Oborf?N8l53!r>miFi#KBZsV_RLJ5l55%eES$co{=mINEF)RjcWeCdbLUa^sAxj6%X4^LuydWMN+iAM10z*"
    "$KY2YS)lgl%C|Z7+t)TC`q}fvLIx-9#!T)LuoL<wyZQ<hI85mkRW5}0F-Kxw#xsiS40^%Z}pK8S*wc4_)ZW4MU)(xVecBST%"
    "J@E1@8!+Ls2V?e@ZD~rxg-nd_m>#V~LwG~>A<3Or=rU>dog~0&9^}6*IPbrjyhJr4b6r?TMW$;8q+U7ntSS7mi3W5T-JPrJx"
    "MlQsi+wwD8<16f@=AxKv@kfh6rJC0VCW6^rnG7x0A_J<w*vgC4EJI_q|Z3;{?<#D@7OK#i9htv13U#w7z}Qi(GctQL;F};8&"
    "{pv!xVY|GTHkbGv%M6JHpb-R6J3x2|0hzpHrtE<TbhZA&er2%!d5*G)kXGZ$=9^Xes1w=NKLqd}Fom0puAl&g1|q&A7X7-|6"
    "twJZ9G$dwX(afQ!jsm8P(v@#>+G`t#q`Lrg%dN;ijAx=Z(4hWAE4H2fazganP4J#o!5s5upQk!b;DOmSXu$d4x6SQqa;axEx"
    "IVe$RvD-TM{&U4=)2B0R!$Detq7vUNj8wU|L{bp?$r7CY$j5otbb)Rvi62qcSVg2MPu%*Zabjre1-veXDhY0mUPR+N|Psra("
    "+d7@K^U5Xxs=U!<NNS8mY#%RWk6z2ItvB`{*4*jnPp3x>RiW-7ZLat66u2uM%JB4I9M|Ljc!~f-#cr<_CeEN#T_9-qv<CBzp"
    "q6nD&V09S60=jakBJ5;yLvNk;9i!#P#zQWQ*fOjwW)piQYOX}d|56SsqMFFFDsMdX05JQ(&?;yw-snE?L7S&u6UJDeiAr7@J"
    "QZzIxS6uvK)5oSGbw?zj}e>Z>}VHvE?58C5#Zf7^EZWs8XV$-MhDw8tL6lL@^?<T@<RvTQt_w)AQ0lUva`BXd8?qKZxSIQr5"
    ";BMm}eK{rU6fb%eu6lC0B1$$_E)F?Y3vaT~<clz8Xpe1n@#8H>TRL+}%+e}K%rjKdYGTn(Akvc>XA#UWFwf(xr@KgDJ8T#<j"
    "VShk!kc8q6=!H<-mZ?|&?1Y@Ja5Bu^J0my{IV?A8zg;GcO3MuDz=6@A+qmVdNV{I?vQMM<p=B!nQ?<n&ZSGQUJ6Z3gOEH9rg"
    ";9u3<UoMz1jTmg>az$)}0dw1Lw2q-@4t3WSecy4(ys?W0h!I)D6Cr8MKEaYnY4&AN@rGzd3kL2L`JA!g0Ry5fEA3-Q(Uzg1{"
    "+_s+^m2>cnasd4qXCs5kt=m=`qbr3OOVYWzl1_ktC~MCHQK*6Q?QC?$<jy-lm7IbVA>l;nUeJF<bk>|MZsX45zvx*OL|-WU3"
    "dBY2fkOUa|CZbY)iG^QH5#Ux~GNDh-As|7hDjB@rIBt15Q;qPp7r80(2ppoS&r(bXoGIY>rC|enR}LT`4rM#YdpzL1{e(u=_"
    ";FW~W~VNw4x!ks?4sal$(@oj+~3vr};gb7;f=ZwmypDw|h*@t+a!`QJ-T`&>XoX-cE7`<B^6!_Ne6nX5KiVp!HVi(?HfLSyO"
    "YqpL}fCTLWu;@NoGRM=L_o82fYEiEm{a-vd+&zeQbLQNJxI<YAolL>IDmhmrHmdD95GOzj9c=X2)6(E|@*IN|$>_5FXQZ|}>"
    "CcRlE*M!#o#v1$p^N@fdTye^%KY5%}fq$wwrO_)lfr`7ukm*}So>AMCEctmStlUqhh)RJ1w{sMVUE<~Kc=}He3#@$rK~B6P8"
    "dL$?mGy9ZQ;4p%?@v6yaNbB|y(MIfRqC>y-OH(m+eM}V1{1uYE_x*U4yV@I0U}K!4veA<xR2AXnzLe%Ct{{#cZ3V^mEH-ZHL"
    "4V0Pgj1x6ZL0jUKVKMGF4mVILjTAQgZ5Z_AYcV$5Me>TeChJ5Az6>2%y6A_1C**l~ow=9Y&@Afk3k8B(C?5zg=iaQWPEh?40"
    "Tub^0+b_uorN0E>))e3cXB>T};Gy_#T@Yo(Hb8yTYxG)b+$&=84d){^1&o~x@_6pzfXlD>RP<Ng1L<^0)XTBkz@{wOzX<0vI"
    "wxFzK?g9a!{_KB9X%Ma~jpUi~G=qyDkDXHB1%on`5A^Lmho2DFD3}@+pD8=D=VBR51>G#iZYt`F}Mw3d6V%6RofOEDq>#&x9"
    "%?xLVS)O!;rmF7GKa?DePvHe0U%U?$lDfy|kJrmR2~B$y{y@9vi(D##x~kl5wU9nh%Q(<Wh#mcL5TX^D87;rlB(dk~>ziPGE"
    "IuZ0@P59&48k_&a1jYzj5D)_eT00y^{wUUt*Hmv_W1%eZ*7TIaj9}S`<`i+TA_i4mop1)(z&k#E=%d|hg$0YQ{``-mTMqC4A"
    "P}=bGb?axSGXBk2U<D&s#iE`0uOS=E=QA{ZxZ-%}o|l^w_jneinAhfkG+X$a*9A<MGKi)<S{6-tDp6{f`Zs=SD--Bzd<VuUd"
    "z8p3IuxcuQWlYU}ss4@hdYraXG6eOTnS;Y(9i+sDTol$m~t#m1+mGPNB1Tt4RULWE*Fpu96PKx^TgfHjJiq;MQO{2{GUo;}#"
    "!Smc+0Nd4ra^2FRkgE7|D8~Og&y4DAQdmC$VEW~2%S}8=j9yqhS$y-4M<blnay6FQBns8ofTeKcH4(R~(JL5oK-T^+lLlx6M"
    "rN|Tf{^G2lwrxrdSD6xD?2^d2=m)ptb<MX^n^yQrzh97|q4)Kn(M2LOiS_8M%u7VF4ZD#a(q!Iy+5rF~tUe>YPO~T$$G<}G+"
    "kRw5hQTGw{E>z~$A`Rs=oc|%RG{$=o$-*D-Au@BTQPOXp>No)aVg}(11d4X+m4}vOHqJ9A0|96!9qIKjrAnqfBnu<J&*PS)d"
    "RFOVLmSna~Uc0M#45>$DwsI^G@3)pIaN`n>LBGmgYbKKA$%9ZOHkM^$V-2eVASESFcsV4XqmIRU3Sh9+t}k6Uea!l~Njvh9="
    "G`VcL(h)4L0dGu}NC!B$i0X!F#5fnP*hP$)A{w1T4l4Fu7q6fU0j2W9)IXlDb#V!p}TA<G*=!>gDXS%IOBos#;yfr9+KPrQy"
    "sq~c>ag0={rn6L<*vcce_u?HAXdA_p48^hn0A5G`TOz(fRm7)`p5aCy+E>ItwOrNaPeCi7MVVEDss{1q(V3+Zg!cpMUyRU|H"
    ")9>iC-q=Lt#dq&@cRv||m6qo5JS_{r2=6UkG+fO)bB=E3U>y<I><sMX-^?Iq=b)gV*2^qKluXH3#@G7HaBG*QRDn4#;1m9WN"
    "#x|SKK^FV%%(Vm&JDpY`VW%Ok2AaY862^J?XWzMkAugXQPm^-1w%bpPCm-q$#yRC`m`uaxWS2%ZbOP4BRm~aZ*%o^!6~`xq2"
    "^SqpxO9dhN^E$imE3ZN@2pqW$ii5BLBiWJ5g5N=MUCx+&L##IxnU6(n37ohfM(%fKShb<VlDO0F2>E;TKc6P#0pg9a)Gm1NW"
    "08Vmk8(S4JhBR~wFN?9<Gaz7s1tgkv3Y4qeYq>~#4D=Nk*r!b!Q!*5KDj+ML^i!fKtMUoji{Rb-4}GmfV}G(=or_A<u!Y?gA"
    "yN<%$CM`%qRr)a`5qQ?8#UNd!aA0s_^<L^4h<^p<B^_EHG*ZMJ2@^X1HaO%{h8I0WL=)Olymo*?<32)YcJxg7;_>fRV*lOSm"
    "ts)<pt^qz1HSP|1kHpRj>}OzqE>8tzR|O!pn*<OtTX|9Q9{71CL@M&rn}!6uRlsUY)J^evm$}li?W3yzVHt6$SOr{OLxjQ)k"
    "l3uIK%TTVOlPp`X)m6s-y=hHlud!V>S!#TNqDnP<}I_Jz$g%ai0YMOEwd=HFACWmxLhx5`L8$7L#QX+T6{0YN?JsGN0u>34c"
    "Pe)iGtfz&nWy&4VLmlna(rkO!SXgI{D&(kYf~wwg@MGl@C5HMvchkYj(g|T;Yu~R^7JEAHz{$-UKZp;#)mmK9f%KRfqCz0=@"
    "<jTZH3I3a50GLZuOd1U<EflC1}QY(K}sj(#H8%X&59tQaHBsFIs{74EOC*w)O<Vn<v<QQ7`hM-Nds!FyX@1)(M%$+k^0zH#}"
    "P0|osn!7fa#4xlIFU_e;ANpE~7l@H`>hopomWeOzNeSx-#7;_6>b`=h4a2GyV9FUJ}6_{(?>U;kD&@&FOppV{IA<<z6FEa;|"
    "vsgZwyqsrVrVX+#yi(flB4u5LS#A%41l6$D<mtm$j)DP5+fCug=1^2q-?Dip_e*4rw2kE6>1#^`pipA$L=(Q5Ly5h*@`U4Xr"
    "2;%_fSU;{-*)m-<m)OrI=^0f2E?bJc=n0V^FORdd6Ugl^<T9<2P|(I<9_H@)irYn$zvlXt!WcwwOgdp$n3b(@0N=Cd*$_-(M"
    "ISigVFPmy(-sxTy}V!-ush2?#@dZ!u?N3bPK%mErh)+qlf^NYwlnFxX)GR;|OIXIrGMw{fvd+v9Qy+pM>%}X0B+kyH_6@l`8"
    "ampeY&O@qF;|QO>E)P|YFdx2bH%{frUJInI>7I;9n73iq52=Exesa<{GQK}R^^yE~{CUH4WDD<1gy5q9TO^|7|V-zTB2F<6D"
    "^z15X55M_A-z_jzNU|yb|936AX{!}{GUF85}sSYS=XNN!@zE6Hxe>POp&mq@}Oq5HtWED2r^1Z6J_FME8O;OLiXB)2n?A^0h"
    "7bK!G&1q@ne#~R&zBMnM#7Pq(q=g&mQgKt%8nGs907kpu-vfK5y_tr{J$92e&gI`YU1@So_N>|B|Kn$FBi&nUsVh4cBrbcI_"
    "cBl&SRQOOS{dTM=%rS-Zy`uP&sMT6`6EKz(J%q(QK7|Fkl<^uX3x@ByYl*+a**cO&4`W{h#K3T&yGLE`%{a&%=r3D;muV#QT"
    "n#6OhR5NV<=cK(bkm_*lJrF=~22?jLJb;fn*dyIt9kTvCa!$k|y22v8hKr=)+f-wtk)W-%dWJ2xK=LTes=DMd+Q(docsZmX6"
    "0mcPOd1&hukA=GPVGId246pvKsnSN)kW{-#Fj)LW;2juDXmxKZUr=vUTjpHaP}p8{8zdu^Yg)6@2%zQN^4h?4U^3LOzNe&x="
    "wbzyGCj^r-KZ>M}<nR2O^7S{)Ci*{O>F)4K#0qp|oUJ!Y4o}$+Z$h%Suu<Eo0ev|6FG~s7GoG<uCVg}!5MVkPc%Z)2tt<5`v"
    "PTnmB8~J0FmxTPgDR>j6FRCb0#Hfvm7eiqh|DJ5`dKDKATQVj|!Oll^FPoNw(6wV39Z84x1sfuiD~(#G0g~Um^DD{^f0~m|w"
    "^n}bG(TLThr+xvwVKvlS;(90Xd@=yZZ#n9HGw^Udp@)`dUC>oh|E)tZVX;rCToa@Xws^4Y4-mVhNKPKk1C!djK89#xxVq>gB"
    "KFof2uuClXe%Hbg*&tL?K~YbG^Zw$m8&IMN3A)6``}852lJmf>#0Gf>ll|Ion90!<6v7-9y`=Iu!rlK1swWAQEmb)<Z8re5g"
    "Wk^|L!f!x7S7W^bgHOFjsuX<GUHu8%GHcEeNY8}UEPn2h#;@a1bV99n;!*YX7j$XmoOJeTD!u3_o4P@VfiWAT&K!SAi)ZcCv"
    "oD#IzEf}a$tBI`IH(O13JS7b7(x@eC*+#K-P0GhR_99i^L;mO(?nDO^SMxQZD%$_?WeY<6}O+&Q9kZVqAXxrlWQ3NES{3S|-"
    "<S3AxRJ;MVjb-FR%NozW01FD&c_I6XH%u7S!KO`o{tb^l8eQRX!hTMc&z2A^`{W#DjV9ZSWJ+>{_We>C!#^)yJExCQ3mbFop"
    "Kp5grbddW_*Lh}zK}*i#PHDiAYKC7nkfl(TMY@C2MwCd5diQ2sYijjFn!Uk#h*XykIzE44&$%}9BofU(J1iYAL;X_r%EJ5;@"
    "#NIDyxp5vzz%3Tt+V?8VrG}kBz?`#*9>zbz!1Ay*CDn7cyIqlcq?!Km;n0W}9^tsNr*6|Fu_lWs1r)d$;qwRq43?d9f2QCmO"
    "BJw+H&jWuDd3@HN6V?9&CgUU&@c3)SP*z<Z&_3p&fOl%?0uJ;n;O7j;**)YPPKUgrnlEQ#=df2$-fqM!V`*;vw~gknY*jP%}"
    ")*HJbm#MyVwHkQUdhLGhm%5noJqspPJuBBG$Q7ki{R96L;LjqE^ouKf;JM7_9NlMjl3AeO07J%+w<M+E)<>$9Yb(fCFq}`sU"
    "hTLjbdR-Z6Em)Z>amM9glhDD@0kiKJV(4(cOBIC|7Jst*lkj&etkJ!tYT(|e8CaJrJShzNJNRS<*o5)?TMN!KLk8bC0Or4T_"
    "HpZ~=08$)NjzK>7E`rBhD^?LRQ7!OvSD?e22E%{pIkLnnIr4@mk4PX(%~36C5z`iZlBt&VC&qXEP={$Bi_%`>Bu<(R&)#Z1k"
    "X_Bq!*D9p`dVDk1Z4>iTvRou3d7YRUj>~5uSNXYNS?LJBmc3ID)^}+}dip`@^<z<yjEFa#Am_&Cy;YH%U4%p7-{9`P)Y96Ns"
    "ww6O+A!B$KeNq}!{bG!!)l{HeljP0HsoOq|XK)H28f@k~SCy%rRNSy`^Z@Sh^5d8Xa5*_gtI^whYi;s81cg+!Un^pE?QY#z<"
    "|X7mTa!KeRN%DOSLZ~a>ieeJBO#1Z;H_ocCasX!h7Vz_aI$wWwh-#4}a1rE8!H6%wHV-mwaA}X?N;C#*`CpjqdG#*tZ%Gk=C"
    "8@$(zDZ{rXoF)s*9WJ62{j0B^C2rCG1nE{$tRXtTo|6$Hy%MnNy+m)zy6*{c<lx7mSc8hAVmZT_aoS6t3%wL?i;HLvp^mti?"
    "do$6JHRcV@u8g~4hHUG;UFT--1No}T!J0h6JtEij9pz$TZuJzU_<#Hla5EihonAflftNBne2Y(rd1M~XzFFwA=SV)8>uDVsd"
    "1OVOY?AK$^iJ6bVpVcV$J;OpL6)BvopRmEfj5zn0Kx=!w7;H>#KZ)kHSXJt)R*8U>C9w>{{2RiODS@r#}sFtA$j0tIK(KBN+"
    "ggW0`?{Q#w7uuLOLvuoS1z@prcgu`E*Oho0?s3{%2QDJ^xLW})Ou)UN>3&@*%!NN?Sx3UHk5YH8SOJyf~|9t&NivVNC#J_zi"
    "rU1zLTPcd)t+3?7^<L&`Y@9Q26F>`ml9I#upp?~LqyH3I$_k&4F_X~Y7?nbQBy~Zx%zdAda%A~C#qbNFU&})Q~s_+in=tH@W"
    ")Kc#A_3tTP$q?A3EWi0APCO9{wZpFJi$Xe&@)}3Y@|fbw?@N5Um<)Jt+P8)lSV%dvlM3VeQ)pj>E*lze{piXr6ngp-akW`1m"
    "*sIhUfB*|SYN)c-`XLS6n@{6F}+@F##@=lrmy{KL)23rUZQwX#<Ru`u;@&)jvE1OL-k~Ft>%}SEV+>+duxQ2u~3iP$v+UIa#"
    "gsczva>Va!0V*&XfD7r~YUYc;4gx%-H>M{}aHoiYpV~vW*@~^CA5j)))HFVg&$}Z`0ngyn1*N=W)=4@^G~T;q*7c>9GShvgd"
    ">j+nkH(lDkWhrHH)x()jYp?}GbCL*o!n>#PNMC4!ZC9e;`OgdGi8;}4&ms+x${6ZsmgUkY5bkP|y0!;oiY@I&qzaEpXH3zPM"
    ">^fXCWnAMtJGcWgc*ukJ;&G7c2=XMZha94{|5`5!V7y^IV)bt7SORT|Vs@Mtk`@pRo(R%83m*|Ypf)Ze2B934=$`}hN9!b!a"
    "*+^;ZwFbTO?*UTf;W<mPzpjyKTE;cp_5TZ$FeJXEg>w`HLf;!)i02$6oSrx<9%by#5$~-b%O+hjJeO~W<~ADS8n_j=N)mPvc"
    "=xtN=Fa^X$Dil3zu&ztJ4DRTg9w-fiT9b51(rub{zhkY(Ag&S1<oCsqi*KTYMcr=`-d)Fn2t+-6Jd)0NZR?Eyn*{KnDRX9gR"
    "%}f<Qhkoh<qxXV_V%SOtNBX_zUe)=kGGS2q~+Tc0n=rNoji~b$Utl4Wv~!UnClp9a^&jc{)WFbvmW(1bwVqrurxC3BULL2_)"
    "@c*brxZr#^M;$D?-VYYF0`?@DUFH5tBb2TMUDU$j*G7tCX~N=KBgGMZpWM>uVQEj<-7S_h3A9su)kHwoz{Qx`Nrm$sq399`Y"
    "IDtKq*>&7o~PWb>F+8PmZc8%j7UIZ(^vDyC1GKVX++H*DfndEoN7z0w`O8Y;h0XO$E;q6Y%7MPCAa*IdXuK9dM9zH}iOq5_B"
    "ew#D_=N2;m$&g()Yqp$gs<ZnUH?4y+O!hF`hWDCnn{>G3;Ezj^7>T~3loS31hY(d>=0)Ar=a_)5K->1rUP#VCIUa)np=IULO"
    "YJ4r{MNgajk5wzEh`5DO@(qg(T*-H(Dq+L_lQi`Wu7hc_7B6g9&#C7J=6qprL*=~uo#;LS8M*Jytt>vK9RV~7<{Mi(EbW0qZ"
    "3a<z2}%8ieCO5f6<fr_&P=NIjLShfM>caAOSqU2J$EPdja%aDMKj<8RS_r*#wrc+>UVbSnVFRa<5eP+;z*jMsl7UH)N7(B14"
    "ggNZ3XFwTfXb@hv3Z+JRzzXZN>8qui59a?Yz2@&zpZfRo_$*P-?3zhKj2%VPjz*W|nNsbxEZ$p+8X)+24#)!kHc50;#e!-0_"
    "`ece4^_zCdmF<J&?RC-XU3?BSUz(7M=;EBOU@3PI34)1`+0_3_X;)Smo%=z0bDtWanZVwsoBPzlDlZPhk4XMKwh7$t>_^T;?"
    "okK|nru9$X+ag^XZu41R{$5&A$lC`2t^SGx&zd@qgmfDgE{tZ&{X9AyBV3KCK{c8;5E~?zrfU)vz<$_4$n1S<nA6q$1eKx3_"
    "Tv3JgQe5mg@s>j(<G(ApN!(F7zNgR8vd0<VD<<Q=~DW95*VI<hT+j%Nf#KEJEF}ikss^B)XwdEpM9*_SsQ*mw0$}4c>WL*Kw"
    "e4kp%Y)w=LU;L%|1`S`fDXG`gI77&oo$sxtj^NLCy%>qE|2LR@1D*&i6Cjpe`idJLiS4mY3G^N&rmFiPGJ<LR9Npxwj=&s+o"
    "+om#4ep)^xRtJ9_iE=M9rww0HZ2h^BaNQzF}umgm~SyEBoh>D1bFp}*ETkzac=h~EMN-?OLJq;M>8TMh-d8e5`|Eoimk(0@I"
    "lofkW+LsqA?8JeY;J7+hbs8>}=Qs6g{M$T%H+xOlqrZqIJ;+f46@Z`Rb(Dn7%nKk!(2)$<S>UwNa9`A3H9@$v!;L+P7t&~hb"
    "I*fq`7>4-lI^=XnD$$mhAh=?#4B_fXZO5!4hr|qq->I`wbBP`o$&plECg8DB;qWSJn2u`n#RH<Fva3{qXI@KF1)fCEImYU$$"
    "xZm0bBS%Zh2M<Pt0v9s#mV$sW1PHi<7p&B=kgQYdz%=aLHnSsqo6SbUkSz7!#i4x7jZfvc05!s|4K8qPr5z-)`#*k)l3V~@!"
    "w8`T$v3Q9*H#&$uRx_|3|vzqgD9)SrLqyq`7%%#>dh6f@B43<td_po;3mKR9)}P$8$GmixbZfxOD?NC|LDAd?AWfQTnjiW=%"
    "|4h;6-H;KeO7{<jx6OgQX($hU+liKvTup(EJ;=LP;ylu+A|q)q{>^wTfj+87>>%5Of*OI1<;HW8%f=H-?T5?=%{m#`mqC_g7"
    "P-gvC)Xz%aiER-{4rS~gdw6i(Tr}rx(Rm(y#-VW&c2|{)&>v5V{g~hLUJu9QbVs{9uJB(C2C-jLb0qiUK@d$4-Eq_~w^+l4J"
    "+6duxPwv@)vQ)CRFhf|U>kK5npY$N4EoXLYiR~f#@teh{E9pBcdr2bH+ow;M6OVQ0l`j9)k#k<o^`8#BzL{!s(lBpvKB;&p#"
    "Q%J$1#1wp)Zx;eq`+NR;x<AiqRCvsi|E<8nhW&g(BaBqdrpvKE?pYp8FNqU-9YEd=p;C@p+1eWA*E$KbPsAyg^3z|rPqXe#2"
    "oopV(nIBM?E%>E-mc$k3Q(c?z*koM_Dpgxo3g_2FRenE-!L^D_2*CDc@xd<Vv|U&b7@a?3#uqO3XD4VS-8%9(4+jqe7`ud#@"
    "jZaHO<tj{bfX;iBp%?ehmK-CRV^kT=#M9%9(GmM5#LfO6Ah+4$a|ZpB%zNN2;PvHcK;{<1^~x4o&bbT_XX04(>e2<ZJ%AzEQ"
    "I+Qi29N>|l;{Xez4mT~))x3^wsQ@x=cU*CE!ue9bi#b?~N78ZvJ7b@+I2Pq+P;97TVf*yMRdHibW_Dc76Px7z!KBe@W<o_xZ"
    "QnZZ@yjI^%_q?rwZAw;65asWV&eu8XEC{-ofy_SO_Rkqe-N9EPiYd&&n<>}4{#|YkTRa|F{O4&>>yo6?7ZCKnmiSupDMOcIi"
    "O$+<8tEABAv8l|JBrOh%(P0%l_HfPhi`?EZUE{F+>sLDs8%5-{;wnc0$t^q`0ca<>Z!<MjE>`KX?Nu?K-H|Ay&KC>xV+*R(F"
    "d1#VLC7O`XAbpNAOHsgGj|`-(^<axvJ|gaW7Jib!PDCI*L0sG0;`@qu&Kqir$`EyQsP0!Oeou<^ruQW=mha1xAEVMjxeB8Jl"
    "4xJ*Kotv7DH&9*PM@C@z^kr1%%iNBY6gn2}ruSK@BCvHqFOW6n8vys|vrZnq)C>&Q(}&B>2|icqdZhnF$;O0eCHeFYX~jFxE"
    "pJeh;X5a|f9`(>*E$~|@`ou|=iv@{$L`L+EXTFww88{$E)m3rMcgN;a2hHppJl?g}=EN({9FBMnlf%+Q0*Np&qPPaa3gLma9"
    "1T*<Al#E>8hPthO*tAAP(vbS7IS42ael_afS+}wvN5fP&)K1=m`=h2f$u33Se&k--;1<69Q5aVByml?6S&bvGC}=C;f78*9_"
    "xxeOJ5@e#>u}s#80vb<mDFzR-@)cpr`f@HQ{nU<i1=wzZM2V0>)eixPDxCYC+CCVr+%;WpB|EOo^|c}hhzQKGUs)$e@i1RcP"
    "1Ye<{c2uL%p~Uu9Kn5Y<YAAWlY<B6!i;WbA6TomB#_l)+8LHUM}@X>{IS}My`vo_oO=SH;>Nq%{aj`t<28g`<DV$EsT)*Jr_"
    "@0Qj_wTydTxa_Bo~V8YmvzeJ){E=QOf~wk8Dm(A|u&rZv*_@_d9?*vjGj5%uz%U6*66zC1OYxmx}xma^-n4oH3-Mg&>ewJ%("
    "s_b5IbPpBmodqKKFu9oJR$w}FzMw&~K$A$_MWg!`W3DPP7g5VMdT~nd2;>QMMl(7gw7zgzlJ?V6`OB<W~xT$g<*UH&BW{hbY"
    "+A~L77=Ke%m{x9LMLRuv47lt-OK&&=&__0HKVP`B-gwQ7xa_AkOfGxHcaAH0J*_Pot4Quwt%9$_5nS%z11bQ5g}@0%`fhO0Q"
    "5p(_>#-nj+)FFFp5d4Ky`o_UTk+OcYXuyH_N4Z3*M3ul%B;_R?e#dyW0wnwhnoI{#=6QdgZ}v@R{%nJz>-E9S+qK-FxOCTa*"
    ">$T=`+4qCl&a}1*eU3+GWOt4w)~DH6KrE#EJ$@#H-f)Jjd5Njbu7KdY>(rq<FFQ2RZ+{@7w$VdZC1sN&}{|J#9cLtJR58z)a"
    "Y$FT7^|Fz%0D?b2OL0%JzDMHO9D63z%`VcNm6h>+c}p+NIcE$psf5LB#lvXET$-+Z`beb}y2HfBEc!GrjwXZE&qL?*Wl&#_0"
    "s=8dJb%Zv7qTNZ768rv_^#3>Nk)!rL}r#ZbQd?Md|JPdqo)B)X{h<V%@w&VwI7}7t_H7AzfXk&H03LI4C><{1s?#gG}ww%~%"
    "PHGjnK;GZv%@!cAHU#u1J{+M9o1e-lHjh%JyakcVnXGG5leGkt>E1I}vq;zDSQ)$MR2D9L6mk3RWPMSPJF6g}!Q93>UurMc>"
    ">|GM_dI6sRRhLy)k~Dp=z%L^-I<h!8h^(o(ot45aH+)`c-is8`A!)by(=RPa7V*MJ9naGi=<w#L%?^aF6X4;*VAoTo(4x;yP"
    "FL8G~<IwZw~vejtu}xZ9BLY>h=n#qNwPf)E%;S*>>ayK4p7IJ&0-+xHG8Xd$;s`o<#m2Y#I2-fq&gMWh%VLJ0UD;swpx1P+j"
    "u9^f&|o#vTSpc!m6z{&|hi5psoZCiJQ2c7lFYR^c^;#%4%}ym068<2}DtrOgu(OHSh^PX(>d0c1qC$AXuSd~?rj9=}^z_ygz"
    "OsM&L}f^2D2JV4<d9T<~zFq1a!E$@Y{*QRtL7{d|XK-c=XexAgc^<9Cb0v0860oaC*F)BOf(qhQq+=a7DZxl&5t7=3vH7A&h"
    "2w3LIH>RJ)oi5$@-u<DZm(0Wwj@`oHZ69}8!!8#P9+X$3U;5o;L>whVN_R*~{K~2eG$-_C+5Zls$9u<?*6T%duq7F{QhsIo&"
    "6<voYb%^gPkfVFmIi@7_ljvJeQUPZK9X5sAdeEPbYt~(_ql8Mrbewx=$48mD4Yhceo22*yIkc;lAk=j^#PqMvfuj1KU)xwu7"
    "}14w2K;dB-r_D7|n5novlvf$8yLn$yFCjo0$m|^=}vj82%a}YnWqrWzj5@-2*0ZDWlgFB)XUbMKT>orTl)RvVC$D#@|Ipg>1"
    "kg-QQk+^mhf9qY}6(p~)gnkc{}SX7a%6nHHHBZ8Lb|{+)@2MnNJvSjn`$W#*csNV4D~u;W$JG446hcR{0uK}U;N!F&!OabtS"
    "I9tQ8BZbm>7aOU2vi3+5KvxgOLJ3I8Y&By#gPQp7d$`OKLUYe{`z_pq`!cBo}K6FjKR}X)CnU1S)H|hI7<jRe2z!jbJFKa%p"
    "&i_<)W0H8m*@?;tzD>1Zjo+}Ir)gjRp>Z2_>IR!F;zl*;mE{ZOw4I;1ah_uXiR8%@<rNc;yivP%>wkwRLgh-7P!nsE;T+?Ei"
    "(<i6R&eLs5?Mu##c@<g<4gxNd;5nETuE3EHVFnZ<T&~0@(`j_+Fpgx8x!dW8-CuOa5GdaLx@+Co`h&9`Z^N-8bk%({I|nJcr"
    "wN2OEv3XI%{N>ET6@=D>azexE<7tu5pO0#-d$mf^tTQ08Oi>3CrSV8n*e3(km>QYUMW)ev)x!w!N6HdfvTT>R%RNbh#)*Mr?"
    "R)-QvBmbxmj8!~VFGWEV@!7QM1uY_K+bG(yUqF-8NnZekB`BHADg(jq1kE__)@)e*FNedw%}CN*{f{x(qG&7+cOGsE(&^Zc$"
    "7QX(&?3-joja~-<_A0ws4r^vHlJJGzepRS;pvn4Pl3FB`x>9g?!#+w73v;<pz%KV){e`SvJ6d`+8A!vE701Po2*sqjb%Lo7j"
    "`j)*MpP@7fR=7>%tx*Uoob6^86smEQgTdiLufrMFb;(QvCo-IK{#LBt*ge&9FQ!XUpVAI&mzN(F#*)98IfwYbK`%Gzg0%YK_"
    "9X!ddzlZ%V)QQ(e5(50;}<fU6cm&CyU<@yUcm1>oCJN@Q=7P&`~eyr=#^++r93OOInox_=Xuq)e|;8g=S<O)AK|0@W>%&4Tb"
    "FZw)S*f3gTFnf<8x0GnK3Z^<!$>l2@^`q^-p{q9JyQvOrJtR_hscjC#4!y1BL>FtULCs?q0Z?S<(1*j(BEWRm7iyf?BpO*OW"
    "^#E&q+mVg6kS<unga=G&{39b&o(drNIUN$}D!eS9LQJH<I|D?7xMt*YILXx+_H>ORI>&c%Zc?H#T-)O32Amq6Kh<UJ)6Q<J{"
    "nM8&^kcFUwnJUAX+54_?s!jCCl{`)VOtbNa~YQg!LvOn$cwshy_U`88B(2fo{GbptoDK!3*)s(LitGL6n7=UoS*D*nVNOL(>"
    "hT!YJVsXzuf_qGa&iUbfVTym6nQ5Duxds_-a`-m5yIP5@q}~TRI^UIH#<K@A>m5{aU{<#LkXx@(;7XipR&H1Mfjy~40Ppeb2"
    "-keKH85{Un$dFm>WjGHZ`i>-^OvF2NI!W3hagP?6Cri9t~sZ<5^QyQKJljN%3p2~cD^x!HgEE<{4p4=%~r$vYH>45+i%&`8s"
    "hZ|)^E?YUB#vWP#^^`HnuCAOK&34K3rHHI+XZx0#mrQ_utB6OEC5-Q*8iy+IooDF2Fsc+Py&-mlg}_U%l>n{|*t=u?G$!8xj"
    "NwgC%S37M;6~Z)+^tcf(|K*i7g96^&~uHr@9FNEE|lXcJw^4Q;V=w-nVHI5@>|*4x^SUX>asi08dyO(HMLqtzqLh09;GVb!6"
    "Q;&j7qG3gA~p_`z#Vg(BeP3}rjKUd`DwR4`7F*6;!vXJ)qJuV!^ajU}cj(73;UZ~k<<(EB5Y;9Uc#gda5p&yAv;c}_=TfT3="
    "LlOWn{qk^}gi(aT7_@M!^KI+O=8>qig^z6)vlsK1T!|~M^4a>NMf{D0^VJBp9Oe4BWi!)l-Xj)L9lU(e%xRbAry#%L{QlbqI"
    "u$aG4c^X5<zu`(skoLSU6)<jACvR=r5Ui{7c4=6EuMh!DDt9we&Eiu=eT+_hN?K4I{O0pG#UInVC8DQQV~BocW7Q-)MoAmeg"
    "E4JF7Whj^UUn3u_S_g&s_a#Df#Jg;{;G;kCNy&8tOT45VUskVzg%$x-Qa=!f_HfIY&{hjIGTb2htaHV4GLecY86zh<j@HlcJ"
    "Vg2-nG0)^K(Feg-PrfB6G{mCD}o?(yoQgr<T1k@NiUrm4y!6`(TG;!xY4L%eHysedjohTPcCYIO_+C`wXaOk@u^{=fFF{h#U"
    "n{X5)J6m{34a;UqzlVd{2xsy8zIZc>}JB859aW)h8or+Klbu*+n+fvSEs~lD-W7rBa5yP6XjhWf@wg2M#!{_?({oDKXxE|N_"
    "dS0*R^?crrnL1g;#-|WDa^Qsth~3=g=lelKK?ZU?<E!HYK8bgSIZ&dS;y~nMjCaWl3_`orEvHh;x%+^@V(Wkdqj7pm)>0osP"
    "E4(^qk47*A}~L*WXj3Y${J?bwFou)LY^y{3nzF9J**2U_ECAX@>LkMVN;B5{xJK8)TgvF5E*&e8LUb_y*s&ZT@V54C|P)!X%"
    "y~r@AIjut3G{p-P`31OdHQsRaZ-Js@S6`I$yn@o}$&Fc7N=jam}GW)1vXd8#+$PS|eYtx1Nx>zdT33nEP!pBI$+8k0gr9n8;"
    "=6nO|M??Bg8CY}{4TOXE4#OKo#bC5W}}-DISM_cb+S@da}!Rc~-T@b3iWEI?jB<43?YjWYpl!15G&N8G`(8v64W2ZBytis>k"
    "F8`A@<agXkAiplg^=ybXNVBL>q<zG8hC}Fhzvdr;ddDVOvTNNF*vVRmVB1Y@ZKK70*MG@XoBa@4vw<eqx68dc3wy5KaImxs*"
    "FtOkC(L=?c&!#Cn3*=kzuTdbl>u-=W<XB}iafF+3Qir^0QN_VyDIFxM7OTVF{%(fg91e+`UyzX5dhmJduAxTw7C7v5>xIAmO"
    "DnZt3u-olCK1}uDSyMsaLv4LmbvL*tKEYrWP<kIQ{HHoE-1<NY|{5{E`J55;{Gh)h(Q?E)7JLB5XJV^0@eXZeKKAv{@YD<l1"
    "x+e8nQgxdF#>~IwF?xhuxw*em!;4`F`;{-Mn8QU2K-kBt<*jgL#JV*)QY+S)91c;YV5s{t(;YFi%q6@4J*1j!+tYcE#{6`BH"
    ";JL17JGn%mpullUUEl^*Y({POPB;kJd4vgfARoA2+-<xKwCpF<EcRq@K(_W`!Sb2|G(ZCjA~GWvkSO#aTwo&fzRjFZ~ns6xF"
    "}8StEw%ecG#!vcji1R#y@*%hets^x0UOU=U7=#Qe<-$yG6`jOF*QsxISJPQgB?=KiA#Xi17gE<4f;j{d8R)MH}vpaPD8ED9W"
    "iDz`BiQ~aGzUQsBYasJ_rG=CPS|hvjGBd=_+Ac|$xQpe&G9gzRdWz5<(HiP8)e#RA?4lM%`6KC<UZG!+bdvA#N~%gzHU@VE8"
    "X;jSml@9%b#!O+*fS9BSIRlA$$&fsLe(9<hsBFlH|aA!)n^I}du@N({PnUBYIVMKQ?eE<jqk)KhXp~l&ietDDA_nWyGS^9!j"
    ")c8`LMbI?OfKVA52*PY7VUjsL=O1pq^|caRmaWfBq5aP?h<{qy6ZrnqCn>v=m{{694`QM^G}1U=<xZboQ=hicCFIg}Jz6>O&"
    "jHdz44nsoPGwLU8&nI0$n$?y5Saz#&Q{p;h4%>bqPmi_SNvQQ*U#K$n#^2B`M8xmlO~0_qJBoNYSut17^8k=1UtMDSOEI2cQ"
    "{nQf@7WHnUiP0cC=jaFzer-UW+7ClL_9ZO*vN3jLAqiE>ntT9sftV#1WhU-@IyVp1gW9FqQN2T8A*cOK&5<cHtNajY*j~C$K"
    "a1c$s^$jbLz(H{IUER8Tr_B(u#YHF~?CL>n#nJ>5-#x?E4U}0HecUi$Z(=bYyx5ROyS{;>t$Z!*XWm%4Moq}hZ^0Rht&v=QV"
    "Qoa)uQCp;UPmSk^WUx;tx@#(0{^Jz^;Z#nd*pm8U9H(o$1$>TB6slU&g7A>TX$jD1*`BO7UWE3^?pOX_)?U&S8w-Ihpz#z8O"
    "ZfBlmwHL&3}(jO)~r1E#tla3Z=_<R9Q-jjGSNXB`!)mV<{^QmzSulTVm-2b=%n2Q0Bl><r4wT;iDIqrV`co*DhGNj-84_<Ve"
    "XZJ;1gI2CyzD7BC$?4$_ac+XHGnf$H#MGE6=V%Tc)_?b}SkX=4-4-x4-A_)7kL-wAj$Ue}p5!g0r4Q2%G)aiL;%0zD3xY&}("
    "Z?Y{yuw}&VqCHfTTf^(RmguSRYx%wR|4je;MR_(C*#7T{!lL$hOsob6TlVSv|b8@skw!gs8CB{IoM7OqK)xUkgAxx#IJ~$ZU"
    "K^z`Fve>RKS+NsT*C}X8scT@i<pAcYZ6W`ZiSd&V<ya81zV6qscYGG3>P$LGb1*{Xw>!wvSjrXl;{?v+wIt-zYgE9#%+T?c$"
    "jD%k?1gAfq28IexBBvm&(E`rLTcfuxGu2X-|IR@Zn-bU-@T~7#8MCLVHkUF3-2e_VpZ<~)eANE`5L8gPaxkc?3j9*hH^^8XG"
    "1#vfSEz!8e{L7Fr4Nc9dhg?>+c&{C&%y*vaR6irmGQPz0=QI#O?Dat7$@0SV9r$Qx&P^9^c!@1u#M3f|PoE%e4iBwN3c%iOJ"
    "!fGriKB|HuUc8C!MScaO=SPu&!g)eUcf6!Xg0?iC`p&UxXxm&E<pP4-yx*UQ?-&6SF+eD2>1c{j6GsGtB^IEHfy?jR2v&c%("
    "O6Czn{#9PGzW{m6n52H1hWQ;~=K}a7Qit>FEa)6X;DH{Q)Top->D5Nd#0X6|5_lu$_*WP+<0*t}e=ac(r75D++N&2(vW0UR0"
    "8c?ef@UIDeK*cmtdLktcJ))Cg9zp$*@*b+NmB4*)d%CjS^8IpE)<#{=LXbn`R8FG$Ou(74fRC%J&zfhWCcfblxt~tt9k7u{0"
    "CsQ$9vVZGm|<*P>jj3=IjQ7IU97>jU4s?;1;*0QkGB*nrYO1h=t)voA0O=}=e^ytT-r91eMly8x!3x1P(zt6QUoVI#ZosmQ^"
    "4<Sqrnn1WusFs2E-WhZeu&UwV!@LW6?+lmZN@8B=$K^z!lCl$1$PxBOi)s{<U&hroLdHPElbEBDA=1r`gmCeJ@Dvg}DB$s?|"
    "9@Yi2p+(SNIKGmyQR6V5!ZCRcz3V)#~t{Ig5(3AS%2LV#|#FGZjiP2_&o|8JM&OqS_!J$d`p8n;MTN7$6V_r@jKaW{YK(l<U"
    "~NYq-@@V&6&JinBQ1bpYfj%aA$ZHb}PJ74S42xir(qN>BW3}7m!(NQjA<)B+M1LG(cbRbhOES}_u1M?hg*}!7uW}o#Umx#RC"
    ")sxWcua9K!>_mvxW`X@<<d|EpsPuTPJijS4E^(+9;1P191;^}<xi{#jY~HF;<2^8ZW1*#FA_k=kS+wW4xn=xx+-B>ZOU13qo"
    "ZxgeN5Num>(f(z?%L_4pML{<uwROMq6J#azM&%blcQs??#`lG(Rlbeg>$Z$>iEc$k+h~)?;+UC6*1P?=S%vu)ek1LCToBxrm"
    "#T76U^rbfQN<IN%v~_J4JcDXy3P?*LX8NxIo(%|L8bkU!&5DXM6~6D1^mB-AC*=<0R;n|1c!@wx-NdfHqm?S;RgYkj!p&Nil"
    "%lyWy$0IN_-@+KPec`RfX{l5=H4gOSs*7I6g_aw!tg>_m8?Cw;J9g4t}XgPYOHs@Lk)qU$#!RDwY>B)<b|)(UcWHivY@L+;o"
    "8j(H_~dQy>?obM%OI4Za?hei#Dhu_UZ(YHtGk7nN4Yk=X9@zI<MXY60-fA@O+`8nPng!lsA39Y*e2a#;mif6tbtb7#Ov>WuA"
    "P9K3j7Cj|LNF~yhy>2>M%l4&b)`?P)bSK(OQ%yqiRMXrkVaz+_m^Ba9Tdz;0XPhGitN=R<l@y>yz5_NBvF(^%T*Lvl9hHKV6"
    "%FL|`|qAcE5qolK#M)X^EOht-@?l70QWCp*nOIx6zlpNKvy%b8$A4q8LjDI>@EBR_-~9kEr9vYz@{T4=wjMWHY;4nza8+ydv"
    "=gvdc`a>yX{aXw+Nehbpc*ovbR|QR(yM+l~yDG*;QiXE*Z>|d_H;HYVvtsUy{=<ioLs#^Y+oYbrYv0nn56cxs<-6EYiE~wM4"
    "HpMiBpr=57(y1GOv6<C^<U6Y8})*QJ&izX05<Gt3nS>Ex~2<2rj-%aO&f#HB>#M1qLUQIqW_UkzXp_0Z@&E@*Ck)y}QLKE6#"
    "pHp|v1Rk>z=X}8^F0-+s#=r;b7Fv$p<c-WD6+^z~Q?YdikwXpJKQxUMIMv7mu+~%+V+oLO?59kKOQv{t(rO`XQlHLh3`aS)8"
    ")G>fvXLR(X=(I$89gi<Ve}fzw|D5;`|M5u1PSj2P_jN3v`hBA+Cxr^nRP_miow>L;nCrb=Hq~VOqBkzQ^%e~a`g=R?XIkT0o"
    "nJUzJh1Tx8Dhn=^%q)KK579IuQ1VR2cnX)iN`d;uQ3~p?v7O%4W4S7&WyvpGRzp4Z?eyK>*4FD-f#S4NU)43ge{$~Si`B@l-"
    "+aS+`Q7eYJIl~L1%3Q6VO8Z^1QITSILqbvwPUbU@*@6VesS&)d`3$)h}^FWxiSEAr1VQ!OJqnFx(^LzmTCh{|5N3npciQPO4"
    "*W*xH<LrMx`3+x*JJHPCo{)71VC9+=5~)WDPV`Hq&2<lrDXW3cL6{#slLs6%1zF=1C?6qEbUe0z37Hij39X*Be2G1G@hc%{T"
    "wVSz{UL`eq3lSs-+_O7Ft$4y@_Y3MkmjR2t$hEY`6SJT7fk%gYRz_ljhCNRIG<Lo?D4ddCR%S<fIr%El4`V_~7t}c#t$FZp9"
    "qIbe9-mO`l9d)CQQ3Iu>Pqbg}Uyw9Xm%^7Vd|n<CnB}fN_t?-k56U0t_EZ0NENLcVAR3etvfGE~KVBPD#5;^|6}jL<1@>&?Q"
    "bidDR$1StzNk7xT|w?I#U=Llw^g6sd4+L5;)O4Bk8U79xfACrRsZ4W#=l>ZF*)FKrlrr@=9kT4{u~4B5fEPcS{7o{91Y&p-T"
    "r9i_O<%ML;ona+Y94qj5v7GexukZjVn{)`+CVR@Ml5#H&dnzOfVPMra+iYhm8)!y1}3O9h7&VjN6nmE9E-bE#ogxAV@Eu8@z"
    "!5`%!E@FthGhgXAAJq}Y*TUe|kRk}FO#(-Irx=2!XjLyS=bo<mJv7dJa?f<W>=@ah5I3_$+DhkHftfQy3PufqzyW&ZsPmT~8"
    "hHoQT}B_@^REYHW9jjX0HR_c^M!MDmd8#>5znufGsU_sN&lTbg)2a4Qgv$xt3&JxA)cu4AR_<+{CA;@B;0`2xA0Pp-dRwS(y"
    "rnUncHiBK5iE?9bYj>Uts)Gk~1@UQ$f7PurWZa=g28=N30kQ3mfA)@z51`kYs&>i9!WN!h=NJ&!pj8<j?5OT`^MIl};cOo|&"
    "%?!<kkU84tDZwW-TGPt%hMIY?{(DKaz#d+q{;0At=c;i(#!iV!ayW&j)+4fwj-7eqmxuo(jEMYXBq`vPYzjRo6!eMNLr?F{*"
    "aTC^I*qeri!aUk0tLhSBazq(<rbt%sQjoAWBGKCTz<)sEs}=lg2siL$MWv=c_I?=H@CY63VPXG=S8~M+2syd@smyY^+N7`sP"
    "4G;L}d|juWY>%~<%=8N)ria<r9k%1Wjacyn4K!-4_lEwAE`;`ulIMiB!h%7TgDg|r9;VO289?1~1px&P}xav652xfDvu)~?v"
    "=YI!qJI9sR==D*Z<BI}AqR|5BRp6|?^jrxXhZX9;4nI+?xf)MmU9)nOYf!AsE8zs;HU)GcC1u^ZvUsnnGxzs<?WJj{8WC;?#"
    "Y%kFrqirSe9l@tpN{or4j-&v<wpo+r)G(SIyS8bT36Y}gXn<c&92Ja*0sD+rgn;xND@7#dzr#B7Tf>pU76)x6N*}03H-*&PR"
    ";2J>Rfg24ly;nn5P3iN)b){T!d*F~oq^?R5Z|r^)@-7B$%Wi$!VKHY=kxeQQh&uftDO5_Aenta8~Ef6CypLFd~Gj?Fy0tKa="
    "#xXI4^E56}8WCL=359Xnb<5WsQpdi<x%24MO(eKv5+duz)$dsWLD`VnS>BzWTffnU7Tu?7N>>TD8$|Zc>jdlagg~MhTGIiyR"
    "quTt_BmMrZbeQi^yv@6w(VC^q~5VUD4;8X{3wM&`H{s$(kFWH0I6?O}GLw!Psjy|2w$;K@`erl6&wfbr4jnhNpT-+P86-rEr"
    "CKQcJOsCt}Sk)rjAq|ZZjzG+#jr^C{g_nbU&J1di*iZMz(hcwSlRWTnsVe-cQi712+yJELG;^|~DnK-i?Et!iR@s8okye=bM"
    "9Pn=L9e!nBX3n&kcN@A4gzS5mzsjQ3y*8&rI=gra3uR0b1eU=zDz$RsOX*LVT6ANS3{va}KA-(v`cc$jfZR!horVH0;yU9jE"
    "hV7=bq?1rZwb(&`~Uo6O4gFGR&pY4`iGBQ9y+VXaCdm;cptI`rfLL``?EY9i(HIfuct@?)Yf`dX#=GmgZ()Dk_c&gLPi^H)C"
    "0EsUU{53W~c4u4G;Lyz$UdJJ4X5*&DZh^3AgRS<sViXJCq|{ipyDb1Ie~p`-nfExs1&Qa-S7uNft^aVblEy*v;tgZ*KjpQ6b"
    "w)H-8A3r3}2ZTpe+TuTSLaU*o7JWC+T>>wKi#Qq>+OY|Hz0^sHd#a@=bdpnIGCJ3m;17eQb?F?&KVzsi9|pFqq#*2iiF$d-%"
    "7qlsOK#WkC5=tpk3z6WJimY1ta;{Bj54*AAQNvEG}PN3v3{foL$>rkH+veit}69~K#b`vsdQ`%Fqg};tA4}_2Wls!6M6X*lW"
    "f^XW#AA!=a9%MB`LH%vpx>NbGM=sA2piIyAsP~lj{b6wP=}uO#MhR|l4JR%`aJx7NT-d)hv-zH5QR(4Ung&PJ6xtkKAzq2+p"
    "?yjRZF5AeUcQiA6Q7qeVzORPI0NU`TzkqlY7(C$BMCqH#z1a?wllEzs)5UG<GK@1Jjk|6&t_G;3iRD;`2`)>TS!UoPU9g+O-"
    "unJr+?wc3{WIVJai2o`M$qb?grQ*ER$37VfOITfwwZ-zjPpe8jy}dup_!P@KZ_^CDsY9J?&H1du?B?ezjoOP|V4SA*0zPs>7"
    "Iw+iXjclu2eXK_uYxiasJC>~$kWctqItnD;N9uEr1Rum}Dz0-B&b$NZZ0<b6DvGY^kw@kDjW2IyA0F88zBkle;khMOQ~lCd3"
    "b_JkyxBJ}pd>PxG;s)&n6%BR|*4~z<5`K-uzL{}=>&)7x=t~>^2*$F?n`Lv2lIB@2jtv;Q8G{@$Rwt?|n`jY${oJ{WR`Ym{H"
    "yj8){EsKO}k|HGh)jw*ryEV&BDlNpqLyV1gDb&Bo`|M~jaj$!d;$qyebcoJ1S?IEplQRt$Z>;W3V*F?tZwecJ#-@4K`4}#kA"
    "QoJ}pRLU0r?*cQY3G@-nSVy9?`Noj*FOx+ef`f$9j28q0g>6Jy(vu%!z9NQzz&^8`nN`Dmn6+SuL#Mpjc?iwopWWe_iX)DW}"
    "ctgs-KoP0ZXmFVLB=bLGFLN9}2G4UkFBM9PhvGq&=!73dyz#eMy#AKmMQ{sB>IA(arxYT!U-ltqwq)3SG6x9^ac=wq5Rj@xS"
    "<A{4f4r$GadsF)}*+w;vz6f8CaSxN^z$BKCYx+W!GC2&}R"
)


def embedded_logo_data() -> str:
    return base64.b64encode(zlib.decompress(base64.b85decode(EMBEDDED_LOGO_B85.encode("ascii")))).decode("ascii")


def resource_path(relative_path: str) -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base_path = Path(meipass)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path

# Curated executor catalog — every name below is checked with identical rules (paths, BAM,
# Prefetch, downloads, hashes, full-PC walk). No single brand is weighted or prioritized.
EXECUTOR_NAMES = [
    # Windows script executors
    "Volt",
    "Potassium",
    "Wave",
    "Synapse Z",
    "Seliware",
    "Madium",
    "Cosmic",
    "Velocity",
    "SirHurt",
    "Solara",
    "Xeno",
    # Windows external exploits
    "Serotonin",
    "Severe",
    "RbxCli",
    "Lumen",
    "Matcha",
    "Matrix Hub",
    "Photon",
    "DX9WARE V2",
    # Mac
    "MacSploit",
    "Opiumware",
    # Mobile / cross-platform
    "Delta",
    "Vega X",
    "Codex",
]

# Extra tokens commonly seen in paths, prefetch stems, or renamed folders.
EXECUTOR_ALIASES: dict[str, list[str]] = {
    "Volt": ["volt", "voltexecutor", "volt.exe"],
    "Potassium": ["potassium", "potass", "kpotassium", "potassiumware", "potassium.exe"],
    "Wave": ["waveexecutor", "wave.exe"],
    "Synapse Z": ["synapse", "synapsez", "synapse z"],
    "Seliware": ["seliware", "seliware.exe"],
    "Madium": ["madium", "madium.exe"],
    "Cosmic": ["cosmic", "cosmicexecutor", "cosmicware"],
    "Velocity": ["velocity", "velocityexecutor"],
    "SirHurt": ["sirhurt", "sir_hurt", "sirhurt.exe"],
    "Solara": ["solara", "solarav3", "solarav2"],
    "Xeno": ["xenoexecutor", "xeno.exe"],
    "Serotonin": ["serotonin", "serotonin.exe"],
    "Severe": ["severe", "severe.exe"],
    "RbxCli": ["rbxcli", "rbxcli.exe"],
    "Lumen": ["lumen", "lumenexecutor", "lumen.exe"],
    "Matcha": ["matcha", "matcha.exe"],
    "Matrix Hub": ["matrixhub", "matrix hub", "matrixhub.exe"],
    "Photon": ["photon", "photon.exe"],
    "DX9WARE V2": ["dx9ware", "dx9warev2", "dx9ware v2"],
    "MacSploit": ["macsploit", "macsploit.exe"],
    "Opiumware": ["opiumware", "opiumware.exe"],
    "Delta": ["deltaexecutor", "delta.exe"],
    "Vega X": ["vegax", "vega x", "vegax.exe"],
    "Codex": ["codexexecutor", "codex.exe"],
}

# Verified sample SHA256 (lowercase hex) -> label. Extend in code or assets/executor_sha256_blocklist.json.
EXECUTOR_SHA256_BLOCKLIST: dict[str, str] = {}
EXECUTOR_HASH_SCAN_MAX_FILES = 15_000
EXECUTOR_HASH_MAX_FILE_BYTES = 120_000_000
EXECUTOR_ACTIVITY_RECENT_HOURS = 72
USN_JOURNAL_MAX_LINES = 12_000
USN_DELETE_MAX_LINES = 6000
RECYCLE_BIN_MAX_ITEMS = 500
RECYCLE_BIN_HASH_MAX_BYTES = 80_000_000
FULL_PC_SCAN_MAX_DEPTH = 16
FULL_PC_SCAN_MAX_ENUMERATED = 800_000
FULL_PC_SCAN_MAX_HITS = 3000
FULL_PC_BINARY_PROBE_MAX_FILES = 12_000
FULL_PC_BINARY_PROBE_MAX_BYTES = 8_000_000
FULL_PC_SKIP_DIR_FRAGMENTS = (
    "\\windows\\winsxs\\",
    "\\windows\\servicing\\",
    "\\windows\\softwaredistribution\\",
    "\\system volume information\\",
    "\\$recycle.bin\\",
    "\\programdata\\microsoft\\windows\\deliveryoptimization\\",
)

ROBLOX_PROCESS_NAMES = frozenset({"robloxplayerbeta.exe", "robloxplayer.exe", "roblox.exe"})
ROBLOX_MODULE_TRUSTED_FRAGMENTS = (
    "\\windows\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\roblox\\",
    "\\nvidia\\",
    "\\amd\\",
    "\\intel\\",
    "\\microsoft\\",
)

PATH_ALLOWLIST_FRAGMENTS = (
    "\\windows\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\roblox\\versions\\",
    "\\roblox\\content\\",
    "\\microsoft\\",
    "\\dotnet\\",
    "\\nvidia corporation\\",
    "\\steam\\",
    "\\discord\\",
    "\\epic games\\",
    "\\node_modules\\",
    "\\cursor\\",
    "\\google\\chrome\\",
    "\\mozilla firefox\\",
    "\\spotify\\",
    "\\visual studio\\",
    "\\valve\\",
    "\\unity\\",
    "\\unreal engine\\",
    "\\obs-studio\\",
    "\\overwolf\\",
    "\\razer\\",
    "\\logitech\\",
    "\\blizzard\\",
    "\\battle.net\\",
    "\\ubisoft\\",
    "\\ea games\\",
    "\\rockstar games\\",
    "\\adobe\\",
    "\\zoom\\",
    "\\teams\\",
    "\\slack\\",
    "\\notepad++\\",
    "\\git\\",
    "\\github\\",
    "\\jetbrains\\",
    "\\python\\",
    "\\wsl\\",
    "\\java\\",
    "\\openjdk\\",
)

# Cheat / hack filename hints (also applied to each folder segment in cheat_path_hint_labels).
CHEAT_FILENAME_HINT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("cheat_label", re.compile(r"\bcheats?\b", re.IGNORECASE)),
    ("hack_label", re.compile(r"\bhacks?\b", re.IGNORECASE)),
    ("script_hub", re.compile(r"script[\s._-]*hub|hub[\s._-]*script", re.IGNORECASE)),
    ("roblox_hack", re.compile(r"roblox[\s._-]*hack", re.IGNORECASE)),
    ("aimbot", re.compile(r"aim[\s._-]*bot|aimbot", re.IGNORECASE)),
    ("wallhack", re.compile(r"wall[\s._-]*hack|wallhack", re.IGNORECASE)),
    ("triggerbot", re.compile(r"trigger[\s._-]*bot|triggerbot", re.IGNORECASE)),
    ("silent_aim", re.compile(r"silent[\s._-]*aim", re.IGNORECASE)),
    ("speedhack", re.compile(r"speed[\s._-]*hack|speedhack", re.IGNORECASE)),
    ("flyhack", re.compile(r"fly[\s._-]*hack|flyhack", re.IGNORECASE)),
    ("noclip", re.compile(r"noclip|no[\s._-]*clip", re.IGNORECASE)),
    ("cheat_engine", re.compile(r"cheat[\s._-]*engine|cheatengine", re.IGNORECASE)),
    ("dll_injector", re.compile(r"dll[\s._-]*inject|injector", re.IGNORECASE)),
    ("esp", re.compile(r"\besp\b", re.IGNORECASE)),
    ("exploit", re.compile(r"(?:roblox|rbx|lua|script)[\s._-]*exploit|exploit[\s._-]*(?:roblox|rbx|lua|script)", re.IGNORECASE)),
    ("free_cheat", re.compile(r"free[\s._-]*cheat", re.IGNORECASE)),
    ("rbx_cheat", re.compile(r"rbx[\s._-]*cheat|rbx[\s._-]*hack", re.IGNORECASE)),
]

USER_FOLDER_SCAN_EXTENSIONS = frozenset(
    {".exe", ".dll", ".txt", ".json", ".log", ".bat", ".ps1", ".msi", ".vbs", ".scr", ".com", ".jar", ".zip", ".rar", ".7z"}
)
FULL_PC_EXECUTABLE_EXTENSIONS = frozenset({".exe", ".dll", ".msi", ".bat", ".ps1", ".vbs", ".scr", ".com"})
# Kept for backwards reference only; the actual scan now covers the full home directory.
USER_FOLDER_SCAN_SUBDIRS = ("Downloads", "Desktop", "Documents")
USER_FOLDER_SCAN_MAX_DEPTH = 16
USER_FOLDER_SCAN_MAX_ENUMERATED = 600_000
USER_FOLDER_SCAN_MAX_HITS = 3000
USER_FOLDER_TRUSTED_APP_STEMS = frozenset(
    {
        # Executables often used as disguises when dropped into user folders.
        "discord",
    }
)
SCAN_WORKERS = min(24, max(10, (os.cpu_count() or 4) * 3))

# Populated once per build_report() pass to avoid duplicate full USN journal reads.
_usn_comprehensive_cache: dict[str, object] | None = None
_roblox_logs_cache: list[dict] | None = None
_roblox_logs_cache_lock = threading.Lock()


def _reset_usn_comprehensive_cache() -> None:
    global _usn_comprehensive_cache
    _usn_comprehensive_cache = None


def _reset_roblox_logs_cache() -> None:
    global _roblox_logs_cache
    with _roblox_logs_cache_lock:
        _roblox_logs_cache = None


def _windows_user_profile_prefix() -> str:
    if platform.system() != "Windows":
        return str(Path.home()).lower() + "\\"
    return str(Path(os.getenv("USERPROFILE") or Path.home()).resolve()).lower() + "\\"


def load_executor_sha256_blocklist() -> dict[str, str]:
    """Merge in-code blocklist with bundled JSON (hash matches survive renames and folder moves)."""
    merged = {k.lower(): v for k, v in EXECUTOR_SHA256_BLOCKLIST.items() if len(k) == 64}
    candidates = [
        resource_path("assets/executor_sha256_blocklist.json"),
        Path(__file__).resolve().parent / "assets" / "executor_sha256_blocklist.json",
    ]
    for path in candidates:
        try:
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ("version", "description", "entries") or not isinstance(value, str):
                    continue
                if len(key) == 64:
                    merged[key.lower()] = value
            entries = data.get("entries")
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    digest = str(entry.get("sha256") or entry.get("hash") or "").strip().lower()
                    label = str(entry.get("label") or entry.get("name") or "known_executor").strip()
                    if len(digest) == 64:
                        merged[digest] = label or "known_executor"
        break
    return merged


def file_sha256_full(path: Path, max_bytes: int = EXECUTOR_HASH_MAX_FILE_BYTES) -> str:
    try:
        size = path.stat().st_size
        if size <= 0 or size > max_bytes:
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def executor_user_hash_scan_roots() -> list[tuple[Path, int]]:
    """Hash executables on every local and removable drive."""
    return full_pc_scan_roots()


@functools.lru_cache(maxsize=1)
def executor_name_patterns() -> dict[str, re.Pattern[str]]:
    """Match executor brands as standalone tokens in paths (avoid 'Wave' inside 'shockwave', etc.)."""
    patterns: dict[str, re.Pattern[str]] = {}
    for name in EXECUTOR_NAMES:
        inner = re.escape(name).replace(r"\ ", r"[\s._-]+")
        patterns[name] = re.compile(rf"(?<![A-Za-z0-9]){inner}(?![A-Za-z0-9])", re.IGNORECASE)
    return patterns


def cheat_filename_hint_labels(filename: str) -> list[str]:
    labels: list[str] = []
    for label, pattern in CHEAT_FILENAME_HINT_PATTERNS:
        if pattern.search(filename):
            labels.append(label)
    return labels


def cheat_path_hint_labels(path: str) -> list[str]:
    """Match cheat/hack hints against every path segment and the basename."""
    normalized = str(path or "").replace("/", "\\").strip()
    if not normalized:
        return []
    labels: list[str] = []
    parts = [part for part in normalized.split("\\") if part]
    for part in parts:
        labels.extend(cheat_filename_hint_labels(part))
    return sorted(set(labels))


def suspicious_path_profile(
    path: str,
    patterns: dict[str, re.Pattern[str]] | None = None,
) -> dict[str, list[str]]:
    patterns = patterns or executor_name_patterns()
    norm = forensic_normalize_pathish(path) if path else ""
    if not norm:
        return {"executor_name_hits": [], "cheat_filename_hints": [], "name_anomaly_reasons": []}
    executor_labels = sorted(set(match_executor_labels(norm, patterns)))
    cheat_hints = cheat_path_hint_labels(norm)
    stem = Path(norm).stem
    full_name = Path(norm).name
    weird = list(weird_filename_reasons(stem, full_name)) if full_name else []
    for part in Path(norm).parts[:-1]:
        weird.extend(weird_filename_reasons(part, part))
    return {
        "executor_name_hits": executor_labels,
        "cheat_filename_hints": cheat_hints,
        "name_anomaly_reasons": sorted(set(weird)),
    }


def path_is_suspicious_profile(path: str, patterns: dict[str, re.Pattern[str]] | None = None) -> bool:
    profile = suspicious_path_profile(path, patterns)
    return bool(
        profile["executor_name_hits"]
        or profile["cheat_filename_hints"]
        or profile["name_anomaly_reasons"]
    )


def executor_scan_path_excluded(path_str: str) -> bool:
    """Skip game/content trees that cause noisy executor-token matches."""
    low = path_str.lower().replace("/", "\\")
    excluded = (
        "\\roblox\\versions\\",
        "\\roblox\\content\\",
        "\\windows\\winsxs\\",
        "\\windows\\servicing\\",
        "\\microsoft\\windows\\inetcache\\",
        "\\package cache\\",
        "\\nuget\\packages\\",
        "\\node_modules\\",
        "\\windowsapps\\",
        "\\appdata\\local\\packages\\",
        "\\winsat\\",
        "\\windows defender\\",
    )
    return any(fragment in low for fragment in excluded)


def path_is_allowlisted(path_str: str) -> bool:
    low = path_str.lower().replace("/", "\\")
    profile = suspicious_path_profile(path_str)
    if profile["executor_name_hits"] or profile["cheat_filename_hints"]:
        return False
    if "\\prefetch\\" in low and any(
        pattern.search(path_str) for pattern in executor_name_patterns().values()
    ):
        return False
    return any(fragment in low for fragment in PATH_ALLOWLIST_FRAGMENTS)


def loose_executor_labels_for_artifact(text: str) -> list[str]:
    """Aggressive token match for Prefetch stems, registry blobs, and binary artifacts."""
    if not text:
        return []
    compact = re.sub(r"[\s._\-\\/]", "", str(text).upper())
    labels: list[str] = []
    for name in EXECUTOR_NAMES:
        token = re.sub(r"[\s._\-]", "", name.upper())
        if len(token) < 4:
            continue
        if token in compact:
            labels.append(name)
            continue
        for alias in EXECUTOR_ALIASES.get(name, []):
            alias_token = re.sub(r"[\s._\-]", "", alias.upper())
            if len(alias_token) >= 4 and alias_token in compact:
                labels.append(name)
                break
    return sorted(set(labels))


def extract_dos_paths_from_binary(
    data: bytes,
    *,
    limit: int = 24,
    require_executor_label: bool = True,
    executable_only: bool = False,
) -> list[str]:
    """Pull drive-letter paths out of binary blobs (Prefetch, LNK, hives, logs)."""
    if not data:
        return []
    found: list[str] = []
    seen: set[str] = set()

    def accept(path: str) -> bool:
        if not path or len(path) < 6:
            return False
        if executable_only and not re.search(r"\.(exe|dll)\b", path, re.I):
            return False
        if require_executor_label and not executor_labels_for_artifact_text(path):
            return False
        return True

    patterns = (
        rb"[A-Za-z]:\\(?:[\x20-\x7e\\]|[^\x00-\x1f]){4,420}",
        rb"\\\\Device\\\\HarddiskVolume\d+\\(?:[\x20-\x7e\\]|[^\x00-\x1f]){4,420}",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, data):
            try:
                raw = match.group(0).split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip()
            except Exception:
                continue
            path = device_path_to_dos_path(raw) if raw.startswith("\\") else forensic_normalize_pathish(raw)
            if not accept(path):
                continue
            key = path.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(path[:520])
            if len(found) >= limit:
                return found
    if len(found) < limit:
        try:
            wide = data.decode("utf-16le", errors="ignore")
        except Exception:
            wide = ""
        for match in re.finditer(r"([A-Za-z]:\\[^\x00-\x1f]{4,420})", wide):
            path = forensic_normalize_pathish(match.group(1))
            if not accept(path):
                continue
            key = path.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(path[:520])
            if len(found) >= limit:
                break
    return found


def _iter_windows_drive_letters() -> list[str]:
    if platform.system() != "Windows":
        return ["C"]
    letters: list[str] = []
    for code in range(ord("C"), ord("Z") + 1):
        letter = chr(code)
        try:
            if Path(f"{letter}:\\").exists():
                letters.append(letter)
        except OSError:
            continue
    return letters or ["C"]


def device_path_to_dos_path(path: str) -> str:
    """Best-effort \\Device\\HarddiskVolumeN\\... to drive-letter path conversion."""
    s = str(path or "").replace("/", "\\").strip()
    if not s:
        return ""
    upper = s.upper()
    tail_match = re.match(r"^\\Device\\HarddiskVolume\d+\\(.+)$", s, re.IGNORECASE)
    if tail_match:
        tail = tail_match.group(1)
        for letter in _iter_windows_drive_letters():
            candidate = f"{letter}:\\{tail}"
            try:
                if Path(candidate).exists():
                    return candidate
            except OSError:
                continue
        if tail.upper().startswith("WINDOWS\\"):
            return f"C:\\{tail}"
    idx = upper.find("\\USERS\\")
    if idx != -1:
        profile = os.getenv("USERPROFILE")
        if profile and len(profile) >= 2:
            return f"{profile[0:2]}{s[idx:]}"
    m = re.search(r"([A-Za-z]:\\[^|*\"<>?\n\r]+)", s)
    if m:
        return m.group(1)
    return s


BAM_BENIGN_EXECUTABLE_NAMES = frozenset(
    {
        "powershell.exe",
        "pwsh.exe",
        "conhost.exe",
        "cmd.exe",
        "explorer.exe",
        "svchost.exe",
        "runtimebroker.exe",
        "dllhost.exe",
        "searchhost.exe",
        "sihost.exe",
        "taskhostw.exe",
        "dwm.exe",
        "fontdrvhost.exe",
        "audiodg.exe",
        "spoolsv.exe",
        "wudfhost.exe",
        "backgroundtaskhost.exe",
        "smartscreen.exe",
        "openwith.exe",
        "mmc.exe",
        "msiexec.exe",
        "setup.exe",
        "werfault.exe",
        "consent.exe",
        "msedge.exe",
        "chrome.exe",
        "firefox.exe",
        "brave.exe",
        "opera.exe",
        "vivaldi.exe",
        "ctfmon.exe",
        "python.exe",
        "pythonw.exe",
        "cursor.exe",
        "code.exe",
        "windowsterminal.exe",
        "nvidia overlay.exe",
        "nvcontainer.exe",
        "nvdisplay.container.exe",
    }
)

SYSTEM_PATH_MARKERS = (
    "\\windows\\system32\\",
    "\\windows\\syswow64\\",
    "\\windows\\systemapps\\",
    "\\windows\\immersivecontrolpanel\\",
    "\\program files\\",
    "\\program files (x86)\\",
    "\\windowsapps\\",
)


def bam_path_is_benign_system(path: str) -> bool:
    if not path:
        return True
    norm = forensic_normalize_pathish(path) or path
    low = norm.lower().replace("/", "\\")
    name = Path(low).name.lower()
    if name in BAM_BENIGN_EXECUTABLE_NAMES:
        return True
    if path_is_allowlisted(norm):
        return True
    if any(marker in low for marker in SYSTEM_PATH_MARKERS) and name.endswith((".exe", ".dll")):
        return True
    return False


def artifact_path_is_review_noise(path: str) -> bool:
    return bam_path_is_benign_system(path)


def executor_labels_for_artifact_text(text: str) -> list[str]:
    patterns = executor_name_patterns()
    labels = sorted(set(match_executor_labels(str(text or ""), patterns)))
    labels.extend(loose_executor_labels_for_artifact(str(text or "")))
    return sorted(set(labels))


def scan_binary_blob_for_executor_names(data: bytes, *, limit: int = 12) -> list[str]:
    if not data:
        return []
    hits: list[str] = []
    for name in EXECUTOR_NAMES:
        if len(name) < 4:
            continue
        for encoding in ("utf-16le", "utf-8"):
            try:
                if name.encode(encoding) in data or name.lower().encode(encoding) in data:
                    hits.append(name)
                    break
            except UnicodeEncodeError:
                continue
        if len(hits) >= limit:
            break
    return sorted(set(hits))


def path_stem_key(path_str: str) -> str:
    try:
        return Path(path_str).stem.lower()
    except Exception:
        return ""


def executor_blocklist_hash_known_paths(
    blocklist: dict[str, str],
    paths: Iterable[str],
    *,
    source: str,
) -> list[dict]:
    hits: list[dict] = []
    seen: set[str] = set()
    for path_str in paths:
        if not path_str:
            continue
        norm = forensic_normalize_pathish(path_str)
        if not norm or not re.match(r"^[A-Za-z]:\\", norm):
            continue
        key = norm.lower()
        if key in seen:
            continue
        seen.add(key)
        path = Path(norm)
        if path.suffix.lower() not in {".exe", ".dll"}:
            continue
        try:
            if not path.is_file():
                continue
        except OSError:
            continue
        sha = file_sha256_full(path)
        if not sha:
            continue
        label = blocklist.get(sha.lower())
        if not label:
            continue
        try:
            stat = path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        except OSError:
            modified = None
        hits.append(
            {
                "label": label,
                "sha256": sha,
                "path": norm,
                "size_bytes": path.stat().st_size if path.exists() else None,
                "modified": modified,
                "detection_source": source,
                "renamed_disguise": path.name.lower() not in {
                    f"{label.lower()}.exe",
                    f"{label.lower()}.dll",
                    f"{label.lower().replace(' ', '')}.exe",
                },
            }
        )
    return hits


def _executor_blocklist_scan_root(
    root: Path,
    max_depth: int,
    blocklist: dict[str, str],
    max_hashes: int,
) -> tuple[list[dict], int]:
    if not blocklist or max_hashes <= 0:
        return [], 0
    patterns = executor_name_patterns()
    hits: list[dict] = []
    hashed = 0
    seen_paths: set[str] = set()
    try:
        for path in walk_files_depth_limited(root, max_depth):
            if hashed >= max_hashes:
                break
            try:
                if not path.is_file() or path.suffix.lower() not in {".exe", ".dll"}:
                    continue
            except OSError:
                continue
            key = str(path).lower()
            if key in seen_paths:
                continue
            seen_paths.add(key)
            sha = file_sha256_full(path)
            hashed += 1
            if not sha:
                continue
            label = blocklist.get(sha.lower())
            if not label:
                continue
            try:
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                size_bytes = stat.st_size
            except OSError:
                modified = None
                size_bytes = None
            hits.append(
                {
                    "label": label,
                    "sha256": sha,
                    "path": str(path),
                    "size_bytes": size_bytes,
                    "modified": modified,
                    "detection_source": "filesystem_hash_scan",
                    "renamed_disguise": not any(pat.search(path.name) for pat in patterns.values()),
                }
            )
    except (PermissionError, OSError):
        pass
    return hits, hashed


def executor_blocklist_path_scan(
    blocklist: dict[str, str],
    max_hashes: int = EXECUTOR_HASH_SCAN_MAX_FILES,
) -> tuple[list[dict], int]:
    """Hash user-profile executables; ignores path allowlists so disguised paths still match."""
    if not blocklist:
        return [], 0
    roots = executor_user_hash_scan_roots()
    per_root_budget = max(250, max_hashes // max(1, len(roots)))
    workers = min(SCAN_WORKERS, max(1, len(roots)))
    hits: list[dict] = []
    hashed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(_executor_blocklist_scan_root, root, max_depth, blocklist, per_root_budget)
            for root, max_depth in roots
        ]
        for future in as_completed(futures):
            root_hits, root_hashed = future.result()
            hits.extend(root_hits)
            hashed += root_hashed
            if hashed >= max_hashes:
                break
    return hits[:max_hashes], min(hashed, max_hashes)


def executor_sha256_blocklist_scan(max_hashes: int = EXECUTOR_HASH_SCAN_MAX_FILES) -> dict:
    """Hash profile-folder executables and match against known executor samples."""
    return combined_user_folder_security_scans(max_hashes=max_hashes)[1]


def persistence_signals() -> dict:
    """Startup, Run keys, scheduled tasks, and recent shortcuts — common executor persistence."""
    if platform.system() != "Windows":
        return {"available": False, "reason": "Persistence scan is Windows-focused in this build"}

    patterns = executor_name_patterns()
    entries: list[dict] = []
    suspicious: list[dict] = []

    def classify_entry(source: str, name: str, target: str) -> None:
        target_text = target.strip()
        if not target_text:
            return
        executor_labels = sorted(set(match_executor_labels(f"{name} {target_text}", patterns)))
        cheat_hints = cheat_filename_hint_labels(Path(target_text).name)
        weird = weird_filename_reasons(Path(target_text).stem, Path(target_text).name)
        entry = {
            "source": source,
            "name": name,
            "target": target_text[:500],
            "executor_name_hits": executor_labels,
            "cheat_filename_hints": cheat_hints,
            "name_anomaly_reasons": weird,
            "path_allowlisted": path_is_allowlisted(target_text),
        }
        entries.append(entry)
        if entry["path_allowlisted"]:
            return
        if executor_labels or cheat_hints or weird:
            suspicious.append(entry)

    run_keys = [
        (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run", "registry_run_hkcu"),
        (r"HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce", "registry_runonce_hkcu"),
        (r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run", "registry_run_hklm"),
        (r"HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce", "registry_runonce_hklm"),
    ]
    for hive, source in run_keys:
        out = run_command(["reg", "query", hive], timeout=10, max_chars=6000)
        if not out or out.startswith("Unavailable"):
            continue
        for line in out.splitlines():
            match = re.match(r"\s+(\S+)\s+REG_(?:EXPAND_)?SZ\s+(.*)", line)
            if match:
                classify_entry(source, match.group(1), match.group(2).strip().strip('"'))

    startup_dirs: list[Path] = []
    appdata = os.getenv("APPDATA")
    programdata = os.getenv("PROGRAMDATA")
    if appdata:
        startup_dirs.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup")
    if programdata:
        startup_dirs.append(
            Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        )
    for folder in startup_dirs:
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if not path.is_file():
                continue
            classify_entry("startup_folder", path.name, str(path))

    tasks_out = run_command(["schtasks", "/Query", "/FO", "LIST", "/V"], timeout=18, max_chars=14000)
    if tasks_out and not tasks_out.startswith("Unavailable"):
        task_name = ""
        task_run = ""
        for line in tasks_out.splitlines():
            if line.startswith("TaskName:"):
                if task_name and task_run:
                    classify_entry("scheduled_task", task_name, task_run)
                task_name = line.split(":", 1)[1].strip()
                task_run = ""
            elif line.startswith("Task To Run:"):
                task_run = line.split(":", 1)[1].strip()
        if task_name and task_run:
            classify_entry("scheduled_task", task_name, task_run)

    cutoff = datetime.now(timezone.utc).timestamp() - 14 * 86400
    for root in designated_user_folder_roots():
        try:
            for lnk in root.rglob("*.lnk"):
                try:
                    if lnk.stat().st_mtime < cutoff:
                        continue
                except OSError:
                    continue
                classify_entry("recent_shortcut", lnk.name, str(lnk))
        except OSError:
            continue

    return {
        "available": True,
        "entry_count": len(entries),
        "suspicious_count": len(suspicious),
        "entries": entries[:120],
        "suspicious_entries": suspicious[:60],
    }


def _roblox_integrity_module_entry(
    *,
    scan_mode: str,
    module_path: str,
    reasons: list[str],
    executor_labels: list[str],
    cheat_hints: list[str],
    sha_label: str = "",
    offline_source: str = "",
    pid: int | None = None,
    process_name: str | None = None,
    extra: dict | None = None,
) -> dict:
    entry = {
        "scan_mode": scan_mode,
        "pid": pid,
        "process_name": process_name,
        "module_path": module_path,
        "reasons": reasons,
        "executor_name_hits": executor_labels,
        "cheat_filename_hints": cheat_hints,
        "sha256_blocklist_label": sha_label or None,
    }
    if offline_source:
        entry["offline_source"] = offline_source
    if extra:
        entry.update(extra)
    return entry


def _roblox_module_reasons(path_norm: str, patterns: dict[str, re.Pattern[str]]) -> tuple[list[str], list[str], list[str], str]:
    path_lower = path_norm.lower().replace("/", "\\")
    reasons: list[str] = []
    trusted = any(frag in path_lower for frag in ROBLOX_MODULE_TRUSTED_FRAGMENTS)
    if not trusted:
        if any(frag in path_lower for frag in ("\\temp\\", "\\downloads\\", "\\desktop\\")):
            reasons.append("module_from_high_risk_folder")
        elif "\\users\\" in path_lower and "\\appdata\\" in path_lower and "\\roblox\\" not in path_lower:
            reasons.append("module_from_user_appdata_outside_game")
    executor_labels = sorted(set(match_executor_labels(path_norm, patterns)))
    cheat_hints = cheat_filename_hint_labels(Path(path_norm).name)
    if executor_labels:
        reasons.append("executor_name_in_module")
    if cheat_hints:
        reasons.append("cheat_hint_in_module")
    sha_label = ""
    if path_lower.endswith((".exe", ".dll")) and Path(path_norm).is_file():
        sha, _, _ = forensic_file_peek(Path(path_norm))
        sha_label = load_executor_sha256_blocklist().get(sha.lower(), "")
        if sha_label:
            reasons.append(f"sha256_blocklist:{sha_label}")
    return reasons, executor_labels, cheat_hints, sha_label


def roblox_offline_integrity_signals(prefetch: dict) -> list[dict]:
    """Injection-related signals from logs and disk when Roblox is not running."""
    patterns = executor_name_patterns()
    signals: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)
    log_inject_re = re.compile(
        r"(inject(?:or|ion)?|dll\s*hook|execute\s*script|script\s*ware|memory\s*scan|"
        r"cheat\s*engine|aimbot|wallhack|bypass\s*anticheat|external\s*cheat)",
        re.IGNORECASE,
    )

    for log in _roblox_read_client_logs():
        tail = log.get("tail") or ""
        if not tail:
            continue
        matched_lines: list[str] = []
        for line in tail.splitlines():
            line_l = line.lower()
            if log_inject_re.search(line) or any(p.search(line) for p in patterns.values()):
                matched_lines.append(line.strip()[:500])
            if len(matched_lines) >= 10:
                break
        if not matched_lines:
            continue
        signals.append(
            _roblox_integrity_module_entry(
                scan_mode="offline",
                offline_source="roblox_log",
                module_path=f"roblox-log:{log.get('name', 'unknown')}",
                reasons=["roblox_log_injection_or_executor_language"],
                executor_labels=[],
                cheat_hints=[],
                extra={"matched_log_lines": matched_lines, "log_modified": log.get("modified")},
            )
        )

    bam_struct = bam_execution_records()
    if bam_struct.get("available"):
        for item in bam_struct.get("items", [])[:320]:
            path = str(item.get("normalized_path") or "")
            if not path or not path.lower().endswith(".dll"):
                continue
            if path_is_allowlisted(path):
                continue
            iso = item.get("last_execution_utc")
            if iso:
                try:
                    exec_at = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                    if exec_at.tzinfo is None:
                        exec_at = exec_at.replace(tzinfo=timezone.utc)
                    if exec_at < cutoff:
                        continue
                except ValueError:
                    pass
            reasons, executor_labels, cheat_hints, sha_label = _roblox_module_reasons(path, patterns)
            path_lower = path.lower()
            if not reasons and not any(
                frag in path_lower for frag in ("\\temp\\", "\\downloads\\", "\\desktop\\", "\\appdata\\")
            ):
                continue
            if not reasons:
                reasons.append("dll_executed_from_staging_folder")
            signals.append(
                _roblox_integrity_module_entry(
                    scan_mode="offline",
                    offline_source="bam_dll_execution",
                    module_path=path,
                    reasons=reasons,
                    executor_labels=executor_labels,
                    cheat_hints=cheat_hints,
                    sha_label=sha_label,
                    extra={"last_execution_utc": iso, "file_exists": item.get("file_exists")},
                )
            )

    local_app = os.getenv("LOCALAPPDATA")
    if local_app:
        roblox_root = Path(local_app) / "Roblox"
        if roblox_root.is_dir():
            for dll in roblox_root.rglob("*.dll"):
                path_str = str(dll)
                if "\\versions\\" in path_str.lower():
                    continue
                reasons, executor_labels, cheat_hints, sha_label = _roblox_module_reasons(path_str, patterns)
                if not reasons:
                    continue
                try:
                    modified = datetime.fromtimestamp(dll.stat().st_mtime, timezone.utc).isoformat()
                except OSError:
                    modified = None
                signals.append(
                    _roblox_integrity_module_entry(
                        scan_mode="offline",
                        offline_source="roblox_folder_dll",
                        module_path=path_str,
                        reasons=reasons + ["dll_outside_roblox_versions_tree"],
                        executor_labels=executor_labels,
                        cheat_hints=cheat_hints,
                        sha_label=sha_label,
                        extra={"modified": modified},
                    )
                )
                if len([s for s in signals if s.get("offline_source") == "roblox_folder_dll"]) >= 25:
                    break

    temp_roots: list[Path] = []
    for env_name in ("TEMP", "TMP", "LOCALAPPDATA"):
        value = os.getenv(env_name)
        if value:
            temp_roots.append(Path(value))
    for root in temp_roots:
        if not root.is_dir():
            continue
        try:
            for dll in walk_files_depth_limited(root, 3):
                if dll.suffix.lower() != ".dll":
                    continue
                try:
                    stat = dll.stat()
                except OSError:
                    continue
                if datetime.fromtimestamp(stat.st_mtime, timezone.utc) < cutoff:
                    continue
                path_str = str(dll)
                if path_is_allowlisted(path_str):
                    continue
                reasons, executor_labels, cheat_hints, sha_label = _roblox_module_reasons(path_str, patterns)
                if not reasons:
                    continue
                signals.append(
                    _roblox_integrity_module_entry(
                        scan_mode="offline",
                        offline_source="recent_temp_dll",
                        module_path=path_str,
                        reasons=reasons,
                        executor_labels=executor_labels,
                        cheat_hints=cheat_hints,
                        sha_label=sha_label,
                        extra={"modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()},
                    )
                )
                if len([s for s in signals if s.get("offline_source") == "recent_temp_dll"]) >= 30:
                    break
        except (PermissionError, OSError):
            continue

    return signals[:100]


def roblox_integrity_scan(prefetch: dict | None = None) -> dict:
    """Live DLL inspection when Roblox runs, plus offline log/BAM/folder signals always."""
    if platform.system() != "Windows":
        return {"available": False, "reason": "Roblox integrity scan is Windows-focused in this build"}

    patterns = executor_name_patterns()
    processes_found: list[dict] = []
    live_modules: list[dict] = []
    modules_sampled = 0

    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = proc.info
            name = (info.get("name") or "").lower()
            if name not in ROBLOX_PROCESS_NAMES:
                continue
            pid = int(info["pid"])
            processes_found.append({"pid": pid, "name": info.get("name"), "exe": info.get("exe")})
            module_paths: list[str] = []
            try:
                p = psutil.Process(pid)
                try:
                    for mmap in p.memory_maps(grouped=False):
                        module_paths.append(getattr(mmap, "path", "") or "")
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    module_paths = []
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                module_paths = []

            if not module_paths:
                ps_script = (
                    f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
                    "if ($p) { $p.Modules | ForEach-Object { $_.FileName } }"
                )
                out = run_command(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    timeout=14,
                    max_chars=12000,
                )
                module_paths = [line.strip() for line in (out or "").splitlines() if line.strip()]

            for raw_path in module_paths:
                path = (raw_path or "").strip()
                if not path or path.startswith("["):
                    continue
                modules_sampled += 1
                path_norm = path.replace("/", "\\")
                reasons, executor_labels, cheat_hints, sha_label = _roblox_module_reasons(path_norm, patterns)
                if not reasons:
                    continue
                live_modules.append(
                    _roblox_integrity_module_entry(
                        scan_mode="live",
                        pid=pid,
                        process_name=info.get("name") or name,
                        module_path=path_norm,
                        reasons=reasons,
                        executor_labels=executor_labels,
                        cheat_hints=cheat_hints,
                        sha_label=sha_label,
                    )
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
            continue

    offline_signals = roblox_offline_integrity_signals(prefetch or {})
    combined = (live_modules + offline_signals)[:120]

    return {
        "available": True,
        "live_process_detected": bool(processes_found),
        "processes_found": processes_found,
        "live_suspicious_modules": live_modules[:80],
        "offline_signals": offline_signals,
        "suspicious_modules": combined,
        "modules_sampled": modules_sampled,
        "note": (
            "Offline checks (Roblox logs, BAM DLL executions, Prefetch, Roblox folder, recent temp DLLs) "
            "run even when the game is closed. Live module enumeration runs when Roblox is open."
        ),
    }


def roblox_runtime_module_scan(prefetch: dict | None = None) -> dict:
    return roblox_integrity_scan(prefetch=prefetch)


def designated_user_folder_roots() -> list[Path]:
    """Return scan roots: all accessible local/removable drive letters plus user home."""
    roots: list[Path] = []
    seen: set[str] = set()
    for drive_root in all_logical_drive_roots(include_removable=True, include_network=False):
        key = str(drive_root).lower()
        if key not in seen:
            seen.add(key)
            roots.append(drive_root)
    if platform.system() == "Windows":
        base = os.getenv("USERPROFILE")
        if base:
            home = Path(base)
            if home.is_dir() and str(home).lower() not in seen:
                roots.insert(0, home)
    else:
        home = Path.home()
        if home.is_dir():
            roots.insert(0, home)
    return roots


def all_logical_drive_roots(
    *,
    include_removable: bool = True,
    include_network: bool = False,
) -> list[Path]:
    """Enumerate fixed (C:, D:, …) and optional USB/removable volumes for full-PC scans."""
    if platform.system() != "Windows":
        return [Path.home()]
    allowed_types = {3}
    if include_removable:
        allowed_types.add(2)
    if include_network:
        allowed_types.add(4)
    script = (
        "Get-CimInstance Win32_LogicalDisk -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.DriveType -in @({','.join(str(t) for t in sorted(allowed_types))}) }} | "
        "ForEach-Object { $_.DeviceID + '\\' } | ConvertTo-Json -Compress"
    )
    data = forensic_powershell_json(script, timeout=12.0, max_chars=4000)
    roots: list[Path] = []
    letters: list[str] = []
    if isinstance(data, list):
        letters = [str(x) for x in data if isinstance(x, str)]
    elif isinstance(data, str) and data.endswith(":\\"):
        letters = [data]
    for letter in letters:
        candidate = Path(letter)
        if candidate.is_dir():
            roots.append(candidate)
    if not roots:
        system_drive = os.getenv("SystemDrive", "C:") + "\\"
        fallback = Path(system_drive)
        if fallback.is_dir():
            roots.append(fallback)
    return roots


def full_pc_scan_roots() -> list[tuple[Path, int]]:
    """Every local/removable drive with a generous depth budget."""
    return [(root, FULL_PC_SCAN_MAX_DEPTH) for root in all_logical_drive_roots(include_removable=True)]


def walk_files_depth_limited(root: Path, max_depth: int):
    try:
        root = root.resolve()
    except Exception:
        root = root
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        current_low = str(current).lower().replace("/", "\\")
        if any(skip in current_low for skip in FULL_PC_SKIP_DIR_FRAGMENTS):
            dirnames.clear()
            continue
        try:
            rel_depth = len(current.relative_to(root).parts)
        except ValueError:
            dirnames[:] = []
            continue
        if rel_depth >= max_depth:
            dirnames.clear()
        for fn in filenames:
            yield current / fn


def _path_is_user_writable_execution_zone(path_str: str) -> bool:
    low = path_str.lower().replace("/", "\\")
    zones = (
        "\\downloads\\",
        "\\desktop\\",
        "\\documents\\",
        "\\appdata\\",
        "\\temp\\",
        "\\tmp\\",
        "\\users\\",
    )
    return any(zone in low for zone in zones)


def _probe_executable_binary_labels(path: Path) -> list[str]:
    """Read PE/binary content and match embedded executor branding (survives renames)."""
    try:
        if not path.is_file():
            return []
        size = path.stat().st_size
        if size <= 0 or size > FULL_PC_BINARY_PROBE_MAX_BYTES:
            return []
        data = path.read_bytes()[:FULL_PC_BINARY_PROBE_MAX_BYTES]
    except OSError:
        return []
    labels = scan_binary_blob_for_executor_names(data)
    labels.extend(loose_executor_labels_for_artifact(data.decode("utf-16le", errors="ignore")[:500000]))
    return sorted(set(labels))


def weird_filename_reasons(stem: str, full_name: str) -> list[str]:
    reasons: list[str] = []
    if not stem:
        reasons.append("empty_base_name")
        return reasons
    letters = [c for c in stem if c.isalpha()]
    digits = sum(1 for c in stem if c.isdigit())
    alnum = sum(1 for c in stem if c.isalnum())
    if len(stem) >= 52:
        reasons.append("very_long_name")
    if full_name.count(".") >= 3:
        reasons.append("multiple_dot_segments")
    if re.search(r"\.[A-Za-z0-9]{1,5}\.(exe|dll|bat|ps1)\Z", full_name, re.IGNORECASE):
        reasons.append("double_extension_style")
    if digits and alnum and (digits / max(alnum, 1)) >= 0.38 and len(stem) >= 12:
        reasons.append("high_digit_ratio")
    if re.fullmatch(r"[0-9A-Fa-f]{24,}", stem):
        reasons.append("hex_like_name")
    if len(stem) >= 18 and re.fullmatch(r"[A-Za-z0-9+/=_-]+", stem) and any(c.islower() for c in stem) and any(c.isupper() for c in stem):
        reasons.append("mixed_case_alnum_blob")
    if re.search(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}", stem):
        reasons.append("guid_like_segment")
    if re.search(r"[_-]{4,}", stem):
        reasons.append("long_separator_run")
    non_word = sum(1 for c in stem if not (c.isalnum() or c in "._- "))
    if non_word >= 3:
        reasons.append("unusual_symbols")
    if stem.lower() in USER_FOLDER_TRUSTED_APP_STEMS:
        reasons.append("trusted_app_name_in_user_folder_context")
    if len(letters) >= 14:
        transitions = sum(1 for i in range(len(letters) - 1) if letters[i].islower() != letters[i + 1].islower())
        if transitions >= min(10, max(6, len(letters) // 3)):
            reasons.append("chaotic_mixed_case")
    if stem.lower() in {"setup", "installer", "update", "patch", "crack", "loader", "inject", "bypass", "exploit"}:
        reasons.append("generic_risky_token")
    return reasons


def match_executor_labels(text: str, patterns: dict[str, re.Pattern[str]]) -> list[str]:
    return [name for name, pattern in patterns.items() if pattern.search(text)]


def _full_pc_scan_root(root: Path, max_depth: int, patterns: dict[str, re.Pattern[str]]) -> dict:
    hits: list[dict] = []
    enumerated = 0
    binary_probes = 0
    skipped_permission = 0
    try:
        for path in walk_files_depth_limited(root, max_depth):
            enumerated += 1
            if enumerated > FULL_PC_SCAN_MAX_ENUMERATED:
                break
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue
            ext = path.suffix.lower()
            if ext not in USER_FOLDER_SCAN_EXTENSIONS and ext not in FULL_PC_EXECUTABLE_EXTENSIONS:
                continue
            if executor_scan_path_excluded(str(path)):
                continue
            path_str = str(path)
            executor_labels = sorted(set(match_executor_labels(path_str, patterns)))
            cheat_hints = cheat_path_hint_labels(path_str)
            weird = list(weird_filename_reasons(path.stem, path.name))
            for part in path.parts[:-1]:
                weird.extend(weird_filename_reasons(part, part))
            weird = sorted(set(weird))
            binary_labels: list[str] = []
            if ext in {".exe", ".dll"} and binary_probes < FULL_PC_BINARY_PROBE_MAX_FILES:
                binary_labels = _probe_executable_binary_labels(path)
                binary_probes += 1
                if binary_labels:
                    executor_labels = sorted(set(executor_labels + binary_labels))
            if not executor_labels and not cheat_hints and not weird:
                continue
            try:
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                accessed = datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat()
            except OSError:
                modified = None
                accessed = None
            hits.append(
                {
                    "path": path_str,
                    "name": path.name,
                    "extension": ext,
                    "size_bytes": stat.st_size if modified else None,
                    "modified": modified,
                    "accessed": accessed,
                    "executor_name_hits": executor_labels,
                    "cheat_filename_hints": cheat_hints,
                    "name_anomaly_reasons": weird,
                    "binary_embedded_labels": binary_labels,
                    "path_allowlisted": path_is_allowlisted(path_str),
                    "scan_source": "full_pc_drive_walk",
                }
            )
            if len(hits) >= FULL_PC_SCAN_MAX_HITS:
                break
    except PermissionError:
        skipped_permission += 1
    except OSError:
        skipped_permission += 1
    return {
        "root": str(root),
        "hits": hits,
        "enumerated_files": enumerated,
        "binary_probes": binary_probes,
        "skipped_permission_roots": skipped_permission,
    }


def full_pc_filesystem_executor_scan() -> dict:
    """Walk every local/removable drive for executor names, cheat hints, and embedded binary branding."""
    if platform.system() != "Windows":
        return {"available": False, "reason": "Full-PC scan is Windows-only", "hits": []}
    patterns = executor_name_patterns()
    roots = full_pc_scan_roots()
    workers = min(SCAN_WORKERS, max(1, len(roots)))
    hits: list[dict] = []
    enumerated = 0
    binary_probes = 0
    skipped_permission = 0
    roots_scanned: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_full_pc_scan_root, root, max_depth, patterns) for root, max_depth in roots]
        for future in as_completed(futures):
            partial = future.result()
            roots_scanned.append(str(partial.get("root") or ""))
            hits.extend(partial.get("hits") or [])
            enumerated += int(partial.get("enumerated_files") or 0)
            binary_probes += int(partial.get("binary_probes") or 0)
            skipped_permission += int(partial.get("skipped_permission_roots") or 0)
            if enumerated >= FULL_PC_SCAN_MAX_ENUMERATED or len(hits) >= FULL_PC_SCAN_MAX_HITS:
                break
    if len(hits) > FULL_PC_SCAN_MAX_HITS:
        hits = hits[:FULL_PC_SCAN_MAX_HITS]
    return {
        "available": True,
        "hit_count": len(hits),
        "hits": hits,
        "enumerated_files": min(enumerated, FULL_PC_SCAN_MAX_ENUMERATED),
        "binary_probes": binary_probes,
        "roots_scanned": roots_scanned,
        "skipped_permission_roots": skipped_permission,
        "note": "Full-PC walk of all fixed and removable drives; probes .exe/.dll binaries for embedded executor strings.",
    }


def scan_execution_artifact_binaries(
    *,
    bam: dict,
    dam: dict | None,
    blocklist: dict[str, str],
) -> list[dict[str, object]]:
    """Inspect BAM/DAM execution paths — catches renamed executors via binary branding and hashes."""
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    sources = [("bam_execution_binary", bam), ("dam_execution_binary", dam or {})]
    for artifact_source, struct in sources:
        for item in struct.get("items") or []:
            path = str(item.get("normalized_path") or "")
            if not path or not re.search(r"\.(exe|dll)\b", path, re.I):
                continue
            labels = list(item.get("executor_name_hits") or [])
            labels = sorted(set(labels + executor_labels_for_artifact_text(path)))
            file_exists = bool(item.get("file_exists"))
            sha = ""
            if file_exists:
                file_path = Path(path)
                if not labels:
                    labels = _probe_executable_binary_labels(file_path)
                if blocklist:
                    sha = file_sha256_full(file_path)
                    block_label = blocklist.get(sha.lower()) if sha else None
                    if block_label:
                        labels = sorted(set(labels + [block_label]))
            if not labels and file_exists and _path_is_user_writable_execution_zone(path):
                profile = suspicious_path_profile(path)
                if profile["cheat_filename_hints"] or profile["name_anomaly_reasons"]:
                    labels = ["suspicious_executed_binary"]
            if not labels:
                continue
            _append_executor_artifact_hit(
                hits,
                seen,
                path=path,
                labels=labels,
                occurred_at=item.get("last_execution_utc"),
                artifact_source=artifact_source,
                timestamp_source="bam_execution",
                file_exists=file_exists,
                note="Execution record path matched via name, embedded binary string, or hash.",
                extra={"sha256": sha or None},
            )
    return hits


def combined_user_folder_security_scans(max_hashes: int = EXECUTOR_HASH_SCAN_MAX_FILES) -> tuple[dict, dict]:
    """Full-PC name/binary hits plus SHA256 blocklist scan across all drives."""
    blocklist = load_executor_sha256_blocklist()
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_full_pc = pool.submit(full_pc_filesystem_executor_scan)
        fut_sha = pool.submit(executor_blocklist_path_scan, blocklist, max_hashes)
        full_pc = fut_full_pc.result()
        sha_hits, hashed = fut_sha.result()

    merged_hits = list(full_pc.get("hits") or [])
    merged_hits.sort(key=lambda row: str(row.get("modified") or ""), reverse=True)
    cheat_only = sum(
        1
        for item in merged_hits
        if (item.get("cheat_filename_hints") or [])
        and not item.get("executor_name_hits")
        and not item.get("name_anomaly_reasons")
    )
    weird_only = sum(
        1
        for item in merged_hits
        if not item.get("executor_name_hits") and item.get("name_anomaly_reasons")
    )

    designated = {
        "hit_count": len(merged_hits),
        "executor_name_hits": sum(1 for item in merged_hits if item.get("executor_name_hits")),
        "cheat_filename_only_hits": cheat_only,
        "weird_name_only_hits": weird_only,
        "skipped_roots_permission_errors": full_pc.get("skipped_permission_roots", 0),
        "hits": merged_hits[:FULL_PC_SCAN_MAX_HITS],
        "full_pc_scan": {
            "enumerated_files": full_pc.get("enumerated_files"),
            "binary_probes": full_pc.get("binary_probes"),
            "roots_scanned": full_pc.get("roots_scanned"),
            "hit_count": full_pc.get("hit_count"),
        },
    }
    if not blocklist:
        sha_blocklist = {
            "available": True,
            "blocklist_size": 0,
            "files_hashed": 0,
            "hits": [],
        }
    else:
        sha_blocklist = {
            "available": True,
            "blocklist_size": len(blocklist),
            "files_hashed": hashed,
            "hits": sha_hits,
        }
    return designated, sha_blocklist


def designated_folder_extension_scan() -> dict:
    return combined_user_folder_security_scans()[0]


def hashed_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hidden_subprocess_kwargs() -> dict:
    """Prevent PowerShell/cmd windows from flashing during scans on Windows."""
    if platform.system() != "Windows":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
    return {
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        "startupinfo": startupinfo,
    }


def run_command(command: list[str], timeout: float = 8, max_chars: int = 8000) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=timeout,
            check=False,
            **_hidden_subprocess_kwargs(),
        )
        output = result.stdout or result.stderr or b""
        return output.decode("utf-8", errors="replace").strip()[:max_chars]
    except Exception as exc:
        return f"Unavailable: {exc}"


def hardware_identifiers() -> dict:
    system = platform.system()
    result = {"hardware_model": platform.machine(), "uuid_hash": None, "uuid_source": "unavailable"}
    if system == "Windows":
        model = run_command(["wmic", "computersystem", "get", "model", "/value"])
        uuid = run_command(["wmic", "csproduct", "get", "uuid", "/value"])
        result["hardware_model"] = model.replace("Model=", "").strip() or result["hardware_model"]
        raw_uuid = uuid.replace("UUID=", "").strip()
        if raw_uuid:
            result["uuid_hash"] = hashed_identifier(raw_uuid)
            result["uuid_source"] = "wmic csproduct UUID"
    elif system == "Darwin":
        output = run_command(["system_profiler", "SPHardwareDataType"])
        model_match = re.search(r"Model Name:\s*(.+)", output)
        uuid_match = re.search(r"Hardware UUID:\s*([A-Fa-f0-9-]+)", output)
        if model_match:
            result["hardware_model"] = model_match.group(1).strip()
        if uuid_match:
            result["uuid_hash"] = hashed_identifier(uuid_match.group(1).strip())
            result["uuid_source"] = "macOS Hardware UUID"
    return result


def installed_apps_summary() -> dict:
    system = platform.system()
    if system == "Windows":
        output = run_command([
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
            "Select-Object -First 80 DisplayName,DisplayVersion,Publisher,InstallDate | ConvertTo-Json",
        ])
        return {"source": "Windows uninstall registry", "sample": output}
    if system == "Darwin":
        apps = []
        for folder in [Path("/Applications"), Path.home() / "Applications"]:
            if folder.exists():
                apps.extend(path.name for path in folder.glob("*.app"))
        return {"source": "macOS Applications folders", "sample": sorted(apps)[:80]}
    return {"source": "unsupported", "sample": []}


def windows_filetime_to_iso(value: int) -> str | None:
    if value <= 0:
        return None
    timestamp = (value - 116444736000000000) / 10_000_000
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    except (OSError, ValueError, OverflowError):
        return None


def chrome_webkit_time_to_iso(value: object) -> str | None:
    try:
        micros = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if micros <= 0:
        return None
    try:
        epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        return (epoch + timedelta(microseconds=micros)).isoformat()
    except (OverflowError, ValueError):
        return None


def firefox_pr_time_to_iso(value: object) -> str | None:
    """Firefox PRTime: microseconds since Unix epoch."""
    try:
        micros = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if micros <= 0:
        return None
    try:
        return datetime.fromtimestamp(micros / 1_000_000, tz=timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def resolve_display_timestamp(
    *,
    primary: str | None = None,
    fallbacks: list[tuple[str, str | None]] | None = None,
) -> tuple[str | None, str | None]:
    if primary:
        return primary, "recorded"
    for source, candidate in fallbacks or []:
        if candidate:
            return candidate, source
    return None, None


HIGH_CONFIDENCE_ACTIVITY_SOURCES = frozenset(
    {
        "bam_execution",
        "usn_delete",
        "recycle_bin",
        "recycle_metadata",
        "event_log",
        "security_audit_delete",
        "sysmon_file_delete",
        "userassist",
        "browser_download_start",
        "browser_download_end",
    }
)


def timestamp_in_scan_window(
    ts: str | None,
    scan_started_at: str | None,
    generated_at: str | None,
    *,
    buffer_seconds: int = 180,
) -> bool:
    event_ms = _iso_to_epoch_ms(normalize_event_time(ts))
    end_ms = _iso_to_epoch_ms(normalize_event_time(generated_at))
    start_ms = _iso_to_epoch_ms(normalize_event_time(scan_started_at))
    if event_ms is None or end_ms is None:
        return False
    if start_ms is None:
        start_ms = end_ms - 45 * 60 * 1000
    return event_ms >= (start_ms - buffer_seconds * 1000) and event_ms <= (end_ms + buffer_seconds * 1000)


def sanitize_activity_timestamp(
    ts: str | None,
    source: str | None,
    scan_started_at: str | None,
    generated_at: str | None,
) -> str | None:
    normalized = normalize_event_time(ts)
    if not normalized:
        return None
    if source in HIGH_CONFIDENCE_ACTIVITY_SOURCES:
        return normalized
    if timestamp_in_scan_window(normalized, scan_started_at, generated_at):
        return None
    return normalized


def _iso_to_epoch_ms(value: str | None) -> int | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def _parse_us_datetime(raw: str) -> str | None:
    cleaned = raw.strip().replace(",", "")
    for fmt in ("%m/%d/%Y %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue
    return None


def parse_usn_timestamp(body: str) -> str | None:
    if not body:
        return None
    for pattern in (
        r"Time\s+[Ss]tamp\s*,\s*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}(?:\.\d+)?)",
        r"Time\s+[Ss]tamp\s*:\s*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2}(?:\.\d+)?)",
        r"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?)",
    ):
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            parsed = _parse_us_datetime(match.group(1))
            if parsed:
                return parsed
            try:
                dt = datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except ValueError:
                pass
    filetime_match = re.search(r"Time\s+[Ss]tamp\s*,\s*(0x[0-9a-fA-F]+)", body, re.IGNORECASE)
    if filetime_match:
        return windows_filetime_to_iso(int(filetime_match.group(1), 16))
    csv_match = re.match(
        r"[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,\s*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})",
        body,
    )
    if csv_match:
        return _parse_us_datetime(csv_match.group(1))
    return None


def normalize_event_time(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"none", "null", "0"}:
            return None
        if is_iso_date_string(text):
            return text
        parsed = _parse_us_datetime(text)
        if parsed:
            return parsed
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        if value > 10_000_000_000_000:
            return chrome_webkit_time_to_iso(int(value))
        if value > 1_000_000_000_000:
            try:
                return datetime.fromtimestamp(float(value) / 1000.0, timezone.utc).isoformat()
            except (OSError, ValueError, OverflowError):
                return None
        if value > 1_000_000_000:
            try:
                return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
            except (OSError, ValueError, OverflowError):
                return None
        return windows_filetime_to_iso(int(value))
    return None


def is_iso_date_string(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value))


def recycle_info_record(path: Path) -> dict | None:
    try:
        data = path.read_bytes()
    except Exception:
        return None
    if len(data) < 24:
        return None
    version = int.from_bytes(data[0:8], "little", signed=False) if len(data) >= 8 else 0
    if version >= 2 and len(data) >= 28:
        original_size = int.from_bytes(data[8:16], "little", signed=False)
        deleted_raw = int.from_bytes(data[16:24], "little", signed=False)
        path_offset = 28
        if len(data) >= 28:
            path_len = int.from_bytes(data[24:28], "little", signed=False)
            if path_len > 0 and path_offset + path_len * 2 <= len(data):
                raw_path = data[path_offset : path_offset + path_len * 2].decode("utf-16-le", errors="replace")
            else:
                raw_path = data[path_offset:].decode("utf-16-le", errors="replace").split("\x00", 1)[0]
        else:
            raw_path = ""
    else:
        original_size = int.from_bytes(data[8:16], "little", signed=False) if len(data) >= 16 else 0
        deleted_raw = int.from_bytes(data[16:24], "little", signed=False) if len(data) >= 24 else 0
        raw_path = data[24:].decode("utf-16-le", errors="replace").split("\x00", 1)[0]
    deleted_at = windows_filetime_to_iso(deleted_raw)
    metadata_modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    companion_mtime: str | None = None
    companion = path.with_name(path.name.replace("$I", "$R", 1))
    if companion.is_file():
        try:
            companion_mtime = datetime.fromtimestamp(companion.stat().st_mtime, timezone.utc).isoformat()
        except OSError:
            companion_mtime = None
    display_at, timestamp_source = resolve_display_timestamp(
        primary=deleted_at,
        fallbacks=[
            ("recycle_metadata_mtime", metadata_modified),
            ("recycle_data_mtime", companion_mtime),
        ],
    )
    return {
        "recycle_metadata_file": path.name,
        "original_path": raw_path.strip(),
        "deleted_at": deleted_at,
        "display_at": display_at,
        "timestamp_source": timestamp_source,
        "original_size_bytes": original_size,
        "metadata_modified": metadata_modified,
        "recycle_data_modified": companion_mtime,
    }


def recycle_bin_metadata() -> dict:
    candidates: list[Path] = []
    if platform.system() == "Windows":
        for letter in string.ascii_uppercase:
            recycle = Path(f"{letter}:\\$Recycle.Bin")
            if recycle.is_dir():
                candidates.append(recycle)
    elif platform.system() == "Darwin":
        candidates.append(Path.home() / ".Trash")
        volumes = Path("/Volumes")
        if volumes.is_dir():
            try:
                for vol in volumes.iterdir():
                    trashes = vol / ".Trashes"
                    if trashes.is_dir():
                        candidates.append(trashes)
            except OSError:
                pass

    items = []
    for folder in candidates:
        if not folder.exists():
            continue
        try:
            paths = [path for path in folder.rglob("*") if path.is_file()]
        except Exception:
            paths = []
        for path in paths:
            try:
                stat = path.stat()
                info_record = recycle_info_record(path) if path.name.startswith("$I") else None
                item = {
                    "name": path.name,
                    "location": str(path.parent),
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                    "size_bytes": stat.st_size,
                }
                if info_record:
                    item.update(info_record)
                    original_path = str(info_record.get("original_path") or "").strip()
                    if original_path:
                        profile = suspicious_path_profile(original_path)
                        if path_is_suspicious_profile(original_path):
                            item["suspicious_recycle_item"] = True
                            item["executor_name_hits"] = profile["executor_name_hits"]
                            item["cheat_filename_hints"] = profile["cheat_filename_hints"]
                            item["name_anomaly_reasons"] = profile["name_anomaly_reasons"]
                else:
                    display_at, timestamp_source = resolve_display_timestamp(
                        primary=item.get("modified"),
                        fallbacks=[("os_access", item.get("accessed"))],
                    )
                    item["display_at"] = display_at
                    item["timestamp_source"] = timestamp_source
                items.append(item)
            except Exception:
                continue
    items.sort(key=lambda item: item.get("display_at") or item.get("deleted_at") or item.get("modified") or "", reverse=True)
    suspicious_count = sum(1 for item in items if item.get("suspicious_recycle_item"))
    return {
        "status": "Recycle Bin metadata collected" if items else "No accessible Trash/Recycle Bin item found",
        "count": len(items[:RECYCLE_BIN_MAX_ITEMS]),
        "latest": items[0] if items else None,
        "items": items[:RECYCLE_BIN_MAX_ITEMS],
        "suspicious_count": suspicious_count,
        "note": "Windows: all fixed-drive $Recycle.Bin folders scanned. $I metadata lists original paths before "
        "emptying; $R payload files are hashed in a follow-up pass. After permanent delete, BAM, Prefetch, USN, "
        "and registry artifacts below still recover evidence.",
    }


def prefetch_metadata() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows Prefetch is only available on Windows"}

    folder = Path(os.getenv("SystemRoot", "C:\\Windows")) / "Prefetch"
    if not folder.exists():
        return {"available": False, "reason": "Prefetch folder not found"}

    items = []
    executor_name_hits_in_prefetch = 0
    try:
        files = sorted(folder.glob("*.pf"), key=lambda path: path.stat().st_mtime, reverse=True)
    except Exception as exc:
        return {"available": False, "reason": str(exc)}

    for path in files:
        try:
            stat = path.stat()
            pf_labels = executor_labels_for_artifact_text(path.name)
            if not pf_labels:
                pf_labels = executor_labels_for_artifact_text(prefetch_extract_stem(path.name))
            if pf_labels:
                executor_name_hits_in_prefetch += 1
            items.append(
                {
                    "name": path.name,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                    "size_bytes": stat.st_size,
                    "executor_name_hits": pf_labels,
                }
            )
        except Exception:
            continue
    # Keep metadata payload bounded; full Prefetch sweep runs separately on every .pf file.
    return {
        "available": True,
        "folder": str(folder),
        "count": len(items),
        "total_pf_files": len(items),
        "executor_pf_matches": executor_name_hits_in_prefetch,
        "items": items[:400],
    }


def amcache_metadata() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Amcache is a Windows artifact"}

    hive_path = Path(os.getenv("SystemRoot", "C:\\Windows")) / "AppCompat" / "Programs" / "Amcache.hve"
    if not hive_path.exists():
        return {"available": False, "path": str(hive_path), "reason": "Amcache hive not found"}

    try:
        stat = hive_path.stat()
        hive_mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
    except OSError as exc:
        return {"available": False, "path": str(hive_path), "reason": str(exc)}

    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        f"$src='{str(hive_path).replace(chr(39), chr(39)+chr(39))}';"
        "$tmp=Join-Path $env:TEMP ('amcache_'+[guid]::NewGuid().ToString('N')+'.hve');"
        "Copy-Item $src $tmp -Force;"
        "$hive='Amcache'+[string](Get-Random);"
        "$regKey='HKU\\'+$hive;"
        "reg.exe load $regKey $tmp 2>&1 | Out-Null;"
        "$items=@();"
        "$fileRoot='Registry::'+$regKey+'\\Root\\InventoryApplicationFile';"
        "$appRoot='Registry::'+$regKey+'\\Root\\InventoryApplication';"
        "if(Test-Path $fileRoot){"
        "Get-ChildItem $fileRoot -ErrorAction SilentlyContinue | Select-Object -First 500 | ForEach-Object {"
        "$p=Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue;"
        "if($p.FullPath){"
        "$items += [pscustomobject]@{"
        "Path=$p.FullPath;"
        "Name=$p.Name;"
        "Publisher=$p.Publisher;"
        "LastWrite=$p.LastModifiedTime;"
        "Sha1=$p.SHA1Hash;"
        "Source='InventoryApplicationFile'"
        "}"
        "}"
        "};"
        "if(Test-Path $appRoot){"
        "Get-ChildItem $appRoot -ErrorAction SilentlyContinue | Select-Object -First 200 | ForEach-Object {"
        "$p=Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue;"
        "if($p.Name){"
        "$items += [pscustomobject]@{"
        "Path=$p.Name;"
        "Name=$p.Name;"
        "Publisher=$p.Publisher;"
        "LastWrite=$p.LastModifiedTime;"
        "Sha1=$null;"
        "Source='InventoryApplication'"
        "}"
        "}"
        "};"
        "reg.exe unload $regKey 2>&1 | Out-Null;"
        "Remove-Item $tmp -Force -ErrorAction SilentlyContinue;"
        "[pscustomobject]@{Available=$true;Count=$items.Count;Items=$items} | ConvertTo-Json -Depth 4 -Compress"
    )
    parsed = forensic_powershell_json(script, timeout=28.0, max_chars=32000)
    items: list[dict] = []
    if isinstance(parsed, dict):
        raw_items = parsed.get("Items") or parsed.get("items") or []
        if isinstance(raw_items, list):
            patterns = executor_name_patterns()
            for entry in raw_items[:500]:
                if not isinstance(entry, dict):
                    continue
                path = str(entry.get("Path") or entry.get("path") or "")
                if not path:
                    continue
                profile = suspicious_path_profile(path, patterns)
                items.append(
                    {
                        "path": path,
                        "name": entry.get("Name") or entry.get("name"),
                        "publisher": entry.get("Publisher") or entry.get("publisher"),
                        "last_write": normalize_event_time(entry.get("LastWrite") or entry.get("last_write")),
                        "sha1": entry.get("Sha1") or entry.get("sha1"),
                        "source": entry.get("Source") or entry.get("source") or "InventoryApplicationFile",
                        "executor_name_hits": profile["executor_name_hits"],
                        "cheat_filename_hints": profile["cheat_filename_hints"],
                    }
                )

    suspicious = [item for item in items if item.get("executor_name_hits") or item.get("cheat_filename_hints")]
    return {
        "available": True,
        "path": str(hive_path),
        "modified": hive_mtime,
        "size_bytes": stat.st_size,
        "entry_count": len(items),
        "suspicious_count": len(suspicious),
        "items": items[:300],
        "suspicious_items": suspicious[:80],
        "note": "Parsed offline Amcache.hve inventory (executables and installers).",
    }


def bam_registry_entries(bam_structured: dict | None = None) -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "BAM is a Windows registry artifact"}

    if bam_structured and bam_structured.get("available"):
        items = bam_structured.get("items") or []
        return {
            "available": True,
            "source": "HKLM SYSTEM CurrentControlSet Services bam State UserSettings",
            "items": items,
            "raw_sample": json.dumps(items[:120], default=str)[:12000],
            "note": "Structured BAM parse (same data as forensic_analysis.bam_structured).",
        }

    script = (
        "$base='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\bam\\State\\UserSettings';"
        "if(Test-Path $base){"
        "Get-ChildItem $base | ForEach-Object {"
        "$sid=$_.PSChildName;"
        "Get-ItemProperty $_.PSPath | Select-Object -Property * | ConvertTo-Json -Depth 2"
        "}"
        "} else { '[]' }"
    )
    output = run_command(["powershell", "-NoProfile", "-Command", script])
    return {
        "available": True,
        "source": "HKLM SYSTEM CurrentControlSet Services bam State UserSettings",
        "raw_sample": output[:12000],
        "note": "BAM entries are reported as a bounded raw PowerShell JSON sample.",
    }


def userassist_registry_entries() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "UserAssist is a Windows registry artifact"}

    script = (
        "function Decode-Rot13($s){"
        "-join ($s.ToCharArray() | ForEach-Object {"
        "$c=[int][char]$_;"
        "if($c -ge 65 -and $c -le 90){[char]((($c-65+13)%26)+65)}"
        "elseif($c -ge 97 -and $c -le 122){[char]((($c-97+13)%26)+97)}"
        "else{[char]$c}"
        "})"
        "};"
        "$base='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist';"
        "$out=@();"
        "if(Test-Path $base){"
        "Get-ChildItem $base -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -eq 'Count' } | ForEach-Object {"
        "$props=Get-ItemProperty $_.PSPath;"
        "$props.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } | ForEach-Object {"
        "$decoded=Decode-Rot13 $_.Name;"
        "$lastRun=$null;"
        "if($_.Value -is [byte[]] -and $_.Value.Length -ge 16){"
        "  $ft=[BitConverter]::ToUInt64($_.Value,8);"
        "  if($ft -gt 0){ $lastRun=$ft }"
        "};"
        "$matches=@();"
        "$out += [pscustomobject]@{DecodedPath=$decoded; MatchedKeywords=$matches; LastRunFileTimeUtc=$lastRun}"
        "}"
        "}"
        "};"
        "$out | Select-Object -First 220 | ConvertTo-Json -Depth 4"
    )
    raw = run_command(["powershell", "-NoProfile", "-Command", script])[:16000]
    structured: list[dict] = []
    try:
        parsed = json.loads(raw) if raw and not raw.startswith("Unavailable:") else []
        rows = parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            path = str(row.get("DecodedPath") or "")
            last_run = normalize_event_time(row.get("LastRunFileTimeUtc"))
            display_at, timestamp_source = resolve_display_timestamp(primary=last_run)
            profile = suspicious_path_profile(path) if path else {
                "executor_name_hits": [],
                "cheat_filename_hints": [],
                "name_anomaly_reasons": [],
            }
            if path and not profile["executor_name_hits"]:
                profile["executor_name_hits"] = loose_executor_labels_for_artifact(path)
            matched_kw = list(row.get("MatchedKeywords") or [])
            if not matched_kw and profile["executor_name_hits"]:
                matched_kw = profile["executor_name_hits"][:4]
            if not profile["executor_name_hits"] and not profile["cheat_filename_hints"]:
                continue
            structured.append(
                {
                    "path": path,
                    "matched_keywords": matched_kw,
                    "executor_name_hits": profile["executor_name_hits"],
                    "cheat_filename_hints": profile["cheat_filename_hints"],
                    "last_run_utc": last_run,
                    "display_at": display_at,
                    "timestamp_source": timestamp_source,
                }
            )
    except json.JSONDecodeError:
        structured = []
    return {
        "available": True,
        "source": "HKCU Software Microsoft Windows CurrentVersion Explorer UserAssist",
        "raw_sample": raw,
        "items": structured[:120],
        "note": "UserAssist entries include last-run timestamps when the Count blob is available.",
    }


def _normalize_powershell_list(data: object) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def windows_defender_signals() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows Defender signals are Windows-only"}

    status_script = (
        "try { Get-MpComputerStatus | Select-Object AMServiceEnabled,AntispywareEnabled,"
        "AntivirusEnabled,RealTimeProtectionEnabled,IoavProtectionEnabled,NISEnabled,"
        "QuickScanAge,FullScanAge,IsTamperProtected,AntivirusSignatureLastUpdated | "
        "ConvertTo-Json -Depth 3 } catch { '{}' }"
    )
    preference_script = (
        "try {"
        "$p=Get-MpPreference;"
        "[pscustomobject]@{"
        "DisableRealtimeMonitoring=$p.DisableRealtimeMonitoring;"
        "ExclusionPath=$p.ExclusionPath;"
        "ExclusionProcess=$p.ExclusionProcess;"
        "ExclusionExtension=$p.ExclusionExtension;"
        "PUAProtection=$p.PUAProtection"
        "} | ConvertTo-Json -Depth 4"
        "} catch { '{}' }"
    )
    threat_script = (
        "try { Get-MpThreatDetection -ErrorAction SilentlyContinue | "
        "Select-Object -First 60 DetectionTime,ActionSuccess,Resources,ThreatID,"
        "InitialDetectionTime,ProcessName,ThreatName,DomainUser | ConvertTo-Json -Depth 5"
        "} catch { '[]' }"
    )
    history_script = (
        "$start=(Get-Date).AddDays(-14);"
        "Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Windows Defender/Operational'; StartTime=$start} "
        "-ErrorAction SilentlyContinue | "
        "Where-Object { $_.Id -in @(1116,1117,1118,1119,1120,1121,1150,1151,5008,5010,5012) } | "
        "Select-Object -First 80 TimeCreated,Id,LevelDisplayName,Message | ConvertTo-Json -Depth 3"
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        status_future = pool.submit(forensic_powershell_json, status_script, 14.0, 8000)
        settings_future = pool.submit(forensic_powershell_json, preference_script, 12.0, 12000)
        threat_future = pool.submit(forensic_powershell_json, threat_script, 16.0, 28000)
        history_future = pool.submit(
            run_command, ["powershell", "-NoProfile", "-Command", history_script], 18, 20000
        )
        computer_status = status_future.result()
        settings_data = settings_future.result()
        threat_detections = _normalize_powershell_list(threat_future.result())
        history = history_future.result()

    settings = settings_data if isinstance(settings_data, dict) else {}
    status = computer_status if isinstance(computer_status, dict) else {}
    quarantine_history: list[dict] = []
    for entry in threat_detections:
        resources = entry.get("Resources")
        if isinstance(resources, list):
            resource_text = " ".join(str(item) for item in resources)
        else:
            resource_text = str(resources or "")
        blob = f"{resource_text} {entry.get('ThreatName') or ''} {entry.get('ActionSuccess') or ''}".lower()
        if any(token in blob for token in ("quarantine", "removed", "malware", "threat", "blocked")):
            quarantine_history.append(entry)

    user_exclusions = [
        str(path)
        for path in (settings.get("ExclusionPath") or [])
        if any(marker in str(path).lower() for marker in ("\\users\\", "\\downloads", "\\desktop", "\\appdata\\local\\temp"))
    ]

    return {
        "available": True,
        "computer_status": status,
        "settings": json.dumps(settings, ensure_ascii=False)[:12000] if settings else "",
        "settings_structured": settings,
        "threat_detections": threat_detections[:60],
        "quarantine_history": quarantine_history[:40],
        "protection_history": history[:20000],
        "summary": {
            "real_time_protection_enabled": status.get("RealTimeProtectionEnabled"),
            "tamper_protection_enabled": status.get("IsTamperProtected"),
            "antivirus_enabled": status.get("AntivirusEnabled"),
            "threat_detection_count": len(threat_detections),
            "quarantine_count": len(quarantine_history),
            "user_profile_exclusion_count": len(user_exclusions),
            "realtime_monitoring_disabled": settings.get("DisableRealtimeMonitoring") is True,
        },
    }


def windows_security_event_summary() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows Security event log is Windows-only"}

    script = (
        "$start=(Get-Date).AddDays(-14);"
        "$ids=4624,4625,4688,4697,4698,4720,4722,4723,4724,4728,4732,1102;"
        "Get-WinEvent -FilterHashtable @{LogName='Security'; StartTime=$start} -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Id -in $ids } | "
        "Select-Object -First 100 TimeCreated,Id,ProviderName,Message | ConvertTo-Json -Depth 3"
    )
    events = _normalize_powershell_list(forensic_powershell_json(script, timeout=22.0, max_chars=28000))
    return {
        "available": True,
        "log": "Security",
        "window": "last 14 days",
        "event_ids_tracked": [4624, 4625, 4688, 4697, 4698, 4720, 4722, 4723, 4724, 4728, 4732, 1102],
        "events": events[:100],
        "count": len(events),
    }


def powershell_operational_events() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "PowerShell operational log is Windows-only"}

    script = (
        "$start=(Get-Date).AddDays(-14);"
        "Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; StartTime=$start; Id=@(4103,4104,53504)} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object -First 80 TimeCreated,Id,ProviderName,Message | ConvertTo-Json -Depth 3"
    )
    events = _normalize_powershell_list(forensic_powershell_json(script, timeout=20.0, max_chars=26000))
    return {
        "available": True,
        "log": "Microsoft-Windows-PowerShell/Operational",
        "window": "last 14 days",
        "events": events[:80],
        "count": len(events),
    }


def windows_service_change_events() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows service change events are Windows-only"}

    script = (
        "$start=(Get-Date).AddDays(-30);"
        "Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$start; Id=@(7036,7040,7045)} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object -First 100 TimeCreated,Id,ProviderName,Message | ConvertTo-Json -Depth 3"
    )
    events = _normalize_powershell_list(forensic_powershell_json(script, timeout=18.0, max_chars=24000))
    return {
        "available": True,
        "log": "System",
        "window": "last 30 days",
        "event_ids_tracked": [7036, 7040, 7045],
        "events": events[:100],
        "count": len(events),
    }


def windows_event_log_summary() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows Event Logs are only available on Windows"}

    script = (
        "$start=(Get-Date).AddDays(-7);"
        "Get-WinEvent -FilterHashtable @{LogName=@('Application','System'); StartTime=$start} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object -First 120 TimeCreated,ProviderName,Id,LevelDisplayName,Message | "
        "ConvertTo-Json -Depth 3"
    )
    output = run_command(["powershell", "-NoProfile", "-Command", script])
    return {
        "available": True,
        "logs": ["Application", "System"],
        "window": "last 7 days",
        "raw_sample": output[:20000],
    }


def xml_event_log_files() -> dict:
    roots = []
    if platform.system() == "Windows":
        for env_name in ["USERPROFILE", "LOCALAPPDATA", "APPDATA"]:
            value = os.getenv(env_name)
            if value:
                roots.append(Path(value))
    else:
        roots.append(Path.home())

    items = []
    for root in roots:
        if not root.exists():
            continue
        try:
            matches = list(root.rglob("*.xml"))[:300]
        except Exception:
            matches = []
        for path in matches:
            lowered = path.name.lower()
            parent = str(path.parent).lower()
            if "event" not in lowered and "event" not in parent and "log" not in lowered:
                continue
            try:
                stat = path.stat()
                items.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                        "size_bytes": stat.st_size,
                    }
                )
            except Exception:
                continue
    items.sort(key=lambda item: item["modified"], reverse=True)
    return {"count": len(items[:80]), "items": items[:80]}


def recent_items_metadata() -> dict:
    folders = []
    if platform.system() == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            folders.append(Path(appdata) / "Microsoft" / "Windows" / "Recent")
            folders.append(Path(appdata) / "Microsoft" / "Windows" / "Recent" / "AutomaticDestinations")
            folders.append(Path(appdata) / "Microsoft" / "Windows" / "Recent" / "CustomDestinations")
        userprofile = os.getenv("USERPROFILE")
        if userprofile:
            folders.extend(
                [
                    Path(userprofile) / "Downloads",
                    Path(userprofile) / "Desktop",
                    Path(userprofile) / "Documents",
                ]
            )
    else:
        folders.extend([Path.home() / "Downloads", Path.home() / "Desktop"])

    items = []
    patterns = executor_name_patterns()
    seen: set[str] = set()
    for folder in folders:
        if not folder.exists():
            continue
        try:
            paths = list(folder.rglob("*"))[:500] if folder.name in {"Recent", "AutomaticDestinations", "CustomDestinations"} else list(folder.iterdir())
        except Exception:
            continue
        for path in paths:
            try:
                if not path.is_file():
                    continue
                stat = path.stat()
                fname = path.name
                full_path = str(path)
                matched_exec = [label for label, pat in patterns.items() if pat.search(full_path)]
                cheat_hints = cheat_path_hint_labels(full_path)
                target_path = full_path
                if path.suffix.lower() == ".lnk":
                    try:
                        lnk_data = path.read_bytes()[:1_500_000]
                        for extracted in extract_dos_paths_from_binary(
                            lnk_data,
                            limit=4,
                            require_executor_label=False,
                            executable_only=True,
                        ):
                            matched_exec = sorted(
                                set(matched_exec + executor_labels_for_artifact_text(extracted))
                            )
                            if not matched_exec:
                                matched_exec = _probe_executable_binary_labels(Path(extracted)) if Path(extracted).exists() else []
                            if matched_exec:
                                target_path = extracted
                                break
                    except OSError:
                        pass
                if not matched_exec and not cheat_hints:
                    continue
                dedupe = target_path.lower()
                if dedupe in seen:
                    continue
                seen.add(dedupe)
                items.append(
                    {
                        "name": fname,
                        "folder": str(folder),
                        "path": target_path,
                        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                        "size_bytes": stat.st_size,
                        "matched_indicator_names": matched_exec,
                        "matched_cheat_filename_hints": cheat_hints,
                    }
                )
            except Exception:
                continue
    items.sort(key=lambda item: item["modified"], reverse=True)
    return {
        "count": len(items[:400]),
        "items": items[:400],
        "note": "Recent shortcuts and folders; .lnk targets are parsed for executor paths and binary branding.",
    }


def command_history_keyword_hits() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "PowerShell/CMD history paths are Windows-focused in this prototype"}

    candidates = []
    appdata = os.getenv("APPDATA")
    userprofile = os.getenv("USERPROFILE")
    if appdata:
        candidates.append(Path(appdata) / "Microsoft" / "Windows" / "PowerShell" / "PSReadLine" / "ConsoleHost_history.txt")
    if userprofile:
        candidates.append(Path(userprofile) / "AppData" / "Roaming" / "Microsoft" / "Windows" / "PowerShell" / "PSReadLine" / "ConsoleHost_history.txt")

    keywords = EXECUTOR_NAMES + [
        "prefetch",
        "usn",
        "fsutil",
        "journal",
        "wevtutil",
        "clear-log",
        "Clear-EventLog",
        "Set-MpPreference",
        "Add-MpPreference",
        "Unblock-File",
        "Clear-RecycleBin",
        "$Recycle.Bin",
        "Remove-Item",
        "rd /s",
        "del /f",
        "cipher /w",
        "deletejournal",
        "vssadmin",
    ]
    hits = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            stat = path.stat()
            file_mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        except OSError:
            file_mtime = None
        try:
            lines = path.read_text(errors="replace").splitlines()[-500:]
        except Exception:
            continue
        total = len(lines)
        for offset, line in enumerate(lines):
            matched = [keyword for keyword in keywords if keyword.lower() in line.lower()]
            if not matched:
                continue
            lines_from_end = total - offset
            occurred_at = file_mtime
            hits.append(
                {
                    "path": str(path),
                    "line_number_from_tail": lines_from_end,
                    "matched": matched,
                    "line": line[:500],
                    "history_file_modified_utc": file_mtime,
                    "occurred_at": occurred_at,
                    "timestamp_source": "powershell_history_file_mtime",
                    "timeline_note": (
                        "PSReadLine history is a plain text log without per-line UTC clocks. "
                        "The time shown is when this history file was last updated on disk — "
                        "usually close to when recent commands (low 'lines from end') were run."
                    ),
                    "lines_from_end": lines_from_end,
                }
            )
    return {
        "available": True,
        "hits": hits[:120],
        "note": "Matched PowerShell lines include history-file mtime as the best available activity time.",
    }


def windows_service_signals() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows services are Windows-only"}

    services = ["SysMain", "EventLog", "WinDefend", "SecurityHealthService", "DiagTrack", "PcaSvc"]
    script = (
        "$names=@('SysMain','EventLog','WinDefend','SecurityHealthService','DiagTrack','PcaSvc');"
        "$names | ForEach-Object {"
        "$s=Get-Service -Name $_ -ErrorAction SilentlyContinue;"
        "if($s){ [pscustomobject]@{Name=$s.Name; DisplayName=$s.DisplayName; Status=$s.Status; StartType=$s.StartType} }"
        "} | ConvertTo-Json -Depth 3"
    )
    return {"available": True, "services_checked": services, "raw": run_command(["powershell", "-NoProfile", "-Command", script])[:8000]}


def usb_event_summary() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "USB event summary is Windows-only"}

    script = (
        "$start=(Get-Date).AddDays(-30);"
        "Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=$start; Id=@(20001,20003,2100,2101,2102,2105,2106)} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object -First 80 TimeCreated,ProviderName,Id,Message | ConvertTo-Json -Depth 3"
    )
    return {
        "available": True,
        "window": "last 30 days",
        "raw_sample": run_command(["powershell", "-NoProfile", "-Command", script])[:20000],
    }


def shellbag_clear_signal() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Shellbag signal is Windows-only"}

    script = (
        "$paths=@("
        "'HKCU:\\Software\\Microsoft\\Windows\\Shell\\BagMRU',"
        "'HKCU:\\Software\\Microsoft\\Windows\\ShellNoRoam\\BagMRU'"
        ");"
        "$paths | ForEach-Object {"
        "$exists=Test-Path $_;"
        "$count=0;"
        "if($exists){ $count=(Get-ChildItem $_ -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count }"
        "[pscustomobject]@{Path=$_; Exists=$exists; KeyCount=$count}"
        "} | ConvertTo-Json -Depth 3"
    )
    return {
        "available": True,
        "raw": run_command(["powershell", "-NoProfile", "-Command", script])[:8000],
        "note": "Very low shellbag key counts can be a clearing signal but are not proof by themselves.",
    }


def deletion_and_log_clearing_signals() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Deletion/log clearing signals are Windows-only"}

    event_script = (
        "$start=(Get-Date).AddDays(-30);"
        "$events=@();"
        "$events += Get-WinEvent -FilterHashtable @{LogName=@('System','Security','Application'); StartTime=$start} -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Id -in @(104,1102,1100,1104,1105,3079,4660,4663) -or $_.Message -match 'journal|usn|deleted|cleared|truncate|recycle' };"
        "$events += Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Sysmon/Operational'; StartTime=$start; Id=@(23,26)} -ErrorAction SilentlyContinue;"
        "$events | Sort-Object TimeCreated -Descending | "
        "Select-Object -First 100 TimeCreated,LogName,ProviderName,Id,Message | ConvertTo-Json -Depth 3"
    )
    security_script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$start=(Get-Date).AddDays(-30);"
        "$sec = @();"
        "try {"
        " $sec = Get-WinEvent -FilterHashtable @{LogName='Security'; StartTime=$start; Id=4660,4663,4656} -MaxEvents 600 -ErrorAction SilentlyContinue |"
        "   Where-Object { $_.Message -match '(?i)delete|eliminated|removed|recycle' } |"
        "   Select-Object -First 120 @{N='TimeCreated';E={$_.TimeCreated.ToString('u')}},Id,"
        "   @{N='Message';E={ if ($_.Message.Length -gt 1400) { $_.Message.Substring(0,1400) } else { $_.Message } }}"
        "} catch {};"
        "$sm = @();"
        "try {"
        " $sm = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Sysmon/Operational'; StartTime=$start; Id=23,26} -MaxEvents 300 -ErrorAction SilentlyContinue |"
        "   Select-Object -First 100 @{N='TimeCreated';E={$_.TimeCreated.ToString('u')}},Id,"
        "   @{N='Message';E={ if ($_.Message.Length -gt 1600) { $_.Message.Substring(0,1600) } else { $_.Message } }}"
        "} catch {};"
        "$recycleEmpty = @();"
        "try {"
        " $recycleEmpty = Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=$start} -MaxEvents 400 -ErrorAction SilentlyContinue |"
        "   Where-Object { $_.Message -match '(?i)recycle|empty.*trash|shell32' } |"
        "   Select-Object -First 25 @{N='TimeCreated';E={$_.TimeCreated.ToString('u')}},Id,ProviderName,"
        "   @{N='Message';E={ if ($_.Message.Length -gt 900) { $_.Message.Substring(0,900) } else { $_.Message } }}"
        "} catch {};"
        "[pscustomobject]@{"
        " security_object_deletion_events = @($sec);"
        " sysmon_file_delete_events = @($sm);"
        " recycle_empty_events = @($recycleEmpty)"
        "} | ConvertTo-Json -Depth 5 -Compress"
    )
    ps = ["powershell", "-NoProfile", "-Command"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        event_future = pool.submit(run_command, ps + [event_script], 24, 24000)
        security_future = pool.submit(run_command, ps + [security_script], 32, 48000)
        usn_future = pool.submit(usn_journal_comprehensive_read)
        event_sample = event_future.result()
        security_raw = security_future.result()
        usn_pack = usn_future.result()
    try:
        extended_parsed = (
            json.loads(security_raw)
            if security_raw and not security_raw.startswith("Unavailable:")
            else {"raw": security_raw}
        )
    except json.JSONDecodeError:
        extended_parsed = {"json_parse_error": True, "raw_head": security_raw[:4000]}
    if isinstance(extended_parsed, dict):
        delete_lines = list(usn_pack.get("delete_lines") or [])
        extended_parsed["usn_file_delete_lines"] = delete_lines[:USN_DELETE_MAX_LINES]
        extended_parsed["usn_scan_source"] = usn_pack.get("source")

    usn_lines = list(usn_pack.get("delete_lines") or [])
    usn_text = "\n".join(str(line) for line in usn_lines)

    return {
        "available": True,
        "window": "last 30 days (events); comprehensive NTFS USN delete scan (recent journal tail)",
        "raw_sample": event_sample,
        "deleted_file_evidence": extended_parsed,
        "usn_delete_sample": usn_text[:120000],
        "usn_delete_line_count": len(usn_lines),
        "note": "Recycle Bin $I metadata shows files still in the bin. After emptying or Shift+Delete, BAM/Prefetch/registry "
        "traces remain; this section adds comprehensive USN FILE_DELETE recovery, Security 4660/4663, Sysmon ID 23/26, "
        "and recycle-empty event samples.",
    }


def _event_log_items(raw: object) -> list[dict]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        return [raw]
    return []


def _iso_epoch_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _duration_human(seconds: float) -> str:
    if seconds < 0:
        seconds = abs(seconds)
    if seconds < 90:
        return f"{int(round(seconds))} seconds"
    if seconds < 5400:
        minutes = max(1, int(round(seconds / 60)))
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    if seconds < 172800:
        hours = round(seconds / 3600, 1)
        return f"{hours} hours"
    days = round(seconds / 86400, 1)
    return f"{days} days"


def _format_report_datetime_dd_mm_yyyy(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%d/%m/%Y %H:%M:%S UTC")
    except ValueError:
        return None


def probe_usn_journal_health() -> dict[str, object]:
    if platform.system() != "Windows":
        return {"available": False, "drives": [], "disabled_drives": []}
    drives: list[dict[str, object]] = []
    for letter in string.ascii_uppercase:
        root = Path(f"{letter}:\\")
        if not root.exists():
            continue
        out = run_command(["fsutil", "usn", "queryjournal", f"{letter}:"], timeout=10, max_chars=4000)
        entry: dict[str, object] = {"drive": f"{letter}:", "raw_head": (out or "")[:600]}
        low = (out or "").lower()
        if not out or out.startswith("Unavailable"):
            entry["status"] = "unreadable"
            entry["impact"] = "Could not read USN journal status on this volume."
        elif any(
            phrase in low
            for phrase in (
                "no usn journal",
                "journal not active",
                "does not have a usn journal",
                "usn journal is not active",
            )
        ):
            entry["status"] = "disabled_or_missing"
            entry["impact"] = (
                "NTFS change journaling is off or missing on this volume. Create, rename, and delete "
                "activity cannot be reconstructed from USN here."
            )
        else:
            entry["status"] = "active"
            for pattern, key in (
                (r"Max USN\s*:\s*(0x[0-9a-fA-F]+|\d+)", "max_usn"),
                (r"Next USN\s*:\s*(0x[0-9a-fA-F]+|\d+)", "next_usn"),
                (r"Usn Journal ID\s*:\s*(0x[0-9a-fA-F]+|\d+)", "journal_id"),
            ):
                match = re.search(pattern, out, re.I)
                if match:
                    entry[key] = match.group(1)
            max_match = re.search(r"Max USN\s*:\s*(0x[0-9a-fA-F]+|\d+)", out, re.I)
            if max_match:
                raw = max_match.group(1)
                try:
                    max_val = int(raw, 16) if str(raw).lower().startswith("0x") else int(raw)
                    if max_val < 1_000_000:
                        entry["possibly_recreated"] = True
                        entry["impact"] = (
                            "USN Max USN is unusually low — the journal may have been deleted and recreated recently."
                        )
                except ValueError:
                    pass
        drives.append(entry)
    disabled = [str(item.get("drive") or "") for item in drives if item.get("status") != "active"]
    return {"available": True, "drives": drives, "disabled_drives": disabled}


def build_filesystem_evidence_integrity(
    *,
    deletion: dict,
    command_history: dict,
    services: dict | None = None,
) -> dict[str, object]:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Filesystem evidence integrity checks are Windows-only"}

    usn_health = probe_usn_journal_health()
    findings: list[dict[str, object]] = []
    evidence = deletion.get("deleted_file_evidence")
    raw_sample = str(deletion.get("raw_sample") or "")
    clearing_blob = f"{raw_sample}\n{deletion.get('usn_delete_sample') or ''}"

    def add_finding(
        *,
        severity: str,
        category: str,
        action: str,
        detail: str,
        impact: str,
        occurred_at: str | None = None,
        evidence_source: str | None = None,
    ) -> None:
        findings.append(
            {
                "severity": severity,
                "category": category,
                "action": action,
                "detail": detail,
                "impact": impact,
                "occurred_at": occurred_at,
                "occurred_at_display": _format_report_datetime_dd_mm_yyyy(occurred_at),
                "evidence_source": evidence_source,
            }
        )

    for drive_row in usn_health.get("drives") or []:
        status = str(drive_row.get("status") or "")
        drive = str(drive_row.get("drive") or "")
        if status == "disabled_or_missing":
            add_finding(
                severity="high",
                category="usn_journal",
                action="disabled",
                detail=f"USN Change Journal is not active on {drive}.",
                impact=(
                    "File create, rename, and delete reconstruction from USN is unavailable on this volume. "
                    "Reviews must rely on Recycle Bin metadata, BAM, Prefetch, PCA, registry artifacts, and event logs."
                ),
                evidence_source="fsutil usn queryjournal",
            )
        elif status == "unreadable":
            add_finding(
                severity="medium",
                category="usn_journal",
                action="unreadable",
                detail=f"USN journal status could not be read on {drive}.",
                impact="USN-based delete timelines for this volume may be incomplete in this scan.",
                evidence_source="fsutil usn queryjournal",
            )
        elif drive_row.get("possibly_recreated"):
            add_finding(
                severity="high",
                category="usn_journal",
                action="recreated",
                detail=f"USN journal on {drive} shows a very low Max USN value.",
                impact=(
                    "A deleted and recreated USN journal wipes prior NTFS lifecycle history on that volume. "
                    "Only activity after recreation can be reconstructed from USN."
                ),
                evidence_source="fsutil usn queryjournal",
            )

    tamper_patterns = (
        (r"fsutil\s+usn\s+deletejournal", "deleted", "usn_journal", "high"),
        (r"deletejournal\s+/d", "deleted", "usn_journal", "high"),
        (r"wevtutil\s+cl|Clear-EventLog", "cleared", "event_log", "high"),
        (r"vssadmin\s+delete\s+shadows", "deleted", "volume_shadow_copy", "high"),
        (r"Clear-RecycleBin", "emptied", "recycle_bin", "medium"),
    )
    for hit in (command_history.get("hits") or [])[:80]:
        line = str(hit.get("line") or "")
        for pattern, action, category, severity in tamper_patterns:
            if re.search(pattern, line, re.I):
                add_finding(
                    severity=severity,
                    category=category,
                    action=action,
                    detail=f"PowerShell history contains: {line[:240]}",
                    impact=_filesystem_tamper_impact(category, action),
                    occurred_at=normalize_event_time(hit.get("occurred_at")),
                    evidence_source="powershell_history",
                )
                break

    for match in re.finditer(
        r"TimeCreated[^}]*?(\d{4}-\d{2}-\d{2}T[^\"\\]+).*?(?:Id[\"']?\s*:\s*(\d+)).*?(?:Message[\"']?\s*:\s*\"([^\"]{0,400}))",
        raw_sample,
        re.I | re.S,
    ):
        event_id = match.group(2)
        message = match.group(3)
        occurred_at = normalize_event_time(match.group(1))
        if event_id == "3079" or re.search(r"usn.*journal.*delet", message, re.I):
            add_finding(
                severity="high",
                category="usn_journal",
                action="deleted",
                detail=f"System event ID {event_id or '?'} references USN journal deletion.",
                impact=_filesystem_tamper_impact("usn_journal", "deleted"),
                occurred_at=occurred_at,
                evidence_source="windows_event_log",
            )
        elif event_id in {"104", "1102", "1100"}:
            add_finding(
                severity="medium",
                category="event_log",
                action="cleared",
                detail=f"System event ID {event_id} indicates log clearing or logging service interruption.",
                impact=_filesystem_tamper_impact("event_log", "cleared"),
                occurred_at=occurred_at,
                evidence_source="windows_event_log",
            )

    if re.search(r"fsutil\s+usn\s+deletejournal|deletejournal\s+/d", clearing_blob, re.I):
        add_finding(
            severity="high",
            category="usn_journal",
            action="deleted",
            detail="Collected Windows event text mentions fsutil USN deletejournal activity.",
            impact=_filesystem_tamper_impact("usn_journal", "deleted"),
            evidence_source="deletion_event_sample",
        )

    services_raw = str((services or {}).get("raw") or "")
    if services_raw and re.search(r'"Name"\s*:\s*"EventLog"[^}]*"Status"\s*:\s*(?:1|"Stopped")', services_raw, re.I):
        add_finding(
            severity="high",
            category="event_log",
            action="service_stopped",
            detail="Windows Event Log service is not running.",
            impact=(
                "Security audit deletes, Recycle Bin emptying logs, and USN deletion events may not be recorded "
                "while the service is stopped."
            ),
            evidence_source="windows_services",
        )
    if services_raw and not re.search(r"Sysmon", services_raw, re.I):
        sysmon_log_missing = True
        if isinstance(evidence, dict):
            sysmon_rows = _event_log_items(evidence.get("sysmon_file_delete_events"))
            sysmon_log_missing = len(sysmon_rows) == 0
        if sysmon_log_missing:
            add_finding(
                severity="medium",
                category="sysmon",
                action="unavailable",
                detail="Sysmon file-delete telemetry was not collected (service absent or log empty).",
                impact=(
                    "Independent Sysmon delete events will be missing. USN, Security audit, Recycle Bin metadata, "
                    "BAM, and Prefetch become more important for delete reconstruction."
                ),
                evidence_source="windows_services_and_event_log",
            )

    usn_lines_read = int(deletion.get("usn_delete_line_count") or 0)
    active_drives = [
        str(row.get("drive") or "")
        for row in (usn_health.get("drives") or [])
        if row.get("status") == "active"
    ]
    if active_drives and usn_lines_read == 0:
        add_finding(
            severity="medium",
            category="usn_journal",
            action="no_delete_rows",
            detail="USN journal is active but this scan recovered zero delete rows from the sampled journal tail.",
            impact=(
                "Recent delete reconstruction may be limited to Recycle Bin metadata, BAM, Prefetch, and event logs. "
                "The journal tail may have rotated past older deletes."
            ),
            evidence_source="usn_journal_scan",
        )

    confidence = "normal"
    if any(item.get("category") == "usn_journal" and item.get("action") in {"disabled", "deleted", "recreated"} for item in findings):
        confidence = "severely_limited"
    elif findings:
        confidence = "reduced"

    return {
        "available": True,
        "usn_journal_health": usn_health,
        "finding_count": len(findings),
        "findings": findings[:40],
        "reconstruction_confidence": confidence,
        "impact_summary": _filesystem_reconstruction_summary(findings, usn_health),
        "note": "Summarizes whether USN journaling, event logs, and related services appear intact for delete reconstruction.",
    }


def _filesystem_tamper_impact(category: str, action: str) -> str:
    impacts = {
        ("usn_journal", "disabled"): (
            "With USN journaling disabled, NTFS no longer records a durable change history on that volume. "
            "Delete and rename timelines must be rebuilt from Recycle Bin metadata, BAM, Prefetch, PCA, registry, "
            "and Windows event logs only."
        ),
        ("usn_journal", "deleted"): (
            "Deleting the USN journal erases prior NTFS change history on that volume. Deletes that happened before "
            "the wipe cannot be reconstructed from USN."
        ),
        ("usn_journal", "recreated"): (
            "A recreated USN journal starts history from scratch. Only filesystem activity after recreation remains "
            "visible in USN samples."
        ),
        ("event_log", "cleared"): (
            "Cleared event logs remove Recycle Bin emptying records, audit delete entries, and USN deletion events "
            "that reviewers would normally use to time cover-up activity."
        ),
        ("event_log", "service_stopped"): (
            "While the Event Log service is stopped, new delete and cleanup events may never be written."
        ),
        ("volume_shadow_copy", "deleted"): (
            "Deleted shadow copies can remove volume snapshots that might otherwise preserve older file metadata."
        ),
        ("recycle_bin", "emptied"): (
            "Manual Recycle Bin emptying is normal, but when paired with suspicious deletes it shortens the window "
            "where $I metadata is still available."
        ),
        ("sysmon", "unavailable"): (
            "Without Sysmon delete telemetry, reviewers depend more heavily on USN, Security audit, and artifact traces."
        ),
    }
    return impacts.get(
        (category, action),
        "This change can reduce how completely file deletion and cleanup activity can be reconstructed.",
    )


def _filesystem_reconstruction_summary(findings: list[dict], usn_health: dict) -> str:
    if not findings and not (usn_health.get("disabled_drives") or []):
        return (
            "USN journaling and sampled event-log sources look intact. Delete reconstruction can use Recycle Bin "
            "metadata, USN delete rows, BAM, Prefetch, and audit events together."
        )
    parts: list[str] = []
    if usn_health.get("disabled_drives"):
        parts.append(
            f"USN journaling is disabled or unreadable on {', '.join(usn_health['disabled_drives'])}."
        )
    categories = sorted({str(item.get("category") or "") for item in findings if item.get("category")})
    if categories:
        parts.append(f"Tamper or integrity alerts were recorded for: {', '.join(categories)}.")
    parts.append(
        "When USN or event logs are disabled, cleared, or recreated, delete timelines fall back to surviving artifacts "
        "such as Recycle Bin $I metadata (while items remain), BAM, Prefetch, PCA, and registry traces."
    )
    return " ".join(parts)


def build_deletion_cleanup_analysis(
    *,
    trash: dict,
    deletion: dict,
    forensic_bundle: dict | None = None,
) -> dict[str, object]:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Deletion cleanup timing is Windows-only"}

    evidence = deletion.get("deleted_file_evidence")
    recycle_empty_events: list[dict[str, object]] = []
    for row in _event_log_items((evidence or {}).get("recycle_empty_events")):
        occurred_at = normalize_event_time(row.get("TimeCreated"))
        if not occurred_at:
            continue
        recycle_empty_events.append(
            {
                "occurred_at": occurred_at,
                "occurred_at_display": _format_report_datetime_dd_mm_yyyy(occurred_at),
                "source": "application_event_log",
                "event_id": row.get("Id"),
                "message": str(row.get("Message") or "")[:320],
            }
        )
    recycle_empty_events.sort(key=lambda row: row.get("occurred_at") or "")

    permanent_cleanup_events: list[dict[str, object]] = []
    for row in _event_log_items((evidence or {}).get("security_object_deletion_events")):
        message = str(row.get("Message") or "")
        if not re.search(r"(?i)recycle|\$recycle\.bin|\$I", message):
            continue
        occurred_at = normalize_event_time(row.get("TimeCreated"))
        if not occurred_at:
            continue
        permanent_cleanup_events.append(
            {
                "occurred_at": occurred_at,
                "occurred_at_display": _format_report_datetime_dd_mm_yyyy(occurred_at),
                "source": "security_audit",
                "event_id": row.get("Id"),
                "message": message[:320],
            }
        )
    permanent_cleanup_events.sort(key=lambda row: row.get("occurred_at") or "")

    trash_paths_now = {
        _artifact_path_key(str(item.get("original_path") or ""))
        for item in (trash or {}).get("items") or []
        if item.get("original_path")
    }
    file_deletions: list[dict[str, object]] = []
    seen_delete_paths: set[str] = set()

    def register_deletion(*, path: str, deleted_at: str | None, source: str, still_in_recycle_bin: bool) -> None:
        normalized = forensic_normalize_pathish(path)
        if not normalized:
            return
        ts = normalize_event_time(deleted_at)
        if not ts:
            return
        key = _artifact_path_key(normalized)
        if key in seen_delete_paths:
            return
        seen_delete_paths.add(key)
        file_deletions.append(
            {
                "path": normalized,
                "deleted_at": ts,
                "deleted_at_display": _format_report_datetime_dd_mm_yyyy(ts),
                "source": source,
                "still_in_recycle_bin": still_in_recycle_bin,
            }
        )

    for item in (trash or {}).get("items") or []:
        original = str(item.get("original_path") or "").strip()
        if not original:
            continue
        register_deletion(
            path=original,
            deleted_at=item.get("display_at") or item.get("deleted_at") or item.get("modified"),
            source="recycle_bin_metadata",
            still_in_recycle_bin=True,
        )

    usn_records = _collect_usn_records_for_removed_artifact_merge(forensic_bundle or {}, deletion or {})
    for row in usn_records:
        reasons = [str(reason).upper() for reason in (row.get("reasons") or [])]
        if not any("DELETE" in reason for reason in reasons):
            continue
        path = str(row.get("path") or "")
        if not path:
            continue
        key = _artifact_path_key(path)
        register_deletion(
            path=path,
            deleted_at=row.get("display_at") or row.get("timestamp_utc"),
            source="usn_delete",
            still_in_recycle_bin=key in trash_paths_now,
        )

    correlations: list[dict[str, object]] = []
    for deletion_row in sorted(file_deletions, key=lambda row: row.get("deleted_at") or "", reverse=True):
        path = str(deletion_row.get("path") or "")
        deleted_at = str(deletion_row.get("deleted_at") or "")
        deleted_epoch = _iso_epoch_seconds(deleted_at)
        if deleted_epoch is None:
            continue
        name = Path(path).name or path
        cleanup_at: str | None = None
        cleanup_type = "awaiting_cleanup"
        cleanup_source = None
        if deletion_row.get("still_in_recycle_bin"):
            cleanup_type = "still_in_recycle_bin"
        else:
            next_empty = next(
                (
                    event
                    for event in recycle_empty_events
                    if (_iso_epoch_seconds(str(event.get("occurred_at") or "")) or 0) >= deleted_epoch
                ),
                None,
            )
            if next_empty:
                cleanup_at = str(next_empty.get("occurred_at") or "")
                cleanup_type = "recycle_bin_emptied"
                cleanup_source = str(next_empty.get("source") or "")
            else:
                next_permanent = next(
                    (
                        event
                        for event in permanent_cleanup_events
                        if (_iso_epoch_seconds(str(event.get("occurred_at") or "")) or 0) >= deleted_epoch
                    ),
                    None,
                )
                if next_permanent:
                    cleanup_at = str(next_permanent.get("occurred_at") or "")
                    cleanup_type = "permanent_recycle_removal"
                    cleanup_source = str(next_permanent.get("source") or "")
                else:
                    cleanup_type = "removed_without_logged_empty"

        gap_seconds: float | None = None
        gap_human: str | None = None
        if cleanup_at:
            cleanup_epoch = _iso_epoch_seconds(cleanup_at)
            if cleanup_epoch is not None:
                gap_seconds = max(0.0, cleanup_epoch - deleted_epoch)
                gap_human = _duration_human(gap_seconds)

        summary = _deletion_cleanup_summary_text(
            name=name,
            deleted_at_display=deletion_row.get("deleted_at_display"),
            cleanup_at_display=_format_report_datetime_dd_mm_yyyy(cleanup_at),
            cleanup_type=cleanup_type,
            gap_human=gap_human,
        )
        correlations.append(
            {
                "path": path,
                "deleted_at": deleted_at,
                "deleted_at_display": deletion_row.get("deleted_at_display"),
                "cleanup_at": cleanup_at,
                "cleanup_at_display": _format_report_datetime_dd_mm_yyyy(cleanup_at),
                "cleanup_type": cleanup_type,
                "cleanup_source": cleanup_source,
                "gap_seconds": gap_seconds,
                "gap_human": gap_human,
                "still_in_recycle_bin": bool(deletion_row.get("still_in_recycle_bin")),
                "summary": summary,
            }
        )

    insights: list[str] = []
    timed = [row for row in correlations if row.get("gap_human")]
    if timed:
        sample = timed[0]
        insights.append(
            f"{Path(str(sample.get('path') or '')).name or 'A deleted file'} was removed from the Recycle Bin "
            f"{sample.get('gap_human')} after it was first deleted."
        )
    if recycle_empty_events:
        latest = recycle_empty_events[-1]
        insights.append(
            f"Recycle Bin emptying was logged on {latest.get('occurred_at_display') or latest.get('occurred_at')}."
        )
    if not correlations:
        insights.append("No per-file delete timestamps were available to measure cleanup timing.")

    return {
        "available": True,
        "recycle_empty_event_count": len(recycle_empty_events),
        "recycle_empty_events": recycle_empty_events[:20],
        "permanent_cleanup_event_count": len(permanent_cleanup_events),
        "file_deletion_count": len(file_deletions),
        "correlations": correlations[:80],
        "insights": insights,
        "note": (
            "Measures the time between a file delete (Recycle Bin $I metadata or USN FILE_DELETE) and the next "
            "logged Recycle Bin emptying or permanent Recycle Bin cleanup event."
        ),
    }


def _deletion_cleanup_summary_text(
    *,
    name: str,
    deleted_at_display: str | None,
    cleanup_at_display: str | None,
    cleanup_type: str,
    gap_human: str | None,
) -> str:
    deleted_text = deleted_at_display or "an unknown time"
    if cleanup_type == "still_in_recycle_bin":
        return f"{name} was deleted on {deleted_text} and is still in the Recycle Bin."
    if cleanup_type == "recycle_bin_emptied" and gap_human and cleanup_at_display:
        return (
            f"{name} was deleted on {deleted_text}; the Recycle Bin was emptied {gap_human} later "
            f"on {cleanup_at_display}."
        )
    if cleanup_type == "permanent_recycle_removal" and gap_human and cleanup_at_display:
        return (
            f"{name} was deleted on {deleted_text}; permanent Recycle Bin cleanup was logged {gap_human} later "
            f"on {cleanup_at_display}."
        )
    if cleanup_type == "removed_without_logged_empty":
        return (
            f"{name} was deleted on {deleted_text}, is no longer in the Recycle Bin, and no Recycle Bin emptying "
            "event was logged after that delete."
        )
    return f"{name} was deleted on {deleted_text}."


def bypass_resilience_signals(
    *,
    prefetch: dict,
    deletion: dict,
    defender: dict,
    shellbag: dict,
    bam: dict,
    forensic_bundle: dict,
    prefetch_health: dict,
    amcache: dict,
    command_history: dict,
    designated: dict | None = None,
    trash: dict | None = None,
    executor_artifact_evidence: dict | None = None,
) -> dict:
    """Correlate tamper, cover-up, and anti-forensics patterns across multiple independent sources."""
    if platform.system() != "Windows":
        return {"available": False, "reason": "Bypass resilience scan is Windows-only"}

    findings: list[dict] = []
    risk_score = 0

    def add(
        *,
        severity: str,
        title: str,
        detail: str,
        category: str,
        weight: int,
    ) -> None:
        nonlocal risk_score
        findings.append(
            {
                "severity": severity,
                "title": title,
                "detail": detail,
                "category": category,
            }
        )
        risk_score += weight

    reg_script = (
        "$out=[ordered]@{};"
        "try{$out.Prefetcher=(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters' -Name EnablePrefetcher -ErrorAction SilentlyContinue).EnablePrefetcher}catch{};"
        "try{$out.TrackedPrefetch=(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management\\PrefetchParameters' -Name EnablePrefetcher -ErrorAction SilentlyContinue).EnablePrefetcher}catch{};"
        "try{$out.BamDisabled=(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\bam\\State' -Name Start -ErrorAction SilentlyContinue).Start}catch{};"
        "try{$vss=Get-Service -Name VSS -ErrorAction SilentlyContinue;if($vss){$out.VssStatus=$vss.Status.ToString()}}catch{};"
        "try{$out.EventLogSvc=(Get-Service -Name EventLog -ErrorAction SilentlyContinue).Status.ToString()}catch{};"
        "$out | ConvertTo-Json -Compress"
    )
    reg_raw = run_command(["powershell", "-NoProfile", "-Command", reg_script], timeout=12, max_chars=4000)
    reg_data: dict = {}
    try:
        if reg_raw and not reg_raw.startswith("Unavailable:"):
            parsed = json.loads(reg_raw)
            if isinstance(parsed, dict):
                reg_data = parsed
    except json.JSONDecodeError:
        reg_data = {}

    prefetcher = reg_data.get("Prefetcher")
    if prefetcher == 0:
        add(
            severity="high",
            title="Runtime logging appears turned off",
            detail="Windows prefetching is disabled in the registry — a common way to hide which programs ran.",
            category="tamper",
            weight=18,
        )
    elif prefetch.get("available") and not (prefetch.get("items") or []):
        add(
            severity="medium",
            title="No runtime traces in the usual cache",
            detail="Prefetch folder is empty or unreadable while the feature should normally retain recent program traces.",
            category="cover_up",
            weight=12,
        )

    if str(reg_data.get("EventLogSvc") or "").lower() == "stopped":
        add(
            severity="high",
            title="System event logging is stopped",
            detail="The Windows Event Log service is not running, which reduces visibility into deletes and security events.",
            category="tamper",
            weight=20,
        )

    if str(reg_data.get("VssStatus") or "").lower() == "stopped":
        add(
            severity="medium",
            title="Shadow-copy service is stopped",
            detail="Volume Shadow Copy (restore points) is not running — sometimes disabled before cleanup or tampering.",
            category="tamper",
            weight=10,
        )

    defender_text = f"{defender.get('settings') or ''}\n{defender.get('protection_history') or ''}"
    if re.search(r"DisableRealtimeMonitoring\s*:\s*True", defender_text, re.I):
        add(
            severity="high",
            title="Real-time protection is off",
            detail="Windows Defender real-time monitoring is disabled on this machine.",
            category="defender",
            weight=22,
        )
    if re.search(r"ExclusionPath|ExclusionProcess|Add-MpPreference", defender_text, re.I):
        add(
            severity="medium",
            title="Defender exclusions are configured",
            detail="Antivirus exclusions can hide folders or programs from scanning — verify they are legitimate.",
            category="defender",
            weight=8,
        )

    clearing_blob = f"{deletion.get('raw_sample') or ''}\n{deletion.get('usn_delete_sample') or ''}"
    if re.search(
        r"wevtutil\s+cl|Clear-EventLog|fsutil\s+usn\s+deletejournal|vssadmin\s+delete\s+shadows|"
        r"Remove-Item.*Prefetch|del\s+/f.*\.pf|cipher\s+/w|Clear-RecycleBin|\$Recycle\.Bin|rd\s+/s\s+/q",
        clearing_blob,
        re.I,
    ):
        add(
            severity="high",
            title="Signs of log or trace cleanup",
            detail="Recent system events mention journal clears, log wipes, shadow-copy deletes, or prefetch cleanup language.",
            category="cover_up",
            weight=24,
        )
    if re.search(r"\b(104|1102|1100)\b", clearing_blob) and re.search(
        r"cleared|audit|log.*clear", clearing_blob, re.I
    ):
        add(
            severity="medium",
            title="Security or system logs were cleared recently",
            detail="Event IDs associated with log clearing appeared in the sampled Windows event history.",
            category="cover_up",
            weight=14,
        )

    shell_raw = str(shellbag.get("raw") or "")
    low_shellbag = False
    try:
        shell_parsed = json.loads(shell_raw) if shell_raw.strip().startswith("[") else json.loads(shell_raw)
        rows = shell_parsed if isinstance(shell_parsed, list) else [shell_parsed]
        for row in rows:
            if not isinstance(row, dict):
                continue
            count = int(row.get("KeyCount") or 0)
            if row.get("Exists") and count < 8:
                low_shellbag = True
    except (json.JSONDecodeError, TypeError, ValueError):
        if re.search(r'KeyCount["\s:]*[0-3]\b', shell_raw):
            low_shellbag = True
    if low_shellbag:
        add(
            severity="medium",
            title="Very little folder history remains",
            detail="Shell history registry keys are unusually empty — can happen after privacy cleaners or manual clearing.",
            category="cover_up",
            weight=11,
        )

    bam_items = list(bam.get("items") or [])
    if not bam_items and bam.get("available"):
        add(
            severity="medium",
            title="No recent program-run records found",
            detail="Execution history that Windows normally keeps was missing or empty on this scan.",
            category="ghost_trace",
            weight=10,
        )
    ghost_runs = [
        it
        for it in bam_items
        if it.get("last_execution_utc") and it.get("file_exists") is False and not it.get("path_allowlisted")
    ]
    if len(ghost_runs) >= 3:
        add(
            severity="high",
            title="Programs ran but files are gone",
            detail=f"{len(ghost_runs)} execution record(s) point to files that no longer exist on disk (possible delete-after-run).",
            category="ghost_trace",
            weight=16,
        )

    if amcache.get("available") and amcache.get("size_bytes", 1) == 0:
        add(
            severity="medium",
            title="Program inventory database looks empty",
            detail="The Amcache hive exists but has zero size — unusual on an active Windows install.",
            category="tamper",
            weight=9,
        )

    for hit in (command_history.get("hits") or [])[:40]:
        line = str(hit.get("line") or "")
        if re.search(
            r"wevtutil\s+cl|Clear-EventLog|fsutil\s+usn|vssadmin\s+delete|Remove-Item.*Prefetch|"
            r"Set-MpPreference.*DisableRealtimeMonitoring|Unblock-File|del\s+/[fq]|Clear-RecycleBin|\$Recycle\.Bin|"
            r"rd\s+/s\s+/q|cipher\s+/w",
            line,
            re.I,
        ):
            add(
                severity="high",
                title="Shell history mentions cleanup or disable commands",
                detail=f"PowerShell history contains a suspicious maintenance command: {line[:220]}",
                category="cover_up",
                weight=20,
            )
            break

    wmi_script = (
        "Get-CimInstance -Namespace root\\subscription -ClassName __EventFilter -ErrorAction SilentlyContinue | "
        "Select-Object -First 20 Name, Query | ConvertTo-Json -Compress"
    )
    wmi_raw = run_command(["powershell", "-NoProfile", "-Command", wmi_script], timeout=14, max_chars=8000)
    if wmi_raw and not wmi_raw.startswith("Unavailable:"):
        if re.search(r"CommandLineEventConsumer|ActiveScriptEventConsumer|FROM\s+__Instance", wmi_raw, re.I):
            add(
                severity="high",
                title="Hidden auto-run hooks in WMI",
                detail="WMI event subscription filters were found — a stealth persistence method sometimes used by bypass tools.",
                category="persistence",
                weight=18,
            )

    motw_script = (
        "$root=Join-Path $env:USERPROFILE 'Downloads';"
        "if(-not(Test-Path $root)){ '[]' } else {"
        "Get-ChildItem $root -File -Include *.exe,*.dll,*.bat,*.ps1 -ErrorAction SilentlyContinue | "
        "Sort-Object LastWriteTime -Descending | Select-Object -First 25 | ForEach-Object {"
        "$z=$_.FullName+':Zone.Identifier';"
        "[pscustomobject]@{Path=$_.FullName;HasZone=(Test-Path -LiteralPath $z);Modified=$_.LastWriteTimeUtc.ToString('u')}"
        "} | Where-Object { -not $_.HasZone } | Select-Object -First 8 | ConvertTo-Json -Compress"
        "}"
    )
    motw_raw = run_command(["powershell", "-NoProfile", "-Command", motw_script], timeout=14, max_chars=6000)
    try:
        motw_rows = json.loads(motw_raw) if motw_raw and motw_raw.strip().startswith("[") else []
        if isinstance(motw_rows, dict):
            motw_rows = [motw_rows]
        if isinstance(motw_rows, list) and len(motw_rows) >= 3:
            add(
                severity="medium",
                title="Recent downloads missing safety markers",
                detail=f"{len(motw_rows)} recent executable(s) in Downloads have no Zone.Identifier (mark-of-the-web) — can indicate manual unblocking or copying.",
                category="tamper",
                weight=10,
            )
    except json.JSONDecodeError:
        pass

    artifact_rows = list((executor_artifact_evidence or {}).get("hits") or [])
    deleted_artifact = [
        row for row in artifact_rows if row.get("file_exists") is False or row.get("removed_artifact")
    ]
    prefetch_artifact = [row for row in artifact_rows if row.get("artifact_source") == "prefetch_execution"]
    if deleted_artifact:
        sample = ", ".join(
            sorted({label for row in deleted_artifact[:8] for label in (row.get("executor_name_hits") or [])})[:5]
        )
        add(
            severity="high",
            title="Known executor left forensic traces after deletion",
            detail=(
                f"{len(deleted_artifact)} independent artifact(s) still reference a checked executor after the file or "
                f"folder was deleted or the Recycle Bin was emptied"
                + (f" ({sample})." if sample else ".")
            ),
            category="cover_up",
            weight=24,
        )
    elif prefetch_artifact:
        sample = ", ".join(
            sorted({label for row in prefetch_artifact[:6] for label in (row.get("executor_name_hits") or [])})[:5]
        )
        add(
            severity="high",
            title="Prefetch proves a checked executor ran",
            detail=(
                f"Windows Prefetch still contains execution residue for a checked executor"
                + (f" ({sample})." if sample else ".")
                + " Deleting the folder does not remove Prefetch."
            ),
            category="ghost_trace",
            weight=20,
        )

    removed_hits = [
        hit
        for hit in (designated or {}).get("hits") or []
        if hit.get("removed_artifact") and hit.get("path_allowlisted") is not True
    ]
    if removed_hits:
        executor_removed = [h for h in removed_hits if h.get("executor_name_hits")]
        cheat_removed = [
            h
            for h in removed_hits
            if (h.get("cheat_filename_hints") or h.get("name_anomaly_reasons"))
            and not h.get("executor_name_hits")
        ]
        if executor_removed:
            sample = ", ".join(
                sorted({label for hit in executor_removed[:6] for label in (hit.get("executor_name_hits") or [])})[:4]
            )
            add(
                severity="high",
                title="Deleted executor traces recovered",
                detail=(
                    f"{len(executor_removed)} executor path(s) were removed from disk or the Recycle Bin but still "
                    f"appear in BAM, USN, Prefetch, or download history"
                    + (f" ({sample})." if sample else ".")
                ),
                category="cover_up",
                weight=22,
            )
        elif cheat_removed:
            add(
                severity="high",
                title="Deleted cheat-like paths recovered",
                detail=(
                    f"{len(cheat_removed)} deleted path(s) with cheat/hack-style folder or file names were recovered "
                    "from Windows activity artifacts after cleanup."
                ),
                category="cover_up",
                weight=20,
            )
        elif len(removed_hits) >= 2:
            add(
                severity="medium",
                title="Multiple deleted suspicious paths recovered",
                detail=(
                    f"{len(removed_hits)} suspicious path(s) no longer on disk were reconstructed from independent "
                    "system traces — deleting folders or emptying the Recycle Bin does not erase this evidence."
                ),
                category="cover_up",
                weight=16,
            )

    suspicious_trash = [
        item
        for item in (trash or {}).get("items") or []
        if item.get("suspicious_recycle_item") and item.get("original_path")
    ]
    if suspicious_trash:
        add(
            severity="medium",
            title="Suspicious items sitting in Recycle Bin",
            detail=(
                f"{len(suspicious_trash)} Recycle Bin item(s) match executor or cheat path rules — emptying the bin "
                "will not remove USN, Prefetch, or execution history already collected."
            ),
            category="cover_up",
            weight=14,
        )

    trash_paths = {
        _artifact_path_key(str(item.get("original_path") or ""))
        for item in (trash or {}).get("items") or []
        if item.get("original_path")
    }
    emptied_cover_up = [
        it
        for it in bam_items
        if it.get("executor_name_hits")
        and it.get("file_exists") is False
        and not it.get("path_allowlisted")
        and _artifact_path_key(str(it.get("normalized_path") or "")) not in trash_paths
    ]
    if emptied_cover_up:
        sample = ", ".join(
            sorted({label for row in emptied_cover_up[:6] for label in (row.get("executor_name_hits") or [])})[:4]
        )
        add(
            severity="high",
            title="Executor deleted and Recycle Bin cleared",
            detail=(
                f"{len(emptied_cover_up)} executor(s) ran on this PC but the file is gone and not in the Recycle Bin"
                + (f" ({sample})" if sample else "")
                + " — BAM/Prefetch/USN/registry traces still prove prior presence."
            ),
            category="cover_up",
            weight=26,
        )

    evidence = deletion.get("deleted_file_evidence")
    if isinstance(evidence, dict) and evidence.get("recycle_empty_events"):
        add(
            severity="medium",
            title="Recycle Bin emptying detected in event logs",
            detail=(
                "Application event logs contain recycle-bin emptying activity. If an executor was removed before this "
                "scan, independent BAM and Prefetch artifacts should still be reviewed."
            ),
            category="cover_up",
            weight=12,
        )

    deletion_usn = str(deletion.get("usn_delete_sample") or "")
    if deletion_usn and not deletion_usn.startswith("Unavailable"):
        profile_roots = (
            str(Path(os.getenv("USERPROFILE") or Path.home()).resolve()).lower()
            if platform.system() == "Windows"
            else str(Path.home()).lower()
        )
        suspicious_deletes = 0
        for line in deletion_usn.splitlines()[:800]:
            if "FILE_DELETE" not in line.upper():
                continue
            path_m = re.search(r"([A-Za-z]:\\(?:[^,\"\n\r\t|<>?]+))", line, re.IGNORECASE)
            if not path_m:
                continue
            candidate = path_m.group(1)
            if profile_roots and not candidate.lower().startswith(profile_roots):
                continue
            if path_is_suspicious_profile(candidate):
                suspicious_deletes += 1
        if suspicious_deletes >= 1:
            add(
                severity="high" if suspicious_deletes >= 2 else "medium",
                title="Recent cheat-path deletes in USN journal",
                detail=(
                    f"{suspicious_deletes} NTFS journal delete record(s) under the user profile matched executor or "
                    "cheat folder/file naming — evidence of cleanup after use."
                ),
                category="cover_up",
                weight=18 if suspicious_deletes >= 2 else 12,
            )

    if isinstance(forensic_bundle, dict) and forensic_bundle.get("available"):
        flat = list(forensic_bundle.get("detections_flat") or [])
        for det in flat[:80]:
            reason = str(det.get("reason") or "")
            if not reason or "Unified forensic pass completed" in reason:
                continue
            lower = reason.lower()
            if any(
                token in lower
                for token in (
                    "timestomp",
                    "alternate data stream",
                    "log clearing",
                    "delete event",
                    "rename-away",
                    "unsigned executable",
                    "crash loop",
                )
            ):
                sev = str(det.get("severity") or "medium").lower()
                weight = {"critical": 20, "high": 14, "medium": 8}.get(sev, 6)
                add(
                    severity=sev if sev in {"critical", "high", "medium", "low"} else "medium",
                    title="Cross-check found suspicious behavior",
                    detail=reason[:320],
                    category="correlation",
                    weight=weight,
                )
        chains = (forensic_bundle.get("unified_correlation") or {}).get("execution_chains") or []
        if len(chains) >= 2:
            add(
                severity="high",
                title="Multiple traces line up for the same program",
                detail=f"{len(chains)} independent trace chains matched the same program name — harder to fake than a single artifact.",
                category="correlation",
                weight=15,
            )

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda row: (severity_rank.get(str(row.get("severity")), 9), row.get("title") or ""))
    capped = min(100, risk_score)
    risk_level = "high" if capped >= 45 else "medium" if capped >= 20 else "low"
    return {
        "available": True,
        "finding_count": len(findings),
        "findings": findings[:40],
        "risk_score": capped,
        "risk_level": risk_level,
        "note": "Combines registry, defender, shell history, execution ghosts, WMI, downloads, and cross-artifact correlation.",
    }


def prefetch_health_signals(prefetch: dict) -> dict:
    if platform.system() != "Windows" or not prefetch.get("available"):
        return {"available": False, "reason": "Prefetch health signals require available Windows Prefetch metadata"}

    items = prefetch.get("items", [])
    if not items:
        return {"available": True, "count": 0, "oldest_modified": None, "newest_modified": None}
    modified = sorted(item["modified"] for item in items if item.get("modified"))
    return {
        "available": True,
        "count_sampled": len(items),
        "oldest_modified": modified[0] if modified else None,
        "newest_modified": modified[-1] if modified else None,
        "indicator_hits": [
            {
                **item,
                "executor_name_hits": executor_labels_for_artifact_text(str(item.get("name") or "")),
            }
            for item in items
            if executor_labels_for_artifact_text(str(item.get("name") or ""))
        ][:80],
    }


def executor_indicator_scan() -> dict:
    patterns = executor_name_patterns()
    file_hits: list[dict] = []
    traceback_hits: list[dict] = []
    scanned_files = 0

    roots_spec: list[tuple[Path, int | None]] = []

    if platform.system() == "Windows":
        seen_roots: set[str] = set()
        for drive_root, depth in full_pc_scan_roots():
            key = str(drive_root).lower()
            if key not in seen_roots:
                seen_roots.add(key)
                roots_spec.append((drive_root, depth))
        roots_spec.append((Path(os.getenv("SystemRoot", "C:\\Windows")) / "Prefetch", None))
    elif platform.system() == "Darwin":
        roots_spec.extend(
            [
                (Path.home() / "Library" / "Logs", 6),
                (Path.home() / "Library" / "Application Support", 6),
                (Path("/Applications"), 3),
            ]
        )
    else:
        roots_spec.append((Path.home(), 6))

    for root, max_depth in roots_spec:
        if not root.exists():
            continue
        try:
            if max_depth is None:
                if root.name.lower() == "prefetch":
                    path_iter = (p for p in root.glob("*.pf") if p.is_file())
                else:
                    path_iter = (p for p in root.rglob("*") if p.is_file() or p.is_dir())
            else:
                path_iter = walk_files_depth_limited(root, max_depth)

            for path in path_iter:
                try:
                    if len(file_hits) >= 800 and len(traceback_hits) >= 200:
                        break
                    name_text = str(path)
                    if executor_scan_path_excluded(name_text):
                        continue
                    matched = [name for name, pattern in patterns.items() if pattern.search(name_text)]
                    cheat_h = cheat_filename_hint_labels(path.name)
                    if matched or cheat_h:
                        stat = path.stat()
                        file_hits.append(
                            {
                                "matched_names": matched,
                                "cheat_filename_hints": cheat_h,
                                "path": str(path),
                                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                                "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                                "is_file": path.is_file(),
                                "size_bytes": stat.st_size if path.is_file() else None,
                                "path_allowlisted": path_is_allowlisted(str(path)),
                            }
                        )

                    if not path.is_file():
                        continue
                    scanned_files += 1
                    if path.suffix.lower() not in [".log", ".txt", ".traceback", ".json", ".xml"]:
                        continue
                    if path.stat().st_size > 2_000_000:
                        continue
                    text = path.read_text(errors="replace")
                    cheat_in_text = any(p.search(text) for _, p in CHEAT_FILENAME_HINT_PATTERNS)
                    if (
                        "traceback" not in text.lower()
                        and not any(pattern.search(text) for pattern in patterns.values())
                        and not cheat_in_text
                    ):
                        continue
                    lines = []
                    for line in text.splitlines():
                        if (
                            "traceback" in line.lower()
                            or any(pattern.search(line) for pattern in patterns.values())
                            or any(p.search(line) for _, p in CHEAT_FILENAME_HINT_PATTERNS)
                        ):
                            lines.append(line.strip()[:500])
                        if len(lines) >= 12:
                            break
                    if lines:
                        traceback_hits.append({"path": str(path), "matched_lines": lines})
                except Exception:
                    continue
        except Exception:
            continue

    return {
        "executor_names_checked": EXECUTOR_NAMES,
        "cheat_filename_patterns": [label for label, _ in CHEAT_FILENAME_HINT_PATTERNS],
        "roots_checked": [str(r[0]) for r in roots_spec],
        "scanned_text_files": scanned_files,
        "file_hits": file_hits[:800],
        "traceback_or_log_hits": traceback_hits[:200],
    }


_ROBLOX_URL_USER_ID = re.compile(
    r"roblox\.com/(?:users/|profile(?:\?[^#\"']*?userId=))(\d{6,})",
    re.IGNORECASE,
)
_ROBLOX_USERNAME_FROM_TITLE = re.compile(
    r"^([A-Za-z0-9_]{3,20})(?:\s*['\u2019]s)?\s+(?:Profile|on Roblox)\s*$",
    re.IGNORECASE,
)
_ROBLOX_PAGE_TITLE_NOISE = frozenset(
    {
        "roblox",
        "home",
        "catalog",
        "avatar",
        "bodies",
        "classics",
        "experiences",
        "friends",
        "people",
        "settings",
        "lemonade",
        "discover",
        "create",
        "develop",
        "marketplace",
        "charts",
        "groups",
        "notifications",
        "messages",
        "search",
        "login",
        "signup",
        "download",
        "blog",
        "events",
        "premium",
        "gift",
        "clearapocookie",
    }
)


def _roblox_is_plausible_username(name: str) -> bool:
    candidate = str(name or "").strip()
    if not candidate or len(candidate) < 3 or len(candidate) > 20:
        return False
    if not re.fullmatch(r"[A-Za-z0-9_]+", candidate):
        return False
    if candidate.isdigit():
        return False
    return candidate.lower() not in _ROBLOX_PAGE_TITLE_NOISE


def _roblox_username_from_title(title_text: str) -> str | None:
    title = str(title_text or "").strip()
    if not title:
        return None
    match = _ROBLOX_USERNAME_FROM_TITLE.match(title)
    if not match:
        return None
    username = match.group(1)
    return username if _roblox_is_plausible_username(username) else None


def _roblox_user_ids_from_text(text: str) -> list[str]:
    return sorted(set(_ROBLOX_URL_USER_ID.findall(str(text or ""))))


_ROBLOX_RBXID_FROM_TRACKER = re.compile(r"rbxid=(\d+)", re.IGNORECASE)
_ROBLOX_SESSION_COOKIE_NAMES = frozenset({".ROBLOSECURITY", "RBXEVENTTRACKERV2"})
_ROBLOX_USER_ID_TEXT = re.compile(r"\buserId[=: ]+(\d{6,})\b", re.IGNORECASE)


def _windows_dpapi_decrypt(encrypted_bytes: bytes) -> bytes | None:
    if platform.system() != "Windows" or not encrypted_bytes:
        return None
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", ctypes.wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    def _to_blob(data: bytes) -> DATA_BLOB:
        buffer = ctypes.create_string_buffer(data, len(data))
        blob = DATA_BLOB()
        blob.cbData = len(data)
        blob.pbData = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
        return blob

    in_blob = _to_blob(encrypted_bytes)
    out_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        return None
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _chromium_cookie_db_paths(profile_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for candidate in (profile_dir / "Network" / "Cookies", profile_dir / "Cookies"):
        if candidate.is_file():
            paths.append(candidate)
    return paths


def _chromium_master_keys(user_data_dir: Path) -> tuple[bytes | None, bytes | None]:
    local_state_path = user_data_dir / "Local State"
    if not local_state_path.is_file():
        return None, None
    v10_key: bytes | None = None
    v20_key: bytes | None = None
    try:
        payload = json.loads(local_state_path.read_text(encoding="utf-8"))
        os_crypt = payload.get("os_crypt") or {}
        encrypted_key = base64.b64decode(os_crypt.get("encrypted_key") or b"")
        if encrypted_key.startswith(b"DPAPI"):
            encrypted_key = encrypted_key[5:]
        v10_key = _windows_dpapi_decrypt(encrypted_key)
        app_bound_b64 = os_crypt.get("app_bound_encrypted_key")
        if app_bound_b64:
            app_bound = base64.b64decode(app_bound_b64)
            if app_bound.startswith(b"APPB"):
                decrypted = _windows_dpapi_decrypt(app_bound[4:])
                if decrypted:
                    second = _windows_dpapi_decrypt(decrypted)
                    key_material = second or decrypted
                    if len(key_material) >= 32:
                        v20_key = key_material[-32:]
    except (OSError, KeyError, ValueError, json.JSONDecodeError, TypeError):
        pass
    return v10_key, v20_key


def _chromium_decrypt_cookie_value(
    encrypted_value: bytes | memoryview | None,
    plain_value: bytes | str | None,
    master_key: bytes | None,
    v20_key: bytes | None = None,
) -> str | None:
    if plain_value not in (None, b"", ""):
        text = plain_value if isinstance(plain_value, str) else plain_value.decode("utf-8", errors="replace")
        cleaned = text.strip()
        return cleaned or None
    if not encrypted_value:
        return None
    try:
        from Cryptodome.Cipher import AES
    except ImportError:
        try:
            from Crypto.Cipher import AES
        except ImportError:
            AES = None
    blob = bytes(encrypted_value)
    if AES and master_key and blob.startswith((b"v10", b"v11")):
        nonce = blob[3:15]
        ciphertext = blob[15:-16]
        tag = blob[-16:]
        try:
            cipher = AES.new(master_key, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt_and_verify(ciphertext, tag)
            cleaned = decrypted.decode("utf-8", errors="replace").strip()
            return cleaned or None
        except (ValueError, KeyError):
            pass
    if AES and v20_key and blob.startswith(b"v20"):
        nonce = blob[3:15]
        ciphertext = blob[15:-16]
        tag = blob[-16:]
        try:
            cipher = AES.new(v20_key, AES.MODE_GCM, nonce=nonce)
            decrypted = cipher.decrypt_and_verify(ciphertext, tag)
            payload = decrypted[32:] if len(decrypted) > 32 else decrypted
            cleaned = payload.decode("utf-8", errors="replace").strip()
            return cleaned or None
        except (ValueError, KeyError):
            pass
    decrypted = _windows_dpapi_decrypt(blob)
    if not decrypted:
        return None
    cleaned = decrypted.decode("utf-8", errors="replace").strip()
    return cleaned or None


def _chromium_has_auth_cookie(cookie_db: Path) -> bool:
    conn = _sqlite_open_readonly(cookie_db)
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM cookies
            WHERE host_key LIKE '%roblox%'
              AND UPPER(name) = '.ROBLOSECURITY'
            LIMIT 1
            """
        )
        return bool(cur.fetchone())
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def _roblox_user_from_authenticated_cookie(roblosecurity: str) -> dict | None:
    token = str(roblosecurity or "").strip()
    if not token:
        return None
    try:
        response = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            cookies={".ROBLOSECURITY": token},
            timeout=4,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        user_id = data.get("id")
        if not user_id:
            return None
        username = str(data.get("name") or "").strip() or None
        return {"user_id": str(user_id), "username": username}
    except (requests.RequestException, TypeError, ValueError):
        return None


def _roblox_valid_user_id(user_id: str | None) -> bool:
    if not user_id or not str(user_id).isdigit():
        return False
    return int(user_id) > 0


def _roblox_rbxid_from_text_blob(text: str) -> str | None:
    matches = _ROBLOX_RBXID_FROM_TRACKER.findall(str(text or ""))
    for candidate in reversed(matches):
        if _roblox_valid_user_id(candidate):
            return str(candidate)
    user_ids = _ROBLOX_USER_ID_TEXT.findall(str(text or ""))
    for candidate in reversed(user_ids):
        if _roblox_valid_user_id(candidate):
            return str(candidate)
    return None


def _roblox_rbxid_from_profile_storage(profile_dir: Path) -> str | None:
    storage_dir = profile_dir / "Local Storage" / "leveldb"
    if not storage_dir.is_dir():
        return None
    candidates: list[Path] = []
    try:
        candidates.extend(sorted(storage_dir.glob("*.ldb"), key=lambda path: path.stat().st_mtime, reverse=True)[:12])
        candidates.extend(sorted(storage_dir.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)[:4])
    except OSError:
        return None
    for path in candidates:
        try:
            text = path.read_bytes().decode("latin-1", errors="ignore")
        except OSError:
            continue
        user_id = _roblox_rbxid_from_text_blob(text)
        if user_id:
            return user_id
    return None


def _roblox_rbxid_from_roblox_appdata() -> str | None:
    local_app = os.getenv("LOCALAPPDATA")
    if not local_app:
        return None
    roblox_root = Path(local_app) / "Roblox"
    if not roblox_root.is_dir():
        return None
    scan_paths: list[Path] = []
    for pattern in ("*.log", "*.txt", "*.json", "*.xml", "*.dat"):
        try:
            scan_paths.extend(sorted(roblox_root.rglob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)[:8])
        except OSError:
            continue
    for path in scan_paths[:24]:
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        user_id = _roblox_rbxid_from_text_blob(text)
        if user_id:
            return user_id
    return None


def _roblox_session_from_cookies(
    cookie_map: dict[str, str],
    *,
    auth_cookie_present: bool = False,
    fallback_user_id: str | None = None,
) -> dict | None:
    has_auth = auth_cookie_present or any(name.upper() == ".ROBLOSECURITY" for name in cookie_map)
    if not has_auth:
        return None
    roblosecurity = next(
        (value for name, value in cookie_map.items() if name.upper() == ".ROBLOSECURITY"),
        "",
    )
    user_id: str | None = None
    username: str | None = None
    if roblosecurity:
        auth_user = _roblox_user_from_authenticated_cookie(roblosecurity)
        if auth_user:
            user_id = auth_user.get("user_id")
            username = auth_user.get("username")
    if not user_id:
        tracker = next(
            (value for name, value in cookie_map.items() if name.upper() == "RBXEVENTTRACKERV2"),
            "",
        )
        match = _ROBLOX_RBXID_FROM_TRACKER.search(str(tracker or ""))
        if match:
            user_id = match.group(1)
    if not user_id and fallback_user_id:
        user_id = str(fallback_user_id)
    if not _roblox_valid_user_id(user_id):
        return None
    return {"user_id": str(user_id), "username": username}


def _roblox_read_chromium_session_cookies(profile_dir: Path) -> tuple[dict[str, str], bool]:
    cookies: dict[str, str] = {}
    auth_present = False
    v10_key, v20_key = _chromium_master_keys(profile_dir.parent)
    for cookie_db in _chromium_cookie_db_paths(profile_dir):
        auth_present = auth_present or _chromium_has_auth_cookie(cookie_db)
        conn = _sqlite_open_readonly(cookie_db)
        if not conn:
            continue
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT name, value, encrypted_value FROM cookies
                WHERE host_key LIKE '%roblox%'
                  AND UPPER(name) IN ('.ROBLOSECURITY', 'RBXEVENTTRACKERV2')
                """
            )
            for name, value, encrypted_value in cur.fetchall():
                cookie_name = str(name or "").strip()
                if not cookie_name:
                    continue
                decrypted = _chromium_decrypt_cookie_value(encrypted_value, value, v10_key, v20_key)
                if decrypted:
                    cookies[cookie_name] = decrypted
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    return cookies, auth_present


def _roblox_resolve_chromium_session(profile_dir: Path) -> dict | None:
    cookie_map, auth_present = _roblox_read_chromium_session_cookies(profile_dir)
    fallback_user_id = _roblox_rbxid_from_profile_storage(profile_dir)
    session = _roblox_session_from_cookies(
        cookie_map,
        auth_cookie_present=auth_present,
        fallback_user_id=fallback_user_id,
    )
    if session:
        return session
    if auth_present and fallback_user_id:
        return {"user_id": str(fallback_user_id), "username": None}
    return None


def _firefox_has_auth_cookie(profile_dir: Path) -> bool:
    conn = _sqlite_open_readonly(profile_dir / "cookies.sqlite")
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM moz_cookies
            WHERE host LIKE '%roblox%'
              AND UPPER(name) = '.ROBLOSECURITY'
            LIMIT 1
            """
        )
        return bool(cur.fetchone())
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def _roblox_read_firefox_session_cookies(profile_dir: Path) -> tuple[dict[str, str], bool]:
    cookies: dict[str, str] = {}
    auth_present = _firefox_has_auth_cookie(profile_dir)
    conn = _sqlite_open_readonly(profile_dir / "cookies.sqlite")
    if not conn:
        return cookies, auth_present
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT name, value FROM moz_cookies
            WHERE host LIKE '%roblox%'
              AND UPPER(name) IN ('.ROBLOSECURITY', 'RBXEVENTTRACKERV2')
            """
        )
        for name, value in cur.fetchall():
            cookie_name = str(name or "").strip()
            cookie_value = str(value or "").strip()
            if cookie_name and cookie_value:
                cookies[cookie_name] = cookie_value
    except sqlite3.Error:
        pass
    finally:
        conn.close()
    return cookies, auth_present


def _roblox_resolve_firefox_session(profile_dir: Path) -> dict | None:
    cookie_map, auth_present = _roblox_read_firefox_session_cookies(profile_dir)
    fallback_user_id = _roblox_rbxid_from_profile_storage(profile_dir)
    session = _roblox_session_from_cookies(
        cookie_map,
        auth_cookie_present=auth_present,
        fallback_user_id=fallback_user_id,
    )
    if session:
        return session
    if auth_present and fallback_user_id:
        return {"user_id": str(fallback_user_id), "username": None}
    return None


def _roblox_read_client_logs() -> list[dict]:
    global _roblox_logs_cache
    with _roblox_logs_cache_lock:
        if _roblox_logs_cache is not None:
            return _roblox_logs_cache
        candidates: list[Path] = []
        if platform.system() == "Windows":
            local_app_data = os.getenv("LOCALAPPDATA")
            if local_app_data:
                candidates.append(Path(local_app_data) / "Roblox" / "logs")
        elif platform.system() == "Darwin":
            candidates.append(Path.home() / "Library" / "Logs" / "Roblox")

        logs: list[dict] = []
        for folder in candidates:
            if not folder.exists():
                continue
            try:
                log_paths = sorted(folder.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)[:5]
            except OSError:
                continue
            for path in log_paths:
                try:
                    stat = path.stat()
                    text = path.read_text(errors="replace")
                    logs.append(
                        {
                            "name": path.name,
                            "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                            "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                            "signals": extract_roblox_signals(text),
                            "tail": text[-4000:],
                        }
                    )
                except Exception as exc:
                    logs.append({"name": path.name, "error": str(exc)})
        _roblox_logs_cache = logs
        return logs


def _roblox_client_session_user() -> dict | None:
    for log in _roblox_read_client_logs():
        signals = log.get("signals") or {}
        user_ids = signals.get("user_ids") or []
        if user_ids:
            return {
                "user_id": str(user_ids[-1]),
                "username": None,
                "sources": [f"Roblox client log:{log.get('name', 'unknown')}"],
                "authenticated": True,
            }
    user_id = _roblox_rbxid_from_roblox_appdata()
    if user_id:
        return {
            "user_id": user_id,
            "username": None,
            "sources": ["Roblox client storage"],
            "authenticated": True,
        }
    return None


def _roblox_merge_account_entry(target: dict, source: dict, source_bits: list[str] | None = None) -> None:
    if source_bits:
        target["sources"] = sorted(set(target.get("sources") or []) | set(source_bits))
    target["authenticated"] = bool(target.get("authenticated")) or bool(source.get("authenticated"))
    source_username = str(source.get("username") or "").strip()
    if source_username:
        target["username"] = source_username
    source_headshot = str(source.get("headshot_url") or "").strip()
    if source_headshot:
        target["headshot_url"] = source_headshot


def _roblox_chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _roblox_enrich_accounts(accounts: list[dict], *, include_headshots: bool = True) -> list[dict]:
    """Resolve Roblox usernames and avatar headshots for recovered user IDs."""
    by_id: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    for account in accounts:
        user_id = str(account.get("user_id") or "").strip()
        username = str(account.get("username") or "").strip()
        sources = list(account.get("sources") or [])
        if user_id:
            entry = by_id.setdefault(
                user_id,
                {
                    "user_id": user_id,
                    "username": None,
                    "headshot_url": None,
                    "sources": [],
                    "authenticated": bool(account.get("authenticated")),
                },
            )
            _roblox_merge_account_entry(entry, account, sources)
            continue
        if username and _roblox_is_plausible_username(username):
            key = username.lower()
            entry = by_name.setdefault(
                key,
                {
                    "user_id": None,
                    "username": username,
                    "headshot_url": None,
                    "sources": [],
                    "authenticated": False,
                },
            )
            _roblox_merge_account_entry(entry, account, sources)

    ids_needing_names = [uid for uid in sorted(by_id.keys()) if not by_id[uid].get("username")]
    for user_id_chunk in _roblox_chunked(ids_needing_names, 100):
        try:
            response = requests.post(
                "https://users.roblox.com/v1/users",
                json={"userIds": [int(uid) for uid in user_id_chunk], "excludeBannedUsers": False},
                timeout=4,
            )
            if response.ok:
                for row in response.json().get("data") or []:
                    uid = str(row.get("id") or "").strip()
                    name = str(row.get("name") or "").strip()
                    if uid and uid in by_id and name:
                        by_id[uid]["username"] = name
        except (requests.RequestException, TypeError, ValueError):
            pass

    unresolved_names = [entry["username"] for entry in by_name.values() if entry.get("username")]
    for username_chunk in _roblox_chunked(unresolved_names, 100):
        try:
            response = requests.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": username_chunk, "excludeBannedUsers": False},
                timeout=8,
            )
            if response.ok:
                for row in response.json().get("data") or []:
                    uid = str(row.get("id") or "").strip()
                    requested = str(row.get("requestedUsername") or row.get("name") or "").strip()
                    resolved_name = str(row.get("name") or requested).strip()
                    if not uid:
                        continue
                    entry = by_id.setdefault(
                        uid,
                        {
                            "user_id": uid,
                            "username": None,
                            "headshot_url": None,
                            "sources": [],
                            "authenticated": False,
                        },
                    )
                    if requested:
                        name_entry = by_name.get(requested.lower())
                        if name_entry:
                            _roblox_merge_account_entry(entry, name_entry, name_entry.get("sources"))
                    if resolved_name:
                        entry["username"] = resolved_name
        except (requests.RequestException, TypeError, ValueError):
            pass

    resolved_ids = sorted(by_id.keys(), key=lambda value: int(value) if value.isdigit() else value)
    if include_headshots:
        for user_id_chunk in _roblox_chunked(resolved_ids, 100):
            try:
                response = requests.get(
                    "https://thumbnails.roblox.com/v1/users/avatar-headshot",
                    params={
                        "userIds": ",".join(user_id_chunk),
                        "size": "150x150",
                        "format": "Png",
                        "isCircular": "false",
                    },
                    timeout=4,
                )
                if response.ok:
                    for row in response.json().get("data") or []:
                        uid = str(row.get("targetId") or "").strip()
                        image_url = str(row.get("imageUrl") or "").strip()
                        if uid in by_id and image_url and row.get("state") == "Completed":
                            by_id[uid]["headshot_url"] = image_url
            except (requests.RequestException, TypeError, ValueError):
                pass

    enriched = [by_id[uid] for uid in resolved_ids if by_id[uid].get("authenticated")]
    for entry in enriched:
        entry["authenticated"] = True
    return enriched[:40]


def _sqlite_open_readonly(db_path: Path) -> sqlite3.Connection | None:
    if not db_path.is_file():
        return None
    uri = f"file:{db_path.as_posix()}?mode=ro"
    for opener in (
        lambda: sqlite3.connect(uri, uri=True, timeout=1.0),
        lambda: sqlite3.connect(str(db_path), timeout=1.0),
    ):
        try:
            conn = opener()
            conn.execute("SELECT 1")
            return conn
        except sqlite3.Error:
            continue
    try:
        tmp_dir = tempfile.mkdtemp(prefix="vs-sqlite-")
        tmp_root = Path(tmp_dir)
        copied = tmp_root / db_path.name
        shutil.copy2(db_path, copied)
        for suffix in ("-wal", "-shm"):
            sidecar = db_path.parent / (db_path.name + suffix)
            if sidecar.is_file():
                shutil.copy2(sidecar, tmp_root / (db_path.name + suffix))
        for opener in (
            lambda: sqlite3.connect(f"file:{copied.as_posix()}?mode=ro", uri=True, timeout=1.0),
            lambda: sqlite3.connect(str(copied), timeout=1.0),
        ):
            try:
                conn = opener()
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                continue
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except OSError:
        pass
    return None


def _chromium_profile_names(base: Path) -> list[str]:
    names: list[str] = []
    if not base.is_dir():
        return names
    try:
        for entry in sorted(base.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name == "Default" or entry.name.startswith("Profile "):
                has_cookies = (entry / "Cookies").is_file() or (entry / "Network" / "Cookies").is_file()
                if (entry / "History").is_file() or has_cookies or (entry / "Web Data").is_file():
                    names.append(entry.name)
    except OSError:
        pass
    return names or ["Default"]


def _scan_chromium_roblox_profile(browser: str, profile: str, profile_dir: Path) -> dict:
    artifact: dict[str, object] = {
        "browser": browser,
        "profile": profile,
        "user_ids": [],
        "usernames": [],
        "authenticated": False,
        "history_hits": 0,
        "cookie_hits": 0,
        "sources": [],
    }
    user_ids: set[str] = set()
    usernames: set[str] = set()
    history_db = profile_dir / "History"
    conn = _sqlite_open_readonly(history_db)
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT url, title FROM urls
                WHERE url LIKE '%roblox.com%'
                ORDER BY last_visit_time DESC
                LIMIT 150
                """
            )
            rows = cur.fetchall()
            artifact["history_hits"] = len(rows)
            if rows:
                artifact["sources"] = list(artifact.get("sources") or []) + ["history"]
            for url, title in rows:
                user_ids.update(_roblox_user_ids_from_text(str(url or "")))
                title_username = _roblox_username_from_title(str(title or ""))
                if title_username:
                    usernames.add(title_username)
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    cookie_hits = 0
    auth_present = False
    for cookie_db in _chromium_cookie_db_paths(profile_dir):
        conn = _sqlite_open_readonly(cookie_db)
        if not conn:
            continue
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*) FROM cookies
                WHERE host_key LIKE '%roblox%'
                """
            )
            cookie_hits += int((cur.fetchone() or [0])[0] or 0)
            auth_present = auth_present or _chromium_has_auth_cookie(cookie_db)
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    if cookie_hits:
        artifact["cookie_hits"] = cookie_hits
        artifact["sources"] = list(artifact.get("sources") or []) + ["cookies"]
    session = _roblox_resolve_chromium_session(profile_dir)
    if session:
        artifact["authenticated"] = True
        artifact["session_user_id"] = session["user_id"]
        if session.get("username"):
            artifact["session_username"] = session["username"]
    elif auth_present:
        artifact["authenticated"] = True
    artifact["user_ids"] = sorted(user_ids)
    artifact["usernames"] = sorted(usernames)
    return artifact


def _scan_firefox_roblox_profile(profile_name: str, profile_dir: Path) -> dict:
    artifact: dict[str, object] = {
        "browser": "Firefox",
        "profile": profile_name,
        "user_ids": [],
        "usernames": [],
        "authenticated": False,
        "history_hits": 0,
        "cookie_hits": 0,
        "sources": [],
    }
    user_ids: set[str] = set()
    usernames: set[str] = set()
    places_db = profile_dir / "places.sqlite"
    conn = _sqlite_open_readonly(places_db)
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT url, title FROM moz_places
                WHERE url LIKE '%roblox.com%'
                ORDER BY last_visit_date DESC
                LIMIT 150
                """
            )
            rows = cur.fetchall()
            artifact["history_hits"] = len(rows)
            if rows:
                artifact["sources"] = list(artifact.get("sources") or []) + ["history"]
            for url, title in rows:
                user_ids.update(_roblox_user_ids_from_text(str(url or "")))
                title_username = _roblox_username_from_title(str(title or ""))
                if title_username:
                    usernames.add(title_username)
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    auth_present = _firefox_has_auth_cookie(profile_dir)
    conn = _sqlite_open_readonly(profile_dir / "cookies.sqlite")
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*) FROM moz_cookies
                WHERE host LIKE '%roblox%'
                """
            )
            cookie_hits = int((cur.fetchone() or [0])[0] or 0)
            if cookie_hits:
                artifact["cookie_hits"] = cookie_hits
                artifact["sources"] = list(artifact.get("sources") or []) + ["cookies"]
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    session = _roblox_resolve_firefox_session(profile_dir)
    if session:
        artifact["authenticated"] = True
        artifact["session_user_id"] = session["user_id"]
        if session.get("username"):
            artifact["session_username"] = session["username"]
    elif auth_present:
        artifact["authenticated"] = True
    artifact["user_ids"] = sorted(user_ids)
    artifact["usernames"] = sorted(usernames)
    return artifact


_ROBLOX_BROWSER_PROCESS_NAMES = frozenset(
    {
        "chrome.exe",
        "msedge.exe",
        "brave.exe",
        "opera.exe",
        "vivaldi.exe",
        "firefox.exe",
    }
)


def _close_browsers_for_roblox_scan() -> dict:
    """Close browsers so Roblox cookie databases are not locked during the scan."""
    if platform.system() != "Windows":
        return {"closed": [], "failed": []}
    targets = _ROBLOX_BROWSER_PROCESS_NAMES
    closed: list[str] = []
    failed: list[str] = []
    terminating: list[psutil.Process] = []
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            proc_name = str(proc.info.get("name") or "").lower()
            if proc_name not in targets:
                continue
            proc.terminate()
            terminating.append(proc)
            closed.append(f"{proc.info.get('name')} (pid {proc.info.get('pid')})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            failed.append(proc_name or "unknown")
    if terminating:
        _gone, alive = psutil.wait_procs(terminating, timeout=2)
        for proc in alive:
            try:
                proc.kill()
                proc.wait(timeout=1)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                try:
                    failed.append(f"{proc.name()} (pid {proc.pid})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    failed.append("unknown")
    if closed or terminating:
        time.sleep(0.35)
    return {"closed": closed, "failed": failed}


def roblox_browser_account_scan() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Browser Roblox scan is Windows-focused in this build"}
    browsers_closed = _close_browsers_for_roblox_scan()
    artifacts: list[dict] = []
    for browser, base in _chromium_user_data_roots():
        for profile in _chromium_profile_names(base):
            profile_dir = base / profile
            row = _scan_chromium_roblox_profile(browser, profile, profile_dir)
            if row.get("user_ids") or row.get("usernames") or row.get("authenticated"):
                artifacts.append(row)
    appdata = os.getenv("APPDATA")
    if appdata:
        profiles_root = Path(appdata) / "Mozilla" / "Firefox" / "Profiles"
        if profiles_root.is_dir():
            try:
                for entry in profiles_root.iterdir():
                    if entry.is_dir():
                        row = _scan_firefox_roblox_profile(entry.name, entry)
                        if row.get("user_ids") or row.get("usernames") or row.get("authenticated"):
                            artifacts.append(row)
            except OSError:
                pass
    raw_accounts: list[dict] = []
    for art in artifacts:
        session_user_id = str(art.get("session_user_id") or "").strip()
        if not session_user_id:
            continue
        browser = str(art.get("browser") or "Browser")
        profile = str(art.get("profile") or "unknown")
        raw_accounts.append(
            {
                "user_id": session_user_id,
                "username": art.get("session_username"),
                "headshot_url": None,
                "sources": [f"{browser}/{profile}:logged-in session"],
                "authenticated": True,
            }
        )
    accounts = _roblox_enrich_accounts(raw_accounts, include_headshots=False)
    return {
        "available": True,
        "browsers_closed": browsers_closed.get("closed") or [],
        "browsers_close_failed": browsers_closed.get("failed") or [],
        "artifact_count": len(artifacts),
        "artifacts": artifacts[:30],
        "accounts": accounts,
        "aggregate_user_ids": sorted({str(acct.get("user_id")) for acct in accounts if acct.get("user_id")}),
        "aggregate_usernames": sorted(
            {str(acct.get("username")) for acct in accounts if acct.get("username")}
        ),
        "note": "Recovers logged-in Roblox accounts from active browser sessions (not profile history).",
    }


def extract_roblox_signals(text: str) -> dict:
    user_ids = sorted(set(re.findall(r"\b(?:userId|UserId|userid|uid)[=: ]+(\d{3,})\b", text)))[:40]
    usernames = sorted(
        {
            name
            for name in re.findall(r"\b(?:username|Username|userName|UserName)[=: ]+([A-Za-z0-9_]{3,20})\b", text)
            if _roblox_is_plausible_username(name)
        }
    )[:40]
    place_ids = sorted(set(re.findall(r"\b(?:placeId|PlaceId|placeid)[=: ]+(\d{3,})\b", text)))[:40]
    load_client_settings = [
        line.strip()[:500]
        for line in text.splitlines()
        if "LoadClientSettings" in line
    ][:40]
    return {
        "user_ids": user_ids,
        "usernames": usernames,
        "place_ids": place_ids,
        "load_client_settings": load_client_settings,
    }


def roblox_diagnostics() -> dict:
    logs = _roblox_read_client_logs()
    browser_scan = roblox_browser_account_scan()
    merged_accounts: list[dict] = list(browser_scan.get("accounts") or [])
    if not merged_accounts:
        client_session = _roblox_client_session_user()
        if client_session:
            merged_accounts.append(client_session)
    accounts = _roblox_enrich_accounts(merged_accounts, include_headshots=False)

    log_locations_checked: list[str] = []
    if platform.system() == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            log_locations_checked.append(str(Path(local_app_data) / "Roblox" / "logs"))
    elif platform.system() == "Darwin":
        log_locations_checked.append(str(Path.home() / "Library" / "Logs" / "Roblox"))

    return {
        "detected": bool(logs) or bool(accounts),
        "log_locations_checked": log_locations_checked,
        "logs": logs,
        "browser_scan": browser_scan,
        "accounts": accounts,
        "aggregate_user_ids": sorted({str(acct.get("user_id")) for acct in accounts if acct.get("user_id")}),
        "aggregate_usernames": sorted(
            {
                str(acct.get("username"))
                for acct in accounts
                if acct.get("username") and _roblox_is_plausible_username(str(acct.get("username")))
            }
        ),
    }



_FORENSIC_ENGINE_VERSION = "2026-05-14.unified-v1"

_CHEAT_QUERY_TERMS = (
    "cheat",
    "aimbot",
    "wallhack",
    "esp hack",
    "injector",
    "dll inject",
    "bypass",
    "kernel driver",
    "undetected",
    "external cheat",
    "internal cheat",
    "lua executor",
    "roblox executor",
    "speedhack",
    "triggerbot",
)
_LOADER_TERMS = (
    "loader",
    "inject",
    "mapper",
    "kdmapper",
    "manual map",
    "reflective dll",
    "process hollowing",
    "gdrv",
    "capcom",
    " vulnerable driver",
)
_PREFETCH_TOOL_STEMS = (
    "CHEATENGINE",
    "PROCESSHACKER",
    "PROCEXP",
    "PROCEXP64",
    "PROCMON",
    "PROCMON64",
    "X64DBG",
    "X32DBG",
    "IDA64",
    "IDA",
    "WINDUMP",
    "MIMIKATZ",
    "EXTREMEINJECTOR",
    "XENOS",
    "GHIDRA",
)
_BROWSER_PARENT_MARKERS = (
    "CHROME",
    "MSEDGE",
    "FIREFOX",
    "BRAVE",
    "DISCORD",
    "TELEGRAM",
    "WHATSAPP",
    "SLACK",
)
_TEMP_MARKERS = (
    "\\TEMP\\",
    "\\TMP\\",
    "\\INetCache\\",
    "\\APPDATA\\LOCAL\\TEMP",
    "\\WINDOWS\\TEMP",
    "\\APPDATA\\LOCAL\\PACKAGES\\",
    "ZIPFOLDER",
    "\\APPDATA\\LOCAL\\TEMP\\",
)
_ARCHIVE_EXT = frozenset({".zip", ".rar", ".7z", ".tar", ".gz", ".cab"})


def forensic_finding(
    *,
    severity: str,
    confidence: float,
    reason: str,
    artifact_source: str,
    file_path: str = "",
    sha256: str = "",
    signature_status: str = "not_checked",
    entropy_score: float | None = None,
    yara_matches: list[str] | None = None,
    timestamps: dict[str, str] | None = None,
    correlated_evidence: list[dict[str, object]] | None = None,
    risk_score: int = 0,
) -> dict[str, object]:
    return {
        "severity": severity,
        "confidence": round(float(confidence), 3),
        "reason": reason,
        "artifact_source": artifact_source,
        "file_path": file_path,
        "sha256": sha256 or "",
        "signature_status": signature_status,
        "entropy_score": entropy_score,
        "yara_matches": list(yara_matches or []),
        "timestamps": dict(timestamps or {}),
        "correlated_evidence": list(correlated_evidence or []),
        "risk_score": int(max(0, min(100, risk_score))),
    }


def forensic_shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    ln = len(data)
    return -sum((c / ln) * math.log2(c / ln) for c in counts.values() if c)


def forensic_file_peek(path: Path, max_bytes: int = 1_572_864) -> tuple[str, float | None, int | None]:
    sha = ""
    ent: float | None = None
    size: int | None = None
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            chunk = fh.read(max_bytes)
            h.update(chunk)
            ent = forensic_shannon_entropy(chunk) if chunk else None
        sha = h.hexdigest()
        size = path.stat().st_size
    except OSError:
        pass
    return sha, ent, size


_AUTHENTICODE_STATUS_BY_HRESULT: dict[int, str] = {
    0x00000000: "Valid",
    0x800B0100: "NotSigned",  # TRUST_E_NOSIGNATURE
    0x80096010: "HashMismatch",  # TRUST_E_BAD_DIGEST
    0x800B0003: "NotSupportedFileFormat",  # TRUST_E_SUBJECT_FORM_UNKNOWN
    0x800B0004: "NotTrusted",  # TRUST_E_SUBJECT_NOT_TRUSTED
    0x800B0109: "NotTrusted",  # CERT_E_UNTRUSTEDROOT
    0x800B010A: "NotTrusted",  # CERT_E_CHAINING
    0x80096004: "NotTrusted",  # CERT_E_EXPIRED
    0x80096005: "NotTrusted",  # CERT_E_VALIDITYPERIODNESTING
    0x80096019: "NotTrusted",  # CERT_E_UNTRUSTEDTESTROOT
}


def _hresult_to_authenticode_status(code: int) -> str:
    return _AUTHENTICODE_STATUS_BY_HRESULT.get(code & 0xFFFFFFFF, "UnknownError")


def _win_authenticode_status(path: str) -> str:
    if not os.path.isfile(path):
        return "Missing"
    try:
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", wintypes.BYTE * 8),
            ]

        class WINTRUST_FILE_INFO(ctypes.Structure):
            _fields_ = [
                ("cbStruct", wintypes.DWORD),
                ("pcwszFilePath", wintypes.LPCWSTR),
                ("hFile", wintypes.HANDLE),
                ("pgKnownSubject", ctypes.c_void_p),
            ]

        class WINTRUST_DATA(ctypes.Structure):
            _fields_ = [
                ("cbStruct", wintypes.DWORD),
                ("pPolicyCallbackData", ctypes.c_void_p),
                ("pSIPClientData", ctypes.c_void_p),
                ("dwUIChoice", wintypes.DWORD),
                ("fdwRevocationChecks", wintypes.DWORD),
                ("dwUnionChoice", wintypes.DWORD),
                ("pFile", ctypes.POINTER(WINTRUST_FILE_INFO)),
                ("dwStateAction", wintypes.DWORD),
                ("hWVTStateData", wintypes.HANDLE),
                ("pwszURLReference", wintypes.LPCWSTR),
                ("dwProvFlags", wintypes.DWORD),
                ("dwUIContext", wintypes.DWORD),
                ("pSignatureSettings", ctypes.c_void_p),
            ]

        action = GUID(
            0x00AAC56B,
            0xCD44,
            0x11D0,
            (ctypes.c_ubyte * 8)(0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE),
        )
        file_info = WINTRUST_FILE_INFO(ctypes.sizeof(WINTRUST_FILE_INFO), path, None, None)
        trust_data = WINTRUST_DATA(
            ctypes.sizeof(WINTRUST_DATA),
            None,
            None,
            2,  # WTD_UI_NONE
            0,  # WTD_REVOKE_NONE
            1,  # WTD_CHOICE_FILE
            ctypes.pointer(file_info),
            1,  # WTD_STATEACTION_VERIFY
            None,
            None,
            0,
            0,
            None,
        )
        wintrust = ctypes.windll.wintrust
        result = wintrust.WinVerifyTrust(None, ctypes.byref(action), ctypes.byref(trust_data))
        trust_data.dwStateAction = 2  # WTD_STATEACTION_CLOSE
        wintrust.WinVerifyTrust(None, ctypes.byref(action), ctypes.byref(trust_data))
        return _hresult_to_authenticode_status(result)
    except OSError:
        return "Error"
    except Exception:
        return "Error"


def forensic_authenticode_status(path: str) -> str:
    if platform.system() != "Windows" or not path:
        return "skipped_non_windows"
    batch = forensic_authenticode_status_batch([path])
    return batch.get(path, batch.get(path.replace("/", "\\"), "unknown"))


def forensic_authenticode_status_batch(paths: list[str]) -> dict[str, str]:
    if platform.system() != "Windows" or not paths:
        return {}
    unique: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        path = str(raw or "").strip()
        if not path:
            continue
        key = path.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    if not unique:
        return {}
    workers = min(8, max(1, len(unique)))
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for path, status in pool.map(lambda p: (p, _win_authenticode_status(p)), unique):
            results[path] = status[:120]
    return results


def _is_exec_dll_path(path: str) -> bool:
    return bool(path) and bool(re.search(r"\.(exe|dll)\Z", path, re.IGNORECASE))


def _collect_forensic_exec_paths(
    designated: dict[str, object],
    bam_items: list[dict[str, object]],
    pca_items: list[dict[str, object]] | None = None,
) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(raw: str, require_drive: bool = False) -> None:
        path = str(raw or "").strip()
        if not _is_exec_dll_path(path):
            return
        if require_drive and not re.match(r"^[A-Za-z]:\\", path):
            return
        key = path.lower()
        if key in seen:
            return
        seen.add(key)
        paths.append(path)

    for hit in designated.get("hits") or []:
        add(str(hit.get("path") or ""))
    for item in bam_items[:220]:
        add(str(item.get("normalized_path") or ""), require_drive=True)
    for item in (pca_items or [])[:200]:
        add(str(item.get("normalized_path") or ""), require_drive=True)
    return paths


def build_executable_forensic_cache(paths: list[str]) -> dict[str, dict[str, object]]:
    if not paths:
        return {}
    signature_map = forensic_authenticode_status_batch(paths)
    cache: dict[str, dict[str, object]] = {}

    def analyze_path(path: str) -> tuple[str, dict[str, object]]:
        sha256, entropy, _size = forensic_file_peek(Path(path))
        ymatches = forensic_yara_hook_scan(Path(path))
        signature = signature_map.get(path) or signature_map.get(path.replace("/", "\\")) or "unknown"
        return path.lower(), {
            "sha256": sha256,
            "ent": entropy,
            "sig": signature,
            "ymatches": ymatches,
        }

    workers = min(SCAN_WORKERS, max(2, len(paths)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for cache_key, payload in pool.map(analyze_path, paths):
            cache[cache_key] = payload
    return cache


def exec_forensic_lookup(cache: dict[str, dict[str, object]], path: str) -> dict[str, object]:
    default: dict[str, object] = {"sha256": "", "ent": None, "sig": "not_checked", "ymatches": []}
    if not path:
        return default
    return cache.get(path.lower(), default)


def forensic_yara_hook_scan(path: Path) -> list[str]:
    try:
        import yara  # type: ignore

        rules = getattr(forensic_yara_hook_scan, "_rules", None)
        if rules is None:
            setattr(forensic_yara_hook_scan, "_rules", False)
            rule_dir = Path(os.getenv("LOCALAPPDATA", "")) / "VirelloScanner" / "yara_rules"
            compiled = None
            if rule_dir.is_dir():
                paths = sorted(rule_dir.glob("*.yar")) + sorted(rule_dir.glob("*.yara"))
                if paths:
                    compiled = yara.compile(filepaths={f"r{i}": str(p) for i, p in enumerate(paths[:24])})
            setattr(forensic_yara_hook_scan, "_rules", compiled)
        rules = getattr(forensic_yara_hook_scan, "_rules", None)
        if not rules:
            return []
        matches = rules.match(str(path), timeout=6)
        return [f"{m.namespace}:{m.rule}" for m in matches][:40]
    except Exception:
        return []


def forensic_risk_score(
    *,
    unsigned: bool = False,
    high_entropy: bool = False,
    temp_path: bool = False,
    deleted_hint: bool = False,
    packed_hint: bool = False,
    rename_hint: bool = False,
) -> int:
    score = 0
    if unsigned:
        score += 28
    if high_entropy:
        score += 18
    if temp_path:
        score += 22
    if deleted_hint:
        score += 16
    if packed_hint:
        score += 12
    if rename_hint:
        score += 10
    return min(100, score)


def forensic_normalize_pathish(raw: str) -> str:
    s = (raw or "").strip().strip('"')
    if s.startswith("\\\\?\\"):
        s = s[4:]
    if s.startswith("\\??\\"):
        s = s[4:]
    m = re.search(r"([A-Za-z]:\\[^|*\"<>?\n\r]+)", s)
    if m:
        return m.group(1)
    if s.upper().startswith("\\DEVICE\\"):
        return device_path_to_dos_path(s)
    return s


def forensic_is_temp_path(p: str) -> bool:
    u = p.upper().replace("/", "\\")
    return any(m in u for m in _TEMP_MARKERS)


def forensic_is_downloads_path(p: str) -> bool:
    u = p.upper().replace("/", "\\")
    return "\\DOWNLOADS\\" in u or u.rstrip("\\").endswith("\\DOWNLOADS")


def forensic_is_removable_path(p: str) -> str | None:
    u = p.upper()
    m = re.match(r"^([A-Z]):\\", u)
    if not m:
        return None
    letter = m.group(1)
    script = (
        f"$d='{letter}:'; try {{ (Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='$d'\").DriveType }} catch {{}}"
    )
    out = run_command(["powershell", "-NoProfile", "-Command", script], timeout=6, max_chars=200).strip()
    if out == "2":
        return "removable_drive_type_2"
    return None


def forensic_powershell_json(script: str, timeout: float = 22.0, max_chars: int = 28000) -> object:
    raw = run_command(["powershell", "-NoProfile", "-Command", script], timeout=timeout, max_chars=max_chars)
    if not raw or raw.startswith("Unavailable:"):
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def bam_execution_records() -> dict[str, object]:
    if platform.system() != "Windows":
        return {"available": False, "items": [], "reason": "Windows-only"}
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$base='HKLM:\SYSTEM\CurrentControlSet\Services\bam\State\UserSettings'
if(-not(Test-Path $base)){ Write-Output '[]' } else {
$rows=New-Object System.Collections.Generic.List[object]
foreach($sid in Get-ChildItem $base){
  $p=Get-ItemProperty $sid.PSPath
  foreach($prop in $p.PSObject.Properties){
    $n=$prop.Name
    if($n -match '^PS'){ continue }
    if($n -in @('SDL','Status')){ continue }
    $ft=$null
    if($prop.Value -is [byte[]] -and $prop.Value.Length -ge 8){
      $ft=[BitConverter]::ToUInt64($prop.Value,0)
    }
    $rows.Add([pscustomobject]@{ Sid=$sid.PSChildName; RegValueName=$n; FileTimeUtc=$ft })
  }
}
$rows | Select-Object -First 2500 | ConvertTo-Json -Compress -Depth 3
}
""".strip()
    data = forensic_powershell_json(script, timeout=36.0, max_chars=180000)
    items: list[dict[str, object]] = []
    if isinstance(data, list):
        items = [dict(x) for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        items = [dict(data)]
    normalized: list[dict[str, object]] = []
    for it in items:
        raw_path = str(it.get("RegValueName") or "")
        norm = forensic_normalize_pathish(raw_path)
        check_path = norm
        if check_path and not re.match(r"^[A-Za-z]:\\", check_path):
            check_path = device_path_to_dos_path(raw_path) or device_path_to_dos_path(check_path or "")
        if check_path and re.match(r"^[A-Za-z]:\\", check_path):
            norm = check_path
        ft = it.get("FileTimeUtc")
        try:
            ft_int = int(ft) if ft is not None else 0
        except (TypeError, ValueError):
            ft_int = 0
        iso = windows_filetime_to_iso(ft_int) if ft_int else None
        exists = False
        if norm and re.match(r"^[A-Za-z]:\\", norm):
            try:
                exists = Path(norm).exists()
            except OSError:
                exists = False
        profile = suspicious_path_profile(norm) if norm else {
            "executor_name_hits": [],
            "cheat_filename_hints": [],
            "name_anomaly_reasons": [],
        }
        if norm and not profile["executor_name_hits"] and not bam_path_is_benign_system(norm):
            profile["executor_name_hits"] = loose_executor_labels_for_artifact(norm)
        normalized.append(
            {
                "registry_path_value": raw_path,
                "normalized_path": norm,
                "last_execution_utc": iso,
                "file_exists": exists,
                "path_allowlisted": bam_path_is_benign_system(norm) if norm else True,
                "sid": it.get("Sid"),
                "executor_name_hits": profile["executor_name_hits"],
                "cheat_filename_hints": profile["cheat_filename_hints"],
                "name_anomaly_reasons": profile["name_anomaly_reasons"],
            }
        )
    return {"available": True, "items": normalized, "source": "BAM UserSettings"}


def dam_execution_records() -> dict[str, object]:
    """Desktop Activity Moderator — same shape as BAM; present on newer Windows builds."""
    if platform.system() != "Windows":
        return {"available": False, "items": [], "reason": "Windows-only"}
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$base='HKLM:\SYSTEM\CurrentControlSet\Services\dam\State\UserSettings'
if(-not(Test-Path $base)){ Write-Output '[]' } else {
$rows=New-Object System.Collections.Generic.List[object]
foreach($sid in Get-ChildItem $base){
  $p=Get-ItemProperty $sid.PSPath
  foreach($prop in $p.PSObject.Properties){
    $n=$prop.Name
    if($n -match '^PS'){ continue }
    if($n -in @('SDL','Status')){ continue }
    $ft=$null
    if($prop.Value -is [byte[]] -and $prop.Value.Length -ge 8){
      $ft=[BitConverter]::ToUInt64($prop.Value,0)
    }
    $rows.Add([pscustomobject]@{ Sid=$sid.PSChildName; RegValueName=$n; FileTimeUtc=$ft })
  }
}
$rows | Select-Object -First 2500 | ConvertTo-Json -Compress -Depth 3
}
""".strip()
    data = forensic_powershell_json(script, timeout=36.0, max_chars=180000)
    items: list[dict[str, object]] = []
    if isinstance(data, list):
        items = [dict(x) for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        items = [dict(data)]
    normalized: list[dict[str, object]] = []
    for it in items:
        raw_path = str(it.get("RegValueName") or "")
        norm = forensic_normalize_pathish(raw_path)
        check_path = norm
        if check_path and not re.match(r"^[A-Za-z]:\\", check_path):
            check_path = device_path_to_dos_path(raw_path) or device_path_to_dos_path(check_path or "")
        if check_path and re.match(r"^[A-Za-z]:\\", check_path):
            norm = check_path
        ft = it.get("FileTimeUtc")
        try:
            ft_int = int(ft) if ft is not None else 0
        except (TypeError, ValueError):
            ft_int = 0
        iso = windows_filetime_to_iso(ft_int) if ft_int else None
        exists = False
        if norm and re.match(r"^[A-Za-z]:\\", norm):
            try:
                exists = Path(norm).exists()
            except OSError:
                exists = False
        profile = suspicious_path_profile(norm) if norm else {
            "executor_name_hits": [],
            "cheat_filename_hints": [],
            "name_anomaly_reasons": [],
        }
        if norm and not profile["executor_name_hits"] and not bam_path_is_benign_system(norm):
            profile["executor_name_hits"] = loose_executor_labels_for_artifact(norm)
        normalized.append(
            {
                "registry_path_value": raw_path,
                "normalized_path": norm,
                "last_execution_utc": iso,
                "file_exists": exists,
                "path_allowlisted": bam_path_is_benign_system(norm) if norm else True,
                "sid": it.get("Sid"),
                "executor_name_hits": profile["executor_name_hits"],
                "cheat_filename_hints": profile["cheat_filename_hints"],
                "name_anomaly_reasons": profile["name_anomaly_reasons"],
            }
        )
    return {"available": bool(normalized), "items": normalized, "source": "DAM UserSettings"}


def pca_executed_records() -> dict[str, object]:
    if platform.system() != "Windows":
        return {"available": False, "items": [], "reason": "Windows-only"}
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$store='HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store'
$out=New-Object System.Collections.Generic.List[object]
$storeModified=$null
if(Test-Path $store){
  $storeItem=Get-Item $store
  $storeModified=$storeItem.LastWriteTimeUtc.ToString('o')
  foreach($v in $storeItem.Property){
    if($v -match '^PS'){ continue }
    $out.Add([pscustomobject]@{ StoreValueName=$v })
  }
}
[pscustomobject]@{
  StoreKeyModifiedUtc=$storeModified
  Items=@($out | Select-Object -First 220)
} | ConvertTo-Json -Compress -Depth 4
""".strip()
    data = forensic_powershell_json(script, timeout=18.0, max_chars=24000)
    items: list[dict[str, object]] = []
    store_key_modified: str | None = None
    if isinstance(data, dict):
        store_key_modified = normalize_event_time(data.get("StoreKeyModifiedUtc"))
        raw_items = data.get("Items")
        if isinstance(raw_items, list):
            items = [dict(x) for x in raw_items if isinstance(x, dict)]
        elif isinstance(raw_items, dict):
            items = [dict(raw_items)]
    elif isinstance(data, list):
        items = [dict(x) for x in data if isinstance(x, dict)]
    parsed = []
    for it in items:
        name = str(it.get("StoreValueName") or "")
        norm = forensic_normalize_pathish(name)
        exists = False
        file_modified: str | None = None
        if norm and re.match(r"^[A-Za-z]:\\", norm):
            try:
                target = Path(norm)
                exists = target.exists()
                if target.is_file():
                    file_modified = datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                exists = False
        display_at, timestamp_source = resolve_display_timestamp(
            primary=file_modified,
        )
        parsed.append(
            {
                "raw": name,
                "normalized_path": norm,
                "file_exists": exists,
                "file_modified_utc": file_modified,
                "display_at": display_at,
                "timestamp_source": timestamp_source,
            }
        )
    return {
        "available": True,
        "items": parsed,
        "source": "PCA Store (HKCU)",
        "store_key_modified_utc": store_key_modified,
        "note": "Missing files are cross-enriched with BAM, Prefetch, USN, and Recycle Bin timestamps when available.",
    }


def _artifact_path_key(path: str) -> str:
    return forensic_normalize_pathish(path).lower()


def _build_timestamp_index(
    items: list[dict],
    *,
    path_field: str,
    time_field: str,
) -> tuple[dict[str, str], dict[str, str]]:
    by_path: dict[str, str] = {}
    by_basename: dict[str, str] = {}
    for item in items:
        ts = normalize_event_time(item.get(time_field))
        if not ts:
            continue
        path = _artifact_path_key(str(item.get(path_field) or ""))
        if path:
            existing = by_path.get(path)
            if not existing or ts > existing:
                by_path[path] = ts
        base = basename_key(str(item.get(path_field) or ""))
        if base:
            existing = by_basename.get(base)
            if not existing or ts > existing:
                by_basename[base] = ts
    return by_path, by_basename


def _paths_relate(left: str, right: str) -> bool:
    a = _artifact_path_key(left)
    b = _artifact_path_key(right)
    if not a or not b:
        return False
    if a == b or a.endswith(b) or b.endswith(a):
        return True
    shared = basename_key(a)
    return bool(shared) and shared == basename_key(b)


def _lookup_indexed_timestamp(
    path: str,
    by_path: dict[str, str],
    by_basename: dict[str, str],
) -> str | None:
    key = _artifact_path_key(path)
    if key and key in by_path:
        return by_path[key]
    for stored_path, ts in by_path.items():
        if _paths_relate(key, stored_path):
            return ts
    base = basename_key(path)
    if base and base in by_basename:
        return by_basename[base]
    return None


def _build_usn_timestamp_index(usn_records: list[dict]) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    by_path: dict[str, str] = {}
    by_delete: dict[str, str] = {}
    by_basename: dict[str, str] = {}
    for row in usn_records:
        ts = normalize_event_time(row.get("display_at") or row.get("timestamp_utc"))
        if not ts:
            continue
        reasons = row.get("reasons") or []
        is_delete = any("DELETE" in str(r) for r in reasons)
        target = by_delete if is_delete else by_path
        path = _artifact_path_key(str(row.get("path") or ""))
        basenames: set[str] = set()
        if path:
            existing = target.get(path)
            if not existing or ts > existing:
                target[path] = ts
            base = basename_key(path)
            if base:
                basenames.add(base)
        raw = str(row.get("raw") or "")
        for match in re.finditer(r"([^\s\\/,;\"|]+\.(?:exe|dll|bat|ps1))", raw, re.IGNORECASE):
            basenames.add(match.group(1).lower())
        for base in basenames:
            existing_base = by_basename.get(base)
            if not existing_base or ts > existing_base:
                by_basename[base] = ts
    return by_path, by_delete, by_basename


def _build_simple_path_timestamp_index(
    items: list[dict],
    *,
    path_field: str,
    time_field: str,
) -> dict[str, str]:
    by_path: dict[str, str] = {}
    for item in items:
        path = _artifact_path_key(str(item.get(path_field) or ""))
        ts = normalize_event_time(item.get(time_field))
        if not path or not ts:
            continue
        existing = by_path.get(path)
        if not existing or ts > existing:
            by_path[path] = ts
    return by_path


def _build_prefetch_timestamp_index(prefetch: dict) -> dict[str, str]:
    by_stem: dict[str, str] = {}
    for item in prefetch.get("items") or []:
        ts = normalize_event_time(item.get("modified"))
        if not ts:
            continue
        stem = prefetch_extract_stem(str(item.get("name") or ""))
        if not stem:
            continue
        existing = by_stem.get(stem)
        if not existing or ts > existing:
            by_stem[stem] = ts
    return by_stem


def _build_recycle_timestamp_index(trash: dict) -> dict[str, str]:
    by_path: dict[str, str] = {}
    for item in trash.get("items") or []:
        original = _artifact_path_key(str(item.get("original_path") or ""))
        if not original:
            continue
        ts = normalize_event_time(
            item.get("display_at") or item.get("deleted_at") or item.get("metadata_modified")
        )
        if not ts:
            continue
        existing = by_path.get(original)
        if not existing or ts > existing:
            by_path[original] = ts
    return by_path


def path_exists_on_disk(path: str) -> bool:
    if not path or not re.match(r"^[A-Za-z]:\\", forensic_normalize_pathish(path)):
        return False
    try:
        return Path(forensic_normalize_pathish(path)).exists()
    except OSError:
        return False


def _collect_usn_records_for_removed_artifact_merge(
    forensic_bundle: dict,
    deletion: dict,
) -> list[dict[str, object]]:
    """Merge USN rows from forensic bundle and deletion evidence for removed-path recovery."""
    records: list[dict[str, object]] = [
        row for row in (forensic_bundle.get("usn_file_lifecycle_rows") or []) if isinstance(row, dict)
    ]
    extra_lines: list[str] = []
    usn_text = str(deletion.get("usn_delete_sample") or "")
    if usn_text:
        extra_lines.extend(usn_text.splitlines()[:USN_DELETE_MAX_LINES])
    evidence = deletion.get("deleted_file_evidence")
    if isinstance(evidence, dict):
        for line in evidence.get("usn_file_delete_lines") or []:
            extra_lines.append(str(line))
    usn_pack = usn_journal_comprehensive_read()
    for line in list(usn_pack.get("lines") or []) + list(usn_pack.get("delete_lines") or []):
        extra_lines.append(str(line))
    if extra_lines:
        records.extend(usn_parse_records(extra_lines))
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, object]] = []
    for row in records:
        key = (_artifact_path_key(str(row.get("path") or "")), ",".join(row.get("reasons") or []))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:2000]


def merge_removed_executor_artifact_hits(
    designated: dict,
    *,
    scan_started_at: str | None = None,
    generated_at: str | None = None,
    bam: dict,
    prefetch: dict,
    prefetch_health: dict,
    trash: dict,
    usn_records: list[dict],
    command_history: dict,
    persistence: dict,
    forensic_bundle: dict,
    recent_items: dict | None = None,
    userassist: dict | None = None,
    browser_download_history: dict | None = None,
    deletion: dict | None = None,
) -> None:
    """Surface executor/cheat paths removed from disk and Recycle Bin via BAM, USN, PCA, Prefetch, etc."""
    patterns = executor_name_patterns()
    if deletion:
        usn_records = _collect_usn_records_for_removed_artifact_merge(forensic_bundle, deletion)
    existing_keys = {_artifact_path_key(str(hit.get("path") or "")) for hit in designated.get("hits") or []}
    seen_removed: set[str] = set()
    new_hits: list[dict] = []

    def consider(path: str, *, occurred_at: str | None, source: str) -> None:
        normalized = forensic_normalize_pathish(path)
        if not normalized:
            return
        if executor_scan_path_excluded(normalized):
            return
        profile = suspicious_path_profile(normalized, patterns)
        if not (
            profile["executor_name_hits"]
            or profile["cheat_filename_hints"]
            or profile["name_anomaly_reasons"]
        ):
            return
        if path_exists_on_disk(normalized):
            return
        key = _artifact_path_key(normalized)
        if key in existing_keys or key in seen_removed:
            return
        seen_removed.add(key)
        display_at, timestamp_source, correlated = resolve_path_activity_timestamp(
            normalized,
            bam=bam,
            prefetch=prefetch,
            usn_records=usn_records,
            trash=trash,
            designated=designated,
            command_history=command_history,
            recent_items=recent_items,
            userassist=userassist,
        )
        resolved_source = timestamp_source or source
        display_at = sanitize_activity_timestamp(display_at, resolved_source, scan_started_at, generated_at)
        occurred_at = sanitize_activity_timestamp(occurred_at, source, scan_started_at, generated_at)
        new_hits.append(
            {
                "path": normalized,
                "executor_name_hits": profile["executor_name_hits"],
                "cheat_filename_hints": profile["cheat_filename_hints"],
                "name_anomaly_reasons": profile["name_anomaly_reasons"],
                "modified": occurred_at or display_at,
                "display_at": display_at,
                "timestamp_source": timestamp_source or source,
                "correlated_timestamps": correlated,
                "file_exists": False,
                "removed_artifact": True,
                "artifact_source": source,
                "path_allowlisted": path_is_allowlisted(normalized),
                "note": "No longer on disk or in Recycle Bin; recovered from Windows activity artifacts.",
            }
        )

    for item in bam.get("items") or []:
        consider(
            str(item.get("normalized_path") or ""),
            occurred_at=item.get("last_execution_utc"),
            source="bam_execution",
        )

    pca = forensic_bundle.get("pca_executed") or {}
    for item in pca.get("items") or []:
        consider(
            str(item.get("normalized_path") or ""),
            occurred_at=item.get("display_at"),
            source="pca_compat",
        )

    for row in usn_records:
        reasons = [str(reason).upper() for reason in (row.get("reasons") or [])]
        if not any("DELETE" in reason or "RENAME_OLD" in reason for reason in reasons):
            continue
        consider(
            str(row.get("path") or ""),
            occurred_at=row.get("display_at") or row.get("timestamp_utc"),
            source="usn_delete" if any("DELETE" in reason for reason in reasons) else "usn_rename",
        )

    pf_folder = str(prefetch.get("folder") or "")
    for item in prefetch.get("items") or []:
        name = str(item.get("name") or "")
        stem = prefetch_extract_stem(name)
        if not path_is_suspicious_profile(stem, patterns) and not path_is_suspicious_profile(name, patterns):
            continue
        path = f"{pf_folder}\\{name}" if pf_folder and name else name
        consider(path, occurred_at=item.get("modified"), source="prefetch")

    for item in prefetch_health.get("indicator_hits") or []:
        name = str(item.get("name") or "")
        path = f"{pf_folder}\\{name}" if pf_folder and name else name
        consider(path, occurred_at=item.get("modified"), source="prefetch")

    for hit in command_history.get("hits") or []:
        line = str(hit.get("line") or "")
        for match in re.finditer(r'([A-Za-z]:\\(?:[^"\n\r]+))', line, re.IGNORECASE):
            consider(match.group(1), occurred_at=hit.get("occurred_at"), source="powershell_history")

    for item in persistence.get("suspicious") or []:
        consider(str(item.get("target") or ""), occurred_at=None, source="persistence")

    for item in trash.get("items") or []:
        consider(
            str(item.get("original_path") or ""),
            occurred_at=item.get("deleted_at") or item.get("display_at"),
            source="recycle_bin",
        )

    for item in (recent_items or {}).get("items") or []:
        folder = str(item.get("folder") or "")
        name = str(item.get("name") or "")
        combined = f"{folder}\\{name}" if folder and name else name or folder
        consider(
            combined,
            occurred_at=item.get("modified") or item.get("accessed"),
            source="recent_items",
        )

    for item in (userassist or {}).get("items") or []:
        consider(
            str(item.get("path") or ""),
            occurred_at=item.get("display_at") or item.get("last_run_utc"),
            source="userassist",
        )

    for item in (browser_download_history or {}).get("items") or []:
        if not item.get("suspicious"):
            continue
        consider(
            str(item.get("target_path") or ""),
            occurred_at=item.get("started_at") or item.get("ended_at"),
            source="browser_download",
        )

    if not new_hits:
        return
    designated.setdefault("hits", []).extend(new_hits)
    designated["removed_artifact_hits"] = len(new_hits)


def _append_executor_artifact_hit(
    hits: list[dict[str, object]],
    seen: set[str],
    *,
    path: str,
    labels: list[str],
    occurred_at: str | None,
    artifact_source: str,
    timestamp_source: str | None = None,
    file_exists: bool | None = None,
    note: str | None = None,
    extra: dict | None = None,
) -> None:
    norm = forensic_normalize_pathish(path) if path else ""
    if not norm or not labels:
        return
    if executor_scan_path_excluded(norm) or artifact_path_is_review_noise(norm):
        return
    dedupe_key = f"{artifact_source}|{_artifact_path_key(norm)}|{','.join(sorted(labels))}"
    if dedupe_key in seen:
        return
    seen.add(dedupe_key)
    profile = suspicious_path_profile(norm)
    payload: dict[str, object] = {
        "path": norm,
        "executor_name_hits": sorted(set(labels + profile["executor_name_hits"])),
        "cheat_filename_hints": profile["cheat_filename_hints"],
        "name_anomaly_reasons": profile["name_anomaly_reasons"],
        "display_at": occurred_at,
        "modified": occurred_at,
        "timestamp_source": timestamp_source or artifact_source,
        "artifact_source": artifact_source,
        "file_exists": file_exists,
        "removed_artifact": file_exists is False,
        "path_allowlisted": bam_path_is_benign_system(norm),
        "note": note or f"Executor evidence from {artifact_source}.",
    }
    if extra:
        payload.update(extra)
    hits.append(payload)


def scan_recent_lnk_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    folders: list[Path] = []
    appdata = os.getenv("APPDATA")
    if appdata:
        folders.append(Path(appdata) / "Microsoft" / "Windows" / "Recent")
    userprofile = os.getenv("USERPROFILE")
    if userprofile:
        auto = Path(appdata or userprofile) / "Microsoft" / "Windows" / "Recent" / "AutomaticDestinations"
        if auto.is_dir():
            folders.append(auto)
        custom = Path(appdata or userprofile) / "Microsoft" / "Windows" / "Recent" / "CustomDestinations"
        if custom.is_dir():
            folders.append(custom)
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for folder in folders:
        if not folder.is_dir():
            continue
        try:
            candidates = list(folder.glob("*.lnk"))[:80]
            if folder.name in {"AutomaticDestinations", "CustomDestinations"}:
                candidates = list(folder.iterdir())[:40]
        except OSError:
            continue
        for path in candidates:
            try:
                data = path.read_bytes()[:2_500_000]
                stat = path.stat()
                modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            except OSError:
                continue
            labels = scan_binary_blob_for_executor_names(data)
            if not labels:
                continue
            for match in re.finditer(rb"(?:[\x20-\x7e\\:]){8,260}", data):
                try:
                    fragment = match.group(0).decode("ascii", errors="ignore")
                except Exception:
                    continue
                if not re.match(r"^[A-Za-z]:\\", fragment):
                    continue
                frag_labels = executor_labels_for_artifact_text(fragment)
                if frag_labels:
                    _append_executor_artifact_hit(
                        hits,
                        seen,
                        path=fragment[:520],
                        labels=frag_labels,
                        occurred_at=modified,
                        artifact_source="recent_lnk",
                        file_exists=path_exists_on_disk(fragment),
                        note="Executor path recovered from a Recent/Jump List shortcut or destination file.",
                    )
            if labels and not hits:
                _append_executor_artifact_hit(
                    hits,
                    seen,
                    path=str(path),
                    labels=labels,
                    occurred_at=modified,
                    artifact_source="recent_lnk",
                    file_exists=path.is_file(),
                    note="Executor name found inside a Recent/Jump List artifact.",
                )
    return hits[:120]


def scan_registry_uninstall_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$roots=@(
 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$rows=New-Object System.Collections.Generic.List[object]
foreach($root in $roots){
  Get-ItemProperty $root -ErrorAction SilentlyContinue | ForEach-Object {
    $name=$_.DisplayName
    $loc=$_.InstallLocation
    $icon=$_.DisplayIcon
    $pub=$_.Publisher
    if($name -or $loc -or $icon){ $rows.Add([pscustomobject]@{DisplayName=$name;InstallLocation=$loc;DisplayIcon=$icon;Publisher=$pub}) }
  }
}
$rows | Select-Object -First 220 | ConvertTo-Json -Compress -Depth 3
""".strip()
    data = forensic_powershell_json(script, timeout=22.0, max_chars=28000)
    rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        blob = " ".join(
            str(row.get(key) or "")
            for key in ("DisplayName", "InstallLocation", "DisplayIcon", "Publisher")
        )
        labels = executor_labels_for_artifact_text(blob)
        if not labels:
            continue
        path = str(row.get("InstallLocation") or row.get("DisplayIcon") or row.get("DisplayName") or "")
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=None,
            artifact_source="registry_uninstall",
            file_exists=path_exists_on_disk(path) if path else None,
            note="Installed-program registry entry references a checked executor name.",
            extra={"display_name": row.get("DisplayName"), "publisher": row.get("Publisher")},
        )
    return hits[:80]


def scan_mui_cache_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    script = (
        "$base='HKCU:\\Software\\Classes\\Local Settings\\Software\\Microsoft\\Windows\\Shell\\MuiCache';"
        "if(-not(Test-Path $base)){ '[]' } else {"
        "Get-ItemProperty $base | Select-Object -First 1 | "
        "ForEach-Object { $_.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } | "
        "Select-Object -First 220 Name,Value } | ConvertTo-Json -Compress -Depth 3"
        "}"
    )
    data = forensic_powershell_json(script, timeout=14.0, max_chars=24000)
    rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name") or "")
        labels = executor_labels_for_artifact_text(name)
        if not labels:
            continue
        path = name.split(".FriendlyAppName", 1)[0] if ".FriendlyAppName" in name else name
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=None,
            artifact_source="mui_cache",
            file_exists=path_exists_on_disk(path),
            note="Shell MuiCache records a friendly name/path for a checked executor.",
        )
    return hits[:80]


def scan_amcache_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    path = Path(os.getenv("SystemRoot", "C:\\Windows")) / "AppCompat" / "Programs" / "Amcache.hve"
    if not path.is_file():
        return []
    try:
        data = path.read_bytes()[:50_000_000]
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return []
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    labels = scan_binary_blob_for_executor_names(data)
    for label in labels:
        _append_executor_artifact_hit(
            hits,
            seen,
            path=str(path),
            labels=[label],
            occurred_at=modified,
            artifact_source="amcache_hive",
            file_exists=True,
            note="Amcache program inventory hive contains a checked executor name (binary string match).",
        )
    for extracted in extract_dos_paths_from_binary(data, limit=40):
        path_labels = executor_labels_for_artifact_text(extracted)
        if not path_labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=extracted,
            labels=path_labels,
            occurred_at=modified,
            artifact_source="amcache_hive_path",
            file_exists=path_exists_on_disk(extracted),
            note="Amcache hive embeds a full path to a checked executor — survives file deletion.",
        )
    return hits[:120]


def scan_entire_prefetch_executor_hits() -> list[dict[str, object]]:
    """Scan every Prefetch .pf file on disk — not just the newest 120."""
    if platform.system() != "Windows":
        return []
    folder = Path(os.getenv("SystemRoot", "C:\\Windows")) / "Prefetch"
    if not folder.is_dir():
        return []
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    try:
        pf_files = list(folder.glob("*.pf"))
    except OSError:
        return []
    for pf_file in pf_files:
        name = pf_file.name
        stem = prefetch_extract_stem(name)
        labels = executor_labels_for_artifact_text(name)
        if not labels:
            labels = executor_labels_for_artifact_text(stem)
        pf_bytes: bytes = b""
        try:
            pf_bytes = pf_file.read_bytes()[:2_000_000]
            labels = sorted(set(labels + scan_binary_blob_for_executor_names(pf_bytes)))
        except OSError:
            if not labels:
                continue
        extracted_paths = extract_dos_paths_from_binary(
            pf_bytes,
            limit=16,
            require_executor_label=False,
            executable_only=True,
        ) if pf_bytes else []
        for extracted in extracted_paths:
            path_labels = executor_labels_for_artifact_text(extracted)
            if path_labels:
                labels = sorted(set(labels + path_labels))
            elif Path(extracted).exists():
                labels = sorted(set(labels + _probe_executable_binary_labels(Path(extracted))))
        if not labels:
            continue
        try:
            modified = datetime.fromtimestamp(pf_file.stat().st_mtime, timezone.utc).isoformat()
        except OSError:
            modified = None
        original_guess = extracted_paths[0] if extracted_paths else ""
        original_exists = path_exists_on_disk(original_guess) if original_guess else False
        display_path = original_guess or str(pf_file)
        _append_executor_artifact_hit(
            hits,
            seen,
            path=display_path,
            labels=labels,
            occurred_at=modified,
            artifact_source="prefetch_execution",
            timestamp_source="prefetch_mtime",
            file_exists=original_exists if original_guess else True,
            note=(
                "Full Prefetch sweep: Windows recorded this executor binary running"
                + ("; original file path is gone." if original_guess and not original_exists else ".")
            ),
            extra={"prefetch_file": str(pf_file), "prefetch_stem": stem},
        )
    return hits


def scan_all_usn_executor_path_hits(
    forensic_bundle: dict,
    deletion: dict,
) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in _collect_usn_records_for_removed_artifact_merge(forensic_bundle, deletion):
        path = str(row.get("path") or "")
        labels = executor_labels_for_artifact_text(path)
        if not labels:
            continue
        reasons = [str(r).upper() for r in (row.get("reasons") or [])]
        is_delete = any("DELETE" in r or "RENAME_OLD" in r for r in reasons)
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=row.get("display_at") or row.get("timestamp_utc"),
            artifact_source="usn_delete" if is_delete else "usn_journal",
            file_exists=path_exists_on_disk(path) if re.match(r"^[A-Za-z]:\\", path) else False,
            note="NTFS USN journal references this executor path.",
        )
    return hits[:500]


def scan_recycle_bin_content_hits(
    trash: dict,
    blocklist: dict[str, str],
) -> list[dict[str, object]]:
    """Hash and inspect $R payload files still in Recycle Bin — catches cheats before bin is emptied."""
    if platform.system() != "Windows":
        return []
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in trash.get("items") or []:
        meta_name = str(item.get("recycle_metadata_file") or item.get("name") or "")
        if not meta_name.startswith("$I"):
            continue
        location = str(item.get("location") or "")
        if not location:
            continue
        data_path = Path(location) / meta_name.replace("$I", "$R", 1)
        original_path = str(item.get("original_path") or "").strip()
        if not data_path.is_file():
            continue
        labels = list(item.get("executor_name_hits") or [])
        if original_path:
            labels = sorted(set(labels + executor_labels_for_artifact_text(original_path)))
        try:
            size = data_path.stat().st_size
        except OSError:
            continue
        sha = ""
        if blocklist and 0 < size <= RECYCLE_BIN_HASH_MAX_BYTES:
            sha = file_sha256_full(data_path, max_bytes=RECYCLE_BIN_HASH_MAX_BYTES)
            if sha and blocklist.get(sha.lower()):
                labels = sorted(set(labels + [blocklist[sha.lower()]]))
        blob_labels: list[str] = []
        try:
            blob = data_path.read_bytes()[:4_000_000]
            blob_labels = scan_binary_blob_for_executor_names(blob)
            labels = sorted(set(labels + blob_labels))
        except OSError:
            pass
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=original_path or str(data_path),
            labels=labels,
            occurred_at=item.get("display_at") or item.get("deleted_at"),
            artifact_source="recycle_bin_content",
            file_exists=True,
            note="Recycle Bin still holds the deleted file payload ($R); hashing confirms executor identity.",
            extra={
                "recycle_data_file": str(data_path),
                "sha256": sha or None,
                "original_path": original_path or None,
            },
        )
    return hits[:120]


def scan_scheduled_tasks_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    roots = [
        Path(os.getenv("SystemRoot", "C:\\Windows")) / "System32" / "Tasks",
        Path(os.getenv("SystemRoot", "C:\\Windows")) / "Tasks",
    ]
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            task_files = list(root.rglob("*.xml"))[:400]
        except OSError:
            continue
        for task_file in task_files:
            try:
                text = task_file.read_text(encoding="utf-16", errors="ignore")
            except OSError:
                try:
                    text = task_file.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
            labels = executor_labels_for_artifact_text(text)
            if not labels:
                labels = scan_binary_blob_for_executor_names(text.encode("utf-8", errors="ignore")[:500000])
            if not labels:
                continue
            for extracted in extract_dos_paths_from_binary(text.encode("utf-16le", errors="ignore"), limit=6):
                path_labels = executor_labels_for_artifact_text(extracted)
                if path_labels:
                    labels = sorted(set(labels + path_labels))
            try:
                modified = datetime.fromtimestamp(task_file.stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                modified = None
            _append_executor_artifact_hit(
                hits,
                seen,
                path=str(task_file),
                labels=labels,
                occurred_at=modified,
                artifact_source="scheduled_task",
                file_exists=True,
                note="Task Scheduler XML references a checked executor path or name.",
            )
    return hits[:80]


def scan_registry_shell_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$rows=New-Object System.Collections.Generic.List[object]
$paths=@(
 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\TypedPaths',
 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs',
 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\RunMRU',
 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\OpenSavePidlMRU',
 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\LastVisitedPidlMRU'
)
foreach($p in $paths){
  if(Test-Path $p){
    Get-ItemProperty $p -ErrorAction SilentlyContinue | ForEach-Object {
      $_.PSObject.Properties | Where-Object { $_.Name -notlike 'PS*' } | ForEach-Object {
        $rows.Add([pscustomobject]@{Source=$p; Value=([string]$_.Value); Name=$_.Name})
      }
    }
  }
}
$rows | Select-Object -First 260 | ConvertTo-Json -Compress -Depth 4
""".strip()
    data = forensic_powershell_json(script, timeout=20.0, max_chars=32000)
    rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        blob = f"{row.get('Value') or ''} {row.get('Name') or ''}"
        labels = executor_labels_for_artifact_text(blob)
        if not labels:
            continue
        path = str(row.get("Value") or row.get("Name") or blob)[:520]
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=None,
            artifact_source="registry_shell",
            file_exists=path_exists_on_disk(path) if re.match(r"^[A-Za-z]:\\", path) else None,
            note="Explorer typed/recent/open-dialog registry data references a checked executor.",
            extra={"registry_key": row.get("Source")},
        )
    return hits[:100]


def scan_wer_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    roots = [
        Path(os.getenv("LOCALAPPDATA", "")) / "CrashDumps",
        Path(os.getenv("ProgramData", "C:\\ProgramData")) / "Microsoft" / "Windows" / "WER" / "ReportArchive",
        Path(os.getenv("ProgramData", "C:\\ProgramData")) / "Microsoft" / "Windows" / "WER" / "ReportQueue",
    ]
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            files = [p for p in root.rglob("*") if p.is_file()][:120]
        except OSError:
            continue
        for path in files:
            try:
                data = path.read_bytes()[:900_000]
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                continue
            labels = scan_binary_blob_for_executor_names(data)
            if not labels and not executor_labels_for_artifact_text(path.name):
                continue
            labels = sorted(set(labels + executor_labels_for_artifact_text(path.name)))
            extracted = extract_dos_paths_from_binary(data, limit=4)
            display = extracted[0] if extracted else str(path)
            _append_executor_artifact_hit(
                hits,
                seen,
                path=display,
                labels=labels,
                occurred_at=modified,
                artifact_source="wer_crash_dump",
                file_exists=path_exists_on_disk(display),
                note="Crash/WER artifact contains a checked executor name or path.",
            )
    return hits[:80]


def scan_defender_artifact_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    roots = [
        Path(os.getenv("ProgramData", "C:\\ProgramData")) / "Microsoft" / "Windows Defender" / "Scans" / "History",
        Path(os.getenv("ProgramData", "C:\\ProgramData")) / "Microsoft" / "Windows Defender" / "Support",
    ]
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            files = [p for p in root.rglob("*") if p.is_file()][:80]
        except OSError:
            continue
        for path in files:
            if path.suffix.lower() not in {".log", ".txt", ".json", ".xml", ""}:
                continue
            try:
                data = path.read_bytes()[:600_000]
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                continue
            labels = scan_binary_blob_for_executor_names(data)
            if not labels:
                continue
            for extracted in extract_dos_paths_from_binary(data, limit=3) or [str(path)]:
                _append_executor_artifact_hit(
                    hits,
                    seen,
                    path=extracted,
                    labels=labels,
                    occurred_at=modified,
                    artifact_source="defender_history",
                    file_exists=path_exists_on_disk(extracted),
                    note="Windows Defender history/support logs mention a checked executor.",
                )
    return hits[:60]


def scan_application_event_log_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    pattern = "|".join(re.escape(name) for name in EXECUTOR_NAMES if len(name) >= 4)
    script = (
        "$start=(Get-Date).AddDays(-30);"
        f"$pat='{pattern}';"
        "Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=$start} -MaxEvents 500 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Message -match $pat } | "
        "Select-Object -First 40 TimeCreated,Id,Message | ConvertTo-Json -Compress -Depth 3"
    )
    data = forensic_powershell_json(script, timeout=22.0, max_chars=28000)
    rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        message = str(row.get("Message") or "")
        labels = executor_labels_for_artifact_text(message)
        if not labels:
            continue
        path = ""
        for match in re.finditer(r"([A-Za-z]:\\[^\s\"']{4,420})", message):
            if executor_labels_for_artifact_text(match.group(1)):
                path = match.group(1)
                break
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path or f"(application event {row.get('Id', '?')})",
            labels=labels,
            occurred_at=normalize_event_time(row.get("TimeCreated")),
            artifact_source="application_event_log",
            file_exists=path_exists_on_disk(path) if path else None,
            note="Application event log message references a checked executor.",
        )
    return hits[:40]


PROFILE_BINARY_SWEEP_EXTENSIONS = frozenset(
    {".log", ".txt", ".json", ".cfg", ".xml", ".lua", ".dat", ".ini", ".bat", ".ps1", ".ldb", ".sqlite", ".db"}
)
PROFILE_BINARY_SWEEP_MAX_FILES = 40_000
PROFILE_BINARY_SWEEP_MAX_HITS = 300


def scan_profile_binary_executor_sweep() -> list[dict[str, object]]:
    """Search all drives for leftover strings/paths after delete."""
    if platform.system() != "Windows":
        return []
    roots = [root for root, _depth in full_pc_scan_roots()]
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    enumerated = 0
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for path in walk_files_depth_limited(root, USER_FOLDER_SCAN_MAX_DEPTH):
                enumerated += 1
                if enumerated > PROFILE_BINARY_SWEEP_MAX_FILES or len(hits) >= PROFILE_BINARY_SWEEP_MAX_HITS:
                    break
                ext = path.suffix.lower()
                if ext not in PROFILE_BINARY_SWEEP_EXTENSIONS and ext != ".exe" and ext != ".dll":
                    continue
                if executor_scan_path_excluded(str(path)):
                    continue
                try:
                    size = path.stat().st_size
                    if size <= 0 or size > 2_500_000:
                        continue
                    data = path.read_bytes()[:2_500_000]
                    modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
                except OSError:
                    continue
                labels = executor_labels_for_artifact_text(path.name)
                if not labels:
                    labels = scan_binary_blob_for_executor_names(data)
                if not labels:
                    continue
                extracted = extract_dos_paths_from_binary(data, limit=2)
                display = extracted[0] if extracted else str(path)
                _append_executor_artifact_hit(
                    hits,
                    seen,
                    path=display,
                    labels=labels,
                    occurred_at=modified,
                    artifact_source="profile_binary_sweep",
                    file_exists=path_exists_on_disk(display),
                    note="User-profile binary/text sweep found a checked executor name or path residue.",
                )
        except (PermissionError, OSError):
            continue
        if enumerated > PROFILE_BINARY_SWEEP_MAX_FILES or len(hits) >= PROFILE_BINARY_SWEEP_MAX_HITS:
            break
    return hits


def scan_roblox_log_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    la = os.getenv("LOCALAPPDATA")
    if not la:
        return []
    roots = [
        Path(la) / "Roblox" / "logs",
        Path(la) / "Roblox",
    ]
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            files = [p for p in root.rglob("*.log") if p.is_file()][:80]
        except OSError:
            continue
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:500_000]
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                continue
            labels = executor_labels_for_artifact_text(text)
            if not labels:
                continue
            extracted = extract_dos_paths_from_binary(text.encode("utf-8", errors="ignore"), limit=3)
            display = extracted[0] if extracted else str(path)
            _append_executor_artifact_hit(
                hits,
                seen,
                path=display,
                labels=labels,
                occurred_at=modified,
                artifact_source="roblox_log",
                file_exists=path_exists_on_disk(display),
                note="Roblox client log mentions a checked executor.",
            )
    return hits[:40]


def scan_shimcache_executor_hits() -> list[dict[str, object]]:
    if platform.system() != "Windows":
        return []
    path = Path(os.getenv("SystemRoot", "C:\\Windows")) / "AppCompat" / "Programs" / "RecentFileCache.bcf"
    if not path.is_file():
        return []
    try:
        data = path.read_bytes()[:4_000_000]
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return []
    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    labels = scan_binary_blob_for_executor_names(data)
    for extracted in extract_dos_paths_from_binary(data, limit=12):
        row_labels = sorted(set(labels + executor_labels_for_artifact_text(extracted)))
        if not row_labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=extracted,
            labels=row_labels,
            occurred_at=modified,
            artifact_source="shimcache",
            file_exists=path_exists_on_disk(extracted),
            note="AppCompat RecentFileCache references a checked executor path.",
        )
    return hits[:60]


def scan_prefetch_executor_artifact_hits(prefetch: dict) -> list[dict[str, object]]:
    # Full-folder sweep supersedes the bounded metadata sample.
    return scan_entire_prefetch_executor_hits()


def build_executor_artifact_evidence(
    *,
    bam: dict,
    dam: dict | None,
    prefetch: dict,
    prefetch_health: dict,
    designated: dict,
    forensic_bundle: dict,
    trash: dict,
    userassist: dict,
    browser_download_history: dict | None,
    command_history: dict,
    persistence: dict,
    deletion: dict,
    sha_blocklist: dict,
    executor_indicators: dict,
    recent_items: dict,
) -> dict[str, object]:
    """Aggregate every executor trace source into one scored evidence list."""
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows-only", "hits": []}

    hits: list[dict[str, object]] = []
    seen: set[str] = set()
    sources_used: set[str] = set()

    def ingest(source: str, rows: list[dict[str, object]]) -> None:
        if rows:
            sources_used.add(source)
        hits.extend(rows)

    blocklist = load_executor_sha256_blocklist()
    ingest(
        "bam_execution_binary",
        scan_execution_artifact_binaries(bam=bam, dam=dam, blocklist=blocklist),
    )
    for item in bam.get("items") or []:
        path = str(item.get("normalized_path") or "")
        if not path or item.get("path_allowlisted") or artifact_path_is_review_noise(path):
            continue
        labels = list(item.get("executor_name_hits") or [])
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("last_execution_utc"),
            artifact_source="bam_execution",
            timestamp_source="bam_execution",
            file_exists=item.get("file_exists"),
            note="BAM recorded execution of this path.",
        )
    if any(h.get("artifact_source") == "bam_execution" for h in hits):
        sources_used.add("bam_execution")

    for item in (dam or {}).get("items") or []:
        path = str(item.get("normalized_path") or "")
        if not path or item.get("path_allowlisted") or artifact_path_is_review_noise(path):
            continue
        labels = list(item.get("executor_name_hits") or [])
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("last_execution_utc"),
            artifact_source="dam_execution",
            timestamp_source="dam_execution",
            file_exists=item.get("file_exists"),
            note="DAM recorded execution of this path.",
        )
    if any(h.get("artifact_source") == "dam_execution" for h in hits):
        sources_used.add("dam_execution")

    for item in designated.get("hits") or []:
        if item.get("removed_artifact"):
            continue
        path = str(item.get("path") or "")
        labels = list(item.get("executor_name_hits") or [])
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("modified") or item.get("accessed"),
            artifact_source="full_pc_filesystem",
            file_exists=path_exists_on_disk(path),
            note="Full-PC drive walk found this executor on disk.",
            extra={"binary_embedded_labels": item.get("binary_embedded_labels")},
        )
    if any(h.get("artifact_source") == "full_pc_filesystem" for h in hits):
        sources_used.add("full_pc_filesystem")

    ingest("prefetch_execution", scan_prefetch_executor_artifact_hits(prefetch))
    ingest("usn_journal", scan_all_usn_executor_path_hits(forensic_bundle, deletion))

    pca = forensic_bundle.get("pca_executed") or {}
    for item in pca.get("items") or []:
        path = str(item.get("normalized_path") or "")
        labels = executor_labels_for_artifact_text(path)
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("display_at") or item.get("file_modified_utc"),
            artifact_source="pca_compat",
            file_exists=item.get("file_exists"),
            note="Program Compatibility Assistant store references this path.",
        )
    if any(h.get("artifact_source") == "pca_compat" for h in hits):
        sources_used.add("pca_compat")

    for item in trash.get("items") or []:
        path = str(item.get("original_path") or "")
        labels = list(item.get("executor_name_hits") or []) or executor_labels_for_artifact_text(path)
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("display_at") or item.get("deleted_at"),
            artifact_source="recycle_bin",
            file_exists=False,
            note="Recycle Bin metadata still lists this executor path.",
        )
    if any(h.get("artifact_source") == "recycle_bin" for h in hits):
        sources_used.add("recycle_bin")

    for item in designated.get("hits") or []:
        if not item.get("removed_artifact"):
            continue
        path = str(item.get("path") or "")
        labels = list(item.get("executor_name_hits") or [])
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("display_at") or item.get("modified"),
            artifact_source=str(item.get("artifact_source") or "removed_artifact"),
            file_exists=False,
            note=str(item.get("note") or "Removed executor artifact recovered during scan."),
        )

    for item in sha_blocklist.get("hits") or []:
        path = str(item.get("path") or "")
        label = str(item.get("label") or "known_executor")
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=[label],
            occurred_at=item.get("modified"),
            artifact_source="sha256_blocklist",
            file_exists=path_exists_on_disk(path),
            note="Verified SHA256 blocklist match.",
            extra={"sha256": item.get("sha256")},
        )
    if any(h.get("artifact_source") == "sha256_blocklist" for h in hits):
        sources_used.add("sha256_blocklist")

    for item in (browser_download_history or {}).get("items") or []:
        path = str(item.get("target_path") or "")
        labels = list(item.get("matched_labels") or []) or executor_labels_for_artifact_text(path)
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("started_at") or item.get("ended_at"),
            artifact_source="browser_download",
            file_exists=path_exists_on_disk(path),
            note="Browser download history references this executor.",
        )
    if any(h.get("artifact_source") == "browser_download" for h in hits):
        sources_used.add("browser_download")

    for item in (userassist or {}).get("items") or []:
        path = str(item.get("path") or "")
        labels = list(item.get("executor_name_hits") or []) or executor_labels_for_artifact_text(path)
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("display_at") or item.get("last_run_utc"),
            artifact_source="userassist",
            file_exists=path_exists_on_disk(path),
            note="UserAssist recorded opening this executor path.",
        )
    if any(h.get("artifact_source") == "userassist" for h in hits):
        sources_used.add("userassist")

    for item in (recent_items or {}).get("items") or []:
        folder = str(item.get("folder") or "")
        name = str(item.get("name") or "")
        path = f"{folder}\\{name}" if folder and name else name or folder
        labels = list(item.get("matched_indicator_names") or []) or executor_labels_for_artifact_text(path)
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("modified") or item.get("accessed"),
            artifact_source="recent_items",
            file_exists=path_exists_on_disk(path),
            note="Recent folder listing still references this executor file.",
        )

    for item in (executor_indicators.get("file_hits") or [])[:120]:
        path = str(item.get("path") or "")
        labels = list(item.get("matched_names") or []) or executor_labels_for_artifact_text(path)
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=item.get("modified"),
            artifact_source="filesystem_indicator",
            file_exists=item.get("is_file") if item.get("is_file") is not None else path_exists_on_disk(path),
            note="Deep filesystem scan matched a checked executor name.",
        )

    for item in (persistence.get("suspicious_entries") or []):
        path = str(item.get("target") or item.get("name") or "")
        labels = list(item.get("executor_name_hits") or []) or executor_labels_for_artifact_text(path)
        if not labels:
            continue
        _append_executor_artifact_hit(
            hits,
            seen,
            path=path,
            labels=labels,
            occurred_at=None,
            artifact_source="persistence",
            file_exists=path_exists_on_disk(path),
            note="Startup/persistence entry references a checked executor.",
        )

    ingest("recent_lnk", scan_recent_lnk_executor_hits())
    ingest("registry_uninstall", scan_registry_uninstall_executor_hits())
    ingest("mui_cache", scan_mui_cache_executor_hits())
    ingest("amcache_hive", scan_amcache_executor_hits())
    ingest("registry_shell", scan_registry_shell_executor_hits())
    ingest("wer_crash_dump", scan_wer_executor_hits())
    ingest("defender_history", scan_defender_artifact_executor_hits())
    ingest("application_event_log", scan_application_event_log_executor_hits())
    ingest("profile_binary_sweep", scan_profile_binary_executor_sweep())
    ingest("roblox_log", scan_roblox_log_executor_hits())
    ingest("shimcache", scan_shimcache_executor_hits())
    ingest("recycle_bin_content", scan_recycle_bin_content_hits(trash, load_executor_sha256_blocklist()))
    ingest("scheduled_task", scan_scheduled_tasks_executor_hits())

    deletion_blob = "\n".join(
        [
            str(deletion.get("raw_sample") or ""),
            str(deletion.get("usn_delete_sample") or ""),
            json.dumps(deletion.get("deleted_file_evidence") or {}, default=str)[:120000],
        ]
    )
    for name in EXECUTOR_NAMES:
        if len(name) < 4:
            continue
        if re.search(re.escape(name), deletion_blob, re.IGNORECASE):
            _append_executor_artifact_hit(
                hits,
                seen,
                path=f"(deletion log mention) {name}",
                labels=[name],
                occurred_at=None,
                artifact_source="deletion_log_mention",
                file_exists=False,
                note="Executor name appears in deletion/USN/event-log samples collected during scan.",
            )
            sources_used.add("deletion_log_mention")

    by_executor: dict[str, int] = {}
    for hit in hits:
        for label in hit.get("executor_name_hits") or []:
            by_executor[str(label)] = by_executor.get(str(label), 0) + 1

    hits.sort(
        key=lambda row: (
            0 if row.get("file_exists") is False else 1,
            str(row.get("display_at") or row.get("modified") or ""),
        ),
        reverse=True,
    )
    return {
        "available": True,
        "hit_count": len(hits),
        "hits": hits[:1200],
        "by_executor": by_executor,
        "sources_used": sorted(sources_used),
        "executors_checked": EXECUTOR_NAMES,
        "note": "Exhaustive pass: full Prefetch folder, BAM, DAM, PCA, comprehensive USN journal, Recycle Bin metadata "
        "and $R payload hashing, Amcache path extraction, ShimCache, MuiCache, scheduled tasks, uninstall registry, "
        "Explorer typed/recent paths, WER/crash dumps, Defender logs, Application event log, Roblox logs, profile binary "
        "sweep, Recent/Jump Lists, downloads, UserAssist, and persistence. Deleting files or emptying the Recycle Bin "
        "does not remove Prefetch, BAM, USN delete records, or registry-backed traces.",
    }


def _build_shell_history_correlation_index(
    command_history: dict[str, object] | None,
) -> tuple[dict[str, str], dict[str, str]]:
    by_path: dict[str, str] = {}
    by_basename: dict[str, str] = {}
    for hit in (command_history or {}).get("hits") or []:
        ts = normalize_event_time(hit.get("occurred_at") or hit.get("history_file_modified_utc"))
        if not ts:
            continue
        line = str(hit.get("line") or "")
        for match in re.finditer(r'([A-Za-z]:\\(?:[^"\n\r]+))', line, re.IGNORECASE):
            key = _artifact_path_key(match.group(1))
            if key:
                existing = by_path.get(key)
                if not existing or ts > existing:
                    by_path[key] = ts
        for match in re.finditer(r"([^\s\\/,;\"|]+\.(?:exe|dll|bat|ps1))", line, re.IGNORECASE):
            base = match.group(1).lower()
            existing = by_basename.get(base)
            if not existing or ts > existing:
                by_basename[base] = ts
    return by_path, by_basename


def resolve_path_activity_timestamp(
    path: str,
    *,
    bam: dict[str, object] | None = None,
    prefetch: dict[str, object] | None = None,
    usn_records: list[dict[str, object]] | None = None,
    trash: dict[str, object] | None = None,
    designated: dict[str, object] | None = None,
    recent_items: dict[str, object] | None = None,
    userassist: dict[str, object] | None = None,
    command_history: dict[str, object] | None = None,
    pca_store_key_modified: str | None = None,
) -> tuple[str | None, str | None, dict[str, str]]:
    norm = str(path or "")
    if not norm:
        return None, None, {}
    stem = Path(norm).stem.upper() if norm else ""
    correlated: dict[str, str] = {}

    bam_by_path, bam_by_base = _build_timestamp_index(
        list((bam or {}).get("items") or []),
        path_field="normalized_path",
        time_field="last_execution_utc",
    )
    usn_by_path, usn_by_delete, usn_by_base = _build_usn_timestamp_index(list(usn_records or []))
    prefetch_by_stem = _build_prefetch_timestamp_index(prefetch or {})
    recycle_by_path = _build_recycle_timestamp_index(trash or {})
    designated_by_path = _build_simple_path_timestamp_index(
        list((designated or {}).get("hits") or []),
        path_field="path",
        time_field="modified",
    )
    recent_by_path: dict[str, str] = {}
    for item in (recent_items or {}).get("items") or []:
        folder = str(item.get("folder") or "")
        name = str(item.get("name") or "")
        combined = _artifact_path_key(f"{folder}\\{name}" if folder and name else name or folder)
        ts = normalize_event_time(item.get("modified"))
        if combined and ts:
            existing = recent_by_path.get(combined)
            if not existing or ts > existing:
                recent_by_path[combined] = ts
    userassist_by_path = _build_simple_path_timestamp_index(
        list((userassist or {}).get("items") or []),
        path_field="path",
        time_field="last_run_utc",
    )
    shell_by_path, shell_by_base = _build_shell_history_correlation_index(command_history)

    bam_ts = _lookup_indexed_timestamp(norm, bam_by_path, bam_by_base)
    if bam_ts:
        correlated["bam_execution"] = bam_ts
    usn_delete_ts = _lookup_indexed_timestamp(norm, usn_by_delete, usn_by_base)
    if usn_delete_ts:
        correlated["usn_delete"] = usn_delete_ts
    usn_ts = _lookup_indexed_timestamp(norm, usn_by_path, usn_by_base)
    if usn_ts:
        correlated["usn_journal"] = usn_ts
    if stem in prefetch_by_stem:
        correlated["prefetch_mtime"] = prefetch_by_stem[stem]
    recycle_ts = _lookup_indexed_timestamp(norm, recycle_by_path, {})
    if recycle_ts:
        correlated["recycle_bin"] = recycle_ts
    designated_ts = _lookup_indexed_timestamp(norm, designated_by_path, {})
    if designated_ts:
        correlated["designated_mtime"] = designated_ts
    recent_ts = _lookup_indexed_timestamp(norm, recent_by_path, {})
    if recent_ts:
        correlated["recent_mtime"] = recent_ts
    userassist_ts = _lookup_indexed_timestamp(norm, userassist_by_path, {})
    if userassist_ts:
        correlated["userassist"] = userassist_ts
    shell_ts = _lookup_indexed_timestamp(norm, shell_by_path, shell_by_base)
    if shell_ts:
        correlated["powershell_history"] = shell_ts

    fallback_order = (
        "bam_execution",
        "prefetch_mtime",
        "usn_delete",
        "powershell_history",
        "recycle_bin",
        "designated_mtime",
        "recent_mtime",
        "userassist",
        "usn_journal",
    )
    fallbacks = [(name, correlated[name]) for name in fallback_order if name in correlated]
    display_at, timestamp_source = resolve_display_timestamp(primary=None, fallbacks=fallbacks)
    if not display_at and pca_store_key_modified:
        display_at, timestamp_source = pca_store_key_modified, "pca_store_key_mtime"
    return display_at, timestamp_source, correlated


def _apply_resolved_timestamp_to_pca_item(
    item: dict[str, object],
    display_at: str | None,
    timestamp_source: str | None,
    correlated: dict[str, str],
) -> None:
    if correlated:
        item["correlated_timestamps"] = correlated
    if not display_at:
        return
    item["display_at"] = display_at
    item["timestamp_source"] = timestamp_source
    if timestamp_source == "bam_execution":
        item["last_execution_utc"] = display_at
    elif timestamp_source == "prefetch_mtime":
        item["prefetch_modified_utc"] = display_at
    elif timestamp_source in {"usn_delete", "usn_journal"}:
        item["usn_timestamp_utc"] = display_at
    elif timestamp_source == "recycle_bin":
        item["recycle_deleted_at"] = display_at
    elif timestamp_source == "powershell_history":
        item["powershell_history_utc"] = display_at


def enrich_pca_executed_records(
    pca: dict[str, object],
    *,
    bam: dict[str, object],
    prefetch: dict[str, object],
    usn_records: list[dict[str, object]],
    trash: dict[str, object] | None = None,
    designated: dict[str, object] | None = None,
    recent_items: dict[str, object] | None = None,
    userassist: dict[str, object] | None = None,
    command_history: dict[str, object] | None = None,
) -> dict[str, object]:
    if not pca.get("available"):
        return pca
    store_key_modified = normalize_event_time(pca.get("store_key_modified_utc"))
    for item in pca.get("items") or []:
        if item.get("display_at"):
            continue
        norm = str(item.get("normalized_path") or "")
        if not norm:
            continue
        display_at, timestamp_source, correlated = resolve_path_activity_timestamp(
            norm,
            bam=bam,
            prefetch=prefetch,
            usn_records=usn_records,
            trash=trash,
            designated=designated,
            recent_items=recent_items,
            userassist=userassist,
            command_history=command_history,
            pca_store_key_modified=store_key_modified,
        )
        _apply_resolved_timestamp_to_pca_item(item, display_at, timestamp_source, correlated)
    return pca


def sync_forensic_finding_timestamps(
    forensic_bundle: dict[str, object],
    *,
    bam: dict[str, object],
    prefetch: dict[str, object],
    usn_records: list[dict[str, object]],
    trash: dict[str, object] | None = None,
    designated: dict[str, object] | None = None,
    recent_items: dict[str, object] | None = None,
    userassist: dict[str, object] | None = None,
    command_history: dict[str, object] | None = None,
) -> None:
    pca = forensic_bundle.get("pca_executed") or {}
    pca_items = list(pca.get("items") or [])
    store_key_modified = normalize_event_time(pca.get("store_key_modified_utc"))
    for finding in forensic_bundle.get("detections_flat") or []:
        if not isinstance(finding, dict):
            continue
        path = str(finding.get("file_path") or "")
        if not path:
            continue
        existing_ts = (finding.get("timestamps") or {}).get("display_at")
        if existing_ts and str(existing_ts).strip() and str(existing_ts).lower() not in {"none", "null"}:
            continue
        display_at, timestamp_source, correlated = resolve_path_activity_timestamp(
            path,
            bam=bam,
            prefetch=prefetch,
            usn_records=usn_records,
            trash=trash,
            designated=designated,
            recent_items=recent_items,
            userassist=userassist,
            command_history=command_history,
            pca_store_key_modified=store_key_modified,
        )
        for item in pca_items:
            if _paths_relate(path, str(item.get("normalized_path") or "")):
                _apply_resolved_timestamp_to_pca_item(item, display_at, timestamp_source, correlated)
                break
        if display_at:
            finding["timestamps"] = {
                "display_at": display_at,
                "timestamp_source": timestamp_source,
                "correlated": correlated,
            }


def patch_unified_correlation_timeline(forensic_bundle: dict[str, object]) -> None:
    uc = forensic_bundle.get("unified_correlation")
    if not isinstance(uc, dict):
        return
    pca_items = list((forensic_bundle.get("pca_executed") or {}).get("items") or [])
    timeline = list(uc.get("timeline") or [])
    for row in timeline:
        if row.get("artifact") != "pca_store":
            continue
        path = str(row.get("path") or "")
        for item in pca_items:
            norm = str(item.get("normalized_path") or "")
            if not _paths_relate(path, norm):
                continue
            ts = item.get("display_at") or item.get("file_modified_utc")
            if ts:
                row["timestamp"] = ts
            break
    timeline.sort(key=lambda x: (x.get("timestamp") or ""), reverse=True)
    uc["timeline"] = timeline


def removable_drive_letters() -> set[str]:
    if platform.system() != "Windows":
        return set()
    script = (
        "Get-CimInstance Win32_LogicalDisk -ErrorAction SilentlyContinue | "
        "Where-Object { $_.DriveType -eq 2 } | ForEach-Object { $_.DeviceID.TrimEnd(':') } | ConvertTo-Json -Compress"
    )
    data = forensic_powershell_json(script, timeout=10.0, max_chars=2000)
    letters: set[str] = set()
    if isinstance(data, list):
        for x in data:
            if isinstance(x, str) and len(x) == 1 and x.isalpha():
                letters.add(x.upper())
    elif isinstance(data, str) and len(data) == 1:
        letters.add(data.upper())
    return letters


def usn_journal_comprehensive_read(*, force_refresh: bool = False) -> dict[str, object]:
    """Read recent NTFS USN journal tail under the user profile — survives delete + empty Recycle Bin."""
    global _usn_comprehensive_cache
    if _usn_comprehensive_cache is not None and not force_refresh:
        return _usn_comprehensive_cache
    if platform.system() != "Windows":
        result = {"available": False, "lines": [], "delete_lines": [], "reason": "Windows-only"}
        _usn_comprehensive_cache = result
        return result
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$profile = ($env:USERPROFILE + '\').ToLower()
$maxLifecycle = 6000
$maxDelete = 3000
$usnList = New-Object System.Collections.Generic.List[string]
$deleteList = New-Object System.Collections.Generic.List[string]
foreach ($d in (Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3 OR DriveType=2' | ForEach-Object { $_.DeviceID })) {
  try {
    $startUsn = 0
    $qj = fsutil usn queryjournal $d 2>$null
    if ($qj) {
      foreach ($qline in ($qj -split "`n")) {
        if ($qline -match '(?:Next|Max) USN:\s*0x([0-9a-fA-F]+)') {
          $parsed = [Convert]::ToUInt64($matches[1], 16)
          if ($parsed -gt 50000000) { $startUsn = $parsed - 50000000 } else { $startUsn = 0 }
        }
      }
    }
    fsutil usn readjournal $d csv start=$startUsn max=4500 2>$null | ForEach-Object {
      $line = $_.TrimEnd("`r")
      if (-not $line) { return }
      $lower = $line.ToLower()
      $inProfile = $lower.Contains($profile)
      $isDelete = $line -match 'FILE_DELETE|0x80000002|0x80000200'
      $isRename = $line -match 'RENAME_OLD_NAME|RENAME_NEW_NAME|0x00001000|0x00002000'
      $isExec = $line -match '\.EXE|\.DLL|\.PS1|\.BAT|\.MSI|\.VBS|\.JS'
      $isCheatish = $line -match '(?i)cheat|hack|exploit|inject|script.?hub|aimbot|executor|delta|solara|synapse|potassium|wave|xeno|volt|cosmic|lumen|seliware|madium|sirhurt|serotonin|severe|rbxcli|matcha|photon|vegax|codex|macsploit|opiumware|dx9ware|matrixhub|velocity'
      if ($isDelete -and $deleteList.Count -lt $maxDelete -and ($isExec -or $isCheatish -or $inProfile)) {
        [void]$deleteList.Add(($d + [char]9 + $line))
      }
      if ($usnList.Count -lt $maxLifecycle -and ($isExec -or $isCheatish -or $inProfile) -and
          ($isDelete -or $isRename -or $line -match 'FILE_CREATE|CLOSE|DATA_EXTEND|BASIC_INFO|STREAM_CHANGE')) {
        [void]$usnList.Add(($d + [char]9 + $line))
      }
    }
  } catch {}
}
[pscustomobject]@{
  lifecycle_lines = @($usnList)
  delete_lines = @($deleteList)
} | ConvertTo-Json -Compress -Depth 3
""".strip()
    data = forensic_powershell_json(script, timeout=48.0, max_chars=520000)
    lines: list[str] = []
    delete_lines: list[str] = []
    if isinstance(data, dict):
        raw_lifecycle = data.get("lifecycle_lines")
        raw_delete = data.get("delete_lines")
        if isinstance(raw_lifecycle, list):
            lines = [str(x) for x in raw_lifecycle]
        if isinstance(raw_delete, list):
            delete_lines = [str(x) for x in raw_delete]
    result = {
        "available": True,
        "lines": lines[:USN_JOURNAL_MAX_LINES],
        "delete_lines": delete_lines[:USN_DELETE_MAX_LINES],
        "lifecycle_line_count": len(lines),
        "delete_line_count": len(delete_lines),
        "source": "fsutil usn readjournal (recent journal tail, user-profile focused)",
    }
    _usn_comprehensive_cache = result
    return result


def usn_journal_enriched_sample() -> dict[str, object]:
    pack = usn_journal_comprehensive_read()
    return {
        "available": pack.get("available", False),
        "lines": list(pack.get("lines") or []),
        "delete_lines": list(pack.get("delete_lines") or []),
        "source": pack.get("source"),
        "lifecycle_line_count": pack.get("lifecycle_line_count"),
        "delete_line_count": pack.get("delete_line_count"),
    }


def usn_parse_records(lines: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in lines:
        if not line or line.startswith("Unavailable"):
            continue
        drive = ""
        body = line
        if "\t" in line:
            drive, body = line.split("\t", 1)
        reasons = []
        for tag in (
            "FILE_CREATE",
            "FILE_DELETE",
            "FILE_DELETE_CLOSE",
            "DATA_EXTEND",
            "DATA_TRUNCATION",
            "RENAME_OLD_NAME",
            "RENAME_NEW_NAME",
            "CLOSE",
            "BASIC_INFO_CHANGE",
            "INTEGRITY_CHANGE",
            "STREAM_CHANGE",
        ):
            if tag in body:
                reasons.append(tag)
        path_m = re.search(r"([A-Za-z]:\\(?:[^,\"\n\r\t|<>?]+))", body)
        path = path_m.group(1) if path_m else ""
        if not path:
            path_m2 = re.search(r"(\\\\[^\s,\"]+)", body)
            path = path_m2.group(1) if path_m2 else ""
        timestamp_utc = parse_usn_timestamp(body)
        display_at, timestamp_source = resolve_display_timestamp(primary=timestamp_utc)
        rows.append(
            {
                "drive": drive,
                "reasons": reasons,
                "path": path,
                "timestamp_utc": timestamp_utc,
                "display_at": display_at,
                "timestamp_source": timestamp_source,
                "raw": body[:900],
            }
        )
    return rows


CHROMIUM_DOWNLOAD_STATE_LABELS: dict[int, str] = {
    0: "in_progress",
    1: "complete",
    2: "cancelled",
    3: "interrupted",
    4: "dangerous",
}


def _download_basename(path: str) -> str:
    normalized = str(path or "").replace("/", "\\").strip()
    if not normalized:
        return ""
    parts = [part for part in normalized.split("\\") if part]
    return parts[-1] if parts else normalized


def _download_sort_ms(row: dict) -> float:
    ts = row.get("started_at") or row.get("ended_at")
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _chromium_user_data_roots() -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    la = os.getenv("LOCALAPPDATA")
    if not la:
        return roots
    mapping = (
        ("Chrome", Path(la) / "Google" / "Chrome" / "User Data"),
        ("Edge", Path(la) / "Microsoft" / "Edge" / "User Data"),
        ("Brave", Path(la) / "BraveSoftware" / "Brave-Browser" / "User Data"),
        ("Opera", Path(la) / "Opera Software" / "Opera Stable" / "User Data"),
        ("Opera GX", Path(la) / "Opera Software" / "Opera GX Stable" / "User Data"),
        ("Vivaldi", Path(la) / "Vivaldi" / "User Data"),
    )
    for label, base in mapping:
        if base.is_dir():
            roots.append((label, base))
    return roots


def _chromium_history_database_paths() -> list[tuple[str, str, Path]]:
    paths: list[tuple[str, str, Path]] = []
    for browser, base in _chromium_user_data_roots():
        for prof in _chromium_profile_names(base):
            hp = base / prof / "History"
            if hp.is_file():
                paths.append((browser, prof, hp))
    return paths


def _firefox_profile_download_databases() -> list[tuple[str, Path]]:
    rows: list[tuple[str, Path]] = []
    appdata = os.getenv("APPDATA")
    if not appdata:
        return rows
    profiles_root = Path(appdata) / "Mozilla" / "Firefox" / "Profiles"
    if not profiles_root.is_dir():
        return rows
    try:
        for entry in profiles_root.iterdir():
            if not entry.is_dir():
                continue
            db = entry / "downloads.sqlite"
            if db.is_file():
                rows.append((entry.name, db))
    except OSError:
        pass
    return rows


def _download_row_matches(path: str, url: str, patterns: dict[str, re.Pattern[str]]) -> tuple[bool, list[str]]:
    labels = sorted(set(match_executor_labels(f"{path} {url}", patterns)))
    labels.extend(cheat_path_hint_labels(path))
    if not labels and url:
        lower = url.lower()
        if any(ext in lower for ext in (".exe", ".dll", ".bat", ".ps1", ".msi", ".zip", ".rar", ".7z")):
            labels.append("download_url_extension")
    return bool(labels), labels


def _read_chromium_downloads(browser: str, profile: str, history_db: Path, patterns: dict[str, re.Pattern[str]]) -> list[dict]:
    items: list[dict] = []
    conn = _sqlite_open_readonly(history_db)
    if not conn:
        return items
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='downloads'"
        )
        if not cur.fetchone():
            return items
        cur.execute(
            """
            SELECT target_path, tab_url, start_time, end_time, received_bytes, total_bytes, state, danger_type, mime_type
            FROM downloads
            WHERE start_time IS NOT NULL AND start_time > 0
            ORDER BY start_time DESC
            LIMIT 180
            """
        )
        for target_path, tab_url, start_time, end_time, received, total, state, danger_type, mime_type in cur.fetchall():
            path = str(target_path or "")
            url = str(tab_url or "")
            started = chrome_webkit_time_to_iso(start_time)
            ended = chrome_webkit_time_to_iso(end_time)
            suspicious, labels = _download_row_matches(path, url, patterns)
            state_code = int(state) if state is not None else -1
            items.append(
                {
                    "browser": browser,
                    "profile": profile,
                    "url": url[:520],
                    "target_path": path[:520],
                    "file_name": _download_basename(path) or _download_basename(url),
                    "started_at": started,
                    "ended_at": ended,
                    "received_bytes": received,
                    "total_bytes": total,
                    "state": CHROMIUM_DOWNLOAD_STATE_LABELS.get(state_code, str(state_code)),
                    "state_code": state_code,
                    "danger_type": danger_type,
                    "mime_type": str(mime_type or "")[:120],
                    "suspicious": suspicious,
                    "matched_labels": labels,
                    "source": "chromium_downloads_table",
                }
            )
    except sqlite3.Error:
        pass
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    return items


def _read_firefox_downloads(profile_name: str, db_path: Path, patterns: dict[str, re.Pattern[str]]) -> list[dict]:
    items: list[dict] = []
    conn = _sqlite_open_readonly(db_path)
    if not conn:
        return items
    queries = (
        """
        SELECT content, source, start_time, end_time, state, total_bytes, fileSize
        FROM moz_downloads
        WHERE start_time IS NOT NULL AND start_time > 0
        ORDER BY start_time DESC
        LIMIT 150
        """,
        """
        SELECT target, source, start_time, end_time, state, total_bytes, fileSize
        FROM moz_downloads
        WHERE start_time IS NOT NULL AND start_time > 0
        ORDER BY start_time DESC
        LIMIT 150
        """,
    )
    try:
        cur = conn.cursor()
        rows: list[tuple] = []
        for sql in queries:
            try:
                cur.execute(sql)
                rows = cur.fetchall()
                if rows:
                    break
            except sqlite3.Error:
                continue
        for row in rows:
            path = str(row[0] or "")
            source_field = str(row[1] or "") if len(row) > 1 else ""
            start_time = row[2] if len(row) > 2 else None
            end_time = row[3] if len(row) > 3 else None
            started = firefox_pr_time_to_iso(start_time)
            ended = firefox_pr_time_to_iso(end_time)
            url = source_field if source_field.startswith("http") else ""
            suspicious, labels = _download_row_matches(path, url, patterns)
            items.append(
                {
                    "browser": "Firefox",
                    "profile": profile_name,
                    "url": url[:520],
                    "target_path": path[:520],
                    "file_name": _download_basename(path),
                    "started_at": started,
                    "ended_at": ended,
                    "received_bytes": row[6] if len(row) > 6 else None,
                    "total_bytes": row[5] if len(row) > 5 else None,
                    "state": str(row[4]) if len(row) > 4 else "unknown",
                    "state_code": row[4] if len(row) > 4 else None,
                    "danger_type": None,
                    "mime_type": "",
                    "suspicious": suspicious,
                    "matched_labels": labels,
                    "source": "firefox_downloads_sqlite",
                }
            )
    except sqlite3.Error:
        pass
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    return items


def browser_download_history_scan() -> dict[str, object]:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Browser download history is Windows-focused in this build"}

    patterns = executor_name_patterns()
    items: list[dict] = []
    browsers_probed: list[str] = []

    for browser, profile, history_db in _chromium_history_database_paths():
        browsers_probed.append(f"{browser}/{profile}")
        items.extend(_read_chromium_downloads(browser, profile, history_db, patterns))

    for profile_name, db_path in _firefox_profile_download_databases():
        browsers_probed.append(f"Firefox/{profile_name}")
        items.extend(_read_firefox_downloads(profile_name, db_path, patterns))

    items.sort(key=_download_sort_ms, reverse=True)
    suspicious_count = sum(1 for row in items if row.get("suspicious"))
    return {
        "available": True,
        "download_count": len(items),
        "suspicious_count": suspicious_count,
        "browsers_probed": browsers_probed[:20],
        "items": items[:250],
        "note": "Reads Chrome, Edge, Brave, Opera, and Vivaldi (History downloads table) and Firefox "
        "(downloads.sqlite). Copies locked databases when needed.",
    }


def sqlite_forensic_probe() -> dict[str, object]:
    findings: list[dict[str, object]] = []
    if platform.system() != "Windows":
        return {"available": False, "findings": findings}
    history_paths: list[Path] = [hp for _, _, hp in _chromium_history_database_paths()]
    keywords_sql = []
    for group_name, terms in (
        ("cheat_terms", _CHEAT_QUERY_TERMS),
        ("loader_terms", _LOADER_TERMS),
    ):
        for t in terms:
            keywords_sql.append((group_name, t.replace("'", "''")))
    for hp in history_paths[:6]:
        wal = hp.parent / (hp.name + "-wal")
        shm = hp.parent / (hp.name + "-shm")
        uri = f"file:{hp.as_posix()}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        except sqlite3.Error:
            try:
                conn = sqlite3.connect(str(hp), timeout=2.0)
            except sqlite3.Error as exc:
                findings.append(
                    {
                        "database": str(hp),
                        "error": str(exc),
                        "wal_present": wal.exists(),
                        "shm_present": shm.exists(),
                    }
                )
                continue
        try:
            cur = conn.cursor()
            try:
                cur.execute("PRAGMA freelist_count")
                fl = int(cur.fetchone()[0])
            except sqlite3.Error:
                fl = -1
            hits: list[dict[str, object]] = []
            for group_name, term in keywords_sql[:48]:
                try:
                    cur.execute(
                        "SELECT url, title, last_visit_time FROM urls WHERE url LIKE ? LIMIT 8",
                        (f"%{term}%",),
                    )
                    for url, title, lvt in cur.fetchall():
                        hits.append({"group": group_name, "term": term, "url": (url or "")[:500], "title": (title or "")[:240], "last_visit_time": lvt})
                except sqlite3.Error:
                    continue
            exe_hits: list[dict[str, object]] = []
            try:
                cur.execute(
                    "SELECT url, title, last_visit_time FROM urls WHERE url LIKE '%.exe%' OR url LIKE '%.dll%' LIMIT 15"
                )
                for url, title, lvt in cur.fetchall():
                    exe_hits.append({"url": (url or "")[:500], "title": (title or "")[:200], "last_visit_time": lvt})
            except sqlite3.Error:
                pass
            temp_hist: list[dict[str, object]] = []
            try:
                cur.execute(
                    "SELECT url, title, last_visit_time FROM urls WHERE "
                    "lower(url) LIKE '%/temp/%' OR lower(url) LIKE '%\\\\temp\\\\%' OR lower(url) LIKE '%/tmp/%' "
                    "LIMIT 12"
                )
                for url, title, lvt in cur.fetchall():
                    temp_hist.append({"url": (url or "")[:500], "title": (title or "")[:200], "last_visit_time": lvt})
            except sqlite3.Error:
                pass
            findings.append(
                {
                    "database": str(hp),
                    "wal_present": wal.exists(),
                    "shm_present": shm.exists(),
                    "freelist_count": fl,
                    "keyword_hits": hits[:40],
                    "executable_url_hits": exe_hits[:20],
                    "temp_path_url_hits": temp_hist[:12],
                    "note": "WAL present may retain uncommitted rows; freelist_count>0 suggests carve-able deleted records (not live-carved).",
                }
            )
        finally:
            try:
                conn.close()
            except sqlite3.Error:
                pass
    return {"available": True, "findings": findings}


def prefetch_extract_stem(pf_name: str) -> str:
    m = re.match(r"(.+)-[0-9A-F]{8}\.pf\Z", pf_name, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return Path(pf_name).stem.upper()


def basename_key(path: str) -> str:
    if not path:
        return ""
    try:
        return Path(path).name.lower()
    except OSError:
        return ""


class UnifiedCorrelationEngine:
    def build(
        self,
        *,
        designated: dict[str, object],
        prefetch: dict[str, object],
        deletion: dict[str, object],
        bam: dict[str, object],
        pca: dict[str, object],
        sqlite_pack: dict[str, object],
        usn_records: list[dict[str, object]],
        detections_flat: list[dict[str, object]],
    ) -> dict[str, object]:
        timeline: list[dict[str, object]] = []
        for item in designated.get("hits", [])[:120]:
            timeline.append(
                {
                    "artifact": "designated_folder_scan",
                    "path": item.get("path"),
                    "timestamp": item.get("modified"),
                    "detail": "user_profile_hit",
                }
            )
        for it in bam.get("items", [])[:200]:
            timeline.append(
                {
                    "artifact": "bam",
                    "path": it.get("normalized_path"),
                    "timestamp": it.get("last_execution_utc"),
                    "detail": "bam_execution",
                }
            )
        for it in pca.get("items", [])[:200]:
            timeline.append(
                {
                    "artifact": "pca_store",
                    "path": it.get("normalized_path"),
                    "timestamp": it.get("display_at") or it.get("file_modified_utc"),
                    "detail": "pca_record",
                }
            )
        for row in usn_records[:180]:
            timeline.append(
                {
                    "artifact": "usn",
                    "path": row.get("path"),
                    "timestamp": row.get("display_at") or row.get("timestamp_utc"),
                    "detail": ",".join(row.get("reasons") or []) or "usn_row",
                }
            )
        for pf in prefetch.get("items", [])[:120]:
            timeline.append(
                {
                    "artifact": "prefetch",
                    "path": str(Path(str(prefetch.get("folder", ""))) / str(pf.get("name", ""))) if prefetch.get("folder") else pf.get("name"),
                    "timestamp": pf.get("modified"),
                    "detail": "prefetch_trace",
                }
            )
        timeline.sort(key=lambda x: (x.get("timestamp") or ""), reverse=True)

        prefetch_basenames = {prefetch_extract_stem(x.get("name", "")) for x in prefetch.get("items", []) if x.get("name")}
        bam_names = {basename_key(str(x.get("normalized_path", ""))) for x in bam.get("items", [])}
        chains: list[dict[str, object]] = []

        def prefetch_stem_base(st: str) -> str:
            return Path(st).stem.upper() if st else ""

        for stem in sorted(prefetch_basenames):
            if len(stem) < 4:
                continue
            st_base = prefetch_stem_base(stem)
            chain_evidence: list[dict[str, object]] = []
            if any(st_base == Path(str(h.get("path", ""))).stem.upper() for h in designated.get("hits", [])):
                chain_evidence.append({"source": "saved_files", "detail": "profile_hit_same_stem"})
            if stem.lower() in bam_names or f"{st_base.lower()}.exe" in bam_names or f"{st_base.lower()}.dll" in bam_names:
                chain_evidence.append({"source": "bam", "detail": "execution_record"})
            if any(
                st_base == Path(str(r.get("path", ""))).stem.upper()
                for r in usn_records
                if "DELETE" in ",".join(r.get("reasons") or [])
            ):
                chain_evidence.append({"source": "usn", "detail": "delete_near_stem"})
            if len(chain_evidence) >= 2:
                chains.append(
                    {
                        "pattern": "download_or_staging_to_execution",
                        "stem": stem,
                        "evidence": chain_evidence,
                    }
                )

        pca_paths = [str(it.get("normalized_path") or "") for it in pca.get("items", []) if it.get("normalized_path")]
        pca_counts = Counter(pca_paths)
        for path, cnt in pca_counts.most_common(12):
            if cnt >= 3 and path.lower().endswith(".exe"):
                chains.append(
                    {
                        "pattern": "pca_crash_loop_or_repeat_launch",
                        "stem": Path(path).stem.upper(),
                        "evidence": [{"source": "pca_store", "detail": f"repeated_entries={cnt}", "path": path[:520]}],
                    }
                )

        return {
            "engine_version": _FORENSIC_ENGINE_VERSION,
            "timeline": timeline[:400],
            "execution_chains": chains[:80],
            "cross_artifact_summary": {
                "prefetch_stems_sampled": len(prefetch_basenames),
                "bam_basenames": len(bam_names),
                "usn_rows": len(usn_records),
                "flat_detection_count": len(detections_flat),
            },
        }


def assemble_forensic_detections(
    designated: dict[str, object],
    prefetch: dict[str, object],
    deletion: dict[str, object],
    bam_struct: dict[str, object],
    pca: dict[str, object],
    sqlite_pack: dict[str, object],
    usn_extra: dict[str, object],
) -> dict[str, object]:
    detections: dict[str, list[dict[str, object]]] = {k: [] for k in (
        "saved_files",
        "usn",
        "bam",
        "deleted_bam",
        "sqlite",
        "prefetch",
        "pca",
        "global",
    )}
    flat: list[dict[str, object]] = []
    removable = removable_drive_letters()

    usn_lines = list(usn_extra.get("lines") or []) + list(usn_extra.get("delete_lines") or [])
    usn_text = str(deletion.get("usn_delete_sample") or "")
    if usn_text:
        usn_lines.extend(usn_text.splitlines()[:USN_DELETE_MAX_LINES])
    usn_records = usn_parse_records(usn_lines)

    bam_items = bam_struct.get("items") or []
    bam_name_set = {basename_key(str(x.get("normalized_path", ""))) for x in bam_items if x.get("normalized_path")}
    exec_cache = build_executable_forensic_cache(
        _collect_forensic_exec_paths(designated, bam_items, pca.get("items") or [])
    )

    temp_delete_exe = [
        r
        for r in usn_records
        if forensic_is_temp_path(r.get("path") or "")
        and any("DELETE" in x for x in (r.get("reasons") or []))
        and re.search(r"\.(exe|dll)\Z", (r.get("path") or ""), re.IGNORECASE)
    ]
    if temp_delete_exe:
        detections["usn"].append(
            forensic_finding(
                severity="high",
                confidence=0.62,
                reason="Executable-related USN delete/close activity under a temp or cache directory (staging/cleanup).",
                artifact_source="USN Journal (bounded sample)",
                file_path=temp_delete_exe[0].get("path", "")[:520],
                correlated_evidence=[{"source": "usn", "detail": r.get("raw", "")[:240]} for r in temp_delete_exe[:5]],
                risk_score=forensic_risk_score(unsigned=True, temp_path=True, deleted_hint=True),
            )
        )

    rename_rows = [r for r in usn_records if any("RENAME" in x for x in (r.get("reasons") or [])) and r.get("path")]
    if len(rename_rows) >= 2:
        detections["usn"].append(
            forensic_finding(
                severity="medium",
                confidence=0.55,
                reason="Rename-related USN reasons observed; may indicate rename chains prior to execution.",
                artifact_source="USN Journal",
                file_path=rename_rows[0].get("path", "")[:520],
                correlated_evidence=[{"source": "usn", "detail": x.get("raw", "")[:200]} for x in rename_rows[:6]],
                risk_score=forensic_risk_score(rename_hint=True),
            )
        )

    ads_rows = [r for r in usn_records if ":" in (r.get("path") or "") or "STREAM_CHANGE" in ",".join(r.get("reasons") or [])]
    if ads_rows:
        detections["usn"].append(
            forensic_finding(
                severity="medium",
                confidence=0.48,
                reason="Possible alternate data stream or stream change activity in USN sample.",
                artifact_source="USN Journal",
                file_path=ads_rows[0].get("path", "")[:520],
                correlated_evidence=[{"source": "usn", "detail": x.get("raw", "")[:200]} for x in ads_rows[:4]],
                risk_score=40,
            )
        )

    timestomp_hint = [r for r in usn_records if "BASIC_INFO_CHANGE" in (r.get("reasons") or []) and re.search(r"\.exe\Z", r.get("path") or "", re.I)]
    if timestomp_hint:
        detections["usn"].append(
            forensic_finding(
                severity="low",
                confidence=0.35,
                reason="BASIC_INFO_CHANGE on executable path(s); corroborate with SI vs FN MFT attributes offline.",
                artifact_source="USN Journal",
                file_path=timestomp_hint[0].get("path", "")[:520],
                correlated_evidence=[{"source": "usn", "detail": x.get("raw", "")[:180]} for x in timestomp_hint[:4]],
                risk_score=22,
            )
        )

    path_groups: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for r in usn_records:
        key = basename_key(r.get("path") or "")
        if key:
            path_groups[key].append(r)
    clusters = [(k, v) for k, v in path_groups.items() if len(v) >= 4 and k.endswith((".exe", ".dll"))]
    if clusters:
        k, v = clusters[0]
        detections["usn"].append(
            forensic_finding(
                severity="medium",
                confidence=0.5,
                reason="Clustered USN activity for a single filename (rapid lifecycle / staging).",
                artifact_source="USN Journal",
                file_path=v[0].get("path", "")[:520],
                correlated_evidence=[{"source": "usn_cluster", "detail": str(len(v))}],
                risk_score=35,
            )
        )

    for hit in designated.get("hits", [])[:80]:
        p = str(hit.get("path") or "")
        ext = Path(p).suffix.lower()
        sha256, ent, _sz = ("", None, None)
        sig = "not_checked"
        ymatches: list[str] = []
        if ext in {".exe", ".dll"} and p:
            analysis = exec_forensic_lookup(exec_cache, p)
            sha256 = str(analysis["sha256"])
            ent = analysis["ent"]
            sig = str(analysis["sig"])
            ymatches = list(analysis["ymatches"] or [])
        unsigned = sig.upper() in {"NOTSIGNED", "NOT_SIGNED"} or "NOTSIGNED" in sig.upper()
        high_ent = ent is not None and ent >= 7.4
        in_temp = forensic_is_temp_path(p)
        in_dl = forensic_is_downloads_path(p)
        reasons_list: list[str] = []
        if in_dl and ext in {".exe", ".dll"}:
            reasons_list.append("executable_under_downloads")
        if in_temp and ext in {".exe", ".dll"}:
            reasons_list.append("execution_or_drop_from_temp_like_path")
        weird = hit.get("name_anomaly_reasons") or []
        if weird:
            reasons_list.append("suspicious_filename_entropy_or_shape:" + ",".join(weird[:4]))
        if in_temp and ext in {".exe", ".dll"} and (unsigned or high_ent or weird):
            detections["saved_files"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.53,
                    reason="Binary under a temp or package cache path with at least one additional risk signal (unsigned, high entropy, or odd filename).",
                    artifact_source="Saved Files",
                    file_path=p,
                    sha256=sha256,
                    signature_status=sig,
                    entropy_score=ent,
                    yara_matches=ymatches,
                    timestamps={"modified_utc": str(hit.get("modified") or "")},
                    correlated_evidence=[{"source": "path_heuristic", "detail": "temp_or_cache_like"}],
                    risk_score=forensic_risk_score(temp_path=True, unsigned=unsigned, high_entropy=bool(high_ent)),
                )
            )
        if unsigned and (in_dl or any(m in p.upper() for m in _BROWSER_PARENT_MARKERS)):
            detections["saved_files"].append(
                forensic_finding(
                    severity="high",
                    confidence=0.58,
                    reason="Unsigned executable under Downloads or browser-related path with suspicious filename signals.",
                    artifact_source="Saved Files / profile scan",
                    file_path=p,
                    sha256=sha256,
                    signature_status=sig,
                    entropy_score=ent,
                    yara_matches=ymatches,
                    timestamps={"modified_utc": str(hit.get("modified") or "")},
                    correlated_evidence=[{"source": "designated_scan", "detail": ",".join(reasons_list)}],
                    risk_score=forensic_risk_score(unsigned=True, high_entropy=high_ent, temp_path=in_temp),
                )
            )
        if in_dl and ext in {".exe", ".dll"} and Path(p).name.lower() in bam_name_set:
            detections["saved_files"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.56,
                    reason="Downloads-resident executable whose basename matches a BAM execution record (probable download-to-execution chain).",
                    artifact_source="Saved Files + BAM",
                    file_path=p,
                    sha256=sha256,
                    signature_status=sig,
                    entropy_score=ent,
                    yara_matches=ymatches,
                    timestamps={"modified_utc": str(hit.get("modified") or "")},
                    correlated_evidence=[{"source": "bam", "detail": Path(p).name.lower()}],
                    risk_score=forensic_risk_score(temp_path=False, unsigned=unsigned, high_entropy=high_ent),
                )
            )
        if in_dl and ext in {".exe", ".dll"} and weird and any(
            x in weird for x in ("hex_like_name", "mixed_case_alnum_blob", "guid_like_segment", "chaotic_mixed_case")
        ):
            detections["saved_files"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.51,
                    reason="Renamed or high-entropy style filename under Downloads (possible rename-after-fetch).",
                    artifact_source="Saved Files",
                    file_path=p,
                    sha256=sha256,
                    signature_status=sig,
                    entropy_score=ent,
                    yara_matches=ymatches,
                    timestamps={"modified_utc": str(hit.get("modified") or "")},
                    correlated_evidence=[{"source": "name_heuristic", "detail": ",".join(weird[:6])}],
                    risk_score=forensic_risk_score(rename_hint=True, high_entropy=bool(high_ent)),
                )
            )
        if ext in {".exe", ".dll"} and p:
            deleted_name_match = any(
                Path(str(r.get("path", ""))).name.lower() == Path(p).name.lower()
                for r in usn_records
                if "DELETE" in ",".join(r.get("reasons") or [])
            )
            if deleted_name_match and Path(p).is_file():
                detections["saved_files"].append(
                    forensic_finding(
                        severity="medium",
                        confidence=0.49,
                        reason="File still exists on disk but USN sample shows delete event for same filename (possible rename-away or volume shadowing; verify with full journal).",
                        artifact_source="Saved Files + USN",
                        file_path=p,
                        sha256=sha256,
                        signature_status=sig,
                        entropy_score=ent,
                        yara_matches=ymatches,
                        timestamps={"modified_utc": str(hit.get("modified") or "")},
                        correlated_evidence=[{"source": "usn", "detail": "delete_name_collision"}],
                        risk_score=32,
                    )
                )

        if ext in _ARCHIVE_EXT and in_dl:
            detections["saved_files"].append(
                forensic_finding(
                    severity="low",
                    confidence=0.4,
                    reason="Archive in Downloads; correlate with subsequent temp execution in USN/Prefetch.",
                    artifact_source="Saved Files / profile scan",
                    file_path=p,
                    timestamps={"modified_utc": str(hit.get("modified") or "")},
                    risk_score=15,
                )
            )

    prefetch_items = prefetch.get("items") or []
    pf_stems = {prefetch_extract_stem(str(x.get("name", ""))) for x in prefetch_items}

    for it in bam_items[:220]:
        norm = str(it.get("normalized_path") or "")
        if not norm:
            continue
        stem = Path(norm).stem.upper()
        unsigned = False
        sig = "not_checked"
        sha256, ent = ("", None)
        ymatches = []
        if re.search(r"\.(exe|dll)\Z", norm, re.I) and re.match(r"^[A-Za-z]:\\", norm):
            analysis = exec_forensic_lookup(exec_cache, norm)
            sha256 = str(analysis["sha256"])
            ent = analysis["ent"]
            sig = str(analysis["sig"])
            ymatches = list(analysis["ymatches"] or [])
            unsigned = sig.upper() in {"NOTSIGNED", "NOT_SIGNED"} or "NOTSIGNED" in sig.upper()
        in_temp = forensic_is_temp_path(norm)
        high_ent = ent is not None and ent >= 7.5
        exists = bool(it.get("file_exists"))
        stem_pf = any(Path(s).stem.upper() == stem for s in pf_stems)
        if unsigned and (in_temp or high_ent):
            detections["bam"].append(
                forensic_finding(
                    severity="high" if in_temp and unsigned else "medium",
                    confidence=0.63 if in_temp else 0.52,
                    reason="BAM execution of unsigned binary" + (" from temp-like path" if in_temp else "") + (" with high byte entropy" if high_ent else ""),
                    artifact_source="BAM",
                    file_path=norm,
                    sha256=sha256,
                    signature_status=sig,
                    entropy_score=ent,
                    yara_matches=ymatches,
                    timestamps={"last_execution_utc": str(it.get("last_execution_utc") or "")},
                    correlated_evidence=[{"source": "bam", "detail": "prefetch_hit" if stem_pf else "no_prefetch_stem_match"}],
                    risk_score=forensic_risk_score(unsigned=True, temp_path=in_temp, high_entropy=bool(high_ent), packed_hint=high_ent),
                )
            )
        if not exists and re.search(r"\.(exe|dll)\Z", norm, re.I):
            detections["deleted_bam"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.57,
                    reason="BAM references an executable path that no longer exists on disk (possible delete-after-run).",
                    artifact_source="BAM + filesystem",
                    file_path=norm,
                    sha256=sha256,
                    signature_status=sig,
                    entropy_score=ent,
                    yara_matches=ymatches,
                    timestamps={"last_execution_utc": str(it.get("last_execution_utc") or "")},
                    correlated_evidence=[{"source": "prefetch", "detail": "stem_match" if stem_pf else "no_stem_match"}],
                    risk_score=forensic_risk_score(deleted_hint=True, unsigned=unsigned, temp_path=in_temp),
                )
            )
        drive_letter = norm[0].upper() if re.match(r"^[A-Za-z]:\\", norm) else ""
        if drive_letter and drive_letter in removable:
            detections["deleted_bam"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.54,
                    reason="BAM execution path resides on a currently mounted removable drive (letter).",
                    artifact_source="BAM + Win32_LogicalDisk",
                    file_path=norm,
                    signature_status=sig,
                    correlated_evidence=[{"source": "wmi", "detail": f"DriveType=2 letter={drive_letter}"}],
                    risk_score=30,
                )
            )

    missing_bam_stems = {
        Path(str(x.get("normalized_path", ""))).stem.upper()
        for x in bam_items
        if not x.get("file_exists") and re.search(r"\.(exe|dll)\Z", str(x.get("normalized_path", "")), re.I)
    }

    for row in prefetch_items[:120]:
        name = str(row.get("name") or "")
        stem = prefetch_extract_stem(name)
        if any(tool in stem for tool in _PREFETCH_TOOL_STEMS):
            detections["prefetch"].append(
                forensic_finding(
                    severity="high",
                    confidence=0.72,
                    reason="Prefetch artifact for a known memory/tooling/injector-class binary stem.",
                    artifact_source="Prefetch",
                    file_path=str(Path(prefetch.get("folder", "")) / name) if prefetch.get("folder") else name,
                    timestamps={"prefetch_modified_utc": str(row.get("modified") or "")},
                    correlated_evidence=[{"source": "prefetch", "detail": stem}],
                    risk_score=68,
                )
            )
        norm_name = name.upper()
        if "\\TEMP\\" in norm_name or "TMP" in stem:
            detections["prefetch"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.44,
                    reason="Prefetch filename suggests temp-oriented execution (heuristic on token).",
                    artifact_source="Prefetch",
                    file_path=str(Path(prefetch.get("folder", "")) / name) if prefetch.get("folder") else name,
                    timestamps={"prefetch_modified_utc": str(row.get("modified") or "")},
                    risk_score=28,
                )
            )
        base = Path(stem).stem.upper() if stem else ""
        if base and base in missing_bam_stems:
            detections["prefetch"].append(
                forensic_finding(
                    severity="high",
                    confidence=0.58,
                    reason="Prefetch artifact for a binary stem that also appears as a missing on-disk BAM target (deleted executable with prefetch residue).",
                    artifact_source="Prefetch + BAM",
                    file_path=str(Path(prefetch.get("folder", "")) / name) if prefetch.get("folder") else name,
                    timestamps={"prefetch_modified_utc": str(row.get("modified") or "")},
                    correlated_evidence=[{"source": "bam", "detail": f"deleted_stem_match:{base}"}],
                    risk_score=55,
                )
            )

    for it in pca.get("items", [])[:200]:
        norm = str(it.get("normalized_path") or "")
        if not norm:
            continue
        exists = bool(it.get("file_exists"))
        sig = "not_checked"
        sha256, ent = ("", None)
        if re.search(r"\.(exe|dll)\Z", norm, re.I) and re.match(r"^[A-Za-z]:\\", norm):
            analysis = exec_forensic_lookup(exec_cache, norm)
            sha256 = str(analysis["sha256"])
            ent = analysis["ent"]
            sig = str(analysis["sig"])
        unsigned = sig.upper() in {"NOTSIGNED", "NOT_SIGNED"} or "NOTSIGNED" in sig.upper()
        if not exists and norm.lower().endswith((".exe", ".dll")):
            detections["pca"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.5,
                    reason="PCA compatibility store lists an executable that is missing on disk (possible cleanup).",
                    artifact_source="PCA Store",
                    file_path=norm,
                    sha256=sha256,
                    signature_status=sig,
                    entropy_score=ent,
                    timestamps={
                        "display_at": str(it.get("display_at") or ""),
                        "timestamp_source": str(it.get("timestamp_source") or ""),
                        "correlated": it.get("correlated_timestamps") or {},
                    },
                    correlated_evidence=[{"source": "bam", "detail": "compare_timestamps_offline"}],
                    risk_score=forensic_risk_score(deleted_hint=True),
                )
            )
        if unsigned and norm.lower().endswith(".exe"):
            detections["pca"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.48,
                    reason="Unsigned portable executable referenced from PCA store.",
                    artifact_source="PCA Store",
                    file_path=norm,
                    sha256=sha256,
                    signature_status=sig,
                    entropy_score=ent,
                    risk_score=forensic_risk_score(unsigned=True),
                )
            )
        drv = norm[0].upper() if re.match(r"^[A-Za-z]:\\", norm) else ""
        if drv and drv in removable:
            detections["pca"].append(
                forensic_finding(
                    severity="medium",
                    confidence=0.52,
                    reason="PCA record path uses a drive letter currently classified as removable (Win32_LogicalDisk DriveType=2).",
                    artifact_source="PCA Store + WMI",
                    file_path=norm,
                    signature_status=sig,
                    correlated_evidence=[{"source": "wmi", "detail": f"removable_letter={drv}"}],
                    risk_score=34,
                )
            )

    for dbf in sqlite_pack.get("findings", [])[:8]:
        for h in dbf.get("keyword_hits", [])[:12]:
            browser_hit = forensic_finding(
                severity="low",
                confidence=0.35,
                reason=f"Browser history keyword hit ({h.get('group')} / {h.get('term')}).",
                artifact_source="SQLite Web Data/History",
                file_path=str(dbf.get("database", "")),
                timestamps={"last_visit_time": str(h.get("last_visit_time"))},
                correlated_evidence=[{"source": "url", "detail": h.get("url", "")[:400]}],
                risk_score=12,
            )
            browser_hit["browser_only"] = True
            detections["sqlite"].append(browser_hit)
        for th in dbf.get("temp_path_url_hits", [])[:8]:
            temp_hit = forensic_finding(
                severity="low",
                confidence=0.35,
                reason="Browser history references a temp-style URL path (possible download/execution staging).",
                artifact_source="SQLite History",
                file_path=str(dbf.get("database", "")),
                timestamps={"last_visit_time": str(th.get("last_visit_time"))},
                correlated_evidence=[{"source": "url", "detail": th.get("url", "")[:400]}],
                risk_score=10,
            )
            temp_hit["browser_only"] = True
            detections["sqlite"].append(temp_hit)
        if dbf.get("wal_present"):
            detections["sqlite"].append(
                forensic_finding(
                    severity="low",
                    confidence=0.42,
                    reason="SQLite WAL present; examiner may recover additional rows offline.",
                    artifact_source=str(dbf.get("database", "")),
                    file_path=str(dbf.get("database", "")),
                    correlated_evidence=[{"source": "pragma", "detail": f"freelist_count={dbf.get('freelist_count')}"}],
                    risk_score=12,
                )
            )

    for cat in detections.values():
        flat.extend(cat)

    engine = UnifiedCorrelationEngine()
    correlation = engine.build(
        designated=designated,
        prefetch=prefetch,
        deletion=deletion,
        bam=bam_struct,
        pca=pca,
        sqlite_pack=sqlite_pack,
        usn_records=usn_records,
        detections_flat=flat,
    )

    detections["global"].append(
        forensic_finding(
            severity="low",
            confidence=0.9,
            reason="Unified forensic pass completed; review correlated execution chains and timeline.",
            artifact_source="UnifiedCorrelationEngine",
            correlated_evidence=[{"source": "summary", "detail": json.dumps(correlation.get("cross_artifact_summary"), default=str)[:1200]}],
            risk_score=0,
        )
    )

    return {
        "engine_version": _FORENSIC_ENGINE_VERSION,
        "usn_file_lifecycle_rows": usn_records[:2000],
        "detections": detections,
        "detections_flat": flat[:500],
        "unified_correlation": correlation,
    }


def build_forensic_analysis_bundle(
    designated: dict[str, object],
    prefetch: dict[str, object],
    deletion: dict[str, object],
    trash: dict[str, object] | None = None,
) -> dict[str, object]:
    if platform.system() != "Windows":
        return {
            "available": False,
            "reason": "Forensic correlation bundle is Windows-focused in this build",
            "engine_version": _FORENSIC_ENGINE_VERSION,
        }
    with ThreadPoolExecutor(max_workers=min(10, SCAN_WORKERS)) as pool:
        bam_future = pool.submit(bam_execution_records)
        pca_future = pool.submit(pca_executed_records)
        sqlite_future = pool.submit(sqlite_forensic_probe)
        usn_future = pool.submit(usn_journal_enriched_sample)
        bam_struct = bam_future.result()
        pca = pca_future.result()
        sqlite_pack = sqlite_future.result()
        usn_extra = usn_future.result()
    usn_lines = list(usn_extra.get("lines") or []) + list(usn_extra.get("delete_lines") or [])
    usn_text = str(deletion.get("usn_delete_sample") or "")
    if usn_text:
        usn_lines.extend(usn_text.splitlines()[:USN_DELETE_MAX_LINES])
    usn_records = usn_parse_records(usn_lines)
    enrich_pca_executed_records(
        pca,
        bam=bam_struct,
        prefetch=prefetch,
        usn_records=usn_records,
        trash=trash,
        designated=designated,
    )
    bundle = assemble_forensic_detections(
        designated=designated,
        prefetch=prefetch,
        deletion=deletion,
        bam_struct=bam_struct,
        pca=pca,
        sqlite_pack=sqlite_pack,
        usn_extra=usn_extra,
    )
    bundle["bam_structured"] = bam_struct
    bundle["pca_executed"] = pca
    bundle["sqlite"] = sqlite_pack
    bundle["usn_enriched_sample"] = {"line_count": len(usn_extra.get("lines") or []), "source": usn_extra.get("source")}
    bundle["available"] = True
    return bundle


def _activity_recency_bucket(timestamp: str | None, report_end: str | None) -> str:
    return _executor_activity_recency_bucket(timestamp, report_end)


def _append_activity_event(
    events: list[dict],
    *,
    category: str,
    kind: str,
    label: str,
    path: str,
    occurred_at: str | None,
    timestamp_source: str | None,
    detail: str,
    generated_at: str,
    scan_started_at: str | None = None,
    extra: dict | None = None,
) -> None:
    resolved_source = timestamp_source or ("recorded" if occurred_at else None)
    display_at = sanitize_activity_timestamp(occurred_at, resolved_source, scan_started_at, generated_at)
    if not display_at:
        resolved_source = None
    payload = {
        "category": category,
        "kind": kind,
        "label": label,
        "path": path,
        "occurred_at": display_at,
        "timestamp_source": resolved_source if display_at else None,
        "recency": _activity_recency_bucket(display_at, generated_at),
        "detail": detail,
    }
    if extra:
        payload.update(extra)
    events.append(payload)


def _extract_structured_deletion_events(deletion: dict) -> list[dict]:
    rows: list[dict] = []
    evidence = deletion.get("deleted_file_evidence")
    if not isinstance(evidence, dict):
        return rows
    for source_key, kind in (
        ("security_object_deletion_events", "security_audit_delete"),
        ("sysmon_file_delete_events", "sysmon_file_delete"),
    ):
        for item in evidence.get(source_key) or []:
            if not isinstance(item, dict):
                continue
            occurred_at = normalize_event_time(item.get("TimeCreated"))
            message = str(item.get("Message") or "")[:240]
            rows.append(
                {
                    "kind": kind,
                    "label": f"Event {item.get('Id', '?')}",
                    "path": message.split("\n", 1)[0][:320] if message else kind,
                    "occurred_at": occurred_at,
                    "timestamp_source": "event_log" if occurred_at else None,
                    "detail": message or "Windows event log deletion signal.",
                }
            )
    return rows


def build_user_activity_timeline(
    *,
    generated_at: str,
    scan_started_at: str | None = None,
    trash: dict,
    bam: dict,
    userassist: dict,
    prefetch: dict,
    prefetch_health: dict,
    recent_items: dict,
    designated: dict,
    executor_indicators: dict,
    persistence: dict,
    deletion: dict,
    command_history: dict,
    roblox: dict,
    forensic_bundle: dict,
    sha_blocklist: dict,
    browser_download_history: dict | None = None,
) -> dict:
    events: list[dict] = []

    for item in (browser_download_history or {}).get("items") or []:
        fname = str(item.get("file_name") or _download_basename(str(item.get("target_path") or "")))
        browser = str(item.get("browser") or "Browser")
        labels = list(item.get("matched_labels") or [])
        _append_activity_event(
            events,
            category="browser",
            kind="browser_download",
            label=", ".join(labels) if labels else f"{browser} download",
            path=str(item.get("target_path") or item.get("url") or ""),
            occurred_at=item.get("started_at") or item.get("ended_at"),
            timestamp_source="browser_download_start" if item.get("started_at") else "browser_download_end",
            detail=f"Downloaded via {browser} ({item.get('state', 'unknown')}).",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
            extra={"url": item.get("url"), "browser": browser, "suspicious": item.get("suspicious")},
        )

    for item in trash.get("items") or []:
        path = str(item.get("original_path") or item.get("name") or "")
        is_delete = bool(item.get("original_path") or str(item.get("name", "")).startswith("$I"))
        _append_activity_event(
            events,
            category="deletions",
            kind="recycle_bin" if is_delete else "recycle_bin_artifact",
            label="Deleted to Recycle Bin" if is_delete else "Recycle Bin item",
            path=path or str(item.get("location") or ""),
            occurred_at=item.get("display_at") or item.get("deleted_at") or item.get("modified"),
            timestamp_source=item.get("timestamp_source"),
            detail=(
                f"Original size {item.get('original_size_bytes', '?')} bytes."
                if is_delete
                else "Recycle Bin metadata without $I original path."
            ),
            generated_at=generated_at,
            scan_started_at=scan_started_at,
            extra={"deleted_at_raw": item.get("deleted_at")},
        )

    for item in designated.get("hits") or []:
        if not item.get("removed_artifact"):
            continue
        path = str(item.get("path") or "")
        labels = list(item.get("executor_name_hits") or [])
        cheat_labels = list(item.get("cheat_filename_hints") or [])
        label_text = ", ".join(labels + [f"cheat:{c}" for c in cheat_labels[:3]])
        _append_activity_event(
            events,
            category="deletions",
            kind="removed_executor_artifact",
            label=label_text if label_text else "Removed suspicious artifact",
            path=path,
            occurred_at=item.get("display_at") or item.get("modified"),
            timestamp_source=item.get("timestamp_source") or item.get("artifact_source"),
            detail=str(
                item.get("note")
                or "Evidence recovered from system traces after the file or folder was deleted."
            ),
            generated_at=generated_at,
            scan_started_at=scan_started_at,
            extra={"file_exists": False, "artifact_source": item.get("artifact_source")},
        )

    for row in _extract_structured_deletion_events(deletion):
        _append_activity_event(
            events,
            category="deletions",
            kind=row["kind"],
            label=row["label"],
            path=row["path"],
            occurred_at=row["occurred_at"],
            timestamp_source=row["timestamp_source"],
            detail=row["detail"],
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    usn_rows = (forensic_bundle.get("usn_file_lifecycle_rows") or []) if isinstance(forensic_bundle, dict) else []
    usn_delete_rows: list[dict] = []
    usn_other_rows: list[dict] = []
    for row in usn_rows:
        if not isinstance(row, dict):
            continue
        reasons = row.get("reasons") or []
        if not reasons:
            continue
        path = str(row.get("path") or "")
        is_delete = any("DELETE" in str(r) for r in reasons)
        if is_delete and (path_is_suspicious_profile(path) or executor_labels_for_artifact_text(path)):
            usn_delete_rows.append(row)
        else:
            usn_other_rows.append(row)
    for row in usn_delete_rows + usn_other_rows[:160]:
        reasons = row.get("reasons") or []
        category = "deletions" if any("DELETE" in str(r) for r in reasons) else "filesystem"
        _append_activity_event(
            events,
            category=category,
            kind="usn_journal",
            label=", ".join(str(r) for r in reasons[:4]),
            path=str(row.get("path") or ""),
            occurred_at=row.get("display_at") or row.get("timestamp_utc"),
            timestamp_source=row.get("timestamp_source"),
            detail="NTFS USN journal change record.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    for item in bam.get("items") or []:
        path = str(item.get("normalized_path") or item.get("registry_path_value") or "")
        if not path or item.get("path_allowlisted") or bam_path_is_benign_system(path):
            continue
        labels = list(item.get("executor_name_hits") or [])
        if not labels and not item.get("cheat_filename_hints"):
            continue
        _append_activity_event(
            events,
            category="execution",
            kind="bam_execution",
            label=", ".join(labels) if labels else "Program executed",
            path=path,
            occurred_at=item.get("last_execution_utc"),
            timestamp_source="bam_registry",
            detail="Background Activity Moderator last execution timestamp.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
            extra={"file_exists": item.get("file_exists")},
        )

    for item in userassist.get("items") or []:
        path = str(item.get("path") or "")
        if not path:
            continue
        _append_activity_event(
            events,
            category="execution",
            kind="userassist",
            label=", ".join(item.get("matched_keywords") or []) or "GUI launch",
            path=path,
            occurred_at=item.get("display_at") or item.get("last_run_utc"),
            timestamp_source=item.get("timestamp_source") or "userassist",
            detail="Explorer UserAssist records a GUI program run.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    pca_items = (forensic_bundle.get("pca_executed") or {}).get("items") or []
    for item in pca_items[:120]:
        path = str(item.get("normalized_path") or item.get("raw") or "")
        if not path:
            continue
        _append_activity_event(
            events,
            category="execution",
            kind="pca_compat",
            label="Compatibility Assistant",
            path=path,
            occurred_at=(
                item.get("display_at")
                or item.get("last_execution_utc")
                or item.get("prefetch_modified_utc")
                or item.get("usn_timestamp_utc")
                or item.get("recycle_deleted_at")
                or item.get("file_modified_utc")
            ),
            timestamp_source=item.get("timestamp_source"),
            detail="PCA store references this executable path.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
            extra={
                "file_exists": item.get("file_exists"),
                "correlated_timestamps": item.get("correlated_timestamps"),
            },
        )

    for item in prefetch.get("items") or []:
        name = str(item.get("name") or "")
        if not name:
            continue
        folder = str(prefetch.get("folder") or "")
        path = f"{folder}\\{name}" if folder else name
        _append_activity_event(
            events,
            category="execution",
            kind="prefetch",
            label="Prefetch trace",
            path=path,
            occurred_at=item.get("modified"),
            timestamp_source="prefetch_mtime",
            detail="Windows Prefetch records that this executable ran.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    for item in prefetch_health.get("indicator_hits") or []:
        _append_activity_event(
            events,
            category="execution",
            kind="prefetch_indicator",
            label=str(item.get("name") or "matched prefetch"),
            path=str(item.get("name") or ""),
            occurred_at=item.get("modified"),
            timestamp_source="prefetch_mtime",
            detail="Prefetch file matched an executor indicator name.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    for item in recent_items.get("items") or []:
        folder = str(item.get("folder") or "")
        name = str(item.get("name") or "")
        labels = list(item.get("matched_indicator_names") or []) + list(item.get("matched_cheat_filename_hints") or [])
        if not labels:
            continue
        _append_activity_event(
            events,
            category="files",
            kind="recent_download",
            label=", ".join(labels),
            path=f"{folder}\\{name}" if folder else name,
            occurred_at=item.get("modified"),
            timestamp_source="file_mtime",
            detail="Recent file in Downloads/Desktop matched scan keywords.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    for item in designated.get("hits") or []:
        if item.get("path_allowlisted"):
            continue
        labels = list(item.get("executor_name_hits") or []) + list(item.get("cheat_filename_hints") or [])
        if not labels:
            continue
        _append_activity_event(
            events,
            category="files",
            kind="profile_folder",
            label=", ".join(labels),
            path=str(item.get("path") or ""),
            occurred_at=item.get("modified"),
            timestamp_source="file_mtime",
            detail="User profile folder file matched executor or cheat filename rules.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    for item in executor_indicators.get("file_hits") or []:
        if item.get("path_allowlisted"):
            continue
        labels = list(item.get("matched_names") or []) + list(item.get("cheat_filename_hints") or [])
        if not labels:
            continue
        _append_activity_event(
            events,
            category="files",
            kind="filesystem_scan",
            label=", ".join(labels),
            path=str(item.get("path") or ""),
            occurred_at=item.get("modified"),
            timestamp_source="file_mtime",
            detail="Deep filesystem scan matched executor or cheat filename rules.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    for item in sha_blocklist.get("hits") or []:
        _append_activity_event(
            events,
            category="files",
            kind="sha256_blocklist",
            label=str(item.get("label") or "known hash"),
            path=str(item.get("path") or ""),
            occurred_at=item.get("modified"),
            timestamp_source="file_mtime",
            detail="File hash matches a known executor blocklist entry.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    for item in persistence.get("suspicious_entries") or []:
        if item.get("path_allowlisted"):
            continue
        labels = list(item.get("executor_name_hits") or []) + list(item.get("cheat_filename_hints") or [])
        if not labels:
            continue
        target = str(item.get("target") or item.get("name") or "")
        occurred_at = None
        timestamp_source = None
        if target.lower().endswith(".lnk"):
            try:
                occurred_at = datetime.fromtimestamp(Path(target).stat().st_mtime, timezone.utc).isoformat()
                timestamp_source = "shortcut_mtime"
            except OSError:
                pass
        _append_activity_event(
            events,
            category="persistence",
            kind="persistence",
            label=", ".join(labels),
            path=target,
            occurred_at=occurred_at,
            timestamp_source=timestamp_source,
            detail=f"Persistence via {item.get('source', 'unknown')}.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    for hit in command_history.get("hits") or []:
        occurred = normalize_event_time(hit.get("occurred_at") or hit.get("history_file_modified_utc"))
        _append_activity_event(
            events,
            category="commands",
            kind="shell_history",
            label=", ".join(hit.get("matched") or []) or "keyword",
            path=str(hit.get("path") or ""),
            occurred_at=occurred,
            timestamp_source=hit.get("timestamp_source") or ("powershell_history_file_mtime" if occurred else None),
            detail=str(hit.get("line") or "")[:320],
            generated_at=generated_at,
            scan_started_at=scan_started_at,
            extra={"lines_from_end": hit.get("lines_from_end"), "timeline_note": hit.get("timeline_note")},
        )

    for log in roblox.get("logs") or []:
        _append_activity_event(
            events,
            category="roblox",
            kind="roblox_log",
            label=str(log.get("name") or "Roblox log"),
            path=str(log.get("path") or log.get("name") or ""),
            occurred_at=log.get("modified"),
            timestamp_source="file_mtime",
            detail="Roblox client log file activity.",
            generated_at=generated_at,
            scan_started_at=scan_started_at,
        )

    sqlite_pack = forensic_bundle.get("sqlite") if isinstance(forensic_bundle, dict) else {}
    for db in (sqlite_pack or {}).get("findings") or []:
        for hit in (db.get("keyword_hits") or [])[:20]:
            visit = chrome_webkit_time_to_iso(hit.get("last_visit_time"))
            _append_activity_event(
                events,
                category="browser",
                kind="browser_history",
                label=str(hit.get("term") or hit.get("group") or "visit"),
                path=str(hit.get("url") or db.get("database") or ""),
                occurred_at=visit,
                timestamp_source="browser_last_visit" if visit else None,
                detail=str(hit.get("title") or "Browser history keyword hit."),
                generated_at=generated_at,
                scan_started_at=scan_started_at,
            )

    def _sort_key(row: dict) -> tuple[int, float]:
        recency_rank = {
            "last_24h": 0,
            "last_72h": 1,
            "last_7d": 2,
            "older": 3,
            "unknown": 4,
        }.get(str(row.get("recency") or ""), 5)
        occurred = row.get("occurred_at")
        if not occurred:
            return recency_rank, 0.0
        try:
            ts = datetime.fromisoformat(str(occurred).replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = 0.0
        return recency_rank, -ts

    events.sort(key=_sort_key)

    with_ts = [e for e in events if e.get("occurred_at")]
    without_ts = [e for e in events if not e.get("occurred_at")]
    by_category: dict[str, int] = defaultdict(int)
    by_recency: dict[str, int] = defaultdict(int)
    for event in events:
        by_category[str(event.get("category") or "other")] += 1
        by_recency[str(event.get("recency") or "unknown")] += 1

    recent_deletions = [
        e
        for e in events
        if e.get("category") == "deletions" and e.get("recency") in ("last_24h", "last_72h", "last_7d")
    ]
    recent_executions = [
        e
        for e in events
        if e.get("category") == "execution" and e.get("recency") in ("last_24h", "last_72h")
    ]
    insights: list[str] = []
    if without_ts:
        insights.append(
            f"{len(without_ts)} event(s) lack a direct timestamp — often shell history or persistence entries where only the artifact text is available."
        )
    if recent_deletions:
        insights.append(
            f"{len(recent_deletions)} deletion-related event(s) occurred within the last 7 days — review Recycle Bin, USN, and Security/Sysmon rows first."
        )
    if recent_executions:
        insights.append(
            f"{len(recent_executions)} execution trace(s) in the last 72 hours via BAM, Prefetch, UserAssist, or PCA."
        )
    if not events:
        insights.append("No user-activity artifacts were collected on this host or scan build.")
    elif not with_ts:
        insights.append("No events carried a usable timestamp — re-run with the latest scanner on Windows as Administrator.")

    return {
        "available": True,
        "generated_at": generated_at,
        "event_count": len(events),
        "timestamped_event_count": len(with_ts),
        "missing_timestamp_count": len(without_ts),
        "recent_deletion_count": len(recent_deletions),
        "recent_execution_count": len(recent_executions),
        "by_category": dict(sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_recency": dict(sorted(by_recency.items(), key=lambda kv: kv[0])),
        "insights": insights,
        "events": events[:250],
        "note": "Unified, timestamp-first activity feed for reviewer triage. Times are UTC in the raw report; dashboard shows GMT+3.",
    }


def _executor_activity_recency_bucket(timestamp: str | None, report_end: str | None) -> str:
    event_ms = None
    end_ms = None
    if timestamp:
        try:
            event_ms = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() * 1000
        except ValueError:
            event_ms = None
    if report_end:
        try:
            end_ms = datetime.fromisoformat(report_end.replace("Z", "+00:00")).timestamp() * 1000
        except ValueError:
            end_ms = None
    if event_ms is None or end_ms is None:
        return "unknown"
    hours = (end_ms - event_ms) / 3_600_000
    if hours <= 24:
        return "last_24h"
    if hours <= EXECUTOR_ACTIVITY_RECENT_HOURS:
        return "last_72h"
    if hours <= 168:
        return "last_7d"
    return "older"


def build_executor_activity_summary(
    *,
    generated_at: str,
    recent_items: dict,
    sha_blocklist: dict,
    prefetch_health: dict,
    designated: dict,
    executor_indicators: dict,
    bam: dict,
    persistence: dict,
) -> dict:
    events: list[dict] = []
    patterns = executor_name_patterns()

    def append_event(
        *,
        kind: str,
        label: str,
        path: str,
        occurred_at: str | None,
        detail: str,
        extra: dict | None = None,
    ) -> None:
        payload = {
            "kind": kind,
            "label": label,
            "path": path,
            "occurred_at": occurred_at,
            "recency": _executor_activity_recency_bucket(occurred_at, generated_at),
            "detail": detail,
        }
        if extra:
            payload.update(extra)
        events.append(payload)

    for item in sha_blocklist.get("hits") or []:
        path = str(item.get("path") or "")
        append_event(
            kind="sha256_blocklist",
            label=str(item.get("label") or "known_executor"),
            path=path,
            occurred_at=item.get("modified"),
            detail="Known executor binary hash (survives rename / disguised folder).",
            extra={
                "sha256": item.get("sha256"),
                "renamed_disguise": item.get("renamed_disguise"),
                "detection_source": item.get("detection_source"),
            },
        )

    for item in (recent_items.get("items") or [])[:80]:
        names = list(item.get("matched_indicator_names") or [])
        cheats = list(item.get("matched_cheat_filename_hints") or [])
        if not names and not cheats:
            continue
        label = ", ".join(names) if names else ", ".join(cheats)
        folder = str(item.get("folder") or "")
        path = f"{folder}\\{item.get('name')}" if folder and item.get("name") else str(item.get("name") or folder)
        append_event(
            kind="recent_file",
            label=label,
            path=path,
            occurred_at=item.get("modified"),
            detail="Recent Downloads/Desktop file name matched a checked executor or cheat hint.",
        )

    for item in (prefetch_health.get("indicator_hits") or [])[:40]:
        matched = [name for name, pattern in patterns.items() if pattern.search(str(item.get("name") or ""))]
        if not matched:
            continue
        append_event(
            kind="prefetch_execution",
            label=", ".join(matched),
            path=str(item.get("name") or ""),
            occurred_at=item.get("modified"),
            detail="Windows Prefetch shows this executable ran recently.",
        )

    for item in (designated.get("hits") or [])[:60]:
        if item.get("path_allowlisted"):
            continue
        names = list(item.get("executor_name_hits") or [])
        cheats = list(item.get("cheat_filename_hints") or [])
        if not names and not cheats:
            continue
        label = ", ".join(names) if names else ", ".join(cheats)
        append_event(
            kind="profile_folder",
            label=label,
            path=str(item.get("path") or ""),
            occurred_at=item.get("modified"),
            detail="File in Downloads/Desktop/Documents matched executor or cheat filename rules.",
        )

    for item in (executor_indicators.get("file_hits") or [])[:40]:
        if item.get("path_allowlisted"):
            continue
        names = list(item.get("matched_names") or [])
        cheats = list(item.get("cheat_filename_hints") or [])
        if not names and not cheats:
            continue
        label = ", ".join(names) if names else ", ".join(cheats)
        append_event(
            kind="filesystem_indicator",
            label=label,
            path=str(item.get("path") or ""),
            occurred_at=item.get("modified"),
            detail="Deep scan path matched executor or cheat filename rules.",
        )

    for item in (bam.get("items") or [])[:40]:
        path = str(item.get("normalized_path") or item.get("path") or "")
        if not path:
            continue
        matched = match_executor_labels(path, patterns)
        if not matched:
            continue
        append_event(
            kind="bam_execution",
            label=", ".join(matched),
            path=path,
            occurred_at=item.get("last_execution_utc") or item.get("last_execution"),
            detail="Background Activity Moderator recorded execution of this path.",
        )

    for item in (persistence.get("suspicious_entries") or [])[:25]:
        if item.get("path_allowlisted"):
            continue
        names = list(item.get("executor_name_hits") or [])
        if not names:
            continue
        append_event(
            kind="persistence",
            label=", ".join(names),
            path=str(item.get("target") or item.get("name") or ""),
            occurred_at=None,
            detail="Startup / Run key / scheduled task references a checked executor name.",
        )

    def _event_sort_key(row: dict) -> tuple[int, float]:
        recency_rank = {
            "last_24h": 0,
            "last_72h": 1,
            "last_7d": 2,
            "older": 3,
        }.get(str(row.get("recency") or ""), 4)
        occurred = row.get("occurred_at")
        if not occurred:
            return recency_rank, 0.0
        try:
            ts = datetime.fromisoformat(str(occurred).replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = 0.0
        return recency_rank, -ts

    events.sort(key=_event_sort_key)

    recent_count = sum(1 for row in events if row.get("recency") in ("last_24h", "last_72h"))
    hash_hits = sum(1 for row in events if row.get("kind") == "sha256_blocklist")
    if hash_hits or recent_count >= 2:
        verdict = "likely_recent_executor_activity"
    elif events:
        verdict = "possible_executor_activity"
    else:
        verdict = "no_matched_executor_activity"

    return {
        "available": True,
        "recent_window_hours": EXECUTOR_ACTIVITY_RECENT_HOURS,
        "verdict": verdict,
        "event_count": len(events),
        "recent_event_count": recent_count,
        "hash_hit_count": hash_hits,
        "events": events[:80],
        "note": "Pre-aggregated timeline for reviewers; check SHA256 hits first when the file was renamed or moved.",
    }


STRING_SCAN_EXTENSIONS = frozenset({".txt", ".log", ".json", ".bat", ".ps1", ".cfg", ".xml", ".lua"})
STRING_SCAN_MAX_FILES = 100
STRING_SCAN_MAX_BYTES_PER_FILE = 350_000
STRING_SCAN_CONTEXT_CHARS = 90

SUSPICIOUS_STRING_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("executor_brand", re.compile("|".join(re.escape(n) for n in EXECUTOR_NAMES), re.IGNORECASE)),
    (
        "injection_language",
        re.compile(
            r"inject(?:or|ion)?|dll\s*hook|memory\s*scan|execute\s*script|script\s*ware|external\s*cheat|"
            r"bypass\s*anticheat|setfflag|getrawmetatable|hookfunction|loadstring",
            re.IGNORECASE,
        ),
    ),
    (
        "cleanup_language",
        re.compile(
            r"wevtutil\s+cl|Clear-EventLog|fsutil\s+usn|deletejournal|vssadmin\s+delete|Remove-Item.*Prefetch|"
            r"cipher\s+/w|cleaner|trace\s*wipe|Clear-RecycleBin|\$Recycle\.Bin|rd\s+/s\s+/q|del\s+/[fq]",
            re.IGNORECASE,
        ),
    ),
    ("cheat_terms", re.compile(r"aimbot|wallhack|esp\b|noclip|speedhack|triggerbot|free\s*cheat", re.IGNORECASE)),
]


def _digest_path_key(path: str) -> str:
    return str(path or "").replace("/", "\\").strip().lower()


def _digest_basename(path: str) -> str:
    key = _digest_path_key(path)
    if not key:
        return ""
    parts = [part for part in key.split("\\") if part]
    return parts[-1] if parts else key


def _digest_sort_ts(row: dict) -> float:
    ts = row.get("occurred_at") or row.get("last_seen") or row.get("modified")
    if not ts:
        return 0.0
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _scan_file_for_strings(path: Path) -> list[dict]:
    hits: list[dict] = []
    if path.suffix.lower() not in STRING_SCAN_EXTENSIONS:
        return hits
    try:
        if path.stat().st_size > STRING_SCAN_MAX_BYTES_PER_FILE:
            return hits
    except OSError:
        return hits
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        matched_groups: list[str] = []
        matched_terms: list[str] = []
        for group, pattern in SUSPICIOUS_STRING_PATTERNS:
            found = pattern.findall(line)
            if not found:
                continue
            matched_groups.append(group)
            if isinstance(found[0], tuple):
                matched_terms.extend([str(x) for x in found[:3]])
            else:
                matched_terms.extend([str(x) for x in found[:5]])
        if not matched_groups:
            continue
        snippet = line.strip()
        if len(snippet) > STRING_SCAN_CONTEXT_CHARS * 2:
            snippet = snippet[: STRING_SCAN_CONTEXT_CHARS * 2] + "…"
        hits.append(
            {
                "source": "file_content",
                "file_path": str(path),
                "line_number": line_no,
                "matched_groups": sorted(set(matched_groups)),
                "matched_terms": sorted(set(matched_terms))[:12],
                "snippet": snippet,
            }
        )
        if len(hits) >= 25:
            break
    return hits


def recent_disk_executable_scan() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Recent executable enumeration is Windows-only"}
    script = (
        "$cut=(Get-Date).AddDays(-45);"
        "$roots = Get-CimInstance Win32_LogicalDisk -ErrorAction SilentlyContinue | "
        "Where-Object { $_.DriveType -in 2,3 } | ForEach-Object { $_.DeviceID + '\\' };"
        "$out=@();"
        "foreach($root in $roots){"
        " if(-not(Test-Path -LiteralPath $root)){continue}"
        " Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |"
        " Where-Object { $_.Extension -match '^\\.(exe|dll|bat|ps1|msi|vbs|scr|com)$' -and $_.LastWriteTime -ge $cut } |"
        " Select-Object -First 200 | ForEach-Object {"
        "  $out += [pscustomobject]@{"
        "    Path=$_.FullName;"
        "    Name=$_.Name;"
        "    Modified=$_.LastWriteTimeUtc.ToString('u');"
        "    SizeBytes=$_.Length"
        "  }"
        " }"
        "};"
        "$out | Sort-Object Modified -Descending | Select-Object -First 300 | ConvertTo-Json -Compress"
    )
    raw = run_command(["powershell", "-NoProfile", "-Command", script], timeout=90, max_chars=120000)
    items: list[dict] = []
    patterns = executor_name_patterns()
    try:
        if raw and not raw.startswith("Unavailable:"):
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else [parsed]
            for row in rows:
                if not isinstance(row, dict) or not row.get("Path"):
                    continue
                path = str(row.get("Path"))
                labels = sorted(set(match_executor_labels(path, patterns)))
                binary_labels: list[str] = []
                if not labels and path.lower().endswith((".exe", ".dll")):
                    binary_labels = _probe_executable_binary_labels(Path(path))
                    labels = binary_labels
                items.append(
                    {
                        "path": path,
                        "name": str(row.get("Name") or _digest_basename(path)),
                        "modified": row.get("Modified"),
                        "size_bytes": row.get("SizeBytes"),
                        "source": "full_pc_disk_enumeration",
                        "executor_name_hits": labels,
                        "binary_embedded_labels": binary_labels,
                    }
                )
    except json.JSONDecodeError:
        pass
    executor_items = [item for item in items if item.get("executor_name_hits")]
    return {
        "available": True,
        "count": len(items),
        "executor_match_count": len(executor_items),
        "items": items,
        "executor_items": executor_items,
    }


def build_executable_inventory(
    *,
    generated_at: str,
    bam: dict,
    prefetch: dict,
    prefetch_health: dict,
    designated: dict,
    executor_indicators: dict,
    sha_blocklist: dict,
    disk_executables: dict,
    executor_artifact_evidence: dict | None = None,
) -> dict:
    patterns = executor_name_patterns()
    by_path: dict[str, dict] = {}

    def upsert(
        path: str,
        *,
        source: str,
        occurred_at: str | None = None,
        labels: list[str] | None = None,
        suspicious: bool = False,
        extra: dict | None = None,
    ) -> None:
        if not path:
            return
        path = forensic_normalize_pathish(path) or path
        if artifact_path_is_review_noise(path):
            return
        key = _digest_path_key(path)
        name = _digest_basename(path)
        row = by_path.get(key)
        if not row:
            row = {
                "path": path.replace("/", "\\"),
                "name": name,
                "sources": [],
                "labels": [],
                "suspicious": False,
                "last_seen": None,
                "file_exists": None,
            }
            by_path[key] = row
        if source not in row["sources"]:
            row["sources"].append(source)
        for label in labels or []:
            if label and label not in row["labels"]:
                row["labels"].append(label)
        if suspicious:
            row["suspicious"] = True
        if occurred_at and (not row["last_seen"] or occurred_at > row["last_seen"]):
            row["last_seen"] = occurred_at
        if extra:
            row.update({k: v for k, v in extra.items() if v is not None})
        try:
            row["file_exists"] = Path(path).exists()
        except OSError:
            row["file_exists"] = False

    for item in disk_executables.get("items") or []:
        path = str(item.get("path") or "")
        labels = [
            label
            for label, pat in patterns.items()
            if pat.search(path) or pat.search(str(item.get("name") or ""))
        ]
        labels.extend(cheat_filename_hint_labels(_digest_basename(path)))
        upsert(
            path,
            source="disk_scan",
            occurred_at=item.get("modified"),
            labels=labels,
            suspicious=bool(labels),
            extra={"size_bytes": item.get("size_bytes")},
        )

    for item in bam.get("items") or []:
        path = str(item.get("normalized_path") or item.get("registry_path_value") or "")
        if not path or item.get("path_allowlisted") or bam_path_is_benign_system(path):
            continue
        labels = match_executor_labels(path, patterns)
        labels.extend(cheat_filename_hint_labels(_digest_basename(path)))
        if not labels:
            continue
        upsert(
            path,
            source="execution_history",
            occurred_at=item.get("last_execution_utc"),
            labels=labels,
            suspicious=bool(labels) or item.get("file_exists") is False,
            extra={"file_exists": item.get("file_exists")},
        )

    pf_folder = str(prefetch.get("folder") or "")
    for item in prefetch.get("items") or []:
        name = str(item.get("name") or "")
        path = f"{pf_folder}\\{name}" if pf_folder and name else name
        stem = re.sub(r"-[0-9A-F]{8}\.pf$", "", name, flags=re.IGNORECASE)
        stem = re.sub(r"\.pf$", "", stem, flags=re.IGNORECASE)
        labels = [label for label, pat in patterns.items() if pat.search(stem) or pat.search(name)]
        labels.extend(cheat_filename_hint_labels(stem))
        upsert(
            path,
            source="runtime_cache",
            occurred_at=item.get("modified"),
            labels=labels,
            suspicious=bool(labels),
        )

    for item in (designated.get("hits") or []) + (executor_indicators.get("file_hits") or []):
        path = str(item.get("path") or "")
        if item.get("path_allowlisted"):
            continue
        labels = list(item.get("executor_name_hits") or item.get("matched_names") or [])
        labels.extend(item.get("cheat_filename_hints") or item.get("matched_cheat_filename_hints") or [])
        if not labels:
            continue
        upsert(
            path,
            source="removed_artifact" if item.get("removed_artifact") else "folder_scan",
            occurred_at=item.get("display_at") or item.get("modified"),
            labels=labels,
            suspicious=True,
            extra={"file_exists": item.get("file_exists")},
        )

    for item in (executor_artifact_evidence or {}).get("hits") or []:
        path = str(item.get("path") or "")
        if item.get("path_allowlisted"):
            continue
        labels = list(item.get("executor_name_hits") or [])
        labels.extend(item.get("cheat_filename_hints") or [])
        if not labels:
            continue
        upsert(
            path,
            source=str(item.get("artifact_source") or "executor_artifact"),
            occurred_at=item.get("display_at") or item.get("modified"),
            labels=labels,
            suspicious=True,
            extra={"file_exists": item.get("file_exists")},
        )

    for item in sha_blocklist.get("hits") or []:
        path = str(item.get("path") or "")
        upsert(
            path,
            source="known_hash",
            occurred_at=item.get("modified"),
            labels=[str(item.get("label") or "known_hash")],
            suspicious=True,
            extra={"sha256": item.get("sha256")},
        )

    items = sorted(by_path.values(), key=_digest_sort_ts, reverse=True)
    suspicious_count = sum(1 for row in items if row.get("suspicious"))
    return {
        "available": True,
        "generated_at": generated_at,
        "total_count": len(items),
        "suspicious_count": suspicious_count,
        "items": items[:200],
    }


def build_execution_activity_feed(
    *,
    generated_at: str,
    bam: dict,
    userassist: dict,
    prefetch: dict,
    forensic_bundle: dict,
    executor_activity: dict,
) -> dict:
    rows: list[dict] = []

    def add(*, path: str, occurred_at: str | None, source: str, summary: str, suspicious: bool = False) -> None:
        if not path and not summary:
            return
        rows.append(
            {
                "path": path.replace("/", "\\") if path else "",
                "name": _digest_basename(path),
                "occurred_at": occurred_at,
                "source": source,
                "summary": summary,
                "suspicious": suspicious,
                "recency": _executor_activity_recency_bucket(occurred_at, generated_at),
            }
        )

    patterns = executor_name_patterns()
    for item in bam.get("items") or []:
        path = str(item.get("normalized_path") or "")
        if not path or item.get("path_allowlisted") or bam_path_is_benign_system(path):
            continue
        labels = match_executor_labels(path, patterns)
        if not labels and not item.get("cheat_filename_hints"):
            continue
        suspicious = bool(labels) or item.get("file_exists") is False
        add(
            path=path,
            occurred_at=item.get("last_execution_utc"),
            source="execution_history",
            summary="A program was run on this PC."
            + (" The file is no longer on disk." if item.get("file_exists") is False else ""),
            suspicious=suspicious,
        )

    for item in userassist.get("items") or []:
        path = str(item.get("path") or "")
        if not path:
            continue
        keywords = item.get("matched_keywords") or []
        add(
            path=path,
            occurred_at=item.get("display_at") or item.get("last_run_utc"),
            source="app_launch",
            summary="An app was opened from the desktop or Start menu.",
            suspicious=bool(keywords),
        )

    pf_folder = str(prefetch.get("folder") or "")
    for item in (prefetch.get("items") or [])[:80]:
        name = str(item.get("name") or "")
        path = f"{pf_folder}\\{name}" if pf_folder and name else name
        stem = re.sub(r"-[0-9A-F]{8}\.pf$", "", name, flags=re.IGNORECASE)
        stem = re.sub(r"\.pf$", "", stem, flags=re.IGNORECASE)
        labels = [label for label, pat in patterns.items() if pat.search(stem)]
        add(
            path=path,
            occurred_at=item.get("modified"),
            source="runtime_cache",
            summary="Windows cached evidence that a program ran recently.",
            suspicious=bool(labels),
        )

    pca_items = (forensic_bundle.get("pca_executed") or {}).get("items") or []
    for item in pca_items[:60]:
        path = str(item.get("normalized_path") or item.get("raw") or "")
        if not path:
            continue
        add(
            path=path,
            occurred_at=item.get("display_at") or item.get("last_execution_utc") or item.get("file_modified_utc"),
            source="compatibility_trace",
            summary="Windows recorded compatibility activity for a program.",
            suspicious=item.get("file_exists") is False,
        )

    for event in executor_activity.get("events") or []:
        add(
            path=str(event.get("path") or ""),
            occurred_at=event.get("occurred_at"),
            source="matched_signal",
            summary=str(event.get("detail") or "Matched a reviewed executor or cheat signal."),
            suspicious=True,
        )

    rows.sort(key=_digest_sort_ts, reverse=True)
    with_ts = [r for r in rows if r.get("occurred_at")]
    return {
        "available": True,
        "event_count": len(rows),
        "timestamped_count": len(with_ts),
        "recent_count": sum(1 for r in rows if r.get("recency") in ("last_24h", "last_72h")),
        "suspicious_count": sum(1 for r in rows if r.get("suspicious")),
        "items": rows[:150],
    }


def build_string_detection_hits(
    *,
    command_history: dict,
    roblox: dict,
    designated: dict,
    executor_indicators: dict,
) -> dict:
    hits: list[dict] = []
    seen: set[str] = set()

    def append_hit(row: dict) -> None:
        key = f"{row.get('file_path')}|{row.get('line_number')}|{row.get('snippet')}"
        if key in seen:
            return
        seen.add(key)
        hits.append(row)

    for item in command_history.get("hits") or []:
        append_hit(
            {
                "source": "powershell_history",
                "file_path": item.get("path"),
                "line_number": item.get("line_number_from_tail"),
                "matched_groups": ["command_history"],
                "matched_terms": list(item.get("matched") or []),
                "snippet": str(item.get("line") or "")[:400],
                "occurred_at": item.get("occurred_at") or item.get("history_file_modified_utc"),
            }
        )

    for log in roblox.get("logs") or []:
        tail = str(log.get("tail") or "")
        if not tail:
            continue
        path = str(log.get("path") or log.get("name") or "")
        for line_no, line in enumerate(tail.splitlines()[-120:], start=1):
            matched_groups: list[str] = []
            matched_terms: list[str] = []
            for group, pattern in SUSPICIOUS_STRING_PATTERNS:
                if pattern.search(line):
                    matched_groups.append(group)
                    matched_terms.extend(pattern.findall(line)[:3])
            if not matched_groups:
                continue
            append_hit(
                {
                    "source": "roblox_log",
                    "file_path": path,
                    "line_number": line_no,
                    "matched_groups": sorted(set(matched_groups)),
                    "matched_terms": sorted({str(t) for t in matched_terms})[:10],
                    "snippet": line.strip()[:400],
                    "occurred_at": log.get("modified"),
                }
            )

    scan_paths: list[Path] = []
    for item in (designated.get("hits") or [])[:40]:
        p = Path(str(item.get("path") or ""))
        if p.is_file() and p.suffix.lower() in STRING_SCAN_EXTENSIONS:
            scan_paths.append(p)
    for item in (executor_indicators.get("file_hits") or [])[:30]:
        p = Path(str(item.get("path") or ""))
        if p.is_file() and p.suffix.lower() in STRING_SCAN_EXTENSIONS:
            scan_paths.append(p)

    for path in scan_paths[:STRING_SCAN_MAX_FILES]:
        for row in _scan_file_for_strings(path):
            row["occurred_at"] = None
            try:
                row["occurred_at"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            except OSError:
                pass
            append_hit(row)

    hits.sort(key=lambda r: _digest_sort_ts({"occurred_at": r.get("occurred_at")}), reverse=True)
    return {
        "available": True,
        "hit_count": len(hits),
        "items": hits[:120],
        "note": "Searches logs, scripts, and history for cheat, injection, and cleanup-related words.",
    }


def _deletion_activity_summary(path: str, *, removed_only: bool = False) -> str:
    name = Path(str(path or "")).name or "a file"
    if removed_only:
        return (
            f"{name} is no longer on disk or in the Recycle Bin; "
            "Windows activity traces still record the deletion."
        )
    return f"{name} was deleted or moved to the Recycle Bin."


def _gather_priority_deletion_events(
    *,
    scan_started_at: str | None = None,
    generated_at: str | None = None,
    trash: dict | None = None,
    designated: dict | None = None,
    executor_artifact_evidence: dict | None = None,
    forensic_bundle: dict | None = None,
    deletion: dict | None = None,
    deletion_cleanup_analysis: dict | None = None,
) -> list[dict]:
    events: list[dict] = []
    seen: set[tuple[str, str]] = set()
    cleanup_by_path = {
        _artifact_path_key(str(row.get("path") or "")): row
        for row in (deletion_cleanup_analysis or {}).get("correlations") or []
        if isinstance(row, dict)
    }

    def add(*, occurred_at: str | None, path: str, kind: str, removed_only: bool = False) -> None:
        path = str(path or "").strip()
        ts = sanitize_activity_timestamp(occurred_at, kind, scan_started_at, generated_at)
        if not path or not ts:
            return
        key = (_artifact_path_key(path), ts)
        if key in seen:
            return
        seen.add(key)
        cleanup = cleanup_by_path.get(_artifact_path_key(path)) or {}
        summary = str(cleanup.get("summary") or "") or _deletion_activity_summary(path, removed_only=removed_only)
        payload = {
            "occurred_at": ts,
            "category": "deletions",
            "kind": kind,
            "summary": summary,
            "path": path,
        }
        if cleanup:
            payload.update(
                {
                    "cleanup_at": cleanup.get("cleanup_at"),
                    "cleanup_at_display": cleanup.get("cleanup_at_display"),
                    "cleanup_type": cleanup.get("cleanup_type"),
                    "gap_seconds": cleanup.get("gap_seconds"),
                    "gap_human": cleanup.get("gap_human"),
                    "still_in_recycle_bin": cleanup.get("still_in_recycle_bin"),
                }
            )
        events.append(payload)

    for item in (trash or {}).get("items") or []:
        original = str(item.get("original_path") or "").strip()
        if original:
            add(
                occurred_at=item.get("display_at") or item.get("deleted_at") or item.get("modified"),
                path=original,
                kind="recycle_bin",
            )

    for item in (designated or {}).get("hits") or []:
        if not item.get("removed_artifact"):
            continue
        add(
            occurred_at=item.get("display_at") or item.get("modified"),
            path=str(item.get("path") or ""),
            kind="removed_executor_artifact",
            removed_only=True,
        )

    for hit in (executor_artifact_evidence or {}).get("hits") or []:
        if hit.get("file_exists") is not False:
            continue
        path = str(hit.get("path") or "")
        if not path or hit.get("path_allowlisted") or artifact_path_is_review_noise(path):
            continue
        labels = list(hit.get("executor_name_hits") or [])
        if not labels and not hit.get("cheat_filename_hints"):
            continue
        source = str(hit.get("artifact_source") or "removed_artifact")
        add(
            occurred_at=hit.get("display_at") or hit.get("modified"),
            path=path,
            kind=source,
            removed_only=source != "recycle_bin",
        )

    usn_records = _collect_usn_records_for_removed_artifact_merge(forensic_bundle or {}, deletion or {})
    for row in usn_records:
        reasons = [str(r).upper() for r in (row.get("reasons") or [])]
        if not any("DELETE" in reason or "RENAME_OLD" in reason for reason in reasons):
            continue
        path = str(row.get("path") or "")
        if not path_is_suspicious_profile(path) and not executor_labels_for_artifact_text(path):
            continue
        add(
            occurred_at=row.get("display_at") or row.get("timestamp_utc"),
            path=path,
            kind="usn_delete" if any("DELETE" in reason for reason in reasons) else "usn_rename",
            removed_only=True,
        )

    events.sort(key=_digest_sort_ts, reverse=True)
    return events


def build_last_computer_activity(
    *,
    generated_at: str,
    scan_started_at: str | None = None,
    boot_time: str | None,
    user_activity: dict,
    execution_activity: dict,
    download_history: dict | None = None,
    trash: dict | None = None,
    designated: dict | None = None,
    executor_artifact_evidence: dict | None = None,
    forensic_bundle: dict | None = None,
    deletion: dict | None = None,
    deletion_cleanup_analysis: dict | None = None,
    filesystem_evidence_integrity: dict | None = None,
) -> dict:
    milestones: list[dict] = []
    if boot_time:
        milestones.append(
            {
                "occurred_at": boot_time,
                "label": "PC was turned on",
                "summary": "Last boot time for this machine.",
            }
        )
    milestones.append(
        {
            "occurred_at": generated_at,
            "label": "Scan finished",
            "summary": "This report was collected.",
        }
    )

    category_plain = {
        "execution": "A program was run or launched on this PC.",
        "files": "A file in a watched folder was touched or matched.",
        "persistence": "Something was set to start with Windows.",
        "commands": "A command line matched reviewed words.",
        "roblox": "Roblox log activity was recorded.",
        "browser": "Browser history matched reviewed words.",
        "filesystem": "A filesystem change was logged.",
    }
    priority_deletions = _gather_priority_deletion_events(
        scan_started_at=scan_started_at,
        generated_at=generated_at,
        trash=trash,
        designated=designated,
        executor_artifact_evidence=executor_artifact_evidence,
        forensic_bundle=forensic_bundle,
        deletion=deletion,
        deletion_cleanup_analysis=deletion_cleanup_analysis,
    )
    other_events: list[dict] = []
    for dl in (download_history or {}).get("items") or []:
        started = dl.get("started_at") or dl.get("ended_at")
        if not started:
            continue
        fname = str(dl.get("file_name") or "a file")
        other_events.append(
            {
                "occurred_at": started,
                "category": "browser",
                "summary": f"A file was downloaded in {dl.get('browser', 'a browser')}: {fname}.",
                "path": dl.get("target_path") or dl.get("url"),
            }
        )
    for event in user_activity.get("events") or []:
        if not event.get("occurred_at"):
            continue
        cat = str(event.get("category") or "")
        if cat == "deletions":
            continue
        payload = {
            "occurred_at": event.get("occurred_at"),
            "category": cat,
            "summary": event.get("summary") or category_plain.get(cat) or "Activity was recorded on this PC.",
            "path": event.get("path"),
        }
        for extra_key in (
            "cleanup_at",
            "cleanup_at_display",
            "cleanup_type",
            "gap_seconds",
            "gap_human",
            "still_in_recycle_bin",
            "kind",
        ):
            if event.get(extra_key) is not None:
                payload[extra_key] = event.get(extra_key)
        other_events.append(payload)
    other_events.sort(key=_digest_sort_ts, reverse=True)
    deletion_cap = 80
    other_cap = max(0, 120 - min(len(priority_deletions), deletion_cap))
    events = priority_deletions[:deletion_cap] + other_events[:other_cap]
    events.sort(key=_digest_sort_ts, reverse=True)
    total_event_count = len(priority_deletions) + len(other_events)

    return {
        "available": True,
        "boot_time": boot_time,
        "scan_time": generated_at,
        "milestone_count": len(milestones),
        "milestones": milestones,
        "event_count": total_event_count,
        "deletion_event_count": len(priority_deletions),
        "recent_event_count": user_activity.get("recent_execution_count", 0)
        + user_activity.get("recent_deletion_count", 0),
        "execution_count": execution_activity.get("event_count", 0),
        "events": events[:120],
        "deletion_cleanup_insights": (deletion_cleanup_analysis or {}).get("insights") or [],
        "filesystem_evidence_integrity": filesystem_evidence_integrity or {"available": False},
    }


def build_scan_review_bundle(
    *,
    generated_at: str,
    scan_started_at: str | None = None,
    boot_time: str | None,
    bam: dict,
    prefetch: dict,
    prefetch_health: dict,
    designated: dict,
    executor_indicators: dict,
    sha_blocklist: dict,
    userassist: dict,
    roblox: dict,
    command_history: dict,
    forensic_bundle: dict,
    executor_activity: dict,
    user_activity: dict,
    disk_executables: dict,
    browser_download_history: dict | None = None,
    trash: dict | None = None,
    executor_artifact_evidence: dict | None = None,
    deletion: dict | None = None,
    deletion_cleanup_analysis: dict | None = None,
    filesystem_evidence_integrity: dict | None = None,
) -> dict:
    execution_activity = build_execution_activity_feed(
        generated_at=generated_at,
        bam=bam,
        userassist=userassist,
        prefetch=prefetch,
        forensic_bundle=forensic_bundle,
        executor_activity=executor_activity,
    )
    executable_inventory = build_executable_inventory(
        generated_at=generated_at,
        bam=bam,
        prefetch=prefetch,
        prefetch_health=prefetch_health,
        designated=designated,
        executor_indicators=executor_indicators,
        sha_blocklist=sha_blocklist,
        disk_executables=disk_executables,
        executor_artifact_evidence=executor_artifact_evidence,
    )
    string_detection = build_string_detection_hits(
        command_history=command_history,
        roblox=roblox,
        designated=designated,
        executor_indicators=executor_indicators,
    )
    last_computer_activity = build_last_computer_activity(
        generated_at=generated_at,
        scan_started_at=scan_started_at,
        boot_time=boot_time,
        user_activity=user_activity,
        execution_activity=execution_activity,
        download_history=browser_download_history,
        trash=trash,
        designated=designated,
        executor_artifact_evidence=executor_artifact_evidence,
        forensic_bundle=forensic_bundle,
        deletion=deletion,
        deletion_cleanup_analysis=deletion_cleanup_analysis,
        filesystem_evidence_integrity=filesystem_evidence_integrity,
    )
    return {
        "available": True,
        "last_computer_activity": last_computer_activity,
        "executable_inventory": executable_inventory,
        "string_detection": string_detection,
        "execution_activity": execution_activity,
        "download_history": browser_download_history or {"available": False, "items": []},
    }


def in_scan_binary_change_signals(usn_rows: list[dict], bam_items: list[dict]) -> dict:
    """
    Summarize install/rename/move-related evidence from the current scan only.
    """
    creates: list[dict] = []
    renames: list[dict] = []
    deletes: list[dict] = []
    for row in usn_rows[:500]:
        path = str(row.get("path") or "")
        if not re.search(r"\.(exe|dll|bat|ps1)\Z", path, re.IGNORECASE):
            continue
        reasons = [str(x).upper() for x in (row.get("reasons") or [])]
        if any("FILE_CREATE" in reason for reason in reasons):
            creates.append(row)
        if any("RENAME_" in reason for reason in reasons):
            renames.append(row)
        if any("DELETE" in reason for reason in reasons):
            deletes.append(row)
    bam_exec = [
        str(item.get("normalized_path") or "")
        for item in bam_items[:350]
        if re.search(r"\.(exe|dll)\Z", str(item.get("normalized_path") or ""), re.IGNORECASE)
    ]
    return {
        "available": True,
        "install_like_events": {"count": len(creates)},
        "rename_or_move_events": {"count": len(renames)},
        "delete_or_disappear_events": {"count": len(deletes)},
        "executed_binary_count": len(bam_exec),
    }


def _process_overview_sample() -> dict:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "status"]):
        try:
            info = proc.info
            processes.append({"pid": info["pid"], "name": info["name"], "status": info["status"]})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {
        "count": len(processes),
        "items": sorted(processes, key=lambda item: (item["name"] or "").lower())[:250],
    }


def build_report() -> dict:
    _reset_usn_comprehensive_cache()
    _reset_roblox_logs_cache()
    scan_started_at = datetime.now(timezone.utc).isoformat()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home().anchor or Path.home()))
    dam_registry: dict = {"available": False, "items": []}
    executor_artifact_evidence: dict = {"available": False, "hits": []}

    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        fut_prefetch = pool.submit(prefetch_metadata)
        fut_deletion = pool.submit(deletion_and_log_clearing_signals)
        fut_folders = pool.submit(combined_user_folder_security_scans)
        fut_hardware = pool.submit(hardware_identifiers)
        fut_apps = pool.submit(installed_apps_summary)
        fut_trash = pool.submit(recycle_bin_metadata)
        fut_roblox = pool.submit(roblox_diagnostics)
        fut_amcache = pool.submit(amcache_metadata)
        fut_userassist = pool.submit(userassist_registry_entries)
        fut_defender = pool.submit(windows_defender_signals)
        fut_events = pool.submit(windows_event_log_summary)
        fut_security_events = pool.submit(windows_security_event_summary)
        fut_powershell_events = pool.submit(powershell_operational_events)
        fut_service_changes = pool.submit(windows_service_change_events)
        fut_xml = pool.submit(xml_event_log_files)
        fut_recent = pool.submit(recent_items_metadata)
        fut_cmdhist = pool.submit(command_history_keyword_hits)
        fut_services = pool.submit(windows_service_signals)
        fut_usb = pool.submit(usb_event_summary)
        fut_shellbag = pool.submit(shellbag_clear_signal)
        fut_exec_ind = pool.submit(executor_indicator_scan)
        fut_persist = pool.submit(persistence_signals)
        fut_disk_exe = pool.submit(recent_disk_executable_scan)
        fut_browser_downloads = pool.submit(browser_download_history_scan)
        fut_dam = pool.submit(dam_execution_records)
        fut_processes = pool.submit(_process_overview_sample)

        wait({fut_prefetch, fut_deletion, fut_folders})
        prefetch = fut_prefetch.result()
        deletion_signals = fut_deletion.result()
        designated, sha_blocklist = fut_folders.result()

        fut_forensic = pool.submit(build_forensic_analysis_bundle, designated, prefetch, deletion_signals)
        fut_pref_health = pool.submit(prefetch_health_signals, prefetch)
        fut_roblox_int = pool.submit(roblox_integrity_scan, prefetch)

        wait(
            {
                fut_forensic,
                fut_pref_health,
                fut_roblox_int,
                fut_hardware,
                fut_apps,
                fut_trash,
                fut_roblox,
                fut_amcache,
                fut_userassist,
                fut_defender,
                fut_events,
                fut_security_events,
                fut_powershell_events,
                fut_service_changes,
                fut_xml,
                fut_recent,
                fut_cmdhist,
                fut_services,
                fut_usb,
                fut_shellbag,
                fut_exec_ind,
                fut_persist,
                fut_disk_exe,
                fut_browser_downloads,
                fut_dam,
                fut_processes,
            }
        )

        forensic_bundle = fut_forensic.result()
        bam_structured = forensic_bundle.get("bam_structured")
        bam_registry = bam_registry_entries(
            bam_structured if isinstance(bam_structured, dict) else None
        )
        blocklist = load_executor_sha256_blocklist()
        if blocklist:
            bam_paths = [
                str(item.get("normalized_path") or "")
                for item in (bam_registry.get("items") or [])
                if re.search(r"\.(exe|dll)\b", str(item.get("normalized_path") or ""), re.I)
            ]
            artifact_hits = executor_blocklist_hash_known_paths(
                blocklist, bam_paths, source="bam_execution_path"
            )
            if artifact_hits:
                merged_paths = {str(h.get("path") or "").lower() for h in sha_blocklist.get("hits") or []}
                for hit in artifact_hits:
                    if str(hit.get("path") or "").lower() in merged_paths:
                        continue
                    sha_blocklist.setdefault("hits", []).append(hit)
                    merged_paths.add(str(hit.get("path") or "").lower())

        prefetch_health = fut_pref_health.result()
        roblox_integrity = fut_roblox_int.result()
        executor_indicators = fut_exec_ind.result()
        persistence = fut_persist.result()
        recent_items = fut_recent.result()
        generated_at = datetime.now(timezone.utc).isoformat()
        trash = fut_trash.result()
        userassist = fut_userassist.result()
        roblox = fut_roblox.result()
        command_history = fut_cmdhist.result()
        browser_download_history = fut_browser_downloads.result()
        services_snapshot = fut_services.result()
        hardware = fut_hardware.result()
        installed_apps = fut_apps.result()
        amcache = fut_amcache.result()
        defender = fut_defender.result()
        windows_event_logs = fut_events.result()
        windows_security_events = fut_security_events.result()
        powershell_events_summary = fut_powershell_events.result()
        service_change_events_summary = fut_service_changes.result()
        xml_event_log_summary = fut_xml.result()
        usb_events = fut_usb.result()
        shellbag = fut_shellbag.result()
        disk_executables = fut_disk_exe.result()
        process_overview = fut_processes.result()
        dam_registry = fut_dam.result()
        deletion_cleanup_analysis = build_deletion_cleanup_analysis(
            trash=trash,
            deletion=deletion_signals,
            forensic_bundle=forensic_bundle,
        )
        filesystem_evidence_integrity = build_filesystem_evidence_integrity(
            deletion=deletion_signals,
            command_history=command_history,
            services=services_snapshot,
        )
        usn_rows = forensic_bundle.get("usn_file_lifecycle_rows") or []
        merge_removed_executor_artifact_hits(
            designated,
            scan_started_at=scan_started_at,
            generated_at=generated_at,
            bam=bam_registry,
            prefetch=prefetch,
            prefetch_health=prefetch_health,
            trash=trash,
            usn_records=usn_rows,
            command_history=command_history,
            persistence=persistence,
            forensic_bundle=forensic_bundle,
            recent_items=recent_items,
            userassist=userassist,
            browser_download_history=browser_download_history,
            deletion=deletion_signals,
        )
        enrich_pca_executed_records(
            forensic_bundle.get("pca_executed") or {},
            bam=forensic_bundle.get("bam_structured") or {},
            prefetch=prefetch,
            usn_records=usn_rows,
            trash=trash,
            designated=designated,
            recent_items=recent_items,
            userassist=userassist,
            command_history=command_history,
        )
        sync_forensic_finding_timestamps(
            forensic_bundle,
            bam=forensic_bundle.get("bam_structured") or {},
            prefetch=prefetch,
            usn_records=usn_rows,
            trash=trash,
            designated=designated,
            recent_items=recent_items,
            userassist=userassist,
            command_history=command_history,
        )
        patch_unified_correlation_timeline(forensic_bundle)
        executor_artifact_evidence = build_executor_artifact_evidence(
            bam=bam_registry,
            dam=dam_registry,
            prefetch=prefetch,
            prefetch_health=prefetch_health,
            designated=designated,
            forensic_bundle=forensic_bundle,
            trash=trash,
            userassist=userassist,
            browser_download_history=browser_download_history,
            command_history=command_history,
            persistence=persistence,
            deletion=deletion_signals,
            sha_blocklist=sha_blocklist,
            executor_indicators=executor_indicators,
            recent_items=recent_items,
        )
        executor_activity = build_executor_activity_summary(
            generated_at=generated_at,
            recent_items=recent_items,
            sha_blocklist=sha_blocklist,
            prefetch_health=prefetch_health,
            designated=designated,
            executor_indicators=executor_indicators,
            bam=bam_registry,
            persistence=persistence,
        )
        user_activity = build_user_activity_timeline(
            generated_at=generated_at,
            scan_started_at=scan_started_at,
            trash=trash,
            bam=bam_registry,
            userassist=userassist,
            prefetch=prefetch,
            prefetch_health=prefetch_health,
            recent_items=recent_items,
            designated=designated,
            executor_indicators=executor_indicators,
            persistence=persistence,
            deletion=deletion_signals,
            command_history=command_history,
            roblox=roblox,
            forensic_bundle=forensic_bundle,
            sha_blocklist=sha_blocklist,
            browser_download_history=browser_download_history,
        )
        bypass_resilience = bypass_resilience_signals(
            prefetch=prefetch,
            deletion=deletion_signals,
            defender=defender,
            shellbag=shellbag,
            bam=bam_registry,
            forensic_bundle=forensic_bundle,
            prefetch_health=prefetch_health,
            amcache=amcache,
            command_history=command_history,
            designated=designated,
            trash=trash,
            executor_artifact_evidence=executor_artifact_evidence,
        )
        in_scan_changes = in_scan_binary_change_signals(
            usn_rows=usn_rows if isinstance(usn_rows, list) else [],
            bam_items=bam_registry.get("items") or [],
        )
        boot_time_iso = datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat()
        scan_review = build_scan_review_bundle(
            generated_at=generated_at,
            scan_started_at=scan_started_at,
            boot_time=boot_time_iso,
            bam=bam_registry,
            prefetch=prefetch,
            prefetch_health=prefetch_health,
            designated=designated,
            executor_indicators=executor_indicators,
            sha_blocklist=sha_blocklist,
            userassist=userassist,
            roblox=roblox,
            command_history=command_history,
            forensic_bundle=forensic_bundle,
            executor_activity=executor_activity,
            user_activity=user_activity,
            disk_executables=disk_executables,
            browser_download_history=browser_download_history,
            trash=trash,
            executor_artifact_evidence=executor_artifact_evidence,
            deletion=deletion_signals,
            deletion_cleanup_analysis=deletion_cleanup_analysis,
            filesystem_evidence_integrity=filesystem_evidence_integrity,
        )

    return {
        "scan_started_at": scan_started_at,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_overview": {
            "os": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "hostname_hash": hashed_identifier(socket.gethostname()),
            "hardware": hardware,
        },
        "performance_environment": {
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "boot_time": datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat(),
            "installed_applications": installed_apps,
            "trash": trash,
            "prefetch": prefetch,
        },
        "application_diagnostics": {"roblox": roblox},
        "process_overview": process_overview,
        "security_integrity_signals": {
            "amcache": amcache,
            "bam": bam_registry,
            "dam": dam_registry,
            "userassist": userassist,
            "defender": defender,
            "windows_event_logs": windows_event_logs,
            "windows_security_events": windows_security_events,
            "powershell_operational_events": powershell_events_summary,
            "windows_service_change_events": service_change_events_summary,
            "xml_event_log_files": xml_event_log_summary,
            "recent_items": recent_items,
            "command_history_keyword_hits": command_history,
            "services": services_snapshot,
            "usb_events": usb_events,
            "shellbag_clear_signal": shellbag,
            "deletion_and_log_clearing_signals": deletion_signals,
            "deletion_cleanup_analysis": deletion_cleanup_analysis,
            "filesystem_evidence_integrity": filesystem_evidence_integrity,
            "prefetch_health": prefetch_health,
            "roblox_executor_indicators": executor_indicators,
            "executor_artifact_evidence": executor_artifact_evidence,
            "designated_folder_suspicious_files": designated,
            "executor_sha256_blocklist": sha_blocklist,
            "executor_activity_summary": executor_activity,
            "user_activity_timeline": user_activity,
            "persistence_signals": persistence,
            "roblox_runtime_integrity": roblox_integrity,
            "forensic_analysis": forensic_bundle,
            "bypass_resilience": bypass_resilience,
            "scan_review": scan_review,
            "browser_download_history": browser_download_history,
            "binary_change_signals_in_scan": in_scan_changes,
        },
    }


class DiagnosticApp:
    UI_BG = "#111114"
    UI_SURFACE = "#18181c"
    UI_BORDER = "#2a2a32"
    UI_ACCENT = "#c41e3a"
    UI_TEXT = "#ececee"
    UI_MUTED = "#8e8e98"
    UI_SUCCESS = "#2ea872"
    UI_PENDING = "#5c5c68"

    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Virello Scanner")
        self.root.geometry("460x520")
        self.root.minsize(460, 520)
        self.root.resizable(False, False)
        self.root.configure(bg=self.UI_BG)
        self.logo_image = self.load_logo()
        if self.logo_image:
            try:
                self.root.iconphoto(True, self.logo_image)
            except Exception:
                pass
        self.pin = StringVar()
        self.consent = BooleanVar(value=False)
        self.status = StringVar(value="Ready to scan")
        self.progress_percent = StringVar(value="0%")
        self.stage_labels: dict[str, ttk.Label] = {}
        self._body: Frame | None = None
        self.progress = ttk.Progressbar(self.root, maximum=100, mode="determinate")
        self.configure_style()
        self._build_shell()
        self.build_welcome()

    def load_logo(self) -> PhotoImage | None:
        path = resource_path("assets/scanner-icon.png")
        try:
            if path.exists():
                image = PhotoImage(file=str(path))
            else:
                image = PhotoImage(data=embedded_logo_data(), format="png")
            max_size = 72
            factor = max(image.width() // max_size, image.height() // max_size, 1)
            return image.subsample(factor, factor)
        except Exception:
            return None

    def configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        bg = self.UI_BG
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=self.UI_TEXT, font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=bg, foreground=self.UI_MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=bg, foreground="#ffffff", font=("Segoe UI", 18, "bold"))
        style.configure("Heading.TLabel", background=bg, foreground="#ffffff", font=("Segoe UI", 13, "bold"))
        style.configure("Percent.TLabel", background=bg, foreground="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("Stage.TLabel", background=bg, foreground=self.UI_TEXT, font=("Segoe UI", 9))
        style.configure("StageStatus.TLabel", background=bg, foreground=self.UI_MUTED, font=("Segoe UI", 9))
        style.configure("Primary.TButton", background=self.UI_ACCENT, foreground="#ffffff", padding=(16, 8), borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#e02545"), ("disabled", "#5a5a62")])
        style.configure("Secondary.TButton", background="#232329", foreground="#ffffff", padding=(14, 8), borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#2f2f38")])
        style.configure("TEntry", fieldbackground=self.UI_SURFACE, foreground="#ffffff", bordercolor=self.UI_BORDER, padding=8)
        style.configure("TCheckbutton", background=bg, foreground=self.UI_TEXT, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", bg)], foreground=[("active", "#ffffff")])
        style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=self.UI_SURFACE,
            background=self.UI_ACCENT,
            bordercolor=self.UI_BORDER,
            lightcolor=self.UI_ACCENT,
            darkcolor="#8f1528",
            thickness=8,
        )

    def _build_shell(self) -> None:
        border = Frame(self.root, bg=self.UI_BORDER, height=1)
        border.pack(fill="x")
        self._body = Frame(self.root, bg=self.UI_BG, padx=32, pady=26)
        self._body.pack(fill=BOTH, expand=True)

    def _separator(self, parent) -> None:
        Frame(parent, bg=self.UI_BORDER, height=1).pack(fill="x", pady=16)

    def _button_row(self, parent, buttons: list[tuple[str, object, str]]) -> None:
        row = ttk.Frame(parent)
        row.pack(anchor="w", pady=(18, 0))
        for idx, (label, cmd, kind) in enumerate(buttons):
            style = "Primary.TButton" if kind == "primary" else "Secondary.TButton"
            ttk.Button(row, text=label, style=style, command=cmd).pack(
                side="left",
                padx=(0, 10) if idx == 0 else (0, 0),
            )

    def clear(self) -> None:
        if self._body is not None:
            for child in self._body.winfo_children():
                child.destroy()

    def build_welcome(self) -> None:
        self.clear()
        if self.logo_image:
            ttk.Label(self._body, image=self.logo_image).pack(anchor="w", pady=(0, 12))
        ttk.Label(self._body, text="Virello Scanner", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            self._body,
            text="Secure remote system diagnostics for reviewer sessions.",
            style="Muted.TLabel",
            wraplength=380,
        ).pack(anchor="w", pady=(6, 0))
        ttk.Label(
            self._body,
            text="Enter a session PIN to run a one-time scan. Results are sent to your reviewer dashboard.",
            style="Muted.TLabel",
            wraplength=380,
        ).pack(anchor="w", pady=(10, 0))
        self._button_row(
            self._body,
            [
                ("Get Started", self.build_pin_screen, "primary"),
                ("Join Discord", lambda: webbrowser.open(DISCORD_URL), "secondary"),
            ],
        )

    def build_pin_screen(self) -> None:
        self.clear()
        ttk.Label(self._body, text="Session PIN", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self._body, text="Enter the PIN provided by your reviewer.", style="Muted.TLabel").pack(
            anchor="w", pady=(6, 14)
        )
        entry = ttk.Entry(self._body, textvariable=self.pin, font=("Consolas", 18), width=10, justify="center")
        entry.pack(anchor="w")
        entry.focus()
        self._separator(self._body)
        ttk.Label(self._body, text="Collection summary", style="Heading.TLabel").pack(anchor="w")
        for item in COLLECTED_CATEGORIES:
            ttk.Label(self._body, text=f"• {item}", style="Muted.TLabel", wraplength=380).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(
            self._body,
            text="I agree to run this scan and submit the results for review.",
            variable=self.consent,
        ).pack(anchor="w", pady=(16, 0))
        self._button_row(
            self._body,
            [
                ("Start Scan", self.start_scan, "primary"),
                ("Back", self.build_welcome, "secondary"),
            ],
        )

    def build_progress_screen(self) -> None:
        self.clear()
        ttk.Label(self._body, text="Scan in progress", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self._body, textvariable=self.status, style="Muted.TLabel").pack(anchor="w", pady=(6, 16))
        progress_row = ttk.Frame(self._body)
        progress_row.pack(fill="x")
        self.progress = ttk.Progressbar(
            progress_row,
            maximum=100,
            mode="determinate",
            length=320,
            style="Accent.Horizontal.TProgressbar",
        )
        self.progress.pack(side="left", fill="x", expand=True)
        ttk.Label(progress_row, textvariable=self.progress_percent, style="Percent.TLabel").pack(side="left", padx=(12, 0))
        self._separator(self._body)
        ttk.Label(self._body, text="Stages", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))
        self.stage_labels = {}
        for stage in SCAN_STAGES:
            row = ttk.Frame(self._body)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=stage, style="Stage.TLabel").pack(side="left")
            status = ttk.Label(row, text="Waiting", style="StageStatus.TLabel")
            status.pack(side="right")
            self.stage_labels[stage] = status

    def set_stage(self, stage: str, state: str) -> None:
        label = self.stage_labels.get(stage)
        if label is None:
            return
        if state == "complete":
            label.config(text="Complete", foreground=self.UI_SUCCESS)
        elif state == "running":
            label.config(text="In progress", foreground=self.UI_ACCENT)
        else:
            label.config(text="Waiting", foreground=self.UI_MUTED)
        self.root.update_idletasks()

    def set_progress_percent(self, percent: float) -> None:
        clamped = max(0.0, min(100.0, float(percent)))
        self.progress.config(maximum=100, value=clamped)
        self.progress_percent.set(f"{round(clamped)}%")
        self.root.update_idletasks()

    def start_scan(self) -> None:
        if not self.pin.get().strip():
            messagebox.showerror("PIN required", "Enter the session PIN provided by your checker.")
            return
        if not self.consent.get():
            messagebox.showerror("Agreement required", "Please agree to run the diagnostic scan before continuing.")
            return
        self.build_progress_screen()
        thread = threading.Thread(target=self.scan_and_upload, daemon=True)
        thread.start()

    def scan_and_upload(self) -> None:
        try:
            stop_anim = threading.Event()
            progress_value = {"v": 2.0}

            def animate_progress() -> None:
                while not stop_anim.is_set():
                    current = progress_value["v"]
                    if current < PROGRESS_CAP_DURING_SCAN:
                        progress_value["v"] = min(PROGRESS_CAP_DURING_SCAN, current + PROGRESS_STEP)
                        pct = progress_value["v"]
                        self.root.after(0, self.set_progress_percent, pct)
                    time.sleep(PROGRESS_TICK_SEC)

            anim_thread = threading.Thread(target=animate_progress, daemon=True)

            with ThreadPoolExecutor(max_workers=1) as pool:
                report_future = pool.submit(build_report)

                for stage in SCAN_STAGES[:3]:
                    self.root.after(0, self.set_stage, stage, "running")
                    time.sleep(PRE_SCAN_STAGE_DELAY_SEC)
                    progress_value["v"] = max(progress_value["v"], {"Preparing Scan": 10, "Checking Device": 18, "Reviewing App Data": 26}[stage])
                    self.root.after(0, self.set_progress_percent, progress_value["v"])
                    self.root.after(0, self.set_stage, stage, "complete")

                collect_stage = "Collecting Diagnostics"
                self.root.after(0, self.set_stage, collect_stage, "running")
                anim_thread.start()

                while not report_future.done():
                    time.sleep(0.25)

                stop_anim.set()
                anim_thread.join(timeout=2.0)
                report = report_future.result(timeout=900)
                self.root.after(0, self.set_stage, collect_stage, "complete")

                finalize_stage = "Finalizing Report"
                self.root.after(0, self.set_stage, finalize_stage, "running")
                progress_value["v"] = 93.0
                self.root.after(0, self.set_progress_percent, progress_value["v"])
                time.sleep(0.05)
                self.root.after(0, self.set_stage, finalize_stage, "complete")

                upload_stage = "Uploading Results"
                self.root.after(0, self.set_stage, upload_stage, "running")
                payload = {
                    "pin": self.pin.get().strip(),
                    "consent_version": CONSENT_VERSION,
                    "collected_categories": COLLECTED_CATEGORIES,
                    "report": report,
                }
                response = requests.post(f"{API_URL}/reports", json=payload, timeout=20)
                if response.status_code == 410:
                    raise RuntimeError("This PIN has expired. Ask your reviewer for a new PIN.")
                if response.status_code == 404:
                    raise RuntimeError("PIN not found. Check the code and try again.")
                if response.status_code == 409:
                    raise RuntimeError("This PIN was already used or is no longer valid.")
                response.raise_for_status()
                self.root.after(0, self.set_progress_percent, 100)
                self.root.after(0, self.set_stage, upload_stage, "complete")

            self.root.after(0, self.complete)
        except Exception as exc:
            self.root.after(0, self.fail, str(exc))

    def _exit_after_success(self) -> None:
        """End the UI and process; Windows often needs quit + destroy + hard exit."""
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def complete(self) -> None:
        self.status.set("Scan complete. Your results have been submitted.")
        self.root.update_idletasks()
        messagebox.showinfo(
            "Submitted",
            "Scan complete. Your results have been submitted.",
            parent=self.root,
        )
        self._exit_after_success()

    def fail(self, error: str) -> None:
        self.status.set("Scan failed. No further collection is running.")
        messagebox.showerror("Scan failed", error)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    DiagnosticApp().run()
