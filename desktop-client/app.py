from __future__ import annotations

import base64
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
import sqlite3
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from tkinter import BOTH, BooleanVar, PhotoImage, StringVar, Tk, ttk, messagebox

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
PROGRESS_TICK_SEC = 0.35
PROGRESS_STEP = 0.42
PROGRESS_CAP_DURING_SCAN = 88.0
PRE_SCAN_STAGE_DELAY_SEC = 0.25

COLLECTED_CATEGORIES = [
    "Device and app diagnostic metadata needed for review.",
    "Recent activity and security signals relevant to the support case.",
    "No passwords, messages, or personal file contents are intentionally collected.",
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
    "zSs%M;0-=xcMw>O+@RtD;Jf_vB8CZwz0a@;%)o?m^#PyJeY0`hfUJhwr$(FW7}zL+eTyCYHZuKZQI;^-hSDCVUAhXoY&F-5>"
    "s9srHDI864(X?zKg<vbSwII6a#&y9n48!_c-zqN)oA6il6ZPjKo)K&#}H{kA0<^MO<}Q7P`E`*x!8dIeThsk=^jrv+<5c-hA"
    "thlX=snNgf;=%96e>{C`z$J6KgZ0sV@pZJZ8ZnPCd)N+NF5IZK|@-YVD*EHVGJRBEI|#_1lMDwDEMCFDs}KsQJGMDO!3+`_1"
    "4c-o52(dbI=u6WlZim(W^k07^tKnvf%Js7c4z=xv=C@cOjqA|ix4qaaz)So(Pj^-^&`aTwvkz^auXTYc;_+K)j3bO3j9J`sk"
    "WVm!4&!;wv3oXw9D!?yb-}r3%&&RZul+R^LMK0ox7NTcUN+eWMpYh1Zg?G9BFJbNN_TST;k2)UNt@D4$k@g)PcU}j`frnQi!"
    "$2fD=gDRh7=gAqioC6VAl@N6tg48J`}xk~hQ7IRdl1B3O2fmm)d)Og&7Z)<q>I%0iP8mQ*1vxsu7H69Cg~@>`+4AohDCwM*d"
    "%wARtkw93D6+o&TScCe3MJxN}mHX%fTzj&*^bw#bK2z&i5nIm*|Z3K{M8XhNgPG<9h0E(}KlqEr6d>5p$WdFTjGzDpO=_$Qv"
    "u`GAha8<LSo7I@}_Kw9~L9{>6L%ZpWLuYWLID9ic?Ez~O`B%TT8IQ*ECs*?52CMGWOU8dFg1D~U+f&^vkz5gqxA#P7lp0OS_"
    "z5}+7vD+7C*ubz?)fd9*XN&mW+A{Y?CxXj*VjU&2phcYK@Q`YP|1CkXqBL+-cDR-6{RK_m83mezxG7dQkRV8U0n*cO_>^>kX"
    "ZZXMnw&9f$I^M6^Ushn7YZfn#Wn^kQbu58Do@&w4=#DgQcrq2SlP@jx-ivL)061sC?exG0Dl_N~g7|N&c#LMG9NNan;;<yB^"
    "3gOQ_?}2d)TN5qa^5F_2NG$xoRc05qUF`lzO3#6fMueq3w;0!Uk4Mwa8|uM9z7;N%I&LKIdWG~S4-hznlF%apY#nQfn+|yt}"
    "H0<H<(woK)*|x)%dOFuum>^FKBKE+Oah0U+6QEGu5o5B^1W^{t)MbXLgjn^o%>*CqJb{aZU*h3vQZXS11Kc&&<SXDKnoEmjm"
    "U)64(IajZrfhtwtU5etDRLVFK71Ty;lFEdL_Q`2VD^#ZZK84e8WX{F!lSJw)lEaLG*mj;m($6jQ1bNNM%M<p?~sQSVIamqKz"
    "e7}ccmrcz`_gZU4{NOCzu_^kYr<_x(FZ~EmlIzO4oosW)mFjDBtZSFUY#mmhF?HKuJc&HN`HS(xJrVbz2OY|cLSCkIzhk-U_"
    "#!8c&boE5T$k*eie&}~XfZKbZ?GbYGc3EJdR`X-kI4GJsOIfV1?FrbtwR?G$xYc`0Hj8nICL{wHNAucuYqsg1{B7lDTWj=na"
    "&!lD^-Ecz`)!v$@44=@Ka+x$sF1n%9#@7o>wX8axTPyk`(sz}{4Uereg2N&f1y}@1JD12D1(JllBaAu%jcUq=oBOORE!)Eva"
    "Kt@MTvHD-LVLbSec6EW%Np9uNs-GZE4Kd=6^uxHv~YREqp`)UNB%n{($_C{nVn;Fi3^eJw?DKLQ6Mfr_Kto21Vw?%1kX2RDO"
    "SJOfvoH(ipH`x}ZK=OTLus2uM;#xfvO@`&czKxM6wj-i7_R!QLV<0&;2>gV$#!W<KzgaPzPa@E{DmyKB=TX{0gK(sZn6ZP5r"
    "f^=3sv9rvogcF(sB!PatGA|~s;$H?TGOg7Ah@4kIZJZQ{HuJO7|lT$$2`gZmX;zJcwBbO2kI6SJQ(TlOIcmUPOTon8a<^s``"
    "6)G;8A^`X;b~B!<$B!pWYB$0SGBqlug=Y@i;(P0ov#m9!`4m$BZs`w`8_96B*(bJjXO5DKhlx?(<do2?PM9`chFu+)7OcWBp"
    "L58GeI{_{udA)R@Rp1RB6^|_C##Z^r*R~xxC1f7H~a6H(EsTmMV3}G0h9W-!8URf2~=?9dMVk?(Oue1d=qGtlV>H1Rs>FJ7F"
    "VgVft0C$lDkF&kg_2n8D%(WWjE!Oc5pa(cF-ym-&-`q>wxoe9cj?{&(}YNKdf3dR$c?Hs9v*-rt8!v_MM&dUpWIvie;r`Jb("
    "^fYBWRqs$~i_tEd;#@_(q(Tw%k>X3p8XPvGP0f0UUL=<Qj%ZjEwRuLE$Zw#|vVaEC>q^<9E$He~mX)Z=a7w3Hu}aE5iu-m2?"
    "%wI=Uc1~iJ{(XnA$><;<gXD9(s2q~oBOy_e;*C}A4`8efOa*u75AA@BDnP6pKe~^v#$-bR}PiiEZ)v1zVzchD_`JNadsTRcL"
    "n7h6iv}i)vW-UuYJ-)@p=5p#~V<vtJJvkm>#AzrLn`grMQUqTfDO_ICB>wcWyg*^%*hkG^YyR>7M9{&?OXzoDDOZiFi;!pQ@"
    "tQ~JQlM3r>PK3-4iGIX5P74W61LVFb5R<*Yz^`(RP$q>mQ~|C#gG(|Noa^VS4~V+v<u&Tax<~Tw5pRmFh~E;uLe~WZyD}Z^k"
    "T6z7ZmfUd4sAVD;jEST!1L^9&0qoXgtZ1p|c>)t|l9mEZ`h=&0d4U4Mj{Ww<OE8^IkA+eZerD+cB7R8ce#d)O|<Gkr+oyyXW"
    "e3aZ!EMI=LuJW#a;li@#F;Q<3UD#VLn*4kVeylbsteeVIIol(I-i8zRakx>Ww46!n%p2~ok1UE9D5YA-?AHSqHjo@c^(y%`x"
    "6j**!`po1Y4HMkIv=sa*z5!YEEkWltPUP{7TvG^1t^V@I2n1t{V=g2FgKZ)~c@kj$mmR3ckZ&;r}Tjihj?P+%xktYSurI@~R"
    "W;NH0i{7cqs%bU+X{y>IWl_#Y->gHpZzL7ikOm1OQi@RA!`az4`*u|@cmnMIAbyAI37_xSt@3<X__QVY*+>1E2x~bqWk`vd*"
    "Jvw^bHt&NpBZY|ijpKum;~-EnQEfa@h3@*NcY)ch6~a>|6A6O)8jx41pgA!Pngmk@IzeV?W(yK;I<sPH9c(89&A%)ww9LAr-"
    "^)=i01M!HG_EMozbB;hlO8etss{ldDU$UAE#1%*eZgeSA`Y`_mQ6Aq|nf`m~6*X{EITCp>o1^>ltIX@U3GptVajnA;Kpng6Z"
    "$N?aUt2aevwN$j`w#;iShOtr#>Z*_EWp5#ATBb;ca8jRu~cbW5o47Nc|{Q9lsi1oOgH63-PQ^I*Q)oy9$1)bn2q)BP*o+y5X"
    "dR^FN<_5kYkJb)rYeX+h=4Uj^coBY};q=cmC1iG^o@w1KuQ(KC_E-@THp;KcI^iU!H*_WnKObR9c=hl_)4bet9S)IQKcWE&f"
    ")V5^<hF&ER2b^Bwv2sU#6dlrDB4MIXYU?$zQuj`*^iS&_tKF$1uVy`)WYKfFyW4UAv9@_mj1kW|v1Hv;YUZ|>dUf5PJ?5&fU"
    "v77fkS8|2`;N>5h@(_|m6qqwdD#`r8y_m%AZwpC-UUwHB|><1fB9z|6t_vzGwSFJY6c%+T+jDK$_`TCw`2DfwG_oGc6^OfIs"
    "~BK0nlW%dpc@gh;0nHaC^J@hvTr}^>pOW-v6>Ert5k01v-*}ulKZ*evVAAyW^Sz&!s%9Kg7k=tW{>jQx5IJ^qt4@J%uDODsQ"
    "z#HhY0yelq3Mb=Uk?hnT(ouYn84zwx|i@V|I2*XL_&;Cgb5N05h#48}Q#P%n!taBwr1ZMOEz77qNux)`fTB8b9HZ>(V`(Dif"
    "R>^B&_LfcseydqijQ|-%wlG7XB_t~s?t8T@9eB!&yB@@6;Mnay>{^!fIxUPQHLU_A#3EbG3gOxgCQ-TRGnMS9ot;f-_qQ^K@"
    "o5px`WBFh^tEErz!}?*7N*<c;EwnWkN8FRqX`=h8R(>F15*Wwbhv8}1%>x>kGtYQ$xMJU}#t|G|K&$)K{ixjC3HDY^6?CY>H"
    "5;$^=Q!xJ()nfaE;{4|PWU;p3A51Tj-K)KcpZSIc4z#o(Zi;la;=zFxDxf#7iv!vq`=h1G@cYsOJ?hjjU4i&(4KnL7q)Er$&"
    "NyzWbz#+92$*}(MOG}6;>5Z^RtaiN;&Ih?_Kxz47vNx(Yb+*|GXS;ppp(z3Kb7$is5N66eR`va?|52>8P=wYr$zXO`>(&3as"
    "H`j|;CwEwuGI=554B%DguW6^FgbGX^G1$THKvN9w0o0jbJHlW4Qd*K)77v<nKPHvTZJ8Fn)kFm5Xw*6;GF53TGh+6m`Idfs|"
    "YHBv5$SPhv)$lLiuArN5*xZd7=9;a<@ucsxgB51!^r4lzC@e%-t6;lX0^%|Ny&tXmmuBkGqaw1WVEpe1lKE=#u&*-Xcs5#nI"
    "_W-%R`xXy2Zp+QX>!E>j`&(<1S|rbVA?tF5=`ypiccmlQX(L9{yC~Z8WAFVtVd-s|IKL$N`S8d^fa(-JL>KSEv^1q0abq|(Q"
    "<pwHxlwXE$HO_1zi+*zM6(4sNj$yz)tu^B$s?8a&ts2H;|_x3mxVo2oWrph#Ie!1#C1qlt6g|F-hu>q)GRy(Z9w^aeFJDt%d"
    "rce*EX-+1;=l12#Jy-`+W77ZZqsCljcyD^f2U#U!=gL;(V%5B5O@iKw&N+F-j-;3$Cx%<T=7soJMo9zy3o2%73Se^<#)E@p="
    "shmHxR4y~d*naR5%WtMt64F_%or>W--hhYcJg1^tFzCszu51~pRP^^}4vQ*Y<R(K8qCCRm(r=-p*I3d3P?YBYYbX0^q@(zXr"
    "K%iIh<VH14g$puI20mzHDJ>%8G)KJ$U>IChIWW6xmODvbZfZ`7vqxq+f<&p!KK(^K|<E^9BdvtQxGQ(z*6;UFBKHUn#tn^%;"
    "6AtO$4*h|)2ldZe<L3mMCZnCp$)ly^RhzZK@J}CC4+=vb4vA~rlmmFtB9AhfMuPd41baDm+CdV6{r&>mi+!@H&fp!tFcW_xX"
    "v1Vl$U{{bDTJGxPB<&d71a-rQzc?duXd<s>~n&Yv%R!#9QtU$&?kr?*~MJn!sCCEP)Vn`-!c#rIcQkMI@T44#w4!H@e;Y@t-"
    "Z)$198p$7MARnY=rwA>zvWT;Q~zU5)SR2T^e-?$5u<k`X85K{^L?qRBSR7FM10*_3}@hO%^MN^=C5@Rx9W`*=UY9Hs7hurgg"
    ">Lp`pRv;eIG&E~}K+`Ti*1Yx^~>_Lqf>?efZ8k)G3|s{B)sm0y_{Im+3VmhX+#S$t7zYr>?m<{}YZwOK1fmQc1o?zx}{M)Qj"
    "s3kg&c*93E0Pg2&knj9@RcmB}b*>hR}9ljdh-%&H)H@Rh&KymWNq);`L;XEP}E6ZhttZMjNWL?jOGnbTM)+|ZON)u`V8THIV"
    "@6%9;(&@#k>qYvGiA!bDo*Rrft&>tB<TO@mE`BGOdfH4$G-j5p=Oe06YPz2p=%{@oa}PU#C~aPP9X{+<AmJ1Yol6yCc?Gu|z"
    "ghmbPuk};=X*g;!G$L|d%gc6&SydBHxeBu07*)q+KPyDpFcuG^CP3X;E|7bIYPp`5!2h3`w@^h9B|AO=lF`xEUbB*=Pfmy<k"
    "9vYd;$IuL^($FumzXssNr`^C>%q5XJngk9ub8)=NZ7ewQbvw6fu@|K`YW*qdXWOE!%ofNa<E4$SIq4c~0(O1OI%v(Hq12!qy"
    "a~KR<!wdbws850nuVVtHO0Uo9JB7r?dDMC&%_l1$|fcj26*7Xwn!(%oF%uVM5dIYNP-f0g|kxMCQgXU(z7boOVl@rKxT!Ipm"
    "0H_GV@Sd@(8xQ^@X$obW5^}H&7^U?8y8%n96DR+O*bq?2*q9<Ve8~_oh-Ux`z#%wZnu|j0bLrqZEaHvU|(P$OQ{BuSh9$PWn"
    "zNlmGVsR^tDDf)mmr<_~Ww~=)Mix=po?$y}nzZv!G4<UvA-Yu)9R&|}_G|I`Zf3ppJ|simEHTYHRG|PlQ3+a)@`7L}!ie@QM"
    "QrXX$AVhp6mM2FW)dt9w?xBLe*Tcqx^U%Hw!FRR?wvfx2&lB(&dqR&#0%y}zsm3b?eY18WWMPW5L6wLNz&|`u>>L!>*AAQp}"
    "d@Z<$+iQT1z9X<t;ehn{@?T12q?dhiey383eT?6r3>4N3VF}wR7e9G7523LJ>KrBvxfv&!`N$z)>0j7US7HEiy|^)x3W+CbQ"
    "d;wE7iwKWJtu8*S^<&@N_Sz}{|Lr}4@RsyqC6)5*hWtR#taq{owg$#R(Kc>oGeT&+J>T0eQe<b#r1M`7q88PECt2Rf=1&5e`"
    "h@Z_yq8@Mh;ncT_gu=};%hG^@0bveyO!o`~-BZXUacZCgl(LLgoEqN|c%#>U>dQwds!uipcgYVu?Lp?c}r2^dr=6Zc~T#ok+"
    "QhJ)<YvNvncs~)T0W_o`P9&V=a~v|NK$KNfiO6Cth>VG-;esU&msQiT&w&EPGu4$hyJG4l2y%7IQ{oTf<bQH&_>b0-X#C<`#"
    "`rV11|`z>8lMrUAjYSN&n<MylqNMMRQOXSts}ECAOkr)@{(1)kRrzVWr;S#0_{8^W~)D8tvj_|W}CaRrnkI4?>1@-?g=CB$t"
    "5@qAtv7O{MB6t(R4dJn!cq00#LD9i@WvIhuE6}ig?`_Vax7Ern!NJNhaA(li$nzent8KSMCN+&iF1tju{C1B&{t6c6_gX?3+"
    "S3JTS{Iw~{^@n1qN6bh%4o8&7ugsxTw>0nJB#rPF0^oVh;QaKT2+WkM;p0ZAHRt!eu~rW#{xH<QC|$}g8_dw5<U!t!rJ0LGA"
    "dkqa4DgjdlwIPS-^O|jMN577$U!OO#(uLC*3M!}bddK$dTet6MSJ*-zF#=H6Fr01WA(I}MS&99BJXsqDuT5tpoO)n0%hYAXG"
    "Qk$Dzx61hBeqPOmasQ2Qo&DRqtTGNmVgCL({?#w-nka9r!%_%4KY9Lox!54xmdx9oaoLe1a^zGWtdaS{10|REI00IyyaXaV$"
    "16QQXI}}vGZLG&P=}>6kGH$GpSypx!8s)r%*S*aK9v@|?C`#=pil+a7V68m?In#Nw<aD(Jqt`dr+KOo1sLVR7<7^*chOgg)i"
    "ldmKKl2uhes4y)iMP*aDpKe2N$G$ApYkGv6bc5$K|rEUW%ibBCH|wOUm#QGFoJzZ1ju^)Wt-bePeDx_W9Cj&mySsBuTGECtm"
    "fz<HJCNJPT=}%*x_Wf+I4IO#ff=0B-essm!J9a|@kg+<x9a%SQ%>L$YnQLsHu`EA6D8!&dY~LRt7pRP$g4DA)PrB<|+~S{RR"
    "0A2twx95XWh*Szk~$KcMbq4eiQ%VAeS1oqZ2{_Dn9nFsnJs=TSx_ZMpgoi;DQ5(}#9S-$N4xnB1eK$mzUK<d_&0p+J*2Gyg9"
    "baL3K?3_q*kL7$fMx<xX&~gn#GvV<5`Fsn%^~~oYb?DeNbY;Cs22~TDnpt&H8xPu(S0hwZARRw`Dp_OQPBKO$4@Gr6XJ#>09"
    "TdLm<)*5WEG!)m=rq|5L`MeFq6u@8L<*kXEoj^=Jn((M3GPyyZoAHAu+pP|mR(1wPS?9Z^SSM-4F=NU`E2ubEB68BuD{pta9"
    "+WCI0c6ZzGI6fo;H41dVDvat4rM+N#;iYk_T>l>P_OGq3rHlqz2)bcGNG)?DG_ihbO<fBnciY^2QOnEDqt9&z@`5dD_lGkYh"
    "=1MeWE_eqU6!uW7s2R@uIE*vOEH-;Q`+#%+7(?YaeBpd@|0D#yVqEGwo*5-TSPq^wO;hxToj^d`E3(wx}Sor~j;obo$<R3VP"
    "KhUA(^XY(VMt$%r+@>j=y>1Z~je+*`!ytTNer^n;&XT+w=-EJ3gSvo)_%e-1GaWN*3l86CDh4ou(scE&rC1Tp<e6g|@$|f_G"
    "P8q}N3mgM$7x~%?KBxU%mv<dUPEPN%#HJ-mLdwO{HWUy1rCK~Yx2-XueBThA3oxL@2e7{fKT{}`+MmN9xIdufch^x{iUv}Yn"
    "`)Z$<D=JPo|=pft#HVmoQymRfeR<)j1^H|{Be52ak}-%z%@l|>lur!eS_TM=y{z^KKW*Hyg)KC<QgK2V09X-jkrE$u$s-c46"
    "W<W@G~XpD`lQz@;IsS!IXB>v|jUeyPh`-Y}R^*)_>MS%8iWkL_dYA%*pxY7?hrA8HbgVi?3ygK5&=EDR)kbz}sxy<?B%HgJo"
    "hl&ErkOqQC!Okc}yB$(Ixa?vEIEo$C*%cjnpdizaD)GJ?2h|Aiss;ZXIws@9MK)rpkh=#ytMfaHHw60yF2@*q=$7H>&?8ocy"
    "<eNYc`VHK(vn#yiqj&Gvp0n}iIYz}4~C27=YhyFk$xBRKKrzgW|rvol+m!BGp9#i}BX__0mKaBqgnX}@IJBZ-HB*)lKw)=9B"
    ">0qseFBKyLQ>#of8%AqUOEFAsO<mGRN<;b<OK<Q<^Rjq*l-5yB%MD+*O}r>8nB9ag$OlFp4<^8jO*E~cfr3O4HBo<aA()y|6"
    "13;*^PnUF$-+Zr@cM=T;;Vvxn2U-)8N=2d_OnhfR}<x2^)h)TM;4^~$dThbDjDs@SZmnirrU#m*gg}gkJeR^BAk$v*UuWY%p"
    "Lq`P^C+*oEy1VU^0ifQD5EC1!a8>hmv$B#rNoXcao;|WkQ##L~eKCToYOd<YOSdhfntk#N7E#1TARNNbuUzdqm==eEOHp&$!"
    "Ubq|;~XFS8qhcfrK(#hr>mpZ}(K_U)W24E`&J@=W++sh65PUL)?PJ^AF6dBLr<mzJcN){}q~3ZWyM{LDFS;X;h%^si=ds9y0"
    "i9*L?C%*POk>UIlzwf&&I)XDnjE8&~;t`gPyxqLJYhY5p?nM7|9*Tm0N8*2Bi`qyk;2w`(}OD}}k(PS{dL6W95Tu{;vE2dAv"
    "RC5JXJ+aR~{|0La&^8aXRT<Lan50emm9E^T1%MyV*XKl`2JRgt?3)i{;G81gdXu$TpgKDjKRDw2>1FBW*H93-a#v#oq18H|*"
    "!V1xEzf_JazP38qN?^bZ5l?=>+1p@cYKxmu;Ip>XU1JxRT;$r*X_H<Fh{R^k~}kSN7_<UN!yr=b^`A6S>h8y`{=iGgLw2Fy{"
    "mji;veN-#1YTpg43t2*q1p=Ok_lq|F+GARz8YU<d8-MOT#Trw;g?UV&IE)gKLQU(F|resmqQ5gB||I`}4mYaOv*yp#qoS*|y"
    "4M4-W`O&<pt@&9>`f!$XVp9ns1k@inb0)0v%m5k;n;%9%UsXg&xG9|!X{6Zcl@&anKSyYRPUxh2Up{Z1fOSjE)PG^`1LnBQ5"
    "3ZN$~$z%+;EQVi@#L5gHQDRhW5T3oAu?2S6SbtSL`2EH_9u@vcTy(=j8*Y%CxAln?UhF26KazqN5p(k>9pady={Jow!;m^m;"
    "J>m|$XwP1L4<f$hQ$c47AG{94&pGm*<pnve@*xQda8D|4I#Y>*ZB4lWnBtm~yt4_j2*OUZ>OBc$>(s>KiSmw_Ri|zb`dG+|l"
    "tzR1=TVU%bqUeX&{p6+<~;d(K)GEIVSgiL@|7Vg%L*fD5J4K5hIcaLQ4kYrvN}AzZaRUPMTjSNAR$N2C*E&P3=-ByPlj3EzL"
    "Ue%@kOBjwFfn9R#B)?z4{C+X&^qf4+z6qi5pASEk1(HpwwDXnT6RoNR}BT(gS6p;}>O(r&Rh#3O78JPZwiNH6y3^9|F{3-S@"
    "rCw~qK;B5H{wel6CXF{fZFB;h1wD}dM+ela+PIL9*0d~)Ef!vrzL<n!37axjw+dr62OO|UB-O8-A;j-<eID(M)1Y_+TtN^C7"
    "v$4Lv5308**$-|p#0UYj<-_g%}4{*FcW+;~|ad9nus$giR0BW)EB2zgqJaW#a@KV_Y35dTfaMi9$Pz~5WrJZB9?;NIw@CwHb"
    "im-Pkc*||&L=ko4!g6zizQzWh?*;}z$hBYQHUL@j=?q`jYEg6&&^<Amp7{8_^Vm=^IRqTu>9d~@5>(J`$xa@v6yrq6pS0<Wf"
    "QSNQVQL+NN#K~ndqGhs<B}e)%82>(er4D2ZNAq+mplfxn7@HfZ1lhO2Vus|h94ik(R{rkSi30^Ek4-{bF7k`evwckl&3#N$}"
    "?8`Y)Dbept44J3z<qQ5*f<lkRR`787*RXp@fZiUf$kcTH(Fb(NZU(B+q(lG*Y2KL;M0Gl{j!OHG$+?TTN=v5yKy|%tErrCsK"
    "&5`|GK0Qtpe5omT8}k5~qo6Qnt}RoQASPp=KuB?7%UxJD;tjcPamwFLw4-Ny!1z4=`=K5ZusOZ;M4C3BqRS)><UvYxHYobEc"
    "0){D++k+@A&;NyKhrYc`4he8>f!c33^8BQP)?=4PYG@6upr=EhY@#>_vf(+VFO-G%|(z@Go>yyX)pOosFL|8ndFWJZD{rNjD"
    "B2)`-jB~y5YJBbkq{US+1^|?Cdpt_J1d(&F1{TALLVsdh`c|Gu;}l!bgb#sjU*yd9zoN<d&r!h+Ga~B7zi!6?58dOL=M`42i"
    "xiI64q!3VUs>d(!%kL$`$|2G*YcnRfa@II)5K&R%1h9gz(3EwT*2$x$31U4lJmbuH_wAQ<xmppuZ+BOHCer%-57-Eq(15-&#"
    "6yr)+$18J2-jPWPj=v5z!MKMzjqK?Oo6TW#L$Ek>ogKJd|^_WC}Z6HEbXpxTIylC8V-MQGg-#zJN&u1}6R##p`;u;c@ql56f"
    "`5)J|~}ZTKQ(eGU!HHpx4wkEL*UWl9nwh5m5Xr}w0pd$%ci>^?-CY2Z)frRvK~_L}M<#}!3-kUHduTNYYnp-B<MjxJ3lFJlb"
    "c`&DE@)JNUpvMsZz*<;;9|243kM=M>HgQ4%Xt(#d?-t<8n0oV`g$RYl%gk`Ri(~h_0VCbenY_h1^P*XdC$bly)$Nr8b^)V~o"
    "ZSx7giGxdJx&{6Btq=J(>K^iI%H_rOH)dB(kg_D{+Io{&(Y2=Ha^;2rQDtTm+7;3-|LQt`3GeW_gp!4M?qinmp=t2XKUFux5"
    "cCZgyc^;VAAENS^B)tT{5__&?EoYoCM10{pA5fIF=5Uky3MI~>fx^86;_>z=9I>k%m|te`Q6hvB*gTf0ohvRC6ww+<?n9NXx"
    "FdS_g}x8QI+rawVNxy)W5QoACaZVxt%iFn|NdI2Z!X6whl5!=kO()$J*`7ZByu=FvCa0p?>Evn&|PsJaV~q?>>6%ZM8RG?A$"
    "8#pCh5fBv90DC2)Rx1-oZnYNbJf&~)bxb6BA!s3U!dx0nZw1e;7tXD6lNNP4;@gN0p)Q1_lI_$#k{()O{49O5XT4Z3&*M8mz"
    "gUhnWnKi8Jx6i<1gU@XO7R^>FY3-Q%iQ+K~P`sQS;w}(Gn81KBt{Pju^+2SZH5B6t;boRnSeTv#RAVjASxq^O0Br~>8?&@VO"
    "5V6mo+jOxlqybyB4~?%MM>mY#QKKuP>gr04=9?F;e|6a4-((yiW)v|inFkQ@Fo(#1wkK4C@#SP^B1?_8X{%yJFk_vuIgq)_R"
    "JjLrWj7Mah#@1hHweEhCa)Xh(2%}WX3pnIf!AB~vceJoXdk8q^Q3x$q6`loEc%7<_Y)fuy<9wnGF29d3^xZUut7b%0O>J8+<"
    "I!o6;LdRKwT!rNYj!+HYsp=b9GfNIaDjd5MG8qc~0=4yU&FZJ~A%QCavRe<9R{GY`fzhirRavz;{f7!UkvT<jZqMzT`iCB*5"
    "v%uaXYMjUNi8r})3N6aEOqE}2iKgo~cYuY$GW%!B7_^W2bp#yd$A*>BWrU0hwsR@U@B_H2L85O26mI@f#?FhjuY(W@vtav8{"
    "5Z*gOPj8&bbZFQpsE@&d~H8u!RTtg;{qC}EO%aVUl&B@Fx4T+SE;NyDu^8v818h!tsAmCretpR{1)P83h9&blrwMdg<eybMu"
    "0;jP>upC6eVNQ3Ou}Kv&MKd>P?IgzJyc+Jzsb&U=KcV$F=xqZ;JjWyC?Ka_oDl*6Y0eS7JLZlCFdK-)|mr(Cy2kgc+=Y>qcG"
    "knG2W(-%Nz|KsojfiGApbFv71a}82fo%v$4>hS&lte;@3<JxU&^M5@oZaO*{sH;cCmJskGe-+w8>V;vzT}kF><@P<pQxFqSS"
    "5a$!mAvO;Gw2D$E~zHqoohp`VAs045L%aK$cG_@gNsif;@>hi^_Os@K(`s+{=sVDf7#)#ml{r$Ne=gx=J~@dgPbkoHvr@ZP#"
    "uzYu=X?qX`&T#Rh9HPP(Lv>7=JGt5{O0FS>SZ^|};VA#9z`XTT_FJeW((nDJ5j+UwK-!gMS`YL?Ys*M;~$*TqI-Bv^Qqo@~?"
    "Ya^haRww4yx<V&Bjc#~)bJkZt_Na}O6h7Cj-`C-CZU-YBu*q0PzMnQ+{R@Fr(RnPFCN3i%AcSm!0cl-N;zD9~?I&dh-=PhKs"
    "XVjvYjNSuin{!pXvpq1q?)J`Dh`K&{9?jmIETm+BO&VINiRG>u=eYjalat?fD(2|E6Qk*Pf1S>TIG2xY>LHJqfoUkF`x<nOw"
    "}7T(oogm9lVy3SxEfS1i(^oTQCyxPUY)K`gMfl08SE43ql`H~81QrKMczfnj0-;ug9sR0vZ3{Iz$H5Y&ddA*16iP}#M?VNb2"
    "lpOyFqn%c!~czZ~88qy$cEs-(;t(q~_>|0+8Takk{_4twr+ntATWVyV83T>qo*)cXm*Vjchl6n1KG&ZJ8+Hi~Gsxk^b6F%&}"
    "PG=C7*u1Q+Hn<G%+9rRMQJT&-S16%YY_2KM!+i@7y~;@2DcP13Wh>#J^G@wths^NRla#;J8|x$fu0TIV1-@4Z-a0vJDFG#EH"
    ")TK*iLfMac%*BbXDCFjjk8(J~g19sVu9X(&``<<CQt*tn;WkGgkgl4DkQS0cFRFGs?k_?Q(V1P@s8Qq|$$lE)PL}I2iZ!ai+"
    "Um-1(01tQh3bWI7qj%cpAaF%7Sr6i9PU4Z4rnE<ai{pDup5Kudcc7|-7Mirw*4eUxf<hvKf%~~gm_UKe#mb0ul_H48X`42lB"
    "Gdu{@kO+Yow?6G3&RgN;l3C`KTF|v?75%b+XVSb4=sCt4`s;L(>jYt5R)VY8B`U?8G>4hyx#CW3%33!4;=|%Y`B)BqQJGQ*6"
    "z>_2~_eW(kh&}DLDk%(d*tVI%2IxcYB7>e0@Ia|C%CKQ2v+8UO}PBdpS2t?lcedXa%jFsS@q_^`JKWeeUvIu}5FJh%VTg5Kr"
    "gFT-ldjDhr&Uji7+ZF?n<Esc)CM+}M1J&-dQ%!AJ%0+tj%vL#*k=gkXjJXhzRoD&H>e3|xq(${$<XtV}-1!QnS8Kh%TO4kz)"
    "0EI-7BM-?wEBDL`TWXbl1J34ZI>1{rftaNLrUfxfOR%C_tDr1^Bcyft1)Zq4BX{+SV07kDvsC`Ta<csHtKsJ;elgj`xy(z$A"
    "E6*o>M4xjC_UTRhHXHU=K!&WMX18f4+XOL(dJ)h0B8k~@q_;s}_};*y0xh|*gq<5AQbpOXUK_53RL#!2$RVxLe74g`5i5wh^"
    "yKMVATzf-PPDx(nIGo-$#j+XR#GCfWBd2!q5g|x@S-Lg+KET(esMR(3gpCg`%M?^yUDW{5}-n0jz18MQ5#cmd#dB_uWoI6Jr"
    "N)gWulJ{1jKUu1?!pHPSf5WDbwF9>;7v|C$ZRUOzbYMB}7!OldA@@novs7QomZ;EJYIcf=47DXj&WMGn%KPL^jywQfXTQTqe"
    "|c98k!}Pg{4zz6OtdM96{HmK0c&j^2#<zrK1+OH(2=VP+(8GY9(O1oX<gWNP_o5hN-;cRH8u6(VNhtAJ_}1J~yV^Ry?fqp#y"
    "^h))?9dUv=SJg1+W46MRHZfyD9&G}rWJ8RU7o(7nuFZd-GqfVY2oHRwflg08k32}9!3j)7Yh19eJ;?2l`PGKB>fzd?QDsqCL"
    "Bx`}S_f+iP9+m-jfj0aC`)|&x{(n_%10_2L1Icn<NlhnTqXWoyYthb1><>1>LpJc91LBFloU^`Jfdcr`Jn^kLIlWpmJ9jptN"
    "IJ2~=YkQRqPkP7aP)i?T#|FxH3j!|fBYT21h!%_1kA>wc$ly+?$y=Z^2|N)nAix>0@>df4Rsr83y!K*@Vf5d3OuqMng7GR#I"
    "HQGWf80Q2181YAKsv^AD*WN4)9m*e?J-oC|3cWX*n`aq&O<`#<?Kd##n^{Kys6SCU68uC=xFxMs!(#iH42YOz)-ZdiWI4mM="
    "9hg0wuF3h$K)*4z(=^?d1b-1f0+(b3XAr}km^np1>Q<sESP-jK|RmVDAG|CD&0DYQtI){+9JKKhgvmzp9$9MIrPZQ(nR9&xR"
    "4niYL4&IRC+Vlt27{rA-VW0tbmpPP6J&iI@ojO%1H&T&W3Z4O#0utMZh+PO-z-)Oh=;t($JU<f)uywsT{On#E?nxY+aSRm0-"
    "TTQj)uonGB(igsQYo|V2PS=|s8Sp-do97!>R_fRym+$5v(eF^IC8?{e>fx201H6a%i891+bT3zB>G<dw)BGtw+eI7K7v1weZ"
    "Rii5^)75Xad6fNNhZM9l}5PXmgbO*rmsW0eC`gB_}>e1`ejK^o4OYKY_qtAyyOraM777sW$TVFxc7c2lFJIysAYoG)xw=V5y"
    "C#21s)zstVuo$!}?h60F@kkY_(Z$<_udVol6!u8F+x8zl1|v?dpAw9M{ALy&mi7J6#J(61FgHp^m9&({L9l4VMU(Pwx)YiFO"
    "52K-r0m2}|*YxJj;k8qp$9f9jaW?-1t4kv_Q|zRK+nJC}%i+CC@wK>e3Fn*0YarySstUK!u(Cxo&GIQfRyunJ%l2MwuOB4O8"
    "V8lugsz%ve!x==-Rud~vu+R0Jzs1gba5*_M!e2f4N9_fz<rH<pR_m>oSej*(ptI45ASZtK;0?;(#?@9D7@s=W~KciYU;S>OS"
    "MF?tDw<d7}@s6c%BgW+hfKuE<LV5Xb^db(Wc@g@Hz*kPbk1AIO%d)5myKWn)>$WWHI@c~$%;Qp2#W+9yTKi3&F&FhHG|I!DZ"
    "J+$LNLT}5*d2w^5hyi8wXjZ@PKsX+52bKlqQrYAFDoi5&$XO@6e>5$j}cJUyXo#5qf(N*yUS~)hYh|DF#)=%cv%^I^sLfF8@"
    "M)4;`5pC!a@Ff5HlZHdGn|a&|m2c5nip4PUot!?{wc+JIo$Y6SU3D4CY5)|1E|2=WU7$4O_h;!?rQ`q-PdIJw556rJOO<isv"
    "m05LFuEJ;`8K)>J+C8hO=;n*3G+n9Qf(+w;-rwzbO{eQpp&S1_Vr?)=}c4%zv?IIH9sTokZV=N%o(4f_E*w|Pp+?Ob6$jjf<"
    "yl+^Nn;;eU-lK`oy-7h=B2z(`z02!VZ&z_yZ>0a#7D`T$JLs+o>l)QcBdoswv(Mm^w>U<=0*nzwmCWni4dEP<gG9RdWM~bkC"
    "BY;sDBa$%0Qq33r{zW6ev*Y+uD#RU{6*T-yP7gN(z8Z?lZhq^?;3MIAd+__MR@}hee=R}I?&Do<XPSQQP)bOaMVske3~*rbl"
    "RmA^w_FETq+f71Y*3G=KyMCxW)94*<`O4c>({J<dootHi$@HJyVLr2Prkj|Uoy$~_oa14d>Y9@`IVf~@p?g^^npXe^A(9K&A"
    "^$)>Cv1O8Ak>*pEv`lpo|nV7ob720n9i1a!1P7ym4sf3tfX}34+<N!}wX|W3Qcm;<pE(B^NLoRXwBRQRnwBD|}+`n6{``4$g"
    "QHi;yNfWP4g<)Uku8%pXKx6hh&udplI(F=Jr$^%H#U5J%{*FQB#u*4)iVMU?DTIyrQHd611eJ<L6`xq?OVeqK=QDdb^7R^kS"
    "pbb=dB;I-C<#!4!b<&}|`)BEH7<RZ5@hAGl{*h}ennG3`VeQ~zuXFK>l7sw662pu&!yn63HvecbgIIa09dA0WLs4U=Wzc!p)"
    "XGZ;CFlFK#SxFP~;40w}ir5h0{P*QY4>9QvU)ELt*$`xtbZmbq4)K2_N-Ir~1#93zbo3vq=j$vTOxCZoEFyQ~x6VbS&WMRP0"
    "&JLBP~Yae6bg||b>-bOB&0Lp1&I{?6fz^Nc)b%i_3v=~wfhX*Q}0*Zk-qnNG4{+OLQ7GgR`SVypgpc+5E?WnVVxkX;cmEc(9"
    "y=4cWPbGJKCt<k0&5A`;3#SmhQAX_EHikWh4L|09a37oDl<0unNu18@8(@=`-?v!ugUIKXP8-@y?%u(6lp~g0mJ5n{1BXwbr"
    "wNu1*kv>fUSik_W5GKk=BeM6)yT3aZUP**T34zL(M~yQ+m9p}wyB_W8dKre{pJ|C*TDYVT0o@IP5t4J|o1zH7<%MZ@mnN7EJ"
    "&A8}$U`DeKfn&`QN#30erid8*Mw(!$p&RxQ}f#2@LZ>9_wy2SsWZGq*Ev-0HQJ9|aE`yAoHChy3jkV?t5*%>Cq!rE^s8Qi5#"
    "RNdoAYxneMN1Bo#X%0EIp64!JT3yp{r`5D9=W19(a|hIQV~XDU2JsS(pne)x3|+sU5ma&lx0`EmI29GywGq(`?vbS!PwKq|6"
    "GAS&RO8b%9eF99FA~rf)Uk3kIn}${&%ixQj^~rAORAzfr*nyWUJ9Q30u1{UgxdGyLiNby-YhT|2FO>2{t9>PkR-wxCZ<bS$x"
    "wb7KPz1dFmn#7Sl;)pjAz4oqi8EB3Dx`N|AKF#f`7t49MJO)eDVlTv5aLA%Cf7|3FXl7&YFTNnaE_GUGm9?C%^?Ff~CkQV$L"
    "Nr0!<EGo)w&#?d@urx{ksZj~CJ5CVkZZ&n3YAyI&R|maK~-htAa3-MDVq=n)Y$>T{PLnvcGZ!SZTJbtD2un6yGlL^fppLQSc"
    "O>#<cp<D_NaiJJj7fmQ5ioNov4VX`=(V!`lTr@&v;(>~FadyGDZ(1RgrJ@HA6;QVYe(?XQu>J#%dw3if!T4_lKNe6~-pqAn4"
    "Wg2B+6#!^I7Mn=@Vip4}4nh>-j9)g%z5PT#I7Ek^E<ZNJ`OB$0?(gF@HSi^a>108D?e@UqtEMVI31DuNpy^dP04AT5$1ZRg="
    ">;$2Wx(0YY<B08Q^6SyY~OF_UwoH813n=zU)Egh#gA+IgQ}kB0w`txCF-OL^H#-rvVxdHaXxU?$Eo=VZFiiO@6#I`g_hLG(J"
    "_kQGf$ixyo2a+m!?1~UEa{%{pZVR|9LAltbYoYUF#t;sfk8jh`e)C5A)PeKQk}f@9+@yEeTtu!8-SIHXJQBe$Yswu(Iz!_@H"
    "o)gzR_GT^VG6fLdT=lMEpw=hr|23mk69tihJ&z08MRjE|x#h!yKT5O(w`80i(FFJAUuDlXE|y<00z)AcL@>#Yg&hsDA7sk=="
    "~rB(Y}c;I-W-OQ6O)nJ`Sunx;(ZxgPz)h2Kat6m`^=iop+y#T`9*D`<4<5<2|^wMSHo}05Kt9DADNCyLZbejpcY}IcuB4ckT"
    "IAq$Jv=?`@JNFQr$YD#B5E<^5wwl2@rPKH||Gn*RIsV})k`VudOt&NRkD_usY|0kC`ulpfrpRM=<-niWPfrOX3u6?~I4W<NR"
    "mZJ$magT`j1<Fys1eHJ#!q6fU5c1TEiFD)mq#zDX<zJruO02bPmah^0Z5DTHF{jY(U*rajaq<an|WuS@h8Xx7U;8tuzb?TuO"
    "NzWDAb^2(SFHrryVjy#WZVzH94L^06`8%A~A$-?bt(h-~{h8h=o(C_|`4j*LBVd2)6)R0aQ&d0wJJ`;JaCP+MqGXK2gq!TV#"
    "w#nTacYll~8jN##(!2wgKfDX4R9{v~;a#r^8E_S<?j*ZIEUwP#mO_sX>b`ij%cwwG?Sj|JlZVpE;7sYtFK_+_tHhkOCCQ>w="
    "<&;$J3X9&d0Y>aoR&`;}gH@ZYgQe2F$p&nh?Cif^Kg|n6DORX07jC93`7I0bH%R{vvPf8lq5Kmag9-?c>10M&Qt~bZu$Mm-$"
    "m&-`k{1V&jUH<JHF-c%;#MDt(FAg$jg54AgL<y=yeLi!JNJxt01QQ#Yh0Ic|Z#b~E2dX^7pvz19xa2$;zU<!G?cB=Rp~(C57"
    "Hpd*l$?RR`fl$3mZ(q4*IT3c36p%RIc^*Egf#rgXgfS1@mrwtc2JIwfOBjB*JsvGs1X}c24dQ+=SUtpp3oW#pPd5AheDX1V)"
    "iV|xh=`@2Mu*ww{E`w!~f3g1j^33`3Dv|P(#rfW<lwcXgJ{KqGI%*N0_lY1vj$mh=*{YrHIL>C{Mg`R+y^m=ov!4<nnW+EA0"
    "^Q!Rd(OLdL?^pq>)Ck+Y1>c5<_KriX+9Wp0}-|6eel{>!*6WjnLr8+DfFZJE#|CZ>x*%xU+VxAQgD*z-x{PvPjlfx6p6AJVP"
    "8OihB6(l9a&U{^IPmQ{UUQNF&ox5m0Z+kI2EwBt_7N>1LFo@-1@%+)4kD~=H3>82m68(u;Ixq~>~<NZmFa#P%ZH8R3HlA?wa"
    "qd1E*dCT)(xhMDM<j>}ja)_>(aP^5*|9#%M^gl?xNjD&iP?<u0=N|;3^krNaHk0FS^a36qGoTI)c@d?~35k9X{oI~AJMw5!w"
    ")`=YSr6vPWJF~Wuv%!2Al2;GSLdB58J<F={3gqI8+aTZ{cu~{ezn`|`-Q$D*ykd_{hMJYL<nT$d*d0Uo}1h3dNUeT^1b~JvW"
    "U=mOYB$+pQ;l(kcf*ANjO<>Hv9A51&8J}`?ez~@YFJ<9c9)JOif#FcewS0R!gY919z!oX&iY6M>j#C@2yV;R#Ik=kByj*Qk%"
    "<cPTHySb74={lI-WNxiX^xt#*lVW1M!0Sz9B37#LddOTp~ECiO3=Y6@43r2tF&IWObvtR8-k=l0j&7;hvj#7BId{@!c8=yv6"
    "j)U{HAzS%Vxq#Lc3yGAr?=NcslMe&e^p1T@kOfKLQ6ge9eM2EDPeT+ZyWER(lK`HzEnJXpMgfgL_f3Ifc|H@aptfI70cK6_k"
    "b+2%+UltcAj)O?%Wik-gu!c0l^T`TG8>3#`U~fn(4dvfV=QPf;NfDyC!KBvP6#3sVozH&t`&8FozDhRRx(#QlDYUKY4%e_S1"
    "1Kp$SRno^1nyE}@4g8FNV*``Qm`Z>0t5{LJwtxhJ#0<(N$oVFXV#>ZV^2QoiTB?;rdJxczmK<cM&qBh7Vj5L8=hs`m8LQ|<("
    "@%PZVHnG3bKUSPK?}!Z7#g`Fj1EIVj`32hEu*Dj5zqs^QR!vfopSX{dqwwfY5tXfu^G$^Ha-0v&?e6_UpXC%7#jv!M=bLX_B"
    "*v1@i?u^>gvQ_>gsb#^^)7;t<3<Dxv<+s_fc1l*SAqPNU8?+9TI|6KvVt7IAbpVqyYM$dStd-nVD@%^s4exOv>o=*6_Kc2_8"
    "2xIhAFVckx4;K~k8e?(PwZdzgTLD2wAL~ymsK3->%)b<0fTZC2RF+D#3R&Fndzkb4<fy>(t5y~f8pGr`L6o4xHir}Y)-PK|e"
    "hkhJJNk?V(<9OUfkTAw#_%&?jri%S#{_RmgY>QC$;phVqVj$~i()SW*fMGHw-*Ie57pbiif#kjGA7|5{h|zC=rCE$MW7wFt!"
    "*Rm{JPjF=d*Fdp2u<RZ7M$J(dQwkF!O@dAIt?=p!h>(8ol19@iB`%kQwaZ%d%io&`1XLz(cFlr_jw|2e;n^V2fK!a+1tlahM"
    "sCMR0=-^@bSL?b0RZjz}DPb@PXLpXF#!t0M&`d)1TlxMqYQAqT5u6qlgDO-y04K4k_|QfGrUF?e`T&6~tsV5Jad`1K<d}&YJ"
    "=X(c2_L1u|g@-|jku9hqS?zBg+eA>UgNFaX-#Y6jPVHIE`YkF&Jsug4fBM!?`#fv`{CI~qQ8yy3U$0>|$<CCjzs?;u~!x4d*"
    "TbLJfwt}A7xImjd|j7?mJl&M7H0i?=<L2ief$K54aa0~=$V-rCLb1+Q|Rao{&XmNkJoGZ=U$@P6V=mLcpq*D2#0>SiWy1)ox"
    "w2Kc%6&FR;K==4QT@Q7Ip!~pM!eFx=h~gRurcHQH3P~@*I%X04`CW(CNW*v7k4zUNZd?k3$&{PlZ9anKh&yl(p6cDX^8PT7;"
    "qyhB35=Z6vY+)balH{N_LG{TO?^nxue{ij#WvPCH4$j~=`oibF%X|PqkvSH->W~Ca<o)4h+2D<OoAZp>T4ldBo`=lo+Vp67V"
    "~p}3gjVA<c791KhE)9f>iN_7s8Mwa;TQ5j=qzsva4Cg8}^Fh+OQ0af%mSAleG{lq3-HkZHYHRSjHJ6n;Uw2wE<W-G0}!{@my"
    "c_2d!Tz=*_6>7u=TT=VM);<W-qzjpwE2fcTI>bWC0}(le*VfE3$@z9OEQI12C?{bTomyC^RsrEw$?c?#)1ECZHS%{<F(pf&c"
    "dy=7UnFU$}FGJSBMeufg-3>RlCDKz?oLty^;XH=ee?4Fm6Rfaw15d!}PQ-a+%>}Kd?r(I1voCKyeh^11+uKPK1_>klN`~#H`"
    "Sm7gNiV+eO6o_oc;aJR3gNH#_49^3~g=3u!pIxkvea|gnQV<0_C;K0#$f@Nab9_GMGh`1gEWHxT{Y=Od7(a%L!}*asgD13Q0"
    "pq{wnDE1rzK|AN%7Gb!eG?GFUd0oQbnTvyzkitvY>Q7c6dJShvB0@*1Mj?|`wxj}yFRUwa$lDjZQE^OM6J4k_Y8SpcjNKUAb"
    "%^YcB{Ew@)j*Z$)ZmI4F~~!zs2$QTBB#d_fzLTr@-rfx243593jx7%}N7+IzgmYZQn-vi>zoU(qogDOW_}-H{T;j-g2KpOkX"
    "L|Wf8hi<v>qWaUx1?`n$YeIO|4apTYGpLduxRjY#?!V3=ii>P<^#JKXXnU_L+nJKd(HCFOwFb@ZrS)yi3|TbPQmizQ=B#)AA"
    "=AZ0Lq)z^VyqiT4V%TrNMsvyC6X)t#&YS1HVbB4kbcUL0s$MAyVob{sCo9;tj`!u5jo$<&!&@guU=NF_|1O-9efw<`pqqRKB"
    "-0V|w6oW6b>}rK5zoe2uk%_Or8Z!YncUj$mEf5z4`j2y`A}gB1-H<rR$)!L{Dlo7vIYOSVhi9gAda`+2zCy6=?4`I(6ym#-D"
    "BQ?R8Uc~t{M~mPSDUTify#0Ew>*q6@{K?)$i7((y(r`7Sc6^yu{Yf?J<DG&#4R4L4ynXOE3Y~H11r&+676(nhRHO?$48EJ+I"
    "qSz3>85Wt$C6rKhu;0P%L{3y@0(0Mad%>V1eiB2qsAC9v@edqW5nvDDWtw6=WgguR@XM9WX)+Ony`V>0=x<6t6N2zVW_Cy=h"
    "c3jjo$M+4e@ll0C7K=r6O6p3Esvgxuh)pj=<R)_^bO6^qy=`i%(-#-_?KehZ2@l>>=i?ewt}p`tXAGAj<tK*LJ(U`!j?&CB9"
    "^9SWP_VD+L>r|f(BJ}Goqo-)N2Rd67Q5ZANTwV4G`(s2J4Txn_cC4Wjto!fw6PD}oYkK`7a4L#5Bi?gSP3QxWN)EN7|6sadp"
    "8%P1^x>kJ$bvU{8dtf&sL^&)@UMyMNK|im%%DksB&?s*%J#n|sk&+`ocB_BqinphVx6Wzj`g=-80?3RjczDx&hauPjqwrxJ_"
    "c^Y7T>m{Al!hdmz+}=w+};WU8p!L{q5I33I9~+orFG9!7RKwLFon%};Db7xy?75jM-7YxCs{<7pE=nMBz|9maay<fM1V17-9"
    "h<{4ySvczd>xkV!@WO$I8GZOsu(>s}AVZFh>{PMz8_(kN$|9(s@ISkTk{{=okYGvHv6CD#N1cy7mOkP~*@wbT`u7DXFw{J<="
    "g5%+S&uf`Af&(jpy0cPlMj5;7nS!iVqo=dAzhy4M|huYGK*fC6TK&ZR|UZdyWi7T?GD)da(Cl?FN9zv?EZd8xUStbJvH@;P$"
    "Z`oO~dj<hvCZfK$!1R`O^31s8K)_v_mL6L|XV^V1x((?ng|6}k1vSCIf8xy*86<e>HTA1BvyXQyq`^%RIGA<6RwzgUt;$uZ7"
    "nfg;kV`*u%-BaRgYv-~0a=Lsp+<Z8OzL)br!tWFFU2X_*mwDn4Mqmjud*jO6gma=}$(l*5PRq|@FJtF;^?9|1Q><~W62sHmI"
    "1%(;1#GSc2MB}<8mZ2WEHNuyMkYP1hW3WKEptnA&4VnLDh~IEH-G*V?D|!Z7s|2nX6)(Us2lL*&zStImnzl|483)jCUtyjbd"
    "+TS?CYG*zZZ7OIO}TSKD8(a2EsEwrHcYOg1w5v#=_$wa^&i&fZ)=|519^kpC5=jM3=Q0=$0J?AwB6xX}}|reFQmZgb~%3ew$"
    "yg8*CkeXeSpF6}sd`HM-DFlcsXC8}b<Sda-&uxUvxy78W;JAgk%8DIVHlr5u}maU~_5cszRt10C3ONdGI`;wNPHTaCvk^3~U"
    "pJ6Te=##hz6YFD2+G3Wh3J^li+5TPG2O)(4(%yv7sVdPtH5xNQlxV@$yrAU+}=A>XyMT4OeOVcaOU6wC&$yt!{es(sjG4D5a"
    "Wr1>4h~Muer`oN-@Zh%FOwqxMm0qUQce}cNq7LAzD{A+iR`+(woE-_PzgTCo4~%t^7pURHLIyHbtrsbiscQPChO5a8g8Cnr5"
    "n56lJa?4FYRO(dc)BlXv-NS|#Nn8dIo)NBwq>=XmdDGn?gV~mBeFgG5CdSy&&O6d(a?-gMq|dWP@pLge6DXuZymo`)t6BA8E"
    "cq+32Qk976ahyvT|#`E0qfMp<>X}41>l(idi`mIqz~q)3#()7k|jDr9W<;kq7{+*!16TQ1E)=>RWqOHGb$A!ub1CZvgOfjQM"
    "E#&?epQMex)j-hc)whOM|zCrxvK0RnXzg*)4^|F*=H_!bWtn7#jurO}<MflxboS%SrEEz1jG=6OOfW)sm3co~e#^`am_)Z9N"
    "2^5xf>Qufo4Lk#xc^bbb_?!A&#O|TpvyvVGVsEcU2ey3fT?>S@}hEIDqG$uHn8=nvA3YRr297VzG`tJP8?>-Z)@(sV7Q=uuP"
    "jE2wMw*;QelilpruiplVu35|SwW}TO7*Ogy>WV>74G3XP!5VgR!+N%W`U<$e%rvTTb(0)j_yf?mBLAXDsLU~%hE@a{a01mZO"
    "4dM^vrTB?KhjN6d~B3o_OVY^x1J^oy3V6hwEEW*lB|!PyjpLoAw0>B)FkKW?Yx_!-_WNPRDbtFGQ$3-0;7y9@cl<m3Y4ikzz"
    "na*V=0%P5hE5x2#xFE=XU-9X&s$u|0JTQ;8n@A)KRD(jbuZNPP<`+$!<&FDA0o<V|3L8rS(DCYEw@sXjCRfssYbP{C)=GlTp"
    "euj$VtDt7e<pRN)GI0tD}0ETJVuUlPE+4$53mpUHI6&8iV*x-&ZJ`p2+*y-RD1$I}z%G>kk2s9~BU>vU&os+(BB-AVv)P)sW"
    "JUVRT!iOD4a{DS#w#t=O6fKyo6mw}b852kaK0*}_v&=`o~hdk*TM>1^I;1?|c8j{&iU-)d&esx(2lQ&ba$l=cxMIe|*BUSV4"
    "E)7L2hrx1mAiEzQ<tycR*FYY$MCY|wc3(}355@Ga85^XoF|Z0ku=alS?JG%l+-8M_6IuEL-vy(7(RPQ~g+&%|A~${z0h@wu<"
    "0yVPMHv+Ux$!$R-!gJMC{BX9XG8vz;1sYrQi$X)S5QHZWs9jk#PDQkFbsbcwlXc=uhTuF%~2Ejh5zV9;|~u&7l%EmEF+$C=X"
    "2^A$fGd?I%WouQOWa>me`wPrW5z>;C3~<@nxX+=x;Zg`*TIHyE{#E;LW598%g7aATtIl%l20*<6_wK?Jz1=BfyZv(4<d9EkS"
    "Aj`G1mfD@Eo|Pk)}u`3#NCha-PXKJZ==uyvi%!nTO}P6*PY1@cRW^zf59#Wmt}ibX7-%arKvefqregfdk>H`13XHiSaM69>1"
    "tKFO_Rbrb*PF$vR_f1$g`x)-P}M%B;1zd6QlBNFx1mRJBE6FlhSQ|P+RSZq`P78YIGt!@hoz5M~6hmebpC^f1++aC21!j8%&"
    "K+2j0(z(^{>xR})@67YteCO1d7BG?h<$I9PvDBgUmTjr~EwS$>Hr%z8tI+K+IZhySO{$0Yy<aj-+F|2aJWQLu$|HqXVMm!Fj"
    "*?=mxMpwh3vuhI#-W4{1^wOKLk5fZ<;hj?z6l`a1)#CQIFV@COX!7&DBzap<8jKsI?bUnmZ!<zUQzB}lpA_D>BM!x1q?!0*h"
    "dlF_G+{a>8Ezag1B&Lro{UDB{hX?vbqjnYZZx#V8R$H`d7ZIm{sp26U~`tkoBXO3Vw4%Jo-ZMp)=Ck1fYLEK+6Yo)p#UXGcL"
    "j};>TO}I(bAQ8#GwO@&}kLLlY<1fvuoNjQ{KvhB&b74^JT?Q;F-ePYN#*lqx{&yrlA;Pj^0)So%Q3W&+#^kht7z;HvIk4Mks"
    "i_Ea=God)~lb+`P|3K;dL0s}(oUP%XTV8#BzsPLgOJWKq2N)lI^JnO~4esjGS4EQ!klA*})HdkX`WoWrR7$9Hj_c>=>AsdT("
    "B+Ncr@FCK|$I8)r{%`k)oI79Ucy9FNPk*6(lC6&HDsNlP85|tweXcq~;3m)2fn*3Z*OG&#PGVIwJ@RWO{+NCgADlAjU%J{IC"
    "N9e+R_mMLFOQ)&xzoIbNU4CTNzQ%du>ukRrS@I5E?XP8u%)G%u{!iozUw@u)mIP5{{l%O!3zNYBLpLxct#psG0@j<ZqatOOn"
    "9`k=uP!2;X#%;_d4V|`L}WdXkFpKX?3zmF#^XDC?cwjmj*T#R$>31XU9sH$M>_Rw*BTQp+4`VQ#SuVv~>c3%|zU*b@xzG^7n"
    "os_c!B`=-JtYX=-E!U}nO&79k*q$7CU3Rm1zXwkgt1F|9uEU7cYuK2f3z_1RA(-;yRVb*LR^n;?0HBy!r2y(C+zoa|u^YUlQ"
    ";90q~2mE*8Sf|IilV4d+#p_vEWUT^%1agcI&tW@P1DkAu2x+;;NDoH=m75*Sz+#KWla$6QT(%S#-X$0_zU6El}4`&^h8-M3s"
    "CI(I@|E?XVIdbd-U}2Sr&Lp!BXFrgzS!%4PuE2TOrArUCiv1wpz&#pTO}C$lJ8>!%Z94H)VOEr6c=`B3KM@Mvk|MbxGE420u"
    "Q)KG^GTzuDR#20$@L#2Gsm>UJ4PHk%ohNE_ZHGQ(FUe`YE|wm<sy4q_9g9SE7Oa(xv7{GHSKU6IV)<GEMq=mLQPQmVZ5@He9"
    "2qrhcrQk=sa%G=uFnDG3{*M+5d#igQWQdV?$eyW$tFUCe#nUIuES(Y5DAiL48Nd?bTIV`CEc&aZqgI%@D_=fEe2Ss9)P8qS{"
    "ya;C1~IRWrOxpW|{Cijq1<JWfiAHBBSuP2VVRo=c=$bNiPym<0B<=vjMxrptCZu^X|>v?EW?Ve1N(-SpLzPRQG8nOoTFRQ<>"
    "Sj^{uY_}Dq&2c-G^gmD<r@(pWVYcR=VGj-2IrQ&gBC2Eg&pZ%&&ACKGY;#K-px{@y*27@m#i&Dk}!kxjH#V$ZiwG>^%34GM1"
    "brjOI&wj{I_IXlD6zk!a>H+cwX+G~dj~JXD{?U^jI=~|{8Wc}l63oHzW$kdA+#PREEES~(zcqBJmGCFis<5g*|Dvsnd5}%5*"
    "d52DLOG$?EsN`vSz~?uTK!7YdInC3WizeuTFFCmV7lwIViEhHWQ>K5Y}^M+DI77n`!(s~zTMw}e3>(WZX^!8Ny_KxX79y+9R"
    "B|ORHf_<!2fjx{pJu%aO?<861|zB0MznwB;44xEyh9Han{dVI1JTf8`EUcDyC(i)_(JDiMRp}#ds~+ss30qD2kI!=bhD2Q5@"
    "4UCNbS5J<VFLUb!dCYxTiJpJJWK+(24HT@+mE5f}boXl4S%b<mYc;rH}K`i%SZKq2Zdo4@5yCB`TLKixnqJL0q#p?L2<`iJ&"
    "B`?zL8{EHPLB5d<&y7yt}LP}(&*4X9Rks>NUI<KRM=n;CG#Y4hM-mKwMQvw<hk-63z7s?|7BSTCwVh}FPw_h~gR<i21>q&fp"
    "TfkWe)AtejL|T-a&T3zxz8PvHM<{#ICJjK@uXw!-Z-yHL{>yffuw}@!c+FAcg-HlG+lWq*4hwo2LegGeT`J*1OSReY7beunz"
    "*NVyX{-^zINnO4c{^ZzcHTXh)GhL6-p89(rvYcCe*KD2t4Cs(GejZ)FnHm9!+yh?dLpc%W##|k$#~nJ*H$mE@6T0bd&w;W<)"
    "e(^GdX$lzNcBg?4cYZ04;bnMZ$smyDQhv%)j|l4&o07_%gM;Tm&@w0Vshv^C_pdyKlU%lhj!_Ag2JF)c17G3o=sSZH2)&1vl"
    "!*_zcA6c1bF#F4b$P&6;UtIk9#}rR{JBUEONg_xb|oQANZVYOn#1m=h4(!nd8+%hr-nehUo6pf5OBj{1G`!aql(cZNWJnTYX"
    "$qckHz9D2)RLchX=do4fxMNUudqcsVPKBU;YRBK_2j{3XyrM(yG1(fj8*LqVYG;!ITZa`|Jd!VY5B(%vPfu=ZD(bfsrJ00+K"
    "fqD%#{Z!Bm0uWx8ovrShZ(HD>J~teMgh6)<%sXAXS=I;qN_f(Lhr(1_hbPS0DdFGl!wi&$`K^zS!yh(OIQA_)hm?&o)EO`f`"
    "xp=Sy+2dZ)5w2ZTbKSrzKMLeHfs8>56`NMXeBMlc9kiKNkl9n{eZ!Bkw2Ir!?f6^4q}G)SAO0=mm@M;?TSqrTxN8Zti{H^mB"
    "2tm{?<pM|5lPN+37!3KLe%^X_1KP^oR#;QQ#xOo`7C`f7Fj>fOOJZF95w+E!Nj)l}SAxhN!aFfD(Boz5EJGc~}1|?z=GkqKx"
    "6<p?K#KbAY}xu^}$JNPq>x`~d8!-(t(!aIU1d%O+rZFE{fM)2YRdU~&>M-YwQ~^2KuF)6(n0f(obNinWmYbOqn3A+D{NS8iP"
    "_(gDIWGLTPVcs<OQ4o0RroB5bC{A+QAQZMJh2u@54*AFeyfHPa!!27B6KLCE0STMh?&(J3Fl!1ccl^beVaupJ~09wAi!@s)v"
    "DVt(1fDL&9mdWanTF4W3%-oaw&P02<3%E+7cJIfoYNqsvMLlZf<(Yw;pXi}EP=JeP<W6rdRr`ZhDRAPGq~@CpL(gaPIT1TRx"
    "LN71Zs9jq-Qk<fY6Av>YzSLstNMEDYUj1CF1O_ZdJOyLlt~MFe(Zp_N5}=VdpHjBL%cywSW23OI4ITK>i$UnspX|4I|i;wGb"
    "9E56$r+G@d9W5b4ZIbiVru`j<n&g98j*jc2Gk@(HZ*Drj|lW2jv~U?n_38CqPZ`)zNl#|0}W&fBoCH&8&&`n9w(Sz{AHD0M2"
    "QT_N10a{{H2#dcnxEmtUZ0GEHs~-Ulv1<Ar;?*Ao*d4-4+49ln$k2d1O=o@rvD#7@=bap&m*6e(h;J!wSDd#k00j@&yiTM22"
    "q3*P+VsyoG^g3e1Sd<N{;O=IC`I9zAibDdngs_tvn%mjyrvrAn{1zP@u2nYg}&~_D_^3NXV)&?=MkfPCgEf48veLg?RdSs!}"
    "XRTo8WI>^%Y*IxFsRV@;#mrONQInWTXZ(k6ubA=?a7<Qx0_}Nm!QRXKM|H*MqUC&?Q(QYj_&69{)xgrkOr|<Bh%>q@wzgYhQ"
    "4k@s3i<d~+nJ{*+xP|=0UEq!5r4bfJ5-rjXFJ2%QQrVm=VIk?#~caQIj@x_y0(KJIaaGIHSdBeUFT<4qxt^s%iMWAg#5x?>*"
    "qNmeLf4^vGeAIchp>YnJ1s?7SKjXio__4BJJ_#F^L)+hdqePVX?Y^WON9#SKtl@po}Fj69G@cv4p$oSH*$qUVx-sohzEoRjl"
    "r%?hbztTzx56Ns<RhOF4*hRJgd3fd7K)wnwqhLyhgEqCC?0<xyBx6Cr0Zx7_^~$EuuWa<LT`rEH|hiJMH$pVnKxt71OavMEh"
    "y)9KRU{QlNUI$a6?p^w6WTI+MwmbH&)u#>eZ(T*;7*VghUy3?-2W&xeA-QUULx3&Z}t=c>i9n#~||4^4hI}#I-rpOfB7P<m8"
    "H?vF%kp8QdkZALrGV5(E)B!J174se<RySEdV1{>UcsCqv-)~1LKb+}$jZ{E!666hqY3aU`6C(LO$ZF&@QM3Mzb>pjp^>2Ifp"
    "0+c_D`oQ4H(PU8yQ=hk@^wvAsL7M<Oxwhi07MfV>Y;JtKkmKXsum$MOcc@XFl%yYW(Yp(^DtfBX;luO2IHCM7D$W?6VdV8uu"
    "(kl=cW!w4G%DYa|-W`3~w4uvbI(7XBW1&;u8nEHoi=v>*=w4b98X!J3)N$Cwn_WP%;OaP>Lxk85Icdv+$u?c_<aNe)fh+Y#G"
    "~SF>-xuNud4#0Oe0kOxc){U*Q{UP)xa(4-SRj(K~CWqhM$rgD6Symn2d4jBaKg`1O_1fnN!gI|1@R&xAjAb`VNZPhVa9&MH9"
    "{d_{b(cyTE8ec~_aKSV~U&_n*!jT%K85q`c*;#H{{>Rk53*W1l|YP~7!b_f^3XB`NP=806FV@wu+HV2JK%oJi-IEC$tDK~E<"
    "hdw}en)@k~tYnBIP`|8B3oPJO&Lc5MyQi?b2!dJ!2^_zpK51?2z}4It?R&VMIJRyzgv&9fs?&_`23Wm;dTN1lgOTIu$m_AO!"
    "6WK$lCSHe-Z8nXTAYz&A{hlLgCedJH7@vqPs50b1^J>70;$Rk2LP|72HRQX-Sw8Q6a6DeGRmaDUN{%<8O|=ZG4su(->{551L"
    "E?fA8p8SLSxwQbJ(nOlEte6<&QxaLoOs7IK2s|gTeDRz3~{(w-~1Zr#yIWYE2vl6`cnordc&=lJH=$NJhaIf;gcc%vsB_@-^"
    "T5f?dqAoNWK(3s3z_NF^t$JVNtPi}hdY-bP^~9xK~hLb>liW5P9}2`OrFM*`-SAZrOsj(W)|pYbe(q#IS1daH%OAUdnX>0r("
    "$Agu0I*kAi`IV!IuGO6`$ehjUdbnsc*E=rWUX^8n98IQtkANjBs(xRy6YQbP)ZM7f-8trtOjdW98aL9QwHl0YAa{RmB1kllP"
    "X3Bj?AC*fT!QoYN7Y5m_v0tyBnE@kYnz#CFQnm{OZKux*3qfFU09XLXZGkB9>mUg4W4yneyC>+RqUo_lIYsb9b>XfjW;OVmX"
    "ZJDgfUhdIxlUFdhg)-Z0*mmX5PgR~f8C9*Miv(n)M2RhP6b|*>sFrdjGZBz`pXyAaQ{%wAo;hn;oN}YWi3;6)DywHx82xM%<"
    "JFhYzs?plSr{nj(XnvxZ97)W(C_l&T}(*E$NXLnWyO*mD={!wE&^QL72SHib?2yE7tAFZN+(c&_L2H{5^_wRlWg1B>b#gI5g"
    "$+8f4S(3^)S>Xp}s;g}DIciESgDemW<l6`#X;SIWw5>@Bddo6p0ADb?zYeSbs!5M@y!AH0IG;Y)c)k1Iu<{bb}CarMPycP)Y"
    "Et2OOj7{!sI#dL(hpr$o@1pu!0!Qfqh1`IHe%eAJ&4v^a>Q3tLWoZ}M-)CrqmML~$#8&IbQ)$;q9)F(5l^!=-U?~Dos<9=nn"
    "cA;G>&KwvXZeSHy7G*xZF$Y-suiko|pOPXxkmK!pApx{eeuoNQk9)jme$^`cjoSp}tB&6YFpp9|h}d=WL&H;VQbbif!rv^o{"
    "hj`MVeMa4;RMZkm>Cr_-~XBF%P#WNDhc=Qbd63bjOGF)hO+&a)(k*IR}_ziMi75myL+4v`5B{4d?vz=&opYbOAi(lZ52QltQ"
    "TR8vHeh%FM_L3jDg-#3IL6!>XL2&afUH&y!b17`G>2H%oI!wIKH%?hf+DW8pMsAOqwA_Sr#$#8$yU1NXPk~f{mplSq@CjtcE"
    "0N3J=V{=l=!nMDWuSYXa|%a^}`F2Eu-PBf3_Qoqj78EZVdh%k&cPNd<@w3~0v#=o_cxig5snZALzkxysFB(e%jWFS?mMAq%}"
    "~-}8>U`ZMu{gl`9bj{w^1Dfyl;j(QrzWD<}t1DN%xU$2(EvgS_gL$=?p9m>X38HqB@t;Ruc&z=!FGbOee@|xBVaGp8>ODXp#"
    "?Je|?QYP0!i<X?$pD{wiyfT<EzPW3dQ>hZl*!Uh%2x7EFvC@2w+mu{-*=6caQOZc<Em^Z|CAw<xuaf}3hQ}fP6!SukyA&vf@"
    "Z*zuLTk&rpU0RNOxBU67^d-8PfK=?b}=)o8QTC)k+VOu;vt=wU#&%1y(x?t$QuA2{B9=Sgov*dafL|{{W1i%cqw`~eEVpBZN"
    "n{fNn_Ooa#`%4y{xo|!)|m{w&bvFbo$&g`#~T?G*50kils`PR;FQ(hMR^eDuWsnYck)Tf(PhLnb3&oj(-7|3}m*MURZQUMo&"
    "Lc{>A9lzkya`u)og!V<!6X_vy&V)?yYq>++r=ng<*tMQE9W=lJbu+)0PL9e^8*{^Yk3dBE2O*coKMdoRh~@`{MieL1%2fa#g"
    "Z2O9E(AsCCjTo=nRv&MI)VNRAh*;EZG%bgnC%jDBE;<|nu4othm=)xB8xyBKJ_f#%lA)7;wB|rK5sHAF_0Nf=Y%z$;&7|-Gm"
    "+50Ha!)x+%kDSP1(^p|)Q}#(UbMfP^iFf3ihyHjRJ>f!9G&qs@OxR=cc09_;*dIHfe(AY90f63MQ!;-L#>Y;ait<tpF35bh!"
    "t6x10_cSx^8Su}gWz1PL8Qp-UP{>fb!5F@_0L*T*^qr)sUNFE8m$>Z2t{+AwTLO47#4s`(Cjy35&nqG5AySo*1cm_Q(>ph#Q"
    "-?Xf4k|`3OlKv^bsP#N&7ZpHLjfg&Ne9G!SQ3%u-Pi0+L`Qrub?BwGM=EO^@^GM-4BMkH_}e2bjqmK2}$zfmVGMjVPU`<FvU"
    "teZjWSR4>gqnH(8p7a_)324t_wE;5pd03`}~*)W>+vr@!~ftGJY!nckOQ4~#Nu*H;J1-NvP@B63ho$KB4Zs;d=b%bk9bzsCq"
    "iprMDS6Z{Y%>HnSIJ5U+p#Kdvn8adF7=l?{G&Ql07F~vxVqxe7_pZa33!7gFuZgJ@*W&mgFA&LEBL4<Rc2!|gcc?h6h!}d+i"
    "LNNTpotO>THH<<~-HMFYCP90UTMT^e$Sr3xMJaYje&RJ@eTN=ewQ`*R)SZ37^#Wtv#43jvwLQxOZzuplLr=z>Ry*j&Hf@PR^"
    "maUT!vst^NbTgGlS}LV$uq@7`1BRn-Oe2V*K|iixf8<_d9pQnSV~6x$&_>a6Ey}1nh2wwc#d}7=?h!<Gl)oTHvJuWD2DcXwn"
    "A!MX1N6xmxvVo>*`lyBN84isxGa@4x61QDEs!lm<iOsVY^!iDIR=x+$#9~qw)}iwAU^<zl+Aas`{O|No9mo!XRJxz23tHh2f"
    "iCWfd~_;vmX1ozD{L089eoL4B|3i`PD)#prX|YAad<9YRw=5YnT?ba(owHaV<2UBte`V$`fFezR10;$l%gmV6M|=%#f>Ongi"
    "}B5b+o;lef2;yxb;?}jHQSDA(fCLJiM@Pj{b=ofUc@_2ePP|djzLwJrq<*OF6gP+yK=j|FJZp_7Z{G8^?jTe-61J!hCKS1m<"
    "qWS7pbN<Lx^6GFCL}A52Xw4pXTcvT*#fm(NHj0lX`voLXhvU&{+Y|!|&5785PN0sN;7ub20Z5%v5#1q{q$E_p!?)NdbhQd60"
    "8(f?>?>FGz^rDvcwwi_t1BHaqp(6AGf@!U^7Kne^9f$?pAPzUAtD)_g$?`Xh&f-VPz+{HI=bK635PRzEnL(x+KjgiK<j#hnm"
    "yVJI3a~e5W!_qm9-kGnJ!oPu8C8qL%R$w`yzPMlG)sup{EIj$H~JCL=7I+lvs5iWBj?1ZE0C2_vQY0n|+KnIS%pl!Zx;}J$|"
    "p<`yBv908_F8q|xQ!_HF;a)dmmj(Z@1Yf#7iH8hHO!#9SyyWLh!Y$tRY0f#ka;xhXUfW8(!)z(iyXcaA^TZv#Sv95K^}a#)7"
    "h;+N1~sHSI&aD3M0jn$;it7Z`voHMKMj>$PQ$XQZNtAcN!!D0_9CxC3=nP}5-34xd~Rny$JdYfB0*-p{K@RG5yZc3Ws&w#7d"
    "qg@*Us0S7y>f%%%C`WnnHGONU&JL<-kcn%^La%x0z41p&58z*?jitaU%vHyMsYhu*_(XXXnWo0r5y;{2(}Oaw&GRlP^wv)*("
    "_YleMxK=^@5D35E<N?`Z<p`f2G6TmtBVSewKWDiQFr;{*&}q&4atP$pzf-*u?MT0Do0Q#2a#GAUa%gwJl><}di+qXCE0M)va"
    "@_H&STlUXMab%G$kq(p~W4p7p;&u9pg9J{UJNjsGX+6(}}1BU}uZ6=Je_QcgW4PO!Du#Md&M!L3VzU1m_RTwd(N}4DTD2WIF"
    "1|j7PuBBpOOiN4j}IV5gLvvBdNC?z0n|1;iZJ>4+s_=(WqjMTct=CI2c%e&{Jl@BX`nw_$0~OoPpH3T-90+L{w`GoMLOch~I"
    "iux5{cCb7LVNuqZ(PC7|dm8&bkl*Gom`s+!f4krg*xsPdjy0&0yhqn)Ic?*7Ram2M#zZ1l?=|-&kPhY<iW4z)r^hcNo;UQ|!"
    "d=IgOgDfW5B?_OJuWsx9P6sQx?c#$s6;Q9-`af#&V(_*CWc|@uS0j!El1COpyJp1abj9cgRimHr_?bL?pS{O12<aj^{baEke"
    "xuM;KWn@Lm<RC(Auz6v<DMFqg@WEPsv`EEn)+?&ZpqgA5Ax4dLE9fqhM%R1LKa>|YJNt@i6_VY_^{_+Gow8?TT(0Px^DKK8q"
    "J81*EpTe?yXvvx}<y*{O16_{(l8kCw^qJ`{AW62Rsveg>L&{oT9}jG8xwrOqgkw+#P6JN;uoZbkrrkeTMRVcj#B8jtlII04S"
    "@sI{|dUeVm_XfP?YK*%!?IGNy`fJb{SiCslZ)JcUqHCJc_gkG{@&2@-y4y?kEd=FS%K?Kg{5y<-+PZT6>Wiv(>kDZzO8F3JV"
    "AA|UY?0dB7<UK0*#AoFF|^P+(7L`f))Evp=m@<=3?d9OA&N>hD7?TiswS-h7b=%e1uWV!b30|3WmWbt)L3U*&P_7c}>hTJ1R"
    "_prF*3}kq2y;Z^spr`nwCCp<M+cLt}J;D_3zuPWbsCD}3r`S$>zlwmMR6Hxd6(HmD<405Af{B>-crYbn#7{{N{}GY1<M~K`k"
    "tD3_!R%6q(1(t$ui7waBTh{9Yo)B9k1R1v&Gc$DpWKTjiq!+CNqK<LBE$`CvH^`aBNeJ`m9z^{ST5s9>#{8``}+0ULM>iNOW"
    "dmJwB9~i1%pbD=tsIRP!`r>>5#MP{c%pvbQDi&ydWJ_nj$b?8u!6mc0VB<wiw6g@q=ZglXIvff{W6KC(-T~YcWU;FFl<|4j#"
    "p5!=J)NGA3-*XT#n?ClxENQ>+)y#=pD#Jm&p3sIf3nbRePa&)@HjZ%?`Wx7HX;B=}VY+IhzIXef%aT|z!-b-T#br+s^UuW^^"
    "T5SF+uu%&X7!Y|d!O|Hy_zbayd2X0Ws15j5{n!l*~j<wMssTVR<#)yeB#0<sc0667-tl)EJ<W(bCV{%L*kK-Z*Y!Re1Ks}`K"
    "O@_H-9eLxo<4)qb-0sHuzs<j)`qmto;G9A|&S(;Q5;{N`=W**hSICgof0+5&ia8EUBunVy%OsMYHkX)sZt}vzB96}fQdEOQM"
    "H+{x>EZh<&h~S`4*<9hu)O%BWTaD_fqFW(C!7l~r`7$3fEk+LVP;m-I^Li5_h(b<F~SgfBS8I(8yUWEGP6S`0O|P-TIP795<"
    "?EhOz6PhA9Zmx!n=%5Mermg2}iucG=L>d9;z+(T-J%^_uK3i4u3yAlc}l3!U$*!@AdNhrDz3b14F`Sz{SFa!=ULMM>c`~DA7"
    "yQQ}r$arkT7zhi_e!6YG8B&!p-ci9$L&!wo@dNr+Mvs>4l>l+#$DZDU<L%qyjVfTl?eV0gP4?5kP|wwxz~(Ak}Ru;-H?QpB8"
    "TaFsX>kCrG=e)~^ww#?6V)8_!)%z*zInbolH5O(Di_T!u!0QRXo)mS1894EL#W6|Uk@(pdm)!9hW8V8=Li3ir}qk?AK?RQ!R"
    "!X>E`^b^BZA$U(rEsT<6I}hGBHFXfO?*Q47ejbS0`0vVm-!`u&LpJHmO~}#p!JCVNr|sqS7U;{A;^a?tf9PP8)qP|>Gthx6K"
    "GkCAH0ZRxO$SXz6gc;nQHIZbk6C$4M)kkMUBHvC0MX6y>^=NiKLl+p-#xO)x6#u8@4hu;cs2o89cMY&2^B<ErLeg!^PT(@9T"
    "%>aUeN`6dqB-9#W~GG+XHUxjD-_@24VEIY#};?@7O-bTKCz1<b&RTBS9?JrwoVLhMa>+)}@hppJKFbx$F64z&RNs2+Ti7AF8"
    "BEv!vaZ!6co(mO0We_1mh|%*2uj^qT~>Gb9^}aF5OFss0S~lN=n&FY+pgnTTa_ZLYY=bH4Le2U-n}9{CW__J}j!AvXD-6e|<"
    "8TmW`#OpYp?xN${R5F~HZq9^i|UY%yF7&iAn6#7Zomx6?Q6W6QXPUIawz8bY;T~44qweaDCiv=I}8D_e%S3)FtU;2`z_VlQo"
    "pIHSj5yqcgS{M5P1d^bCa`^EubGG<Y0%U`Sk9C^KAlE<B0?4(DqY~QSdJk%tSkK*3ZSE|D2AANNq560l_6gV{{Px#+e3`wv6"
    "@-z>e>^NFc<;(?lShdZGAIKbucWOhqRM@n(i|R({!TG<<T_b0-;Mw|N*u5v8brF2%W8@r(2E^J!u8`MlcYr-SSa`!TcAxopj"
    "r+{%nq{41aQPpp$j$;JhC--!!eezU92PYeIE>D0Cn>C_*JTZxVHu~<{KtEyu=rIJ3&=wfkW8T5$VZV)cIAl(X6^W0tWom0_&"
    "$CYL8^>e8s2$%miMIkY;VxRUnP$UKSroX{AJ4`zPN}kZ@f)_l6m}2KWsHETz;gKdl77CrE_`fy9^WM9PyOXUqI`4I)I|V^n_"
    "^!+<odqf{v+2zs}FGR31~LvAua&fB~5=GMV*>Ax@rXl5icN1zn_c}Z^}ed`}y^Y#s`?C>6n<74Fu6cFON682(7r6V*sj0qk="
    "G*YjN{-ZXJ>+eRw!Nrjglx`MQRqXuE<IO%8WC?)Yxc)j;#AsKZ5)9*n7{2X}XHa={)lmUh>$BxI;Mk&~s+p)c`Poig%S(LI%"
    "*^zN@C5#%mwAr}7fQiA*9H|al|}PyhE|uo>ei<HQ{(Vm{^ulrT|PK`I>>;`&5M-pdF&?$kdWru$l;*W9GL$6XJLh9I)Gb^P;"
    "E5{=M`sH9^W6F!3jZUxT~cXoD75sCD!K{m3SpCNS+TKbyMy7Q+tk<m%3ZVzv}Bx5L5;9fd&NCeG<K~(ERv7d3)f)>K#{&hZ9"
    "A<5J10{B9dm~1tj0GOVp(tr|{O<2@h}zC}ei=w_pIUMZupaUmHKn83GGM)accQm=&qZEGPwgq$107B{S#%>eK;qm^AoKE<I|"
    "tTp>^A!`+E|t^Y!3I=Nr{2kS>?`!s)|f$s{7tXG-2b>;H5!aQiKcHJQEKcm*idBu7Z`Dw5PCRCU4q1WZNmHGDDV5K?BZR`(E"
    "AuZ&F8xx5=zIb)oQ}6QCtNwyAf%ByVs|<Z|x^dk~VRUx!qV_dHN1HiQz-8&lxY|_4p{nYh%&A&RKb?PDu8hkjkF5P2kPyWX7"
    "0F+gPGf>e4!Uw0(C7BXG~MJd-rQtQgjhZM3~XMmi7$8o4#lfvJ!tpAE<Lmm{3=Rn$pjQ)$5+_~KeBj7yl7(teFRqeVe2$?Vf"
    "xd&*IEi#xDb;O#7wIE<_622u`iiNKO^eAwzZQ;*5npOXWU4LtuX{Tm{zCw1#37XIBosZ8;Q8`f248F%qZC!dJa+SFWIVEtgq"
    "_jb7;8b$4`p88I%+J456rBF95m+F`T!4XL=DZ3>Hi|;?QT6y8Ss?hDGEh`k7l%zo|qH{jvHk7W~C`Hu0C{HlG8|9Y_0qw_`g"
    "hNt#Y)lPs)zaz5eUIoV~IzCte@qn_^;V8ifGU4Qph>L`nXBp9%wQ)niJnDe8Q#TmnBa1Hx)Oiq%PpKLzu?lcWAv?~yRo^X7n"
    "xA0!T#=)5g-whhf_VoxxW}6U+=BP9}7q-eEgNR)FP4$2G+3s;mU_Eb&SrRyF9*=MOcO))E`@4cN%KE?f*Fqc{AusVDSt!(PW"
    "_8zcmz1fuNz4fl2S$<vzTWWXIFQXSD!Q_St`U4^NEEXXoGsw4s^e|)xn~K>w&c83CR1u>HeNH*{Y=VB3UMoxf`{8MMk;v=O?"
    "&SaS})jGO)0?By4GFDIs;Fg?+(icrc7c<O1Cb8z(t$R6Et$>cx%UeO(d@GEu3iRGJjAG;yrVwvp?*lhux*UFg5ut5R<^Ro|F"
    "D`rUZavc3%VoFds&ff?f_$BkCqcw(IOEVSD^3^Qjj+%8N>PA$24cmFHKjKl#>K@F<;}QHjWuckZ%|W3Nd5Vq?j@l~MN(?Mb!"
    "wpCL6`4^wu8tLM{OVDq<lv)#P@t>Rfo-muGP3*ac&^8F05L1nFof0v0kyRQ|-1U$z+(U4#aEPZaq@eZj&%wgd&lR7NZ<EtS<"
    "fn_d<l`YceglbG>XBDDwaqah3A(K5^W|R(MAH^mZn-}dKmWr~@HZ9t*Ec|x}$K}eZ)K0_=M0YJXZhZ6sL&4H&Vw>o?A~iNG="
    "W{=4=<yK5sppi3dGIs$8w^8zIp}SM7<utAVQP4}xO@m8C#=d&Jw4M&PpP}X>IP=Sog9v$X!d9nDY9M%)$^FdUJaA#Gahp7p!"
    "cGT(0`-p`{@8hFz~Ygki$0{Rh<XtTi$oHjmoxDeFZ$y)Qx7^gNM@aKY*>+qMD-!*f^BVWC*;MKZM~bh->A`1xQ~CO$Q+&9^f"
    "SmktP269wlP0Z!}#qB0~Qwx2?sv6Zbxe5DM#*t|v8fL^YN0xZ!@;`;a07ZaS#b^f)qcv^_rzh-sFYT#c?BZ>L!N`Bp)PZ`7Q"
    "SG7T!Pe@-NdCQQ*`DZwUy0U}IpO7rbGFV*v5Eg(78v!Xlt^eI_~B4cii>H?UJ8g+w~jJR9w;J_yOiL-xY<-9viu-|~DKV5RS"
    "Y&l_UROHL9w=(}Ao$@X;MG(@HH!ckRDB#>P+}Z>}1x+;L;NPfBzVKN~NCM>J7ifgx!g)99l;F54ylTmX6kgDtuv9nIxHu#Z8"
    "Sxbm!xy92TDOH}i7{p|)3c|>x-`urB06{qvn&?ym^EHTl#*&9#E;k;M63(52U?6o*2=YW(Q6;vD5>OTm0HJp?*;Vv^71c}p`"
    "eh5<=n~IYV6-v@M+H{ecfU%>kR9dWH#Mg7NITruuBVVJj4+9!@g5k{3)x{NM?a;zGO;aY8Y+VPrbeHIGC4qrC5C-_+hnQ^~8"
    "&S?VZ_TI@yXb874VQTW8_#iQ}Ak<d+xk-!@lP#w6HV6UKK*d*CRxN(ju(5X}66$0AdC>=!-a`U-<Tkz|R>o)&Yn<8I08cQXC"
    "{Tc59isqqrP{Q1iy9VeUmtAr7AI2JTS*Pc<WmjXN0m%>%UI#d&@^Y>EpZ6M){Z<b$KM<v11?ahCubdTYkAGrMXk-JBU#|7c0"
    "80e~&7ZuJfs&536AS_tiWLD&H(=BRYNHZwRaQ$g|MHG_YBxcfywwyrMluZ}F-e?15X1C5h6HNB}CGYC@EyKQ--wh|8)s=Z?O"
    "#V+@iIYhKtn5{UkZ{<*YqvfoYSFb{J<$S&ctka>D76v+vCN)AoVaA6tZl^AZS$9t{(f<am0AJ<Loe;7n#k}7a(3sfZ)}YLo8"
    "R1i4j5q;deH)&Yi}6C0IDpvUkU+mBETHnOoT%)R^Cfd@kN2ER`Mx3vLXlB7>wKD=g-z5x*XX<HpyjS@?W^nyM5($dz-dUV>;"
    "oC(_HY{d(oA!FPYW7bv}4#+W4dS#HrtIcCCaxM@OpNTp!1a@rZrIgR`-ot0(tAq}J$!K+m|bE5q_<;Ge<-NM4de#HXi%-tFV"
    "EVgizrErYk5t7yYn2EzvsIfI4SpB0miZF4PAqN?Hgan)$!6l)3x6+Iz7{U~dSQo(e1azy-vek!W5VSK==w`Q<j&xl=NOLdLx"
    "t3D<??FLtakqjptNn4<Gt7;zQT4eX%EDV5@fcyJm^kF`C06<ry=A#hWCH)c6VU`iJnl|4#x?|@U4ubeooh!tS%_+vlP|M8}B"
    "Ri8%g%Rhsmz!({1zGFBP5wy&fz4NK2Nf8-`hd`HXZjVKILv{8R{kdCfEx8vux?=(z;JYoX)d$`TBfwUjYL_{{l}C+%n+SW1A"
    "^z>P00S&SvsmN&odmsbnrYGs-BIdCG<8}3f$;RD3QC5mKBjfzJc)yegd}=`p#+PW@E;%nk*7EiT#N1(+z&;W^q#gBv9wgw*R"
    "MyVtMK9RQ}7}^3$#>cJ?D%)|6z8rvW?!VC9_ji3oevV*N2R!~|>lyj<&}XbS#Dj36Ieml|`<j1xlx|N9KJ5CQBBxlF+E_eS{"
    "YbXcVukcf6Mj_uCVq^rnqsK}v8yoVnmB)(k!583cczfq{Iw6q$Y6&>O!pz762#CADkKi0%}L7*2;yjQIWt!^h;qFlfkPR}qX"
    "#;1sJhq^9E{sGWX?h32e$b_BQva&pRLhSY-{V~~n#2JY#+7nl!P)`;ph;OV{$vkW&(00m^BvRpgt7I!=gHOI8ClE&-*y8b!d"
    "G5cVn{;MKA&O{AUIF%N>0qf{9vqF~pZwmzEIW`uG-WBr!vKtfH^<rX%Tn7IVm8;8UsQl-Q)FiyNN%{X<Pd7OnB1mor{8K!Rg"
    "@zE;muB(aPz0)1I)kJzI-@jiBr~bWOI?#jnOMfBm~S=zl@|d%1gkP*kO3ek99_5Q{RZ)w;mEtF9VnM7HlAx7-D$#T!dX_l`m"
    "B`!R0}Kiy`hTpc~=LB4>T6;IJdA2Ma(I*1Rp0z&1Gr>&g1RXrFvz_>?J~5wVy`uG8)QA4-=M>39=_UQ-hl0a0KK-dO&a%lo("
    "FCDY{XND-BT991ugEEv&{x8p@{K`ED|LUB#8Ri;w@B#%0lh|x8=LRw9JnbO6vtdVk1i@n9Gsvsq11{HUEr-vjKLt<4f*Kb*X"
    "I(W2piiV$&OfkCK08^@_T7v*Vq%n6?N-$aZjYB<;S=d#8BZzApAjlf>=k$-i)e*kG)vf%Nwp9|IbAFd_rWY{S^Mu7%I$xDr5"
    "+EuWA^ekk0C}7nGXV9V@yZe92yQLL5tGqD3@HFuSHD07#$we087va}m+E@yb!mb+k;g$b@vw*t6?Zcxx*`9o=_=PPT>bOf2O"
    "b1`A~z%b`|<vW$It6s>u0aHMr&y%MIjGzd|p8<{K0$tr;!5X{9oT#wrq_+L-Y|uUeaaU_r+G;gF=W@84b&~`U^^(Fe<BNbO~"
    "cpTfkm<i7v22A2*%LaMoRGD_NshkC}*OLN!(4VGOq1|JsKQI)9k7?kL^L-t{s5Ty?Sg12@~1?PI6Q4bSm2{_Q&btp{$zr!ua"
    "+KhmtxVis8Xqgz1T=ifn|Q0@Su!8Q?%OV0>9ZWc_GW$z_3EM!Bzk03ZDgLf5}r)$qhags@2l}5C~@l0^THL|5PVzoAySe^=5"
    "_f8Kku=b~l942CMcW!{J)`MxNsQQ0Sv`6q&T12}rMkz+-SULs+;VU?6?&B@ca`5dW#M0rvPZ%DQk_ig6{0t3CTZ<MwcnG+6L"
    "^Os;votxbB*8>{kri8QV-ZPcvm<R^K^k@7kJZa-#MMA!JFdHF3xvlv0oB0^3v3neX(BJO_=%ci-#<<FpNZy|PDO<~#=x9dF8"
    "{(iEVbB&LG~uZk&1JM(vHRKg(b>c+h3h?YEk%dfp+Qn>biA0<N>hB>F>z(TD`4cq(3LYQY=%}@Y)X-x>u@1>m0D+HCZcQ_|t"
    "S-<p03Sjw$?)Fv1ytoVJSb&8W_^-~D)i#&NSm{M7R@dXbc|#E~rdb_?t|@8TZ?taa?E$-5~*ov<B^X&ja(LL7Rz$t=CFl0%^"
    "B35w}t(2M#ApMye61LU|s;T_8^kq#MGc|Cx05pSm#+AlTQd<ZoU-3hpw_;#RnHITaC-TS*I+Mxn5P4?vp2U`+>M{O7H+DCsX"
    "3QEN(-}UQ!!|uU6d<VGjGuf%IzjkHjz%2u)=q9oLIxPIv0z2~tg}W1Kq^Eta0=ORf(xRxQKgv_xLb@uy9Ve$s9(LIo3(jpEh"
    "TJ}r!Dc#!ALR}Xp61fgSfZHLElm%T^57h^#jUa#YTRS#AX$?`&4WF1CI|g~B1^pc^qx&M!3q6SS;?q~jBYf#2C_F)oXelD@$"
    "pkTNz&`1?l(p4$hGQ?J1*6Te^x>$;&Vu?;J-bSMEsrlxGu$ZCw6=0PAJN3hqot~3pdCIa^X*ynWoxq-*a-xPXMk$mrx7#k(h"
    ";8<)ps|8dl*;gpsjXC*ml5*9Qtpo4xrJSrm<%d_EUDkm4JL5%J51>X|^&M*}$q>!R&D?-a3J7pd>Eh|ac4RaJ}(%F$t;@IeP"
    "vJN1Ey>J}=V_t9`A!fro!9^;0OI}LWJGxkgJnSCH}``=e-Ksr4b#t~EY0ZQJ2F~R%;&eAic-CXwiMr$KQkmXA4v)T8@pHFY4"
    "ClF4gsI1j<8S|ORs1M&Jm^y>_l4+wAw+XbLsLzyc1oB&`2DT5bQS?M{JrPe`lI0jvyCUlK`*muGcU(9$3%&c5LFu$wOmVuE8"
    "O1#!|4h78M*~>6b}h&KR$#uyY*DYmy}zXkcvl=6t<})nhy~;R-?~op|K8j^dooMA|I{#`4y;(ThlxH2m-Mu?WvX({iGDr=b4"
    "ZZ%P{Afqq!A}!W@6%!wWntr`Ko@>Z|4h3mzj*<iwrdg1grUNPrDCsf=aS?Jlqh4fq*q#Uf`VaXwBLUZ{7(Ba{>hwakyizKtm"
    "CJW!!kLWK{>DWy_^%oz|LG2{4la>F6?&I2cq<LOgMPvG%zXi&;gAIatTRMbw6j+e~9#UjwqeF3H;c662m3FKj4}kQF18XJ~o"
    "qRyL66dq^1p2AMn9fjhy*0;}_IAu<cN<rD#h$(2b^S;buJNWidFJ<sz3noi?O24!0b$2)q|;<v4FCHU|Y(G2FpK5`SFx4-1e"
    "#|q6YJs#{(32>sMR6hdTyHkfU2o+GZ4O0VGfSp9OoZD&&ClxD|li`;hhcf<GA#K4NOY4`Cv!q|IcE)#$*DRA+L<!E?OLdtZh"
    "um8Nh4=5>{Y-qjVv*O{s-=e1W!k!Rn}k$6^%$1<i~#+ggB?_9s@+Qx+zDW;@|BD-EUipFam3op4!*B`@~oLRYdI_YGhjzAtd"
    "spsX~gUFAVfL_B^PfGkxdw99{JiXt#Ll`uIiaF?UDb(n0x;x`VhctRu00%UB|pNh3?M#_Yw6$fsNJ+v0o+yWC(LpMN;G1%;c"
    "71d;Hoz2Spydco<5K#pm?gm8h|ChOx)Cmyp~>gj*62S!Hib4bgXKI6pdP39;Bdz)I*Jo*JwuPp75VRy9P<Ty*LCT+-m;<r>K"
    "8JKTnI>CgVeI43@1b`1n|SDGd98ka_=X@z#7EILTktx8ab-Klm^Hy3t3!o6R&O!H&1mK7>?lUVA`>z2!(1_k`jk&GX{dH01e"
    "D&pT`Ags@?&QOn2o~OS^CBZK>9c~1#S)%WnAad=`-8b_%s<__Uqn2-t>8jIiQik)TUEn&G7w;qFEdcgKQmI3CG2h9Uq0D_q="
    "#Bd5^Vh0#1QE1eNW$3*z4Re0>0%p7v5xSS_V-T4!bI-vJDkDi>)4Z``LaBwI6o{udAUr$RM3e#4!zRkn5)qTO*Iyu@hu}<+d"
    "7P{?0D}DYOhpXi5u>s6+tlMW=mufzn)r&2i$e@L)8(5$~jvRQ}ka6K&Nk)iSdu=un)dwh!X*0{Ws4e!o#?i*qBb=SO&Ud81*"
    "YH^KZ2amEj@U2)Fc}NU5`YLk5%4P~zzhS1=&_Js33Sgv#pVbw1el>baL#FW^G@T@RmuS`B3A<~s?fHAQm_9cud_qb?-y61sm"
    "#TkQUSq-9$${d^Mk!f%Zfexr(A^V$dCK2dKQNvo>L7-=^e@x0h&Q^tHXe3KMj4EU`7kW!MWl*N<}v>P!hz=3)eqd%SkagfEd"
    "(Ypcc{sHCYH5=+%_$Kq+%2R)msi~1~_5h}tyeQSx3&OiGozO7<Wmt4v^}u!ejkDYPr0~BMS5qqlO?E@}{2L<6o<zQ{&0C@kV"
    "z6){e|V8{nmiO`>X{YRB-t?%&I!P&sB0DmH$HT;|0gfy>y60`LRWpMLI%`OgO~hJbae8={Ogo5Qj`VsdAKHM*OC0PcfdL1Cb"
    "@lzHYr_^%l)vB9LIN1pGhGsS%z^-y^sz*qL7lVaDt&E5gyDP&eJS#*W$>Rub^jo7nC8B*g#2D(1G9oh$%yYfvoPVe<(}QO>I"
    "vxgd6~Z1KY?8=)@7K`-r14U$nyn@>Pla$2jLtCAy}<<}ppku=Q@8>{H1AJYAbQxFn#N13%|j$|1W(xe!j=p%auM4q&G<)um~"
    "2h8vA`iEIo85e5q;-6)?OFGebfBsISG`%qzJMf!%@l>e2=Ex+G|ALWZWl3QS~>*ZI9{F$h{48(D=6{Qk#<kZ9G2qQrI%1ggn"
    "gvHfxWLVp}*h?js)$Ca(3Gd~niU;Jes#Rs?0Hf=UT{SOeWVVRSG?sOj4(k-XD7x~!nca(<o4~qCBR=m<0eN-d(Bsp%8ZndT+"
    "9OFTLI|U>xFAF=GSgZ&mpmrUs?Iro6Ig|<n7kSu8KxCZA;q-CrWgWNo(VVN%u0dEEt0EU88Y-Bm=G1mh3w|csgyDPcp(Seka"
    "6c8184dNcYih+fjaQzN423R)-3y<ZuJHJ-5lct{d<hYuj&ck)rtuPBj#H}`CfpUSbj!joF_OXi7LiJ;1;7JQg*mKDvS;vbO("
    "E)kWKF~g2^+T<^7qnQ`dGe6*!f-(il;(Lt@TeuQOR)!<P$_WD>Jo8FzyCRR$(+5C1rY_GtejJd~yM9bDq_((vuk?bg(LdR7v"
    "%WWk;1Ut^wr-Gz$_N7W+TirJ~dS$hvCDHEU4J^1GgyT=F)sQocG352AG*uHo&>lj^(JuHuMqM&_}z~ATb<4Tlfec8m-rs)$A"
    "KCo@`qbBkVcJfa@Ky6rfgnie!`LFweh8el84BmTTl4*Lms6mXxdjT$9X=l6=<9q+n%pqZC1`ch!Ze<#Qa((sQgEd^Dd{^KvW"
    "<osr1s}YiQ<I9-uk;fPNn`SP4=Jx+P`s}i>HP;wfq#E*h_W75u<zb?(QI1_oKHXM$#bE1%j<-_+8OJLMe6y)ixy^&bf41-FC"
    "^5sJ}C+q7I3r4tDBv9R%Z9!B=F}T)ZXxSd_+-p9t%PK6R(ekxEQau!s1|%`OKsfi&kXM&!&^ZueDn#*c_`lVrBaT<5s4*5;d"
    "V^)Rv1^ppN=|uk7FasV5RRb4d8Mno_Y0?%c41<=Y`Ilum<r<Hi56_m)vnw%;4*(9+#4-7VeS4Ba6h(nv{zbc51JcMhR+w}jF"
    "mjWBdKL(BnvfB*COd_QYFpJvTnJFb20J@>OGqG{R#&Q4T%tp-y-7N)Qq**A0Z780&j4xp0Tsz|bCOs7EfflOemC$P7n{M02Y"
    "T>98cMp@d5e=4HsOg#1N(-&UNJ#ifb=?2>j+@NhDg6LI&x2foT@xxQ`ozmkn>-dtt-yG_bpM$Vzr`;X#{Bcb!MO&v3ultQ3="
    "0T2AmceBAZr@WZECNc@+~d&4Z+C)U7<Itkcb5CKi>A@JXT~d)qdwJ<U3(n$S^`!x-VY$4v%Po93iFx_;m--t`O)_&ioT5^p0"
    "T^w>%A)yLw@p~%;Hn&50kpXst=K2mkPx}RG6)fB(;8ouf@ZO=w2;%;F9ZA^_(obpo?7`FigNl<`Wwa`K20gU|?KnG4U4?V;v"
    "01e{dXPB|^gJV<o^YR5rl*-gkV<ummS@+@<0wJ|IH`y8<jMV%4BVl|#E?BPVhy@8jnep)r{wHPYJMV*oY^83<LHdWjY`i=_5"
    "ilcTOXFNJM@;1r0G7sug$KRNQyi<(Cd90H|TQ{c7USD<SK-E{^Txfl1+I?)#C1)Zv9EK~2i(%%yjNR9JjMeHg@&JMtUw)l#A"
    "0?sq>(Wo+NEr__R+z`;}Psd-b(7>|15WaM#59X{kRSxfQ)!1Xm)d-;4yYeMXlxa)0%gtW++XG+H4`8bc1=H`0nf8UTE`~uIZ"
    "k?pzc!qFwiHVbk#R9u|&A(-QNY>Io$9Uu>?rs9jZo&lBrk~nCtpsb(E8O(GD}c{Kp7Cb%0IKXsj{oiUs$SindVX`o##cOgfK"
    "V-z+*c2PWDPMLj-c98v6cbx!zs!|v-jbgti;#(Mo)^^GR=))(y38#Y8V_TBhy#cI~9f*Ne9FO4glwl_1CObmC{aY6ke8sTj#"
    "R0=%kI=Qmaf<>=C+KziMzyzu=&`FjaP?`V7A*zoh#OVbc#smw$z4OsGivxp6;Hv1Eeu8>dJYK50AfVJFq5PD>a4RWGvPyM{t"
    "%cQhn7_m%hTeJ`@Y_)k{TqC&ycz~taXQ&%98OwHE;9%0jdyXcr4Uy5H@YlvNKgtpl7V=PK6Vr6zg2Y}wMwP*KJ%qnyU);?~6"
    "<ijx-25ND}6-*&QbZ}$nm#^D=`3+N7V{g`6dBn~p`br0~mpW~7+gH(pyxy;QJ~*|*#g+Sbwe;A=-Q}LXNvz0b3MEUPD|NV4;"
    "|}lHM(gZ4vPA<nLYO)3KgyXH_YX#U-PhAKdmY0H2zy!_u1nHd2`KL^tH7~~^p_Ro%Fg*?N+mO!t7MUvw>YHtCR*?y^U&3puH"
    "LL0ai#B}q3DwNi<vj_nm;aJbwc+y7u1TeRo5r5{ZTNkFV&`JUvSBe`0q=`oLX|o(CC2fT@E_bBBEmkOi&tl(kX|B(uV$kYl&"
    "+@H<mhy$2=BTAg*4*SE#?!erlD;Uy283?pp*)H4C_d1IUTQ<^SRQlY^<GOcasO)8YI1SSYe-#f9hTm=_4ZB4iU*K3r@;NT65"
    "_;U9PEZuf$9>IvRRx+Qi=_6R@`1jG-Vn|-+FRsw*Z)G1K7jf3hXNA^7k9^7#_Vz1wl8qC?!YJw3Dd-btV0mfZcbcW{Ue&$%4"
    "D;;IuEEN`zGwyPY@5)U^v5-dM4VafoL3zwcih>+v!>F1cfu4coc#7Q)4&CpiNuINKFKc%|*Y0vu-TH5-9$1`=cji`Dsy`yBW"
    "Az$(UwCS{=|AXccS?SpcWK~GzAr_C3<7}Oe@)PFRDEx27c44*Vk3e%iaG-S1-6@k-;*v<DaKag4`?0Fx*^DFEcnQmF@9&V!y"
    "c2{=uP3(;=ySte;0AC|1AuVQw1%0f0QWjwYTjKfp-8Bpw2Uol>7)aarn1_APA2`R9XS7v@ZUEwp)tunCbHM58}KpH{?JH6}j"
    "XHm~vaI03?VkTx}SWG!CPs%sND^fNj8c0vq@X2`=8YAYH+tRxHH#BPcBjy1!_Xf1`m}k%0$p7r23a283RP9aF1&4C*8W2|Ti"
    "9-Mptfw+3|FUOL%s?663?jNYQGS0!j6r|;3*FboVUso`q4LaJ%tysF&ba!OAz>u-&^CBej!O?I@Wx8@tUFLk4TmwCel^V6ev"
    "2fuKUkx`@uj}`ix2o%<!cFlGYRc2;tB#11cQ(nmt{8FI&gD36?yXmAxuN5<($tWaP^b<aGhYCDY)CBP7e~Wy$a*C7rOPumVz"
    "!Kqj2+pfv>z(MdpzpCUm-{KzQ=u18jA7a)P7^VDh&0iM`r5YyfAF+&C?jHE-^#&)SlbjvVCu!bMk=mFclQNr*ukbK)EZ;KR9"
    "EA?p~#RgK7b9pEKpUXVAG!>%n9|Q%-N$-tnbp35lWT&bw(9S`v8%<oGm_`=m}Xs(jf4K(_w#Tf++}j3$1A;Lyz#CTw6jfO$^"
    ")fNgkt&*Gtypa~di-RiCGK>@Vh4W=5=nA6$VQgKxQI_&mO|(a%k!+Gx(1(`_-`<L_(Q3zG1r&&`18)?c1{?UHy1MSEfPfBv="
    "`LvxebW3ocW3m&)n=1@m9D6;NyLNNyGBIaP+<$`bc=L78lYmqC)7g@p&G|1C#)(*U2SSn#A<Q#2i)_&2DA7$7XnL|D6$x6%s"
    "%lOdG7`@Gj993<Q%b?rt1od}XO#%HM8(nXz`|fN^W6wTw5xqkhcxYC6Bd^Eyj=rd?W#jV?idXkj)4io+sPbPXR8w3sx@Z!El"
    ")1acob=Ac1Qx;FZyfMUkfN+;TxD?wtWY9IxSOF89D`eR+D+&04BR>*G2{P8^BX64@A;sem_<BDP-^yuC|g5SaEHBK*Y4l5zi"
    "o^vk{`x2DLUkpTP8!}LF9eM=|Id_^ykOBFGSpqhh)TkG@=K?mC`6reaWbjqt(qj>)o-}cF%TYQG)ajoETDIFy$)PsUdC%kXT"
    "Wdv+hpxGB_7-*6-$mVse`;w6ULpk#TW7H-n#5=BW>2mGAg=P+zTmW`gDE4I*OtGl6=*xigm1d{xc=2gz(%W&^Rne^2Ug8J~9"
    "SYt$vG1#iE~27ZuU2bTj!tc8v;+{AQ*02=LBb8OQ`Hp;uV1jzl??Jb;+d*SLzfEv6&5Y5P|hpk?U#s`-7rjwk-A7PI42O6g5"
    "(``oT13`=<9!#CtQh%n0>CqMx{oF>~rbe>W7bK|lOAUw7<KMCe9V`+8d@;KP7vh8{vAmH~bxGoPx<4X_Ov|sjnJ>PPVTGxA7"
    "2AxViT+JP;oSt%r;rSR#+{+l{(KYM-w#YMZ|PGcOpH)HkHvW{mtLZo*8kjakBq1=8Z0j@b-y7UamI?V>DPZ29*?iz>LQj%8V"
    "=q961jcO_j1*v+HRg2SiTI?CX2mxw_KmqtF`-yaJ%l2wmI5mAY2$0C<|Q>;N~Lr9vbKnHXH1{sF8nsPeHsEdg{gqL3m|BMXW"
    "A`H%!wV3Qp4Uak165kgK0b!+jX_7q=ruzUA(utPMq0CR2nV3Psb89C&8Rl!8M@WsUxpqSrp&dyuYdcZ6s6!c_#E7`Bio8!l;"
    "hJ;`oGM11B_!7Kk!EDuE`>I`CIr5!8Mj(*OMZ_(p^^aSgfC5RSUdVy+CjWm+yo}`0Rj`@qK9<`@Fi2t;H3FS$c|3bR0h1xw?"
    "?A5iUaP+PWcGrFYzT-;wokv`=-_vVWXXg-6-tgNABDAK+W^myy7`D>=O+r4~(xmI0!EH7wdrwH0K@5;t@pke2k|!Fwo9KgaK"
    "O-@fpRwqhP<tL#7dez#G`KflRZim!lbrqsi5bkd(Bg(p?IhD5uCXZyk4nGpxSN7(N5-y^nGN)C9y+GDHL<p0FdS&&=Tu0;ag"
    "h&IQ2aiQ4`w3Izo)Ok0i=QSVJ|%jYi>BtonUlX!>#<`&I>ooVi>U9SYP!8eRk^B7#ZwI4qGh|67lz<%vt>=kMe+ros@z?1h?"
    "1v4lS<E_oaE%f3H=9XAm@AQ*dXRM<FXSQkfLqB%sIGG=YXP0PM=Ydg<J@3x8h#PrR}2xL%b4yb!$nX}W(sruz>{J<K5xnxC|"
    "KxTr=-R_j7k=m?u8v@TD(f2lUVAHY{YD>cU>r)BNF@Y`Auap-3#I8TXGw*YKmQrWY~SY78be`iC6B3eJCX_QG|apy(SO)=v6"
    "Zw+0zEH0k;SpW_~1a30(h`Wynv%=^y5Mxgkkv{Uqc(KBi?n<Y_#*-s`VTvq@YsZ()@5E@!hNbx3ggbud7Oe8rQ`8_26Z_$<c"
    "(?`8JIFu4<Z(nxIh+#OYb9_`Ku>HSH98l)-OHh1iZxjk!`yLq&s#Z593j9OCzxpPq}i?!AU$cmV!PdF^&q<b)bed{pd@FNxE"
    "g+!%|{NG%2bYm)UB`CPK{*@#D$0AZEK^psEB9c+{;ZF37&dW^ZQ!adY^d<AYj+YY{L*-@DZ8V5KI42^o~gb@yFT)`WA}pOvC"
    "tKqK!o$+3ndXxxlMD|7+G*GSKlD^c$e=Rd<}5UO_-n<mXjje>9?|oM<SW1TmA08;Ugghszm;v)*nCk?+oMo@vj94B$#~>du1"
    "rpm`>3zNoZM8;Qp!=p}`mp+E98WHtDXg@k!1O`Vn^WlcI8izE^J+uDO%A5Wb+L#^A8laSy4^zrt%Lwv}FvRNL*+^GVi&DE0U"
    "iTooX6$tiJ{8uY1OKU_T$)U8Vm4zXqNCLb^MK0E>eGDB~&NA2zmg<{i7OGPufncYe1WiEVDJ3haAL@@|4w^gLh$)_+a~OC*B"
    "x9COpRG_@yxmS`kL*8)OPoRFs*UHnjNIss^;=O|s)e~~1G}`{)6d{Vc)~5#q`MFv>g{RXq$u4umVb7$e5pn|FTlOnX}OTkO4"
    "VeW+d==$z_&%2n|01sGI{#XzCKl?=zvVbApT!YQa7UFect5Cr(GZ~mVmlr@2a2Vy?;{W>TJxt<WQ~g^g2I<j_YH)SrXt#ewJ"
    "C#&K&2p3T~w$1^DB0+BR~mqvG5j&Fe$0w*%>R<&6dVIO&rC+9jV|p@g5MU+2i=OL)I>Fu)Gl*20ISN$M%l#~x1`S)PUcW)ZD"
    ">tH08Y6>@)%Jv!58!b|CUUbygPIf1bC`Yl7~*g8iNbLJcFZ-zn4H+C-!nke|C`zoi(?6=ZVXDKqe9%c0z&)tC?tHx_1lC*V4"
    "XCG9M^N9Ic;mxLb80$4pSc?s7Z%;?|?O-_J2e9{ip$6mY<Mbc#m^ANzu0kVIl#zGgr^Tlr_**5#r{p~KK#%xWP}+wtQauq&4"
    "!50{Yo``QK^sQ3WAN=VI0NB`%Wbx7t*{6Zs*ILsx3@pCPa-(}EC_OkvSlxw9d4Ltw*cViWaXLy*gHpi|2CTA`G*zd2K!$#vF"
    "xj)Pd55)Yc^KAc9Ed8M^k(5h%_{t>3dacOH2rprV<bP>uSpr6Tt@37~E$<TkWuZ)2Jg1y&;mCZ97^ULbtRFF@=`*g^4I|s>p"
    "fT%->Z%TbXNhU!r?ymrT~0f8`>UThAbH&EWNH5!`zn*en+cCE%fdH^jp@M|UdT^~i<>k!3nnu0cVKoGqOYO|Fb`dx`w%jJI?"
    "zRlPAHc7qlbvgHO+*?FWdT$fu+=l<`$c{zRkL4Me$1judK@?kw93H2`{%>j2~vA@m1B!wmLYp#a{q#&Uc+_EqMn7vWF5UqRo"
    "i@>=eXrbzJfutW;FuLATrP=jvcpu%CW{+=R2Z;dew#8UKv7xwFvqy<_zt2s<+q@I0r)hA*cp+<A7y%hCMKF~(o}o7~g)FDrC"
    "7ym|woKdTan$^)n4_b8coaC{m|E|SZmbb~`)W5(KlZMOqtvKmNYtN>8p4(!M9jb?111O+f^YzfwLj4yHVqp)gG5hP>uRxv^w"
    "+-HLA7so0q|gM0mkJ_!FS;=P|jQt#PNayoO~nHdPETb5x$w2j#G`Ynh0wxB?%+L+wz41m1738drvIbJQ0ABH%#(?c*Sc8uN="
    "uGh}hd&tZ#p6(Z4F8b>q`(tVOP-N3~%dC;vXP{K-~E$Jm)07We|HC4cM7&#S@cmqc*^Za#Jf=R@#tqR^(~j0d0EI5l`xn`?_"
    ";yDvve0q1;8P)53-;1K}*@E@~N><hGVwA0NGmnA_qZ8sK0TT)$ZCkn9g;eVMM;Xmd!hL+c08PAG(3rps}Xthyv03(cSk$xJA"
    "Idr*>$Onm!hE5{{Xc9~?+qqDECxfxD2Be^&HGZ^Gl;Fvc5=-j;75WJY)nCBtTs`BjSy+btbv85}xP=e9L7#av7m(IR+j3;hO"
    "lazLQR?*N*f~&;dao_IQ*>Yyif&SZoWE!VCNd_b0#^Y{>tDl-)f(W&ro=NTtswlIjB?oD-qzwGZ>hpr#-ZQp?o=+ICEkl0y)"
    "@q<DjE3~Z~DftFk-SkU~wuSpPv5!pg2}@eqkam%~dI0zf~K4tF9EpnM|7~<690Jq;Bz)%un^2nCj>7onU`l^Cc${lMs=D!2+"
    "jPXf*(lX)5UN87e~lJ3}8M?Cq}&LYHRIxc1sa37i&Vm`<!R<(ZyT+lS!fpm0uVc!Mi+rdvW4EyIhDEEvgp2}7eW6!=a!3F!g"
    "~EDAruNdBg`?i&sd?H_AmADx}-GLMyC5?4+Y_<vQ$bmDMg^+Mck=hho@krep1OhsR=YJU=)t5HyhF!hrf9(J)FA>qnOcheno"
    "EvBX7O8CGhizN_-e~vB&^0K<4uJ3*7^TJQ`e&zbRmp6;=uQ?|5{AV&2hivbd@Brd_izv>kWN3ZCr>y;cxUyYT2;Rg{vk@4q="
    "BG+;L`E$@D6$q&EtX0^c~+jy?I}7Xx+nQy7VP0~a-xIxeK$8Jg;mh^4vxL~#_^lbzoJL6_)qi_h%lDoLGm{qy%{SoYf2K$LH"
    "IF!amdZ#90)#44{7}#g?KpTBgnOWd>XHC5PeF{Q325)R2GwnPIsIeCx3($00zw9+!HmyKb0!|Z(fZb*w8kAqsiHH8IybC{<!"
    "aBn2A@<IWg5ll5DONY%l;o$+Z^2=C{x(9{{I$TN(tTiKl@9GyO^gR-`YKs}h}5mOwp^F)-$@LifY}Q>gSX+!P!1iTrDwy&st"
    "=Gn{Znum!xF&)$=`MGXT2z#As<)JzGBQ5sHZ111~|EeL$?s>+`|XrZ+})W&Zal#KrFt&n=k-#MAO|C4h5cfRo+EVPHWhg29v"
    "j<GYPi5$1J#&9JJ05gfmZiqTAGE~?0O9ns%S5{+Bg1Y)Ce1{ql)qA5r+`_U_uiq0Ojpw>fxN!B7uv=7+{m(6}57wy*Kdi!zA"
    "O!`U_+cYWb8V@TazPka7m~Nsz2Sb~1b%uQ<nVO)JB&jb(U=)`om9b4k(kxI=wR}z;-3iLCgqJT$JO>dF`a+@4*1KyiQXZ8yX"
    "zL~3yb>+$l*Yf=53_1;Oj04><vB2kW>j&gvp~H!RBN)ZZ0CLb=Z44@kJDQ2IFG<`)TAudN3de4hci`#+Li9FcJP0VK{lRWZZ"
    "asV3yrn2+yk>iDDS2V`*6v&7GxQDeV((!BMFL(q>>9i3OlZr_P!}63X-tx3450IGr}ymP`jY4WKqZdm>X6|GD0N*#BH_kCdc"
    "@+rOT5od!vmYhgLkPXy)@QSnt0Zt-K`*i!{<9*y6t=^*RHQ!+yujL%g=F7~)NyP`pG06CcUDYwYK=owy){eOF;1}00jMrJgB"
    "EW<_Gci7@lq)H9?<fQ?a$a@_`PZga1>BJ|}=tKX{bXF+gH}2ZZ%sMT+(;vG*V-IT|21oY9`2LD99_By&*!CuFKKre7#77z<G"
    "bHg0*td9y<_LT+%5ZR~^sE__fcm!*WL)W<um-~M3>b%>>!7^~mZPhV4v#i3=Op>ZNzmLfCl==Dzg>&-PQ`p06pFR_a(XC$)|"
    "Z&XR1GZ|Lrttzxy?cH5{vahksgNkyu-*DdB+8tr)Onw`)`_%|C{Fbyv<7=tV&Xfp(iUcQ=zDIYpQn>RwH%*dWTyO%`^-_>}y"
    "vKF84PBr`aJjc}PLo!zwrBoPS4?{UaO}YCPxRadB7+w)Za6$V9qmIXi{x!jb|()~{0)dgF&QVhtGI*qruj5H<q1FQEBn9~z%"
    "{Uce0fzaS;}bC&=#iLfs2*%=EQm7C<>FeLbLb>;FFaqtlqB`2YvHqp*jKG*TjPG5xeHuU$!w(89W&)+R%{cj7>J}`x(-7(Vs"
    "r#s`a1ugiGh0>?~gu~h>hz?XH37^A-MB07Z+#gFdgGn*T%n$xD@fpVd&~!RE0I)`~-(Mn!TG$vir_DoxgM8Zp8|qBWWslJ~$"
    "hN!_TZjd>&E`Zn?LYRiZXcQW{|)U6s>AHAX}f;g&kHjeesUYhfWvt};?j+Ko1kY#H7brF$cb^dXZ_!joc}it9J3u`stLFxhc"
    "{f>pw%RDGl_jgIgm<!S&XxQ+#U5>pZ9C^-;&b5M{BwYwttO^uCb<B!u^eVq-gcUfU=DllM`G&O3=z*9DEnvP4Q2!Bs>hiX<Y"
    "$1au`db4n>3<gVaL<xY7}INZmx3_<#L*@IM?9j2k8-i|y%V2Yht)Meq&lR*<HlI9g=0gjTnv?up6#HD5KX>!?NSzx!wy$|K5"
    "EIJ_Avqd9i49W1l8a7)XZ3Pc=)l-vM_|ITRP^2Y4%uteL2u-TJ8BsB5O+1*;d-sk;2`peoJo`1hU{~if`0LjM_%^%da3IF$_"
    "zfVR~);EapFUUCO|DC@Sj;ru<3gG{h$N&HQe|u)A2Hh#URkqJZIS6xhdT#s$k*Upz5LKp=17~F}Y+qmA@fxHe41L(zvB~vMJ"
    "(>SdYd6dMS%n@uW?<`z_WVvH^Xpe|L$!>*zi9n$R^xfmeN%Kav>%VvW?cb>C&RLYCbXm&<dhA3LaTLkTt%8pzkj{&lp=4lGy"
    "0x2SL(6r!^_M2!++v#>PFAhyLfwP>24>NW7qG`S#vwRdjPzDqa$gU)JEA=-#E1i%~f{l-Z+;k#M92m-?!nHcB;JOkq*?c1FC"
    "V+I|QOM^YXrZm^pXpDvXa=6lg%m+%*Kd3LY*tRBkT~99V!yQi2z88!A&%Q|Fh3A4%wOq6$H60gqQ*z|lTOmHcbM&RhuhtXlc"
    "nbkp=w$kWqgpixB5XO}jPk0KD8j_mOHD7zcrd}5xMqG(72CZ(K-2{}dJ!&!xMAfcIGodeCxns)0AM3`<_9Ba>=BqStc`YFdE"
    "K6Xz|Ufx=`=;N!aC?6w?oAC@4x$BI}_~K4;FE4$k!qpCS@kidZdE(v-n;fQHf5oy7fm&MA{pV#*>K$vdt_^D1Ys7p36Z2aBa"
    "boI^I*%WVZ{+a4lQ*oqtz(2%*xnqkEIU2B*e~Ie_T5!CM3>{1onH%XmZp@-sjS%ZCLgo)JAC+>u(y+4XLa;Ge6>_Vw#oLGQ?"
    "$3|@jm3#YB{VQ?N{Yr>Az96@3V?D?DP{fOCkwr5McN`5JMPK+hArpt6<b*GfrVSSs;6!zjt`J<@@0aQmnMJv}Tf`E?cp`4uQ"
    "q%5!i}$&Sd&zR!v^@BTJzw;N|(<RZXDiSzDU1Yt$t#wKL+>R)yPZR5}AH_ukCapI`aAwr>^l+8)kF&*Gf@q}kj4M6>ksjEh*"
    "#)FZuG5w2fI#1CHttf<#dgw@FFkE$JnPcFSW;!%>WsVTKzpLH&~8<8%|LP(4Ut|8?crC(l?dOX;9C*vDd<2J7D54Bp4rdqb1"
    "@GrZB>>eEr491b#H+E<T=fo+qx4>_1Zf;SB3=R&?R~6onLpm^w0`S3$>N8?jj@tLgYdkC5GJzg3iN|O8zOPd31HmG*Gh)L$v"
    "?G~C*ELm|U=e`!eXNjprZ!Y&q@;E>YBhWIa@B9`ewC*4BKw4R|H5rtl>aPeVzS0I-{m`!VRJRv!NpLPh}hk*dUR=y56V)bW0"
    "EDm^;Mit<IK&`QWGgq>FRmE8w}!i$ZJa^#6y+${#A(@RX4d1;VgQRgm%;3RalFJp0ZBkpQyeP75<FzJECeRFxUDO=*@6K$bM"
    "IqX84r1-AF}kge}psEl130jwTYQnEl8&61zOe`Me7SU9>;gP21B?Ob|dF*M|9_7aJQElH}DmPd`*+mbdz{oxM(FC;ST?f25="
    "yldiyJ%C8OcT_~GDaGs7&o_-0;Iz`&ggZPAmg$E9Qe*=4$ed2Av#0N<XRs7;Q^sIzOY$b3H_|Be<Tdh7{GUH_58R!3aU`E(="
    "-`2%4p7bl@R|*I_TR5AiWkJ`qK}!bN8Jvs+F#~s!T{%=9)SPr>C4!tQ+fE|P&Nnvox+qs|^xvZvrfPlFa0*002{dSOB5$GFo"
    "YgZMzzjGI`H^kxwGlRD;yDyg&bJni7bYdy>X}rp8ivbMu&BBK7K;T1Av>2s9?Kj@Tb{ELJF$iv#*dm;YMMj*8Ryi?Vjc*=on"
    "4GKQ?5f4x`1RYxpI4n`_dh7;L|uXiX-4GW-yb_z8{sNUBkoiV6QY6&wj3o=^(x`x9b2R&z8`tJ430}yr{C9V4pEL3ACNa|A@"
    "#mU+%bnf+?yZ*I*(VD#w(+*C9P_ZE0DUAKITWBmWC;_wni(W4pFHmp$f9G?D#&Tc>S|u++r5SI;j=YOj@*T|TjuCZgArjuJr"
    "p9#?Q10v`nmQ^OLp8Z7L(@aCjOLOy@S7J)uo+%E5kMPv(q?A*5cA#n9@G48em(!3qal5lD}dUJM>3pF;KUR^bn<TB+okHW#5"
    "SvOgQKY~HS#F;TqGNn~AXR2n<tD2M4XgKA7o^$-^qkO7upPR8Q7jWS_ok;-zd(#%<k3(=$%W;eDUCsswmC^SOCb1};{q|xwI"
    "vE2`O2r?`n~xfotZY<zNzhex$vj3)lj+o(h^D-mB!StKKksKs#lqD6{@|W}bZS47JNrSCFk>t%?6Mw|F8q-la(`c}8InU&3?"
    "ErP7jCxIiooH3tkbLLMJba^RWz=rl^j&c!C}*(v*v;7e7mY!f17sycq*u|#6VX(A}e*TJC4St=NJaERaeJsNSfF0(5=#^E?~"
    "82P^i;S7Nq-u8<``>*FDcv8Z?=9km^pp!VQ9tbahmArUW{E)4bP`F(?~F2lO2&=9Xf*rp$^v_@hutCkK&v#8><*f9$wlIZ0J"
    "wAc=(T%8OTIdNz2S5x*VJ=@_(35PdCLwwp15Un_I_)c>}}JEd*#@|WHbTeceMNN~GFUwDP!$uz?F1w4~w8As8M9MeRvl4;oa"
    "Wzp5FfEqDgnL3!u*aPRfR=Xwi1tr!Gzm2D^m6K20=H#fabQ4mnX$ePZ0`^bV7_C817&S#yMc4Q_r4a0fs;m!^{1P(cxldmq0"
    "@6oD-oT1+-oTU9j@t`ysN2J#jW|zlj@#Eaj(@}|N4$=9Lj|3ZPt_mRk;Ky#o}@4%>kIZUQ6<TPe3~y6JFI@pCeM|2@#YFqkY"
    "JGsxhot8g+WK!p^qoI&2vheB`37qER_MpQO9r{RkkM9S2Rs)ot>S?H;juX<ub_7{-xFHH|Ox_3U5ljG){VJ-cOsUpma!=9w{"
    "W|OCsC4%{Js8K_N9zlCCSGE;<fVHWX+-uDS?Ue(mJS-d+vPY9EK-)k7FtyAVXeRMn?f{VKNd&JKkG6V(Z*3oGjd$U}XAoXF6"
    "T#|br+bu#z`@czi}V&*EUhn@H)aq%is-G4Sq(5=?vKo`RP#%WpL1CG*d;Hc56<^@-9g80)jX|T|PoL-@`ykl04E^91foTqm$"
    "m;(kY-L6*pA2`ynx@#GspzcEMuz`+>xr81dh~U)O-qOL+R1th2M1?|c=6ZWPm*YnICO?x3fku+TN2x_}hma2_UJWU9J(3jdq"
    "J5~eiJR#7kggTM4L{)~xyk8cqwDi=qUg(6g^h}+md~zk@|VO6G4~B9i`iW?6@~917pqCDb|VZ)%ruV*%8AmPx73Q;<4V;{4b"
    "Z=46{*rcv}tmv6w*eo6s{4dlUrC)`|*8pfg}^>?nm3KvM(@|*UIxDIdBlQ+%yg|H8~~{${6v-Y4L0?>bg_2Y?pDj;CwGz$bD"
    "Uc{}>fDu*p3XNf|7J_V|gRC+w*rB8@`9r+oLf>@e!OOzx1%`e%6xZ1?Kqfi#eyzg{$;m>RvS`RWr%KD=G=aOsiQZ4ahe^QQd"
    "3WUj+yC`;fOVIY@9b+KmwA~~}e3^oD#taqio^fSn7Al2X@pLh)k(+6CrI{Rq-Y~XQKFLa|pz-TF)_GSr-L#d%IKy(EozT0@C"
    "rTB@EAl{u?3E2j0+TH3w^>7an0uJS&ngfTb1NcP%$R}nU%jGLc-Lmt*D^*@~@X!Pj<E8g(h0fGlxebl|o0BeRfHc@jB2Eg0u"
    "GLd%FQ1WN`2e=D6BMu(#aQ`hHS(#Jss=Fvo~_VEU>Vfw_-1)6thBb5d1QpR*iW;IP#3=Jg1yunwMlmN`u&7zwBBM)C+^Ie4l"
    "d+A7}Vi26p8?NU3IG!x`fHJcqxJ!DipXqBW1}&_b_?OvYZy4Yu^#5bCarJ8mXMdo`OnWDbt_j_e*dmt5B#BdJ*`P;6f(<&_n"
    "s~$q%W*w`6s1-@oj}(W0^gv_7*WPlw>wEM5{2N`EEV9>=bnOxhPJ3V(H@s{a9NwTnBQ$(mJlzeBz3R15!CRj(qG)n1I*!|O0"
    ";R2gmba!DneE+EVN(#jTk5ctS3aXZ$iy5(v$%s~AGan_qeX!s<_AZ&M|5J}B8Zr0U@Q?a|)V*!;a)4ry|^Yylw$FIwJ9mVzD"
    ";}VMl@t-sn>81}ANrmwz;54(rnt&@7?<7V7%IP2q9<Q5~kEEF5548>qMedrxAlKh>Nc51qig**`Or_y`R)WjkmIF}Rv#trdZ"
    "e@RZ!IX_%lJYxc)y_=#({doKh;od8)tpfwJmuqh9CxP>prQY3*3fdt!gkmZ13<4-$f7ABZ!c^HyMPRNSAeO-h8h!liamb=gS"
    "EeQ2uX3)Oo9&Ge33ULWFq2y&h0az3D>!4rkl9^<m2Oe)qFK)1U`G}6MqP4|Ljiw1Ema9+KRMsP|fnC_eQsC2zc{GNs^4dYJ#"
    "Qobb2YPQ&o@yzronC5|ek-yJC0b`1C@vJT6U(YWKdlQx*JXZ-4*Gg}MxEHEuMeaSa?2Mh~xTt=dK)?|4>vs6{Vs&;hEz>Sq|"
    "QWSzu3o0wl(A7^!<4WG^7NFD5;iK2035SY`a#EJj5G}(3Qr{sl>;A~^#o6eN!*qlR9TbofLX<KXQ{_5v*qZRec8q^yIPbKQa"
    "h$g5D>9P?U>{0BDJ3GD~niA1EBw2hkbN~9Vr_8yO1#RX-rKR4E^jeChgm_>|a^@G4ZCAmwyYaw)xANM*9?+e=q*XhhHq15X0"
    "4p^j+H`-&bS}=t_Rp_n<DfjGP>L)RZz0+ZTIGG=7E;Zu{NO6PX^SY3uIJGr-6bp3!orNpU`Hvt)Adm+I!&3QW2P*1;hk$G{p"
    "ddF+O1rOag9z^+kQ~OtRWtO(0el=adRa(m|FVSFG@x#5hv)Fh6!dS@9VL(HrjW!;%jWv09KBJ@?*1V+yG)+JJaO6GSuLWt1E"
    "CyJc9$D0EIT$W$x2n?w<tcZNflx(<(EIjmTL)t{fX(m*#O!=*Vz^Zz5K!L`|pqKwQ_d=+ueh?S*#P48>KCVX-Ii)8lEK?&6I"
    "$9+8${#Hn`#R2MZRr_c2u&6hB&>Fd65jG%`~!wH6wao@;X1cgr-J*0a&EIuBilae6=iPA5z<^z5=1%M&LdQ>+N!2Q|U1o?cV"
    "Am1L)H%FQI-l*7GJ5!<InM{g4-EN+%_Vz+2S&f@D>=v&iPwQTp+X=hg(SXs>A&O;BX9<BKb!rQmeB_Kxc7LXGpT3LGp9AvV6"
    "b!Yq^it4oSVM%AlI|xH0`MBbow&5vQ<Z#c;Q6ma!mCT{R%*jLr`#$c7xlcpZsspvTR7*Rp2;5-PPJ~_L0lj2wSmLRvjLR;mq"
    "0)0{aTv121~E_*_1K|aVvMwV!YE;q#Z}U)s3i98C%m&s~hqC8)ngiAs_L=Wa*SfHin5*`)|M<>{Y#m*E*`n2lk^(h`saFB4#"
    ")Hk%nm*6unAyW%ou-%RM*o7U_1M@ByVk&zgXyM^YE0g^}Q?TLYvI!g!o2i98KUd||RY<_tu*0TSRd?W{Q~g7njyQ;`mLDmLH"
    "wwpBX4yfG-yTD>G>$+^p9_2bBbx??mRfz@6Kcd}5D!C?VB21(Fr!2MAfU-DN@NsqmhDOI}Zsjw!c;CZXyco1up5~O6V{QHrW"
    "<M%IA;u)s|SEN9xw=)3+p$V1^`xPSe-^oRjE?GOC2~m+oZ013w_So@|_|w^Zs8v`BV<-sgmDXNsI6lX7EGJ&oEj1>cTymIsV"
    "}USlr7{<OWr-Y^!wgP#Xea?pgbkhwrfA`XUVP4aHIA~qz*L%uyq4s8bncZ>_Hw7_1xRJI>tite)^E`9%~a<U@by4OOr!bBgW"
    "AiVqbKtfnQ*R8);I!fMpM}ybYUc{*AymVm_L*}>EcXX-Z38rcS1MCpEmo2O6w2Ttd^fsyzm^X#6`3Q9;JTGcqOS2F{T0e>U<"
    "U(1!9SvJSD-3t%yr99H8!*D?!UJD@dz&3ZS{>T)g&mtW8#YyPTPOgnax=>OTKkVZ2a@S>B%@titNs@BJ_9^c(FLzmfu>k89B"
    "EUPn`0Qyv}3t|^ZIQCKNDWr&ql@sSy3lEH21`Jsxe1_-eiC8f-UzrB5`MP-|>H_Jym*RS1Q?4>?mPM{Ctf|GAWxPL(jJ)<1`"
    "l?#uBqhbpnj;D?bu6o?JE|h}N_T%@b*VEP^h-yCVMOAN`{B(TBDI&s}oCcp_SwVX$<Bw5OI27};nGWN#Bj-ThS(DAmnodKCX"
    "}vCpPDm)5osmyVnd@9J<7E$em_*h-cLambHxBDUI!0b8rj6asir8y#8Lc+UNXnB|VBeCeju-Gi&C_p)2P;k}O=$yAGvuQ@Z#"
    "2uLx3+gz<cIdXW+%tj>1{;Qva9l}sGd-p=TYYE!+vFrQdoHF_(t<;dGmpK7^8FYsk3$~15j!Fw3Ee~=~)uFN~Ek!xx>krzyn"
    "?1-`_3$-!V7DxH`rNUWG2X2&_fCeu$N&BYQ^_p5at+uPOxBd|0n+<qW;5LDHqsY10}%G};Tx+qY-7{zM{CDVbO?T0Y{~{%}4"
    "zYfB**#W;>sVW1uy9{ov=Z!F4Hw`MrCyk7j{s`pNRyYERy(>~}dNnK3vgUXEVk6xh^pGh#{lhRqfQY$0l8MR$3<ue;c6qTN#"
    "(3S=0j5u<Sq)1F7Tq=cJlp9JEURPJ`KqPn^eu}3)%2ylhWxUd(E~BkVk)G`>*@?`viGr}qBAL2R%4(ZP%}8-qT^-D;ldai^-"
    "y8f+#cPGNW~MV`S!pWk0;<sC>7IL4e9!JYs=G`9-oI-4>YB@vy=gUHVHk;`DzNG{oeM3qNfo@>y|Jr*YSL7Q$RuDh?C1Ytk!"
    "~A;|BRV7x&EsH7h@9dTlXs}>6IYmnw&`;Gb#67(FP?w-=alzir>F?>F_%H6Xgi%xL%yz9&o+*$*-PufEjq(7j=rFGZ&g(v5v"
    "z>MZ<E|-Q6vN-2TiOK>IaE*GEeXI8+oY78ajC#W^r0Cewy2M;9&Q{!VYjkn^_?urPX}NWROauusqD9zs%<-Z+p?A*DhB=<ip"
    "CS<5!+wKq0rsttfBLGvsQ8p7Je!81IHx#ebB)(GX?-Qv&-alJ=3+4i$I=j5TgLdwS<R0tB<t4N}h{dJ7*Mv$RNOeoCA&p>wD"
    "OP3oj`-8od=v56axE$-MV_B?shd-k}e=$<%sT{`>SKMGjaI6mdDpp;t#plrOrDe`E!i_{Jpk4&$VBVS6^KgNhE#VTDO4&njC"
    "QlNKG2sS-RpHr&^Zvboo?cp(q;;c9=ILo4=BV3alK362WN+)S1vY*XF<<(W8$zO#EXRfH?i_UOVVhsa*RiJg4~jQ5*Y{Y^)&"
    "o6_iiLl#VbxYMIA2Mq+!s)0ufwwJy_1cLjI-CioAaetrKM!LLw8;xYyk_>pfN8$E2TH87!*yij;%DIc~Q{Fa0v!VY0Y#49p#"
    "fMWUH>pR}%spAe~p6)46cP->H&Iv9lTcb?1Ej%~EhOrcQR9&V7~&y1vIgO^M!iBZ*1yg@9!RPuedkbf@lTYXbN_d<eY$maA&"
    "aL8mc&m4Bf%On;U6YvWUwDW+kUa}x58)~OOQJ8yk+;E_fHVaL&dBal4T&I|~vzCcn@Q%L!ouWr~-Rf$aA6hBSz6>Vyq2&VXc"
    "N=}*$J$D7J`dEx-m+kN<85Bfd$$H~+PKV?SDSFSRXld;ES3QZ%;yX87vs)9rd)I>!q}7ee(Qfq|sFdzJ_3Qqqguv_Ym9g(+3"
    "hF3K(0z0!ao0F+OJUK|eWZfO<o`;!eb^D_Fsr4#oob*0k7(PqPy6Q`CCjE852W0Sp!3Sh$<Z$#aCAMKS9F#z^m5}-%*?ko?7"
    "f7Ye&j?3xCTs<VQHyQCACr`8IOTPc9$@=YdeWjRJZTsM_R}e8}>xjFjGjMH?m+;=9p|`b-T3oZf7p?<AIdv`#Yfa*yN9KAXd"
    "$T<if1`mc^WFMck_>b@9i`&`N*4wjq#dhatt%{TehN1VY>@=I*~ow!5ftg`V=AZ~y5axJGT^Po-V>!HwZhy`#$I3lb+vi_t&"
    "<_Li*DARJHarB_YP4IPUSIk+@RpNix8s<fvOOcr&as;!_IjtGP!B}KK;5LbfxT642sn>2PyxEo=8SwsbRb>P(mFr>rv;^lv0"
    "_^JQ`vb)5EH^(c&T#=cvN}%NLv50b8z&vBSz-L;ihE|Xw>sV6nxb(*RL+52N2XbqtyXdS05cw>r!zzVJCYahpzLkTwTRV8X%"
    "HZ1;hHkYX-5kioXx91A6?Q<o5g9d8Yo(JwV;KByJcmtP0lAshJh52U8@9}PWWVejLB>RHrJ&sC*Q_V)jHa(9EMbEzA5)LqQR"
    "Nig(@Hr8#jMaw`0TfQBhM>K&By4>(olRM%oG=GIvSlJ5MFw;(($^`#?^bu3>7)%MMFcw)5fL_RZy+VhLkpokLFlvDnW*sR7!"
    "f$!Scd_S8@aacJX(hQd+G!$SA1qChj=Q&Wv~OMiXkp#AG38@2-76iEvrlt1Zd{dFne7syI4`e)H(nM}b`d8^heE#CReYEcML"
    "}{c*L@eq;s_7`>$A&xQJg)~C&rq?|W~{An3FU)7?J$lv{iZWN7LL^5Pmd;e+$7MxkRj4>{9F&1S#t6BPFb@7~@AC|>lG4~iX"
    "&-vmheJC(iPT`baI{N+1=B=oItx<I-+lUrjmA>W}9zsx#@$naB_MTRc1FQSI#)9JpcH=!bVI5|TpVMjB8-}MsmnI+a+4M|a$"
    "97T{_Y0ZEd_I;VYsjs&?_`f;A`A!y#o!<g@2g6IaJ=yC#Dz9I@jc=O2M6hyxiu&-ArJky>e`N*zGnl3=t=@UYyLOGmQ|INh1"
    "@mV@QO|QQ+!&hbatzCD1N{e(#tO9{ygJ?A1?POO<`qO6c*~iN+adNIC1+ZgJsv1@DSH~J@)wuR}9f_-`@TFGOC>}+mN4YBd~"
    "=ex7+$&DdALX#DqteL<Mt0%(zSZnKQou=lFIep!KORJey%y;%SW-^ma&m(6MRdy7i{KYPIN99t;C|s+^o0BWb`aMxHwDGXua"
    "G36{|f1mk0SCa~Sq>!dP)ktK@ZzGh}_)zc}b{;<DIZEBZYex^)(ZlVd+=0LTwEZY#=3e#Hud(X`jJ=4!EfPnL)+{jUmF5~ST"
    "s(h&dp-O@AVI1Btwrq%>zj@g*cr?Fhn$f}_3^_%5U?C#GzJ4=a2=mIMNkl8Kz!f1ePi@Yp)pP{x&ka+X1uOAbe4#aOJYG?Q<"
    "5xjOIUA1igx}~$nw_0p(9vNMz+hc)%!Jk1iBen?i^I;09JJA?>MRX;1N<-uo|{cm*ZGY%yXt-dCpsjfEv$F<p?9cQOlv9cO="
    ")tQyVw?!W*h|ooKtN{&8ne0($Sq|SkPOK2OcB>ItuLz_i>Juhd)#LbY%_`njGI_giTOefV>Y(^D*{;1`)nAaf2~B-VZ57I2s"
    "a0pdTpOr0Y49_iL$(>ZFA1%#R`v8dJ?x8!?PKP8P`G5(I)ZE8e<Bm7`hhwK6ps(k=TP*_(aUH&yNx&qu`sv*JQpwM<N%vJHb"
    "m10U~&SI;o+{O``e!Ed9={j3%ozb@h+w?w-<fKYHJks`jwImyoBrtB@1gOvcRdTdlxRIfPny3Ev~@=nB=5wp(28ChyqO&ObB"
    "k>683^iXPywQ0XfTrZX)Q=lsJ=(SK8dM$#(-1Aklck+5%^d_tMa!NVQ4*v;1hLD56*>98d>^UmwT*=}NDIY~A!&uM-1=Q>bo"
    "AjNEAo%N<B8)tW`9a@%C&MbOI6vOZx^`5TU*liH0@tptai1I;I@rJOcU6lh^d9N0nKtB>*~HLm?rW~8MF;=-rM9<mos|0^^R"
    "&(pcsE+%K-o&zXCK<B*r;`&lQ|T;c?m4%02Qfh`VMlcG`s{PG-T-hh3L(4NK@z4(fP$$Cv7q~SHt6{t;TIP9Hs*QN=78k6Ti"
    "a(l{OQ5J<i@)@#RNm1J6AOlZ71JN<mlPrF<Z5;N~-(Zfm|-^{sTxGl;irVBZZMs%v$bf8Bb29ZxQ72MtwwZT7gY#~=nhPwT>"
    ")H+GBDM$@1ygnTXkUdnh-h7v}_0jEQshzCPx;y&5$qwV?4kj44%_qU<E1Giziv{(DmZyXnSKV;2-%Ko6bz5U(p?KW$sDca8<"
    "VipEa@p92tAW@Lf@kvMacVWW;9~DEZw+xCS(8!zx2wz%CgyI9HyN%W$Mt^L?+s2zW<J-`NKA5Iarq_>^S($A;sa?EJeA>Va)"
    "c<QVK<CVtyr8V=VJFKiK1;p@?-C|$L_?L}aoF@bp1hJSy{j{Q7>vPK=Xpwv3TqABhPVh-6p6NOD+N%u@<m?bLI<pM?|x=RS@"
    "~D6k~5_wleRli(_O-3X%gvZriNNp^##|}C(1n{V&jWb;BT6!0ShCjWLgTDQR{I!@oAH%FA9CTmVFMY&)q(LY|{9!0DjffP^R"
    "w!t}8ruDl3Y)%;r8yl2FYdp8a((F7CX$s(7*eGwG4@s>l5SNPIKvT@jk(Gu&P~MeBf%*@V5a54y%?A1*CyqFh<5!7JHl#{xs"
    "}8~kSiuE<~@brJJSdTOeVsps1TCq-8Iolh-0IhFfj23=wsHr<$a0Bs@cj%t~sT)~FWN`uhcgR&jnh<~>*gME)%<gxDjOs&2d"
    "+zF<Q4i8_5)Vqw9YcP`WmERRfXyo=KfsC8aM_6o<wLhM&_tfuHtGk=*`IH~X<l5$Bs^8&+M??&CcL%j^^Qt%D6^1u&XWDQ5E"
    "0H+}Z*Fd$x6jH%jm+3|#7+45XFycuU;C+EPQ{Fk+3Zaf|5>!Jp-X!xJiZUX6l1(+zH+$h<XFnG<CzK9zMm>Bdx~w;T8fX49|"
    "0$bK^U8ON=gLo55HM|eZ232`re65w8?f<7UsZR9m=RysF(Op@JI&Eo)`x{UOhOdz}@-jmX+&|p$;KKKxJI%BsLS=4e@rUysL"
    "R9Gfiqk-kfNCSjLDhnHs&|qoy^dL~x9;`S79wfh|NOwZ%oVYIB1p_b&D!yEHezM=k@M5xAz!I_ra6$%sl~(4j5G19@13-Uo7"
    "g-L2G3j}{ITaN-|<5Hygx`PA9Zvu~aaQS$%TZ+)?$@Y8Vq_MY28{!VIfE%9Pkmoh98op*J{ZBrepmn0WfXT<?7&qy}y){Ewr"
    "wTp~7yQakTkQ8Rbv|!yXl&%y{)?k`^Bkz^TI?4L%3&WwldA3r7?BaLB>LXoSu9eHt!?QrTTOZMfyIiQ?yI}D8bJG4*;2H#Cm"
    "jpq8bXC1FEeBznw+i||l(fL7oxoJoG&UpMZ}SyjNbS6`%Os<Y_kWB4<j#6gC7*Cm`trM8il1mG*}&hw%U2Rl)gDtvD)VuR0U"
    "D3ltER(jSzmCOe?0?EW&lCPbcl=pZQ0>t5|h^GRTHpoXRMrodE*@&okYtW*<cUnn0p^eknPr-k+Tl_Qh2>o<&<Iaj8i?1k=7"
    "@~UCPH@dGLwI^@1gz?IitNjTuM6V^iRL69O_)5miPsER~A(A*&?8SPVy}*V~S4;g2K@PItLV?Sb0M#|MgxKgRsDF)#`m8fNp"
    "nKH@;+<>eV%zm)AG50Ma7p2P0;P6s2Ps{M@O8biJWL@L3TX(^T^jAZ0RDxv*QNjRmH6>yd-rv3Cct6~9^V0Xk$o;)3&s3m_Z"
    "?6Qgz!{$Ktv3-2eFhl2>OCLJl%{H*^sK2S}(b3kV$i6U5pGCf<-@uO8fW5qb=Jb@a(P_odO{(kH*>^$@e{CGDj%B^%;4n5qm"
    "2|VG^R)VEjb7n%KpuSXOv$dZc3Tt*>ckQVWfZ6a7PLvX+w?;4cr=)hUNAig$Vlp|GrYX|$o{Ns_h*E+m809aU%lzHNkoXFiX"
    "kzWP?L!zLjPfF_A>9Y{2;r9d<<J+XZ^V6>Ci3pCz%Pp{0r**Y|yk-a!k`qT9TB-uPi~=uxG~6zKutll3s!En%PpgPbEzFxVb"
    "Oyjr7Q9et!PEK9nWjrf?pqzeuBbw;;xf2K<RzOL>>>ftks=v^BP)wjyHqc);q!sPTaZO^dA-);x1E>0;#><E9|RN(tl%F}_5"
    "uDW%J>ly^Vm>9@;2d9b-mtMaRo9qfqR2zomz0Ht>D;<?0hn*uZCtrv3quYX5*%s+GWiz(;gbBm3uOZ&ndK%QsWpH>6vZkc>v"
    "+({l;Q|08WBnVsm(}DH&i1$XBH^fy3Ljx?4&q*I%?x{_R5do_*t4VfTI(oHMVNBy@C#b9U<kD60<Vpbux2S;81!%)4Q3Y;i*"
    "u-{riZLaB@wk_1-&Is7ff3Xp)F^H+_1P=V#C8pQJTM!ze4Gz_)U$nL*yw6$F)$@v8E7WkfJt*o0rnoN@~_b9wch@Tv6tg=Wr"
    "a&tx<~<g)Q8HY1cV5RP9nJ35qfxdOrZwlC~MAy9sH0-7T*xMoVfu87C+&HgoKoyRuOIYGXkD9zm!mchSflMCD=}3laMPm0=C"
    "o8#yKth;uc{+w5|QDZss8Pb7l4xnNC^Ib4o6FTKtI%`3T;iZI&uSBN_(Zo;1ubjoZBvCuH6%P}Ht`up=i5dJ}MRvn4puGI2$"
    "<`z^r4o&PPJUl}J1{#TU{hQ;`*Sa<Tj+0?`8vn%OOJ6rK_Y8%YX-l^%L0HGj|g*F1<k)LS$ZYMX_%T)VL+`2<gX{_9;Z!QH;"
    "B$0;&o5}Bc?a%^(jB?J#+U@K=$~<y(SdKIV&ZdRmTXvwt7)Iojo}O@)5-6!vKq||ag?(~Mk`Fd+%1D+b+sTDJPvfkJ-Yu?A`"
    "lU#G*p;!dDV<zeVp%a`y2I~q->t#feXj|JW^ElKh3xYk<0u4i`}@kbaWNLV;=zuQe(1N{N0o_~B%G_syNSF=5N0+mHrTXk8~"
    "B#nXM@=q8NKMeuyyv!PeNOW^CllnW?5v^Xtl^?!leNVa6v#;({}yPds3g(SDL0@&g;m4IWS7zg!q}goU>}p9s3jjE#%=$hpw"
    "^9f`}h`(N~-g@m5471m*}5DYdrK^nYm)89u9V^MnR0Xo@xoOFh+|8MDmJCM||<259(R^Yz5_U&d4a9LBroLs!2#wJM_E#>K^"
    "*3r+A*-)xp|0jMNpOvGJ*B`4oSk5065Av66xU3Wj7?E;eV!LCGCkNSwo8<H59a>QZLlMH1w1vW9su@yg6_(B!+7WW8vim}#d"
    "gH+h^+MaNenAA#NGuGo&`J}5b3E~f6v_1WE#k}Z+@3zzZJ0VDzO8MFJDamo6`XuI+nvNUrM!-by*Q!-o&gnPbk5@Z<!H6~O="
    "Ss7v9hhRbd3p8{JJljo3a5F5<<Z!nEf|UUxKRJhnyN1&qIb?u+s?6u%FzP&%nebN`0Ii&_*(HPEP85wB|Az?410G4JMoaLQy"
    "${~r@gO!YdY%RAE|(-fTWZt-5}tQR1j%KN=`sPTDln$(p}Oe-7Q@LGEym}CNTz#h7lXE&v?GikKaGxdH=X;*R|`M_v_rR`@Y"
    "Y8&a8-HwE<eNlFmX61rgmZz`xlshh<!!6ZyxcLjnc+shOeh3G*=EfY2-{FQ6jgHe}@NJ@9xV>%+~}B{8{wDzZDutCY^rHKbI"
    "&rQwTG8+Ao`ybAu?SEBr-pD%GJ&N0`4Qw|jx7p6@gfBg^!t>Bviv~nrj$x9@;ik?~URCbXPTx==HO4e)evny69yt{N^BW77W"
    "cF6vm3DWA<CPFFBNR)qi?7RP#TPU@`&=>Rj&L08-0?sNX(XkN@hs*hsX$AJ6ER~M?2wM=wsw94d2dRr5Q^CVw2oVlL=y7t2D"
    "lZRmb4k)?O49YgN+&X`#KJ{O;Gl^GE-i;)U}Q{j{#KgnTT$_5o>#x>ValD)GAu7X$xQ)~@U5*{C}mC3v99l5o(BLUFbTu6@B"
    "SxQuxyG9Y>`$-vI@ai`F(|cQh)~jPp&dMlIv@zK{uOjr)={}yQeB7Le!_<jC`+pj<qWEiFzyaDy>amAjc7~y&m2}{UH{?;bh"
    "Supjc?~3w<~6pwK-koFda3YH?hQd3n&O(+#S@z3q@HyA6Cz0=rc6EE7u<BS3QXbFd2QTY-abQmkPBM<rA{_3SgkWLm=O>m1l"
    "6ld#vmiBD(Bm1Y}F@|30uo;JQ3+^SMUnD-pAFi9@4#G1};*q|`uy9voj7QXn0M=nZ#5OCmUmG|wD`)PJX6hKGWzr^o?izs-d"
    "RWIwXh!8uTB{BK6yJ#V)XUFV)a~WWY|GeUwIbMiGzgJ{>xc-YJ<AKQSf5i1AE{Lej9<H-sz1R5NaKh`~#LI&e8h-|^N`Jt{g"
    "61oJl7Uo{UmxFVEGDo8wHP3iC3;r}!f$h6<dne%H749|FL89^x2hoZt!k6{;v9f9riy$}&PUhftv3gO6Fp@9plC>8TX;Q%Dn"
    "cqw55+!)M=>!m{ps>Mch7a59XKjgqf^oMJ?J`z+H6f?uO^ACZb}g<>_jtEcspj2@CAc+a=0q~$TAyBc~$Pto64CZY7@7ss@q"
    "MIS`;?n`0?XMiw-VlcI~mGeg$sze*8kx6H@0|iv&HHl)6uaVAbYov->G=n()M5qZ47&;wi)Ojx6wQjcd0T!y)&Z!^(cx+TEr"
    "l6Q3AW_!6QpdDpu(<ZvSWQDp!xcYO&%NwLAu`;zo6Pp6c<(MO;H)?5BUj$2kKUOkxQH4F^feUy9NIm~MRy`e<WkUF9)opf9W"
    "6_R>bW%1qi)9-}^$@+bFGVF&VP(PN*Yw1Z!v#f(&!O1KUe(@ua3SPie<@{dpNs0Z`%8CGF{mWyghdAoJ72``)d7}SHUe_$*u"
    "veRexV<;O#xR8_imD-Jr4t8cxesqhD!vs^##YFD(Q@SABMc*=*JezRpuE;AP=`({AN>n?pg->ByWeILP5#&{br@IwQc((PZ?"
    "^_?sXlKb)2Jv1u6==uOCK^ei_U6mY4s&_wJ%crh83zyH!E-0RDcCCyu~B|fmjSolN2z+_Vnq~<J$ep!tmBml5kQ5Qx;#2t-p"
    "mfYQnQu5@V5y+!HgR)EoMw_jt^oD(J2d&oZaT2SdyD|2CG|p~b(LYY4u>(<;8Te5UiaI$+l|jD!h_U-;BNh}k+h<<ilG-l5z"
    "f(yfW>VE9J<;6e1z(3`gYR0A{a+(7iUt<RGj9C@L-e9(;>Ih2;&@CMbFBI)FT6ORxkw2Y)A57E5_g)SUhpc=K#JcJb91rLAv"
    "E!(1y6PS(DTWc|*6TJcF%QjMny#!RTA?UdBmT*@j=v~|~U4F}(JlhpC3JHqc>Zc{KcJEXGu0ksC1KT#tlMTs=))EG;E!x&~F"
    "!8=#DT|sHjW-xj+Jx&q(vHPlTA5XQ#g-@i$M!4WplUH?&(a;u2hfCvG{;5vL_i8Yx93IFXsZBa7Auz%UQxFjK||-==hEwB;0"
    "t_`9V%r!Bob*gx94j3cYuZi)eyz-u@kqhsbIKo$81yHL}Ctlz&B@{GDjpJ0|U<ZWa4@EKqzT-N8S$m!=edQ`FYhrcCgp7hik"
    "Ez{aggCnYZ~+Pk`nRz*A`R_p|~n+F9$L0U3`z?l7XzC_A>%CN?N}<|EzqBy|$0cDTT<e)WNBSnJl}&MUn?*QT=iuUhZzAj^8"
    "}{JLbP4!EURnjXOIG+xnh({Y3El30HG=zl!I8B6|HoKX+BF~XUb{V<SM*w7D@s<G9o+e|5$HVL^oalJIO$zgAC_-mnCgwOhr"
    "xT+yIdquPSU=_tNx-MeKrr3pzmi$u33Z(w5O^Z$q54tf%i-Sn-2C$so)3qajqBYO6=Zd?r?mNx{q-k92p5Dv|!mojak8I#WP"
    "eA8iZ&h^3V_b(2es)zk*}Clc*lIcLmF!?_l879MAbjcWER0LNIa7&XUoc=>^<u)S`zfLa&hJd2LMN-Y<bN{0wi?c&FFZ(fRN"
    "kIX&3qSGgIv8tw^arNtdfDhzOyMI#d6wdfhHCVqP0FoGHXgL7YH;@<VySfC{&F8Ap0$}V}AP07Cnbm2s2VGfRbB!8v{+{t+y"
    "Jb(Iso|*CVNg6G{YJyE>hL(gx}%pLE6vjHOfcQm?LOsjyI3mEY@8f^w%6o#~B?%7r;|D^hdAAE~AbP<MFlRs2PG@XWVo2P?v"
    "qE+iZA-}`dW4vGB5O-}FpqO-`ofljmUq;jbzB@$iA-M5~*z1A!42D*w5#;X?>t^~Cs91ZPP%dqR5s~jEvt7Jue5^TKGaReVm"
    "DNRvQY5BO8vyO)rTm{h&;b8xE1qa_0U&Z1`oYPRZhvpYOd3MrDJv-rycVhCBh-EJrKN^D>aeGCI{ZMb9r~C*`+z48E04i(v{"
    "7lHp!$W-x)&r5Ph^!k<-6`r%&i$ZyJ)2%WX<q5;9kmcHBY5=^?G=DsT_>%jZO%JHlv&Op^xA3QHIdNi!W4k-W6-6&T^JR7jR"
    "|fcliXQnm*W~>_~MFviMfCABmhTUCCjTNc5Q#&#&IL>U5}5C6O;GbzE`N<(_v!Oi^4uL&*J-Zn@{^354l>`Qoh*l#_a2`z1V"
    "(r#hz{=;-aD36_monvmGaJ#XGM{9Zy?qZUD1|<Xw*0aBN<0O7vvZ<C_C{H;_;GuI7`FYdf=*gC*)&F)&OQj4GunZUIO_|DlV"
    "6h^nnUIl8CjJ=>|c0x5TZP$`-2>cdB~p4$@c?0VjEWzI^DFQk4NVD6Iv+O;)Fv{v~J+gab_ZPT+snL^M3?Ahfus?zBjnYBxe"
    "+}OL-Mg0U@k{Yw*`rw+^m}0;D<AAAd?BN5fmVj}+MVR+?ae75X-}Yokdmv~F-?bQ?+;*XP*2y$^GZ65h?eOzDFn5Ho=uk#CN"
    "e-@Fz~WrZ*^#9JE{FA$A-{!pbHDqP&D?(-@M!fib)TBIl>SSG1`cuw#<C>hP14~Af;;zr9`MKnHuTBOjPgi*%}>B*@P^@9{@"
    "U51vxG+Kp=Q~|Z8CrK4}{^6YqXG*Ac7REHEgE*STjVK(&*;Q8LRK~X*G;CDjgiyRzVnLm#=+SnV;m!T=%6>vmLedWUjQii|)"
    "~;dmKMMKNXU9)sR1$@>QWp%PgxYH^5!qs7*XP57-rxwGS^mE0t|U=j*iH<9!15A=t*uaW;3?0H%m!8aj1kUm?m>LV3afOfUI"
    "McQ<u~6}YMH?uc$lcAFhMT<DQ}kV>e<&TyNCt`ER?>Qebq$NZC23<s3KlMRD8D=R<~9<nOE@xIoj7Pc`v#=Ltc-f2kW)`>f<"
    "cdEo|kVczGa^wytl>OLBgFiKwDj-MYT;(97jTC_E>m<AYJAkz1_0{DGIqbZcHpndL4W}J|j@iHbz)to<m>;f-GSa6*c=F$Y8"
    "_?51;e3tm{--&iF^AEuNomrI#=gT$UTS=nt1PvuhPw8<f9hW|OR<kVlTQxSpAFRI=Ey9i3Y2lTl1qW>8e&qLHAp5yd90MTLc"
    "9YWmL(DHnB86d?#O<3Yt;RGr%oxj+wp}1$1X{J+O*5o+`H?q%F2b0+;)6s)?r08ll9(&32X7W9t#LuYm=zoRgy)6^d!2u;)}"
    "}Qp!xR|%z$CGPUH!+jYTQv^@ZC-Cr43s5}Q9CD41egXNB{$b8Eh6P9=_66KuGjxt+)9_vNe3>$Yw;o+!M4jD_J3lQRGHz8E&"
    "bWv>dF<`T(j7`|6ZE~x+t(xWR%O`U|^BDH_BFQirRKYPd|>HfBR<n0A#^yP@;9q4|wj7_7Vd@!XU9jZYKD#;+$I~&G^RtqM{"
    "snz~CB?Zkm{9_rPBmT7X6Vq8;R=bR*5=+9?-cx9MrSWHbqNt~(o{Ek+H@|@iQ_7BEn|hfu9-t?jcG~k%XYzX~9O$Yu&Bfo6r"
    "-tyoe5)P9q8__|0KaCn>n}#(XQgKa-IYnUP0ajcwM7QKS||Ol($M@KOFQpoZ_28<*zb(%^k*JR-R%$xA9(ojcQR2$9h2U22r"
    "K;QUUDGj)(#_=K38roFbK;(0Wq_+Q!032=LfjmXZ&ZuyzDW#Vm(O!Ml1E&4HC-Ser7tfAKOlDTGlBnY6slE!q@&=g}X^Ni!{"
    "%zIt)-|S-M_wqD?JXc+6Rbsd?qofBwc`fx=fTp>F<xo88nwEOXl1(7ZbyJtWd&sy(&M+5eKvzb=GR1H^vBO000f#1DMuJMK}"
    "Q{nXZY1t6c%Qx*{WK6hs^s;sXts@b6a*9K2@z7zrHA`08G=#*^rH>FNfP+yWo(o-^5Wmtm?FJz*qpuoI8=`F_I(J{5h1qU(u"
    "#X>G3kqrtdC%Iglj0)UDcE7Hl^JOcl!;?z%7D_2CcznJwB2lCdxHzdc-1~SKRkTJ#SY+ZyLI+(>INc;lZzB6Y=?dUwmep!sC"
    "(C@jIfr1+i(K>aNlD0BQ@=v5pFT+>d{g|R*#7k*2wOwen_2^z`S$2uau{o9o^$i0N>8QcDvX4e$lc2D!kc84c+0e;Myc8tz}"
    "1hSYc|0eZ?{D^&@@W)p1MfQ%T$1G|LoQY2V}3Mj(<L-a?Zmk1Z+yM2>ByhZ5nq5t@1yn%i3BRbgTs##5qlZ3{$@miHQ^i9a?"
    "!G1v+*cB10}}v1mcyg$~Kk7ST&7DZU;ZvtV350)?nC@J)L*k&~zS`uTCr`RunLDzv}8FjOFK;dC2_qr53<sfK@6OOY6>S4%x"
    "BC-Xx$l-UUGNU|KTf@seMFyy>!apw|HZe=L9<mqIJY)~lVcnFkBHlw-Sc4zCd^go{N2GL8*Zlir+VyaHIB8eBgrT9iAtmGk-"
    "M{PbLB_o;S-)am7zOQ%T?GcuUuHicYVQRh!Rq7JS!CLp3@;7-E@0b$6`}C2dL9W4pe**k@9Jwp7=0v@x53S(w7ChG${5?uIp"
    "r^0H&mUrq23}uZ!>|D%e5X+AuO^ww-kg<f$D~usdLF0g4@efERv^O(Zfo?1<K4zdXzSLj0hoX5#kN!mMwo=i{c80O*0t;#Xs"
    "4Ev$9g=I9kRY)Un}jn(v-^gD;YF_FZS1Y1|OaO5^7XlD@qL|aZjD&FAd7t{mw}R7{E*;(qERkMtxSn)XWI<<Cg?p%?MIF+ei"
    "*lx~3ZET-DH{*g7~UMFg;c5Vspe&9M$5l{FR>=NV|3Q~-$EaeHB^xzJvMTGjQ!YXCnGSRe|uVChb8myq}VovN11ZF}20Mfbv"
    "2jAvv%+S%Dv7!t`9%X|<avS_<(4^GGk?2i%<bFLtrn=gv6qWc0&yq%GY%Snigu+hb>r#vc8Npkc7W#BUUyskuf@bFE+=5)Sl"
    "*UuE9+$v$+bK`11Hq$NTErYz<xH)i(-5lK3lQgKs6wi#Wb)Q<cs_LUVljr^tu>R_3n5EXpeC>m4Rj@VCoK5Ou?cfi^)D(KSU"
    "AjTTCxZp-hq<G}&T<|z4$K}`v>VW1e|}V#n)P{nt}~@|`EptJ8<N0h|B~k8wC84D6>3~(zG?fzQkfc`lG~KKkJf~2zw}Yxns"
    "b9Q<wN2dpq22{g=VLW+UKc_yGlMpq47^0p2VWni{IzpWTkDJ+lVT^%~UI3D2~bI&NUDX`@|xdVNvqiFZF=)R;C)@mC4`w5l5"
    "%fnvZYY>sUemRk8;ET-SQ`bZxPV-=hhN@`6toKK*9RAx1o>E5-u`I5|1Va0{Gj%3OY1nm@qa9FUR9YK4F)H%3n6;G$Yj$dd="
    "nr`wVXgC_LC?p2wzY2OS{8<;%F_1Vm*pyATs(4m;&XbcYLA8Fpgd)OlLMRZMxWK4&8t0a^2y@=vc{gt)1sq~O!cCTYY0ONt&"
    ">AO}PeMjFC<)1}}G;~f}TwG*yw=c@B-gdgA!s)$^4~;uqV+M_G)*+!OpJadX75!<4OfOQAl;G|`>(Wsuq+`i>=cH(%cExPq@"
    ">&0)Qds^La)*SqXbz;zS^mJ_2^&aR-9GWKO<x;7rK8(HxQ2P=M9T2vlI}`k^9A#NQ$`G-p%Bz%th4`991bvVODcyrFql;CZa"
    "#Y(o-7r%9;;VvWfcn&IDIa}L`U}!M{r!%TRY+WYd4q!h^ce6eNEe&+nBQ}3-(wLD?$;N&qKkL{+^mv(r`&qez<%-+N>w=`iI"
    "Ri$BUc@*Q1;$0R0Mw3V^FMkY8(LP2{hfTHBL!W6d^010y9`!hyLW6@uY%6Xc=v+<5_u@kMJ<3%}Ryu!wA@iJq92^8Qwbwm@b"
    "H(B;!S7}8Z17KNkHt+O@(U3IS9D)mJbB2y?(05iAJM<B@%juONb^DDLeLY~Vqa^#<Zx21~svfvB(HTh9?2hS7P-ZqnT@o{o1"
    "+9j5^?`z^PnZ8C(uqvZhH_0vyc|Z+<5_~cLx*ddTNzhwQKJXd|e*FBhTkxm00>MxjZG25zTok|loTuJn)70sw(P$-^V~V5HT"
    "K_@su6}G3H7`dfw&S4Ncq`;7oK3B#7TQShTquTNcMDM>Sc;mI#a>aB)RpORJbs_jC?0l)GuiNmeSlmIVg3l=vdXJ7-L5-OkQ"
    "2tTYoeXCG+dku{wK2TRB6y(iJKPXsF&u4%Kk06QT^>v^bh{lB{pW?t%6K%{Q(56hhY)nE>}U&O~pfj<1d9b&ZwPP*T<9*dWO"
    "9!{oeyki*CM1_x6v@x@_+$K)@-Da+PqX3QJ2&#k#i2)+a@VR3$mXn>)nBWp<;W73<l3auIrvN^057Gk?cX?%2Y!(QL_6uk}P"
    "f-IaBv@#(zs!@%2{G05}*GhELuDkpJ@MVCe^0m)^kz6CFI1#Hpey9Vd+ye^(AxIE1v{+NfJDLuqZ5)n_q%F)ow^gj(3%wDVJ"
    "E_jx}z+*^{p34fTU2xB?juGB07oz5xalJ6#Eq?U4wCJ!l)UcsYk;D!Zaz7xymMn3{7unyZdm^IyScMf7#s5lgR4X{D<}E3iv"
    "`T`$qds@#DZ_bF_E~LG+cs*os47n>&VJ26Rj27#qq=tT!6s2pWs>#pE>5dlfzWclN~{wQPbQ|_sVU~H5>4%~w`EcevvqLD{&"
    "Z4m2{H%r)N@t8hG17&Ztz&J7sH%^AK}ncv8Pv+$beJCaevm$`Bng<VF_AXZ^Q~Qkt62DukqY>Kg~!16<hJFc1IRv11dOgG-u"
    "DTW2u0Vguj}xV3DGF7(Art9$yA-jNj22ctbOb*s-Jw%N!QECz^u;@h@%vg2{fgdmuL++nj8UziYNjeFXUUufSp*W%PTPs`RZ"
    "HKvU`{^mY?GW}W&bUBHwFCyjYqr9b@(VvVNl;!<WUd$eBW$F(&w;9glBl~sHlu<?{7vBw3+)FW_}iD`QL7TI5wTW$;*ftpVI"
    ")*T7x){khYQzW@W|5I<RtLS4S>3(+j8vvFzP<dF=qe7p*(7a&gQYCN>%6)0BOYA{er~Gcp%_4MCk#pxA)Cb5#8z`+RJzjL6G"
    "E$b})|6cn)_%V!yW#3!u{B=gN^{r!Xl>8}r<QI#W4j$7KZ3%gvuvZf{XC5{GT)z1#awK5{a5)$TjA7+xmpV(K(-wd=$+dwo0"
    "=^K^;LnCFKf3M+CBL8zVNKm?|eVgjtb6YL&4$BUb%8d5pMe4-o+!ob+JxQHj1lOG(h&=e`O6F<;^4z!C3FI{wBl(HbNF;CSa"
    "$fk@j6h84&3j+!|c<0Fei|`Efof*yI1|YaUNKZU0i68{CUwi<?Zj%@QQ|F5vw)LXl<xZmy3joH9p|k$W0StJrtz_ljOA_K(g"
    "SXNbHf0VkJpDb0waW~&dfSAOnrb<}U;N=g6RkjV>A5unp^#a6rXf%XSf9+twM@^(fQ=riB9>nQ890~YY@?r4${EwpO?*k-@t"
    "LPTiGm4!Mz&yz{6#M;Q5WEAn;{P?f2<hmeT1j1)pmTj+bhxMCr&6-iHD!hWSj<Is+bcUw-t)h6^q9;>szRzjpGJ@IwCC4>5M"
    "o`Z2B1<i{sDr@iPn|sJHIH~QF&w1Z&>lXoqu<SM-10LuUhe{otFEox-R!!X<lcO~FVJ>snut@&={w^pe|{4&G$j2(Xa*i9A4"
    "^Q&U~Agb{hM)8iABLzXm^QZ4^0GvTDneJ+2>q4ER-N<L68J>x&&Gwr(D`<tZ>onXH>7~N-B)z&~tp9SGcLD-jtg;(><dwnmQ"
    "cs6stE(!S0^scQfjP2MPuqFMw*QzPT4guFWV5%jGRDEPQ~yo?m|qyC9Zcd}C~!RX~QdpQ}oInakY|VSf;$a$OmC?V*^+Z1;L"
    "TshpoD%rB(_>pto6SvzkA6Gsi0m2dN-zhN%E`qhOubF3ImGrK>UV*WKVTpD1<=$fai+$7L_VevF?ax^`PL6<omKx;*B+VElI"
    "N2k?jT4ec9h0{u>Va;vcouuI=8K6kOOj(kG31oMtRrZkLc@*^M?lbQz944&(I5sfzv3hftw)T!k?CEbWyTCSiyA(Z1sES^6="
    "pC!nQ1G?y6u7}DIlq?g5=yB7L5XBRlT?vh@U(rrhp8l8OV?BJRt+&Q_ju)qZ;rZm@wwTyzL)NpYH2*lkBhCa<vPHZ9PaCr=R"
    "Q3@JF{3HicN72IS!>u*28+QhSAz}Jjo%{#pL^yS`3qPU9sr+=~7+|z)C5jiYC`Dj<)5)BDn?2MpojJ!|u+a{ZesC>kBnN6d)"
    "a`Z(u+>xTJY+28l#+&PDsuhmC#>vwShq@Rk7Ly0_e9oBXcJw^_a)tD6EaFmVa<-psJski2C`kDjFnDeU((9SE)V#mfM+3kaK"
    "}$+K<Qo@~Hw_Fxz46`+Y_6VqYKNK+XagJC<x^9Zdd3NcwyQz3(9q~3Q@66@29h2`6f1N6P%d{IkT5+DhnfuEy7N#``&ZeiW<"
    "$6h-{uie1i;nd`p<n46|O^nH`%9B+MTm}uS`jl6*B9aomX10)Ty;%~@W`l3){4ZVQ7rEeh6*s~<zZRowq_jsL!S|a<!++ym|"
    "JMc9tNj_wUzKZX@0_|i@Ti%AXl$9+>XG-tIN_k=fKW3zFTnaPk2vISgVh^>bgE~eTDIjQ7Fk6mgD81E@{3f~2Ja&*Y$az9s-"
    "GH-Uvum&&79hZXG<N{Wm|k_J5eCW>E54*yRV*ISi}g6M+#G9DOkJ~5<V{MrlWEQrU>D>`;&lG9zUx)xqEslB<g5&<+0}SRWW"
    "3_KHPGmqARhhVh-K?t-(%je8>9b4aB{2czmu<8Oz5H5V?@WNhu}ZPd!57U)kQH{H=_4bl|62Rzli=;l7MPe2hxH9zQ6Q)ZS2"
    "moA3s2mUkTA-Fa#|m$?epe_Nh~nddh(LUPZWKbx_D#Rka)@9S0S$I`}u_7EdrEP5XF?3#@`VVxkfCXK~|@>}Jm2o=Szwax9)"
    "JZ8s^y_Nxyf3m0<ojd0+2=-rLv;f1K%5QxlvtE4ak6{JW_cqb-d%DEec0RNQ$W9Se^-q<4+R{Sr?SbO4?a^;cKmSf0+m<|Ei"
    "0joBA?_6cosIXL{#NA_JAeEe+*$cAuPASr2-z?ykR=7#NL2Dnvx6dJQ01EH_}6sltoX@q@tZceYO@qK&qvb;E@h4a)}%!!>V"
    "Jn|W4Bwu=a&Lxf&t?UwCdtLf_FYu*u4FS>Kni2!)(9dcND*rT@9sr1I#xaa~1wdmF3v-SLn@h{07*Q{A(IvHq8~{-xnX*B!F"
    "P|#o9&~#i0_}=esxHI9OA5>iTm93vR{!ltJ-5lZ?pE`Ucg<NBY6J>a~@lLti?(KfJ_ORmOi$4?O#0Ic)HCTH__Z5uRE}8c)_"
    "_x|q7vndCmA*SucsDt3P3pUshklizOr@Q1_9+an>3&ypsWy<h=FcP|>nMY6OJ?iQEbK%w`Q<({WD6Pfeb`+UrczR2p~JeQwO"
    "!pGDBEh!Bx60LrJtGv?~Zd}1XU1(evzxitHC>jX@H3KTAn05jLvknoukT$id(z|s7_h0S`d2bbjr*$eYM@DqAgd8Zk@+AeqJ"
    ";&&uzsdmE5;0o+OPt2S^S=P6`);r6xE$O1LbdLHFRjhhsC!9vhtR01)YZ2O{em|n!aE=?Qk&V>2*8(n{0EA(DOZz9>x0Oo&G"
    "(uJ<Ov#&%to?_=d_Ek89z@85wlKelbLYqu&#{r_MdY}0hryV1dRT~32o`NeE*99mfS~NqTUnlWdvVU%Y>t@?>038T{N6M&zH"
    "S4(+oR2_j(?o<AIxBM=Wm>ufw!IwvrM)L;O7nsZmV^{6`s}4!X|}KB~_Ko%>MU+H5|z^;n7a1o4^XC67-AG+IW@kE=JMJqkQ"
    "29Mr1S=Y3V$%r>n8e*8rH9dw<SIgmV5?tQU;(lI1V7dHEXSoE(%^_vPt!6(TiN6aoJL*4`rqz-#GM4fxC&sGb<ncH`h0p&7~"
    "315@(hWPFCE^lbbRkgnE^jS#Fxyk+YI=(yA-)wCcgmaaxhQ);*JOiX<Bx}m}_*37ecEYVVBr(UsL|h@;4R7kw;%ywkQTb1j@"
    "c;h69*+uwYo9k*k7xc8n>P^++{OJC!{EnNc=m?j%QP_-xJ|P{tmUa~T(9iVy$I~OG>*@`yosUGlyVs)WPDsXt5iQjTgO-09p"
    "&M6UKN%_v)dYs^)cb}TK1T)b09y-obR;$Di(3{c<o(Gs3PNQ`rb*(stvg>8TWqnJ4i9F2jAx3k|#S?zdZh8WgnU<LM#VnmF1"
    "tRHGWw42lIxW>nw+}g#6w+FJlYa=9bq6{elOr8-8DjAHGw;z09%O4TiQ?OrC$tlNqpg3mfSJX8=Q3c#}@?F+PoY<hpdjNZ@m"
    "yXu?-&*QxroX3}lHyKYdmc~afu;)`lS_kWf&0QHPGSW4Jg*G|^_hLDBgqM2gY4Nln%J}-Ex0S~=iLt24-P+@mw85+A=l1Nj|"
    "x?s?|Lv~>w(CmEDB2y?f_W2I;i%a?1KvZS;5oYbr$iD0mgfaeCL#cjke0#ChK2^q4^!aVzLCSkAlJgC2kjtKnj*1G60g=i2!"
    "R08le%%Xa40U5xar1DKi-dT|ETv$r?P3M>RqIeHH_M%OJh*{s&GjnEUzL~UGSIF)O^A=yCcFWC#Eyb*L~8JM$$Hmm#14MBzs"
    "OuwqGTl)9hZRlf5J7zIPlfar}6hr+}vsoa7E{p5)y9p5JX&T6>D+n(|lLFa8O==<?}EORb_5syt+?vRNm^$5G8dpMCpGr<^-"
    "g@E^vQM`ltGz!%CJN%ypE1fZ+a%_s4@PXDzL<@mY7#PYY;<U7AY%T14|(s{m3la?Ha%vcqJC&31a(PdS`FVXx0?zy98<3bCH"
    "UXd8Ue>WLeilC0IRKZDJZ*H-GcnWd@QET9^iO<-+(o`h*hguNn<K0{VuftbB;PzcLs$fJ#?36t_sMq%+OVR3ICDfA|YMf|OO"
    "fsZ-xN4!ji7peBPEIPgH#@5FNI5c7QJ8C6@-UFk&fptqw{p$Yn-j1Hq7n>42K%f2jo||TE*ZB6-!6tkqUVuYvTF;i4IDY`Lq"
    "!#E5j2o0{L(Lh7-(m4Tyiiiq-haw+`Sapp9Ef;IpJ4jgsPD~99>JHnYR?8S%}$$6&FrUZ7knKAd|p=M5CelKlbT9)jkbHdI>"
    "^pN52=<ko9z}I)%l=2IMyY4I|V#cOEzUMqgvbf0dvrU-Kc1ET5cctX9^;q3;6sr;($jt<-EvRko4m3l`MYvUADqr7A)jyoh5"
    "JVZbHbz+niwXFLdKv&#r8Ct8JeSF@3#>zu9v`8Dv%C%#CwUyRs`RVxxN4;&IwZvS3pCwlBD_(z(qrb8n*P?iCEPavs-nK}2g"
    "J)VUVLJ4Dj<@sbLH4C-zUT=N#R$Brh}tp^fbXMBs+e<RG>k5hK~YN6V>^T*C$?P8?<gZtJrL4!IRq@pg8d!5rByB_SZUmy64"
    "X{gd@F4h2474hF^wC}Yne(~FHLtN~*;W|Xj9fHxm&caJ)4d*$7x(EbY!sHDG2mlk_{7Pb7LE=jG*thob3Lz^SRWkTXn{`F@X"
    "2||Tx?!^?ccDymg5hEJQLJ+ecE5Sv>}fN$F&3{*xX+n4h#TeyQhOX!=`bO~|8aB}Ixo<VzRhWV;mmRWeG#4KyHh?e%mVQjQ8"
    "eVm(>ma+HxWOX4B#0)jhG*H`}>M>2od3?phk^8$;0|9D)2QDdRGraEt@*Q0;6m9@!#EmWx%rfxkX5;cFGO>pT!`~DTz}$eyZ"
    "0;^Q=L=+DU+SL%0#<D%-AOVAz|B!sO<2kTGpLeiwR;rgprqrvV(e6mN}%hwWB1PB36&^@-srAxD{#T(SQOsxEo5vTO=j5lxW"
    "e5zae^Y`2Mvk?PhJG~C3IjQ5VU{j8h^JE6$d$JuvQK?WKgwDK#3w+(X$qw0@Udja32qW5mzv=<D)VCiFqTKjmvtS`cp*0IC`"
    "Snoj-b%H;LTe6aUXRgXnbnHmZ!XZ9k8a;S0f%$vPq0ldwJNiuSYV#i2l1cHr(4m^D^~ISc5T4Q(A9z}X(qOw4-Tg|<9*5LOE"
    "*oX;_zs6_U76f!TURDTN(|7{o_pw>dHu%GBjuB0|7^sHuT-p7{3+PXt1-*0r9nAS*JgSYX%2O>Fl-rdd!PGw)WyBw6?<#50N"
    "_8fwyE)QugN8Ht%&7%OQ-~Y%&48K$wo+*IM9j;)=jY?>K#S4c6-p{$n6&sD=BY4Gt}yz-drF&Oe}qLpBVHaj%+LL<^GE?R<;"
    "g?Dd#kXC=q#`dFynH(&ZmEo{)Oit`rQ!P-`^U=Mp^<D6N6VSHs`B<Vv>;XrPhpAV{@zQ+Noz|L3nq^!juBynCNsHwi@z-yQ*"
    "^V|8z6*vE}sx$>LhY(?L=@xH88VYNp$ud|E5M261ovO^g;IUKXJ%5C~ojC2dX)<!ZIdJ&AIiBmk^eBQmfU|(x`gn6STA@vU5"
    "XJz!nG)GG?Z?ZmZ%{lw2WkzR7Q&J!x>lV_yaAHV<l<bz)a;hJ#<3FOU6X~@Vv)LnE6GbxB#^Pc7=ey6EQJIaKkAkM15>tNe`"
    "V!s;qQL&ccQtA{_S;e253Wnd_y71--7|p>yRsP8AbT|Kx{F;qHy6J9FtGZGZdjiXE!^^k(eDVt;oZ<H=_ngzDQ4fXCiZKG(@"
    "EI-WA@V)9H{o)x<sJAJhs3l!aoU4908NVmoI`lUQD!?SQSI^7k$XDkQ`S5h}asZ7k};kbz}DZ40|wzJ{POu5|?KOne|1QY01"
    "Y+3<&58S()q8X+g|6(bh?POEjN7XRi0!7LEil=Hh^0;5H~w^mXANjMj|q&Yx<IWh?QHtDZoa4+-AL>ee`z1gSKI)`#S^c4~R"
    "1PlK)$d>>*VkG`xsn+O$&$v^k<$1K8R0+U1TOMY~pR+ktz?Q>pHLl(W@_pY`tFgobkYQ|d8Ml5MI5_hOYbROraUw5E?3TB$("
    "D933p!GjoyHD2%~bQN}U)(UDNhPu3JfGd?Hze348L?lRg7H!Jrj`lmXtoRH(UJ=5vz#Ado>8zFKV`%`KvRM2`QA%3X3Yj}g4"
    "Z)l69s8hKx+HijwvTk9fQNS3*mgToOp<7T*p!E()s5qIjo}%}c61|f1|^M@e{^!xsi@6enm1lUlXtbjdFK{=zX(q`#(0Q+rK"
    "(1)wC3zs86BjD?A=<UAvU=_){jP=8pp-gQAwgZYJPcWOzP-dyvOWE#5MYSW<BED+yznfBp+4~#u;DffJYGtebJ*pzutK=@z@"
    "_doyW}Vwd7J%S<`Np?1c4YY931BR#dH&`eNxfcpk3+%UU@tdFS~ka^9e8N6)SC0Re9~VK3>!KFEsf@z1AE-?5wv$CBC2D*~G"
    "Y+~KY+vK>@aW?jC&ZR+_RwZ0h<7#tKP^Tw&0U_+U}aj|)|H0mqocX&-po~9yzn$mk?dvtgvUE{PM(^0VOJWr@+*DxC=9@_;B"
    "$5`LA;>zvfPS06$ZETHv(ObfyKL8ggCG(DZokmDOvM#IWh`U$oj0v@|z3e|k5(&L=xTqw|Z!6Uj(FZZ0{i?5;*kG)O{K{<~Y"
    "1uUld_EUIEcG{v4gX6`Z`GA?VEo*Xk#p^%#j@Eo_MXKieFfCLC#I31t^p~d)><&h%{8%lL2Fs$Jzq<}LLH85k#8!)#J7#a56"
    "=11Nl<U^4Y~q{<XX~@cG6l9jp~Disr1uYs*CFU7qT7QHSX6#YQ(dc3t57VBbkR*Aul-CF5(eSDH<N_te45$sDk1mVF|-t4jn"
    "Hv-weLV_(=3;<{3agqUy5aWa4GGrZj5idoK&^oUc}vAsIh6S%u5z=<}$4l}8J%r-x{KgB~T5nZ^v0P6Lf|T2Yc8M91HfH5hv"
    "S9S%HTF@;>C$mpLt@H964;Yzpf>ejeO3F&KIv8Ol<KuCi0c#H}8!k@j3`Ugoj^`w`+_!qLy((u<hiyZ8KH0Yul#K`rWv>fEU"
    "w`g$e%#5UnNx8NtN(IFUK8#oDJzH{{jBQ!4s~j}@%w*JDT>Z_Y&7ZKDLIDSQ4v`?w!L17UT3Bl>ajTg?t0}K7=;lkBi1L(gX"
    "JB{g`@0#>c6_^czog*l%#}?TAI^xOAw2UgT_#;U8^`qlA{jK*>lREODihy^{%CFy#M27Ys4Qt08?<jz1ExC9i(Iy%F0Jrcdz"
    "9=Q5^K(Xs)RA}oor?~=SrPV=iRs~+hIqsC#^HX9)Cqxp+-PnZBOTz^_TmC{j3eW$ItNUUMU>1Oe2;9&X)%)<E6!KSZKM7ngP"
    "?9kTlxU?_9%*GAq0SzbU>WKK`Uv*zjxl5NrP2E0&cl_{)|ABkkPvISkT}{SVS^OOox1L3Ne*I{@AB?t1j`JJIVlk#1Da^Oru"
    "8Bg9r3)G|xs*2OxD>kLR~P*_~%e$gArIn`$fXgxrs&H2YsRtU-F7{G-&VwkNUp*pl->T$d@X1B2j*UEjL7`$h4pTlU<J2cyc"
    "j>-u-Cti#Z%2jnFtmmmMB6gm=Hn9I(<Mx`Fz|h$ErljV5^VRMgB7O3lXdCYPQJU7Z9hxo7K~UzC&HV&of0<=Wk~!mL0(Yaoc"
    "r)(eIZFbh(nK;!SF_6@JDQjUsQ{?=b(i#}{Blr2E#S1u^-_~Q$B{%5BZb^>+t$T;JWJ0=2kd(P*B~vp^BE!meX(Pd*XE4KFR"
    "Skv>dsQ`c`-S$D08oh@g(&X!iu^NLUVI~BR4L1khE8p<t765TJD7s008yAvVy#B#abYZiJM$ycVgY>c|@?9$v;uK2r>(k-6C"
    "qaKv>yztG&Z_!{8bH>3<C+C5+1fz?$SLJaV{mj(%1PqrxEs%3T`Mpw~-plU={^KFCFFZrCs2%KB594&mlZUWQ4GC2-EgQ#fL"
    "{Wyy8)=<AaZqM3>UekE+}yk<b<WVFk~=w`16Yc5HeujgmixzC-=6U)^`bKMJb`i>6v)*<Ld=zN;a0(_?4l)%QCEYvqcG9UWP"
    "b=UalU5imx>-J$gr3^}Z>t)Y|Tie9b!^wp;MqP<yC*YJ5klNH9%Vkr>g-vU1_#)eC?!#0I(X2R+y}E%r?=GBKMW@g4J@*N`j"
    "Uo(LrIHDJe}8qc&}^Un?4mY4wt@ZiWe#%v`Pt&TbWj^b59hFWRF9z{eqFgTph^gce{SZtC)RB@sK`Z%fOpRR70c(FY8E&HvU"
    "o?p8%I9j`up8?l@C*BuN+orN3HlROz74vuyJ0Umd81>H<KK#;2LZ@08HBewS_?y<P7ERS&0rRk_LG#*p`9<5r29_-;M_x??d"
    "3aK~@Dd_gouW?6V)y-(ZcZ6<OM@4SLYChhHt@=;1L>3`|@GFT94t<AbCT)q?Y{|9+5m0{*kXX^rH&6yJYbKI@<k^$wgj^<t_"
    "rZgqN+4B!rQ6E_zO>1k;5{YWH#37Hs5!Vb%1n3h8KCH{`H85^cpR;D1PkM)WDsu9o)`P|xd{W+0zu^v---#90;ZfBs5nvYC*"
    "`benpyx$Lm&3v7=Ku6Ms&17=J;!qQy4F?Z6@~EoOt?AP>u20bx*jTJ?f1Qp^Z<U&CrZn_f5hPe~%_}Fk5J^n#DY_a%i(2>%p"
    "}Mp2o|cY{UbC(|<+*DSHFkTc<v?*K@gRBv^-zQ)8OGgeocrL!3*nN5==(nC95=k_$U>}tpCpL7<lZKZokWiOQ#q0lP;p6&G7"
    "A5iCCMTvxKMsS32i636YT6$KPD5G@hQSO?w9oH&|_zl?6+?B)hm4#5`u?a`M)(~B3jPoA?4SMO&vsh74|i4*0*Pc;~_KLrP("
    "4^<IaJi%%Av(^P^$3!`6@N8U<Z7&JBn;Oq-W|ZX(WqZq|an$G^J9Q6r%D)zL5~uc$RK9bW?a`=76tl}=2v?XzN-OGEhO_sW*"
    "$%95S~2^3Lfqm%@)T1}<JC?>Vq4Q-c9TR^5ikIrj}+sW^=&uNxvoLwmL$U=3TcC`e?x5MSS?z^_VJwwR#A9c8LBqos5y|D4$"
    "6wS-%Ji}=N<AxHf6<LlgvKV=#Rbea*aNwZ?@Txt>%A&W5h7Agsa5Unpx@Xa+ylcpMz3lb2W->$U?;)CQqp+ze`RM5Po=+mIJ"
    "Qp2XkB9=}rO&=jCaq*6cO;~$-!F*NhV7C6(qpYm-{$#|Dz9wdwyEfat0r~NlxF++`?v0u%Tz8RT#fJt|D8*|$p@xL!7M=p;P"
    "Vr^>xOv0nDe8pqWCyh>ma()4|S~K&jHTM?d?XhBy*Al5~}}lVD;2|EtKB_@Rs@dCYk{CD1TlpzVvaJR_(OUj2Oz);M0l`7B1"
    ";iKEKetH{I-DkKOj|cE&nO!;A!iu`g(U!0ukGXD5h0{-B!aeRX@U$OS8KE#hgK`+Dop^p;U6>bM$#mllQNMW>6f8&6los6Y>"
    "ji(y4^beW=8ki!{0(RBm2MP>X}6`C~cFC}YmEKdHNCnI7KI?S!hV*|^H;uR~70#AP_g*S5Gp@Z`cVV1zZ5bSmM?PmJ-Pt5#y"
    "4MMpgb*bu07^9q-fRsjAhx<F!lY@^w<7V=Yck$477U37G@A1^hN+eFbcPhDaQH{p(@4Ni%|IYb2eUt-^`c@EpBi|O4bw(7be"
    "M()HxBlzI-?;y}+K>+VO%sM`nS=G%V|UQ8D9n%Z$rIJNv*ETU*!a-i5zag*pX-Cb^A7gKt?FY<-oBOQIOE}|&b@(N=o4I9W%"
    "8H-tyfNk%bXUN#|dQ@X(*XX?+>2_n*K%B1e>SVWNzKPTbQ5J97W;%WBm@}r(W-cehB6PSRUO1GEjdr@5iTvLUYZAWHsX_!JQ"
    "B}Ud(A?L4R3*NdVvlq6(wpDF(IfYIC^hnbkKY-~YZI2fDBE-FiH;&7==5Bjm`?ZWx!NKYf0T#ldFHq&?9el%Gdejq{?@$D|@"
    "v@cB1=9VFUo?BscnDPo3P-NN0}epH{L(V@q-gx%QsG7yECK^CBLk6sqen%@tlM?`MXB#;ba4tgNJnGUC3KQR66_6n%4hHP!B"
    "c~WgzeN{;YsMFm<l0rG$_L}E4YV>g;!C;8?-(9p@eiPl`OCy4rqC1n?jg3#jVzOnW1ZsZmzPLT!8H^>L(R&P%fsqoor-5tG_"
    "+Pte1gx~*7ke)w%_N*i9yVtsRz<rh#LfSjm-?>8u<?g2!=wt+j9|^jv4hEfEsIW%Wsh(KZ}M8jiTVO#r&pTu*f_Fe4%5V3D+"
    "@_GIc@sjWYAy0i}wrV4|A?1STMvi&z~dY1M_OikDyo^>B*L}@Z<XKdN!znu|W_R%p$(|a-u=jeYs%-f*W}sBpY0KMZr(y1q("
    "PoN?)+a3wR^3^l8Av;ZPDZ>!qf)c>e!NJnee>_TaKP&D^^4qajiHDISvzn8*OEcz^O8t?S8AnW5B1!t0?2%>IXcH8FyHO>%7"
    "W7{2BQqXh}S=NAeDx3*RBtDY@7b?gbnO<wH*CH<?LC#|q638Dch(=mf?AOgB-g2JgD95z0<-IQ%(qN}US2j85<E-RIwXr095"
    "b7{7`0yL1<82q;G$t_7wqxjjpU-P=sEO}PF9X<)j=4_z3C8eb4f$4!|HNz%4z*zL*n8-UY3|MDYf)s0vv3fXtZOv+W-<3`$O"
    "a{k*li?PhdW-ebKkp#g&#<Y1*MQAr+(`A$N-@9FyPtQzgExVJzFw8q6}%D7<zxWdA|aAZBLB}_4x_k^H=%dTUJ;ULh@Lrf9D"
    "sl0%l4qw9(}djlqSgASD{xqWExheFHqVT<@D0Z(K4VW!WgH^YbLXI1n$s}m7lI%uLs=X!R<}hENaBWG5c~MKw<v3xt=kz*hv"
    "urIWT_y&8{IqOpO5l<MzCBqWnfeMbr5&bLU1WmY>p)7MK3uI@8<`XaL)R^IM^I;mKC!1B^5Z*m%%*eDx3!^7he?59=NL7`K6"
    "%j(y1+myX?r(T~hVgjR)xss7uG^O(7;Tcafr@P5}AhMp6$`&Y=Cr|vom>U1NmyO2#Lbg3kB^!WVDj4FN*xwgjK0CWK!P683x"
    "qP9CW$qw0Hd4Y;TdaYAGjpmoE+sKhde~*v;>;uo;fBt2lQ6Bq9!B&tuuI{FB)H#dsxVgciSZWzN(Rx_mMGqE(y=Nv&cmD<{3"
    "znw4n%rV(?R!u8uZA$ox%*P+tp48B`gccmeB>)v;tO~;%`hZt*fJxVk}nt2dq?JBWG~3`j^uib=;m6d);`wIIAi_EhafE$x9"
    "T5nrR(f6%6Q`kwGBk_QT~_jR0B2I)R_Lbchy`iUDd!bDe-W`3?dVa@nBC~ckbpOSh;)u#BEbKCWESh-Y?q{O({}+U0|QLWjC"
    "8zeQF_Xb)K1mtXV0kCRC)aLmYdo75KxB0}aN#GamjV4Lc4vspqrbu=&xB<3G#3qO|0ja{luls~<turKl0XR}(0)=e!cofNlX"
    "!xES4g?y-656!t_h2V<u;xDb9OSJ3cRfR)yao*XxeGqvZ*tGuu)@5yW`DPrcB`P=hDS^nuS4?5ih1kR$l$cF08ib}*=%uPon"
    "R2@Ap{T)i_$O>;_6e(e{fjYZ>iDN%A5y!3WvnoS@k3TzAP4i7Dy0Viw@m2$9m+>qDe)tqhtqhMOLE_*bV#;YJ7pI?c+@*{$s"
    "K@d%H<$z2i$TFa;T5{u=*VHyw1)BVGdV^BZX3Z7!~0N6-pQ<K{KDg<%+Igeu9_BxY{hO&@!obrkXL4t7r)Wu0nIt^>-ND{IV"
    "L~t)hhq`udIEIHRhv2G`*mC{j6|PSzIUnfN}U$OTIl3s?Ee;&u0Z)Q+)}vvgkJJ=FONknn$e{2nzqwmNnR4^zdQ(as8*Ip8s"
    "TtarjT75;HKcD93ZbRyqC>2S9GemsXeT6Pop1qfv?aY|>5m*e0%Oqae5veh`Xy>DG}PB1*rT>H1+s(h_WQig9ug9%E?u{>d7"
    "<%J=71q=l#ow0*d`9A@^bs$5k~5UZw-_<)SorI~mQmapOKRT@oD%*_-=XIPJ`?}mUrj;8Tfqmo>&e<0bo$RRf;dBb>b&+I4l"
    "`A1FviXd<dBzJ5!C&a6H;*PnI8?GTV5(_1Vx|sc>;S(nMW9qdm7T8E8*!k(A??K=v<w=UR$<T{jdO%8ZU|ZhoNQ3^NZaf-%C"
    ")g^uSdU7o+Swm`a%5}z06KZlp4w9>_{5|(<X)1|e40pN5>g2NhXXt1up5_g;+PIH;UX@>f6pEt%;Bxg`+3Fd9!gr)5m(lxP*"
    "%?cRM!>xWgr|jCu7PnzShY&ItY6Q0quL^xJH&vn?RVW-{4Ie$<f6`rG7O!J=CC!zkSZnK>PlColB*WXzGK6*Z1iM-Cy2r^&T"
    "ETuox~<As6`?g6#GYu)$PHgIr!1oJ&`sKtQ1IXeAG`gy0x83qZ}*d=c#HI$wFo7jk;HaED{Zqfgqt+;uT+u`c^u+N!SQt%Yo"
    "~QSn_ySIPFbb{jXQ^S-HTtv2I&odRUd^!|Jn=@GFM{BChC_rL$rGcXnF+%C!bVw3B$xpj3i$#P(su{6psT6LM(;^cNcgmhcB"
    ")}q6ccc|rW`NL+nYVjrES0H9jqVr!c*?*3%DoMcnPm;2Ep(RuF8#bc5`dZn;8V2LwF8@mtuF0NhJ6Gg+WRHjF>9Lz=FCRGX+"
    "^y~SN=q;uSu{)Z-e}LwCvF=f4YXF+WvQ>hiFD+MWJc?Tam(8XM`q=q7sKxCYM43O`TF0!>TNehwMf;oH059u>(>OomwKS@Tb"
    "4FWm!G?4yl5RlL!Ca?=NQzQNspyPs!BiBQq#<|F#b>0{@<<13Bhs=%vAr}aZFh(ZDxWZ@Wh)3dB;y0eztiIOa`7c_LZ0BO5S"
    "H4?U&Ek+vjyiIWG!I=nE8o5ci(X41$_9cp%Vob*!w@Q#^4dnEp(o3ikH91CBW(QG+@9fGVn&R@fnZ@~y%MRuNJ=(9b37EXTR"
    "W>ues>{!e>juO)^kBKpBq$*yXliY6?Nd4sV74`lt_uTk^2S3$DeFY?*7k;VK~ZoH_vgc8azNwsWzzjxFwrL^J0X7)JpXWhJ+"
    "pJJciqvez|o{I<ZvNsnSfmi#x#9Db&Cs>D?m1gE0K$U;M<vZlkf>8}hCV(Vp4mo=691v)`;I)rlHf^3k`B~u$;14+PyW;fC1"
    "A+FfLR8#<&qJ8-53iV$H_r$~xP?a1mFlWB^P^*woz8E0>y9tc9v%&){@9x9($rJv@cN5*RC@KxS1s*EDw;Bv8ykWCJ%4g<Tg"
    "kUb$h<G#yk?${ss$czcu;i7Eu}3gij%ZkV$atFFO4qbwF6ClzGt<2%~tS`XzlyfvJWCB<ThHJY>SP#!v1D*pOP;s%ZUXg3wE"
    "9U?z=USNb;fmfqxZ*vjkd=Jb$?2w9WE&EzjS|ocyP4Ynk>n^ojr$Jd>+fhRt3370$Eyk7q2%Cvzhwld`fkVN$zw14Bql+#7n"
    "ljH_3&E+=ta4!pG++|Noxc|1Z2pJ&`7T?=drG?v%mpdV#z-^DV9?Y}#>pR1y8ZFzyyAH)x&Pp3?(4xAyF#iD@o<#TYm?1z)h"
    "?<}x3>N+o?P!9mLyt9Gmarb%kWKZ>ZoQJ6_Sb(;5DbO?z>{-O!!N1{Z73^Rnx~(fii)X+QX(7949?nF3;4|q*+`8mC`U%Gbn"
    "U-CKncV6HH&RlC?G=}La4YeR%Xsv4tMj52TZ6~m?!p8di$WqX0gDnTi?yh~C{$N>>adsnW|WlR4D2OUfbcTdGvhX0#W9~z>;"
    "RvJ57L5Tt{tzWpI)Bc`ibYm`h`U%vZxmBbJU+!7^=o=eD;74@b07EUURw&yBTpfv+q_?^}Lw<9N)IM^wAHhJsr1yIJj+LN-O"
    "ZmJac32c>w6-E3B>6>-c_~E0DaoSXXlP88v=`omi;u3-*eSprORI1HYMtILPSEY^4NRVy_)pL)Im8!*pNju=f{*5~J`!3UV!"
    "!O5@!TGN5<?_YQ^^|D#fo0jx$u{3x$?3b%oak1OZWfd4)Jd;a(Qf1aSeU<^d#=nlJkFnI3v17$@Gg_>9IgZ~eF8Tp("
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

EXECUTOR_NAMES = [
    "Volt",
    "Potassium",
    "Wave",
    "Seliware",
    "Synapse Z",
    "Madium",
    "Velocity",
    "SirHurt",
    "Solara",
    "Xeno",
    "RbxCli",
    "Ronin",
    "Matcha",
    "Matrix Hub",
    "Photon",
    "DX9WARE V2",
    "Serotonin",
    "Severe",
    "MacSploit",
    "Opiumware",
    "Delta",
    "Cryptic",
    "Vega X",
    "Codex",
]

# Verified sample SHA256 (lowercase hex) -> label. Extend in code or assets/executor_sha256_blocklist.json.
EXECUTOR_SHA256_BLOCKLIST: dict[str, str] = {}
EXECUTOR_HASH_SCAN_MAX_FILES = 400
EXECUTOR_HASH_MAX_FILE_BYTES = 120_000_000
EXECUTOR_ACTIVITY_RECENT_HOURS = 72

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
)

# File-name-only cheat / hack hints (matched on basename, not full path).
CHEAT_FILENAME_HINT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
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
    ("exploit", re.compile(r"\bexploit\b", re.IGNORECASE)),
    ("free_cheat", re.compile(r"free[\s._-]*cheat", re.IGNORECASE)),
    ("rbx_cheat", re.compile(r"rbx[\s._-]*cheat|rbx[\s._-]*hack", re.IGNORECASE)),
]

USER_FOLDER_SCAN_EXTENSIONS = frozenset({".exe", ".dll", ".txt", ".json", ".log", ".bat", ".ps1"})
# Kept for backwards reference only; the actual scan now covers the full home directory.
USER_FOLDER_SCAN_SUBDIRS = ("Downloads", "Desktop", "Documents")
USER_FOLDER_SCAN_MAX_DEPTH = 8
USER_FOLDER_SCAN_MAX_ENUMERATED = 200_000
USER_FOLDER_SCAN_MAX_HITS = 500
USER_FOLDER_TRUSTED_APP_STEMS = frozenset(
    {
        # Executables often used as disguises when dropped into user folders.
        "discord",
    }
)
SCAN_WORKERS = min(10, (os.cpu_count() or 4) + 2)


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
    """Cover the full user home (includes AppData, Temp, etc.) so no subfolder escapes hashing."""
    roots: list[tuple[Path, int]] = []
    seen: set[Path] = set()
    for folder in designated_user_folder_roots():
        if folder not in seen:
            seen.add(folder)
            roots.append((folder, USER_FOLDER_SCAN_MAX_DEPTH))
    # Also scan system Temp in case the executor was staged outside the user profile.
    if platform.system() == "Windows":
        tmp = os.getenv("TEMP") or os.getenv("TMP")
        if tmp:
            candidate = Path(tmp)
            if candidate.is_dir() and candidate not in seen:
                seen.add(candidate)
                roots.append((candidate, 6))
    return roots


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
    )
    return any(fragment in low for fragment in excluded)


def path_is_allowlisted(path_str: str) -> bool:
    low = path_str.lower().replace("/", "\\")
    return any(fragment in low for fragment in PATH_ALLOWLIST_FRAGMENTS)


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


def executor_blocklist_path_scan(
    blocklist: dict[str, str],
    max_hashes: int = EXECUTOR_HASH_SCAN_MAX_FILES,
) -> tuple[list[dict], int]:
    """Hash user-profile executables; ignores path allowlists so disguised paths still match."""
    if not blocklist:
        return [], 0
    hits: list[dict] = []
    hashed = 0
    seen_paths: set[str] = set()
    for root, max_depth in executor_user_hash_scan_roots():
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
                        "renamed_disguise": not any(
                            pat.search(path.name) for pat in executor_name_patterns().values()
                        ),
                    }
                )
                if len(hits) >= 40:
                    break
        except (PermissionError, OSError):
            continue
        if hashed >= max_hashes or len(hits) >= 40:
            break
    return hits, hashed


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

    for log in roblox_diagnostics().get("logs", []):
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
    """Return the entire user home directory so no subfolder can be used as a hiding spot."""
    roots: list[Path] = []
    if platform.system() == "Windows":
        base = os.getenv("USERPROFILE")
        if base:
            home = Path(base)
            if home.is_dir():
                roots.append(home)
    else:
        home = Path.home()
        if home.is_dir():
            roots.append(home)
    return roots


def walk_files_depth_limited(root: Path, max_depth: int):
    try:
        root = root.resolve()
    except Exception:
        root = root
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        try:
            rel_depth = len(current.relative_to(root).parts)
        except ValueError:
            dirnames[:] = []
            continue
        if rel_depth >= max_depth:
            dirnames.clear()
        for fn in filenames:
            yield current / fn


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


def combined_user_folder_security_scans(max_hashes: int = EXECUTOR_HASH_SCAN_MAX_FILES) -> tuple[dict, dict]:
    """Designated-folder name hits plus full-file SHA256 blocklist scan (renames / disguised folders)."""
    patterns = executor_name_patterns()
    roots = designated_user_folder_roots()
    hits: list[dict] = []
    enumerated = 0
    enumeration_reached_cap = False
    skipped_permission = 0
    blocklist = load_executor_sha256_blocklist()
    sha_hits, hashed = executor_blocklist_path_scan(blocklist, max_hashes=max_hashes)

    for root in roots:
        try:
            for path in walk_files_depth_limited(root, USER_FOLDER_SCAN_MAX_DEPTH):
                enumerated += 1
                if enumerated > USER_FOLDER_SCAN_MAX_ENUMERATED:
                    enumeration_reached_cap = True
                    break
                try:
                    if not path.is_file():
                        continue
                except OSError:
                    continue

                ext = path.suffix.lower()
                if ext not in USER_FOLDER_SCAN_EXTENSIONS:
                    continue
                stem = path.stem
                full_name = path.name
                executor_labels = sorted(set(match_executor_labels(full_name, patterns)))
                weird = weird_filename_reasons(stem, full_name)
                cheat_hints = cheat_filename_hint_labels(full_name)
                if not executor_labels and not weird and not cheat_hints:
                    continue
                try:
                    stat = path.stat()
                except OSError:
                    continue
                entry = {
                    "path": str(path),
                    "name": full_name,
                    "extension": ext,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "executor_name_hits": executor_labels,
                    "name_anomaly_reasons": weird,
                    "cheat_filename_hints": cheat_hints,
                    "path_allowlisted": path_is_allowlisted(str(path)),
                }
                hits.append(entry)
                if len(hits) >= USER_FOLDER_SCAN_MAX_HITS:
                    break
        except PermissionError:
            skipped_permission += 1
        except OSError:
            skipped_permission += 1
        if len(hits) >= USER_FOLDER_SCAN_MAX_HITS or enumeration_reached_cap:
            break

    executor_hits = sum(1 for item in hits if item["executor_name_hits"])
    cheat_only = sum(
        1
        for item in hits
        if (item.get("cheat_filename_hints") or [])
        and not item["executor_name_hits"]
        and not item["name_anomaly_reasons"]
    )
    weird_only = sum(1 for item in hits if not item["executor_name_hits"] and item["name_anomaly_reasons"])

    designated = {
        "hit_count": len(hits),
        "executor_name_hits": executor_hits,
        "cheat_filename_only_hits": cheat_only,
        "weird_name_only_hits": weird_only,
        "skipped_roots_permission_errors": skipped_permission,
        "hits": hits,
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
    return {
        "status": "Recycle Bin metadata collected" if items else "No accessible Trash/Recycle Bin item found",
        "count": len(items[:180]),
        "latest": items[0] if items else None,
        "items": items[:180],
        "note": "Windows: all fixed-drive $Recycle.Bin folders scanned. $I metadata lists original paths before "
        "emptying; after permanent delete, USN / Security / Sysmon samples below may still show evidence.",
    }


def prefetch_metadata() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows Prefetch is only available on Windows"}

    folder = Path(os.getenv("SystemRoot", "C:\\Windows")) / "Prefetch"
    if not folder.exists():
        return {"available": False, "reason": "Prefetch folder not found"}

    items = []
    try:
        files = sorted(folder.glob("*.pf"), key=lambda path: path.stat().st_mtime, reverse=True)[:120]
    except Exception as exc:
        return {"available": False, "reason": str(exc)}

    for path in files:
        try:
            stat = path.stat()
            items.append(
                {
                    "name": path.name,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
                    "size_bytes": stat.st_size,
                }
            )
        except Exception:
            continue
    return {"available": True, "folder": str(folder), "count": len(items), "items": items}


def amcache_metadata() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Amcache is a Windows artifact"}

    path = Path(os.getenv("SystemRoot", "C:\\Windows")) / "AppCompat" / "Programs" / "Amcache.hve"
    if not path.exists():
        return {"available": False, "path": str(path), "reason": "Amcache hive not found"}

    try:
        stat = path.stat()
        return {
            "available": True,
            "path": str(path),
            "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime, timezone.utc).isoformat(),
            "size_bytes": stat.st_size,
            "note": "Raw hive parsing is not performed by this prototype.",
        }
    except Exception as exc:
        return {"available": False, "path": str(path), "reason": str(exc)}


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
        "$keywords=@('Roblox','executor','loader','bootstrapper','script','inject','bypass','cleaner');"
        "foreach($k in $keywords){ if($decoded -match [regex]::Escape($k)){ $matches += $k } }"
        "$out += [pscustomobject]@{DecodedPath=$decoded; MatchedKeywords=$matches; LastRunFileTimeUtc=$lastRun}"
        "}"
        "}"
        "};"
        "$out | Select-Object -First 120 | ConvertTo-Json -Depth 4"
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
            structured.append(
                {
                    "path": path,
                    "matched_keywords": list(row.get("MatchedKeywords") or []),
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


def windows_defender_signals() -> dict:
    if platform.system() != "Windows":
        return {"available": False, "reason": "Windows Defender signals are Windows-only"}

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
        "} catch { $_.Exception.Message }"
    )
    history_script = (
        "$start=(Get-Date).AddDays(-14);"
        "Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Windows Defender/Operational'; StartTime=$start} "
        "-ErrorAction SilentlyContinue | "
        "Select-Object -First 80 TimeCreated,Id,LevelDisplayName,Message | ConvertTo-Json -Depth 3"
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        settings_future = pool.submit(
            run_command, ["powershell", "-NoProfile", "-Command", preference_script], 12, 12000
        )
        history_future = pool.submit(
            run_command, ["powershell", "-NoProfile", "-Command", history_script], 18, 20000
        )
        settings = settings_future.result()
        history = history_future.result()
    return {
        "available": True,
        "settings": settings[:12000],
        "protection_history": history[:20000],
    }


def recent_items_metadata() -> dict:
    folders = []
    if platform.system() == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            folders.append(Path(appdata) / "Microsoft" / "Windows" / "Recent")
        userprofile = os.getenv("USERPROFILE")
        if userprofile:
            folders.extend([Path(userprofile) / "Downloads", Path(userprofile) / "Desktop"])
    else:
        folders.extend([Path.home() / "Downloads", Path.home() / "Desktop"])

    items = []
    patterns = executor_name_patterns()
    for folder in folders:
        if not folder.exists():
            continue
        try:
            paths = [path for path in folder.iterdir() if path.is_file()]
        except Exception:
            continue
        for path in paths:
            try:
                stat = path.stat()
                fname = path.name
                matched_exec = [label for label, pat in patterns.items() if pat.search(fname)]
                cheat_hints = cheat_filename_hint_labels(fname)
                if not matched_exec and not cheat_hints:
                    continue
                items.append(
                    {
                        "name": fname,
                        "folder": str(folder),
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
    return {"count": len(items[:120]), "items": items[:120], "note": "Only files whose names match known executor brands or cheat/hack filename hints are listed (not every file in these folders)."}


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

    keywords = EXECUTOR_NAMES + ["prefetch", "usn", "fsutil", "journal", "wevtutil", "clear-log", "Clear-EventLog", "Set-MpPreference", "Add-MpPreference", "Unblock-File", "Potassium"]
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
    extended_script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$start=(Get-Date).AddDays(-14);"
        "$usnList = New-Object System.Collections.Generic.List[string];"
        "foreach ($d in (Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object { $_.DeviceID })) {"
        " try {"
        "  fsutil usn readjournal $d csv 2>$null |"
        "    Select-String -Pattern 'FILE_DELETE|0x80000002|0x80000200' |"
        "    Select-Object -First 45 |"
        "    ForEach-Object { [void]$usnList.Add(($d + [char]9 + $_.Line)) }"
        " } catch {}"
        "};"
        "$sec = @();"
        "try {"
        " $sec = Get-WinEvent -FilterHashtable @{LogName='Security'; StartTime=$start; Id=4660,4663} -MaxEvents 250 -ErrorAction SilentlyContinue |"
        "   Where-Object { $_.Message -match '(?i)delete|eliminated|removed' } |"
        "   Select-Object -First 50 @{N='TimeCreated';E={$_.TimeCreated.ToString('u')}},Id,"
        "   @{N='Message';E={ if ($_.Message.Length -gt 1200) { $_.Message.Substring(0,1200) } else { $_.Message } }}"
        "} catch {};"
        "$sm = @();"
        "try {"
        " $sm = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Sysmon/Operational'; StartTime=$start; Id=23} -MaxEvents 120 -ErrorAction SilentlyContinue |"
        "   Select-Object -First 55 @{N='TimeCreated';E={$_.TimeCreated.ToString('u')}},"
        "   @{N='Message';E={ if ($_.Message.Length -gt 1400) { $_.Message.Substring(0,1400) } else { $_.Message } }}"
        "} catch {};"
        "[pscustomobject]@{"
        " usn_file_delete_lines = @($usnList | Select-Object -First 130);"
        " security_object_deletion_events = @($sec);"
        " sysmon_file_delete_events = @($sm)"
        "} | ConvertTo-Json -Depth 5 -Compress"
    )
    ps = ["powershell", "-NoProfile", "-Command"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        event_future = pool.submit(run_command, ps + [event_script], 20, 20000)
        extended_future = pool.submit(run_command, ps + [extended_script], 28, 32000)
        event_sample = event_future.result()
        extended_raw = extended_future.result()
    extended_parsed: dict | str
    try:
        extended_parsed = json.loads(extended_raw) if extended_raw and not extended_raw.startswith("Unavailable:") else {"raw": extended_raw}
    except json.JSONDecodeError:
        extended_parsed = {"json_parse_error": True, "raw_head": extended_raw[:4000]}

    usn_lines: list | None = None
    if isinstance(extended_parsed, dict):
        raw_lines = extended_parsed.get("usn_file_delete_lines")
        if isinstance(raw_lines, list) and raw_lines:
            usn_lines = raw_lines
    usn_text = "\n".join(str(line) for line in usn_lines) if usn_lines else ""
    if not usn_text.strip():
        usn_text = run_command(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "$d=$env:SystemDrive; try { fsutil usn readjournal $d csv 2>$null | Select-String -Pattern 'FILE_DELETE' | "
                "Select-Object -First 60 | ForEach-Object { $_.Line } } catch { }",
            ],
            timeout=12,
            max_chars=12000,
        )

    return {
        "available": True,
        "window": "last 30 days (general events); last 14 days (USN / Security / Sysmon file delete)",
        "raw_sample": event_sample,
        "deleted_file_evidence": extended_parsed,
        "usn_delete_sample": usn_text[:20000],
        "note": "Recycle Bin $I metadata (in trash report) shows files still in the bin. After emptying or Shift+Delete, "
        "look here: USN FILE_DELETE lines (Admin may be required), Security 4660/4663 if auditing is on, Sysmon ID 23 if installed, "
        "and general event raw_sample.",
    }


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
        r"Remove-Item.*Prefetch|del\s+/f.*\.pf|cipher\s+/w",
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
            r"Set-MpPreference.*DisableRealtimeMonitoring|Unblock-File|del\s+/[fq]",
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

    patterns = executor_name_patterns()
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
            item
            for item in items
            if any(pattern.search(item["name"]) for pattern in patterns.values())
        ][:80],
    }


def executor_indicator_scan() -> dict:
    patterns = executor_name_patterns()
    file_hits: list[dict] = []
    traceback_hits: list[dict] = []
    scanned_files = 0

    roots_spec: list[tuple[Path, int | None]] = []

    if platform.system() == "Windows":
        la = os.getenv("LOCALAPPDATA")
        if la:
            roots_spec.append((Path(la), 8))
        ap = os.getenv("APPDATA")
        if ap:
            roots_spec.append((Path(ap), 6))
        tmp = os.getenv("TEMP")
        if tmp:
            roots_spec.append((Path(tmp), 4))
        up = os.getenv("USERPROFILE")
        if up:
            home_root = Path(up)
            if home_root.is_dir():
                roots_spec.append((home_root, USER_FOLDER_SCAN_MAX_DEPTH))
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
                    if len(file_hits) >= 200 and len(traceback_hits) >= 80:
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
        "file_hits": file_hits[:200],
        "traceback_or_log_hits": traceback_hits[:80],
    }


def extract_roblox_signals(text: str) -> dict:
    user_ids = sorted(set(re.findall(r"\b(?:userId|UserId|userid|uid)[=: ]+(\d{3,})\b", text)))[:40]
    usernames = sorted(set(re.findall(r"\b(?:username|Username|userName|UserName)[=: ]+([A-Za-z0-9_]{3,20})\b", text)))[:40]
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
    candidates: list[Path] = []
    if platform.system() == "Windows":
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            candidates.append(Path(local_app_data) / "Roblox" / "logs")
    elif platform.system() == "Darwin":
        candidates.append(Path.home() / "Library" / "Logs" / "Roblox")

    logs = []
    for folder in candidates:
        if folder.exists():
            for path in sorted(folder.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]:
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

    return {"detected": bool(logs), "log_locations_checked": [str(path) for path in candidates], "logs": logs}



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
    if len(unique) == 1:
        path = unique[0]
        safe = path.replace("'", "''")
        script = (
            f"try {{ (Get-AuthenticodeSignature -LiteralPath '{safe}' -ErrorAction Stop).Status.ToString() }} "
            f"catch {{ 'Error:' + $_.Exception.Message }}"
        )
        out = run_command(["powershell", "-NoProfile", "-Command", script], timeout=12, max_chars=400)
        return {path: (out or "unknown").strip()[:120]}
    results: dict[str, str] = {}
    chunk_size = 28
    for start in range(0, len(unique), chunk_size):
        chunk = unique[start : start + chunk_size]
        paths_json = json.dumps(chunk)
        script = (
            f"$paths = @({paths_json} | ConvertFrom-Json); "
            "$out = @{}; "
            "foreach ($p in $paths) { "
            "  if (Test-Path -LiteralPath $p) { "
            "    try { $out[$p] = (Get-AuthenticodeSignature -LiteralPath $p -ErrorAction Stop).Status.ToString() } "
            "    catch { $out[$p] = 'Error' } "
            "  } else { $out[$p] = 'Missing' } "
            "}; "
            "$out | ConvertTo-Json -Compress"
        )
        raw = run_command(
            ["powershell", "-NoProfile", "-Command", script],
            timeout=min(18 + len(chunk), 45),
            max_chars=12000,
        )
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            for key, value in parsed.items():
                results[str(key)] = str(value).strip()[:120]
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
$rows | Select-Object -First 320 | ConvertTo-Json -Compress -Depth 3
}
""".strip()
    data = forensic_powershell_json(script, timeout=26.0, max_chars=32000)
    items: list[dict[str, object]] = []
    if isinstance(data, list):
        items = [dict(x) for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        items = [dict(data)]
    normalized: list[dict[str, object]] = []
    for it in items:
        raw_path = str(it.get("RegValueName") or "")
        norm = forensic_normalize_pathish(raw_path)
        ft = it.get("FileTimeUtc")
        try:
            ft_int = int(ft) if ft is not None else 0
        except (TypeError, ValueError):
            ft_int = 0
        iso = windows_filetime_to_iso(ft_int) if ft_int else None
        exists = False
        if norm and re.match(r"^[A-Za-z]:\\", norm):
            try:
                exists = Path(norm).is_file()
            except OSError:
                exists = False
        normalized.append(
            {
                "registry_path_value": raw_path,
                "normalized_path": norm,
                "last_execution_utc": iso,
                "file_exists": exists,
                "sid": it.get("Sid"),
            }
        )
    return {"available": True, "items": normalized, "source": "BAM UserSettings"}


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
                exists = target.is_file()
                if exists:
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


def usn_journal_enriched_sample() -> dict[str, object]:
    if platform.system() != "Windows":
        return {"available": False, "lines": [], "reason": "Windows-only"}
    script = r"""
$ErrorActionPreference='SilentlyContinue'
$usnList = New-Object System.Collections.Generic.List[string]
foreach ($d in (Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object { $_.DeviceID })) {
  try {
    fsutil usn readjournal $d csv 2>$null |
      Select-String -Pattern 'RENAME_|FILE_CREATE|FILE_DELETE|CLOSE|DATA_EXTEND|BASIC_INFO_CHANGE|STREAM_CHANGE|\.EXE|\.DLL|\.PS1|\.BAT|:|TEMP|TMP|Downloads' |
      Select-Object -First 160 |
      ForEach-Object { [void]$usnList.Add(($d + [char]9 + $_.Line)) }
  } catch {}
}
$usnList | Select-Object -First 160 | ConvertTo-Json -Compress
""".strip()
    data = forensic_powershell_json(script, timeout=28.0, max_chars=32000)
    lines: list[str] = []
    if isinstance(data, list):
        lines = [str(x) for x in data]
    return {"available": True, "lines": lines, "source": "fsutil usn readjournal (bounded)"}


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
    )
    for label, base in mapping:
        if base.is_dir():
            roots.append((label, base))
    return roots


def _chromium_history_database_paths() -> list[tuple[str, str, Path]]:
    paths: list[tuple[str, str, Path]] = []
    for browser, base in _chromium_user_data_roots():
        for prof in ("Default", "Profile 1", "Profile 2", "Profile 3"):
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
    labels.extend(cheat_filename_hint_labels(_download_basename(path)))
    if not labels and url:
        lower = url.lower()
        if any(ext in lower for ext in (".exe", ".dll", ".bat", ".ps1", ".msi", ".zip", ".rar", ".7z")):
            labels.append("download_url_extension")
    return bool(labels), labels


def _read_chromium_downloads(browser: str, profile: str, history_db: Path, patterns: dict[str, re.Pattern[str]]) -> list[dict]:
    items: list[dict] = []
    uri = f"file:{history_db.as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=2.5)
    except sqlite3.Error:
        try:
            conn = sqlite3.connect(str(history_db), timeout=2.5)
        except sqlite3.Error:
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
    uri = f"file:{db_path.as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=2.5)
    except sqlite3.Error:
        try:
            conn = sqlite3.connect(str(db_path), timeout=2.5)
        except sqlite3.Error:
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
            started = chrome_webkit_time_to_iso(start_time)
            ended = chrome_webkit_time_to_iso(end_time)
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
        "note": "Reads Chrome, Edge, Brave (History downloads table) and Firefox (downloads.sqlite). "
        "Includes completed and interrupted downloads when the browser database is accessible.",
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

    usn_lines = list(usn_extra.get("lines") or [])
    usn_text = str(deletion.get("usn_delete_sample") or "")
    if usn_text:
        usn_lines.extend(usn_text.splitlines()[:120])
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
        "usn_file_lifecycle_rows": usn_records[:220],
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
    with ThreadPoolExecutor(max_workers=min(6, SCAN_WORKERS)) as pool:
        bam_future = pool.submit(bam_execution_records)
        pca_future = pool.submit(pca_executed_records)
        sqlite_future = pool.submit(sqlite_forensic_probe)
        usn_future = pool.submit(usn_journal_enriched_sample)
        bam_struct = bam_future.result()
        pca = pca_future.result()
        sqlite_pack = sqlite_future.result()
        usn_extra = usn_future.result()
    usn_lines = list(usn_extra.get("lines") or [])
    usn_text = str(deletion.get("usn_delete_sample") or "")
    if usn_text:
        usn_lines.extend(usn_text.splitlines()[:120])
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
    extra: dict | None = None,
) -> None:
    display_at = occurred_at
    resolved_source = timestamp_source or ("recorded" if occurred_at else None)
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
            extra={"deleted_at_raw": item.get("deleted_at")},
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
        )

    usn_rows = (forensic_bundle.get("usn_file_lifecycle_rows") or []) if isinstance(forensic_bundle, dict) else []
    for row in usn_rows[:160]:
        reasons = row.get("reasons") or []
        if not reasons:
            continue
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
        )

    for item in bam.get("items") or []:
        path = str(item.get("normalized_path") or item.get("registry_path_value") or "")
        if not path:
            continue
        _append_activity_event(
            events,
            category="execution",
            kind="bam_execution",
            label="Program executed",
            path=path,
            occurred_at=item.get("last_execution_utc"),
            timestamp_source="bam_registry",
            detail="Background Activity Moderator last execution timestamp.",
            generated_at=generated_at,
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
            r"cipher\s+/w|cleaner|trace\s*wipe",
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
        "$cut=(Get-Date).AddDays(-21);"
        "$roots=@("
        "(Join-Path $env:USERPROFILE 'Downloads'),"
        "(Join-Path $env:USERPROFILE 'Desktop'),"
        "(Join-Path $env:USERPROFILE 'Documents'),"
        "$env:TEMP,"
        "(Join-Path $env:LOCALAPPDATA 'Temp')"
        ");"
        "$out=@();"
        "foreach($root in $roots){"
        " if(-not(Test-Path -LiteralPath $root)){continue}"
        " Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue |"
        " Where-Object { $_.Extension -match '^\\.(exe|dll|bat|ps1)$' -and $_.LastWriteTime -ge $cut } |"
        " Select-Object -First 120 | ForEach-Object {"
        "  $out += [pscustomobject]@{"
        "    Path=$_.FullName;"
        "    Name=$_.Name;"
        "    Modified=$_.LastWriteTimeUtc.ToString('u');"
        "    SizeBytes=$_.Length"
        "  }"
        " }"
        "};"
        "$out | Sort-Object Modified -Descending | Select-Object -First 100 | ConvertTo-Json -Compress"
    )
    raw = run_command(["powershell", "-NoProfile", "-Command", script], timeout=22, max_chars=28000)
    items: list[dict] = []
    try:
        if raw and not raw.startswith("Unavailable:"):
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else [parsed]
            for row in rows:
                if isinstance(row, dict) and row.get("Path"):
                    items.append(
                        {
                            "path": str(row.get("Path")),
                            "name": str(row.get("Name") or _digest_basename(str(row.get("Path")))),
                            "modified": row.get("Modified"),
                            "size_bytes": row.get("SizeBytes"),
                            "source": "disk_enumeration",
                        }
                    )
    except json.JSONDecodeError:
        pass
    return {"available": True, "count": len(items), "items": items}


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
            row["file_exists"] = Path(path).is_file()
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
        labels = match_executor_labels(path, patterns)
        labels.extend(cheat_filename_hint_labels(_digest_basename(path)))
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
        labels.extend(item.get("name_anomaly_reasons") or [])
        upsert(
            path,
            source="folder_scan",
            occurred_at=item.get("modified"),
            labels=labels,
            suspicious=bool(labels),
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
        if not path:
            continue
        labels = match_executor_labels(path, patterns)
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


def build_last_computer_activity(
    *,
    generated_at: str,
    boot_time: str | None,
    user_activity: dict,
    execution_activity: dict,
    download_history: dict | None = None,
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
        "deletions": "A file was deleted or moved to the Recycle Bin.",
        "execution": "A program was run or launched on this PC.",
        "files": "A file in a watched folder was touched or matched.",
        "persistence": "Something was set to start with Windows.",
        "commands": "A command line matched reviewed words.",
        "roblox": "Roblox log activity was recorded.",
        "browser": "Browser history matched reviewed words.",
        "filesystem": "A filesystem change was logged.",
    }
    events: list[dict] = []
    for dl in (download_history or {}).get("items") or []:
        started = dl.get("started_at") or dl.get("ended_at")
        if not started:
            continue
        fname = str(dl.get("file_name") or "a file")
        events.append(
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
        events.append(
            {
                "occurred_at": event.get("occurred_at"),
                "category": cat,
                "summary": category_plain.get(cat) or "Activity was recorded on this PC.",
                "path": event.get("path"),
            }
        )
    events.sort(key=lambda e: _digest_sort_ts(e), reverse=True)

    return {
        "available": True,
        "boot_time": boot_time,
        "scan_time": generated_at,
        "milestone_count": len(milestones),
        "milestones": milestones,
        "event_count": len(events),
        "recent_event_count": user_activity.get("recent_execution_count", 0)
        + user_activity.get("recent_deletion_count", 0),
        "execution_count": execution_activity.get("event_count", 0),
        "events": events[:120],
    }


def build_scan_review_bundle(
    *,
    generated_at: str,
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
    )
    string_detection = build_string_detection_hits(
        command_history=command_history,
        roblox=roblox,
        designated=designated,
        executor_indicators=executor_indicators,
    )
    last_computer_activity = build_last_computer_activity(
        generated_at=generated_at,
        boot_time=boot_time,
        user_activity=user_activity,
        execution_activity=execution_activity,
        download_history=browser_download_history,
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


def build_report() -> dict:
    scan_started_at = datetime.now(timezone.utc).isoformat()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home().anchor or Path.home()))

    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        fut_prefetch = pool.submit(prefetch_metadata)
        fut_deletion = pool.submit(deletion_and_log_clearing_signals)
        fut_folders = pool.submit(combined_user_folder_security_scans)

        prefetch = fut_prefetch.result()
        deletion_signals = fut_deletion.result()
        designated, sha_blocklist = fut_folders.result()

        fut_forensic = pool.submit(build_forensic_analysis_bundle, designated, prefetch, deletion_signals)
        fut_hardware = pool.submit(hardware_identifiers)
        fut_apps = pool.submit(installed_apps_summary)
        fut_trash = pool.submit(recycle_bin_metadata)
        fut_roblox = pool.submit(roblox_diagnostics)
        fut_amcache = pool.submit(amcache_metadata)
        fut_userassist = pool.submit(userassist_registry_entries)
        fut_defender = pool.submit(windows_defender_signals)
        fut_events = pool.submit(windows_event_log_summary)
        fut_xml = pool.submit(xml_event_log_files)
        fut_recent = pool.submit(recent_items_metadata)
        fut_cmdhist = pool.submit(command_history_keyword_hits)
        fut_services = pool.submit(windows_service_signals)
        fut_usb = pool.submit(usb_event_summary)
        fut_shellbag = pool.submit(shellbag_clear_signal)
        fut_pref_health = pool.submit(prefetch_health_signals, prefetch)
        fut_exec_ind = pool.submit(executor_indicator_scan)
        fut_persist = pool.submit(persistence_signals)
        fut_roblox_int = pool.submit(roblox_integrity_scan, prefetch)
        fut_disk_exe = pool.submit(recent_disk_executable_scan)
        fut_browser_downloads = pool.submit(browser_download_history_scan)

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
                if item.get("file_exists")
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
        executor_indicators = fut_exec_ind.result()
        persistence = fut_persist.result()
        recent_items = fut_recent.result()
        generated_at = datetime.now(timezone.utc).isoformat()
        trash = fut_trash.result()
        userassist = fut_userassist.result()
        roblox = fut_roblox.result()
        command_history = fut_cmdhist.result()
        browser_download_history = fut_browser_downloads.result()
        usn_rows = forensic_bundle.get("usn_file_lifecycle_rows") or []
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
            defender=fut_defender.result(),
            shellbag=fut_shellbag.result(),
            bam=bam_registry,
            forensic_bundle=forensic_bundle,
            prefetch_health=prefetch_health,
            amcache=fut_amcache.result(),
            command_history=command_history,
        )
        in_scan_changes = in_scan_binary_change_signals(
            usn_rows=usn_rows if isinstance(usn_rows, list) else [],
            bam_items=bam_registry.get("items") or [],
        )
        disk_executables = fut_disk_exe.result()
        boot_time_iso = datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat()
        scan_review = build_scan_review_bundle(
            generated_at=generated_at,
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
        )

    processes = []
    for proc in psutil.process_iter(["pid", "name", "username", "status"]):
        try:
            info = proc.info
            processes.append({"pid": info["pid"], "name": info["name"], "status": info["status"]})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

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
            "hardware": fut_hardware.result(),
        },
        "performance_environment": {
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "boot_time": datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat(),
            "installed_applications": fut_apps.result(),
            "trash": trash,
            "prefetch": prefetch,
        },
        "application_diagnostics": {"roblox": roblox},
        "process_overview": {
            "count": len(processes),
            "items": sorted(processes, key=lambda item: (item["name"] or "").lower())[:250],
        },
        "security_integrity_signals": {
            "amcache": fut_amcache.result(),
            "bam": bam_registry,
            "userassist": userassist,
            "defender": fut_defender.result(),
            "windows_event_logs": fut_events.result(),
            "xml_event_log_files": fut_xml.result(),
            "recent_items": fut_recent.result(),
            "command_history_keyword_hits": command_history,
            "services": fut_services.result(),
            "usb_events": fut_usb.result(),
            "shellbag_clear_signal": fut_shellbag.result(),
            "deletion_and_log_clearing_signals": deletion_signals,
            "prefetch_health": prefetch_health,
            "roblox_executor_indicators": executor_indicators,
            "designated_folder_suspicious_files": designated,
            "executor_sha256_blocklist": sha_blocklist,
            "executor_activity_summary": executor_activity,
            "user_activity_timeline": user_activity,
            "persistence_signals": persistence,
            "roblox_runtime_integrity": fut_roblox_int.result(),
            "forensic_analysis": forensic_bundle,
            "bypass_resilience": bypass_resilience,
            "scan_review": scan_review,
            "browser_download_history": browser_download_history,
            "binary_change_signals_in_scan": in_scan_changes,
        },
    }


class DiagnosticApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Virello Scanner")
        self.root.geometry("760x620")
        self.root.configure(bg="#08080a")
        self.logo_image = self.load_logo()
        if self.logo_image:
            try:
                self.root.iconphoto(True, self.logo_image)
            except Exception:
                pass
        self.pin = StringVar()
        self.consent = BooleanVar(value=False)
        self.status = StringVar(value="Ready")
        self.progress_percent = StringVar(value="0%")
        self.stage_labels: dict[str, ttk.Label] = {}
        self.progress = ttk.Progressbar(self.root, maximum=100, mode="determinate")
        self.configure_style()
        self.build_welcome()

    def load_logo(self) -> PhotoImage | None:
        path = resource_path("assets/scanner-icon.png")
        try:
            if path.exists():
                image = PhotoImage(file=str(path))
            else:
                image = PhotoImage(data=embedded_logo_data(), format="png")
            max_size = 210
            factor = max(image.width() // max_size, image.height() // max_size, 1)
            return image.subsample(factor, factor)
        except Exception:
            return None

    def configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#08080a")
        style.configure("TLabel", background="#08080a", foreground="#f4f4f5", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#08080a", foreground="#b7b7bd")
        style.configure("Title.TLabel", background="#08080a", foreground="#ffffff", font=("Segoe UI", 24, "bold"))
        style.configure("Header.TLabel", background="#08080a", foreground="#ffffff", font=("Segoe UI", 18, "bold"))
        style.configure("CenterTitle.TLabel", background="#08080a", foreground="#ffffff", font=("Segoe UI", 28, "bold"))
        style.configure("CenterMuted.TLabel", background="#08080a", foreground="#b7b7bd", font=("Segoe UI", 10))
        style.configure("Red.TButton", background="#b11220", foreground="#ffffff", bordercolor="#ef233c", focusthickness=0, padding=(14, 8))
        style.map("Red.TButton", background=[("active", "#ef233c")])
        style.configure("TButton", background="#17171d", foreground="#ffffff", bordercolor="#3a3a45", padding=(12, 7))
        style.map("TButton", background=[("active", "#23232b")])
        style.configure("TEntry", fieldbackground="#111116", foreground="#ffffff", bordercolor="#3a3a45")
        style.configure("TCheckbutton", background="#08080a", foreground="#f4f4f5", font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", "#08080a")], foreground=[("active", "#ffffff")])
        style.configure("red.Horizontal.TProgressbar", troughcolor="#111116", background="#ef233c", bordercolor="#3a3a45", lightcolor="#ef233c", darkcolor="#7f0b16")

    def clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def build_welcome(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill=BOTH, expand=True)
        hero = ttk.Frame(frame)
        hero.pack(fill=BOTH, expand=True)
        if self.logo_image:
            ttk.Label(hero, image=self.logo_image).pack(anchor="center", pady=(8, 20))
        ttk.Label(
            hero,
            text=(
                "Run a one-time Virello Scanner review with a session PIN. Results are uploaded to the reviewer dashboard."
            ),
            style="CenterMuted.TLabel",
            wraplength=560,
            justify="center",
        ).pack(anchor="center", pady=(12, 20))
        actions = ttk.Frame(hero)
        actions.pack(anchor="center")
        ttk.Button(actions, text="Get Started", style="Red.TButton", command=self.build_pin_screen).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Join Discord", command=lambda: webbrowser.open(DISCORD_URL)).pack(side="left")

    def build_pin_screen(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill=BOTH, expand=True)
        if self.logo_image:
            ttk.Label(frame, image=self.logo_image).pack(anchor="w", pady=(0, 14))
        ttk.Label(frame, text="Enter Session PIN", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Enter the PIN provided by your reviewer.", style="Muted.TLabel").pack(anchor="w", pady=(8, 16))
        entry = ttk.Entry(frame, textvariable=self.pin, font=("Consolas", 18), width=12)
        entry.pack(anchor="w")
        entry.focus()
        ttk.Label(
            frame,
            text="Before scanning, please review and agree to the diagnostic collection summary:",
            wraplength=680,
        ).pack(anchor="w", pady=(18, 12))
        for item in COLLECTED_CATEGORIES:
            ttk.Label(frame, text=f"- {item}", style="Muted.TLabel", wraplength=680).pack(anchor="w")
        ttk.Checkbutton(
            frame,
            text="I agree to run this diagnostic scan and submit the results for review.",
            variable=self.consent,
        ).pack(anchor="w", pady=(18, 12))
        ttk.Button(frame, text="Start Scan", style="Red.TButton", command=self.start_scan).pack(anchor="w")
        ttk.Button(frame, text="Back", command=self.build_welcome).pack(anchor="w", pady=(8, 0))

    def build_progress_screen(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=32)
        frame.pack(fill=BOTH, expand=True)
        if self.logo_image:
            ttk.Label(frame, image=self.logo_image).pack(anchor="w", pady=(0, 14))
        ttk.Label(frame, text="Virello Scanner", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(8, 16))
        self.progress = ttk.Progressbar(frame, maximum=100, mode="determinate", length=620, style="red.Horizontal.TProgressbar")
        self.progress.pack(anchor="w", pady=(0, 18))
        ttk.Label(frame, textvariable=self.progress_percent, style="Header.TLabel").pack(anchor="w", pady=(0, 16))
        self.stage_labels = {}
        for stage in SCAN_STAGES:
            label = ttk.Label(frame, text=f"{stage}: pending")
            label.pack(anchor="w", pady=3)
            self.stage_labels[stage] = label

    def set_stage(self, stage: str, state: str) -> None:
        self.stage_labels[stage].config(text=f"{stage}: {state}")
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
