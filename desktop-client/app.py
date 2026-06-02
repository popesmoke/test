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
    "c-ri`Wm6km_y3y^2wvRXDHPXI+%*(hq_|TgxP;<RN^y$2TXA=H*P_9txLYXpzkcUkoSFMGvt~b9vmWd{-(@@OBSZlkgB$|@0"
    "AMRA%4z}t$bkPdH1L0iKNWj0002a@k&*eRBqKxn(Z$iq#@-SDfMuAQn27cOkl%r^uv)yB<fP6Z7<j)lFivntNds}Q@Z%#eNu"
    "5ABrH+fVwp_>C8ljj@MFqqxphFzVa!urV%C7}zu^e%4Ozi@elyDode;OKTenhfB4Oo(+lbV$Dz=*B*72OY!He(?n4E%EsSQc"
    "z~UpRv1$#+rkHv|l_c|)6I%4&sX=49=J^gxrx=#K{q9?$`U|DvPS6r^Hd!S%^V86D{QKNE9vUo>%Z+kc3`mHDnDWu`%|`xE7"
    "7>g+5jsW^wV$!3&=32tY1cQ+9>CK{!~CqUaoCLImh9GMHLW*~hQmKW9t);Gx{ykKB3T`(D-XhA|k!G7~200;mm$x3~OWt^;`"
    "W?1NJalLGa=elU^XJt9L(kh@UPX^JWiC=^Pu|z*^IYNf{j^kNMhWl7BM16na%OP`K4Ch!NCyY;cn(d#Bx=$`YzJ7VkFm!J%^"
    "6u?$Jy*Sd>g4wP#^&zsp1ERO)p4f>!22Kn<A3~*|MCAjPSKBiB!Kkv^dh03*I<4CDhdE~0!d`0CPvnN&$SOLf?M7JM9Mg=*G"
    "KvgzvM5Y0MHXvr=_P~krA#Y_|ILw@EObs;O)VYMo5uuyl+Mk0Js|$-Ahi~^H71mBE&~KQB&_Qv4cN)2?BC}OK-cBxYTRMI@e"
    "C=1i@nYGmrrF&s9=Qb4cIBXpcahs0XAM{0YS-ZX4pf+wNKVxOjMmIl_wn1<F+KNeH|Iq}F=Nv34PEyiiGd(NX_0hye#IO9y~"
    "LknTt@Q*dMqKC$JVJ$S?!Uy2eYNEcw6K`oU070FUJK_cl(ZDYG1MEb_GzUkx##1)^Qust?8^#l%oEtlmH36oc0(Tz5zJjHQ("
    "N4`|GxVN#gIoC7KJpu?rM!lhZjvroh{wKhP_4DV?GfgbObfwF|m3PYCJoZf*wA=pTSw*%DV*Y}Wk0G$?`HWUX#7%`rxsw?W0"
    "lxW;LWzZ$atHdH7!#*?cb->pMq$Zv?^|&i*|CM9SYH$Gl$xR<*!A@5yFbq8Iz;={(tQK+VmVv28)Jc5V*0O3^%5J)C-tQ4WM"
    "dSI<>k(?$(I(Bc-Y*^Q@%%s6`bXJBFT#*8Y0f$DxdF&rN`W(Nx8K|+dK2sBp6ht6bT1|>ai~#Mu|vesk*Vaf9m~QVL>cIWM$"
    "o0wrEw_22Xmm{@N6UO$ZOVkBI*3V2)eI>kJJ$K;kuR&q1pCi1LKdIYv3yj(UPAGmcEhY*|b5Jp~)-<Q}tx4M%QonXD0lW#Mp"
    "cN1O1rU3E#|gweP%84zHYDKuzwp6Z5+lY?7&6VqWMD3m<%O=MYJ=Wd{zG<|_95Qxqx%-hoB4<G4NeIWwNJHA(O`hs+IQL80M"
    "t?$5)Y-h<G`=}Jq^Xbm+0cbznJ;jU0*wzh_R;SYdmx;*3zuFI?FT|6k$0^~;2@}gLP4gs~MNJ7+%6Bz|L9D4-xdJzsC9cE%y"
    "R85XOWHil)J1NJW2*9Gb5Tnx4AgWAnE4)UQVjL`jj70=XsqL8Fn3WA-64=lcZV|g@d;Se4iY9M<laGLCF3&ei4jmu0&>Ma$T"
    "Aqt3t@EDPykP8l=hRu>dF^Td4El*&7Ss4j4d|3Hu|%FcQID)bUD5wg&@{^RkC(b3%(#Z)N=V-zcwWgBO4<TIIu`@YI8FN{+K"
    "R^_d*v%;B&{GR}o=c{aoHr@{q;~9xebP?I_Vnhmdjgx8o3s;p_#4DsSTWrznz9Mx*LNS`k*bJ1SYdI>ER!Y#URu!D=Qu%wVL"
    "S2b`Yg-V*&V>I<6J%P)T5naTknu2XU&)0MBEFT7nb9-naeOaty6%6FjaSc1e|llQ!MYa_N`Bf6-}GWw5cy*P-_%giVdYVE2W"
    ">OEfa3%nsoe2V&i=z77(6`en3z*+@wpHaSaBuo2dIkF7%;@w;3Wvd;WeqSzl`%pW2CU3j!nGIiY)LB36H`Y8qEf8DV=em#I3"
    "_vEaKr!0WK3_9e!SH{NiCoa6IO4ngw11`xkYv7Hv7}SnlAtJ8%-*RU3{VPwbND<rj*QMdyoiq$3m?EZQ0eYg@fU6BFp!XJg-"
    "Y_GFuHc*5S8LnvLethFre|9WovIb|D0{krK`0QCFj=ptvV<NWCN5!-BErXtZIHL`k2`plb{d#W6`%D@(`8oxaY-ks^@b(d#0"
    "HpH1%!}w*E)7l9f<{?OXHPvz<MKn4S26_w`9JNG9Q|c$qSZprVhdedgXxTjAXO&!t+T1)6=n5k!bEX`zLKespk6`56VH(m$5"
    "((o$Zm!x(;oc#UtbmJ{?}#Kdviw7l9}#P9g!IUZ}3n#W)GJSHSC!As}y@EylswD-KgskO@jf<V(!e@?q@F<EilY5~e$uVk8W"
    "?y+Fu+3sLWd02~Cu*kiz3slcyns$^kz5-cOomP9$N|4ZZgzzFqEJx#F=9a&6;dqmxgHwFXW@`f#<df@yp7(+=K4_Y?gFADI4"
    "<le+z!*3}%F@yu^qfC#)-Q}?<w3aBg-O_Y{nW!knm+6A`Q?$Ruvjz^qg`|{tVfkNt&o4PQ}+Bue8Xmo$}SzDr~-Mr{3HD5q|"
    "rwM?hqG{Uv9L5r(<tn2-2B;<tB9@Z&3%p**=G0De=W+d%50k=k8!kxl@T{o42mwpF=6vtWrn8%|81jyvvg`Yyx6DhS8$`Yr~"
    "3G!Vn<YSp^^JG6Zy2T#d=DsclZY0S25(18mzQWzIS^-%X2E-MqI-j(Kjcwd`(qTff1MNj`jP5g|Fp$Vx2w*g%3rq3C4(r!Ot"
    "qS>;a?6iX)_8456FH4M_eM&5pL&br5)AzQM}n)!LL^bLelzQBEq+T0*fovQL$+Zeuhhm^9e;g>aC*-s9rKlUk?2x-f;Q6E3g"
    "W%DRJ{ebDd+NRMXUKK!}blJJ^;Fly@uMZ=@WWHdzOzELN)A$UNRN6U`rqNL~3Y26&Sn9qp!Myn`8-7`M_;2<FqFu`5YdrhUa"
    "+{;<IgXrW_?=MtYf-$lju96Vfu4Xk54FFM?J?U^iPpwfrnR*pLu;KyLzDoYUtK4TO<Xjb?i)tUw~wv+%!_a{f58;)*7b_@eH"
    "u^rqE^<>n+DLV<M9f9(S~_Oy+8u0A_)8N4yZFF`JxH~;sP@n!QZMYaL+48Ss$s>q=K#zP<KFf%!4G}96puyPQJoWaRcFiW-s"
    "KQ3$QDQEDJkV%6@`*J8T1Ju#>no(EaPI8w?a*f%k9NCjosiB_zHsZl@=E&<L1!)_uJw*Q1)UA2)eJx1tf$&zDk)+AMy!m4B-"
    "C)N6%z`A-Nz&639x4`xGdr>8bL+nj0OrQS&C290X{sgId(2x@SMbSTgW4%NIX&d@qZCUW~-w4tR5+*o?Pi`zbDyBebzt1O6_"
    "y<0na<=*p60doIKA;&>#4(s6SEIr?M5L&6q<^l@)uq|(VL8gU=$NG<7p6`WYM@#&8eCcxlv`7X%!o{=f_+a5!p*|)(3!+Odh"
    "IcELKvWWBXG^?)A{FM`vBRnhTRFwI+`<eE$l<xtxNHZ23rtB;wpGge%T#U5*ZR&tf2~LEuN6xZVD52BhSsIT;!1%o<MSPF<|"
    "1w=5~E@8TZwL4${oyS;ukk_^z0L$M*HZs%1Q&`Z=s=WmzM`LfMnv`Cbb_~o#x{T>nic>N3O?|^5l!Gd8T$-FT8WdOPRETJd#"
    "Or*c|M0b0jKpILxWx2Wnzz%Dv2o7DokgiVo7};ib{L*(`PK?$ej&)pg$oJ&c3G(>pBbJ?u}1t4H5jhkO%)95Ht-li?kY!d_b"
    "baI65RpUne2hI#4GVpXiug0Xq@<w`WujXqQRx#_+RPTUCTw?xXGVy^bL=0iOB&W){|HsSyZszwgbBbm<+WsM!ucY{d#Dlq!6"
    "0yQ*xZ=C0{wO*2xI^8~_6;OI=>wZK6T!|TY%b?>9pDXjCej7BI>qqkmc`#%3CC<g{R&&NNK6gJQuI0M@hltGr|2vkf9lvJCi"
    "%`^EvGyy;yX<}NT{<WFI7e+esDLgmxJ@d;4?7*D_tO$5AD?*g$uW%52YgKyDO%4vH$Q`a8QLR|vzJ9L9qeNY!54hw0gLqJD`"
    "OLqh#J7(r7U`5*T?uq&@9Q4;LWE96^@FF{&q$7<RZQZsO@P8krAwrpeFs?+L_7U7*DDh+ZhNDP-nX-Zn@`eNtX6LEEPME)hz"
    "u3ANo<d48Uh}DmxVvFe+WfVgG9xe{u4F^$FoRHKVrDR5!QROEgUZnRWFqh94Og1t4QI`eUJ6MV`;8vz+U5#ls^P@krM^ju+v"
    "DSLZjb&Geyt*$g!0!<M{?8z`A5B&+U~V*!7R6+!4W0g`?+&cqpSRVaYoVjn+&KV6*K<^St$b^CgO|2Wp1Y~1tATuQ2HLkR&R"
    "q>Ce~+^omL`Zqt>;%j(PZQ9bzWEGG<jx(rzw}vEMJ`>EP%mRaCdt||dwAC~vegGeiqiyrGze@T=KRp;AKfijGNi4NHn^A4(W"
    "J$lj!)2ZF)Ag*ESGP$RrFNL}^{L$Gbx%J=3|aO1X3KgT_`Zsbdp1Hgw-Pa^bt|{ha=x48ohTWSbyiT&A3pPf64Cu9?&tXZ7J"
    "sNSCw%$$0weDjFSES;!uB*~!P|xE-_DpNYT$R(wHDs#y}ISwh>o=z{_JSyGs__r!I8YzxmqhNao3j$)q7cfEYau)y4ix98C7"
    "SVwj%Gs@mG=pTK4&Td~4~ySE@+AIM05IIPAjAN^T?^*M5Z-qo`XpU=wc37Ly@;`7GOrqR0Y#=&WF@k&4RGyyJy?Ob4&AP2b_"
    "$mmnL*v?6d0xu?%JU$yScZ-;eYld|;+h*DGKc+|_MUJ*YF4`Q8fO#QyWt@U;d&q{kS(kx+4b!S`ZI?-G194P%Pi1(6h)EoWv"
    "ZA5=3a0tzwdOB5{!`Oz&m`XKCm4O|MQe%uieNFO?%-13=i&>(#)ISg%OvnM!eO?JpzY&0qfNbSkHCte6?YBF44d65V(wsbBe"
    "s6S<XXIRMRtg$DiZ&OCt;a8T9re>06@uAtV=h;98zq)_IUZHtDduO7?AIl;ma<ZbfA=G0HxJJ*eOf05Z2tc`8o`*2`dTFTB}"
    "=?KQ_8n+dcPL27x=nwLaoyZAmG`EEz=~X7?C|%z0f1L47yq=62O}sQi&k3f+N?SLqWW7WSw14y8C116)?KRELT+_GV1R8QRr"
    "T$5iza@oV=hgXJUBRh+_F@3j>>39?k*67mgMSE>iyZ){7MR?lgoVU%XOZzpofB_EaW>vu1=6Cl^g8+m=9L1U2%<g$>^D-*ij"
    "f5-}%apCyjo3Au0UDi3V7E{J5+QRj3$Xi;C+vs^@}wq>{WwwpnAx*(Hz_}(R?G$<P~<pT5^M6E=Ec=?)F8ov<;m>tOf+X?CV"
    "a-1czb|CXggYq>v<o%Obb2!QPd0)dGczW)DpP{X{i|40?2DNgQb=lRJg}Qd=-1F68g5TKDH^0B>zBb;o)_kVvXI$5E-VORAl"
    "UjFE;q%LazVP~uF`d(<TO=2q^ZMcQ{UdNQdJWuadhwfX<P_1pYy2ty5;q2t{qy@KFzsOW&cPn3uY}T~=j9uTrns&(*Nwxg%j"
    "2f8YQ^k6LA;+e`;7OumJvV5p8ZyLTF8M)4(Bp@EIsxQ)E-yoenVfxkVuf@{8gA!Ex^MWIeJ&zUocI5f^qE2cW88yE}Lc;r(X"
    "o8@_%~7j|O>Z^Yls>d1F8I56xKN7?pEJ0YYfY6zN0c#5NUqyKBQQ!U={heoXx2D6*N_?3QcG>Mi$@R@+(pOYGFbxw6eM`(`w"
    "&j~&N3j`l*VUM*5B(d5+vJ)$*cL&AsD5pBQ5`9=apiF=wP?I(pke~2Pl=82gl$`e-B8+VGleQT=ULxev??06L=J#yceR5zua"
    "F;Mc@UVlq*x=b?~1Yp*$Sa%4rzpu7_d|AtK*N^4&g!6-F4YxeVQ2PP`%OQ^Ozq<?t{DlrZrxYyXKYyT`x_fA=GK7mi3KydxD"
    "S~^NeSS#@k$H?D?MV3h@n%k84O{bP9QDl;F^x0P*?Un9Hi<`C;}3VuCcfUdR|m!!%=TS4yG-%DdV7*#a}x9re@qw$csf2lV}"
    "F}o;zv(2GD}xTz@Xml-Yja4QEx~`OhHhESje*@?Yd2<rpGxMS~rpF{-Rq((HN)nFqFC{fT??Rdl<Xxxk3tD#UP12Kcb-@W)`"
    "bBwwpe<=R62xvCn4p2=Sc)1wdWVua3Q&a#7FCSaO8Bkr2pBVQsRqdV<`6_jHyNp)Cw0<i4_MtAd>!@mK<O)16N|kS;iSRLiX"
    "mcwLc*4E=1|tlkn-7K9&p<0nMjS|jhBvt{@G7v}T@V~79og<!_P2=(jg_^jG!2i098{Be&tuTROL(N@&9D!Ed`(QCb>6&R<%"
    "7Wm_a+2*L@lzEfd^PRpw!l1SS?d%ddO`ATz{Gb|Q-^<lRRx}%<ma}%R=+Bw#(q%~8ec&DQI-c(UT)zJ0_Q+ufkU#uaNe~!+H"
    "bLVYf2&a(P|@T`vJax~JFY!vsS12v9vUTY1_XHfHmTe=p-`&J*<vnnpkyh7fFc}}2VSEKSQj#uc3>a(>471Ubc9P+#C^ydci"
    "H0gQ}_WA-lU<qpQ_`gH8HVMl{DE*w<J!0u%Jgz3E@9Q#(ZUQf>|+XT>-pK%BIV>!W{&Eo6-z*A29qb`pS2rtr!)iT4O4)bet"
    ">e#uTLzE`G@GyKp@d!O+&_T8WPo7`o$3<KN+f)V0O|qBtRxbdy3WiqgsI-Wdl|Yrft2!0z6*Vyq_m)n+~!R`M0cNU$%S-=D5"
    "x%c7A5W&6kJgNxSn=?lXC*6+`tLp>9~oIoK{-xtRMNupg;jm%R3Y4zphQp&v<AKI9TY|TCeCjz>8{yIO_-d_6-_a*uAOs(GJ"
    ">Akro7^*=?kBMgS+IS1{5C)N|Arx@L{XTh7*B1NPId@k`v{*1iN}L_sx{~2@`fgNAJJJA1jh{V%0UTSHi|)=UIp#M%ce<#WG"
    "R+lQGSN5@rW*?KdRVqMs;zR87^s7}J+#xh*Z4lU@LmNy3RpxFO=}aDTlBR-#DQqZA1(oB?!e^vG{o-*ukXKl<+*B5Oq<I8u}"
    "5{zu(IN?1&TE$x0CwU!jP+u6kCa6Ojq=US!dRB|4v+&g1OSZbZeD<SF*V|fdq)@Y>suuiy2`okz##J7<Q~c`%JjrR{Qh(*Gp"
    "xY@uwHrc}5B-HI3}P%meRrrXPWXm_Sr$;&JmhyIBW?c}IE<kVY%@#F{|pEz*AJY1?PtRMJt|rNU8oOsIXLgmJ*6AALcDn7$@"
    "_E$fj^|G`*q$XlN|vXRQLQ`qp%d8d*B;xX~&?O~tToqm;*6h_k#*CJf(+~}^MzOeS5O8;(BqWLLu`PqP$R^q`!pJ?^Eo+kbQ"
    "3+*1cF<$H(?b{eK97V`LO5(nw@sTQ{bRd^O!rG5Fd+Lb$OELI9tqtqv%<UJ<{w?38!zAt(bL?Qb!!r8#r`q;Kc^#}z-_7&!5"
    "E$vsW{xZy#W+wtq$5k3QnY$d)FMZAxBoe$x84D??H>JB){{uUva>7qLP*CjY*`cAjva~x27l6IT>*zd+0^fVac2)C9kThLDD"
    "@k`%jZx#KqtE7=zn>i%135yJ+G3di*Ic}<?kE1L$ZVdgZUC$oinOzEw6d-1Y>Pf(eW+rq5@U>6@urfstDCB`U*kYT88|oNYo"
    "u|iZ23o)lW!m^qb*~yuJ+`>>I3voH7Yn6-|xx#$by*Iwu#aIJIrIcu+JI`am`}=qFa*o$bp(gL2p}40YUJ8hu?}<oradex^U"
    "H&Qq6Kmk!vMc(+RJqhsOU25&ZVkA6Ngk3u=wUDGb1IlWC*s(SoVXppFnl00T0AB_29Nzj`UZSx3y_^jl_yO|uI&-~Jo_)Vv;"
    "TdjKSdG~S2`){Z5i}kO~2zJSo1uoKghT$&2jsV)A&cP6z?JvuPAc(>H*K-XgxNpCMY1!<?$f@cIaV|`gPz?kv%O@2;!G@1RP"
    "xr}Vd-ocXD<LB|Z0w=4N|Hw?ih|vR1Ss`BQJ$4m+lF=&u&y*zFf?bwLW(EvgN*5lXdXb+w>8>W95%i1qs6o$0)<O<UhAPL<d"
    "a*Y7JtN<7xh1-$YDNV2l}VwFmuG%1aCk(j8oD3&BmYlebIVBs8QWH{>dWU-$MU*4&zLY>lU%PtRP51kjFPdMgIfNdc&4O1o`"
    "=jL0`I#&ShY8K+0jdtY@0bDepBm|7Eo%ih8-)W>yHsXJmNiRKFxj7RRV|td{Q~+(E~FHr0it(GqbYD>1CsIg$l^-*hd8^UE-"
    "mO3fwo_luPso`}wje?}%_nVW!Ldu#@r*u=3(?dZX2(9xq3mOX{G#0j7!fIXxd{`#;S>cDd6VJUiQ?Woi18WRs@nkCe>iLt&P"
    "-tX)hgE>vnO<4k)k1aoh_|P=vaaE;{k;l@iDtYzQKl2~d2;|Vhc~@N(DkB0P|L$z~w|ztYFq#!n=3RYTd02LUg!S+aaDTm9r"
    "D&Xd<Ic}%R30E@cEXnH>u7nNSh;ZLyl0*KI7VvL6l5Xctz-*g4e`)sHz5e)ASERhwTJO^t{!h1>!%~k_`6A-c~>YDVAS$%m8"
    "#U-68e8&ljHBG7gGAeZmCs~RlA!SatmCCFM<U>kko6mtB%R)Vw(BnGz4ZFWCqYs$>Z0pv7Cxg!oHrrrQ+@~yuRooa7_`SV{W"
    "(4PM+wSfK;8veRcqqXdEzwsXek0iD5}cQMl3g!w}q+m{v2!mQX;RD-#-X)D;EHcBwc27+W-Nr5i}pOTqf#;ohu!4nx4ZHVIN"
    "~5yuiC;3224*VVJs9iVzJ+wn3AQEn>7-Ny*PXz9r0elztl=(?|-74RnFX<1UTk~GUZ<1%dj!t^RzXj$Roofkv=z!vrMNlWXt"
    "*Hy;pk&9r>)XE=tm8JAK^OFn3Lwj8IRFc?7W?ykOY)VBt(d9XE>t(=|W7GMDC5!z7U1AwcY{Nr*kl(U42rfR;Ihnr#xN1PQ4"
    "qra+w$g4^@>pP=v4A2Hl>8O$JX7qtSm8p0n4s3<lf_Ck<4TPD^zku)D?X)<QhrtX!QA;oek7D5=e4nq1smp{FZHQ)YzKBDM3"
    "kpTP`nIyB)uS4BBS@5<Rg+JM>4R(B%l{1`kP_jJ*nOMIr$*s`U<>QWXX+1UHR{xj+Hx@9n|70Tu8qxkhv#P4(>_~J^Zh|ZK<"
    "Zx(t7B+zVBJluxX<;)WQdUWIukXhLIk+&gep`f1oXTi#?syFu>G>0Qis>8%Hxhz+KTlnF)R7#fuU%&|@Srpcd!B^!EY(o(g1"
    "mZobRjxEN9<8j2E9T@ZkO@o!J=$xJltWsB<yM%M~L@}KMv3mq9zxtN{B_iN?})hxG1d6g>PV!>eA$*uHh`*sq(x~#R#0o|Vs"
    "Gf9{r^o@roUY9+(*bl+W+2A)f_E(%Sj%9z_I<{L%|1l?DooZfK#<AFMJlG?BSoL<Gv9P!5u<ZGe8Gz$5|7tjaG{RdQuWV_r@"
    "!m_aMO9P7oA+1pNPa=G3_Nkqiaz@jPjo-1{22L^QOdZMCKiG~UCuT-6L`d`RAM<)mRWYpn<Mfr+#=)BNtmh&Oh7F?o?BdaS-"
    "oln%2CMHd?@<(`S9Fk6o>opvE)IV{Hkf+d=|(4qUdKmRepK<2&18qYlT|cmz+5cB1^@ZLH;OX>bV!h9Z8lPn@g1?`H&jR?bV"
    "7>lFW>HFz!{#)g#W@xneO8z@#s?y5O69cr3!Z%O+SLl|1t}U@5(HKeXh5L()Bh%5`;K>ocZ62TYBg`O1tAR?a6!a079*2|J0"
    "3*Ffv@_FEewJo;$(nHAgRUfKhjB*b?+ZAbBv>N_wylMnsFca#qq)PAInYh{VPtOY&FVVL~S$o{S02)i~aXl-1!Lhm>sU%xtD"
    "-KFjeVflI30(HEYK1bmciZY5QsUI;#EfM?vBG7yfoa7|%*n8I_f-jrfqsq~3?alEtP-BiLuEe=Xg013aqU=qOo7=)X8p3GOG"
    "6y_Amwp6=l$hHyy)yFL$yO8<_!^6N#Y<RzxoX0xZb-?1eqbTkeJ5#h-_%AAb&&Yxk$u_d#tAZM{+OXOcW6lNqns7I=3-)<y}"
    "ZlSmRaz_8gn&2;pzmqo1xiAG-B~tdn@1Gg~nP6-J8M^_unYw1j;R0Nbr=%I0)6CVcA9#l7HShavlO0V*Bv6kc*swT0t->$uW"
    "M333SE7HY=v(bneEd4mO}>x>QI28^Dh&2E##`ND?$k49&Qfd526#+>2xt1aRlVCLG3SMFxJWk*6nsWxi1F-RmcuQsYND-BO("
    "Ni*>9M@wjo|)X6<@xKqYrE-hhUHa*%Q+Gyl`<-1<Xjij?IFozMeU0nA^E8ctIZ{E<@mJ>^_5IYloB(*XlHTN$rW0SAg&i|~9"
    "uv+bF6Vka1{|df5!UL31TK|L;cTPR6%L2QcH))Z+>wY=U-B@fiid-v-r_MD$6`%cCOUToZy*FCdGu>J2%>EB?nBTPBXaA_+O"
    "^Hgn(q_A1`qJ4MHl$6i%Z&mPJXNt)30uaPL&*QJPgPW*WBFpLNe-GaDZ)3A8-UG?@*3e!<hS_|aGTHu9JsajTK-)gAkNav?g"
    "fQwji&*O%BRU0504_(HqLV`SbV>@zt)J~dpLTWNm4;ZYl+M}qu|$K?+|~}0_=tUU|UBYT0oc&9aIju8zjm+Sfr#=H&Ob+FP7"
    "Q-8aKH%RJ1pt%B=;5>^X1U<t(nwZEg~!jBV<3XZX=qn5D+PuCft4v(};%r-fM%18Q)5<c)zT;*n=Pj3C-yN`9^49qxHu4Mm*"
    "=#T0YxfWcdIn<k{M#_ND;rpssg1ml1!3|Mswb)1R&N3T0s-$5MiQ`99ALhi$dudFoKQ=#_x$xv|NyLj3JvGzDGy7SbNjvWy("
    "n1_lEammO!ZY8%_t3Yp|hlM(ix8un9nicWxy75(q{fP<bCK>b@_wdpACe}7|JD77!wwBlcPr1c0K~Y}PtWL~=BGdvjyujy`>"
    "Hzr%b9BX~v2(xB_#CjXg}HgJ<hJGYZ@2#8;ra10B~0lC&J*3lke<l@`-vZBHx$1bC^|kFH+6Yak_>>(;NTsTcH|A(=@4IHvf"
    "y{G4(>$X@ptyvoMXI6+1D|9TG|z*)+>=3ki=d2HZ%PT0tYG+2f!`Zjd7C0W~I%Y>D#0O1Ctv)!!g0eXHAzy^F&XMhM`6ef-!"
    "V?&_BgzHd%yJL-FMCFq4{a+wFW(c0w~8OQq|3-?q}DyLjt5?hm=~32N$%fTbNi!%V8G+H7q<br!8k_jE(UrrGBUo1-RuqDe>"
    "kVeNqWMidZKN-VWtuN64_^bw;|%V4I*J_Ht9aWLjpNcbjE6*<*MS)^6<pCwM$xr&N#aMi7dpqxKXSak_Q+qpL%uoeB{t-%jQ"
    "J(SNljVrmk{S@ynSKC>|KM|74FCai&SPaV`KNK9y7|ApTweC7Yno3qep7T&)Tte<+)RN%><KnSXd_Y{hZ)*7%m%N`{BWVE#a"
    "Vm;!hJnZM0q^goSmMuwJM0Jt%x)N9#4-$vPkzu(U*97D3scfcosNC|Ynu>j2qf?Hl!>n(pPzn%_6@dR2Xe&Ei<-a8;%kSSeI"
    "tab^=}BO3<%G$^FF0!bTxVX>Wa=z%O0YXZrk2CKEAo8{ooK0c(Rc^_2)FGs}e28USSqZl;)T61=HLh7v+Z_f4i~grP}yA!8g"
    "qHO(FMu{;Rru5mqF)gIR_G_{>V`{f+!XlO$)OcZfHSh9e`LVKdkKMMrcCs^5hwxOS4ad0RuflEkFd@cq41X9hSj1k~AWebjy"
    "NHw-gnIqtX*MrH-=SDK)&MUmJ5wB<IA(DVWyc$oIWUx@aSW!x^t?w$gB`kSoNx1J%dyP{miHvYPY>lFZfeVi#->i2C%+UKEi"
    "C$(bR4}w0GIavnGWluGZ)#Ya8sia}n)wu+#q_<8oU7_$eAhGEMx&a0w)qxahY~s_&@`ya@)B<wst+Ah#Forw&E5Hv8IkA2vz"
    "_^E@L!TS88KBc$7=rYM2t$x{a|nZvt(pu;Di1fsZ7k3tsW~X*Au0N9XH{*~HPdvCK0N<E<k;3E9>YK_2)c`@YL*@u5D1ANY&"
    "Grouo(V9s!u>yX8Trvnz52jUy||X?gNHt&c}CeSL1Fj&n5&67NI-w&q%mb`=l}?6~*eR>HCwDTV(Nk2lx2p?&gH}ICH#PG+9"
    "$*ZUj*-g6omZ<Q)0%WkB7G?ydP#&$em1Ed!9h?t{(wj-<5rYWc%@+Ta*5XU|#??>Md4Wi9&?K2=he`cX)t2YR(lx}cW5n>Gt"
    "dy*6I{=g%eDGCmA8JJe16-AA^1Vedo+&BHl0<NwwO;Bcj+_w<cn|6!nMD!<p5qyDS)_1+aede|96!dk!0XlOWfIzc_kY~k{F"
    "%6!|%+jc_K6tddrf&w~yhA7WW5(SS|Y_7bc$qyZP*}XJm@<o?j;)gER(ZD>ox{yJFv76?Z*#EZ=(2X-;KoTdI0)7SgQ7A4Tz"
    "BqAuxylP7D@sbfh>o_Q>%hd%jNa`S?P0umKvAWu)(5vEE5`BH^;b4ppT}=K(mpmJzp>C-7eIC*LTS`r_PnR)oT`<MuY7~t*f"
    "Pbv6iZ=Y&k^u0T^5Px&ZCjr>t9D<d_em-c+^C0NO0P1M7GC4%6noKy}g_dB&LgO21Yud*G%J+_;i0E!PP~n)%BfWj03*zIEn"
    "c&;Z)uxTumFRe?ZUBu=qsc%V4Tq3x-bmfDp{l4qKx702Ewx?V8Ss;gdhNuG7Bq<d7djla)4L+4@t`dzMjDOoq~!%*`^dZlYV"
    "za?U6#D`T18R9~80SMK|7J(Ev@#?CjSey(E3dO{Z|c@Zkk*<Q+|TZi%SFavj_IuXgX{FyT*-3ytUoqFq5!ijivkDhybXVEs1"
    "G_mg)u`Mrmyt#45d+Ps59~N972LEC1kG*BxUr)+`+UGTW&ykqY?id|s&$1R5Y1YFh3g#a^pZl|<RG5TI84PILFK_)wgwjZ9c"
    "#>%^R(`e~A0Bm{vUK$9yh4h&ZOQ<{%s3AfQra&;<Oz%2pW5}EVsgGeCbKt-yfalsX&f%#8au|voz`@uuMjZB{BC(2G84Q%+f"
    "&PBh&Qr@;djQdzb;YPGA^8Y0<U-*cWXBHT1Wi-%R(TBVk%Mgd|xF>932S0+~Xj_v*IVF_2y$G3;}Z_@bBu3Y$AFCsL22MZ_H"
    "<EChKl#rQWOO3CqvPPb$1(^Y3kRCW53s^ds+xLDiI`_|n{t+{()`!}vU)ng$p)QLp4WRcltEyrW+fAz>`~!~g53#w1kG&3Ut"
    "1iX^o6c|4t@7123LI2y+F-q?mqSASTA+}P3`P&?73nF=RzV_VWv*1=}uU}QzH+C8&VEEDGXjb?n%aEUXf0)w-a3C+oMr}M>B"
    "GQwajkwc5jP9erY8>o4mHIL7QDd`!WN*^S?7&Z|&s283tM@kK-7pqrRq_ZzDH@POx8d8YsWK3D2W1&{o^iG~_xWrk5JkG3^`"
    "zMIJUFVlAYaKCBN4?BFDwh)9Wit+jG1fxwqM1Pk**8w+37em+-YC@~F=n_KRx2l`RQmwbBRZq(dU-i7F`MaGS2#d%bhJHyw+"
    "*xe{>ywBjWMbl`cmQqmM14)O>|D1iXyz=$bhR%I>sC(_~b71-FY43G4G}b((t1`GlR`J=3<L9T&c^4%8CkqcZC{D&o4;&i>W"
    "~5WuYI%Vnx-CaXaX16-{UY!7efXie1(RK5IYsSE<!HgHW3x-NS*#iV{Nf1{PCJdX}LSh&`=NkbNUK66%@u%bx0xk|7ELt@%?"
    "ws6uG_blyOK=rf{vR%^<P|9ZZYp2_)UJ<>~lU{mPtn{5X_GVI@wQ<spYGNjDEkNeTMi}F^V-3_ceGA$cEvI&z!P<P_HUnI?2"
    "wv%JmNBaj4k(`Qc1-)Is*?hf@-m#gt8K<v)yI4!pmI7<McOjw<7X)yN6j^L^4U_CrRF3X5|E*+A*T3{E6JUW7RC^1}jd-^@N"
    "=z&{EByZ8b1E2Au9$Ipo8`+9BDVNBQY~?b-d;2JwXr$I@usa2{}CTce6<UiJ8p6VDN?nXGaAX)Ti&^cHl;s*p1$%5X;tjq&Z"
    "zXv0)EP^bb=+yjAG4V{oe>evhva!Di$dESmkl>u<fVjb<8s}q1RZY&{LKys6JUE#W>M#w<gaX%VjIGHj3Rg!lmPS?C=&WQi}"
    "38K!8CdRyd0Koe(WL_KUGM)%n-Toeni{md$y|SzG!;z9x-2RCQ~#+KRon(v!j4=SN)6drCcdg*-|I7uAtVEpB|+*dXo04*QL"
    "}eekr)g;GaUmh}bpS`Q5;b>HLCT?{9$XlibR!k*r>LIbs*y~`T{5RE`rY$HnjK(l;2-WNPgL8!ew)9?bAG|_|lzpCTwAbM-o"
    "pbtlatra44p6RLI3gx+w>zXvbgD!>tC(Gsd3bUVy3wT4Lg#M6}zn~)f$J!3pDg4A@@OFU$a-;Bwm}~UPe>wPa`Fe6(!}R=4Z"
    "AI-R)Rl3um(PwUg=>&G5G0`=mWZB^ajwK1K&TfVkok_B2ow_NcrjlRQH3pn@aPKFSNnc1uLHUy-xO#W`c|d!h{YW|q!qmrd*"
    "wXLzR7b7wra=KIs|dLgUrm^uvEVRi=MjQ;LQG#UWYa^S!(<6R`C3)JZhW7!?$p`iueE3HJOO#bWh@P5~))cJI?QAtU}xE5Hm"
    "8!`d&V~(;8EqS^%V~BSU$O3VR&Hcv1LlYE8a!JBo=TNRx87y|pK@u)?Fa*6)GxTgCaKPCJ)Sr$sUr=HQB}@Zy(2cVr$V?LYG"
    ">@Ya8lAGHy;eNCH|c2}_S4OtQr2;?B|YIvpoVIcLr=xUicB#qPB`^6B&+0p09u|+k2pMx*k^Bqe1iE?oUfH@5M%ml4c!}|(G"
    "&+^=fYKBbWwr~V^H2m;_adeLnzu9~-MNvuTSrFl|>gcW<R^$<Y2SHVc>iN-Pxd!)}0RbO;$8>Bx6A^O>C!er1*u-86m_y(Fv"
    "29wZnz-n!^;OV&9`SprteQdRhtRH7UWXWAD&$_)tRuO#r=GEdem=6k?CdC`D`bGqcKr$p3Lz7%al$;?Be~3RnRg&diT(bh+o"
    "K+kcBOGYTZ!~m$XiITIborJRP6%#I9e`gsVBSOPQR3Px=lTbQh7CiK_#@D467UCRs2A!{McLXp0j$mP!jX4XQ+@s&PU*Ib6#"
    "cWQU@C5$8q%(?UA`ZHId%cxi40L22NV^7F1D)mf#v=jlj=bn28mfY>b{;=&jKg3>$Gi+*=W~9<o~TUf49hWTtj)2fKB0u-J$"
    "i9pv>2i5eOxU;iCa0e6YG<D#neWNj9**gqUqFVmXttqkm9$Y56`KQ6Z^;?hz$Mam0JAB2#f<_#Vvsc%{q1)V`RwlC$|AT=I1"
    "*R!^m>Xm9{#`tE_0x5!lhHn#ZESGm2^=+-r{k_pj>L;vPyEZERL}DQJTCRDLnYdfUIhGo4VQw~m4tLlk)b>w~`W*&-0W#R@n"
    "Wu6&*u|);14$Q$#C&Qt26a?PUh@jYHZZ0)O!Qvm)Wb0#n{A_N2B(kBD_mRR0~nQT3EW!`tYkP!^aMD;c^WAfNFV5G*byRzsX"
    "EKM8$>8>`j9IDP$MQ_n9+#yJ`~DPC;j(}ctH9S+`N~{eA$^+AE@V{8NdGfn2eAeW9{RPSf;?!+=_^}3G=V|<Ok|v%=Og<9G<"
    "Fcp-bOSbJNh^TaQR??GlxcSA)Ui3D!DbbA9wU@dJNdxmz)1wu^nyzKiCoOl>z|bc(p&W&Z?Br7R$aknXIe64TH?m@YR$eQ*7"
    "*<B_3{BNYF(UqP)!Z<pRbZf}?QWm%%h9><Brs}ITI5ZzRzNE{_c1M}kinb^qdiF7>$Sy4OHR-UAD_9XEy*$lJaS2JQ9Y+Kel"
    "u{KH0$47mUn)7>fiD9<<;^#z5yQ1pfW6Ky{TWhl`oLYnImiy(KAD*2kBt0ZZ-jNa?j9a1&@2-nCmfu+u<OA#1hPuM~&yJHNv"
    "d<fweE;+{@pM1#1WVRuo$kc|CZ3-X*h*VxihiP@kkMZJTw&u34pr%+uY8-}<evMT>^mzHhSq7m6}x=V@7FkY`cwdZc^o-#c1"
    "^n06eG*=Q&i@qLtW#hu{I@l#e2TiEnUYnjmt5PXY{&xwckuR0%=NmW4)L}|4^djBzocL><Ejh2%I``fML#2ohP3JMdO9}wQD"
    "mktJFPqbOSg=gN~VT&p*XI|FkhhnElSNji<$oOQz+T*XEo>zq6p(p0n&z&_J!^b>&~SEKh^U=jdt}vta@$ASXh7EA}Bv8uit"
    "D3x9k7c=z^qLx#%bs-~H!#Dk~z=oO1y{uRWAX8*)v`Pn=*wgj0#fJRNC=QxS@GR}c0c+Wh*w3Nrt<Z~ab{bm~`m1wDU-<<8I"
    "5(RNLiWHu}%qJDR!bZqPY>S}yO2imjM27h?(Nnn}vrA3Q)2M%ET$f#sRk701F5L0$KNbS2_rJ$%J%-inIvs=Y(lwu#`3_LYo"
    "0vc!E?@7PqnhNBr4@z%6Iq9Djm%NTsYAi-mIlC(bJm56X-(|pM>#~8w8U)6rA#^*E&I!?UNtLw<np7QHr4g{{v|+?yh$03tW"
    "1B+s?NL^Ciqx<Y(f`f*EG;f8<6byA=av|KAx0AJ)ekiT5FSeuCL3!d}}_F99Jl?2R-Y4=3!qwbtr+zsM#MZA<UNyc}fSBkP6"
    "e@rrL+Rt^zGyJyNaWzWyGPM{OFFAU6Qlstq-u*Du?E+1Un@;{}ZxTqw`&Q3JNL$y$Y-X>%e}C%UTuN_hUlRTsu=bIpWugp9~"
    "0sL89p(+aFt)+adW=8RHa618ZWY6Sx|G79E%PI<pJ?!U96aeqf<;$IQaYk{7vr$1P=;Xz1~?3;##G#w(XM*2PUqO3vSNzxp="
    "_>XC|e!a;%uebvs@MWgnecC|am49HFSm~3EKA%!pBb>eN8{lC#g&!)BK0b^QZEq@g_-oJBN!a7~Z#6-8Nm4+?mA(Fbp;iWym"
    "o*i7^a1dtZey@GpZF!$lPva~)B`jnMJ)5sV97B+NmNiYu#H5<N1^3MXyP&JT_OkMujWgkT|oJZ%BAFohhbaP=F(TMS)}RHhv"
    "a;DUfqm(=76?0`awqc7K)&SFO7jhwwZ^PG3>w^h8e($P)a3uNeAb0W|G;@`cU|#fhlHeCup*&SPhci)qLb)AoxCn0;ei(k*`"
    "^n$leYDTYmBLDjR)B;0VZ_o8xQ)>=2u~m<kAKHy@;m`Nz{&zc@|*%0JL=jnHwV9x7YWl>M=s;&y2U2;gL6%iv{>JM1fxh8bU"
    "1q4HO1Gx5g~eXErU(9oBJxB1jFxZX%Ek9MtnvSJalabI@Jabf5EQkGU;eEmad`V#*no7Hp;>%u=N`6A8=ujAJ7O1R*9ES+!T"
    "lhQ>-7@3cC%@5^`z8pvHD(Qp-YZh9n3Jr8o{U_DZq_KVp5AUZsvGG};Ny_WCnT39kt<7j%f%up+lN5kuBb<+8FjZS3IbW-@>"
    "+|I~dsLt`?#PQ@;bl}wgd<ifLVc|VzM_Mqto?{{4a;+#)WMEViTlH<K&rY$HUPi)vrTxWUv9F1lgmUv8%U*4keQ?Q!9zys<>"
    "MId@X4dUE+cmZ;(YzlhUj|6nP<2%S!J&oQ&nV(>zh#{3X2*b)?5w=$Hl*;l88lDAySyTWZsAJ77TknqJJ@~1IRXA3Fo#YNth"
    "QAS9Uvwj3GuIy#C<R2-)A*$G%r2EDFlISy3fX@2x*DHY>Xa<xW()?SEe0fxaCrhd3;YiqfcntbDn8SpKPrwvf?&dBo{_J<J;"
    "f1#p@@PE@I~Jzey_<Gc+|sYU^IybJw;bI-kxpQPYP#je~qP%SpG0JJs15>ccD9)_8rB@nK6c77MC;MjpW6D_qz4Kb`WguDKo"
    "F%4qTvV-Z?M5|~>F6opoi?cP>b_p4HCFhyD7%>ffM+Pt+%#Z0kjlAr47Z9XzIGTCC+k;Hk?({%2l<x0~g`C+l1S6O~tXuFh#"
    "Ag>NRfm(N8wJV9BL3yrv1b|6*!e)FXv01PBy~KmYRh<rr2VobHQmA&t#D#EJJfQTG9ycVkW)<sxFZggiy(G-!=>#O;HCD|dY"
    "He+f<>sj#l2v0*+ZXnkVq6=8@k_0@4JdZQ<+(FnV4h#O%br7)5QE{>^FWjW0~a0Q^@s*5y3gMa)*kd+y~+rRqY(+1<4J~Hqz"
    "~uDRV!_8q{Q$Uqjdo5qtaWN?W!drLjzX9u%5y{?!Ks4HIqrK`*cv`k`F?cK|`75VLvv46t%a*w=T{*a1qC)ckm;bP3p>XSuB"
    "Z$IliPDv!J5JHbnaZh4-fKe3_dV<QTvw!Htl;QY4f_b1LI<vo`m?L_g(K&dVZr}(q2^W@}9iN}*IRnNq<%WzCY*cEe@`1>eS"
    ";?e^*{%_Ez=Teh<!8WERVN5`?V5&<vGY~Kn*f<o946p|Wz@H>elKzI@SZbxt6{K#}FfQ{|s^zFWB%`bAgr^<$FHjt?L0O)K`"
    "o;clDwKY(o$ak-hO2VPoYg<`AZR1)4~*gB+GZnkYRdWkNL<$3sw<68Mi_~z9@mZaF*w^}A~qmd@WOCjwXI@+cGA|iIU0%cW7"
    "2M&`EIMdOE!%c1Ou>C9&&OSB}Eao_PUBL5EmpR!H?LF(rV9Jl(fEP%~|vkSM&`3{d_OjrDeaxvj6wgYvEG+d+FWD?uO7ADd~"
    "%KXh`CTqkAcPW3<E}i4AdN`^LtaL7#dBBsXC-$jCqJ+_Sah^1n2@Ds`QqN5hq7)V&tOTl9H_;aiHhV8+HixM&OGwUO@`$~jp"
    "mVI5CF=bh@E)zd4BUV;L9-9~>(ZU9seypHU|orw;7Y0G|a{L7zZlqp|jSG^MUQB_nQ*OhI<V<bzwFy!9;)-qD_IRqKpm{Dq3"
    "CRn?Dc*g`M2U1UaE?RQT?PkXjF|bQ`<eAN)$08Fku66y!r%axIX^!BMhx%A@cMpN<04suTMV{+=%tJVF1wdK}+I6rrf28|2q"
    "p;6~fx)E#=%+Gr7y_^qw;>&3lX&xP;+b*g3zr&7g4$bo&T0a0_@4BOVBe0q{BK6j3#Do`hfo8c8eD!(nZX`PWv(=&=mYA?;n"
    "u;t2=Sxn>Vjd>ob;bWO6{-ynaAOGL=!=*kC3G_4!W?{vcE9F8m$JEmJ{JwI)(7@#-+=62^zFmesVr6K>KDA#pR?Cwo$vo7+-"
    "cDP5jrzt^Z!KkpC#)@v`=}pdZYZcupyxR{yzPENM-Aaz>Kz!z@JEUGM{?rU!Lmp`i6noXTPS2K8v=_zfnwjzDfz^kB1V!-f5"
    "&lMH~zo;>%y(mzm1w5>fXJIlCRp!B=Lr+nPP^w7dCuRd4wVUPIEiGZ2qUH_C?uD}5MLgSYEx)raFHE`70k*E{2i#qhkF)(TK"
    "Io((uhT#0`LURm7y!Z=)%?|qvfaXZ3zyTFd^lpxGQvfRnMU=;2kfD!_TD#Qz4IRd;{4^}(V_*dl?PHpy8P`y31%(}^jaiCiy"
    "hDhR{@BVlie*l6p&n27X?v<S-fi(9K>j<Rz!UW>26SzqU}i}OFYk-;MQNcq?8_WTq&!z@zx$8WHNgPd>vNn;vuMfok}_%$>i"
    "D-@Dm|anr#7uu4$N0L$E_m)fV69b*nwSY<&EGQZ1LIkZvXf68+Ir^li%OxMo{A*(T}GTFJSpOdjL1c{%9<`jDR9I4*1#LF|Z"
    "gscvux<0(Prh?$t2iMFb4XoNV5I*odYYF`p#ZBVb;p5=jm(%(#34@n_Am{bJ))A!?#^;=w3XW_9u16y4g0<c^nGHb+bj%ZS%"
    "n-qej-7fqhJ6ERWMV;Y9Cw76a_InbUMmm%<^KrTFagyHSdaY0&F!9x|@poT0$`A-kYj^K-<+k0+dj1=rUn<7KoSxJG5YE8`h"
    "drZWn3-&$QSP9t%7{nY!={@>}>y9)o4XDTb%2w93C4$!M!2ec<t1sl3F~H=5jfJ5drG!vT+?u_htMyW)AXR*HI<VC=sQPH@|"
    "Jt8X6a35xbH&!7gwV8^YAEO@<n0BsYWZAbxq`ZCI!$)^pzHn}&@dRn5*Up=IxD|m<=ujnVt-EZUz>GeA}U4Og=2*{FL#Zc)s"
    "1r=pxA7Rp&o4eW=WgG3c$ORq{ZJV{F{7)=jVEd%N$2r0m*8(r+A~>ry5XCn?`DdbV3LaKHSzAy(y^+$Y^2mz^|_~BUGjiitF"
    "7M;b^z?B6I8|OdC5Plx$LOa8C6qx7j9(dMjEZ8mKuHPyOw}EF_hdRC^`am04*yInNs(i&ZHTL#%N-#j>hd?C}uU!so*{D<HN"
    "~u_)f3LY%MK=4F=8&>I{f(wi3UY@mR!`ZKU^InYJ1Q>R1*Q2+B4r(x-4|Kj^BTcsTEo?Xi++YIGV^=I7ONrA+lQAjK!pJX)2"
    "miC>(&=+R7Aon=#Ft7cO4bDe+!+65`F61=>XSYX|GAUM|Fabd2=QJCm?v+`)uP;g!#dr=}WU!n<L`GmPr3?9WVxv2rh2;{lg"
    "1iF7767Q)pCl2t9i6Xd!tK{2-U6x%+ch0B$ksi5jwL<P-|<pCfLU<2&IO4tXPK5Y>o9Ugym0WE0Ju@e4X7#pX(!uTg(5|kO?"
    "7Inli}IRsj7YjqgL{hWT=2Ep~-*CD?oOr>t8P$oc$%fB_WOeZk7M<6Ubmr_$@;@wxo5jZpVTs*HZV?)ag(sV?UGvG|tc+WK0"
    "R6-+kt=8Lm|@<^>esdlf`M=>!i^J+A1yU#XO2JRA=<clXjc^ufFMUaDSLN~X~+?1>5!fDKt3<D}<jB~-^VLtuZzmr{v3qpwv"
    "qq&9SDRmfH1!PbmIJC8?mjo7DJML(6OmP`OHP%b81+FSk;=f=VVFTXpBANS6IBA$tq5zzQX+yvSHY);bm)P?XU%CQyd`(WMt"
    "syV3er$hinA?dko)z(D%F~TVV?r=b8+c@#P)YyaTdZ;vbe{wv(RHhtymy4fs^dOjX()h`C1TEg4@NKQ=3DNQTSf3C=sUfjxN"
    "e~d*rdc}{YqCiJzub<|hHMh}&=5d-6iH_;zNQFBd`9_CASBLcKI4&2o!vLF=LlMI7#j>mNt)vwKG6vn&3nLa8a3?rm-pYYOS"
    "$y2u(%4zij6PGjH@PIq%MeLH5*A@Cvjb*6wYB<N0CtXmoW=o8k6%aEh*yOVpU>9uqw~*y_4e|IqgVJluoa7oF(!;wB&TuSxo"
    "lPEqM2Vu-$+I@C!^JUzXH+cAtD-$D=F6^Y4oKK9JyBz$>ZS#aR#eda41Em@ZiL6Z5N&|J;C-8hJ`EVt$akvnvUV)UHSeDS*="
    "2gQG{I>E5O!t-aOn*${~yMwVz3oWK|!%#!_2H?S}M9{^N9tG`KRk35!S0+eifK%k@2AVb9l9&E$_N1{H~!Wajp3ix!~#LJf!"
    "@sYOF#W``xV^i4xhdezV!xx(;PfwdyTzM((S(!j{xr@zKf>{-y7z9}@rSxqp0pNmkzEB=aoIttlD8nv(?%!hpfNkq7=iiRG8"
    ">%#@y@JSYr~LC1$MBk@ghBIWjx9tvJRpej!Yj>hHwO5{=>sUo9zx$kD~eH*%FVVZbCzgn2d=auz}7%@Zh16s+X6P(gi7{GyA"
    "d)skjcbsSx4}S3iFdi9M^sP$&n*?WxD{c-9!{~WroIkleZMYgXUSq9-cQfhX;67_&sIYkx6fIS&fmCBbhMBxt2^8WN)yW+`D"
    "(6eC^wn!fZt`TTPT8fyv&t!W9{Fbur{|WwIY;6`rO2nVj@Vn(>C0;3m_v75zUQxA3O;QkdRt0J_<uaj!95Y@{Q{6rNC9!FTx"
    ";Jgi*DrCtG*#J9(e6y=m-G|j?Ek4M*;R^`67!8ap;gS7D9C<{O)`swlK0&_CeFUVeO0DV_Wz{UWT-TEev**6+XCW2p4&=ufs"
    "Hx}_n@f70KQ)QvmOxl}3z9Wz2i$U?=wdN1QK7ML`A0`ms*hU}yzQIASfKUn>WfOT<#L^alwY4nrnPbjr_Wqw_EC3*@CpOc-p"
    "l1?n_zB+EUB~m9lfcF|CBV%24p9yd2%<6HSDQA!Jh>kaDb|oA23238*lyosE<){M05X}%A5uGHrJY3fXJ(VBFu%oM7*UXPX@"
    "kRYAG!cs(kP<sCwTALI^MLnjCV9;fMqXR5)D(R?1Kp#_@(eTo>8AhrSD-j3Q^ad?L}@2{MnO!DZH1a`^)=ICIa$?bMNDP&B|"
    "ffG5fa6WdLM>E4hBS|2TW=+e+ryUjKrxuz>`J^#EUsJNQh}!j}gTJ{=bT%`O*2sfGzl2l2Gv1n%co@qj`V*M?>IQV>v%Uno?"
    "SXZKOtIh8v`T_=q!n@5hvVt&iOu<&fU4Z!h7&2C3EKxCpObp?#FSwa#t=y@6&L4r<2<9(fVe7f7jTe?0lSX4U|g40^Q8v_7)"
    "-6QMM=C>|cz@w`Tgt3Rin|&0t!n|}*(&^`akkwIg3ms{585t-}-a2;n(u@_GE|X;$$iWbq1Ov}t$&c{cCvL<4ZL1yMuS6F!9"
    "u!35s&_MgRO;gS)AOhfe3WJN-)NggS#YguZ0Y{&_G9Uo+wM!-Apo%DP;@gZcL$f6tqfXPqiGWCtAq&a1>DeW;;$A@;1$gTrh"
    "V$vOxpYW;*9yO(BQw-r}3Eb1O{!5AW;akLS6Z&OM5>l#HVF-BuxvJctFXFT8%j}f#33W&BvrNvcf2<Iy%=1(5)a!O0i5vHf7"
    "?E0lpNs@u{eZ|3rjOMkVO}QNCY^wl!nm&EoqiOSq?3vNZxG65n<Un1XLR1Eh<pX(tW4=$UN+kUvtSQ;t8|Wy2l3SyWFZ_i`L"
    "dtXYmz*FivzciXB{+6l@Q9rsk^Scbw%5}{o5Fx3d~iKvO!ubsdfq>yNzld6l6KXHxurBWL&IdljUCP25FpgYj07};8q1)gMZ"
    "@jRGBLQCTrlH=PX??3>+rmraIB(VvaG9Y!Ju^A-zKzAKKwrYU(4IFQXw!s5~Xq-1|o?6lP`KbjwCTze@6b8y5kOg<!qgjnwE"
    "p4~2|BM3w*%fv_wp&(pMV-<BfJ~(9iJJZ9z-rV-FVMC&K%u1Y539@g@pXm4;<tD#U#z@&^QcOUpP8D$;|dd4ZN@0Y9wwC!Pb"
    "LE@T|u-=I$4k)fV|6WTc-SD<=)mV&EIuZvXh3~ds`+V!yrJmk|<xu))i^JbhGZ`BfSm$J34rGrvhm97biM1QwC}tKUH1BQ>v"
    "5rj$#ce0+I-r@d8vm4^d)<wE>3Pda|4yIi}M#f!;|2P<rH#E;hMs1XAEr#vI8Kl5wY@d|ME7GfB|&5;P`!^vednbM!X6t``D"
    "5cIvp8ln*|@ysp&356$lfIx!Yo19{`vR<eQY_m?P=81}SG#|Lk_$-lkG)kfOEX{t^P+x<zcCIxh5i)H})hi>EdP8`L1yBbJX"
    "P?l&roHP(^$Ggn@Y^{%%%pSDWncY|;dnIN6<fvGUyMsAR0APm*fGZTZ<!TwuvZrDH<EI0w43>dHgaj>>piuNsoi5}0<_7-i="
    "n1@{RR&s&cJFn*KVcGEia&%`p2Rc#75x140b4|DtsUF+UFr8d;ivnEZTqDxz~tU$akeMZos!vA!Q8tz|8|s#fU6g<C21vFd9"
    "?3Q$+A=iD=Nmfbr+xLH}P5B#(R1VAX(x5OQN$TMfDm8N(b@c!mW60bprSB%LpTdVxlmmf^0}gr~S5DP1bJHwVSoa{TR1p$Nr"
    "JJ0aB<lcPc2^L48*|P#aszL$)8Zbb@2HCJit>5#aCEmhh79JO-VcfOwhbl6zTW!aTwA@jov;ga=55*+zuTUTn{W8le=3v=QL"
    "6P7?BkDzc({_WZ}yrpTp~-QfU0`n_y7i|m0my##M;F5#Dt%fD~s`;uq}JUEE9)i4OJ!5e2b@tA7E7El|+1~XC*K=!Xmq&eH)"
    "c1B0iwgG_r9Y^h)w332NZo-vC9^CCbN%Pd`LL>GKlE9!;@@!@GcdxDCCwh};AO0+l>pgASCR;wD*25D@RXnvmg_%Kse%GL=W"
    "#S*8Bzy1U1U2Q`J;A=M=r8Y`^j#L)6%(lvo)!blulTz+k1g1gmGyG907m&K>AqpvCoEY2J!NoI5Ada^jn5`6{7t+cN$+|V_9"
    "HqMf-B7Tls53huwmQO&dHQLN;7yW@a)zAdoz2GrojN4iJi@{h7&KF>Tm4i-gfNB0sxXpkOuP7+eik01PFa!VKYupFe?2X9<X"
    "6z^g;t&H28en!aLSi@#cOFh;HGyvj<IFet+}x$ueFrzYqIW5jU)M(a=81#zQTX`bgQJVkiH$$7^~=*_&_Ad(wumqip|tCcrl"
    "5MQ8Ia%HHIWmbx|?CICLs-NY-`7V&|$jCl-95$%K@*hD)zXuhx3#q%cT@bE(2wo0l?J%Du6^RVLV_Re5m+cr0G<D;Zw4qH0e"
    "rJO8LTlUli>51586s2Qs0Mx1lpa^`bxsJa+egc2H#NvQ^)1;A8{wLIWcv88J=hSA=Y$k{zgDEet1(*WmVUTFsZb{mJ$=gR(3"
    "59H7k#=A@H^CRO_t#DCWff80R-?`oTLV<G>TmmtOJ#o*+f~7DC0+by+`;E{A0O|Q0mIZ_qI1fdHOjvfKU%yE4-RU$U!h_H0k"
    "++mwDvTx6L~q*ZP7Iw+*3Ad&F%NM$GV;1r^m1@{wLMkO_~MZx(B!{0Vyt6@jV*^Xaqi*Niu93x}g$G)O>uTw~3E+H}L9S8A<"
    "mho>T4-rO8Xo_o_Btw6GtKsZF5YNwCt5F`;~$RVHr(TQ@=*lw^yd6quD@kz6O|D{%ry%RgbpSNq4S%4E*+-6NR=p6$+L5P2H"
    "kGF`lGbrFBIE}^kiXfXYsXeTycOhnsh;$7`3E(<qsZBWA9{4!##5x73;E`9%`nfxgx|Kruwau>*nnL7bXE9GX_$xO{H-O6C6"
    "jV<QZkZQXUTTcv@*L&~_3g0y`i3eR(!+on&^K0uKqV*ejLbhkr4AeB9UERQAs*`v`v5vL%7zb6+Zu$)+6<FRTQhh&rpU9qlo"
    "6c)1GN-Bh!lq;n+x$r&AT4fb!v(TpxMds5=xeDRAicv|NU*G8oIr#x3|jb1+{U|m`v4r}<e%uypqG`=k@>&T6mBhS*sdDStj"
    "*Z1H+AEqWYXhb3IL`<Qx^2g_VuUpb~nCktz#<zXZe3P3;-%S>_`>&UXq{@2IwY<eMo6dDC3iSpPM&&cub>#hc)UbFCE3p`uh"
    "#^F^)OAoZq<I{6wLLKf2^<O!!4?toJbJ8_fBkZSgwL+Kx9efsj_oiB5ycMOmDXx01Y9Bm)5XeP#LjM%fklEh?u=_uukh`EJZ"
    "vdrKeqdbf)&#(hA=(1w$LqEq1qHPLCP$^*<B8ZA7kRL6c*NLS_Uq&z!>Tp_@*Yyevm?W79oxkGL|8tx+GTaL<6Kj*CvoV%Zp"
    "Rhq#7OFF_;^L3!=;S(!Mc=DQu&XH5~Zl+zMu;2V-Il<4(?#HEZ5x1=Ou^%C-(r-E2DPoKD<=#N91X#M~H+|o@ujOrIQ-8Awz"
    "b$N;WoO1l5BrMS6k_F}uM=#T1pPqcHVp8|eiQGHn)t|I3Q4?f8w`T&zliPvlLn~a(bW!~SgPXDr3uWN0QK0%j0)^3tOWgB?{"
    "zt>Wk0`sHps+Hj(OKQ(6wfh&jTqI>OM!@mLT_e;Q|IW(3p)r(ium_oTOlI<#ZV@Upj){=+qH6zrrzRmkRdZ)4XjW!PDm#fM$"
    "%PjlOL~*$AX{s}%OjElOBp-Hh_onXZkvw#w-{%Lb&fx-;oz?mTGhduG{@-6X=GVDM`vZozA$@L!J^kVL1$4{4&)2@aX(mj?L"
    "%=JsP=hnSava5w<D6t}SefQxpYbcDI6cz*T&6d42C6%@>q6gwG|v&U`45!OtMdez6Iv<r+nc=hq)_={eMWQ_%JcB|^d-OY;&"
    "P5e+}7G4J^_B<RwIO^w}J4edaSS(5F9i7OZ{C;$A*)YEcSY<86?1LG!CF@1{D|^OP_Lp@3FUK8x&UEq7et;xqJ20a2LQNVKE"
    "a17t6+ERfg$IUJG!h?SqHLPBOrT_vFMIuEh_VGevx&Y017zQ{3jo-90BZDk;##cRMs8W_LEGxneN5PSpkxjie7)aAwc?>)H2"
    "6q&1OM1u$46Uo$5ozV?h@ts%gobs3%_~j5bjf|VQq5&KT-%|g|aNKyQq*IYvhfQoc{deYytsx0VF*yk{T6q6WhJUUY3=pwF8"
    "#Bb2{jCO^iWc@XyUvyr5r0fAvdz&k>yg9w<boHEAAN_3#t5N&G;42DQXP(G|QI&f#;Dt8FSTZ|@BI-=1QSmDD?5_TNbn9HUW"
    "C%1+p1<)>8eP%it}^kTfXy@tP9T){^-ctW<T1e2y%I)vY=H1W7n1Ba3#dR=WRfXm)q_YRU1eVL@YqF=5mxSY_-D&4Rsm`Z~J"
    "E=xe_0muoyTxKT++2gs>ESVHYig8mVxY_jZZ-XX2shjwx_N9P14&XS)5Tf&H(jb_^V~ZPjbWp()%9FU(E7?|{fliNU`CPEud"
    "a|~Ew(7s9pmkad)VA?-H38f<p{xb1y>EW3a~*3XARvK3W9*ioH625HK&h;7v)9KTEg!@CTCvn+=V!zPZuW`?nqP>P@l&(&m="
    "DTWT<@YFtznEL6Z!}x03dH1Tj@Vd5lM8C)s{HTuXm@bhb@%HwgE`6D%+0cwx-z&hFOop76SI`bwv0Ex@p_Lj=XVsjze@NSOb"
    "9QwAR&UqRY*`_BtL}Yd|Bwj8sR@Pt4td{&;Hs@Je_2=<glM;B0l82)m!{^|nO=vjV)fP@w_3{RGGQebg&Ho?4s2To~fAqHq2"
    "o4iT*$<w@BEZ_*U2*WwlBB|N$?iALlj=^I=g6m8)pS-rEVlCIrX7K0j1<FmcL!=B)2L9q0Fn_g;9r}FQFEU2KfLSfQrVi^&>"
    "7I*Q<K@*=&y7)-92H-}X*b`k4))nG)d?cPR9|`y2cybtzFHYcr#VRIZDG;cjbXw@o76Tm)M`_zYC%4Wztl1_;9Rx=AOCLtrq"
    "N1Yi`Sw2jSYxA^;F4MqzdXHw3GW2n+?h3O6L{fzM19))TCsyCPVYz1S2(iPLDhJe41%nPpUJWev-1(zI%4!Npma*7I?EU)LC"
    "V18<-WG>EcmwFa(;l?y7F(kRhR@(VDQe>HM}>f1Dc&Eh|Uxz0Yqo2cz5&r)i!=~Y7X-zL|OJ;kGJ>RQZ;>Sc9n}@+r5`I#qu"
    "<R=;>1IYz16N#Y=A+B~qNn%WVw+nkL3!J;2qIC4{vQe{=K*{@bw_=y6NHg{(aFVDpx06Zi7Us6;-hNqUl0^L#|I5(A)PlC<~"
    "|JUh9!dnWC~AGyBZ27ych+$x~RR#;r`<a`EzTplZ61rcsEeS9Wr;zLOj*R>k9Feb3Vaf9fBwck9p*2iOmD!#iki37S|w*^QS"
    "8z}_pX8DpaW{>%8wr#r%q0xVLXxElSvD-;vw+)p%4@U<BTL7+5R%n(J{IAvH_{**b(__&2f>NI}KUxa#-w$1aYl<}-Tj^lXG"
    "nn=Q)C;oTKfk3>wu+>|BP|OKw$QA5<D6nRIL%0*T_6G5bPLFz8;y5cve#*>BF1M1O?=O01=#p^j!Q&mff)cqXUeSN{mmE;uG"
    "TPBl$8~2r%ZO*Gz<is*%)NoG-cJ8Zx^@aKqmPT1dxAgq^Wu?6+r%YY3sskJr9eU5sHHZ&!5|m@2EEM2e-A%`;s!cEw*gCuuP"
    "jL)PQG|R`Bq`3|g%Op;qa(6KTJdB$)7hdlIH36UE&v*MeCBOfF5=T|eFnT(SqGpqH@Oow8LxPUex|xQTEZ`uIR^1D}d}__v<"
    "i?q;4~5nb?(sgLxh%||*@*oc?#(6EjN235>?A$$$HEkKTQTi`SMM6jP1*@RvuWD-mqPQtP;ZD3G7PqNRPVQWF1riu5pMk~_T"
    "9~A6kf4kMigbMKDsRh*hMZB!P&%m@<DD(m_bM1Z13wx{h)rEry2MS+3wuxy3xU5i0SK}qXEaw)ss;o@>vvUl|8j-#E!>G||h"
    "J;h5Ii6wdqmzmvr*BT_Mzd^U{PX%6(32vxM07TILPvB~N6h8s|C{LHCnopda=&O(<$~c9D;u2h<JvF-z_s<uG61rO_SRnO+k"
    "HQE>HvUpGrv(=LLJAph)%H(NRa^av_{GI&@~z-;s}!^ACu(*mP{XSSX;t%8%=y@ll$f_1VL%mJSoulfzlKnQ)-~y);JUtY_)"
    "!=>rgKQ=*9_pNm}ng0stbnhLZIF&)#zGayhZjT6?7@^P`I1a)I0Hzpi3@Tles(xQQ?7Hr_m#1O`j?9-$u~O4wS7XjkxN40IJ"
    "wt+nvzppN?l73?<!Od20`<)`iZvc1((CnS>2AK7O@(Ts8cB#0Q<?M7Kvk#rKsf&daMkZuERLa3Fo0ZRKgzQTzp!dxxD(J;bW"
    "o6GovZh*MMK;rolOk81pw9vx$&&=Sl^#;04jbiMf7i-LT0eq<$;a2vubpO$yk)5cxB7o!Bk7rv1P^FoWX&}ivxqZ@34`hqfC"
    "OBpWcyDJNFI;T^@ohlD%rv62!2kf!*$8J0idW%psw?>J+61OdfSOID$@lw{ip%NV>)|Xtf1NVJ6RF{@fHOK;w>ey0x?KMI*a"
    "2MIzRhwnC+B#s)tgN8<OEFu0#dbE+68{FxrV=AUc%pXJ)m`hp9$y9w0Wwm{MV-OVAP;`z(NqBAQk!*?C-1@Cw3pN{F)`*KP~"
    "u|Yx9?VEx+&lFESqP=S|-pa$kG?W~6zatfnN`Pzi29AD@j{xK6k5uPu2bPWXv-w`qg$3cRp*7>_J8aJ5&$3<5Nak2w{lZ9kF"
    "L6tTmH>k5(;43tT|+fpRtv%?h<wV6c5plI6;Y7_zw9j!4i+GZ?C=J=|K;gx`mVuH7{m+|tXhSusgIL_RKLN#Hkb64P3!&Ut7"
    "+${Ec1srb;?AEdxJQRZfI??cKO`&WOp0)auu#g0r(>AegqMpkTxC0WUPZIzb-}f(nX}dk`CiL+8$B*E;q>8w^#>^6;v&0W!q"
    "O%noFwZRY@G~<D_>QoOF!oUOL%Z7U_Q}bxDJMtip6pTTwY|o!{-=kYTb<o{RBkP}bbF8B;W(O0N^t*{J8mLIC)8M&E~AeKuQ"
    "+-Xzti>*t#F0re0aJPW12pIOX4DQ*I)txs-9=FMcnUC_WEn7lAQe--D#8Tzjfq<%2xT7Y!JJ56X-yruVu9bC@T*|`AQo!O@f"
    "}Uaa=|CeB8nZ;|=^nGz&z>0KLKSfoRV-WS&y%;K^YF4=U7f2?|)yg{)O*I^mPL05YMM&k32}r(4wIb7VC6x0kpsxY^brTZ1$"
    "!FJR|}7+qiR6^=#&^a2gkfR7C}@pJtOx+`Dd=gVE9W+vwDfj3Mv@znYhmfI2Hfk8w0s3<>ox{;e?4~LU<q>=F@-S&}nKXNx8"
    "&v-m5`H8;!zAnpPbiQPR4tn%=q!JwV2l&U0CH&@^2BITMVImt9*>QsCOy$CEM07^tqw1dqGkE{zIyRBm3B8d*e70h4S}@19$"
    "<0mN@|FK(u(K<%w|n4pva>Fet_aI2jyxCpe1>D_s4je3t00TwE1(V^egu5x@H*m-!AmZ`9RISfj7Qd{@9;CDv-ven8=3t7?D"
    "RfN_5=8RU{VE`2-4GSNz;`RZd=ID_40PB`Pmi#cbWVd1)Zb>gqLpJl==`VtpYA>yJWRa_WG~+F}{tSJt==@Zw>#@3W5GN6es"
    "^gd(C0>-c}Xw=xo~5>2I2z&G?ZPpFL&lRxuekiZbzcDgC*vLb46Xwi~ruiPAsz^T`GX(rrX`>v&dQKyFtFeA^jd!7pH5vJJY"
    "hSqOhw>7qLS5M#3w=*|;Pndi=y@qxJ>o?M&6jcYv&ItKd-WmJv*O%BfyhPM1hMhg|gERbRJ=WJRYZ;dbHAA9@TjJ6x}lNbm*"
    "m{^J(8zjELVco|EI&C}ocTa}VB%-s!V}|H<shNk?3i!>bc|4+6M-VC0B?~~v1WWoZWkvqnBn`s>bkv94-TwB;CiM18Z37N*H"
    "aN@UrzzsD#=zF7z5Ac1JljfVIf*e*@ll&7;+wsu%?9{CaT)O{+v?n@f`jJ8wFEz0o5O+*p$4!k{}a+y%XMCIw;fw-v6&=UGR"
    "c;z-J|~u?`K;#Wh*(7qAS+D7@v(>_)OBm7ot8s(XYs*Or<2+gFLTcv@S~y5WM09o*N#;Q!CTBS`{&cV6>f0R#_!`&68lE1hd"
    "t!i-;o`0dl!igm-JT@~JXV>Fo>I_~Wtxyg;F)V;qYkl*^v&5b(96i{D;8hL3k8TF(93=UVCDJ<Y4jef;qBoV0wviDra@s$lo"
    "|+w+ES)G26tqcnV}>L7O$>3Kzd?a<u58UXh4@l^jYKG2O4l!G+G(s%|-D#Bl^AHyH6`#{7_Mntz40{}!rH3PKH{Fo>lGS4p#"
    "@N;wfaS4jD1doOcRFZO?#I{Y2UA@iSMJDO#-v8XTfO8T6NNWp706->sGDzE1VHe#W_SjATPW!`4AR-&cec8_$qZ4S<Yav$50"
    "B>1c#!HhqbT^KnyKx&oE6%xt=GUizCzdC0H(kb{t8qoKWLx~n33f5?(|ws+R%p^meEyf=s(GLEX>Pkg4DW{6Xta>n>d7Zegl"
    "{K3yf<0H-?kS3a|8ejK@#n46WJgj1HuHJUTfjW#R=RmsA4J!?6!ca7YyfPHUN+XlwEqi>oDRLYF#ZGxjeB$P1;>VF1L+ne1("
    "42CQyP3ZTV0NfKt`N7m^lUzH|)lYDuVkiDS$;^7N@`^UH@0;K8LT;-0}~CqYH~n8-GFxHfvD)%M}uz?^&~{<H&x+`?`zJJSH"
    "bX@8@+)c=#luY4QA^rlj$=3jf8c<OQkNN$n>wS3PI-A+7si0+8sUgniEZ9J<sgF@tC$_wE69uh6-YH9j*e)1+!besBbBj2u)"
    "?i~mK<ZHiY17<o_o*Z&F+a>nN8JcWeu;ahB*#KQnqge7#uK4(3uZ2H5dJJ#aknDy&JlSF};6(8bE8NZeTxk<O(U?bd;34W6T"
    "ox8(ZO-n+mDRFp;3G+lU43(;TDSbquBr{wbF=k-DGn$*A#E_ob(qM4KgQS-?^PAy7SqS4`Yn7WZsP6zc{%Y03|HWYF1}zu36"
    "H5oc$8PcgTopg=vOhJeJHI^@qPPwB3x%#`}vY(e#=BK$ua=s2BXbp>10kO{BEclZe8+}Ef6Rz16NdxVqM`Iri(vYK8|<wq?$"
    "YH&)gB^g@fjoLf}R7`>{_Iu(BD!OJKV?$nR4E%Cb!(l&xWjWN~C;zwPpnYZ+?;1f$<&D!-VJFF=et7yvLk-bZUGOqkYHTGSD"
    "aVu05!FXGi3Qh50==PyKe01qIdJHnebkFNl~Grb@84XOwdg^CQSzNANLn__R7v6c7y0DDIQ0NbU|<pcUI!tYMtr0tHa1CTHH"
    "lNIC123k28Sk@61^#FI9F2gS<y#Dwie)5P93^rg32P6yvoccE-*(CCMk7bnj69&ma{A_I%KQb|kTF=Ln4p4!INiRraIDUG@+"
    "|r3nrM2&u+_p=%sPBG*a$=p9f=B}cc9q6u1!OmlJ!4l-{v&SV<NZy1V$i{d22}v8o=kLcYZ%}P{6=kA3X$TFDWDK5l#FNh{m"
    "YuM{d~!9{mwpPj06C(F(~~jogk*I1JhOGKuO>DbR6u<s<TW$jY1O|H<%vgCqjHfck!y#<M<b50^Dv>S3bzRx!lGRr)SaM7~n"
    "{AfGdMix_Lh<PMp|t5~=79#1dRqX_?3L9AUJjEUgukKc~o@YYejqvm2XpJiEx>Pk9)`F?yaxKhSvV<_dnUHHWx)Ju}vb?jQy"
    "Li0-h1=8va+{K&){<`BZyfFI;4*A53rX{eJ10Bk~~9cb@B0ANdUL4MD7E~<XIBU~o^xpqFW);3L3F7N0BEtQ~A_ED;a_-40-"
    "KR$c}f7_JC(Tn`-xIKdVnm=x=<GYKKKo2M;9wwBJ2|utW+NHq9AksD|!<S3|BxzM{mG<7w_vg-j+4eUbx%v;X(x#-4S9W4&j"
    "6Hc;LWHj*9el9Afj{dXgo&;{ZHqq-b)zA_Y$DqGL4f`E+4=^aQJ=<Ds$^5gWjwQ4N!g^{?E{yfqsu^&38h>oqnd18a@k3?Rj"
    "E?;^GoWE$PiQUvJC^;*p*!g5_}`>V&7DV>(RsSEFHxMIx<u;z<j2Pjmyn1RwDeu{{5KqOIX_IA&v|tR4}T=AY72&7HgC-#>+"
    ")@vI)MO)4TJLQMaPe`Gq^L$hYS^_3nXFUZ49G!z=Pd0OdI*iQTfc>c{xa<G11+y#iF!IytybL}x|vXo%>J@H_aofx?5L8m5Y"
    "Y9dP4BCer!IzsRqY<OkW?&-G@Oas8x0+I@M_2JumFz$9tWCdWSKZ0~qQdv=^}wh}~<!QColy!6l^+--FQuSo81mXCgk1Mt}h"
    "?`D3jyo~P(r_hKc%@(M6>EypFT_mI+W0asMskhps=Vm8WPCof}DDMG#0`4+0jmriw==%mo%mAMowD7Tb1Ao&y2orxBvYYbsl"
    "YbWICb~FmO2HWO>gFtNF~{+Qpn-=JYW6c~(xel~VfT@2aae|lw1<1T$eacUjICKR%uJF6e+fuRjTy-R&;}(h&46n~iOmeyXF"
    "_Z?6NI6{AMHDc@Wc^Z*P1r~gUqK^Gmoql@KZAZzJFpKg-Bs-vyW2Z*`Q6}xz+t_p+WxGwhr>Ubm5!aM1J^j@6tWoWc+lq`8("
    "iLqmWHgka`gc1*Pzz%?-RGngXI5^0^5_bUQHsKy(Kc6!5NO29xWHxME+?wmXu2+kqQIa}zl)SH0a{v|a6;v)~Pj@wj4w`D*{"
    "83h>(wwDu$}7r`H<^tr)5J&`D@0Nq}U#X*EiYeoF}{)4#R<~m;An=x-&<=*i#;$LZAT5I74D|4t0e7i4m!uL^-6@3j9CGe6J"
    "+mh88DW)Ytt!%1oA={l9WjX!s_a<9PN}dNPIZ?D}o@wSr6A6;Q;AYdeDgPgeH}S6S44`j3?c`r@<)7#xV<g+BiFdaa%w}y9N"
    "8$k<U!1T7Zs%2is!ZwKoKP~9a)XN9nk1bAOd2S#vdjSaj2dKPkWA#Hj)2VT<a5h*8!!s9Q2;N7t$XsDvj?DX6xT&F#`HP9?B"
    "v-~Mf}$OL%3&Hfr=FtI|Jw#m<pv3u_rnHX*!twUEt&`f0CiN<wPO7O};4cmg2$g-?^f~XFQqT;X<2rU=W)Gfuy~;gh)^7D8="
    "x7g;f*dgo<!oa|7rNPVr5M=xlHWkLX;Pe31FGU>QF#GmoTiFr_5EmaCRKT=~x`xl3<%mv(o14JYv9gYlUj+PRTkipS*(1P%w"
    "|^sH}?#5jflPyl8tA&Mo17hHcM-jY<%T4nL3odo5}%n$l){O^NT;<n{J_Q?w<>o>}Sr_&V8w1Re;KI=+5x>k<)Pw8P{t?XAU"
    "_p=qcW!s6}XKU=_Ut0X#X!`hQZv&q<9lX0MRg?KUBBC=H7G_NtUXJG%4&!@DlXgo$G4`;}4{aL%K(>lyW0!m$$zFduYDnOF*"
    "ySeuJR3mU&nXegr&X?%d{1i>m1nm%b)az@`lvKK+!*%p2aCt>!4|gyj4MoCWq!WY#Y+wz!bBWktrcOlA7joB(eR~>qbm-Rwf"
    "Woj{9>DI!J(7O1>ZTdiEM1M@1eBY#BeKu6p=IudP-x%OYq92V|aPH4h+7@ISbJ_!h?zETnR2Uk1MtCJM;T-A5?7W<mfOPPr="
    "Vmw$En(z};S2&!y?)>4{x#smJvS_JF2|ZA89S@KG*#s7w^_hGWO@qFxP~w{c6rNiS<@!8|L7@W=C)qP3|}k9`~r3$_ZjOx)$"
    "f*Jg#tNwhNPBfVUT0;YR6-3m^c((ft&$ZcIpt~-m8y|$4yww2>oOb74iuHse60qDW4K+;dse2Iv58U|3yMiSXyJ!$;X0-hQy"
    ";s*-Tcvzv1iO9EsZQu9oHYEuJNIJjU^X~!yu2xC9Jt@r=kk2O<2uQo*xb~#Rwmz*Fd>o4hX!;2zCIfsfY2mq11FOeA%g?RM#"
    "Qq1FH`UvC^3*Katv-&l2AJ_eRK2udW4aA6_j2Vc_1mx283X|Gm*1HIfc$-PnFm>5Nh&5Sdl5d@Z{ex8mH^xafEgh~=L)v~5S"
    "=UWCO#ZBaLwv6etGHu>dMddLyk}NbF~1rOQpLb6ZzZA)!cEtn}@sXvQs!4m{+K)z^0{l``T^^sKg0=aAFqsD7Ep|y?OJu9qB"
    "u~29un+z}!V4oHIXD0bV$L2uo`*E=Lh%-?OQ*wIHx9nPlRhWUsQT?vLSajL}J&J8^dJonWlfgPc1_!N4WNxH0bGBhdz4*`5W"
    "w8vy<;i0BMRVYRgWhgerhZyoPc`;3oOTLAEpLEV1-7ZQWA@@#R^(S6fErrio4-DYf|z|lls{;h|fb!lPKv?hQD-!o_@i7i~0"
    "Xkc|S#(f$U{FPeAPt82QY_8mJ5eG19rZzE)7gr*@aG%Dd{uEm4eXMn3OsW7ysO=~J7(2f>RUy8U+?6kNRxH`d`q&s{JJ%dZ2"
    "6)HXs+7m&<e%sqyGTD!iSA67n>Xwa@RZ6FrcIg<IZUT_d+~;YuQ@jXfIGAW;N<6!o&ZW4C!k;}48j(4O6vw>g#wkqiXNa)P^"
    "edm=$ZjuyRwLXTHC-!n-_QLW_9Wk^V4C1XI7>$I|vc>6fX6PX%S|5)%EDtCj0s&wO;}OavCK4wToGiCT+Am@wPiLY=^+DCwX"
    "c4KZCB;cAw-YbrbK7*6`;31Q6YLQU4Bz=p0eA=CM_crv`OAx;TL=Owksbt7L`dBBSj}em-tlka_^winHC~l%I2E!;RE8kt_n"
    "KfzpmOLMagF1Ggr9o5@tFdHA~N;x#Lacuz|{G%v2ea^O#yCsY-FXl5GUU7y5^4$$l-@Dr7$`+Eu|);8#3w}1^R`MaTgG`73$"
    "3_G?D-sYcY<@Ww&Y)t~!6-nDH5(ylwsu*u;uHdH^%YganMfH0px+~;1C=<~+q1N%f<~qKebkQBI>*o6Gx{AExllJZ8Z@b-}J"
    "1oDlJo+;{QII{HI!!INmt@82Y??p<%%~8m58SrghTm6s@qt75gG&$Ksgu(eZJ}O2oHjq^4e+$u6skQRULV-+hc;EVnIyxseJ"
    "wq-hxby$$-kU5%L%jO2e@K@X<Yy*pyl2Z>EF^<I}U&&-T)tuHgR3FjyLx!oct5fxnq{qM|vLK+HB$j-F2MsBE*4I{ZFI9G66"
    ";Q`6b($@|owzWjSprG%s~<vSRd|M57XTDER4pr&WMy9iZ3JxCSLWwLXc)^fedNZ?sf6XnwHa;};h8;n|Zjs74;z9c{N3HoO2"
    "x3``_ld_4FP3~-ZrH>gM|h5IrK6rb!o&#Uu+irfwWX<d7L+{MS+oA7+e03f1sjavYS&NZ{H-k4lvu5EANK&=3&X`H4%ra^$T"
    "6Y_-;(9SIvY{@d038_?Qmg01hzL{@dm}M~7O2XQ<va1C?Zf^CFbo+St+%(>G_Xhs__)+sq>k;(&kqhOAy;Jwj%HJM5RDwgew"
    "`xLf!dA~N!$+hH28a>*3L9~Z2?+@J9%7v~+mqF@tV6avS++$Yvvyl@Qf(*y(nc!_D3$DQ1ZYF!s2<>b@jBk8oA_|M1en|Q{O"
    "e6bcd>X`eLCE4ynYKUo#5H^SxhB9rV!ZAD7)gHjSZd|eU5FJ_`BLSHpmIAL@{OxA$m!Iwn^-^0{MiS^rY*6v6)ggH~ZLM2=V"
    "Ob7Q7ah7+~*zzSZWgH81wt_@hg&f$jlIn~^Q_Dz8hVHA1Pe5T>nUZH*rJGh9V?MF7Vt`VX(l5A@>||L<b1=%1t)4r>n?tRTW"
    "i+nacEZyq}S+MfS?6P*tX01(|7x;Ll~`P1eJ<q4FOhY97|p2t$WO-5S(t{QOjg>|;QKKpyTMxhG=NTvF0e|lOQU@VW*Q#Som"
    "&gKq<1+){5<I5e?D?WaH-vQjCx`sbfUGx66y}czs_Rgk%Pnfu0#DRJr^Cm>a_-J@Omf{GWuh2`heIM9WuP7OIX_6CYCtdxQ>"
    ";P&1=YmD9mV{K*mg^I&BgQc`z<WFE_}zE`aqpHr{TdU|c@`a0pTvyuRTur{627-QiTx;G1_2rfvT-fVW|CBH2>`gyw=}q!Ws"
    "+qn0#XyDnZ#+w6E7_kD0Oq>x=?wxnBYPX;<jjjhVoIY)X?u>PkYS7wE2k%jUU~2C5|k2;71Bm@KN;rY!LRcHh+3FwrAV)POd"
    "CGn&i6x^Y(QD&Os5t+d~2uL9UfC4BAHH7SqQ^x-ICqb?1J6qKg;<07Q3^kM}Bg`^E}hG`k<w#78K_kyM%qASv~--|-Fy0nT*"
    "qzw7;b$}R%A>+|&r?8$>GB(!x;VIuoJP1@gCZad*A6pe!J0!#e?zI%EW*Ir)6>uVMBN?k(p$n~c^qbQ(m29TcAyN~SAe{|&r"
    "EDa`c|56q0L1F^{GhTp>mZW~!*Kg2_<Lte#b@DGK%(jxYT}^ZKk+ODMS=-1>Bv?j_MQ?z2b=U9(^bz+CpU)qgh%Oo{>R+R2^"
    "NDx@ky^t;f*Ky|*HBYFbdpXqg?wz;KUvYzG=w=Sb}AG8$QTrrvIS;s2bwHf&W$_rSt+-Xe>P15jW+fwfA*lQ8}nahW^t`o!m"
    "W#KR1yz$$hm`L+sUomIfH$nM^*iYrvdpD{n0p`zNR^+D?U8zK6CQJ?&yr#8s#2$SjaZb8cB?{-6b}4f;TQN<Nx(401ofU^8l"
    "jVfB^uaJBw-IONoaMw$|}qYqKy(*78lmPX1-`><=3#ovZJ;!$kjdh6RJR3nGlC2aL$%H9ZH(()Vn7x>O_v3R>A}#k0i#zr1h"
    "&_uN>+YwFYHW2Yz(SjD7i@8UvFky%%t)b}%Yj~6j92yh>-0!X1m?PXQ7<u>W7SoD=$#Bo2Yt&VNCh@`KpZ38GL#<tZ~nl-Sl"
    "6SRZG_RIcoZv(H4W|73V0%)G+pPYy;7ABF;@KwBWa4+*>tk^bmQp|K7A*SV%OS$nao%q}PWD|Tlf@HhMWR+k3Em>q{Y%G$lC"
    "jG$RX4A(Pqc*-~V#Lwj`<(MIXC78d@B`Hl&z#zay7sZzPEbrdOn5;$`9I~%+MM#=TMK>Ni9_q{eP|msQg&=yOa}N|uZ7q24+"
    "8PO@7nVKqTPT87}1?6STN5l4e$qZm*NUlM9KJB>b!@<B<DT=a5_5%2lD-bx7=ZykBR*A&DRdd!uqz~v$oqEda~M$1dXzf#%u"
    "*A`Yrs*&9~qUCzkf~XHTJcm3dOQhG!I}aBr_-t7exIFOAP+w~>`H+hIYa>9TGy$Inv#?QTtz)&h`|X;}f=^b>s3^zh#P8eXX"
    "vpgUjO)2|~DUEqrMGCvZYz@x$j9-?YEU<#-j-?pdoCD1KdO%m8ND$RBp^}pTH5l1?n$Y-M5z6Fir7~r$Ig@22hc#Yl%^lk?9"
    "-fIQ;?8zDP(u0R^pK1eZ8$B#{W9$n;l;Pzj|GCaVTPiG`&AG$vTo^dhZ*w-Q|L!qmY)caOfsdw+@GafLtCo)8?^?1pd2G-9u"
    "8A%rJiv(VY=yg<zntjfDYYpaGzGiraegZ9>=Xb<pNrd{IjkYHW%9pW5MV6*FjpJEmU@zN7Mtmyv8-dPdok`dR|P5o{_*fpyr"
    "5M;^XOh~?=xc_Q#N>fP{pIe2KMU$YQ{$uS^sS5jh$7&mR5ghrT;WAAg{grTegbGNwgHmT2>Kmkd^=b2L4BPAE0jl%*Gym{fK"
    "B+@DG}2mwWi$U<&tE6+6z=;Msa7GKZD1MLzQi!}aJa66&I!Syuqr0<~&l+@O2-n(5$e{dN4mqyY?W-dmq@^@8zAGk8hS!!Il"
    "xz;qnq+pAqHcp>V3h<+TSD1*Z=U1Fyo{5hGKpV?i_9eG%_&Euu-0omp;FdB=9@V@RkUa(jN63J@YI<`rnT~}*|i0(LU0U)}w"
    "4VLhpuED;rfXR}N38{c=>j9jHK)~sW0&ZI|c)Q!?R&h=`Nsv|RbVe)b>wf5CA~v>)@$sb|W-B3nXmTI!S=hw?9L$=3SYF<vg"
    "Zhg4XczcIY2G~7Ea8z}9S`(tm@@&2@NDmEX%i`{V)Ad<-|zI&o)NZdz?zQH@)O)(`gnV91%K6@1CrZLIzb{LIxmtV>MfmllT"
    "=o1d%&{iL74zOm8SjM_NMlRZeO~QE_U#gv=D@?W}hg7B^BfArh^Yg8~8W$@Nc~sFnetBUz{~h2{e9kwvH#&CSiKOjm<6^+DF"
    "|l*g}6rd9{>63~3wdwhCt1cEeZWbmtCZRsPTAs{ifzjhwWzP%_-oOhL(RyDc8r_Q}xgZO1lF{)x^l1^|febSvsToy*K6{yMH"
    "MlyIp6YIcBkD<J0~8(<g+aQ~5$47XP^yLh{kjqTzAwzGjdIoX;HAbZ#Q{TQVnK*{samUd4qjilGd-O6SB?tx2iMWJY3VGg0U"
    "b{o(;s`lKuaqk=I|9F?1&5G3R2kz@vFagN~@P}3Y!+bkN+W{c0_TN|9W=?!lck!|QCSKE@1(L7qxz~t@b~(MM-rl*~gq3w0x"
    "V(Q@wfotndcUNzyH>ciqfC}@CM*8NOD|j05&kpo;L~vve;Mybx3|akfCp2iJaZL(D_q3)Oi$r}7h-iYwy)7;K@q;^%U-W^2n"
    "e!qAeU8l(!e`Bbr{R3Kj}u}PO+4qzxj3#b&gL}<mc;{#Lh(ibz>9%5*-B0f9|c{JJAJ-0RW=Ag1$w)Ho3pKrn83cuTP_-y{y"
    "Pvem~#&G)na!g#pH;CnsA^GqOo*zJgQM5x||C6bpXZvd93{AV6Oyh!ddIPB2#t@dpPl$J1Mz_|r}wZ}l!QNoVi%c{ciH^|sc"
    "6>D1P6)C_R%po}ZLl5G`OmK0gL4L}M2rmvl>07)f<!z#kpOc(Fzui~#e^8ikq?;nMTXnT4MZ)#1WS6jt~O7MuFZiC(F>c6dB"
    "Z(IG@3;-MC)V8b1O{R~3kJ|XOZsJ|tc_hh=d+rr}LP_CgYE3+$wt%|vamz;E27)W{`q)-}*&Z<4XvZKn+IC79$yJOM=Jqe=>"
    "ywHDp6dR&`=0H{e7ep6O4%)upX)dAk$ww)?AiAP5#9M103f=H#H}x>4`bRqt}%g{Nl=oAzpDzjC6X_4)#A){V`{c(e5ZCkTi"
    "W}bPJZ=y`|mk^@yW>n*(Emhf2_UXK&Snnln1R76s5nj+&WQMZN*sZM0oII9k0FWYFu&TFkXhsjPC5kp7zJpb*(vb9VYQ(wc~"
    "hVVFK_g_I0dC!6!-d9A;!_Y^nrHD#C|4>-g*LG@xZ)<lZZSMMS%whnmqgbvrTtJeWaSZ{X6ffTEGlHf3v{q!a&i@-M|<n_hy"
    "i#T|TV(8TAWK0ZDu0p=Tf>@%)r9$zcqe_weSt}fMZ!%_<^o!C|XE&Kartj>ZXGJFP})BrenAl^Fm=86NJ(d;~ZyfdHtpRLnH"
    "DDnXXgO-j_D0z6>@fEzkw@<c`+>Y-_M7PHt`=BMdz?CjHKVRzOH|Gz*9{_dFPiq0#sDFMEo@^c1vq`q3Ov-A3XR;yubQuKWL"
    "4=cn3S$-hx4VD-BxJks-Hqwn))g54h9^feq`=)`5@CP6fKn~QKdmm|hg&7|+BX5s?I*muyCBen@%%|V#Bbt>#R?u-s^dO>1="
    "YkyAyM#sg~MuqFDGsMV{aL68SI0JWb(gTe_kTm>wFv5&VNQNn5WkU_?}=Ak1I^rY$u!TEnQDM;3o9&{=qsvowV?-&H*HP2|#"
    ";Kea;o@SDBYjX*_pk4yDM$YCE>=aVLYcRpPJ+qB9(8b6f5(KDOoy@SfpD{cU#C?{LNT53%iO!str*U$*Hl_t4oQhAr}t<$%~"
    "z9D_tBNIcj8(5Jgi{N9O0d^Yj{y|=pq5nV`_0YG$D>fNlq6il1XcA9upxq(3<#Q;ZXe|Chlb9>hUE<ea_v*3RwH3YWY{#0YW"
    "IolS)J72crm1=7tLQkQZ00#nv6YU5|e}M0AOyl1xUA%g+g4dQNO@Haulb*2@MUwsWyVHi!$p$`+3G?ZA9xv=3!EzYm8n1-?V"
    "Zj!|`plq-4-Gc(mcblM^fjIo5zz&0>*QY?SMO{eFkW@t4mna2U@i=8#dj(A_NAze511A{6_ud%Es_(kXFlh=%0Bb`g$U1^4R"
    "P;61z}&I(@PL03X{HU{<Db^X=dEEllYx3&#pTorwZ<$#Y?^8_`bu*#CWBD$z(tl2*~ayU2l3y<J(ae?^$2NXZtk(Cy(<)bm!"
    "p#M|79F()?Vbi=Ug{k9{VzdjRd==vL8(E9&m{X^|x993axuhg>_QQ#oyX;2ahpID^gt>9@>%Pfwv0$F@MAR0Cd(V>F6BYLyU"
    "cYJk_TF5(Y^8LZv7#|lE_l@FRH`CVLt0xl1Wh+*u0*tfPO0o<^6e{Le$`+^1Y#L@uwQbkPr0XjzG#-xYCF!*GvB-@(y)T)2^"
    "(B<Yi{SJO|W*+xc71R?SgGi$<EnOAtSeJGHI>qoiKKb8iY(1kberGW@?|A>yT#?_(Xup@sV90vi>ijv4M&cW+sTglsU%`t{R"
    "I}PPT>U4yEA5#NU7}q>%^3t&;&n62ct&*^6UK+pfG;Nnk{)R^e50UjAK-LfV4Urpl*xZutv|i(8J_^`==QV;QfJ>*aJ%Q3-9"
    "?H**_L;9HAG<}ju3eUla&BLBg8j*O}yZSTk)~x>fZgl@+J+uX#_zHo~JN~7J=y4-u-!r=pr&}g0K$d7m(-ybg~H~E7A|g?4`"
    "-Szwb)(yTu4EoL!J!t}tDL2?PkU@mluxM@AzwURv*EyK!^dvGM{B0J!I})9vJG+L{I$F*N$V!Pnys{&?{S-rg$0D@D+~z1j|"
    "#=)%MUj_AA`dHc*Wsu6x;`XH|LOPEkWR?sJ1?N4_BWPATjS|MIC0J7x4b9m_9!2rN%AO3V13gd+b(`^BAqOg&~C>9k;6D1&w"
    "@msgvf|tiWy2tlofj}WA!}6P#cfj5`DJCM?>%Mn#+WgMJgLqK6fz{0cR0K?Tvdh-M8`k%6sr{~K?pPZAPUGcn2mqu{XlwdnH"
    "t8QeheRXt4US`gH?ObYSJpxxzMf+p(RsiFkLY{}uQ7kp7~s3Blekw<fzq%m{h_S<+tzVX1He@RPOAf_ZQ}AJeAI;(0643xge"
    "+Y!%YGO>ovaRmoILcs1kyIZ6oG%<T*Zr`23BtV0zbQmi0HhUyXJxB#l0o`;PebG)kUndVl1f8X7SndcQ@g8K>!=rcN67p_R;"
    "T}41jGW|HGohxu0{mtx;nj*^IuyC;LtOua)C?XG?+u>m198&Vw`S20}#VUVI!M>^JenejBSMf>Fk{OL8+|N%_yW==1F1>H+{"
    "eRMo$;_xhjH$-lirwn|{^>VVtbkZyg@NVG=L_-M8gcx{DemS^yhYK#}o?K6ehE6!m710o`#GxxpI)8=)42fsRZ5cB;I>zgs="
    "jBV(ej%#-DJ8glR=KO1D6C*YWVy$;5qL*u@d%oqn01T@T=j6Ky<+}rH>2P3%lYi-ad^8^5qs<MxGn(h*pXfYd0D$OxF-`UUb"
    "_t*Fw{TP3M_;)NaGCg;tPilg;V6C3O8=IOfHV9?xFFdR9Jfj!8z{3tfGvoaK4;(ek;EF42yENLrOgP}s1pA7HP_%z>p*3JK>"
    "#8mx@$du-@JMC<(K38>eJY0#^`i37J?!QHtm0`FrJKQwjG`fdkTT45M-Ht7d&;Qw=pMA{^e&>%GUWwJOk|mUmtYwkzN<*OW{"
    "8vI$w6lClJvdWsa)<)t<yxlMdEBDUXwmqjm+sw$0h5jb6rW2ROZa@L;Fw&hSruCBU^V%>Oy*;m@$ouw*=#BnxU}Clc9-lb=;"
    "hmY=r{AGd7|u)fmA&+fYf@1L#UyC<imfZhcf<sc%Wy`p^JLFR8Rzta5mWmnr(|KlqI^!pm~L73h^_Ph`G{M!pgcg|u0lHI3="
    "rSVVUbeRD8Y=Q0m+)-PT5XXL;@sokv`GF&?4((!w!ay0EK!i7}FX58|>2R}l0i-w(UA!0oAUe-XasqGMT*H^64q7U)1^?33g"
    "PmLb$=?6HGkWGXG`O!vRSw*VOsoxxN?{rSx?PRyk2i6Dzly)O>{9&x{wjj$`xz((0*Hv{9IMTnr%z6s_fB;2yqS62y4C}_u&"
    "sRe`-OCoU())wOqTOww`+|j0e;!iw+BY>{L25Z1)#fZlo8O<2|7sd&h=HiRUZWO+WCFnM1(9?iHOb{y{10coiUeftl-d80oQ"
    "tE6eL$p_QVfEbX$uB?TzWb+4A$G?G4k*wCoqOTP9tBKxOMAXa!6M(lG&8Ng}MS#W++g;y3pl!hJSY@!A-8PrTol4qNCE5z!r"
    "2K5%dI5^n=9n7b5>#K*Dq0S<ZvS<1KVdIM?St0jXi+v-0)`IqiK*$%(-y1g)d%a5;ZAj38@ut5MfhUc>$42%cd9QE<m<_6HY"
    "X>a`SM7taV07MspWJSF$zSewKw}ts?i1}>NYq^Yo^dF=4K^J<``>@*a4z|QJw%*R$vZ9b(r<4s0$e)7eVKyuxi4&MUusn$Hr"
    "0OKDDVK4@(s8`DdX4EWeVZp5L_~DEJ+VG*ezH8klj;lb`U-3P1XCt}FVX10&xS8;1K28?{Tr=^U%UD6DBX64?E$;m)}KlKC)"
    "@dCD`U&V=qZhlwl?wcUg11HPa<--1%T*6(fXG9P-_F<j(c{{M0RemCDkqsweJq6?FisX{(E*$<N(IDK}@>_r<bQ40wlFEeJr"
    "U3Age7l)za1n@DU^)YO#+as{>qNiuj8wuEHxD3B0+hcF~JPL_`;i%0Ba)saf;-E3d#0&K*Rl<6(0%#;gfY^L(^*l2sg?gIlF"
    "t7sgMv?Iv?-;$%!sw%w`8_Q~dCo0DyuGugK7I{EAU{(@((z3#Qv{kyJb@7=;}F{<Ah6Qx5Wrc<_aIK=L@U4ya(bB5e^$aPe^"
    "A96gI_^Vn34FNX0_t4YEt7J8PLIU|8mLB<kzT2-uPA_26IpYY1uyzmc;Bhe=sNu(6G2yvj^EAQY-lYFdZ<dtMsjC2-yxo>E>"
    "|y2wBkq$A%oid?+oIZ!O5;uDEQji_<P7+xWqk{VLWV}im`=0My%xUZQ~9z1s`fO}4{bSLf`t``l8G>ZzOoibx5O7ET81*5nf"
    "D<mph7qFn~KulL+R#<^@WHTH{+Fa8$`Wj{-_HNhQ6ho%&o-i@O2^~JCWbCP)G@zApK7hu_d0!9}5;cjDe`~N9KnN?|9&+eu7"
    "$Bk-80*;{;N~D|A#1sk@_?tTQuO0%f)Daa`fb7Ch&~<i3WOsbafjqRZJem6e0vQxmV+MyvZqkq`(q)_j}0wf}n{-gDtD@~J&"
    "H${<ZBY!!D^(^|ZQfefqZK~{T@MNtqou)!*3{mBjrU@OW*wDjk<LYp`9x%KW)eQl*zd%D#VtwBr^y)<mlC}NmEpn~gv2ioAq"
    "hMv6J#2R4!TYEgX#belz@KV!YuqY*$a}07R9@5_R>lTw=<s?(a-XSi|jMHyjl%R_0nzv%6mXUD*6NS1z-F0hu6#}Y8Xv2%ob"
    "Pw1*AV*X?riZJFv^1p0;LqlE`*XgUjV0ZHm1Wr%U7=LgsFMH+DzNN9Q9V1WOGe1E{cQ{YBP6`#eq<gcLLqW==6~b#dd4CZo+"
    "5<T0n{}L1q_052bixTE6Xu&v@0olJ-HXIj?EFLWZDIGL>h{({HWRh!C0HX_o60$S{&LM1DvxUw^(!R&IVRLdD&#x?pdkeR#w"
    "z|U6k(g>e1#GzS8Ahiye~V2LRvG<ON5?Pp0ZPwk6iu^}rUp{4oENt;ra&K^a~Xs`AY}GcpW}ypAiy+p--tpI;uR`p^{(#<Fx"
    "|!4-N2Z4o(D=jF`hn;zD}tH4a&a~pZA60)X6zQv&&ov)VPI=+t^)u4FTeEZRSDfE(HGn-HeQX*ar5-3HfDKhG4Yz)A2IY77Z"
    "QHvmU7^80UV}<fNg2c92i+r@M0P0a|N<>yo!|zd%>+C=Dc?I_%EtS$-^)r05TK>JbWMA2d-I%;rA?<E8<Cpz15cF_8KZyHG5"
    "@pc&D&1k16VvzV?b_>zjDfLkAzgn!A7yddTgv6*=mWtx4&Pk$SeuI&yZ&CsDM!<Ov&j+XYvtKK{pU&5X_dWIjtlqTV~yGsWc"
    "xHdJx@w1|2}Mc)Febjn0J|1&gqf;Q-vDrTj?T}!R>IP;0$3T7JU@JVc`b_deS9QD3t?>gr+_eUfMV9kON(%#EH2`HVTJw-k0"
    "S^_1uEC-_{X-Uie4-BqAK8ffU^`?DXru2KaV&1PNK=PFZc#j2ehhQ1BA%KeeZ&!0L6_Zwk&u#Z*_gSbKJlA{APH2+CVpHB&="
    "vRc+NlUR3xAce!rLXCbUVP87ea26WtLJg<zDvrSoq7-4<0Wfkb??u<4tNR;2@cJ!id1AP13V9`InE<b2CW^Hydl(+?y<+_%p"
    "l85@-vd?EQFDud^n_qwm4n9CUZhqCIPz10fENmz@?Dt=YpyOVd>lF4LcG_Z;i25;ja*CDF0I9&|{e!<)vj_JmD9e{IU(d=uA"
    "k=yS@QNCrheEJ3wtZ&4C!9{yuSR*`o7Pc(oCiSmj|uQK6uE$~74N+7Tp)!M!LOgyd^rxaaiaGch(4Vbe?^R;XD+KkPj?&F%T"
    "cwiJB*Vc&UcwjkDY4_Wv3boa$CKCK8dsfoH-X0XRv<h#Y9UGffyX<C;v93m&+Y?y;~1=wPlHtKpVY%|5oq&EGE{#2aR<Lmil"
    "k}2?counK0Rixyr`=_0@VZPBUJGhSZH)dBt)2mE_ZI_{^hsPF61Y-F5v)V$5X1r2M7-1?}`Clb;ohk3{;XQU0_Np~Mb^;K~M"
    "oD@{wn`HL|uU>fG1p$gEx-b2m_H|LDw3m;%b`Iki7wne9l(2m~2pNqXq_k}}2zVk|FT9ai`@#U`=R*3?erchLI{&@7d-E)1N"
    "GA<n#>E+kODF$5{3r=BSbSfnzY(Bdi2MP>Ouk%S7+iYqB-0E#~L!^XPN<Y<Ah9h%G%<z_yIi6I(HW71~<+al;ojkNLZe=S_t"
    "7nH~RnK-#LK^VoZna(nMM<FAQY<Qnv(|q^o>5L$YvD%|0|3Bu@C4JYai`px(esgsK&T0Db<?$w++gldwf>mBtj;Z>eKUL&Fm"
    "Y09!cE#8<L%=yDjn*59x1Z*MEBxfdFADz*%vixlWTE>^ujU-cj=>WyEnuE1tBKp=~rf8L>hzo{uUdPW6*-l&E$Ii@55ULXO1"
    "d#{m};IWjmI>)TOEILksPv+f{g3dlP!DqY8i<Me^~sxL`k-XrJcehSt+&?@3C7;%_D^Y^~YVd`lqO$ceAr+l2Rpm~-g)GqO>"
    "BXSHcA?iC{z$?M9Q2)1!>*<nG3xoTaLpP7N$rE01FQ-%qY_xonQoeQd<pshyRN7~w^2>>8asdS~f!lfibX7*Q8_7Y!4Q5b@x"
    "K#AT1o)D%2xvfcWD+i6iywWQpCr(VPT@m=MeVYNqW64|&B_PRNou?y2i{paNRgC@CyO+|39AB|ykROFoSL|ZiOph45@w(@Ks"
    "w=-XsfHo!LKAohPWG!k4P_2p-`5%kz;GnM%jgFQ>G6bUR1?w7`+t**&Jx38CCwFU7hMPKx9^^-WPo%{AQ@m!*q$aEza+bMWb"
    "5(7`bJ&uw+o{vSnHPUFK-CBDc8vXgeO*afM|!cf)lJ^ks|niX#MLt^BK-@%D<?~;gMb1?i9nJ5O+U0;XRj2iiz>W*vV$#O^o"
    "m44HAA8!KkzipyNtK?042lJugX!hSI`qUsq45vLgchEIdA60RIBrnRqm|d8auYQfStw#2U7bu9JRTAF`4jDOB5|C00Hkew|#"
    "wcyx*UgjyP?j^f4;gG+_{<|pdt6tQ-|Zvf^wqFkY8bJ}S-AsiBnZlUy%nT;E9+M4Y$UyF$_cQXsrmVAocwj12VsWN6LULmb3"
    "CYiksb<-a%)84oq6?5@#mj5I;;r+$x@LuR}1^7F;qO5km`s4}P2>wBmTp6Bx{Lgt6E3cSkt3_XDgrXXW;2C=KNMjqXAmt)1D"
    "|ctT#HiQYT5Yi96BanCeJEtVZeC2^PRO4Mtv{~1o^Eg%UnP^R&kNZTKpyk_oHR#<4DA04AUn0)vRRkA)0TasU10`^$~0tvA6"
    "ct2k9YoiULYMn4U&wkE&uRWhBr~z1tl4cCY`R!NOTdHnnp+9=8U76qB9!f1@gDYOzT;rix?|Oq*lSvE&k}(8L<KDafTm^8*E"
    "@z6Jtzgv%90+-gv-uJ0G!GS3FK#S|v7w*4@<AeoG-Rs|O4X4chEK^vY~{W-!NY{Dnnuw7H(hu+g|upp@~E>?Vz|{H1YFJ*kZ"
    "$Q!doXi-_En?R@R4k$lyyjY6&uJ;pmMk*^m(01#^r*Y1_z{dS>NlB-_QXKvFBIr5#^-_JR?FM96yZ`7H?+C*?Xz#eXY5-5MM"
    "-q4Sh(!Nv=0Z8Hb*2d3)sJ07i#4)a)9d@EIbC~pj`*5>d=%~~XT@&aSHQ@OqwlAr?hS}Tq*E4}IYuuRw<FwlF#=-H|ijUrOd"
    "^{6%yLHbj1<Zi>8A1K&k2~XGn0?nqa^em5QG?^f<?p;qk?=>~MOLYfUI@#1hnjf>I)F9^cGD`tca=!@Nni3wu5zhYY$6uZKl"
    "IPH(xNQJPS9`l&3~_<JifJeb($%o*)RG+MqZjZ<7H96$6h)xt$sB6fBT9a3#)wA1YwYuHlP_v$&~m51QWa)cJ*+N^U71?uy="
    "*$_Es(-*1%ZWrc}sAx;+e9`9(6Bl~r%^roQ@(Cen`fW9FQi1dXHN4Wux;WV4WxwRfn|b!+o}vpMYj?F7Dt+Q+91*>AO;%{S$"
    "yN%cvgF26;YemGm%oPfMOX8}qbeOu;@OK@(Z#|&1_t3?ggeoyorBHSE~-#*-x$ZmqaD}HNvUg}lR8yA?*Dv2DCEh^%%HVUmC"
    "Vz09e<`}$peWMi?gfpx-%H!)@z4+Sy6+$al>_M?5fwRys@+Z6e6#Psj1W6@^J1kHuPx<=#VqER@@3goVFTLTEi4A}vzdhcdb"
    ">LMvFA(qCpa%+3jS6Zh@uTc|n<$qm!S_kmE$4}A*MKs)uUeX>#nx-gt(CyaQK-#m)PVNQco7!R)b#W_5nDtSY73Jv))wKR@d"
    "hW^IVh%)`<f-A9Q4DEOYUj-B>1%-W19YI>oY@h6?$#&d1XUZX!^kssOW>?0=4uj{+=E98?G__0u&#CN89gXmGkfQSna@cGwo"
    "w7WP|eUlbG5{2%8t$$-rn1{$pfxYFC(F;{z>PkJo-OMG)*gzAq2=pyDz^hwB4@+Xzeyy^#|vxbfKzL4CJ<HF#LWO>5U_VLup"
    "_pkkB0lR}*>T?b8#o{0++1@`@XF-qrEh>#&j0N?zC0R5F0#Ai(9;O_JDn-6;t=U`0><V62#{}1AZ>lnsS@b4)4o{<6H;9ZjG"
    "ufu_<=8L67$B5|Imlpc$)5FI9P;_x|F@|AlVaptED9efJh8>C%Vg#J_4!P)8^8HMi09!O4Pd5MyK+ndkelkv|qo>#`pU7wvp"
    "dB^d8|_J%mKDNY42@Om|Hp|gV@Ucpvo!}pVPOn=tUpu5Ctfo-XZm$erXLGj`s97Z+at|4R2ZDU{!cB@sOrYO>fXHCSDk2hVz"
    "8dX@nLtv`yhv7T1fmc6Br`gg|-!p4ZyzyBwAf_kGYPRh+DtF!$K8K2Mk3-T=^fsR$19>wb?>RCPOqlj4eY=4@SbVO;`Q@UL8"
    "JMZ4gLPg85nr6>`8KpyzQI6408E<xqTr%9@F8r=qeI;L_#_SD=>1{+!oj5k;j1nISnv_Y8jm!z51f`gCm!&glePpD?!{BvDY"
    "T;7F&W=2S|6w!6H)mmp4g_x$!F^jdA3T(BpA4H~p)>TYFpJ4vtaA6NK?*}^zndtQfWt!kVh8ZuL(km1a@#fl|w=J_VqHn};;"
    "wq@PB<s5lQ(Tiy0C2+EJsgZmgvyl{*-V9mv_pi`2X&;ta{yNi=nNLOjHRCLt{S-Fq_LGG}K^7vRO|y3GAtb<TtD+4iy0Q#eM"
    "=Gs?p|01NSs0tJ!@`B2+nS~p)PMLmQ!Xy%tWW3LH&@IuEQ4qTnz$o=C`a$ihNZ|wMtiS`U0)&@KiB%^hL<y)H939q?pp8hLN"
    "#Pt->=ua=6dG(6>G`_V#&~NjZ2UCXb9n-k2bgD!-tIGOHoVAC#r)}CTIkS75eXz0oL~Xlq<#{MXYmE%bA{TWV=+WU59-HSt^"
    "LKc-XXaC*rIhky%H3w2gdOW~nyvOb`EPhe!|rkySOTkZnJALD;}1!dyYMK0KXM@cb(3ZlD!Y>?Z_E$m(7z-Y)dfkZPm}*C+L"
    "e35(Oz5z?(BH}h4DT&4qh<aJNp)4UAo-?)N-Kpi)|<ZITB@ILbB={wA$sjY%_xef;tg3B{*zc3e@u!lO5^dPM1D#HaF=l|bC"
    "T|z*vyrRx4|5#J(yPA>3kwZ3#jxUqK-+!AUaG6LOfaqX^jvvg3XmZC($W3au12HevaeJ}2m4bTCotnPOC?(cVnJ)EVeYrf#e"
    "sDVbja1EY3+xeOd1m|%nyyb`I^pfTRsa6s)<dSbi!TSIE@x-5wdMzV#(7Rm#+jW;x$p#Bo#n?xYx6Ed2jtWp*6aETW_G9cFk"
    "gGTUhk&{^qVynZo|In2g3xmL<^-6ZFQ@geM<wExcjX1(J}_@L4N3H+~|b}3&J=QQzy2QLm3VyJ@EPSa!;1Bh(nloTB0uvpNW"
    "4n+RRl)@~i7}$zTLK%+-P$C$H<1!;X;04DLw|#5=`b=kE9|Ytd$*L@O0he|UOh4qn;(UU>cYc<yd-X$aeMoOxPnJ-WMJ_KGI"
    "6($dCN)jn>%+3m#);|MpDOGSV!cvac*+s&?G`$s2D710=Epq)b|MVsW6A?*rM2f=MnM6XQo!)~_EGVV_X#!dA*7pFJ&$(S_@"
    "g`F&7=oWM+fEoCE(^9<G7h3i3pE?!;c_OU`%Lx_TI{JO1+yc3c6Qa^$Vzl1L^64vkOxY2fUYmOyq*@l_XKx>8op6~<THc#4d"
    "}{Np#k89po^C1YCV#cWASmGC0;yur5e;E<l7B5LB)|R|bp%cN)MeX9HR04iN5qf|*ZjieiW3>2W+J)>Av&CpJ*={yczK;HEv"
    "u@kx;XxO{Gs=ieO6CTO>cYdsd&@CP(&$1Cm0i9Rr$V6wT-j<4odScmrv*nMC>~$y@bzNa8E;XA+N6i9TSXT*QMKa*Ze3rX9E"
    "Fr4hP6I^YjCvVtDnlkBRj1R{9vP3=^5++KcXgv*NibP0GRqcE9{lwpV{CXk7XUC+yMJxGwKkIcJ+MRTB9u6Kp40nv|>)Tasj"
    "x%XHQIZ1QSe9CYAqu<ein#HSIt2lvn0MbP*-n?h)4iB~jv?G;YNR2WSh7tbR>7)Z|^(|Fj*J`)pp9Gqjp2`_lC!T8YsW5Ede"
    "eJDvOV)ah%{Kcj6Lr(;a%%W-wD+|~5A{pYt$A|RW*q0zXuMi%(Fdmpg?KMzGw1l>aY`=&I{2sPTJsK^f2Tvm>svko85s5jRu"
    "rqo>9R6E7Mk&Qtr7RPK)QrEor}|jk-XGqeM@%GWHspTv`PmpXU$v7R>U{#;vKP8LXwx&V%)X7lAhh5*lT(R6BD%fCsq>Ov{("
    "?Wu^Cb2Le1N<6LYxmdGeTZ@nqvbIItUFZY#Ss2neBrIhK*V;1mATgNW=adAS(MAz%UhR(BVF$EHo!aAmlWYB4VbmL3}!4;Fp"
    "x7<UiyvUdYOV)2Uo6a%F-c!Jjr>kSSgYN_Hl^RX?@n)$@2cI}MQ<{)E>5>yOh$O{xp-Zt+48s%OGrTIXzlKvJWgUR#t%0^*y"
    ">l?~4eRRUOY(gtzp$PW=@Wr*r2xD9J(mrg7aaP3D*vnrg({!)>ixI}&sIUrhl@(__gA<!SWe|26Uc!FSBCxLiwabXI-1naG7"
    "8VrTDGp}vrkA?q!^#Z2;h^}Ad>tP*JcT|5(dV#+maV4QOyWvIDi^p_7hYrK`W7edY>hwKVVorqBA4vs^F~bbO7_cq6$4Z8=Q"
    "V$f<KZ~9qO;g-i!EhZU1*|5I{Mg!8sRug_4*CvsJZBUZ`WFlg3H7tWWgRCdD0Ukg3{g5#>sBI`KsVt&m(wXflIbRAt1$dHwC"
    "#B7LL(JCZt6I_H!$bRxp|@T*n?MOO~ZgRF9o=O!PfQRL`0+D1k&)=O31A<_7LF1ApBp}vFB6`mI{W~n>8i=jndpBof4(dKPA"
    "Y*@N_swCH@Y8$ls1;vUM~JB=`vd?uu-HpA|90fJC53&Rt;u6hsCEn`qt_s0J}V>E55E=Gzd*JDrRv*LDH!75v~r0rw#M5MWc"
    "}n#Fy>K9|ov*nwEZUFGnSXwpJ!iAugYRIgH}fMDBXVKQ$VH7#Qdu!PXNl4tWE@Z~O$_~|Y(eBhl|bf@mdq1*Y|jZp?%w>UVg"
    "jUya)ZE$FY+|No#ij03izN1^|)3`9GQxs!~W1@pN1`iiN3=vO*I*0Xrp3r{n7bQW|QVEpd*1cXjzfB_)xz=xjCY@Y$8K0Jw4"
    "s>|QMs0+!8neb?sy5O5Qb^*;J@Ok!ZmyJTg9*JJS|Z{sApU_Ln|J5)WD=>5&o%yQmFN}&_8*KAW~9-`xIC<+A?bvXY*%I4AZ"
    "u=c;PqdXAM%3zu&DkHejwF<c)T)_>zg=;DT$#992(cz2W)~%*-(4b07lPk;3(@DX#gBd2v4kPl3FXNFI!^-o~r2<7;?5osll"
    "=6YgRrSFwrBQ?oAS|$Mp7X{;NVASL@rJ1G=h{)P323BtElW&5LMIGAyev979k1VS##`QYPb0=3-y<nkU-(!3;HN3PA{uqH2{"
    "#yoXs=IG)0I{`A%MJ$6x0RHkHP++TTy1>A`1a~(M0m0sdbT<Ti{-3I~1d1#!w_aD{4k4!AvXnePRFXTk;$o-K)wCTuBinY<D"
    "i^&47H+>HLYxKv;ewfsnC$4^TrScCibY_K5v<76y_>yyNW?x&91BK6Te#zM6qo~X<<{M>+{{x^atus(-AC36#_*ue5>X-V6B"
    "ZmJ@j#-Wf^wQcA7)`lW=Lsx?>qg>8agQ{`H{Dd`cMbITt=-E)ED%DJi8;Z|ugZ^PvQ#4(&gDoa6Y(NpVG%b?)Tj~FR&IT7-+"
    "~wXR)@c^`la!s4Vm0#E5O-7r97HQr@Uo41Hz+!r|wfQQku}QKvagZV7JET?dw8b`9;LkI%{bEAUP9&cBPN(?>|dToZcyL`R~"
    "SAkh?UhI?LSlDN=lbcdwD}D!@^3r?nswL>NK^;hn2HE3V_h^oD60=_UVQ4UGeb3YFp2QTJDqC&KxTo&=uH>cY!+786)~xL$D"
    "dTb$I7$}O*%yHQfdwU+6rV<wOFFrSm3z4~SxGC1(VG<U%_vDhPrO&(gYTWBYa0h(WuNk>p{(Q=2q61EGorKM60vS$)01h^1F"
    "0{F~>5(-3|2Db}#wtBiKr&%5y(}}cM{**TJ_e{Mb1a)i^$-@^~(=Sk1NnIH24hz>$QzaW2VP`qm^AR$d{kw!bkmd(g2<NeR7"
    "CK+yr>vz)^!<iY7(gp(DlN~wa95WxLh_swJ|@*Z4k5r)h|ILpd7=R}pL;M4NV6))V_l-1)?w}MX=F(@a$oKAce$vXG#~DK*P"
    "txoQwc#Du3gm)Yj+WKSDl6E=+)s0mp_@K+q(f2?{_TlR&N@KF>cjgw~g0n1UE8K@O=Dou#o#@q0w-Wowj(&d>pj5icRqxvKa"
    "D;TmU2BKawt~t~{(ylDsf|t`E;bDzjZh_PIWM+QTh3ei$qASQT9#1dSH+@3LGw=1U`9@tLf=_nfaJevH)oU#9DE4&)cEo{;d"
    "aCNDh!-1Wlb{j7X`!fNy!+#EvK5~O+WDqZ0QeBL+{2Ijpt00{(H9oMxSpRl;b_kw>zT&Ez^VX&gC-R+-XM3u>zJ;(6D5*_3>"
    "Jh$EH$*iuMs)gg)VEqfxt=?vANQvXHkIf3EZSQdg`WLH502inWKZGaq%CDC-)Nf}lVa}IHe;}g>R|$a$+gYdQ7m244-PG|(9"
    "uzs^FS|Ji*4Lj8IYi@UYmBIX#xyB&P{#`#pDKpx_iBFPEXJ*k+(4l=5a~xN<ree$<Sth~tLN{Ne2-|HEp7$UekTU@7TrfyW*"
    "hiTes(csI~vkU%;+5y_W<rw=%uyc#dAPdPWg5n?$)zEuIQZhH(vHhwuvoaNFF4V$$7+&5eT;y5-)QX81DO(mdZ3J`|KPT<bG"
    ">-QhxjcMSJPayp_Rf=FA=(ikNiAScT#zG-$OsduOrAA0+li`xv<IRH%LqZz;{A5H;ENHf4|$n5~5RIoOCY{%Cx(tQxL<{8!f"
    "p3_h1<JZmlg&LIgxmMK-Ml|J%U23bgWqIXAj9Y+I6;45zwj?`Toj#YlDFHPaMB|lqxv?3I|C4A-kTW@CgF*EeO<wqLck1F<j"
    "FM%zr4Sz>WzALms!-LS!FP4Wu_E<*RHD$HaABFR3Qv=_S(l~@B@%H&Cy8kT3kKW9>^2KeT<cV$0MjqKGF4JHr+Or1Y-*4hDp"
    "?Oe#6le|5_qAl$wX3;MhUCxeMrmITdk7P1_Fj$`7df_uy|~_1rX;voEb)aOtn^e2a%dtO!kgmF>BFUa`&5}@E<NO4muJLZHw"
    "7Tv<LV*sLzV^fbu&~x?MCltu~{wt-j(63I0~1k6Aw5KHiBgSQN|-%v4M~0&ejxp9R^O=x3~A=YhE5%7yG-@G$z%^E*x+u#f1"
    "0PJk(Ek)NT7aWOD-%Skf3K2cfN{G7D~xC%c&)x!wXq4ovM2@Rofu{5vR=t=CiU$T=nj$76|9V)YuRIGF7WVGhJfdkE%WK38p"
    "Xb%H|m%ZsVNc;94(>nXWM@v@$Qp9huH^ob2s_|G61WPBt-SQeZ=(XDc6v-QA$T8wznimkWLQ@(B$pJMj9D|=T3^Qj(w%L1m7"
    "Y||d%%~$7q4>x8At#?7YwYMMm8^zJ$T_|b>Xq2Sh{}@NrXg>nrFWpz%eNZjfyJbNL06f&wlEY9o2g~3U>EK`Y_hrCh<<V$I+"
    "8?-*F9z56ldNO7J$eBAgBtWqtmeDu(o;f4(2gj~Y)zbuSgoEU_Rdid!nES}2kR-Pk4o84+NpGR@`%_HJxvz5eA^oIk$U7`;|"
    "kvt?c=m2qrU)?;V%}}s)oCN(82GHc<cgjcG}+~tfb4qi&;GPe@zLVlu>PeL+AbHP9P3TL;;EN#QnY_l{@23zcp=PK{dNO4SH"
    "gOj_6>2S7JP3&#7x9AWdetDIH&*DOW=XJ2`xJCcU#HBA8l*cxDCe8gZQ0#XAUQ@^QLwSG~?&qd54(Wz+pt%?<TR3j09zjLYy"
    "-6^P%p2UtU+PAKPB%Sbv}_<tKSREI+R1HjYmR8UT9mA=1qzi7Sw-RCNSV7*2h`m<-J1}l7ETT$ET@Z(50{j?=`CgBG{N_4%V"
    "IUHtvtJik~j=_d=a$y<h5j-Z@MMwBdfUnm(q>lq9T<aYP>FlTeN&gkk>oAbK4)jrw8kFSDC&vmHsxQ&?h@#Ui{Q|EF$K1&<<"
    "z-~<(L+{=U-aE;=3QqHLvas4(_GVarZy&%t*D0NZYnAY$sn_~=18rR;KbbTUD@bhy20sr<u^v4HKv1|S<pb47oX{S=ppzVO-"
    "o0a{hs94BSr+Azyc;~c<Men*t{WmqY+k4oUA;50b6}ewsWDzF>R+FhY&Ayk3$a{&w}JEDo2j+ux;&MbcQMxbV<f@M=3Q1P0`"
    "p-m?on?mmO<XZm)VA@l;HRggWh^(desox<`5LA4i$cM_9)ewl&$yzIzgOYiSRSnnfFn?Ay0)7Z5Hz6BwP&)J}n${d$lTYnVa"
    "6jP}%#i>Szb=CPs`2T>(m_PKHdGV{Pummo16$p-W-#w^^8P0gXzfCAxJu~&jmX&{mQ!aqPa!XYj6scZ@I<@c3U*fBjP=GFJZ"
    "Y=oO*4(pp67<=~Q%xCZMkW7K0>f6_1m|o>lmW!uGXHJg`t_k@$H$VVLqfq{9u5?4muz+?HFWmr-zJxez1(T`r^?m*AaTjgEX"
    ")g?zI&QpwIOlZJGx>F57pIYjsnI(z5rz>EQRB=_AhXyKI<e)y&4BnsJH)pBL=`91ghk<(P-EJ(I0dIXS!|EI7?T)eUR8CHkM"
    "}aEiuvP?31(6W+_pGGOH>Y)EDqMmfB~SWKbqm2t^(lz{lwA-^S{dw?XuH{oknLzS|Mk-lAv<Q97uyF_WpbTBo-^|YN5zGYa<"
    "Psqn))6waY$A_qlcfQ<sl;`SjnUJ}i>X;)Z-1rtJrlVT9oCe%-|1*ju&%z9kKNvSjxwxJYZZ9+H6~KR;)js8FWCOY*wjPg*w"
    "n#=<Eu)-%*_epEZEp}gA23q`&@!$NP*Ee%JbVr-i89bk05Fmgo;CB*R#=NgloaAo1u4A4lOfcO7lqo;B8o@CO|`3=etrbnE#"
    "`cvH)pqkGX7~!4dAyXJ-kSP?h>q9DWCThM8#|!5zT*$+zbW4ANTzD$T%^Ci?9-*#cUy2XeIs}0e5ON~a+yjBmj8*0P-GSq5B"
    "z7)oX81QTOkNd-iS^O@wCRm|&g!5Sb?A*Q2A(JL>nOX~)x;~)$zweipr1A2HvX9Beu45gXz-QdLd&xM8b&@YK{K6>i~f1GI;"
    "iSeAzGh69zc)HFZn&!u|A05y=dtSalxKdA--2!>22g2ks$2|0XiK_C^0pM;Hh#I;1O1U94-^V19bV%WbNSLs?~P70Wv5CQul"
    "6Z%blm6brltj1KG*EltHzs|57day6uMF(m#rRlpySeD9OX)OZrx@&52m<A!p)y>o)M0@Z$IKRKeDbxl<!J62R^Xx@{XYIorw"
    "XD#7I|YZ~O8OsXXzvn_&iVJOb_t|oJgy!=V{0a=btpPb7AtRcQB|I^C+iQE&ekF^hk!idHf{#**?C5{C#+-})F^}kDW#{7zB"
    "nD9I~<;)UB9F`~XC0!Ag;H|`uXzzQXLGJl65}ScRI#`gcqQbE8@eK`AWJ#9mw4Pw=;_w(w^($L<Z1c@Lyyi**aS{W5jsfh5G"
    "XJlW<DUst2gQCSG%{6%r3}!`?~RStEd3q0f4?WoKoF8z+Qt44Ac=}M$1QwM$#c44dpAl4*8?s6PlwIJ#{Qwz1l6xGv8Fz$81"
    "4f;3!vI2qQpbTkr-5mWBLzOaddaX7V6{S{pGp|H7Qkp%OMAt`o*%?NBGU`6jPs<^LK>Z7c$MGCrmXUr9|ZkWOybC!KD<G&I#"
    "&$5iz+|Um|{getfZ#&pOJtA)fNhjZdeb?3@BMD>95L`XUzJE{+3P{%;u5%d38INFt*g4CM|p#fJu#BR4E&>St|-Qh+8ns7Yv"
    "-e%n>X6XJHm)+h*zZ|JlA2`Tu8l<FBHTj~d8LNxE`CvNLZ3c3J}OcqYsrc&TJ4!=B;!|YHo4f`KHc?6)QXP!DM=ZauZ%K)Xo"
    "Ev8L?a=NR{$?U=EssnUgeaIlR5?&#w&lzewS+=;q^m=l=+cLz^cS$!!FM;%i<E)+v>4?iKfL7=wAM-6+b!7R$4@$UNT7&YQ9"
    "THZ;*{bHws+<IH%=>=s3K)nP^eIhcEWAj>(xf`X%l!iBRnrye#(mmS$c-{$B3yOV@=35&eSzrxtisn)C%%)qL$^rm-y?{Lfu"
    "YN3rbcGs0lwGJR#?DH|Co5*8|WX?bT67`Zg9dv-W=Ll_z@S6e9(8@wn9kx7f&Vo#FF&Ws8nUGnYdXelD9F>eDT6ty7ZyJ$B="
    "@vn!Vlamm+JDT16L_{}0b-UbV}SxLe6$dmKrEm6Bv`Rj|mAk`{*H&o>IuJU;1{Nv*3_01xdPZ8%AMoQRP0F!lLT)KE3^SBND"
    "kIAPVkqL>)^-&2hr$)dyYnz(|tmmK!HCu|$jX>b9*{dU5HJ`FZh_UkufC{2m^(@{Ym;4?nydEz%l$uoMkiKuI-kIk4fVo122"
    "7Q&e<X8=_j^xa|e0baWO%xl7m^l~Bupy$3&Uc8YxFU3u2Y#Q=}!S9leIP2eThx7H}r=x0Kb#F+y*gO2}#9RXn9`b`j3X_w&4"
    "#9{F{=trhdHL3f7EIwb52~I*Wfm!z?v)U+gvEDebEv!kHZGim+8uDA7{M|ax}xjn=+x=7f{ITe$v&6!z{l@STw9xY2hZxLm_"
    "`{tFTY{UPYlK8r~8InP+Lq^^j@eoJUK=pzT7CQ0pQFpu2*+TSKYTIR`NdLLJ`l<vw3EWI6o0hs*U?XHmc1&AGwR4jDN&Vi_J"
    "S1@DGw9m{<`Te7o-i&iG{Y?NQ=1qtyNZq66HyZXQ>dA}=EU>Mdx<&#5oAZ1AIBPJMNux0&r7zu%O2#ONG?$FZd76*+KX{!f^"
    "}0($02OT51POD}Wf#U?JM9OKl<JJro&=>fwAa}40zX>KFta2dJ(j7RjZT?i1BulIyxM`oVqe#91Pa$KPw1#++8uc0}-iWTLF"
    "`JcilG|InH*SJl&6C7uu3qqEpX`Ek3D{33fXRNhKrc{&J_&gA+$hM-`kwDgskycLb_b;PdTaJGsfT&DHA~?8J19o^U+l}?Nb"
    "Z*SDj5^JCPC>%->k}*!f`oaUZKe@#baT;YBmD(t$@LtaVSZC-_6XxRdbnSvZu!A|i@c03(BPk+JI<|s?b(SXT#T@_Y7PE0=w"
    "{mx5x`Wz;PUxNTy5}puuAGZu`JRJ#={FSoU~=5G0D@?)t()kM1JK2V98=3bG3+%@|PERl8a2jk}!mxq^=@qRTYk*+6}m85DB"
    "#YMA3HN4ygG~-cL;DI6UWs^l2Y(Xs;8MaUQumw67ZfFfo5khkBFY1>}FD!oHC~1eZ&#p4r3)wQNjT?ZO^7*Qx53p+_BuvtXr"
    "sp*ts{mW9f^(mb+Bs3CI^`7^;?beEUsHCG8ROZx3=-hA~qj?>ZYPK-Y4=Mj6j@R<t>P^=NYX>4D?9N(cQNZVHWw`fuUlb<3I"
    "1Fj&2e`}@e`lRkW4boflEJW@-Qj<G83HKt(><b*OtU`3?yL{p)1B?QF1sz#3Weuy!KxZee&*5h`j&_BxeH8Q&WF6}&E<>DWy"
    "dqMOdmZ|laO6t;wb^^l@U%pTpn->ai|Sqv*7E6vko67LcQqcCQ%k0MAQhKN`L1%WOFT=Bt>9Vf#jdMBK?o;yF(*oTo#~v4eA"
    "q$<rfnf76G9HUrBG*>xe~T(=KktwgNdBbZ-=Y=GbV3Pz%Z+91kZhf8j)SL)<8i8;=z`%@`>-<hgPskm1d6}pG2Wc1B|YdUT7"
    "}_>y@d|^3^5CJ8@iOnrRf?V;PbeBUiI-YLx!<?~MCvG-s%cn{QeU26BCj`|NAJ$MhU>wpJNXop%HV(uSqS`3o8jz8;<puLSU"
    "YFE;;|^{d1v!3&QTTD9v01S{)Cv;*KygH;vPWT@Bqxtjou(yc!FW>#o5z!^&OkDD>X=uDs)<J!L4b?-Bx;C_>XRXg$ss-e5z"
    "-WdI7nZxn78snSdAHv?-SuuBX@y3)_1lTg$X^RpJ8ngSa484LIz;i!C%ije1D%+vScLRUW*VF8)DY*8}Y38U_Fc%J1NSh$ZD"
    "{a+h!M?u)9$r<sk{)HPUrNLSQE>*3XFvVGSABN&P+GjAEf;EBG18e7-r%hG7O_42NaT-(ZcdJfC?awozQm~Y97Jr=ijZaN*x"
    "kp~ZnzB^!G{z~4~TnK&n({9xNhDuU#thS?H;Hhxh}rHTdDRsenQ<r`yIjgVl{!nx47E7r0sFy@~rjkQ*W0&6n@D4$h$fH#kx"
    "q`E!1-nTnv37(2Xhe&C_)g(vO>Ys<WN{OuHXSc=a%wBQ|Jv4d@#B7xYKv$bz$b*bnipB2SC2$jCr|ZnbXZzt05Oifm)JySZg"
    "v9L;wdWyIc@&tyrkK1LT*q$Q8`T^Bn+SrU5BB|P$*u?ymt1PtKkOP>?plc=oQimGk$Fr)Wlji|hw=QCj=;XQ~bHd0ydjIa)J"
    "1h_lu#UEc;?7L64eGOXtHf=~?AT7@y?>pH^59G^?@*<SKgwlGT?R;&oTlE}Z9V0cnL^k{sAalj+$)Y8x&o2*BS~dL?NNnp+Z"
    "HPORQDzd6pW^iej}MZtJ=r%>6>$*gi{mr}wrmqc_k}YgkdQ#t9t(ZhHUO1tBLgIH>Ars{v0$qgMzsZQjpL&RIIWk}Gc`wBSG"
    "C)I51;fT(f-g8PeL5ksqfqUyK{AD#78Xzzwiuj$qgX(7vd)^xvniO8{nt+*Jpv1+OfJ?rucJYam|0pAO*C@gVu$>AS8BFpQ7"
    "2Gc8!#)=5Yc5-eaO<naiHT$>CdlOOa+zGarerx}fcy%n?Ux0a8C}!8S4=1Xve`vbF=I;YtLuu)uBob44~U7EfuYoAzFU=>I2"
    "<mlZ;`(r~L@OWwaR7eTLW!3h*s`^$zUPO7^QHRS#~Zv3d}2|6-I7plQYPW6#V#snoy?9un&;fT4Oa31QKnJdK`DE?x$z|~uu"
    "*Dg=lw{57yhq1jBApVd0GKrE8%933aC#2K|;)(?*UCIbL(VqOo4|^WAol;wUZYL=;8id_V<VmIT?$TQB$PxUd5{zyo)gf@zB"
    "lpT<$pFxB7va$5#`Ccow^7Wx3@}R3!`;bcYdh~yzB*{;VFEbxXP#JCqT8ojEXQk2xjM1Lnyk+3bITx^V<PhHZVSj>T|Qs`EX"
    "bIC)X%N>xwYeTfi3?VmNbr~z;v~Qfk^xx<W#gDC-R#Tb9w?s$~|Va6Xq%3?pr0tO0x%HOLl+l^d$y@H#G&2S4CYRBH_N?&sZ"
    "x}S-75PE8uWDq!jagE8Xg9&r$7dMjB>)zW%7S0yNIrF0M4j5Ldm^I*7ZWjeND#hq1>meCMZaXe_Nb@58oYYYSRGkZ136Z^@#"
    "$NKJp2tJ3ssmaG>x<2r6?%mdkQoGC5;$P}2md?`*8`vG$VAN~?RD!6K~Gc>^<xJL%D#zlU)i51c<;GN}B*%DcNpvQ0XP8F@q"
    "v%b6?meo(94@ZVmOuk-y9`0@OS-gG!k9`W;J_Gz=-|6wI-G8|(kf<WQ6h#d&Ab&U^?9R@m>~*B%(L*q%e=y7m{S+{8DN))>!"
    "(gg|dn28<2f5j~)ay0fn{g1mi!jLh-gvsZ{yo1(9uTsO6Y!71$Eqx_nY0xa$6{BuGt^?Kt)bXFxD8y3zY!+F(zeM?PU&ITI)"
    "-NVqwM3)z{Hl12H;sH<CSVB$KK^m92IN$M=W{1C?k2CP;eW`*62FTMyCgX?|K@Pb4rliWm@sz@8W|wt77VG^$yV#mpk3kdcJ"
    "fKKpIrnf^EU7#pQ!78*)9`5<3*pr(H~PzYkOkZk8Y49xT+t_VVwjx$BN9_P0$MS^tA%nn)P=PZz)OUCxzijdZAig7{@UAK6c"
    "}`Yh3rOMJ@tyjpH21`$sHPfuq@wGyB-zAd!r#Ntz+A7miZO*>yhaF81>bVGL^T}rAiAOP1~?p!p{Vc!?lj2f8Xd#qYHVjg|E"
    "rNZ#^H^wmIUcQM6N_g-?0oBhusm<8`tB#Dj7nTVmGxU*g-kxU5?CBOs3d^?JsRV?J(ERhI|8=Be%?-#_ZM!&TY&TeiU9qZ9n"
    "on3<tLBei9k#B-c9SiXUCR+*gT&LY`;*a5?O{I=co*ZVtwpj!lICENJj9}=_}I)=9^FiQSdFzOwhsytKeKepvaElFoSCgt^+"
    "faBGv0KF?<SAoX%(6_v*Pdq?m6*SFzEzKd+I6u>urL@&h<WZNB_U=$<9+8?alRaxIo~8kP0of7=n<2<xWnPy}fjjgK1%CK@-"
    "OFDF{<d=kf6rX(j5$m4@=8AoAmv>C_eyk@4v8zpm??wfYu4VB$rNW_H^$Nbx9sB&X26`*KHR)WxeqWjN}BpS%mLWF7B`aZI;"
    "TpGM<)=9r+PhAmKhZ_0|U;T52!NvAWHH5}mRH|Z|t)zB(RiXH+?4PUw!i3X;62e?!|pQn-P>tqZoCCyG3eK+C%i?7#x&#o?R"
    "pKIXq`q=ZJf>HGcuuVk((E5dNI=H$bLjb@kLl}Y(g(2|yS^QqMN0lCl2ty#L$=kiqXR<j@U#~Hb*kaHI{$2PR%-u`uaroh%!"
    "-!lzj~!D==B(S{;(*GMlkuaPcH0d*dfC0913(SzrSZlUBF1WvAN^w?LwWLEPYg&y4On*rP=!9!oJ&cE{_Mj+>{7H37E_V(Dq"
    "8OuALs32(p%doTJUMF&dkZ_R_~N%-j&*C$W}=k`j+%#upR<!Wvki7zbXERzLXK$lA7qlWuNI?+!*o5$9VDala}8g%mA#&>;#"
    "Sk&25N_4-p{Ou4E8p*3Y)2$Z-DSaZ|Czx}~x=!t~dR2QRC+hhZdl6dIYJLj^NuvFJFlG-wNfqXkXT?n@X<QJB<v;yoz;mt;@"
    "Pii4|DT7~WH`%#e7F@oh&Hp}^gKQJ{gurb%CtL(~ZSYem2I0#O|)85OUVB1_E+43tISVX8ZE7LU^XQ74>%zHr+u`6;UPiFPW"
    "<OHhI_&GP}Rm0(J%&0RZF(Q343Kwo2;{bs#jXeffm}YCFT^m-r)#;2a^Nb=7BU;MCRm%LO8;Td(IJ3B<IxUdwGydlY*i<fS{"
    "tM2zRm^`bg`>3zlLaKUM{Tj1T?qYFHI1Rv;+^*$(t!9Vd;t8AH277-tJ)1>`3M|c0hKAGoxzd=4tB*H&^J^u8_hPKfl*4+Tp"
    "g})DOsk)2(NQWhu&XCVmtE~X;6sD(l%_0I+etQ_@Rg^YQR(8xmy%8{mH>myaR`yATZu~!HI7sU$;UuZ2y_kK%!$&bq|@m+ja"
    "6Ttzvb1OY^k2+DfXM;}DO;kYM94ltKPdRf$;BP_Fm>`Jnr2g6o?zjX7L*#l?T}Gnd711)OzV3)rl(ER56sVlvQ2+K6s1dR{H"
    "H0U!467(IGMt1hSu9REf^^N}&l#Fg8nNenA`;kGg-v)YP~CZho+TCvi7NRd-tlD;=2imk?hUY>q~4BQA~-KxKB*w*OA08^n5"
    "6sGV)wBYKczdM0zZy5A7GKN*o=!v6tq@)H9ONvzCN%HbH{@qm-sQks^EOw|o;SDK>qlUGbBaPJQT*|kpNbwK93Q=c$Kd-n)#"
    "Rr$pZ8)?cY#%y{3xjFpWTAwnEE=)(+O3~jOpBlsVK&^4DSU>ibFbg3ube`F3;s6aB|T-^QAu1r*Gu2{YZV8TR|D_-7_9e#r!"
    "at7rR*0M5q9?@V1<o)te{J{HozZ>kH7cToIZtF5!dw;=enG2Fh4!!a_i&cnWeFQpEM_GW%DKnu}}@jQL87$G*LUqyMvv}qtU"
    "od!D97*t+T3V8Tozbdy46SNn*VL88cH1Fyf&OX@q|;%zjUTbdK5XE;>*vnZQc}l8gb(YffiSp&EPIHWP@U{<&P3|Ej4TH97c"
    "3;9k%dw)cd3&eWPi3_@I!PCD;Y@z~%O9Yd)h5_vK0ufHpAzxK>z2|d{=ReWu+Xs!C>DqEvLLQQmg-ASdj2^Ea#l9tM-VF-e@"
    "C`@IBd|cLrin-PRYWutkBi@?p^kW{~%ckobJiIwR6O4<QjiZ8bR?iHceO37#jo&h$^DzfqfBvuBUeKhh#(X8_KNgSd2PPIAP"
    "-W|{7Jhm*75riNQ7%sOkw$jn`GuZQ>X9z)&ht+=g;MbXsHx8c3|6lWjNwqfdO3IR(OVYS-Q=l?Q27n21fj<;B6QTa!hG6;yA"
    "@1-v@z&tTrlOensmd=vIelN+t#Th5tr4O*x$~Bq{GY|;rswI=99`Qh)BQVhb#lsV9an8=$o#@Xk*CeG#rvtdLSKBg9CZK12c"
    "NWf*49UvN&IlHg4Y@cMb0p??S~g#~h#Ti#TmP28b~Ju3VjPt%@6B5kM2IyRxNAbZbLaC63H8&DU-}b*V3X#baK=fvbUhO}Rz"
    "eF@O{2xO_nsa>6&oR$)J(ZVJvxH|Uv-P$_xlg4D>9IC)QwD%(BsoJhdrvB9CqDhu~?yvcC4nivdW1IVgF7B(d0*+qGMrLub2"
    "#R<8Ln-Ez#7v|%lPG|Eoi!)Z<va&^LZX^VY6^F+(GWc1ZX}8a;o&A_68Z_ar*Y3xXQOk5iyppP!hJy}&ikq&^Is|HkJ_XcP{"
    "m_uAJe5pSXQu7(Buu$xoO?iXyGi}WI@Y%B9|%kx2eL5iMen#wXz|zU_GA6V$*e=9lR=_3$@^36nny{VrA)X`S!5-=d#u2JEF"
    "<rX<H5>#eCi7Lqs}>|t@Ot13b0NePe!*6?iU_R0DqsLldND6UQE8aMPz4p_o|#7sNQrU6KwEuZ$=~RKa=vgSW>zl9gf*;87o"
    "*uRlK3E|2HG9KA{LZuU_*5)emE}XwF-xLVnSs;2J-Edo4_QFrM>c?m^xvp3d2u%)gMF*q>bl&EUAnx$<MR6HEA#IM-DwL5!&"
    "cPlIZs<$KJboLm96rsna}N-ewDp`t&`a2?!$=F2jA-0hG2FHiy#u1w+8VCL85f8re~DQx^ByY&66ry+2tA;6}v^Z<d-!;}+{"
    "Yi&eva@qGUH{U57Q<b?gTQ=BLlN3;e3dD+GEoEP3?%x#bjNn(NBvc5H+XVwI6p8vOk^?-3Y<p24vEK0d8W6BuyXA%HITAzLP"
    "0(TlwV@DuF0*+8H_z0k_#P|ugglVzS2Z8<|1HYzC>&~o`uixpatr9%zG(UtWEI1(#r&uhiU1^Bgjn3-MTJ`C@B*G+gdKy2!r"
    "__i@!FyD{q?H_u{mYcV=RjO3Ux@U{s9DJc6|1CpvFyJGZr9K5A}uhaH)#m=a;6hhsrXQC$Vi_cXlB4`Py?=!Rw1hmS4I{5(|"
    "VYohfNS6~7a}Rcy}ojKM{B+uDdSeZwF6t$rVxIS>K$fTg@oojh+N;P<oYjAe=*Q|TKE`4y*Ff=W~dI9n-9g9AJAOFI3aAatf"
    "Ce?jNulNo11N)?N&_}6HKsB=m?8=~<6>S%T{zJ8Oepp}~;z_NnZd>hI9I;bX`9YhYbw(I6lrY>ByvqhPba+QL|vYoY#*;dKk"
    "?t@KW%3U(1TkbPf6`22y<`B`ccB2%JYxxUS2GggYFdnje8*ZKs=Jo9W5XSr@hKun=z{|5Um>&(>rcvsE9z+096>tB=LFpMR+"
    "8iD;r*YM^!N0X0x^C`CTcl9BxMb7u%L7+PHv>kO{0Jf%Ezyt&CA7qg5_b$`Q0=IlzEq}U1S6gj&d=3eu}I9X-u@cRhp4;T5r"
    "WL-03vg@HUXH5(i;fZ&$>FdL5CKGn5|{89sUGKsztZ!Q5=M&PRd@R^ykKJ#E>ff_}xK_N^dD0I2BDixUfxye)<IJ<Ec5NJPJ"
    "ebs-ygIbNN|9Ez(~ugO1Df&F^QSHDI;T{AlVq+zS=jMUAAMNA_WG8QnRU$b3QD#6H#b#D|x!YgJ@YA<I%e=9coEmQ5kt6U_N"
    "EHkAMcp}$hvxeniCZMZ+;Q2}fL$AVZ;mG93LyXu%$Yr9z0W&>QqJmkZulX1r6&+Jd0s;uPG>i)P-?frIE!5<$oS)w)0w0;}W"
    "L?4BNp(TqYYW&q)fx~!=-)-=wE+qFLAutq;v6008Mb9h~-64qEINW`^vB>;0TT1f9xee!EK&Ehm?vksTq!*X@mfa`ie^jY{v"
    "4=n`=l_p!zJRU_@l9W9V;J@nw$097t{QHzNmZD3|EPUpf=3@wxNzFtq`kScJbJ+<rAZIC(?_dkh#0WVRsi`1HwY2yW%DD0Ak"
    "Ko^FPbb@%zL;%vM@U%1EF$5D187?CIt>!bi3m+FB-r-mTaiT{Q9;}{W|@G1nxmBu498EHq#fuxvI0o`#3tns7zC~gX0zGD6^"
    "J5)xPpsX{M?4$6S~=U2tQFNTtO)-psIq1-s2d#I7ChX{KK&V!j#7q?Jzji~WEGOFD@o?Q}MCLxJ4R&%&(78RBvV8Ic%4=Y9O"
    "yN?9{DuWbUQjYNnLN%ruS+lJ8Zn9(+lTd~`A^dRZpLS*=0#kFbV4DDSSXFwwp+2twoZdAF7@UA|f;(d~JY-suZn6aNV6xvEj"
    "L|(}i;8XETo~@HLgmsHUjOWgbdnD<fUvu{wP4R`{RqA8Zf>tCIHBC$+MA-x4`5xhsKFg5x<c-Np^ek4g0~hJLxOYjjXQG}2*"
    "`=I~X%HoFL@7SAp}6jQU%FlnbbE;@9z;M#UlI}yIqh{3Uss?TlirRQrW0$eC88x_w>vgiqgcN8l)>gzp`Yt`<6q)Wg7^@JnH"
    "MQV-j=8Jqq4}_yT$T}Zh{5A1>~@vpQo%szfy0ihrI-BgEprj`M)$mT|@G}ZnVN(|NpO1=q>*&625_a4<G6t781Syvh1t^XSz"
    "(Aww0^mXp}D1l`C$+>6%fIia@M)QV%;wNt>(LCxvV|J#A{g<h$v=G94%H?e<m)B!$TR)}-0i-;nF;6AX_5trXeHM>`hzeze%"
    "-AoIK+E#N5~zFhi^D7l#yjihK=d>k)_TzWnNaEX>j9&J4g%J3+#6b((hkWIZK`F}K=1ACoa(}wqsZ5xfvCTXl4+qN33vC-JJ"
    ")!0sUY};ys#%%bt&wG47Va>hfn)8}j_dptLy)+sU0mjBUc~Mo;UH$bZzQng=uj`xh@iv7HQtcf?>X0ai>^{!q4fHm~nVi&o0"
    "WALcGe`ueL|Dek)xFsJ70bN)*X?TA|0$QzjVk)-+PQd#m&%HT>2PdDkfT<Fv8JM3EYu524Dfn6naP-hd7i-l7xyh(!xtSfrB"
    "73|Hl009q{w=-wgQ&CjegC)o%2F_;|S^K^t;$Bc)YzrB-hTK(@7~BD<8%;R&W`nLzhHTX7wapsPT~LXC>UnGkZ6NFuPc-0pD"
    "ACLi`)(124Mync4sMum{fqw_Qb`aeYv|?)pj;UXfnIDMxj%Yy9L`BlmQS&PEQ?AQSEMyE45E=QNywONgvDa-wMPS9~xfuFi("
    "CqY^uyNh;-CVx>9}GT-4fj!*F?jrq4bt8N^nG{GBaL>E<FpQ07;WsX2p@7>LD_4dpRt%YGyR=dWVNlmEc;!nqt(SZl3@j9iD"
    "P&)b?=@!u#Bw=FWi>lX!Cr}G($@iq41&V|&$GI`0bnj6hE1A{mrHfGfD_T#n)T=_e>xcTp$hS9U!F8>E|I-|Zjz{3l@97xSg"
    "|a0@EvBww?x-@HGRN`hfm>|8;sLTiZT8oSVZ*Tfvbk^YIRv?hUbde`$B0?tePRa-1C)P;i*6xYAukR0c3hF!+js%oTe5%ytg"
    "x6QQhzZKl9BeyHzXkyo^YB&1`m~jNWvQ`0p(I|E#(!4Oblh*K;r{vq_b(5(R5)N$}Pw<oKF7z3nkouge*m(e64Z@8CiwP+>B"
    "XjLIJo5(Un`}NnR~vJuCzqJy1V0#AR1kh)`!;v|=m&Z&yT?ur+>;O0QF|S6wGyZF;7}Qfo8!7M3j*6y57zNQ}t(<mn;~2hE}"
    "<$pB>qTh65iVQ!%HOVGXml5DJv%`!iPmVm}=2R_~vi3h@RlldY%s`f$0!|*FMskKI+9^_T(H#0d}Im0SH#@5JR3i4lJ@4KAi"
    "9~pCUgg=}`^Ye8%B##jGtY;}=_S*3H>eVTx{IB$=8h|GHpwL`6$FZAh5W}x)hqSTwzB&KDPy~~!_BYi)<#b!L+qwNwGO`{%J"
    "t3BAHf`YX16pStngC7+B4ctT3}m6%w`3ZE;TGrOEGvCV=Z{veLF}{d$9A+5-}G<;oAwe4kkLNo;;v4lEO>fXRQE>V8lb%b;}"
    "Cno4^sHE3u9*7PoMl}1its`Tl6zn_+N8GffiYqNJffovGvM3NB=-@q(W-SU=is?S>i~a`0q|j^OC||{Bl|+Bs9+=0-U))9qY"
    "pjbR~16<|9YkE<Q|uJ=lt&dR1?QYI{6i%~ns2t4jMT`quU$mJYLjIu~ztp%JJi=1qJTha{t3sG5<$dven71<-F8)$i<XW`&9"
    "MBGt(?2)pYDt&apxk5#{%zRFV6`m}Y<uE!gv2g9O%LK^rj|Ks2k|A-_vhh=Z=$eIX~S1tLZNDh-#MXIHILys?pJ*uF!kn`j4"
    "kTEJ6-s7jmJjabR7bG`ff#wFwBG-+Ju}*`w5f1~UU`r7nm$*J8)Mnp`{!C%V&)mc|AxEbnIpD``^HnXW2Y}ST{F=dnrB#6Gc"
    "*ka>2JG-F?drMR6Uz(d!ti`g`42mz%2OF9wQL_M1W&3|48}<fMZ|;u#xS+)_hou=tqGuTaJa%b!iWfYe)6F9&QP}qYO6behh"
    "bUZ247S4dG`mCrG|7KQG#bz>Cc1a+glH7JDhtBKyMLik?mqg(ZQ37Qktr4>tzueL*&V0ukLstX5Pr1GlC4hZ-Ch^oN*j2b*#"
    "6?D;inctIjF@<gV~vXMcqnpFjVvKOKQ?Dov=$1uO26@Rz6!4Ir8mVe=kB272xtV+2MZZB!GShb<>zm*`T8)1U-Fl9?KUhfGH"
    "TM#s^lh_Yz)mtpwvk6m?qr5FkAX2b>%9E(#2yfgn=&S0ke?g5z{Bo4YE%u}}^l5L*e02<s<BkusmK<$Y@WJEvVlwILie*I)7"
    "<|U&;f2OH~J=Z)YyhZmhAX+oxl4L_gLD>%7sejqZ(60_;pZX0j=@LUg8&Y|SUGHV}y!8FJC@f1}&H!p^ndAI;(Hy)hgOF|}G"
    "qPHc$O}FWBOVZRzKgW+j4nf=G|Ve=p#2p3QpT_bFC3Tg6HjspGMQZTvRVtcy`cl%$f|ns`68UJ;rZJX&thU17;2pU7U(NV{t"
    "dyw{bHCyhKs*muOExfdSJN($SK00MA+|EvQ>8KurLvce)@jmCSIr?y!Y1Jh_MgXzS@qpeQ*1f30C;@NgQ*>QO7of@Bn(Gdf>"
    "ZRf)f^$%H!v<<N$?T)3pb-FXy|U-baD1-f3;X<hIyhTve-_^y?iMUGEI5zzgB1PcmV>R~rQlsvyA%$o}ffBve39FYKI+@Agv"
    "WYqvp7k$Gyss<e}b1(t1*h++3vOQ&|&?)fC()4VavRLy7qu-;ao4Ry8qFs*zJox(7^ANqiiD<BX``eV^?ojL!v?&u4I0@<V%"
    "mOr}98ZJW4FagS&h98N<Ep+_KxviL@$ZK~}T*x52%<+U$)M9F)BU3~N@orvTC$9erGcb`j@9!mI`VIICj-<+}XzEz>E*{Jzg"
    "R+$iUSQw(X;YL~`zrOh>lUj-YYO(oq_v1bPBEA5!w|kAF4aP4+zQ7mX~W*|+b3E-+at@a6q#%J7nJ#0yCEpQ<V=5!PY#POl)"
    "YaovrUZZ(P0!jTq#Y3nCWmExnOsY_&g?k<&ExNUN=o1upDv?)Owu{p?($zS2i>$8HSz?Bpr+gh&h@d`XVn=0@BGHD_iJq>AY"
    "X~y0<Xkit&S`UySk%45aUDBRJ-VXfmrj{J%nz+GqkjJvVe;cvBdb7|wAFxW7bMs+HX}QaT2z7#U}pygh5rDo)G@F8emWx2cN"
    "J-lgT-CqK1ChM+L@eIEBegwhX;<8ZvLS)zJ1yeHrl0gU}8(W!ODe@*P9Up{mG=`k1SU<|<CcDh_sZRTL@h=4?u_8?ikFFLUt"
    "EGhkKEwh|(s{WZN^}AFkvndQeTFFVc{qwNDSNriL5-32qV<OkO%rMi6y+`4`w%Yc#`De@Un*dk~PbLwsMTYk6p}#Z=l&8}t)"
    "Z<9f+ne$-$(mK{vk!kNKZK${7TyqD_-;KQbRs8baCO!U{yYF@c|d&}CwbyD^GYhwUvU?RWRex_AEN9pf{gy@clN)Avf%39>V"
    "9qj-&O^fw$0mfV4;QL<?me|sLlSdn~`#G{P2nSn-Aw308s-)l_HH+@q5pt2Pn#bLeJpax9{uu7R>l5fLXBFtE%Mpv5Z0rbQ^"
    "Dv){P-Mdm0~$`s=?;z5L(g?15#OeS2l{z?W&aJ;lYtrYD*Phry#<A57uQN1(}?lI6P(w^-+VdmLd9Came~l%h_Lw(MTYbu~Q"
    "wp$g+iA>caOUI!^T;NFV%Dba4W(8VOVzc8oIRxrGg7+1^wpxNctgD|%IA+**B2hd3K6uQeuqRbPRkGQbSGAVdd%=xzMHX(>z"
    "7MI1~6VANz18`?i6*H`^6&jqQ{3QV0dMQUIA9*V_{urTRVKYnZ!0!*c{RyX&=~tkVB`r+sIXI)&pnKgA95<=Bm$8%t$8Ti56"
    "n-OZJq*r1&lf%-Na!Zzvp?w-PCxG9{dR~%VtZ6(h#IGO=YqEYp)M;loMC9pEA`|s^vwzVzyCo}A1DH%Hr)B~!gx39AOrqtQ5"
    "2H52*WOB4)lG525^SXaFD~<oWEUd2>DOqG8`@CZvtV887~}3Q9a`r3qCgiYJsl`+BeECrGpKnf$E%NXZ{Tz6X{sHKt+*ZTkp"
    "}NI+*pjf)<Olb9X3ll-MT7&}sF2N3nvC%OCDncYo+!!8iD?LK|J5kvQN@ekz}~tCLpeip#H4k5?yizrzx~W?T<^AE7%uxXEj"
    "l@mSUow`Jt8<Y;xV;8Ma`;yy@TgF5k8H4f3WqRc#f{n7${6G0`_G8n#evkYJ^dGY_Y0h7LFimEwtmOFx23H0-Lw&4Lf)?A!$"
    "`p?IcqifSI)!mP=#e&WuXAOf?US9A<V3t0Toc(vkq7oExdMwlVU}qB|)NP<#r-a-v^AW|y0J$Ys%?gNycb$8dTjzX?NCQO9t"
    "H3_i$-q7oFC`P`yx)h{(!Bt5xxKQXZVyRwgt!S!Rze%7$#q^~8O|+$I?ZRR&A99^>Y~Mj3{rw;zSyK}Y*noCUJADPC&f~@@L"
    "E(jORAPHckfVKgJ<#|hH(Q%Rd~)`NM#_Y5+is*j`6?)U5}&RMDMJcs^>4gQ-9_BLOETtS5>FqZ5qN^KkyIjJn{4U@7X%B@c_"
    "=BhWmn~-zMxz#QOpoofzzM?gG|k$|Id?)X=O9s~A3=f=75g+M1X8%GTYwcJ!gT8aFh~95idxYMpdE)aM3d<M^S5`oL=)Q5yM"
    "<i_^wB=~n)^^H)h?E^5!UQj1M2Rx&MuIbXgo1k3ee#+X;sYo|}f`AsYeu0NrUY^tA_4&68*66b9b1-NX~1pf`wUMMVXm@x|T"
    "A4&upbRqS&09?hX{kcC48t%;C`6S_RF#Fiudk7mr%kODw>qZ*tN35*`EaFHNG1C|B?!u4-@~?@x?OVlrb<h+h3H?G9N=D1<U"
    "*X|nHy-+S5`w96?MLRsbu_$y>p}BjR6z}32R)wPR>Q8*85WBb4-q$o?(@^Cy=H8jlHkac&jRQ7@f0sBE``w}lpOJ1qi0w*=N"
    "&$cH*c-r`n3Aq1h(u&xrh;9Xieg=FxU;NXRqbDbt3I*q#IM%kpynqeg;_gbFp!}kMO7Em8lEjs5gYYX8$eLjZD6+_B!4-$k2"
    "uZq~aIVpJ7#>h-CAHCqj2Z3*XibJcc33)#)W?Ldkq$BtKIk;delkzgeRl_hyRj+g0ISwVv|{t`r>LS+uhKt$L9BeXK|>S5C3"
    "CT2W8eub%v^>@lF96FQUu>=2b;$?4OPBibI)d(UNch`DS7P_PPSe*rqDJ~i53fc4eOv^otQdw#M*yCPV9@WTFRodm|e`_1iW"
    "d>jd%rUu+)aO7}Ts&e<3aa{+&Y6LFX*<%i~;;UJZmcG9vN9ASn2Em>RFbT>meOS!0PDn|I>0{l>M>8AKxAlyJB8Tk4l%YSgM"
    "Y9Q=kctc6Av^P4Df{SsHkrJiv|O-BFS)Ojzu`ExRz!hL+MdZf!wvcBziTSYSUdGv(6FAq3%X{l5~X~a-Bk$gkf#Yk^5d|`k^"
    ">xIsn1(+-E{(@IbK0=bCM!`JOGmep*4Ns_@qy>VE-LductKJOAdXsMQ#LgcBFy-gi9=xr-TE-uh5G$H@#|K`iMSul~+!i`v%"
    "P`Q7Xw<=C-&caB-MEcVBsg`Wzsou+DLM13HDWHEPIJH|<O%@3|xbD2qoEu?*jvAeHrZn5bZ`R5U>wRU96Co8Ar=>TnFC8K0a"
    "^%u{t>)Om6!s~vV87@=cu2$4)8z?oB*4zrMfC9}Z~4|I1rGyCnE=kyVaUaBiZ+3;=u(xj)11;R(s{W@^?Z}G9-ZBYQm>k{3!"
    "{#185#WN_J-uL8K@OW6{tV~@0Lq}BaTnBkf@Zr(>JoHweRWLS6W|tnIgL9fd%Lp%(W{HeEBYhy`rf2f2dJK?n4@W&l=F}rrd"
    "qZ_1dK4hk?F#&;^hOeS*(lvW{>uW~;9#Ty*6{C@g>(h)G?gAsM;Iiz45!n;l_MD*@^Y7eYE_B*LFE-InVfN%$Zcw0j_Cd4T?"
    "25u{PHF0U0m#_GmM#hAB`iFnXezELIAm?gpIy#2|TOw4%pP>upa&RBOjXZfVepBbWu-L?|dC&DoC7?bXWQD+njDkaGvR8tg^"
    "uMr~7FiOhpDck@mjix)%t?guOJW7g8H|8acIeB(Y~RA3|IFGwn4Cd*Xv*D;OX`Y{?ryfycsK54An0kCY{EWXDb8x?TfC=~wH"
    "WAk(yvTsL3a_h0hz2NfxFlL^Hsu!kkAg|!{c24F|clRU|-JhI!(^2ah_cI6BWdP>=QXkdg$|46@~K3xJTN4gwC;QMN2$Y8_K"
    "K~j$TYio&YTZ!yUsU3Zc5nh<|e-FfnD5TUXto_vc!q>U($veOQ@|5ie-9=3;b^R5P>5L`?KZB~&%!n0Q0lU-zP{T!o^`H&HD"
    "s`PdTbDwn6nisTg<EESFG@>fSTjlJG5f?u2hp~~1OU~rWQZ7fS!G4Iakg^{oizK<jyldE-c{CQRqm3mSzhn7*t6hU$onmKk}"
    "Br3L*%3`Rv)<TJU$U9NQ8zrT!{S&cp$C8&e?gHO_w@St<Pg6s*>?UM5V>eyX3sCzu?dBY2^x*z9<*<!>M&)-VYzw=XW?o*aF"
    "YoNYRKF&@xTNw~^v+LS{lKTLuk|CaxCs0Q2gzI4?lwFBIgU9Ab-QJ|zqs|I*%lpJaRtK32*urTdSUZf3!y9|x&MxzQg?ymEh"
    "U)7SogB!$A#z)W`b)Mltk>Y(D>hqayAi#t=f=&Au|Mk|)qRZgVED*2N*#nL>RN8E~mM3ceCKxT(jeD*}c`FzltcrxHsqWiD}"
    "vS&GgT9p~*1@8aQ0-jD7VKolGH&Pj$SmplV=QVZB6#ml3LMjyK;HrN=_G})T$+i*edv|@hmV#4Sag+z){M><5yEp5E9YXhRw"
    ")<<o<I=eMkMQ!VU|5fWNc>O#WDUgwP`<=R&#LXdE<510`po=ez9IbMAS8zL$0op)>cYl#k1muy0DnS+4OhXs=%FUUCF%E~34"
    "42D^^0VRO8m8A9@p&J@78NfuMN|U4~hGCWp|OTa&(ZMhG5U8-5%;X2<XOA_0ECRX!=ix@FbO|%!!YyD}|hYUCFnHe9dHd3iQ"
    "ENq}8~J*F&d(yA!Xm*x)<;H4dP{NFk`$6r$hHv8ChzL#%!`u3J)m(GRA0mqZSrJ{7HEB>>4PLZ^=<TvJ`WEiscgcSVzCR_-R"
    "Ltt(sZF<KDT$5tASc=GdqgPIT^ZESy4YRY?;aeJ3t^s)SYb$)OxbS}gzBKK4E@KtTS?k#s?2z1Ku)FlMDTjQZbpI_;P+1gS?"
    "f9O0q#kf1vk72;~B{)rPs*pg-<H}hR^b!~4W1D`~Ku$Mcx{iAn73=L>RP;?aMnJ+BU8}J?$3Sy^q^dO!jdMvG6NCBFDcqHQZ"
    "4`@pX21%t&KV8H;V)~$^Y5}E4Isrtt0ELe`<x?mjrJnOO{ZKBsz9&sNlb!8khv>UtIrIj1$4?hhbwaD_~tQRm91Y*vjJZv5f"
    "(6)?@><R%S8D0^Cn^b-jNH_LozmHwRwG3WzHnvY*LT?oH-(4OrKb7zGLh0{!WfB;F6}|{3nLcLV9(Xqv)G(O_UIi6GoXDkfS"
    "H2@W_k@AZI7U3%qM4)bD+sS3p9cR6lx5f&su#Zma{*b{X|v^>5kzoXk-idlAcr!?;am1k~Pwx+6zY=sn!s2sBqcIlY0&sEZ*"
    "n2EudSOkY(?L-W}vGH9`vE-cy2Do|xUi_6BioSwSiwR<Pdy(P06ZPF_Xj{)59`<jcH6FeN=*!{|QVNbS({@FEmtZBeM#Su%="
    "SPJNLCb^tpDu0CK@CbY)%QZ^7TD-xknZQ<7<t`=GReTl@SSeOp6pt#Sb+*%3{YYRGm+$#p8SDC`5g^IbnUevPf$(#{=7i6_l"
    "rmaF&qDb-J9F`1^7*cFYgG8kxX0Wi=eGYEY+aM@%M_787lfaWVBFUq6lRJAQY&WZ(>t0Wm!OFAL#mwU*AY>dmw@_bDssN(9m"
    "AR$h-`R0pV-26drPrlfBS2Kd&#A~1$vTPb>1+BbBLQB;aQ-CI5YR}iT1h@Lp5DRFGlI`!M>-gSCzHnivTfmh?B0sVkMhTS3L"
    "ZwBSqRaPc&tv4cNud{If1jQ7d70Qb`u`Kj6ZQ)2joC0e{8i;EEaEL;qg6Dl%>yV>SmogL665Sjok|NuR}S1a3ktmTE@#Wfv$"
    "NQ78@PlQMUMU%h}cFiGsnp$J$bR7^Q}K&DS9Uyx@+D}Bi1slt_-M1TcDl4#cK;>)7$FWYUK{zOa6(qy6kv2V_yNq$U!SW>cd"
    "P!Z$f`Z1Jt9gyhr=_&2BhHaO1b;dn!%>6qQvM;_7ykO6w_5S(kr~G$gU&HB4Rh9~XLuSKu^i4{-GPjO?1dO?Mzi37_vn!)pa"
    "h~`GgsMNOxgj#%hK@3)Zb<zH$RaFtj#L_HEaUV&0h42H$at5Z#xLSQK7<L#6c~1MouL7l_d6N5*_+1#@i%Yi{`EP+w3A8$kU"
    "C-SDo+((A>NC1hii{m_N-Ir^mOS9MTdKvSW9f*Iyv%DNZ#xV)r=*NjnsuxG08ZpU3X)qIHuw27K%ShC;81AkO7B}znxp6k1~"
    "+e+Ws}rD`~P%*P-~E>s?*9FOx)82qhA)$4#{xlg)2+#8&fH6DGTU3cc=*S1Fw54_LEGKxTNwsPzKnJX`1zN(9=2l6F1=4xuR"
    "0AB#$ewxcM!FbEuut`RA0`IKb{<^VdaXE)VHMevX3^Q$MAPt#@L&10w@O=h;QigyL9h-4*~ti_1=J84?#fy+`)H7osP8eam;"
    "u2uf#LpbCEj|pDb8eJuV2}&VPIPQk!)sqRlBEzy{x9VV1LqZY`0vatJZy#zS&~<`wK_cL1h|ZQDEnYfFs&uH%upksubgM>Oe"
    "+1}3Ighje5v@B-;eb@fHs%qOBJ`>CGpi@*wSI~yND6BLrvo}7&F`0YTg6zCjm6nh!ineoWt={|Yald3xV6mHN)D~rsy*{L>%"
    "@0Sn%e7kLVP~*7o_LuROlJR*(S(Ww-*dQr*=4xZ$Ee;)Z>Ko-qO9{6{{5Xu1hN2>u5FmuS09DYn8qQ@^s`e7xfvX4(<NiF-="
    "b_<j2Mjn)44)eo#ySd>Z~CbtYm-7y2t+rmrxv1Q<@A@h<YWSb4>Qe|5@t`Tl{}UitxHwD&JKu>Xn08k#(CDdaS}KL#Ke9bT#"
    "FK63#7hn~dn$L_Nax&~PtZ6Lx>3T<RHE%c(Ouyr-cQeEYql+U6dD_8hZ6haYy_v2Ove6YYopR^6RcvPHuNQ#-RQjd5MVgAq6"
    "r<5d+<AMNm==Pd`6IS|LjH-9J*R^YaCy!PNkch#F!$u%-wmwY(TahqBj3{|xVRO)q+==>lFV&q`v>EimDMPc!@tZkUk8a;O1"
    "+XGdx`MB2_Vmp+g3j7>+j;kRISAc&(Z3Hiy@a%3n2mT|A75|#HAU%9+(cs73ImpTV7eS6dJ9CcZ7>faxho7^g<Mbo<t{_0L%"
    "W^NkNTi*&0hf*ytKH$0oE5ZcfjAmVhbVjoMr{L_8RLE$5pnC$>UMuO|rtv+vV;>f{eeLpn$)X8=iQ6oUAPKHN_9@p_L}unMa"
    "=b#bvPvGk`i>W~E1wzOq$%xa6a3hY<frPU7<ddRz5(A9^d1mZiQCm5~udn*|TMYl`iqELDId1Z&p8y%rcVie~SR%(pk%;}<U"
    "Hd8(KX__bJXBis`TVFA{;58X`UO_1TJgE<Soo6ehFLDc7|yuJej>_eYGS$)zV6jP%PYB^m63Wo7=M3v$k0w3{_adOiy*Y6#p"
    "<$n}YZ3ZJ?#%^MOG{W<9XpsVv(qxN4N`rKOcolF1bO*bzqICAP{^qvLu0IS7;Ey@?JAT-j`oH!AQX~B6)8&VgcD@UK9^eZ8r"
    "Tn?aA4PE@MLDD1QSK2Lx0I+4r;e7AY$=i+F2=XgP`;;3;yT$0LJo^@r{ctX`SlCKl6#Qt`#t4daaL20O=`@G9<BmtH|7?xZH"
    "_*_d(sOqNli<n%92-cVo%yr>$o}gm}976wL65;HJ5fAIQud&D1MX$cO~B&tmvw7jqeYG@U5ihB*@ECejhhB?Hare-v^z^v@q"
    "?Uz`O3(;wIo<s3#Tm7FzkoSYD`G-gK8N3r}u8&LRbe%AHDwSs+Y8r~)e_KN<}hst47OmM6B4>g443BUpK&ccKw+v9<dC*ZJ9"
    "!|C37UA*`cTu=@>KD(cRW)M*&pbW|KyU|h=2#YdLyaKl`oK$=<cv~^8uwoWN~dO2KV|B~-%_7&CWbW9bj5Gm10<`VA<ZuJ|L"
    "$3l|fMvY<btM*Vo1r%itZ38{`cAXbSZc9tAld2x~<8ECdYxOOPx<38d_gu2Z@;da0D(q68d68Oif$g^2NH}SPx5_@HkH}Sev"
    "T}jGbc+Q{IfQ@FRCl*VXPK$qFIiadaI%AO0rwAKqf(%CZ0{6e&<1toj;WN3dx_r>n!_rkrO?Xzi;H}8M6~4l(;Mr=l_EmGKo"
    "MI{!V6()Pz}P9`xzY~Fy=F0r9$9Z?(My$F(1ep;C|Ky1-u3abT)lfAp2|g2>#_q5*wr1)uIXEEkH2SyX(~T0?I6hhMBOyrR*"
    "sRymb1!%$^N#rBoGCSmPugmP*^evJYS34q+CSO-+?k+M8qdCJBF6;<t00?Hl7e6H1|{ni`x+m`_j4->5N=*9P2m#sM^<$5!S"
    "UWG`EvsuQ4Am)CY#OMnz;Xlyt>UwDzYp%MXn&VN8ndolMMDr<dgKpY*&U|C#4ToRF}AMZ(Uj5vm-fYus!VG*dzPgD?Sor6l("
    "1E^zT6e*27Hgq8iedfTr!e)J_YVT#sIg3bAOoeuSCGm|=5VVZ2f_n2}N*FueI-hJ>LpQdlw=YRy52^ZMvMK*EL?`OMr?k?_f"
    "Qk*FF@!6}s*p0MG)L97eo!X}`}G!6!K6|q>X2B)R!u$r^}V}u$l=IOSYT7TKczj$9dPGGg3xXSSK6VG^s~|~vRr+)9JzQQlA"
    "|b?uHc89n2v4td7i=>srn_qby%NHEaG^jl8P?n$ZviK&Hefzgza>1fWJKxEfov#`dR!MUTy8Ohl2TEZVDhcaUb;kIi(o4J{w"
    "BRyF4Tbxh%aEW9Rl$K9+luY4^e&HSbz+K+s*Kdrly{Dw~f)-=J>*!CWo5B!{+X!i+Xa$$(5+z_3*q|Hpx*Oxd%lD8RS7ZCR)"
    ")=d^ESXS7~Q>-ssH8tL_&&?$AU&jQ?lD*MGQFe)(I9NlQ`#?8BTBMaGQ;L))P6xIvrVcGBXZ*a-=Pd(%i2xl5DM+UO-H_2pa"
    "j~Ew=V`QAL{a3mqjmw8Qq6WUcVnPo4i{A?R$j}ls-?oX+GAi-)3ID1qf7met%=*72uW-&4doCJp2M!2TkSCfSD|UE8CVePxs"
    "1BFsKRR=J<%X+<^81-Mq5CiA8*HReZ{iIALPNtV^Rh9Nm|5jB_*~;c&o5lNTQSzt1+b$3WMaMbHf{`QuMACOdtVQaLy&NN!_"
    "d_6%y#f_<S!_CGdJ!>KZH_>$6||f#XQ#134pDjJb_|L!xd!#O#`aYSZ9sN=_Xr;QEJX6%!_GaD*vG7;E<RHX(9AfJA!Is9vK"
    "aXH>9@=?*Z);fN4RK|Npy0<%vhV=?bm$yJ}^C_EEkCZySYSU&JZGd;Xgv^q*=mcF1kfkZ>012vD0He}f)-<y<{l{xn<IY?3K"
    "-6jaFw-iohNWx4roI^Umn6k9t2=gkJz`uBpVI3@V#FW)2*+71W32T@{K-(v{AS*clp0K4}AG@7MXNzGADw<Y&JbU*8Equhz("
    "rt^dwF?Z7?z&Ra4AdlY6uknQoW=%C~iI}=-H9flMA7-U<ebx5aWW-e0;CB43g1UTU-zo;BN65EHTHUunUp|G@*bERiC$HKh%"
    "(0f_JC;|*{7J=jp24L9KYo*@Be|Qlu)?LLGm><RqI|SsQ4{3BfegONysd8Qt!%QT#2TrLwPh%10~f;$>PgEKJMZh~tC4r>K0"
    "9Fl<Dd3X*2$iLf4q)F;aqNm4bWvUQbdH6NQcizOBzi{yWTl8O}6z<q4{zq;&zSyjU=uv(?hf-Xyg}tT?MSh57y<px>NY$QLI"
    "17aOxi=(YWr3TeQxx;^;5X1F2ZFQhjdN?_*;JPq(opv$;*Kp}bv_m86vj{3V>wG-&H5CuZA5)EpzZcibDls^29=Mt0ej5IW*"
    "VmGgQ4btSVhZ=crFDCc?>@k&RU&7{%rH#!ESZQ!EPWGw;rnv%nOcBY(T(FIM^GEYg_d`&TRxgu%Q$80<&T3l;dSm%a;ah+Qv"
    "?*$8BO+F?cUC*bcFNhvHuvk$?>`0CNMzDYZRyvt-GS>TaFK|hGc<2E|c%=RSU1tFFBfFq>u4>+IrO4kB+%?pNbh}*FH0>jmB"
    "lj9k9ZIt$*b>;yeTC8vR+Ey`0dh3L9}<mbCZ}B*m2V<nROjk3#%uvDMEsij@EochvPVSkYRt52=1c$!BC4(*sUru7*jfU|-&"
    "@*;6DRJzF2jbNpin|^t&U0qCFJGHrw!q@-cdM9k=-cA(6}RzJtzY+b$lr}tQ_0*eyrqaX*1@t_ghB{FB7G>#b*{Mw9CY_A`o"
    "Mf)nO6P_iY)V8eX(q4Y_0bhb~;{Fp~)Yi0&=%EI$70^uW|dreo{t$0<|}tE4xLLNF2q#?WnqsiJAsIhX4&c=-R)2{pn8w0_R"
    "~eu2Mfq3!WqbCB}9!9FfU6QV_91chd({?x;L{bif$i#s188Qo8Fq-ZIwO=XA)H{4#=SDyFvmO1_r9l&Jygq4gy+58ZyIu0w7"
    "oxpNQ(a78fq2a=IH{>@Mms-z2(S!@`d5{$7G(1*$-(ZU0hi-1ZVCAJm%=o@<9c4O@v*OTsFUk*%9wm%PyF~ihLAGMyH7C38v"
    "$x$}XxiuKhS}cWhsa0SjS7E*Fv7FQ`)?))Q}?^jdaKyhHFU5NP6;Db`dm#|dflUm)>QCUKDBMOIPpi(8=5c<_7y-edRf!}=O"
    "eF6W+^kRo=08*3sH3by2N!cdUSbK?z45etxBj*q12j};)#*~_@RJ<8bcagS--Z>00+V{lbNJlsb8qS`^n#?EJd?7tyYmbnB9"
    "O)A8g$TD5GI5Y32=Ea7a8lg5_!!N@6RK;)@XS{E)bekVblS^`CW=fZULcaS@9RWuq}Mnu|`dAaoL4LEWV<(LC2hkiGhc;#;z"
    "^d{ZB#3fORZfX(qZ<Md$Qzfy?5d$RwcRTrE8gYi)Mw~Qqa&@xxHkYGIznI0NEvWBe|66(nxu;E3#d8l6!{p^&3T+Q}$?mbAl"
    "$9DS10GB566K5$|@}lIKQ9E1nP~_k+ch*dA|FMrnRKIj<E2Oxj|2SO1^DaJ*RV(D{C>Wy0>!;wR$LNMCyY?jg*9XpA<ulPgv"
    "l*1iRjmnBJoV^aecgZ}B4T6T9&9&;G25B63pMuSkG%Ro^bwBAx0y`^uW%ZP0?HDD5=(|AwS3jLOE>Q)+s=rMZXCgV65t^;8P"
    "9+z%m6Da!hfKXUl|F($J8xze}YDfSX8f|%8KDb5u6;fbcmN891PMjm-|IL2?uN58H?)v3(P5PLDaAX)^yg_JHT>OQ&MLrAqf"
    "u&`@xdDOooc7CN@7ja#hUxK>mXcrER&(J#NN3X@})P2F(UY8|XRFKa?8>noPcW%^(om?}S^Q(%-hWU`eQ*+|4^85msgb-(y?"
    "AG;uyZ>M(Nj53Vj!JMHF6ZGmgck}ndKq+KDt5AhvP%C!D&b1$`N`Z+R-*Ou#4*-OfV{}<_)VMu!Bz8<)oQ}<BmZ!Ts5`SU2>"
    "kp_sg{;SbJ{PYmz2pDA?;~$(-vz)Oyg7?Xb6kl7Y?p_xC^`8-FD$Meg7M=m>-q`*d9U4Gf9!w)f{mo@=CSVmWp?Tyj2&}0*n"
    "`5({lv7>T<9V5?acEg%o90pg8>`uHp7uvtAs`6jN<TDhYI46j?Q*E>n}b6}cUZcLB6gL>(4F*?erRHYk+Ohy_POZA=M<-tMw"
    "&jNFf9ec4<X+0lh0m~heg|dkR~N>u{6Q(5)qXAj#ijdz@o~0_8CxNqfA#Gb<z}S&Z?c%W|`jR+{v!&-(%w3U0q)=qBQ~BR!A"
    "Ow{sBG8|GsF5^~REQ-KSSjQakg#4T>z^Z9xaeR2eN;EQu#lUooM83fgbBW{>BltwCqR&JMP<ig)NdLDH$WjZRA`DrVwuc#CD"
    "3>07WLdbzEKJDAjYDq8lBH9LCTJ!<&ojnTYu3WYF}4&~~9NZZFEPp5=aKND8iklkMlKD(Z_NXu&Ibj=SpHPmk+T*YT#7;p=P"
    "Dt@jI4>c}VFhifI_24ORuJZ{z(PMVfzh_Ze_%Xfs{i_)Fe6CWbxg+RH%ar>mUoR;!4Z}JJV`XL96x&@+Diw3+BW+cwp;4M*o"
    "YYMUpB@`-<L*Sm&nw_}FKB}tq|l^OG8-r^D^>l~MWf>>cV{TCmT`~T6Urb<kOnoqP$=yS8xqI=$UZ;78mc1)b1KBO!=Gs9r0"
    "DBBT_y%EjBtVmA=h5M5#nKJpWG7A471f`_}=P}>bigPV6kz7!Nc4Q1sUInAU2nihGrB#=G<;}EovR*A~5>nUW3+*nmS}y=c%"
    "+LWVzzl6|&3G3+CfSO4<`wYceWBvzD%AH{z)1*bTeJE%GgJI<N+nC34l3xUI&72EY+OQU(QoCh=&YLEz6mpJ(Mw(35`B6-^8"
    "iaW64F(FQ4EqEsv)J!eS&)^bV9iM|{Cd+#iV+un}*s_eXo47U{lWmQY5OH^ROIxyK>aPCWK@wW>jU!gGL7N~y*HbqlKP=HsT"
    "3&!LFOwL5ZaYR6zG6Fd)OKk&$Ee#mt;0afBBn}w^JI)Re+d;H5FVu>nlCw4j!*-!Ke!}v5HVXl^N>j|TwBGWledUjh6iz2Gz"
    "sZLs$zmSqYFHF}`&N-kqk#HVxE&-U+`3?gBj$q-Mp9L)+rcMR)oi{<+~tn8Z8~yC?08gfaQI`G9OCA=U;ji8IiJaOBPD~X2r"
    "6&HP0n%B^;0Tyx0D(5aV#AjaCS5TKNTwBcD)&US{8T5t@BBzHk8Fp$D@oNdWk~f1Gb>90T#Af-blZ8dslB*HOKnAq?b2ca^_"
    "3xhW8NbBuU6Wz`{$09-%9=!JiYN2jZm}%eduI%L@CewW=2WX(X<!RjoWKx-sYf%oBy`?XpO`Yb4*&f>0ar#RZ|&?UYB`V73F"
    "n)z&RS0&lah_u%_M2V?vp*yNnq-+K`?US8{#v<wcFPvOV0?}jKd8XB-}6X_~7wCG9vjoHUW^D$?QD;pnr2Rw7gaxhj>L<@~m"
    ">cWjSx|&{GKN;%~eRz-kwv3x)R#?O?)9*jXrgJ+haS>d+YF!MEM(`F}(m5}MfBY+DTCfglUBv{u2j}6%xixg=KGUPt8|msx!"
    "0Ty0zx8y==}2VSwVowGocnki66s9q%r4|ZlW3h6YcIzDE8)Kdr2`>w{P5o><LK=8u|oq0C5>UKSTHFRjNt)Hmr5Fdw;CuJv@"
    "10fP&L2Jx?@R*ICU1)b^C6J&hhefu^x7_9yCgYRXAO<j;oWb^H11Mw=cEGO-NGo`InF{)a>t=JLJ}>%4G<k6*$C61X$cJBsJ"
    "NUyGt%yn+CZW7k@e*pFf+m5Oma!k6d->1V|i_T_PqsqZH%zHB9A{<~XE_-zDY%f=4W#R`w23A9$$!sk50gq~(4ZaK{n=PhRS"
    "XoV7NNq5hs;H!zOnF0-v&d*m|&YHLTM5_8UqOPx5Y+O#`so5q`KeJt+LFUMe7V{S(yZHN);NEXk`8P-Wwes)$QOi{aIEEz2K"
    "<v{hwKH4PZj7Y5Tg}OFw0k6EDwrV&=(z0g|wAO+%KSVA?u0<|&?itGhG28iV7DGior2xQ40picSpAtHsn(y&G9VkdyboW0;$"
    "RZ8az>tl37IM&s2urW>Py|?Xhm&Sz4&R<V?gf8o{5EL-9^cDLW<DVJMQf{RG)+MXzaGCB<owB&el(ER23ik}m2GS}+ZuEL7+"
    "ZgDIySuXUc}(?!lTpTC7kLLLq(8h=)>)l_c3zA_g~iKL@gsR&$*WnIuh~5iQv6Iq_|S+3@!U<c_n2tM!4FMC84gJj)Rgf*%^"
    "l)#@qGZP~U@xR-0se{i@jYy=lFxB1-<0MOl|BQ*925QVAlL6)f8VK|s;R4#9aJ5@*AlQ9r8gvySQ*nl++&t7?oW$(H@DXkC+"
    "FN}Z{Qx^xR-iO##WIQjBvN565C?ChYEZH%N|{uC--wO#)6XRLFgi%VC>uJjSauUtOsnd(y|!NsprKO~&4ISrKUOvhW53f8G6"
    "xVerX-?*Wj>q!}w3hkd(f{UJemj>_O#w?|mzl|Qlu~MuBHF!ZmY~_^FLH>XvHN0%T-g`!PZ)!DS=MQo?Z-i_H-i$1Aq(tHVt"
    "n|?FLqMGGPj)DRI`AnYudVz#O8Zh%8t~jNM2$2chxCu#BEo|kuH;~Zv6%2V%x5XI7f+?>4v#qssAMpka+Qun3IhSe!~s`Nw6"
    "%f4u%xzA2MATMXSY;#O(gZsbd>r?O+C6UlAkM5*ppK_`{CYe#8(qF@KZ|fJ|0R$x4El<ToBazgaDSz+@bKlML(vqeq!>%Xr{"
    "_P681WIo{p0c16yQRs5z3g^4bZJkKmONkpd&@K<(omo#CxkxiFba@E-ErsaOc(z6i_TtECC;*m43lQ{Jb23!LVIn|ECXxJ1K"
    "yPgfqDItZO+_v85-1KKcWgyF3=SFUG#dtIKfhsL^V+#EZl9AKR!5C1RQwP*)K6}0(mWES@P*gb^yiR7tV4-H`>Vj?nealB+s"
    "T_<Z2kCl4OcZSNkFabSIaMTuAVg+>hnI2j9P;PcF7zXM&Vl!#9C!EtE>s<0-DM4cB6U9Lf!hFI{qPBgt#u=#H#CBhEVgu@xd"
    "#b7H7a(6&KBnuxYl%Jtbf`9YV`yq3dJOCn+5b@Gkd2KchB44reo9z_*0cGOUUm|9L9Do@paPN`+p-{YY7YTs?x7L>7OaOhTa"
    "vM(-p{MqSRZT1=7EnGA2XAD#CWq9SB@XWkV5d5A-MeHqg!AuyNU1W^tCE>rYY;`WgC692huPh*b^Q$FEhvu!GTF{u<^Gi|0e"
    "yvML!G$BV2rucfY4pEfDj++@vD~1Z%wXu})h2Tf4|g&YQejC~mhPn$Y`$*IF&ydi^65c;dK5Yf!pS13f#J)JsCT=eEmzF^DU"
    "JlB-u^l3KXLCu;4AUnt#O^QNhN-&m1iC%I=B^A)%5^KlwBs1hsq_%LbEi4qo`x0?2T<0gPKH$%+H4`FMG1L1vs`z2^HRXNx1"
    "yVo_A<2t<+EJ2A3p_C&BReVNM7HslIQV!64wS3)LAGv$#s!Zz=V(+W~V7cRo->l8~SZM8%cvQ~%(GeJO0OyekCbozDT*G*vQ"
    "5zc9h8SQA`Q8d`{z{5sfi-CTx^UykKae}jMZ0emFNUsRxXSv&o#GhZp!gRILII`4<3qM_dN=I9>|py&R9UA~SRpoEDn|{L{4"
    "QlCPb=Ub#SU}aOeFCs#M~9??o)h5x{>;;-4*M7u{|bgRr1~ohQekPzboLAqCzIQa^H^?8gnpGkUqtH@hlSq<p71GIB;7WCcs"
    "ILcRc7!W-*fc-OCTVwo;Ka5pI9)C}o-6fZdJ2T{9nnutmON9>c&@zIgpj;(NV905Qc$#8x?n{rpUMv{2ZfWKrvimgV9Ir_B~"
    "_FUh$g`<MK<GAxahxV}L9qsKq?n1&Zz*Cda$#TyV;WWxBW;Srl+SN=HD2W!(r3KVe-O-k{p(@;g0j>S1vbjPv$v1sY&+_`o;"
    "p^DJqXG&~Hjokm*-@{}#<w`UFJGl&<)zLnR=-5o<+_VVZ>>8Cg3RKQNa6@NSj^qW@qXU>lYwTT!Pae8^o+bE);=oYh3@?QSE"
    "6Q-0>|FjZu1=_$qF;uod-YXJkTH~>dL$1968M>w-~5wLt3`iBXkZSkl}2eYlk`{3_+eg-8CK8kw*<hVe|@IE-?xV4m>1b)IF"
    "!B?a>~#$tt<||tg~|ti;-z37@@TkUiP9MBOBf9T7CT%=_+9|koO+l06FP>rwI#WmL-*)AE7!rXuOAc@Bg~DwPhNx19TkOYcv"
    "}|zn?6O`}GC)YI74wp`712a5ll8{r$vI<qt7@?kSB}I+3IT;FOvJgt{N_1;~oT0r&4tkartVF~VZc17@c_kT^Feu1l2T0e_7"
    "=p;Urar0^k=YSQWwItdOy@AG@&ljAM@eGnMIfQ>60|LEA$6<t|cSV!Ai6sFKln|)*M>;(0bjT;Cb?Q1EbgMg@Vy9`BJ`Vr>I"
    "#)o6GQOOt*S;_A%2jDrtf!7P`vRw(n@p1Z`zmek*cTrJ`iRpF49#+dS@~26>N}RUxmQakYcE#^QqlT7)!s(7Q?o+7mf}P9kM"
    "J-<vxfUhE4HP3jhNj2&Ol1hz4{0ByKTAqAF-E`^N7Z^TZO&I7)K*u`>Q;n5-Ug4tk0bSwn@IKx2IevAgQK#c`N7P_3Vb?6;a"
    "%#kwB>`$ETj0s7hb0^MzKuyo5}?+eF=If$Jc6k#_1v+YDRdHWvU3Pkv1^aqHKl5d~^v*nv*Er^Jh}Fc)w5RLQ@mVlQ#LZAdO"
    "6$98GEZkW1J}F4gjnm4<1kRp?3Olt?T#qdgbBwQ*dB5B-=x!uymPvgz-nq>)XtcrZ1~T3zy5=_)uR<&Rg{C)Te;N1fNb2vG>"
    "#QQ<7(9`W@y9up?`=6T~;qt5IrGQZaejGxY;6WShq66KdaYRz{o;UDE2Vx<iUJ$$RN-me`{nbXO~>0ZvUQ`GpH^C*_oNF=9t"
    "*XaWs{;hvAJa4{E7)E&S6F|6QhPXk5)D==2?)BB{?}7NB@E6L>%o@Txr~f$yPo$wf>$X;4O4za=gA&6$uwZ90g-=I^*yxoxg"
    "a5CQ`Ct2&lhcV7K^9~#In_KG5^1Xt8L6CO{3#!Ms_4F0n~srzlz|V@C=|I8Ss3(ia8Ach-y3AA%8Mm|ULuvj&+f6J@~|<D@h"
    "(7)lukv0!%Ht(P%o|xD4ELajd3;?(e_GY^bJj$oZcmNM>$8t{dUsHy3wCCfz03T3ME@5NZ*1CrP9j6hRvyc|2mw3FQICk9hD"
    "=w_wr?0>12xgVxYtRL}V(4Tq=aQ3--Q#(JSE2r{I?uU`Cm5-QT4#wicFIa4QQY$Q$66-sw!F%)<C^#p#5@LOZ>e&VK){QOFC"
    "u_FmjvG;t4R6zHHRU)&*=Cz;<%u<*$uKggTc)rt%^PKWxZD3WOaerX?4=t&C2O0djHc@O@l=mbT~n2_S6VL5)e<mjK}oOA`|"
    "eDPlFqR#S@!%A0xxxq^}lAw{JG&Vy=xhzR?G^juvwzIq#cuG$?LQmfuU_*55eGASiwRjj?BFduV#HW-|JHpgorWNN0^(6>?m"
    "G5NlMkC*H*O((gq!rto40BenrRRAXFO9o%Z(>2#lp!C5NM%x%CKId90|Jy1LO27Qk_CQr7!z`CY{x7K$yoT`gyP1Z@s(r6XV"
    "4{_2~|LqCq^ygPW_LLWg9~;1ZhsNKAX$gg?K_KyT1eb&C=>iueIjDw~-6!x5SeOAj0S2tIsC>uIGFO4gQCKe1B;tt*ugAuvz"
    "z@Ni@;`E6hJ5T4ZS<0i4w36_BQODv)ZW3o88F@upY)<Uk!~(Ic6J$^?T4O<+|>1G%}`1<_|ND53!B0ssL3X>k!XFkzv!LXe?"
    "qo_(v6e$97lp7hwEreh-zjGQw>ZgeClp_OglS8S~>gX2%X5NuFE5jzlkW;&$+P5BCkX^wZtMN7TDb4c3sE^JJl1}a+Vk1!#r"
    "&B_@eZK;%LzAzIr>s4)6c?;`~OfmuHmPPj$SJTeZ)bG+&Y-Gd+Mbmg=3~2TW>>aVsKKdcgyS<G0eqX`tCOtpMzjhe5Hhp>&+"
    "WMGs#f;G-F3plOp?tGD<MvAs6iHXdj3X>)ly~4R$q>djk+CWAmw;~Dad86G#;~+xJ%!ykd2^5wyg%N&;oK~OF>(`i2NTH3xI"
    "B;3huJ%fkJ5-q+^gXU37)T&Wc?Wm+&l<m$Q8Bm5@Y|GJ2}$-VoIm=iJhj2hhS<r5tEl;37ss{7HJX^Q&rZc8vFO&gVPH<$nC"
    "1TZv^)Xlb$A10lr7M3jOV9^0e{SOm;pPxqv!`m51q$&+QMy^ek|%08lnj<`y81G3|PJpX!xGL4R#WYvDBfoH|#)jc8o8gQ;Q"
    "+flcy959zb<JJPb}x!oW->oh#;-S&43fNxdVg6A_#cl$5-hh-ytv8T?OvCpyk#FVisOP_ZS&W9@B5{|6Ltti3+WULtCSE=Fq"
    "=3V+4KQT-HRiYM0m#RP^XGLH)Gg-$Wk;Q<JM8@HVktsrpAI_P3#~$zR7tbN1HT_j<@;^w_foc=n<`Aj$j?jNe4)VX3gLeC>8"
    ")U>l8EAX!8eFqUhl7>?G3=(F0!7Guq2XCWX~dhGypanJ2)UsIvAVolBm5cVL{l#>lHI3@NMbOFIU@ugn8o*1(i;i#PgFFUzr"
    "*mG?ITm+5o-`;Z>TB*tG__J)+(qMy!mn~JTQdf^LN5*?j}37oRcf^E|~S{w9K*0oqU)I05)o)5?mpoG2UfC&zLV&DR=k2n~I"
    "l;4r^vxpy{|n`pE#1OXOq`q~u9js6-hm(cqn8zfefz=EdaaZ8lO|G`>zS50)NzeIy_)Bz!{`+2==d<Rcd@nC*-i^IlWFr?&y"
    "lT*fDIn}+D}<h1%p1)ncc(ln5W{qT56Uy+f<ezcDjN$kIf<XoL<`I-vGzJ@0u&O=JIfC;{HBFz}eF;Eb*?IQ(Di3Mp%+{a!l"
    "d5E4t7#L=Owvd%5kpmX@&MnRFC`Ads8gmzL<#L+L4=Z-S__u~ab5J3TLK=zv35-qFxApb_`(S@GIir6xtEz_UM%#YeoD#u*<"
    "OuK5tEGfS9tlI6p@k}c)fW;dTpF`jHCCP+g_kWAdgH|Gi1zpp-W4LJ$ducYDblso8IF%0_YpPCBSC5rt2inh6{d%e<LigpZM"
    "eDKGJxH2{qm$_iA|cQ2^8ciePP~_#T3oJ6rgg`CN6pW3i^V76LGB{Mp32)fyV29f3oyzLXWV?C%4AU*{A-W3;s`&hphm@r(<"
    "Eca;G}ed#v?R3jES`JlSqmlpKu6C3NHxAM!8(bWldz6VSjN4bqGIE2-XSPz1XTq&3)r9WTXx&>Vk^Z;NrB={9T-IB%cJ<a}K"
    "02D>j$^W1n2rAA69m28KYt41pW-AZ}w0*c$8$l+)!X%~Cxx20pr%NSVF02*lSxz^+(`;kxP6vSvZORTI}Aiw{ZLFHLWbU@nn"
    "t|!M+I7~zUteq($z=Q<5HPrNe6!dUeYojHE;`0LT=ta%_D-~O@GAa7j`i34inR}M44<_spFJ0mwMR4JICc{4Xu0A#MBjpvS6"
    "{6>kG`UwfP2TzPe7YmeyE#s#3xt5mjr`&?;pHA=oDTWlh#wddLm}5ewiaSGo5eZkhtpRaKc<+JR+FpM0BLl_!yvfXEh*5`9v"
    "QwYql3OKqdlk0=V&H0IQJ0|or8?`sC_aHSw*OVx2dZI5eTxL#wlfjO@*3n(c7$38k#68z4{Yd;?-Xw&~Yn=!;+n=s#qmgu&>"
    "?GveiPQIv{SUt0tAB(MkG^_>#WpQhF<l3;l$vW<$D1te1aO;pERrLx7eH*&Y$xN*V1wsYS4IlfSeF&zbjA&&rUHtIkuy#xU$"
    "AWq>RN!Oo^Etn<z;%<MD#B6ETd%er-m;@Z_-wDa%6$pEEr<u5lC-l#dU^Jw`uf~R*yq2~Bu#{WhF(UPl<g-8KfkbSR(kirEw"
    "{(L#v1{~+#F`6sXAPLd{th$l@X>C(ksxyuojzodltF-YX!lH9=)c0cO-NoXru0gPcA7kbVc{5)A4QVT%a?Ik9RO}zsxU!kf+"
    "#`+Yghl?3sB>Vivu(n4Y}-j=+qSL7wrw`HZ5xdn+h$`oD|WKt{kGrU$Nme?G0)63*FAHNPGx`i1%%hgG=bob-5yz-{SLB)oc"
    "H|!|DUuFQKKS^)%WxJnw<HH<?|t*Cwn@vtOs5qnpdt3P!cF!%-YtZ&p6Dq|2}lBw|>p|*kIuP+dfb@;)m+Hzl`;%>^aT6FZT"
    "X^o1)m)Thqw_+l<a{$IneWGlw5@leQ!(YZ|m0xWqh$s-wNDL6H$NpWhNDfyL(~<n$O1n*`UUIOWI*FbG2+ldRE0Mbzp-D?;*"
    "YdZvo<De(YTc5iZMkd@FTsQ%UaQ%&520ahEeHY^@Ga&w%aaf`llSJ4^gy>|(k{?pcmwL7BrcO6{Fu1vy2d2`C4L;~u7LR||5"
    "aIeCZA$M1E{u<2@DZH&w7a^mQKg-A&L2I+KhX=_K+SxmyJ&W##ZgnbDZ_i_uJCC|EZ9L6Q{FW1O7J=b9#Al(A%(ngF@6dAo5"
    "U?PNIEqyOT7tQ6`<ue>puHP*hlh2T@6OK<dkuhGrahvi+Wd8b(hA`@ePc#lKGf3$-ab4UDA%15gv3aIBbwthd~k7LTZS~l2="
    "lb@Kc56J;RKr=kE4tWqVO86PMnu5C8;(OaQ4j{2EhW#txVjAP7lsXbzE$ERc$OIEyQ*ktA6~LMPfE*e12h{*IFlc;kpxyOdB"
    "eZ^}R%Aci03x5CKQ#1IAeX?jD@nCRQqWF>}1hm{Y%`C!Cn{&H>e}C#49Tn&7AFjSr{+FIS8bSI!w(%~ri#gIbngFqekjI8y5"
    "@!qUfKfBS^r&*C@o$#88sGE;_CjLz7ls&FCf%eC>jGVEC|Ce45t%snW_T(b<&p4iiHqoz=_b0piD8Pd^jl2giAL39}Dd;2?u"
    "5e;n{f4M!LZxu!FNPAyHpHWYn@YR_$#+^F-KMx`O9?yMUcNuJQaJ&-ZSq>CD!cpH!`X*?UhI~+3o#Zp0M9z{+-$<lh1+jkl5"
    "TqZO<4}fMo*=jaiZ+B<KaYi9jac#dwk4v=V~)s~X8^IXKT(m{e-_p!cg81`MYMxzV7GfHRn<s<E75#c2@iv;b}gSrdGskx^?"
    "1#?LQPYAF<kP}wiRLxP*SX-lJy_GB7;I4EXIlj-!KTOse$CrX#&yYfj4TnuioR&*Z&2FjZgH)jtax8)HC*03Dus@LrVoiFAK"
    "}__o%N?>aF0SGv^<+)5ySbVWTrk^&L@DF$-(uhnlMAipaoHRN=b!Gur-kA40#Mo5Nh)oICdVA&PU5-5(Semfwks)Rjl)Qm=+"
    "EA&CP@q8dybi`5I+KrqTIAU@;~CnqD1aR!IWN(U877o-n@ZpVpvVdS%5{xaj1{%<IOmccLPhEPs)_A0CRe>rJd`rwKD2=va="
    "!c$Pd^dScuM+&+m>o9yzdzOBTHGq#PBPiD>Bohc%ZWn2fhclF$ew)Bz#>GF~H~}8|7i%90FSGQpMIlpK=KBUm5g=G-5?0yh8"
    "rOMkW>9xv83=JD>~`AGHMl<$y{O8gsbqdHJ5BMDDT}FYarf*?R<NIYrI0?VjUADXsE7UOzqU4xkio&ux%h@>el3m^6G}$*S%"
    "o<G>2vt-$t_3n-q+}_=OZLPm?%mJN`#=dMcnZht>^fr?^oCZGEUTb2j18econk9@<_iqB1fk{ucgmjS^N#$uWaE*<4G#qlYv"
    "EoYVWGfe1$>=2+U>eB8A63PfO*8q1LR3coryc1kD9bP$|itPnsWYIM2;rX@VqBir^>DGnjA=Bopw?Mxk7ZkkQaBC!GL4Tl)6"
    "EQ;olk|7|BkW=}9usST1ypPsA%!XnL7d=AVyHjjFnhjf8%<6Xc+6$cj|9i0cpL-dy;{5VXb<PXaaeyg%2%kyoJwdvFwTQ%&P"
    "uCqv&P3)%uY<@jz?ZLSkIWO5497cA5+(}F^rHojARo*zCy=1H;`hLy}<?blN05AENLC}Ti04(9uG)x{_8BhZzESe4^?&CpUj"
    "^#cpNI@N0(GB6bWMKT}z*u%oN8Qqhr4PsC3F%N^f!?zQWKsm1C&b({<DPpnCV!6$LOj(?j|KK~r@+?v^G*C7hPo5g6Zv9@oT"
    "Vy)<lCvbB$@q@6_tEc&`T8?^kA60YJ@Xf=1J#_l4-cH$=@;+L6ptDt^>gw{VfGacv&ewKr#g(#R4b$U33J`W?`DthE8ELFoF"
    "%F4clG&-Tu7j>}MFSflAiW*&{`oqJ2C9i0h9BT*69xB4fbVRITyvu^MS^P$<&a1z$0IockTl<Q+Y)f$UM3{eTEjXUwV9;>=5"
    "rpk01<G(+H19+2AxuJRh)6o6thN0X#GEN3IITw2$h6uYm4cE+APF$`=Ss$ifU!2PwZ@@zO*oq(-SYgQQ0*RX(^X7VVZhwlEh"
    "04-yrs1lwYDkmfWyQbLzf^2x+<}BA0-wr)iq+>vRAyvkNhE(3#KCoM}*6Xh~kUbOwXL%c{3aeC2&0p+<C!+Liw{iZK;*V9QE"
    "|_3P(+`6a1na7cnd@S(kBiu9&g3v+mVH<5Nu6jnFq2&spxXIEs5ywXJ;eWe2f+~tW4?SxqxmF<%48AYh!5UhD^UbpZi`Hxc%"
    "^S1se}i<mG`qvs&QMK%-@0AcbvJFa^RtX1z~(!MwcSn&D4?sy24XMf(wQ?XMviw^{m{l)Gpeju<<=KCCb9nC9Bzu+_RWs-kh"
    "ylZ(&G7<h^2D<1`zC;eR!`fFjQkOLbAP*z#-yrnF=z{E|C6vh}rYCdG+zml&?W|IUgYV0GX>zR_POM&i=_v^4y7Ec`K-1!!!"
    "M=j#iHb1JylkN1EsIA_1*^ro2ChFV?=zv6d+ywJ!U8LKRKoZbI9f>cjOFm$VDU@5*X5FFOOaBLl1azmo$SFJzx_F)^mcklZf"
    "52*!QKzkN7iE(U+Layjg(1*ze`F9^!Y+~URUVnmFxUuNJAqjr{NJ><*VJXP~b~Rbr4@*=!R5c78aU_r{_|_i!m`&e`Wo#XW+"
    "{z<o^`q7#B^5#audH#1NM0@kZb&G_Qz!yZaM2KxoLq=a;Rg-(#=sjdE0HPjD7T5Wn>|@*rp)|-7|rVuXg<F7oN2FWwy~RN@B"
    "YOmz-TK4b-Uqa*C^|3_i)s2kX>@^_I}~G&rH>v))o*+2Wp+#z)On>cXBoeK=Bo9)YRe_ZbJm$7Lwqy!2t9Krd7Lu@XjyCv$u"
    "*0Md~gWh(0U*K}1FTgnFVOQWu!gA8Q;857GqgI^3Oq0wsVQFvNxc4jB|MUwpE{nxz-AH3ivw7S@}p9U+$uspKxoK$-<!=4I5"
    "s+eLqEEuIIQGOJf5{OkQt(#c3p6)14r#|e^*e5=ru6lrtavCULeMw7Mzy`8a$Z2K)`YU7`oVpH&Lh)&<oK;*eyitn4v?*~A8"
    "f>MLl1B9Pf;nEh}x9yk71d~JwrGcvZUMvX}N*cE^8p?U2>mLsc$kgy>-|wcp-1f=S&jlyd!O+_o71|mQWRRtFS^49bZ=l&<U"
    "o|#u9r@|hzPVVK+4&gtM6KqWZWm8!QR}G+_FlC)yOzXn@)B+xoPe})ZSEtAQowls9`Wwx4+Nd7JiZx@jv!kFqsJb1hb&e1nX"
    "b{oxGmq@=(gAd%P+fGIL7Q=;)4S2Zr$&4;c1%79tI<LvtC&HDOteaaQT)Z7)=T%!|{)<nY;c)PqX~H>6cK2QabU234`ATx>C"
    "NofD%upxFsMva=tHsWM!EY?LlW3<QO67a@2J$Dq$ba-Q5)S`w1MkBDy&yZ4i}9(W%|zVUeU+HIq*UC5t<OtZlr_`_h4lsZBw"
    "|MIMLh=Sn5snL3Q8fDF7gXGY|5Yw54HlI#s>Vvz;+i@i{a`3oqo&t-OpdZ8d>rA8hLUvFcLg91XHU=Ouo5{6WUMe&5uB5Kxr"
    "b3dw`x$1UeExYNkvhQ_=jiv}SshIiiwE;AA)dd@pE<&R`3;@;D*$rt1#v)QG%#F6tYwGuvuoxh`C+N+&jueD1p|3&IqI36zU"
    "_!=>G=Gf`BJJd;>YUURA_-WqsfWS&s`47%WocVbTk5M|d2IxfTQ)FnREDGj{4Fe<$(@SmRnY80O3~YuS0NpoXI-LLJS6?wb~"
    "3dt)7c+2lCj`a6cbsRmEUhCxyG6Hf3<}xfQ5G;bhcE1AYnXIsr*X{HL?XwI8iHQ0xUA!qOIU<n2WhWaLwT$>=;)a+}17H9~e"
    "RzZky(gfJcD)ZJc`}o3&CkhoI}Tm9+KncXX8<d2u-;!<%9qPSqYalHT0dN*ZZCmp~XYmo!1#I>TLS%}VnWC;@V%G=4twV1|t"
    "_1RE+Yu}KOAm5Rrb&e|C@^a{CR-Q%UQXbXqiC&klJ#4;`jaXr(aB3{b2<Fz+gqq<-j?Gn{3+npf4qwK-AUuu;QoEOX+LWIAy"
    "S_nS2Xe4-S_7h7-ZXxE;KzmQzopozKAqI9ZKjn-qrKPPt!Uv*}6i__qqufXiR)aec?TRT1pEj>z8s?a%k^29-%&WNwRHiSan"
    "70WA6`D5eBE~6!o*g~9BZ!rUKg(GEFhFxgfrc)SZKHP^9yw5k7(+!wF5^ewV1G<A1IJhx@r|gZyF$vyoatJbZPKS(6g`9!;U"
    "wVbUi;52PHsQb!aINcLN2a=PQ|X$c%NUEq3;6yBXh%WWh81ZdusXBjVEaiB5wsiuDoeD%vO3O8Ku~$ZMC(vW6eUUPZ0aBq0|"
    "G%fE2>_0$RCZ7Ce@Vx_|XVWeS!X(CYEGn(Sw#VZ|R%TcpP6DfPpK#yh1n7W6WN{XqAvVvwe2y(Pw+C<uv|d(H-ajHVrtj|7C"
    "|YCmX<d!yq%CJ_m{MK3*m=s*X_zIwTt;8-C1+uoq8LKKP*wN8B@QV=eFm9U7onTu?npsJ~GV><BqmOw@dEtCthvE202@$T6^"
    "<u_0<x7O{P`Tig@T=jhrFlWXCelWtuh{s{$$%#9naP>T&Rsa+<vw{FE4~;v{PoRr|d_PLk-rCygl3WfR)lr|TPIq3O6oH~#l"
    "w(C&pot*>9f}UjF-lz!azH<4d0o2?7#&<FhuR<vN1~sM*TMu9T+tfY{Z#>a?Qp^4(hR4G$;8-l6TQxwufr2<N*ZCHRE(lE4k"
    "^mF7p*=PPmO4Brv5d~OnE6a=~vh%Bb<;+w0p}7ly65RDq?)Xrz{!5`PisPs^p9+{y3d7chki7g}@0v9r|Bnkczi{b#mR3R~="
    "4Y&A$l>TFK~HrYTQokHgY^!!bXTcK5Mf4x_gv%)$jl$J?|97l0FsWB;#xQjoMWH6CEs_1i`y4AsIJfH6JW>kGBlz5$Q2b^&Y"
    "g>$dSg3S{f46>OW-2H~4wn*<GLR1G<V#rWoS`CPdA<x`)eGNpI`l;!K8G*Ueb5P;>}cefEt#`sisN)z3LyU}P5L-x>=VTMrl"
    "l{+<DR;(#-;RUXfEqU2I%JxI1XESPc3SznN9HmxW&Z&vLHFibKS~b~A<67ZDvBpn;3LEB33W0&r(-F73odM5{pir<uT7?$BQ"
    "m6!2-{XpQiRmV2Py|9!3@2q%ZzPVr-fJyzDB=J5!{|%b6!J-_11}X0bg7Y{651fsM5G<$J8RvN0!!8hlX^r_>PX(k5lN+=-U"
    "{V63AG@ZBwIX-49qACbIKG6-#Ln;`zxD*6^bZbz?8ousA6!9hK1Fi8#9jYV<#{kP->_Ld<^)TXc2%6cfT&I<HhTGr~0e<wLk"
    "DIL|r8}^^3`QnY}KA;xeSb+#|xOTQIN%w4z_n;sF4GyYPj9s!vMarMIv<fZ|>8$ZgeT@21a{HWYzcJVzClHyGEX`8o{yG-;$"
    "n-*csS8gKf`81I7nyPcQ|<|1aLOB@UPFw8&Ygk{3|Gn@c^=S0tv{cLE|_AwxTJ;T~HaNf6eQz`WgR6|PRyub}0azsUkKNFA0"
    "G>a)t_{6{2s926;GBF{vEYjD<uRm!I2r-nTJ`ST7U>VLaj{7zZk(N9hAJHsGu`KwHiSZgBtR?qJ-$_uTr<pq=OqIpxvH@lL="
    "A@<;abZ+-MYH6pGqSZ-{bS!+1b+lb%fgPek$^{m(bKo`^Vg^jo##@#KbGd0a?aFL!!cFOh`I$uH$MD=k&t<nAaM3y)LA=*z>"
    "fYcZ2uLM9`-xCDM(&PL?~@6Dqajs_G1kWI79gfLIwI5woRB6!@)mtdZ6MRHkPKx-{eGq>^kWLR=AyL1&KysTx7BN`eLkTQ>j"
    "e~sx--cSBLpkb!-Y_4ub=VobnmiaJGLqqp`KK{-w6{z{cqU8@c?bFcuaU5N=Fq{*@4qFk}a--Y#_WjCX%DPMBywF2G>yk&St"
    "~^M}U0XS?6De6n&-QqXRbI(&BA2<U6Z*{@?_AqH<j-;!VXk-dpSrObWmlMHX>N6k*^zAASV3*%}>@klhM>$UzsFK9%p5*M>;"
    ";<?t=T)E?720E4~rUtbEL%{wp6qB(yOx3x}nIy?N3yadnRg77_A$ww1d}-W5yw9mmO+Petc?s3IZGHj8X`ybErkpJp*8cl>p"
    "Qlw~E0O6N6T@$!Jr#JV-<>Vtv0l-7y0V#;sI9;Lvfq8S0sQ2{L{LpJ#c#`gCtW{?KBZ2$QT&ekw=#G;iK!SK`_esHDk$^@Sz"
    "%`vOmQqQ`1vd|#gMaJ^YhJAHmnAUv*p;hmGzJ35oDo5W@3jjLQDcN(g1WWY+YfE_`sI65w5K^#fX*rqkef(g#|kkG{Uu=98J"
    "|%4MKPLC7UHME9c9A!Mi8~<etxA39+R2qdRL|$}F>aLvP6_;g%i-McX*>&%wZtYgGH}*o5H~`XHLIQF?-0$4;-?WrP4d2K!4"
    "vmaOgoo&R#RtCc%A;Y&N9TN#6!({D)7dILGpeVe>K52(cPx!Ye5^(JCo%XI&YI;AAPSVSpFJ2JMb{{`dLvh@>EaLN8a=@_<u"
    "7qKqdn_{x!2LB#Q(6uyTSHKz5Ah95L1p~kimMVbHVO(OC)KL)jW0me_3wS?VVDdqr+xrBru;gbVktuMS=5@P`{7Q{6;A>HW`"
    "b*@(6Kdl+Jf7jB3(FmGtbX_|$%v%Kva>H!6@@fo>NFk&VTc*xuU}$Xj<-+1R*g-ZZAqhMm`OiD8N$lQR~DrUgyuoF5*?cy>I"
    "#9=961T8S*hEGs%J`7R>qPoEhKD%Voy@#xqFZ=hfUntv+(dRnp(fMuXsU|#JBz-K%R*y@zrYaWAVV`K@~FH1FRq1fL|cy3l}"
    "3*N6^)%IL<e2@tthtyh8s$N3fbz{l~66M&QgIV7&X2&|=H8B-OEMOb0P+JZ+igW)KaSzc~PXJ|%pzsCY@gN1#DHz1KQR!C%4"
    "|cA~J(eVH4247b&HF__*@Lx+qPjTaDPGJ8a!Er!%TzQ4evQtZoiW{&0`=mG=iqsJFG-X~fgiK{dBQzZm%{AzYdrukrZO9`rx"
    "@ncb3{k-|D^rh4WSh<!E#K5~=*m@od{lBaHu7J~=xAJsWH!yNiq*8KX=xFpLSX2B*DswXel~oW1CF_%1vld_KhIn1VFsWY(1"
    "QRF9i{WayV!T$o5@0&c;)eE(l7Z?y(xhredygD_5@+{0(wju>uj7f4hVqi0Z%|TR*Z_TM8hCfEe&o~|;Oz=Ux9Ry)v`n(Dx{"
    "xKqzV>m7mIIVl;Q~dCi|O8b9I5kV<Rdq%$Akl(T9N4QpQp8$C=0jX9qFQSFF^T<U{8+|kjEbTUGEw%`7}$#y^0^uw=LDfWOo"
    "%#gOeoy-9-JcHp^Mvk)MyAMfI#PVFW&<TR5waITaEB1ZfKt3Y$ICL!o8%C_>M{7QXlF%~7dstUY(9#KK4+0k!621@&;npilY"
    "Vs6jj5DwI|GGmLS<|0j<n)08M?ohfM)szYU%;;8UG+`h(9SQqfwtd|A@lR&s6=sau}r*V#wfw8`Nc@A}Z(03Z!Vm{&Fe#YOF"
    "LGA9A&1PV!c<qg2`t0MTD?F_5Lz<F67k8C)b_d`4&;u=9oV0~e3P~B>hX=uSROaY9kZ&aVMlj0b55qW+gW)mE$UoERMb@E)E"
    "b5wZ@YVR7I@$URsvp7;tT79rVGTic0j<uy6`%-aa&|1gB+Msh^VM`l4rQ^34DI%kMoKbOkX(X=2e1=+2UCxYXt5)TP^F_tl%"
    "2|A!9UnhIp&g5LzH4~L+4S<KnXGXRnbn;V&*(^I$FPjEPrZzDg}H2)@e&rsGWaF5rQQX$ME)$_wgg%x74P7#$N~wF~5N`u9*"
    "LA&~P4738aHpVc$z36C+=xdcqV=?C(7dGb_J%USqR-?ogU*yevm{TWmIPw0?rQS@~2_g$@-bgdkuJStcUMDKeiJwAZC`exh&"
    "wX6<6Kf3Ij`JMdlXQ3(n<q2cf24dME(ueDUcGu>7;U1K=IuwSGIJL3>UdmKL|idiyuQocee>CbI&8@l#p5%p{u=V%71pV|4v"
    "3AVLry~nhr7IbDm7m(JVtV9O^jMGN$bA5ma@V_O`cTgIzf$3m~%B3TDcS?8!7b~Lkw}0Pki!))2h_*M`Na6=8YtK1RI@?(au"
    "dBMH66184Sx}lJA&G#7{o3BJ-a|gd^qC$Kj9{ma-EU|~DgBy8{1AvTPuccXA3b-Ir#bw=_IKNL@b9^7KvAb~S&LTUr#&;ADJ"
    "AOq@$Ut3aXx6PVzhF(6t5JAg%NF#u7u7|WH-XPUi}|sUrFPpO0=m>J{<AVTsxf~+G9Ra>-%C%4o*@LvgpZWC?AtLrmBlGs0`"
    "8za$!y8rYq0;j~Jgzr%PUMJ#}%H&?zDsY2^*WbQXTUd;4P><EZuS*v<1lQN!<in9@`R1NbI0b66M$SO#;F!l$--h<YztL7!`"
    "{V4BRklKIM&1;dHkuf}35V!Q^HRi<U2v2}>9er+vv;#9bLZ%@vtm1Fmq!glm7hx5UHz)tSKnEj4P75}97k4T~u#{WuUHa+kl"
    "lPX(%iP^}a>=lFs*WuaAeYlyJrQNbXhlVYwu$d%GUihjlN^N>1b?zTmDc+<EM>3@T%Tg%+_ky^f2E`Q%qt@W1pTJ{smWg4{i"
    "kTaNl~?~orE#J{XXKID>7{h<^GIG1|EoAeTXtcEG;YG2)3;tyTe^fDw78w>21;JNoY_RcG_KdIg(XW>P%D7Mig<};m%R#0c("
    "%z18cfcfcuaBmhS!;Er;EAFCj-y#)-hSMH!@JOJJNI&RSQ(PxiWyCen1*}__6BTGb^&V6g(iW$hE-7bncHs?8Fb53+^<dytI"
    "0UH_wtluzs$#BRq_-lCx7DWF;nTudCFUh!drARRnG5*<bmylO2<sKYdx}Cw`aS;n;V`0xW~qXKn;pM?QV}?p3fO<^c&d>m^J"
    "0?G%W7PURyqG3j9x$A_kMnD6G#)IrcrD3Qg_ui7=pCEkDVFq3ck8sX@wKoc2b7oI`fpV$2q|Eq)02!Ca{*vt>NT>$l>k_t9c"
    "u5_mQ@W2s31X{R~zg9k)6c!dMl=-w%53G?2MQfC512kW`vbfrgVO*mzR~$)dF-TEIOJ<?Y=~pQOe-YH)YN@c}qhwPqR1#zss"
    "=We3J$h!^V2dWn_kJ5}A<qjO!3~#%uI1mw{`}qC$A@0qxn<3Cf5O1O(_&N=dS7tN_ffBD__bKtm7uP9SMnJLBwP(p%R9u5K!"
    "N#<o$oF6P?|a3CplHPg!v?`3@+6`^7k|asd*4_oEGlEY6XM1W0zqCY>37^kG15Lz_k1lD!wISe{Uu4S)8?S5v3$#SJ~_YyxH"
    "9HPLjj0P1dH0W#xZYK;5e^j6rVA4tf9)(SiB>{2+mfj#PJpbAANt0uj0pkOzy(h)r=l65+cSzxVfk;p;yqxBtqBBNeZ>(;^x"
    "N;H_`M%E2rWQ?@V-rcdF%*+>0o2$9+(Hv|tY`V2+rH^>)1=BCNaWnKb>A2uwWO}Vbq{O!uS00k!2CVvRFlGp=g9<}e`Wd(h{"
    "w)+D$++)xQz?6=HEiZn+hFcA-q;)C-Ju(gvW@cs=XUmbsBC;k}MzT35Dnnb#F2HZy7G0nt81ls$pfIgf4Hw4q?(r+$c36dQ{"
    "puAB(#ADn9xYmI2sZh|XYX}F$AN*)8N7@lhn4>g+ct1&;v!UJKp_D^pA}+4c$Vh|jCg8ttm|A3D1Cp|ugI6FD!7`I#Ohk+6K"
    "8c0QH^B4<{F1}k8Y;>99q9r!IJ;ER6#a5Q{gL8aTe3TP?Y@Oc~mRS4Mr^%3--0(4I^=;PC8P65U5&@>~`kM{*=iXq5f>>WJg"
    "bf?ODzEY4yS{xSdtu0-bjm`Vns)`xPxAKosgxxpZ3;c$B(UhDj1^;L`R?_OSs=d<Hq+A>XiMnL`W1213dOI>h{Ms(zsZ(7)_"
    "pF=Jk$BbpsaiC&>FMY+%*R0<NSEIBXJKt4C-i7fn+wUXk|9rj&#en{+|qCZ22v@<Xq3QrDMawvt<C)3Bq#zl=&b%S~nh?LOY"
    "v&gYG^s<MJXI6rRm*&iDm1=ED#V;6-apMao#M&Oz&ckMNJWcqvi?fb+L28g{djP5Sy>Lw<Gc2y#K9-2Be|TiUcq-XVvtN_o2"
    "{une7tfwZzKX?=jliDm9n}owj~(<PvXhK=N2~r=!J`F;9)TX6xk=pmoSwCcN;;%Esu1t?z#Ku{0m}%PGGn9avx-`L{WaB?Lp"
    "~AMh73-<az%L3V7D_8@(#_%Q=@j7Aovgz4+dJp#>RqGF2qkV9X@}047=c!eyKIhzd+C~C&(c9&h_nJ684)ESmdNmA;KS(v%4"
    "^ts?YhAS3*92o)U0*U@N;4PH_@bk<4)ZG!FfpqXclO1^_^qlL%auTN(|uJR`X$jVMb=Z;5&&DL{BtQ58ky-7@V9dqQFo+7u6"
    "D6w#H&HQeCqXfQ3ThdBuMqvB#egRQD~3OtJcxJA~E*Ls^;O*&rWv7}Fsi)=9C8$U#}zr4n9nyR>|?}=`X9G=htC#Iec`W&v)"
    "k?BbdN2hE!6?MFqdq6lgS9Rd=eo49oZsW_<+Y(MWq7HqpV#$hd-$u`3{4sn#E#wlZeDoE2vH!;d9Dpe0Ex;iO)99slZ1eqKZ"
    "3Wy*#vW>Ib8Np0t|who5sskweglVsrH^{aP+T!{IA8%tTs3W}0fo3zV`8P=m<)+eim^i;hq%ER#{)}cR#-ZVz<u2Xlx+`lNZ"
    "A4WC))NMNbOQl0Jo*P!4bW^-o27mB|;v*@uB4}uqlRw=&=hg_`h#{Ui|;c#1>A3(P?~ErZ|Ft8ChcXMLohynr%jIN%X*_AWK"
    "RJvI_EBP8q8|`Zf7_KU@)<iF&S(yzJDzAhw#a`0IlaIRy1qd5CV4MD{t1AZ)`57`R+aM*6sk_-NElpDJA@hyrjUH{jrl_@bz"
    "(_Pz3j9->|s$v5S?%{@!gvVPN%5;wGEHP)1rQpc7^pa$1s+C*D0gkRdI-}PzjLtkhw``NN9NAaSs!2524VkG0$dAYmUDFwn2"
    "d{dCAvD8{~<Fb`tIhX3JQ6IdtN*dh@*-)bl6UvA>nWFX`&fab*03gk3?inWeQn+ct{WfOCWVZhGLEpT;xz>%HhB~jblt<|TB"
    "15kt^hWA5<pO@~)&S*%?G`r(TKPdmZ(M@IEB=avMmv>~HQ0UF%PBC$r#g6e5g2Z)`Y+8QDxh^Dwc4F|g5Y4FvI6p_ji-cUpO"
    "v7F0nI9xMb_XQj5LfEn><W{Tiu!rCXmQ<Y0Pq>LBSKXtFCtbO+##Wa2{D-@-uJ!FVm5|V{L(~1g%6vg68C*fw2aHOTdKB9nc"
    "t(*;M9DUUO`xs`LGYCG&U5`uN>R23jxdby#Mar(&OVd5IWx55K5v)3G{<8ICNJetgg9wSBSZ48u8>+fFXeI0?b_+Lg@SXG(v"
    "*8u^L}a?QQNm>#U1C2Nq+9@~J!yNR*N0zm$d>l6cjnI9wp!yl?by|TEE+<0F60fDKe`Sjo@!3f&-g}0A^Vq%SWMXA@C%*`P)"
    "sF7U`8tcL@q_q?vRM9!Kq8nqGbL5c=7?<Zcuu*C^D}MeM^w)o>6NM)=w1TZJwuHhjFZU+uf}d16?T`W)oagY=P*)|QpmLjOh"
    "&lEjm<_OwnHJocsB^?{)=sE!8%stq4F;2d{hugapmTvpTnbvwvnFJ>u9zSl??0Lz5*Rh_F7c+wSJfLibpgF6wPbyEfBkZz72"
    "@%=I>3E4TDzvId;gSL>~oYwBjG%tlsTDe0(uzr@+p_fuXl06i3Al^+^m*J-4go+U#$;h+gV^}Jib;ByVfiL+%f*t<<5#nmrU"
    ")q?$KC>&YBEN&gAwz(kFI)w#N;~gOv0nZ`Hq)NSuBRj?L8ZI$R^ve@mzqlywvESq#?@h%TVh8=RtLB;pH%bP)(PP#S!K{9_N"
    "@#`u$2)D>gD;#(ILc<SlnH>nsRlvl-0mUeBscS|17;uE<{9?7q)r{IsYMayDi%0$r4bn!jvZd+^E0=w@Z-n#>AHfd$eC&eu6"
    "r|5BteTo~h2m(off|oTR?fk-8L0sPderw}bC$D(pOzxCl@U)PL&d=p4;>F?%M+uZ9?Cwh+F=AzarpB9xcL6`QXM$3+04y%|b"
    "6~pEHnAVs5$0p!qRQwnJ3mH}>}r9HYM|sI=tN*t_KyqX5nUO7Wk;b8M~0?@1l_MB(By2`B2ph2?F~?;Wtx3Mo|C=lyg#SU<l"
    "L@a_wT3#X*^n;f$vV$-l4y-OuHRL<D$$HyaR2EZq-kePhD!M@0cF_X}|5mMP0w?`=xE{Li!&E23NxY#@8{q)6jw6rQm>PGSF"
    "Yo3rk+L)rGxhB@0My*<ZyeOV&@p<YX#%3*3`8a8n(CyYiDCsQd5|fJ%ZOf)QSO>K4gEdt_o#mK#G(gGyQxcI2T8urnkQ`8Cu"
    "kuv*f7Z7-mfEoR_Cu2AM^pP*SOs1Yt=&}U54vqH^Ci>^9xr*a1L{(aUgg}{>I_q9uarxA|D_5bS5L%;AeO*GbgshkoMT3tm8"
    "nDc1p+5_d)nBgP2Qs#uOfp+C0OiGT%O*-<Cnf;fGL3fRJh>uQh*h_K<fAsh{tfiS9PEmvOh_SMdO`Td+CGk4U`Olh`+oUJ)T"
    "COi&bmdTW)n|Cv{ltyV(?EkHPP3(<nm>P>m(FngOe~))4DXwl^!c0J2<j{f$B<I26<e<!9B@8MFG@Qe56QE>+5YtOXCtL4#k"
    "(rUvM#&T1|clEIaY)(u>bC^iEPaCoq8;5NG|W~27HAepUvJ_g<v4{x^RW_`2jUaY@tm#7QsH6Bqh?kL*G#L5`#JE8K9N(6@$"
    ")F{8K0?DN*7si^c9UM$0gi^vgnR|AW8>t+<wz)l4^i*uOfW&yF6Hv^_&<`;W4>zXR0b*U(V%vKGf!TOUH+j9Hb?FLi0~!Z;A"
    "odB^|Mz5l<-!atlZDDR;<i)S~bz4|V%i;h{NfqF<r<sLfkb3f|o9>K$+O^eEhxc!2jDY0*5zVDy;flAp`^UZ{zUd}hJpb9R%"
    "btxSrcn#(U1nThyu)5$)MI+<zh!Iba+BVzzTM(SDd#qk1mWdXr+H=FErpCG2W3SC%-9FghwpS;gaS$0%{f3bpBd*!uMK4@S%"
    "M2+|%TUOfh^<XA8+Rq)2#9md_Wv{5-A+ikw8wjT{#awZ_^fc|DPsMi8q>OX`C_zpz~%t$@iVB9t1dBT%+|HW%V&KQIaP7*+b"
    "_};HxUS7k!0$cy0=laNrAW(GqgYIvbx{osjjc9Cje(_=Mj>8rx3C8A~0oQly+z)P5v$_XTpO6B5zuSJu1OFYcZ2URGT%xLSF"
    ">sUEap$#gw`(W?SNgI!yP`Fh)-nACS%u8(HzB&!qeCQNoX5Bqgf6l73b0wX&zkPlrH;aN{Q&J+Qw6oHWFQ=9HP|EI}>exmZ!"
    "G#Ko}W5~p{mv9e;Z8lm<|t{^6JKgk96m=69Z61t-T7LgTLcfXsmg1_1vqn8Uc)b#q~UFcChh4Q7mZ{u*VH9FUy?n|`d@=KIO"
    "w`AdT`H6n8=?#+In^PBv@6ro|<A}NGpOWZ$v0MyGq;*t4Jus@i>?FC$(;P9tOX%)(U+=H3bY}Ih!+UwGk2a)rdENgfRXI2!Y"
    "9v(7spTO#%S+>ER3F!7p6It9hms$dekK9ZmD+&_YQT~Y{p(wzg7*T(!@_s>L*Wt^vbs-Vytdwwn~%a6-5#X9f*}z~>?nrh@v"
    "EQ`|9RAc^i`JRt`FC;gd$}tlAzRO$|U3eq|ZN(Raw8KvJC^xJeq<WOjX4{Fu8WE1q-A#y0{XFUVkdGU!+hI*>2dvaOoo+_=B"
    "zD>Y+<(`ZzIzoX|pb{jC-F0SiE(rDG#8?x=Fp?ysEx=x|4_H_2?_-Un#Z_ap(1AJbXL)ljB?mdN<cYj}Cp#ahaz-JBY!6b%u"
    "AF8(e%^fG9z+5A+XNr}vFzx)kr-WiWWRiYW5&@9;&qkl&ow_!*6#dmgjr3L01A41Hyd_(2|zs5brj128fGhd<^fYk`#cA|-{"
    "UHhg|m>O6|WI6iBtAsR~J;xncJly0mSUEMJML2YVh~xn%Xp@m*$e{L0=J&H;$zjquR5W;)oe*>meoq_D5)8ZGlKrO20<m8J8"
    "mO(R!2`b$T>oD?IvRQ=<XVLg$_kc<1|U?HXK^8a^|4lk%fGlhYyZo#`p4}-SQHbO2FsL7Uk^ubwIVY4M4STvII;`pk5p^iz_"
    "}exj8AG{wrC(%xckxDKc?z>aJTGMoM+rn)dvLawUt#V&KgpZz93|f7qVTxWPV1<EY?$Xt2cQtyu4X7bVPYld3$COSh@U|p@n"
    "w%eh^{#$I15|bc@^q6XV=i{CAq|vf~NUfyzsXR@EE#mGV&6yib&!Xq^n}vYRM=ZHP9_L`oYv7)DN+P<=c(Xa7uc3%$naG#^q"
    "vp8(<}=dq^w?qVnG5e~_rN`{$CCU2mA*vfYx@rKC(on`iYlzJfVpHbK%*4cs3U0zO`G{(oq@t<Px1<D}v<#~zAeLE3!7>t8M"
    "RD3l+rYp>##}DuwjZw+<aEBtf1pRF|RTW+Rdxwqvc(;tmP&VN{2T*%nqv*+h1^S<W47qzW8=z1VWVyyjjpn92uwVs^9dNXfh"
    "VBA~VC<P4{mQ4%8m-U;OQ7bw4GF`WEL!AN5Pgev0wcfNIWj3pUt>}*F)J$$v8Cr69_EzM%=W$;g7yC~?OxuEsPZBXW4`FN1("
    "HyodYip&y|sJ?(#n52OXyU-A~ynOAm~crlHY&oH-O`L<at-Nsu9^4jY2Np9>C{c2kE&+m8C6NKww+)!)N=RA-ZGfgT_hkXu-"
    "9tSE<ULpsp6bdgvSp&KL@Ldn$EBLX{qpLd^Ns%?=V9ePqW|;2twooPTpp(tr}pnYyLmXO4vR`;fgTjX+-U(!-rzs(oo+jrYz"
    "n>R$1UlWu!3vKzjzBW~hj$fY<I(p@SjYCO-zzSufbk_s^q{&pCZO%e?6TGD=jQ+kv*RR7hQ3=2Z@m=WTC(I?6;pe=m{8Sw!k"
    "&sQ1TY0G9zb`qpr??`qU6*)_fnYmEajj>|-MDL=#g{6L5^+d}^gG@ImrO1_8&c){H8Sym@LtmeOxauf1s&aRKzLOAqw2u15I"
    "lzmSHLdc&YCfc%7WZG+{XMwi@vCPikFSFpv)jc3Yb;T$8M{B;4M6i2x-32<Ci~U0z?*u^GCI-nEyVH~S0)%CR*Ym{tHgn@4T"
    "4|ESn^2u2Y5^;<-8Yx;+fld@4N}ux|XrrfEDPaS)|)h$rUk9Cv<UB5H-LdLZyV1{?crmvdhn+l3qAaC?!ic-qHs0ci1o-|5i"
    "z7hnUCB^Njhsxh*7D`^o^<XX{gS86hvPE1BJJ3J0s?Y^ut-mz&^!iRPDZgsKRV#|Fd@Gk(xt`xZ9IXHZxLoN!&`@cbhw(+`I"
    "#7-WTM(QFBsDrXH_&a2lKiuhWd4zm%df9II>v%`}xf5)~kz5S<=N)AI>^babZAVlgg%f_rKpX%HIg(fq|<hK1ve_S6XvfV&|"
    "^`jyKux+6abxX9t7U%NqA<Qzc9WOVif;NJ(Gi;=8mS(JmO1ImltQ037F!N0oO}eza!~szuFkIT4h>2@wv#rV%d;9jWJhsn>)"
    "SHM}zI**s-eN4T<J5u>SvhI=U^ovmlGX*QP9+cu>(jYV#Loldqya&vO*mNwE(W^hYjafmcNO3M0ZfF?tPhC@Y(R!HH8))4fQ"
    "S^{b{3YzheS|U2$91zr&HJFAk`5I@RBzuP0YDZD?J1ZY$=?@Z8{Qlp;NkC{EO&QKIcUNw@?liWEsxn`lTHwd|l$-<X@yCrD-"
    "abEV?+u=PEXKw5oWD3Us!vGNL8F)QanUfIZzx1yt%I0fHh~R*$4wzpwK4hDygb!$DL`9Fex)s<^SDPnIcUwT<K6%s+3tQB4`"
    "Al4V0jS9`!uchN^@fuffKeNfp}nf|pj_{f}k@56(nJI(=+T!&661)ZWj7WIXj%a1;29MvBc7-X!U_VB%qu_Pvk;h&{gb3`q%"
    "Zune<C>940s)MVK?`BYv*f?c-a+S>BlA+N~SxGPRJQAp$C9sLLgi3^a(}xV<C2teVZZ1hcva0T{8#Z!MX<XJ$sh;Fc4Si^|T"
    "@SvFo|XQL5G27PBG7lJppeZg$INOp>f+EgR8V;W)g_sBp~m53kf`bCO5GruYGy@Xd9u|hvMauDxG~iK&;g*DV1;Dlc5?l2@^"
    "s%wrB=fB^=7%Dr^Sbsv%*zqY<5deh~NZ7NEOl8(nHjE@Btd`safk&x!8eM0-E|uow4WDBitnCYTL{-u3?YAZjXdc32;VyNW;"
    "MW=TnfvBb|+xSnyTO<+&m~$;!k~aOD<i`DC+J8{|@W(Azy?Y$|4KQx`XH$>H?z9rFr?E`Q-3Gwr%Z#^#9ZB%U8&wjNroQN%~"
    "){&Z?_mIIf=$U=&ml_0odN4=}#^Qt<hJ!g%@o|5IlZJ*tLPHA)Po(#6f6PuH+%Klgw?F(RPxf`-ou{2OwOPekcG4)9OL%jL|"
    "f3I7*Ci)3-2_t=N=@Q7AXScwexZERc0aHd8G<uW33-gdVn0$BZzdpjXVZXI-x#w_vSbn9_tai2;akDcn7KK;uLVm$K6gEpoC"
    "_@`pxFpO#P~sbs-}gG65&|R3hj?HoaA}m(K>+Na>A>sHK-#}G!?7Uv--bT_7CCYJ_euD~bQYtB;bie&|3!CYHgh%N<=RI?&A"
    "cpFkya`SH9S1W#{?Mhv47BY{uq}lQSWiv?XaE(T}+Pper@EZrnq7Xo&52;WjWw_l;307<IS8kK-63yJN*2~21Jjd72F63Nr!"
    "=Wj(Y8eY=#XeN1zxT!&SK^4=SQmR7{^I!oKH(>(psxZed4J!m723=D)S&o;iuD&3BOh3)x=-IIw-mN8A!ZvM}0Qpt{qyCi(0"
    "4L7GKg0Z;;$cW6=Z#|_`a{2sQXUb@XkMp?prZ^T;&(aw_2sMJatz}-qa8o28miKv0Er1@MFj!U>rWr^7OMn((|OSu^Q?NEr9"
    ";=y+ri<KXpWx=(xXuNrKd*phUdD<ZCALmG2OnP0TW-;MBv&1`ZAwN8RPucAoBQ!F&g|q_u%$~_GNJR_y9?IPL6RNEH&G$>&8"
    "z*Pfu{&>uc}-<3KbfA2k{^j?U#BwP2|fwn3d>_VqrPVvlUU%!*|t#;{4B72#Y4jmXrZZ_CtR%=d;8tcTrPNF$*Z4B|L67~OZ"
    "&YwTlMa4JK}28i!J>YctBIz21ZYc4b?ryt?fat5D3gI-z5T)-A|Vp5M)&*AMZ(*uT)IwHbu2)hv&3pVv|bM8EEpkC`ihtqN4"
    "Crz1F?6vNBm6m#}_wtC=5GK(BcL?;)ATL-GN(2Td)Gt@+sd^)B_Vbu$Vs3y5%-fG~zj(zeF%Y+*nsBWyOPT0-*%r0yq`trF&"
    "aXX^~DBNnSjm?c0F&ROi3-`sZ`V4e>6hu?fiQm7s8he46x=ukPZ{GG3>bS7$Q2p#CwXF>~J=(arEo%F{aEfX`|!LbEf&OVEs"
    "PITh_jIBE4yc;b)uck;IeQ`dk`7I!qg^xwWcfk2PZ|~#5#CT$g`NMa(?ZRo7J~cEfjnN!bet#w7dY}tRP)$Q8W*<aN$1m3Br"
    "3HRhL#Hv`W-H=itG4sO&0{>B)ubn9Lyy#y@;-Zgy7P^0aqYV*BIB>i%2^>)R7FK#lem7wB=O=Kam-LQmme;`g~eyR#Hz3KDe"
    "jN<0w!8I_|{1m(5EYIu001R+7Pk1ZPUT^3{or&#sZR#{NOHxx(wP6#|$Z#VR%eW=dmYFL6qbW!udJ0n}R8;qDf?ql!)F}U-?"
    "vk%rM0Kzq>#X4D?GaVrzwzWMUs@N`%gEhO3eRTlI8j7$~bbi?U!wt1d=7Jkr&OMo*x~k;pAd)utwp37It3(D7pVc|aZJ$4dM"
    "r^TpB7%=x`pdV$|RqArCkLmvGcxFJP%p~0ca7seRb7ZrKEw+^2gwOnpWT;aXeTnw>8mcfx)66pI11J*l3$Bq(;zGrZsDOW_*"
    "LVEt84lR4qO*Ko@k-0;gaRZY_**9cMp`dBXxP*{aKSA~*U+*#Z>LOe8g^CTlFJFa%B{VVvE(r+#2skN?fG&$sVp_WuXpixXL"
    "chtO3*wZXBPXJrxgFbMF2X1$432JeFAq0`?Jy3PR7DrVf8nL;KXMkI15m#be<+q=*XZbl=z_2!u>E@ok(rkuY^&!fwGMFx6a"
    "O)5yeyRDQn@5Eq#Y5ZsT>ug9UcnaBYY5fxpz7%(DC1&`Ud?H1l-+0Jp1K<fB!-dA1zu--s=uJJ+YWOR%=A}WOA4za~W9sS<p"
    "5C2#0wD1Jq}sa`Ng&VJ}<UOs?}h?i^3;k0E&!xU%?zHRNiJ{{quM`-~C43P*Ap?5b@0)I+9-wwr(ysMKdkilNQB5@HN7Kk_Z"
    "%0GnPbP7n4EDVUFgZ293A?qxK&kiLA30Zy6+g?C*QM!fRe&_5QEAH%oJ*t=nWxY-ng|3Q{$01wmaQP^-<H!uK3FAvMtOMbu}"
    "=rSImC{7DY0(j4|>+ZcJHg`|Nag>swZ+;aTVkY}Xc!kvz2X~F8bSJ9ngFoZm#(pdrhfv^c0u!I$4#DIFfm<BxP7za>QdFWT9"
    "6%rN7oGoT14cGi#zzsvZ<sY^X~w%D4p$##c@G{+uSr+HpGFMEM_tzb?5*o<8Vx8by|oBfN$Nl_UCcm3N&^igE{V--&W~|1+O"
    "J3;7@&%dsdj$igZ}IVuKk+o7!WLyOSVnL7hFV9Iw`saiJEyxyQTV)&juc*Tzzu-%?yA=_p(ZqswVkSY`|ts@5{1(MCNvn;>x"
    "deN4<0HeSKYgK<Co0Ywsd|DQdVsAMv~1Z<E7*gZ+l9EG&v9D-9t-5*jrqX@n49&b&ALb-l(pYGij~8w<{f1JMNX6UN*c)8l("
    "iNDG~{XDglkP8Zi)-tx}_p6e5yqOQ&g-^ILB*yop>%e<_svopAg>baBv<Vo70ZrNLy*4vs4=fL#6tI@`&rztv>nZTHNe@*Gw"
    "dCz*qd#=Ia*RJnb&BwVH4DH%o=wtL^HgK}=AdKf%fujTC%m^v}R?}Kk)PyT5xta$H9ZdhIro^ETC<x1M^s#u|B|&djM+PKO+"
    "9z#bDR_fQy7RJ2B*~m+tuu8uaK`tk+3e|d8_UD%PVHo=b<?cEwzoY>Z9?z~j_C81%N;XP=JB84HNPCEPHsLV{boP=c6=x*Fn"
    "~;uJ+gU1Jn%IFYI)>+w#`O%gFjC*TgUr_bcgyy$Q;eZfWE-j-}}vS;EX)uotW=<%Zlen(=i)Arw$40<<iOh$W5r?jSIK<L9c"
    "joQl+H;!YB?j8z#(E`-krt<`!Q1?Z5^{5Gl_W{14q;hvODRqm7tWD3Cm=teQuzbq__q6*ET^Z!UTscz(KN-S21`X+@*!U;m~"
    "0e+j?ES;+%4U!l5#m-^c*Mzkh!{|fMY*Pgdnk*d{29Rt_n-eVFA=0DX}dNn%e1~!ir6vE`@QK)?1L2-9W_{ls9-|GPYZUi-7"
    "_GLf$HK<juqJsfGb(VGv<lv3+5+<6{SB0DFf8_wO-n!UG8FZ{WX2^q(9$UIw*VE+~m?`~2v&3~|ZkQ4X$D}0xs6Q?bLEm-4K"
    "qb_CvE-4$QP8Bc4o=qOf^6F5ab;M?6~z%4+0Q#NgBth92d`i<3Y^PqeAzfOu^nB)oS(`AmJ!D7g*Snhz>arsl7Rr@*Z^KBM%"
    "<9$BY;S80G&a24DA4!ide;KV9`cDb_$P~4NAXSEq5S~8ECnG7_$aWE3W3Bx7BU^=?RxCP>7y%+A==q`I-m59yC!KhVZWD!&F"
    "cw?VJ(j>4ASN#TL{E%v>ZidM}xJh3`|VWC9)iiqe%*-SIfu{vd-2S^%mlR5kL`#_yrnu_B|nppAW6s0FD^8Vv~8&P`f_vGj!"
    "iDDigQ#5{|d#|?ac!}gX3&JBj4r=v{=N4IQP#^xf9EaLD89qQX3QO57@2NLfYLn*X;fj7(ZyPCC!93gDf68Wf56gld&Fed_A"
    "toSsT04EZAi<Qkmonw|BL)T;w`=~dQ=C_8o&vmzt__?JuhuL7MXXj%CX;U`~#)E5`<<Q|O`oWBIjxFNVn?zY>Pi`<nS+nS+c"
    "P4yC`JPFk2o(a>ELY7Dp#+xq?bBu-keTLPypz&hv31-S9j7E+I#z@w!oTAiOCpi?<0w9G+U2~(D3q_)!x8eEMd{203@7a1El"
    "x>_WE$Ms)cY%^JX?7843>SUt8@GDNjSU7i2GgdEG5k5ap6z&K@JbBvG;-P-|0LJ>(_X>_EEK5Ra!?LpS|k5{aglCE&RKTQHZ"
    "KxB}N3gO>N);>!UM;`a(m*nLqU&drZ-&R0d6wNpCS^^M9Gv){E@Y3dFw8NUL4o<e*-kYnjlQGuH^tQbwIu_O=YI$6J4M-R7>"
    "mq%*h8>hhEabD>>9{i0ezF^oI&;;ueqI$jyavsRng#VwsSCza!7A!pftfl*Bnkut~b#B5jrpGWeX1Zl+eetCoAaey0KGRJdM"
    "L{mC2NxumGdmYvw%<>Rn$Sv`pSXSkpby#~IgJAJ7%p+eWDKOisLtT7ug(mw+oRY0@50)LniJaO<bWWlU2d_Dy@&Nr5mcPC2M"
    "}|CtZC5Y^(dlx7D(WuU`SG(S;|`I+u8&U8+w@~D+N{yp?=6n@pO4L1lsi9lcs<B&8ubuwe=LY}pA2fhM=T7%rQJhQ!tX`=jJ"
    "(F<4Nmh3XYsvM3vCj<Jj^AtZr;9bQ?+gqaT^LJz()h$0?FB~&=A{tPct;h<2YJ$y(`0dg}USr>gTbEQqO9+#Up1N$Eh%n-Lx"
    "_1&kh4R9ik*kfb=Rphk&yQK0~QvamAL94x;3dP&_<S>JwdUE_T@D0t=iARDMDEBSSx^B?~Iq#w96th(B^h_c`K*pCbKL3#TL"
    "l%|(MR!4R&+L7Akeoll$7#59wMOt$3@Uw#{by>^{uWH^U|W3j#4Hw>0vDwr}piXWDK=sSt2w~IzvbiXsQ(bNTs8**l0#&yR{"
    "{8jqf);IwWfKILF*H4Xx_REsr{Sj_BMvQmax)BZw>0lvI5yS<#1J~hj*2nxvU?z8vXLV#ONHL_7GT{p(!l4LJrB-DuHq-uOR"
    "HBxF?#0FDe3@-r!!l5T73fAKZnjoG&wg!v`QpCjEuwA{LJ2J5Yw8>DP{qjXF3w3Lj*~M}^V<W}qQ9au4!UJ;g!RVi(pYy43&"
    "2@D<AkQdzv4y4ydcK>=(?@^+0B+yK$wcizWxtQ*T7y^+ci&YpV(?_JB^dZY;3EsZQHh!#ztd1Ibp-bw)6Grdwu_4?{&?dH8X"
    "qN>z+odW4qF_{2bS#a%M>QEiXr{nqZjlAHP(C%?$so6v+U?s+xP2&ae|p{sMw!qEyY6<3YDl^z@W^R!wR4=0cMnFf=$$(=Zt"
    "#-AAf}e*P}Gqk{2=b9MLtwNaa<w#{mdvr01*6@V9e(*#Q-4zqQ6zNG1^KHW4)V;vj{#CTA&zdbJDFQMzae!qUOzC6WCW$de("
    "665k<+)^L5C6Y3wa+NvEu2N{>)7<$fi{GeOvX5>OzOAsmUUqD;{&wpdo9?|`*GsSO0?7WS!e3*xGf0aweH_7OOTMjYN-2d6H"
    "fjdHT5)Wk*KUilh`(aS`^4BU`;hk04Qdj=mo`g;I(TN>X1K|nTx!1(@W5Mm^ZfA}hn}@=5W+T%Y;eW>kpMlwy!kI^uvJuL6-"
    "7c|6+fuTCUfyx{5821GiU#Wv8EPKYV4m?o1T0<5JJWWcwp0mXe}nnC04s`*-ehnIkp4n+Qc)gFQg?+_omE@FPuAZwK8-_a+!"
    "`(tEhC-TKAPqvBzc1gCsJk%N2Je&CRb~4fA(XR9@Gf@N&2VxKKbWmENPO8S3FL&}7WQx)e?16o<gEf@aa|#~%V~i4tdETmCz"
    "_TsK}N&-UE!el-{1-3=1ipH#g%hfX=CN3-$Y<qrKPyhtY77V)BUXE{C)XnzGs6Y3*dyHi+hlaIL!>rFBOBE3c)QBYJMl=;TQ"
    "M25Qr+^~c|nR5j>Di4WdHGqyVMIL{eUI@k#8rro7b2LDxVaLCNKD_zI5)cTQ@R&FpyJBUZhsrLtyGHR@*`phaOK)<wUVCIXV"
    "R7WXXtT||-hGdhj+z^~e1&=xwC*mJh!FGE%heA}{!OHZH`z4~2V~m<w(pEgcUsE=y{q*8Z!LewZ*1u<9^PK!*{V6hE}6$Op)"
    "=kyq#*-PQq0opsGj(oirg=^`F-u7Ua@uvm4%XXM;>Eyf~&zWdg8vz0G;*NG&f2ssEaoQ!MeJz$732}sXttoZr$FG7<q%I4Xu"
    "X3d4g5r>OrPHIeTW!c_tX53(F5th?qDIZB+fJC}JGm(xGiEnULt{_g;v7H$ATW=L+DHPq?LB!jhi|g{y4EG#`?o0zRO5xB5w"
    "+OI|<hh?_(R|6xdmMhcaUm_vZOk(*nLVY&dqf1G1UE~*L3QY~KwcLG%*-f5*8M=cvukQ=?Cr76QxEDhgGIPVfUE~|HB{}S?r"
    "?dzBAvObQla3RWY(m5zkAC$wQ5&icmP;XZ&?6Iceh#m*l6cemZz)ec9D)x{|L;>?jYBqW2(s0hj8+m^_5pOX@xRxxiMRtwlQ"
    ";AuqZq3c2*%}ZiBHtxhxJ`BA!Dp0deTTjP?~Fo}^ooUqGF8LqEeu0r=M$Sq&G8xkwc&ynM=<nJpe%S{f<=ZxQ~pad0FPF5>~"
    ">peIoy@ll^{yZ=Zuehjc}xeVcq0i%G_K=2>0;(&>CTXxgsZ*2MG)$uW(sm(E*-mZ$tdB+5g#IUzhSS#Zs6^|3c7#-MP0N-8X"
    "Fvtd!mA{i~457GT}DD%%+7_Xc(l;}gq?aX%E!I$2zQ;tb!4MJpW-B=z|pT1xr@8;-@wdXFi12mx+TbB}c0sYl*?Bq``$ziww"
    "oCr~UZ1$UqS?SKCiceMzK1a&}1;+n;R%z!IdCW^_Q7{(VhP}%`WjK5(GuN<qS;O`@W2!-40-y;-le3=8yA*S9=tl<M+3oM1L"
    "gSKErzYoxEK`_<f8b%lX^+>jCPfL|E>$9&+hxhWFNmJXYWr%<+kkGeWVV+c26aP<cZ{*(8N$_Uc2h0%TlU4~VlA@w?<$xCLF"
    "~zCsno8}+lW4RCExtzb4#HbI7fNe}EqU`rp-ae>9?szQnTdNds=ciU9M`JEF?;EC5nHDA`G{1l{Me5~a=<~4ET42(lCu^yq0"
    "Va)|M<?hA~rgTxXXri-R^`YA+bF{;5Zf-|G2~_(XU5nhe;TjNP@Fmnr~y>7Y*mUk|;S&3n?QlJI!;Sk>iS`_NPr&g#3sD%vJ"
    "x$tty_jAG-m2*L;!8h*T+XOZ5d*cgO+eNvoFSLD$S)DN}(Ikd_L4eSDG*KF$xenKtWzuS%=}+JV~9?DDh$24yTN1AsAw`p#b"
    "}>HO{4W_9zf2~J}Jr-JW0zkha{E^;-ZssHk$+i#`pB}%I|(4!iNVXS0MDhFY7xj3TdY4L<){p@wOt_WyV&<R0^!P#RKmR20x"
    "T4Xt_65@1~-Q?p<24mWru0J;gwBNVC8qe9;)y1I;#C)dqM2>D*9HZpO?b&sx)97g^#lw|5mtmo6$O?ogQg04lM$q>oEm3v}w"
    "P9JhfQ^>d=0*FNG3{W7I&hB)mnEKjx_}7LEhjfSqQ8WW<;vWO25DWdokkJB>{}Gw`C0w3NZs(m75i&jVE(Dikjhb2HQi)5yq"
    "-aB@EZQ=pj5{06f4Z;@YJZImi*rP!9hk*hL};XtH>QC0~Ua4M%+tJNr2Tme-G`6`<EEzBQI23anceZgk&0#LRC4sa?8Davb("
    "H?OD=0~`yor=JHy%y%^P7h_sxq5*(1r2ICE>XSOu)>wK>BLAU1Fp;nf&j$X&MEqsbo^?Wo1CDNnAfU>Uq#u}KR@GNGrey5xN"
    "Jt!RX`Gg`&WzL}2QxXUMv*XlWIUxwtYc{jU~9qW#FjErJ}(FK&~6(<dwMx-cON?1)d`a}AQJ3YLE{r6v=>L7p;uGGaU@!nyi"
    "iC8zIJEF>O7K-|*qo04sE>sWM)MTG?Fb_D!h+n)?L!}TyGShavQ}Zhq6uIB?4AX!AORFwMX{Rg2$}ot~g!2#c+38q32k$=pw"
    "SIA^0JUM)G5x<h0W%6gdx&kGKOw_Og#`vAeYTXb6h(CPd-1l==#9PE`yA@R=~X0tb!SwZd}*AXwp2N_o&!#FW=na&*oAJ~Kk"
    "LytS#u++#+{$uzh$nczHTnNBo)c(YZEDwn9Cq`IXS}XmkUN^8J{8i#$&%4p2MX`=x@7XF}OqueOPm5_->X%M3LEc^3x6PGpE"
    "k}>c?d<Y`(S&9UE<#+uYk~0W!5`Qw)XZv=#Jhl3k9bNCzG}W7me<@{#3Yyb)1F?W16dggdp>c5ZR(%#s9v37VDj?NKl&9Rq&"
    "Ad6=yaA-WW~<Ys}=h!@;BOt0*lB%e--Fqzbm(ryKNzudJ8KuR>&5T}&y-=HK6$6u3HJfCXeQcICi*xgYIf`{P!;};fTrNtr)"
    "yT}G7g!vS(yYS@BUGUw(Q>c-QWTt9H6<tSz-mv9+pW*_pNzrHSZ1eau!T36poGUwLg=ZRA+o3wHS(X}l7h?7(39j2b_n2}8^"
    "C7k(5~UtDOY~(P-q2KvPkf7Rrcxa)VZTFfcrpP%FF(gWQ+_JmuJAz@>7_a94P><gvi30Qesn$&e5fX|#HW4svE8zxLM|8L!="
    "AHcFull{K5DHciBZs1xf4N8V7L0v`mqF&ny{;feqWVxJ+hSaW%pDK%q4REN4k%{M*5(d9+LPU(w`uN_q<>txV%9E=Ni8YL8}"
    "ngV_Z|d*!VUxdLWs?ZgnJSV<ZE}2<QI=`!7m|FFDHJzE-9b-w!T69JvZajKKk_R5z5V)mw-*WKF1R5-QOw12HJ!>!^|T_LAo"
    "_8E+G|Ksu;gW}r&!CAv0s#O>#geA@t!GF2IvF@~15{Q^^~WUzLxD}12~8^Ei}O@No7^KA>i`PJ*b?9$tp4Ht~FIjfd*jl!`w"
    "xFR?bs3*i53yPJm(5CfjW9r0FvuBX$a<l+CR5KT5n|aJ|*?h3Iq~kQKmix7qqIADWigga^Uv#ZcLw2yq)P{A^1S|5gjW7LZ6"
    "=TVwv#b%N4PG2pkP6Nnj7-}ZV;@ZWD^!V>uIBbp<CT9ssm#jlQ{wx)hOyk=>{9AzWDoiSaUQ76rxD>_ezTtg*6n5G)DW{?E_"
    ">oEHSvsHq;!PA%hxW>u?Co5!T(WJlJ<hJJN|gM)J9Bcox1<HT)4J$b*MKMfCq-UP_vjMG*BKcRe1-KyokD3F!7F^`1w7yHTc"
    "yiAPo~QodJ_MNVsYhpT=<>(jv}+vz^|lrRaVz6!B3&k@<JTx+{KWslKE)alI-Injo!Gs67$>;QALyhbZJrhBG-Tf1#k(Xxgr"
    "y+~E@9M$<*psCR)=keX_-hP+_hgbB^ZIZ!{(1AW&cY=bIYl&dBDIiH-4-+4TuA8dfH2)G|=U;BO0Z)t}>ySx{b8dv_&*CFnB"
    "Qr7<7#hbh)4`^VekUs{Q3e!DtZuo8cFy!|WKG=oU8c$(6s_@PgRg_gi7V%KcF|-`>7LiyG8?FB_QZ99SG}Szg=m1eAQiReB2"
    "+gNKGZ~Z4QDjNJi<WqbRym4RWi9%<Ob*zOw(o;(kt%H=ajzeej1heENhd?nxHC*hM#^&<k#t~JI)zqMdTUEwZjn1K^EGB2HO"
    "~11aQS)Ke5PG=a%e4j>x;HI?J-tKUNfME*1=0HKi36{(RU+#SKHf@WT;ty@1IeYH$I{M8x@2Vr*O^t+5pzyZ0`iBRv8tqpqs"
    "n9LY5CXvT*CyvaRBj8_?ax3hayg!m^I=UF_ZC1F;K!{&G|6D&WP}GA<0u!`jt<G){AmdBK)ddPPAhdz>sgfrSY6w2iBJSCkt"
    "JH_SiU|E|9K?8AU_kVKwr37PGrP?;jE9kt`0(Pdh?m{s1%3#lU3j7;7}t?F~3QSeF?eJ9ldxz9ro=C6i=`}g(5RPLZdR>~M<"
    "FMib6maU^H(fH?tx=K(_UYhOhp5W4)r|98?gwc5R=P8$RU^eC{-6Xq{<SIW7sdZUcjFt;Pw_Im6+cp`PEKpD5j(F{yxh<Ew!"
    "8Y4^>Iy)echs;kk$_}~%SNvO{EPjFIQQ4~gWw-S8`<zodK(Cm)zXGX)V^k%5;!u5X1Sb3TI!9fsx^t1Vq%%E*4d&k<Tjf<D8"
    "md^B;>V6URV4D>!hx9q7gMaOx{Pl7vd?qJ8c24{j@!(pdZG(Fk*Coo`$k%0Vfal-^}vRq!P(tiA!@Vgs!s6@zTgv5vC`P`vj"
    ">bZ&^0zrYE1a&;Ui4(^F=|MxuX2&1I!DS*CJggJnF5KYKFB&I8v()u-0d!c3-d9uFaG4vsTs1S|=w5{J8jDd*xKeuwBgm-es"
    "PW!2Nb8&T7P6UW2VDv3E+yH)y;M!X9oUsf@humtCx>p}`~;%eL3R5x!%Sl0hJa@fRhQrN8v+}R|avS`bg?4-wIg%7@Q@U4i="
    "%gq=<`lhfA9Zj3xz=im0JKj@ahhI;?5tEh<H`L`>lJRrI^{421#&q7T_sh`5&)homcZhSVS8bP%=URZt+d6g@-9+)?qf$p$;"
    "xBB3h!qWPN^*u1H-(}|p<f)rG0`8uc>OK>!>m<xem@`x5+3UKcoLQT&OAqQ+yqiFr}sIDx4KD2l2?thT&Flt*6n=f&M(xE6Z"
    "}7<XeMbVVm!?i2Ua0aZrXQ<iP(3DD^&sezV^<G4YlI-PFK&h<a1i_i&YFd$v_B;cmSeg=*HPz@m-X>^FKuHS?h!IaPve{X$g"
    "NVA6GH5^`!a#)+^4sSyzXI1&ukT$!i#=^nN`$t;(lJ6#IpO>1$&J-&z>_G7tKR?Y<-&*eXXPLY|BhR5#Ol{n}*pdJ6@-<2Oa"
    "jkRB1lL$IFLBim)o8x^+Z_1iE4;IWFPO!|V=94IgeB?R;Cej4bEXsAZ>4S<pS!SaR4g1hhNSK&S*oRfFx*i>9aiGk_3pwTWC"
    "Gs=&b)2P6JEZ(5S)4#)B`dAPshOS_foGxo(H(&ZoID-FS#Y~RE%3Vex+&hFM2?sqO*S(Dz5|<g+{UZS`vn$<MLgiMbZm>g_#"
    "FWkJyOc72E4zOyw8G9pKU^rwE0G6sUKPX^FMqT>Is|oipaU>rz+&Pdw<_*;|2iXR+Qy8rX{_1ByAQgR^3yeKF(0Z+)~721FA"
    "JNWj^q$42M8vwVbtZ~48G-dOrxXETa2o^B7m@lPkswohtIgX4ilzSB{TUVZgHBshO3O_uPl|a2<pY^Yt$9VCiCq)c^4dxO(>"
    "lX!R)rV|7M$WiGz#RBeqMIEpO~yqBrnYzzkSI5F^)>E&_zb{Q12UyU1lV%AxGwM))Hfo~~FsoRi0D8wp*!Ph}TG{0KF_ym*0"
    "RWRDIZQQ;#HGy}7WF!ll4d(+I59siiQS&1V%0-Zfn3UYR#IV{=YNG$x0?15^@gDWYg22FHMSoyO|T|9X?yA+-+2ug=85>*c{"
    "Bv6F{8?}pZ@_dq28I_KgGf<38GRo@(s3wmDrDS8K)UjNq9hRGO_DTF+KMmPH>{+*d=<bo+WM!R%hKiO#*<#}fIK>8{8a_t*Y"
    "4%+W8g>~`1f;=Fx(7tOblOsp3ZDSxQlIR#c8?Lk9MKQN2_D%_pUb@A@6E%57m*hiScgG)E;$E&_UJpc!{Hu{kKFm=2M1#W1`"
    "^KqzW$^-7!=e}1>!;#vav?*<K*IgMfK!PFEs7&iDu$xy7tZtX#0TlneumiV~xjH!}Rxo0Ea;~#75Ck)Z2)`A^JJZ4LEU9-o*"
    "u%lir-<c#J*^u=L*tjMAy|*(w6<Xt2qB2+%NSiu>_A+@p0-TTyYx&SqBM#E+}jNNjwURsxUY-?^5af1dAk;ED-EU+W2MaE+J"
    "pLDjZ<k02jBGCUrbsfpcsl#$rysmhoGfXV^Ps_v)zka}UJXLziDL1y2@PJhi_f2(Z6K?LWpxZvW8tn;&S#J=U;L#?f2M1Qlg"
    "5C{@*i$+l`mrtH<n4DeG1VtHDK(+>ppr&TOUygp?Wg6v0B@=wPib$Ew#0}V0C^LRkJEkIi^tMF-Y(_={cLz%FB0LGzl_W%9w"
    "wXMD`Lpx5+PIDe9iR%2-K?EU^w*r8{%@Czq4b8o^_2<UiK=hr8FsMwsm`2??gi=qnXF7vgvIPlLZTMx&vZC%CkI6YQWh9Q52"
    "8m2wd|z&SlQ;*;ZxPGm#JD?G9KsCCmNp3*4heOKe`|7QF2~4UMdJp8Ffn+c6K;_-!dOOhoeV`Qg3%lnt`!2e@k@&`!#CVWo9"
    "B<^?^d8puZ213p#rUU>7YNNITDxf=1whktW{H|5_F~PIxE4e7RpRT3dEi9qph}6Fn26wvmGg)*MAiFv%#g6)xV@&lgk`nCKd"
    "uw31hQNL7aGvP>$v<vP#K0Fb7Fq^6nC5o)=wU4Y6zy+B9LPN}CMHN**B1^lBCi0ogYnuPNZ65jeznmj@J`*sw`gu*C}z@vz0"
    "*7Ggu!nt_#9y!7*)_{S+aL~)l&76=$v6?p&+C?;7xfl9U@|V(OwEW-;4><{2y7@f6#;TCk5{Ri6FKfjU;wtMKU6e<4M`7y>H"
    "LycQ6i{OK^T)Jl@wwSH(G+HDOKZ-XtDDEz2V$~Au?r{k4<RY)SgVm^cR7+i8Oi~an3-)|j7}3FPoj^dE1s?f_Q<4$aEC~Xwc"
    "^;Xgx6epNV;i=5mF{n!47bluYhy=Rz1?qWB&c~>R#j<(KdO=oEaCvUP@|m8FRsOA2KSK6#fJWc%(0Ql@qiBdz#@{MVK4a66K"
    "P7_@5f|reJm98bD~4985)upe?f@Bqd@g9CIx>>BTY1d~r6pZ;GDLeaYMHUJ%V0#g~hcji`R)c@VISV1H|9{Eugle(3Q>h&|$"
    "#jz!2HU#9!>B`_sb9u-GrC-sRlMsKhFykVvg=xSmH7`y<6A?r+1hirG4FOaI-B_yuE`Q&X>zbjg^Gq^8Tx@_TfM_)43Hd(iS"
    "P1E;Uxj&~H=b>LNQKQ<*z*4|vd+{*6;|v{xNCWhGovY#SzZg+E%Q<}Fa61FHIQgS-G4s<sJAB(KeABG&%6Rz*SG<Is+HF@)?"
    "lnYAC36U|)LnE|XtiPkWeCq&*mI<7KF%;x3U;Lba|a-9aIxf@8J#(x<n=iOInEe=&WFOTALJ%-b7<`H7;~)iJj4$|=er<CH5"
    "Vr-PhB!{Du2bceDvZ~abd>mCnFp)(f`%rdi6z(x5i7ncx|@q#jZ$s0};FhM56^J%ykYz6E;*PIv!3kfv>|UMF%iKa9fNzL+O"
    "80;YVF24N}KRJ5jSW9356)w5~@=iL+0#&3<HI_j_>UcV6w8Mhr7s4Z;L(LT-F8jV9&U_vj!@f9*__%B~9L=HZPcj+z;uyHgQ"
    "07V9p&0e*QGM(~(#X<ihxo$A~~i8NLAWD|fNw<cs<;G{@Pt#9dW;B7SaS}DiKH%}G5c=vTOZPDo5)a$@bd?Kd#*uqs0cv+qJ"
    "ZD;m*`?5`=qe6Xb9X`t_=oQ6I^EuouKP)&VIg633WEAatyATcm?jn_}7D|}`F74C$UoPtd`JZH2#c_m+D<f4G3mvt<IxVvt-"
    "(B;X8@T)8Do{VQUviA9D1y&^mxR^Uq1a#b&2$|vf`>bKXmbq5E^fTzLsLPqISBUqn5@ieD8fbOpAq|X+ZF;ou{Xx`goL6$kQ"
    "TVZyoqPI4+4mAD7b{<T7h{2>|ym8dq>1Xc1(iUhGh2x>Cc5z-_>*OKh#m1bkAoOIg;udv&j6lUBRn8^Du3lbKyI+RiV`$SU2"
    "XV_mXyiBur&Oe5RgvT<bxrV3A=<(oZ<?M3Jfsm*e5V?O#UQ+&Dg+UE1k_89ne6?z+FlQohK?7!-Z7{_^ngGX)d=tJMBE>Qxd"
    "B{%Sn#u<vPL@v~{M8qTuTmdIz>V2sPBVh!0u0D<z)YvGffKPBi=2pK#Eqfl=S?&w?~4Ml8pnx)3|TGY^*H8w(;2YGCRlzf8`"
    "bDRCWjThcx7<KWx^*e+PoQ51Y@Tw-{&a@fl%~T!jKCrEk;={ew5@@}@D0mG2c7)$QGO;_-<REmk%8J~2zMM|AM?nm-|MohQ0"
    "?QsU-J)DkU&<()H|Apfqc_VKY%ygpNSZJ&qEgtiy?eE)pFjP5qMR1X{Hg|G;7ZwG4MDN^jOgp5SeBeQn-A=GYSE?i%kRZlms"
    "jRmRn|vJOUK<+_WrW|Lkn!M0p>}Gf4L|AK-|^$#2s0zQz<A@W-Xs4&fAftH|tyBrffiIrX~j;xFVJ?I$f8|4<PK9XL<s5RdL"
    "~*fiir$Hh)OE(IyA>ljm?61cMy<mj@Tyfd`wg=S5q-%uvrV@;>oUubMtRZrh%y*vC$9#~c;L=4LsoZC3U87(^jvo`{4!rn5M"
    "jYT!k*!nQ2%w8<^0LpGC$p{PVOvwp9P2IEHt@|3yTSo&7^t)W_}@P!ZWpWbthM!)^DObs}@%G&J%E3l3wVy6(5KI<P?GYp7*"
    "N#NxDTzHrr(X|}q*$~p^bBb^|-E!$?{#eO!DNpcaQt$e;->K04zWngN(I9+sZ7es_BzM**XKOli>LS%ab!B@!z=Uje&Q9Ec*"
    "a*F72B1Tb8^c}C5MYnjHfp{@l9+>*SFW%-T^@KF9%C1L#cTDOYgB@DI4c8?M#BlpfZINze8}^g32lON)N5=`b<2RB`h8;peB"
    "veoDj`woeJAMmT4H?(g4~6_C{Mmt#Us5bsgP{xH*xl<YZ1PgX&Mi@nczYxSX(isyFB)0hj`Ftz_7?=JIuFybfYI5f>0v-6v%"
    "++WBA0u!-nF=hMLUxM?W@ZucKX{k^Eltn_t#TsHkYcs;p|H*d>2~HTmPyU1I!GO>hu#z~<i_yNwR}WVxxNBGii}W`%FO@D^4"
    "+otui;g2E@NF*Tk3^Z1g<akzE<No0V*Nj<3()0P~{4V=1ddZTl0N1wgcNwaSweBw_n{j`$8J>ol7_pi$^bxRfb%>r833U}(6"
    "pf=-DAawv)B&9@2+$DY<q(trNwY8)of&$vk#66^bjCET%x^CLW8p__=sow4m<jh&^tm8V#MXOR)@2$Xk;4(}7ZYpO?z*<9y%"
    "x+V(gU0uO>b&9FofsM*a@Fopgj%Ppn;uG$ckeklgfW}Dk|pdwhUL3-#apR$sjWw4Sn_*r6Plj}UUJ;~f)`CxEH6Ou<x`~~5c"
    "Xd-JN5584QH$lx_L>zcPdG<E0Uc0kw&Gtb1cA?Ze^?m^p>OApxX-2`rVa*n30AQBaBG+hs}XR6G$BK#lfk&TCFOJ#egbZ!e$"
    "M4tajTg59v3Ba?;Qvk1+pki`08SUZ=iwfOBLT+7cE`1704&!Y8y*nv72+T;&C>Yb`oHqRcQ<1wC>V7v|dY**dNcDF)?cPW~i"
    "oj2mZ$q?$tWN2-Phz(dniZ*&5_yllYCA+jlC!}f=i&@R=EF%5~z+$MCRz0{5>8BJW5k(KyK#2D&REoUWX@$;AFpDEw4mz^E("
    "kFlS9z4*YV`&DBrn;XihO^tH+2>7z-#{~PC=^d-y;`OZ)rM(PBo@ob0$23SDa0?5i9HE@1J~qZc!=0jhNZN|UKUDfrcuz9dI"
    "I6rehlz&ia{nvbknOQU5rn}6;O4&5jCFw)f<y;6&<yAN2fPXK9&JWB#5xdNk4YY4NHbQ3P%M#ZP@@r=DEu^B0IouZ?8&sDrp"
    "PpiP8-C%saVrrsdmD&hs*$IP42PdRp*h44N}ctle#_~i7R4%XW;WYA8i20N1!~9IJkWm7dL5(AA|*8UkV8RdVbM4Pwd7obyp"
    "{VD_X|o{F!ary6gsf`c`3<5xXKG@?VyST|{g0<m}h_SI*yWlB=9_4+wrZ8^HB)JHZMu^G00a;SDswUNMYSeAuBZ3?l@Am#P9"
    "X(l7f{sv9e}3|RLkS&JKs*uWfPmCr@)fvIYdD&g@I2;RlGp{wlwRH;gNQ#6%Y_-vYm;^IUlh8rH+bAx{uM&BU3oDX>fffDbn"
    "q0(S$IQn+n?J9S^cO^>zUq36Odjw~)x&zPsi>+Vz?@Ykv?@lGJO;cd?z2|xd=g;{!vZ-MIrAuqUr30H=#c{~-d&ICv(Wj|jt"
    "dSTauST3@bo!XB;vCtD30PzkO`;>h-~nd(Hqc@tAL-H~rblcx@i{`M3=A-9DzstY5D}etm~WV|5Z6O$MMGN=>b^rXl*7Hc?~"
    "NkCek@L~z3d*4_B3+acpUy{$Hpx3*TUVgd?&{1A9Is0;r+#d+@*S~%+YX=ynzb3?5uN)6cxOT2t{xP-^`Qe;PUg}nm=!W^5!"
    "hLmC{nuw$8YJ(edvhzg2>USgHlsG_k;0wn$Jy!zzF$pzc2S_gz(_>J-$Q>Nch*`BfjXKg73|a4$8&#~}_v9*Jp-4UGMFXnc-"
    "^Wm<N9H^Q0+-zuct2h1bhoxe2|l;{%H=PSdua-Z2C(92qy`zst2b}u9_eG{}2hSr!JLWP>WirEi1KP8CCU#vQL!K(l8HO#H3"
    "N(1>(NGWpFSnN>fgco%eRqZrvdxgrF?{w7Cz1v?D*oxXd6{GXA_=A%y;VO|SkV1weA`>rnjw$-tRIM@Z>}{ACRFwy-VDPwQ1"
    "zwe{+^r$s(C2TCSQ$tCBw`&lN%L1>gHJv}mS;&N7ZRnezpwS_T175>{zVD;Ka?biJsEg&^dy9YSM>6U_Zaxj2e;8g)-3(9mG"
    "qAda{|Vz_W>|PhvBz$aQac66~KNk`bvG6a!xfosrmr(su^~wBbBfno7LJ<7B4yXY#<UonhQT3o^yAd*DD!8KIG0Xb+&oZPtR"
    "YxUKrXR;jE|*3g$<dE8yJ+R$!r#g?fcR3R=Sq4w(9KC$IvmoLM9bTew_y3(dx}&2Q@m3}?xfD-o{#n<PQe1bNP%+7hAoRdi1"
    "iKP23~9rfg-%~jfNhl?D0oVbXBeT)^yp-jWl6RAB#1mFUzh@kO^Vn@lonCAOfBT4boh<ex72Qm!~)#AcUB9jk~%7t;Ig|ehT"
    "k@T96-8OwMK4mUYc^T6*t3%sz9c3}{`w}%hCO7Lwe_Wm|5nUJLEX4gX!#uhCuQ6wth)a23=}TL|hKN<CL}^zJZQ8LuBZEE5T"
    "A_a}v;#oQ5B$7ql3^7~m>K;lE=c~N;EuB;h4)<|QzfCd|HzrFjozQY1jvr`sn-o#(*KkA2=6j#3Fkl6!L|6hsH`IKWWyd2S4"
    "&^`9eDMoF6SMQ?I};r)H=my8(`<k&QVmYEw%;X4}i+p)xp}kje(EX+vv$X`&At1CuVphei9Z4+sj6@t5J4%h4Hrsi5o)xaSS"
    "b38G)+{H`YTd8XsZikA@b6jwG_HO1YkUAwkVE-}B>A?4yhN=03HJ^Th;^r?sU_rwS15u?$<IjbQ`v;l7K%c9)Ag)s&W=LeHY"
    "2&zPVQrR^K-RU?NQwuD-XkN@r5aMO|YgDRCe<IEw#_%|J?bIu+MNmiMC>2R?>TVgY|kECM@L9!m4OPsO&BSx9K9uPs)$WY;Q"
    "htD<ys`E~5-8*}Det;ysxVn6A(lgI}0huh1Em!gutCE%|g#8x^XU%p@n8lLA@g@{iaMAGr@AT~_MYt^<-sl-4Rmwl+t{>DC3"
    "gJRPCZ$VRGFcd?Xt=C8VUSDQPw&RvRhMroKe~t3s_j?}){^Y-Yb%0YRd9@Ba&;7GdI*-UGENZvC0qZ9Mv>1bF%6LE;Zb|PDu"
    "y2dV~x-Q1VKY9ur<>!U?()D^EhfAI}p;PiW<0;qd&}X5-h$s<q!?K>^_^Ck}+rX4Y-J-I3<7N&ANl(CHA0!S$6-~=XRTR;4Q"
    "oBmfnhhd@q)b4P@4YP*pEt<7+@|9a3d{1m;QpcmMc5azbw%S!gR(7NE%~#1oG!{e%5;F6wPVQ^D2Q(%;srI5{?aws>R)vKE("
    "mhv9@?@XIjfBD{hfGR5s~ubO^gPmSuYr4n@LF~>2<KEC9u^<x%_j*>ll$)tehaWKxGnpGMrd+i&qa{5=u3KF+ICdYpuxdaNd"
    "uTr)RaRgKGXnd{AuzG8}DgK!MRB^{qLSIDlXFO?at5EK{v+zIk2*O!5GG#UQZlyOrCs<T)xd1&h<bJ@m{L&YDWQ_d9I01~3Y"
    "Q7Otv#`fyDY#3X#Q$XtJ>lM?|BLSnieYNBuXL&ab3Wv-w?3a%(?>p}1bF5!jmdoZ&?{6yXOnkfLvSZPd44UD$Id9wTmKw8Bt"
    "Y~jHUQRm9Aw<E4R?M=bmv{nsa@(~H+p5S%di$89_wP7eH<b8SynHhg(2nEb5AwE41@hoMv9-bH7D$jDt;}?RTiLc{z4wqQ(L"
    "Z3A7L;%D6u-mTEaAsXpR`*%aAe*CXA6Q3{Rjg{#H~W`XrY6l~es`l0Xss6HyRo>h8;2j#>W=xKxa7g9SI`nS+)FN@P};{XE-"
    "m|90|b72;DSlc(=$3~kgHm9tVv*}gntLC&oKv3&=VIlleuW2c|6y!vw!34Dh%5m!QhSh|>50B2h$m2nrl-f7euQd1AuyZPjL"
    "pB+F+fJbi;hRpNKJA;JF{Bj&C568Cy@nbqn7FRCOuI~7P@&Tx5qAq#MH`Dx~ZBZbkg}r32^2Xmd!7v8IRM=g1#3h!M2e^A%<"
    "Lh)tbXWciOv3{A23epnQRnnkQyaAB8Yy~G)AG)k5hNwl74_$$h0rBxi{tHZ|Dn@SWa&v)zwR6(1?bzYzXHFVsh;DjocuZF?`"
    "e0(xxE)_1t9VVNYMgA=8a=(p?Z(+*eD(D*b3*Q4>Q+%JP+QOq$1k#uVm48idJ0!7k`|_m?u;J88~f<!3x=(<mh{o6f?HP)Ag"
    "NbPSy`T@=CKc1x*Nc(nOpqft)qGA@nU?-e}OX!tNJACYV(AENre)CPn)Qt2Q$e09i@0gMM19;y0eW;0D%+!b2C1OkJ3Wd-Fa"
    "o_t-A8lUJ?v^K5*02U;}Pd}{thlTff3QGw*A5M#+}jWqSenv|g)0s!fOgI9Mfc4{c|4h#-iqlErZDG~|pr-`u2aU5tw>QieK"
    "|4v?4TQ1|<TE@J$hEudsa*IJ4$2k&|x9M7Af&@gf@vHLpp|p8k)ST5H=YGHPRLAMaaEJ!9m%w|R6n8yBGzpL*(}7@bVkEMZ^"
    "7+N5zc%#}k7#+6n^l%tBFH7<mBKZ?i$s1S8=7injbGw)M$8~AWDZC}VgDfoRBYOEF_}#&lHjwpX(w>Bb-G_^F!GyLkcf5EP{"
    ";6spBabM>>4bKF-)Hb{BLl|CIOPG7_^&m46dh#7ceU8RW#cplYpc#arT8xYh|>j771J+!gdYr1;r7v%i938)wGe;a`Ms;A-0"
    "_WZ-?IwnU$Xkw{Jqg3d}M;f)!T_Xlskx|E$!MkzS9qR2#Wlmjw57eJxnP8s(-NKA>=GjY}cZ(Vts6J<|V?DDzj2k#NbMMm}G"
    "pil%6x`?>+TBJpejMkA>Vpi5vhE@&pZ_LG6a=nU56M|&)Vol15r9HAF$y-SAjg05v+;a)AIm5h;QaT`<h?!qw|KwtZl8-+;e"
    "qmTV}eD;uo!p{9bpA*7JlfS-F!otK6uVO2tqYR=Zi}?9b{_>B959#jxifi!qugyC>hef%R;gRres<dr_Jn(~mpVmo(W@jD7C"
    "s}zfn`IS0`T9T;2_*>a6QkW}V;pvND?#<ZSOp3zej8V8)cFMduhm}uA54qsllkj%RWouC72>}Mr-$S21b>e9fsSKbcTWm&mw"
    "$tlzMVwKMn?hCPH29!at3^U`6h*T>+On6f4gfxa9C+Q2(QP@84OngFKs$2sG9mU9zr-uYCi|?#cVnA!%l>9HWlkkp~I&2K4P"
    "|6)OH}0-}pPbYG|E)<xW@}LH{c@<BswBN|%i^Nq6~0IoDN9&;WOEA*a!?`>91cCbVrT)XJ$3*K{Zb%wlPCOZ(^(YdfUxZJQR"
    "U=zFGB3dRa&XcO#`u^&V2o*=GLRQGS<qZk@@agy{tz98`~!}8EHWTGL`y6~m~W=aS|GtNCIqDZ~z=aR6_3aFW=q2qF9@pw#B"
    "+6XYI_}l{w%W(XD)_5@=?!-y0u6k#%8Ms)bLIU_J=P~FUwwu*<R`kQY2}k2Z`F6B4_C19aC)vh(dkWIr$Ybq=_SL^iy9K%x%"
    "mn9vm76J75qEkFha;hxgZ>n&Y6(Lp=VXO-LkFMHijWf$C53r_3nu94`VNtQ@?0Y-W)(o|BfG&M%Ad#{ulP}=6w1z`k$LBeWp"
    "a4>0%HH*({C+us1i6@f@XVa?HuVw#yoiJB;1rxqLNL2C&VIx&*-bBw-D%Xo0&GaTXA}ELK-R?%!?>$>s0!hf|t8K+N<*8$Oc"
    "jh`uvYkbm{N7`)@GOZ2jT2E<%%cT`Fc}9Hk<LO2zK1QCG*~tacU1;Epk}CA$>9MvzZ$5oEvp?wzjp1{%{5A=t;!L%s`(`RC#"
    "3CMyXEN6>qmB<`B**8DnZnGp}WuV_t^6*q+y2tlc#-)4)E7S7#6y|&vWR<b9+`9%tJj#_7#ksQMqhRYvvoKkS}tw0Qsk=bZl"
    ")C6d41we8Hgs+{ypzF(9w^8OUYM}fD>7Ty;HV^4wxeckfFIsQA&)pT2jv>jJQQOYRy~#OG!E3Hg0&IUP!PAxSD6b38Lr76Vr"
    "-ZSqK285pdh=inmnc&3naa@JnYO^m!=7lXR2+06ItG(+hf)BwCVgM7{IIsYU(=?)y==PUY>%})(E*u4ES3gCA9q~4U_(_QQ~"
    "5hE3G2$}Xdz#RUORNz9@BUOd<uQ>TBSoSX=8V?-o7%N9cw~J^1VBj&6j}eClxQJ|1>=>yf59a>vqoTv_wn+NzcJsYn(qLlf}"
    "eM+^H+}a?2xy7HmJuAB1MY@iKV>?BkfWV~hvfpRZ8$zGr@ohn=jWfMqRM?^i0$YuQ=~Yvu9I{LTPAhyHCb1Jjl7_)W!``vLQ"
    "!TH^{Ph1|c@X_GiT=6XB;whk{>goc%c({XanJ?gyu-k|5UDcuC7_DY%$4v1MuJt(ph9eo|cUC@KkLIwDb0e1ddn#mZ&t~sco"
    "MtGQTB!yW*zOY}Cvb>_aX-C_6NJe5tChvzpI7jg4!+wIkg@?HJ`o@;bJK>ZA5iL9M)IAKhftOle%zDnxs#Nbi<yUrZO=}9eo"
    "NLu9^*1Fam$fyju{Hs>S@D>){<YCDhA2g?Tpi;VX_i!S9+YVdNyD7@@)S@njY!ndAp}zFAo=(r7(KI?dR-lP_W-p#YAesltC"
    "gpVe33hUTF<g^Q{(B^ZRcpzVhXRg%TaMg)y7n_(+Jo6PR_!)j;s`2G1qRdBE+xUe~C%{Ha)5I_SA>?A<r4DtR}n+jHEHOeCn"
    "_z#|<hz(8ok46?YGre-xrEn(q%TzOn!OLR}`}Cwm*8(Q}oc=uT3z$7GcT;6O2XNAorDWGU6tz!}W`t5P^4xRqVAr1uM)WTB`"
    "im@P-@PTvwbv6@IocqY%UsyuLs!cW@7iJ*UyEJ6=``AZ0%zy1OEOVsYQjZBVY^kF4f^r_u4czx8*W*Oi0N$yNgVroJxs!Yft"
    "o6I^pDZFyP9)!5gA&T%5Ww~?4%zS{UxXCKpNi6li7Muh#5hCeiL+X#bD7;f}8?E2X>5X?@v|UN1O)Aq{+ph7xp~qBqOcd}m%"
    "2;ys{@hVYwkA)xb8ua@f26%peaLc0<QziN%m#Sz16Vyrf0@hY@PzS_hZkmfO-8dwKbE@Wv$e?$gs7i@<L)m;y_*q)aw&$%%F"
    "~9EzOD38zKt4SVnBpB=m1%2y%9|Xy)7Z%oh1=aMvGYh-va829`E>YU)J12Ym_QXX<bwc<{{Rxrk!amh)?$EVM)=T(DO94hQq"
    "3ot_CT|vwocs4bgNtn821SiYDT{Lyvot!{9W772j5UuHLTB7h34YOn~PbHd3?l$1geAk%azL073t)@o2ZXuz6}@sLWRcma72"
    "Mg2x<LkZkwYX`BVep+P63@L;pS>1*KA&rrn)^TP;(^mzpkGalE!&Zv8EG#t<(7!eAnE$P;5zf5Z(PTYSkaAv59oXTQZ2=b~_"
    "-a1dVX)u_nEQ7wAO)Yi);Y&TvZHm8*UuA?nHRnp#bu;C75p}NO_56C$vBw_BDdKm{EROs-)b*s}gUF?tiuR1I#;TP$TxI!c>"
    "9@on0`jye8TKQ`12E#9#&%*D-10@T+*w-K(GgnbCz`qQMw7@CxvMD-$003W!(gEKn%=<nU=+E3<qV%2l%%<JhD@7(t$0}X5G"
    "<FHaTAU21Mt6-Byc;1$NL3eWI4;zIG$O(!vuTeq~3ZH<5CzY6z-a~Rp@bw1iOn!H8+gt&}tBEY0&TSK}$42!-#+AmO=BDWw0"
    "msKI$IzkRDUzxGhZ2IU_JL!P1WbQAS+&Q;UT=8anw#m?s1NEhMyoxZS;`A2PNKpVjDq&iGPglHUYby{2M&%SFQaM7^mFf?o*"
    "E_|lot7Yu);03#2Pe$ciIHaKE&+a+<WxsjoI^+OAkK{9-0g*yP2VX2N<GgUc_KR(U!lUA}<d)~K`ypnF6`=o;po|kJm;-ltJ"
    "lerBMU#0Q4o|~|O%AM{od>t;)fP(B4b$G^yj-(?liV50<rK-|>`8TQ384O%b$}M|b?oP2X`;r>W{F-jp<Ag5*{at0b(#d;>N"
    "mthsH^2{}B(|sPdfcvR=D_x9|A3VNsRLsPNSs@EY8uuJ?XrclR!w4DuR9WRe>7b7nfB4T-||^d`PwM(C`2JaG@||&8M*yzto"
    "_|F@OD+$uU>$R3t(J%YjkXp^31mB!D~#<X*qCMI<w=FAA}n;U3YqrVK4G^ueMN`oj;_k0k+kAp~ey8Kk)uL9%+Nn$~o-druw"
    "TPjV!g4kVMXRjSSCrjsqQ*&83zXYI&Jr&Lo`xTosGC1pIA#5V)<B^z|S=p<q6HcHBnKJD(+>bB`9UzgQw`w#sKEf~7<t3mI&"
    ")__-7A%_W1a_3S6d(JY}wXpmEtUL$xxx2EAl@q|#vF@a6sM*VRM;|cjzI0Y)gTUb@Ch~*9U%Rob01#jRCDD}E28dVD>qycJ%"
    "upw4pRVq}N3cuzZRO(s_U7%^YtK66}t4X~ECaj4dV!%tiEnY&}W$O+vB)}PEuME+K43UljwfQTUKqGmoc)jg-5(uWCS)`jlN"
    "{!ZD8uU`6t-Ga*1uh=wa@u>q;<%oHEvHoOh3*!D`KIJb5P!JJykQ&3cH$L<*5hS?h+tUB;C<pLS{6kB*xz1WC2R>EGs#Y`-z"
    "5-|$4Se7-6)h{sYB;45Gi*yY<-M3Oo#Yie(+_yO{ivv-N>YeRidlLo&y74<#rvo+JFnje$TSHHeUQ|-mChA!xD_23uka9P7T"
    "aY8E!5ThYco<-b>b-ref#R5&|=a*G}clDP*b!F|j%M!Lz#wi2<Ucrts9<#YxebyT8SleVyOoP|Uh^{-N!$xNl*CG!`Xh2Lyx"
    "V-*1ywTY&em(uwEBNgLlI!Z8uO=2P0#N2q(*8H>46^x}Ca%gnJ_vuGo;S89wuF3aRbM!g&I3l({c47q{~*#m0Q9W1nb3E#Bx"
    "NqwD!%6lGNq?veqm7c?mS|<X?;mNkjctDsr$&D&?|5;BlcsKx$suT)rT!;Js{$}Sc4dFW8M}nh$V2<A#Ieu7h%T8gQYWG_s)"
    "L?h6q!pb?dy-h|8<{_CTApS+#~WaVLH(B%$kB)QBBAUhG!+m6Flp|^BqX^VmA>!15Ou=UGoOPC;1d?)bxg37d@Y4nqPU)puo"
    "NZ;RZiCEBQOypjM;1P#4S@TzNfg6K$pvnDfG5u?9%J-KD735`1M7;rU4|gVQoG5#)UU{d8KQ!iEL-<bm}=?Wt-XW!mC#-NX)"
    "Qwoy5lGE=L35op`cgi4`1~J46@*KV2ne?y{dmBn5CTThYM=R27s5-8?%`qM9q0nJ>sj#IhV?E3)<#->{^^MSBT`3ZRhZ#(~i"
    "}OXYo&;1#&B{PLA;N$8X2z@V6SZ;0EWX+ag{T{=46s-I?Wh+abjy@2UDIr?gB9Nn%Q8SI7(KeRJOs8;V#zrPAbQmNJy2Q7Em"
    "XO_X?-ksSL;Hkui70sM)c`J!*e@O3!a)MgFU)IJ{MfT@NXn=YB-+G5tiGynctpRXlcCk`x0$qfkUB`=&e(ll;y2I0H6;RkE3"
    "yD~Lj_JGNC12l0`^3i^_ZwaMq!T?hGF7jIl?NJJp_-$q@ldn~erBQN*5zC}!?PFFcdx<NnAd*}V{hg!Z*}CAsO+wTHk`rZ>m"
    "8`6w-ZvJYZ;Jsr}hS}0@3b5uCkxPd81$ZX+>sIU0@Z=VU%Rv>_nhjoJ4r%`qVQ*^+Z1NWB}A)A!5(e-FdNxKZy<a^W_ng5jx"
    "wcdl$+{%mbFK-DrI|oq91g517)r=T>2I#bC5?31vX<Dq2srhPb`jxpSHtlSIPG>QZoxmHyPJT1|7NZQLW-bgw@G{Zxr&@4_;"
    "y&>Fj3#OAijOoJs0AvMPjGYr$u|1F-eA-~<l&Dgo7SWHsu7w>Ko_OKIK&lr@O)7^Y+%V4Zhyx~_w<wnH(&C45bUC$$^4U=2>"
    "<ZO)7I*gf}QXd;^d1p`nW+GcGw;m@D^Ev%z*>egG<wE537sqUARTAx}z&DgFB0k4#`bG3E2ODse1<99IhdI{&enqd+OV|{xz"
    "O#OSUT`*}bn&;7D@?2|HnWcGJ3fIv3R`ibaNAZ*6>(m{h)5ZR8z@cFfz$o@TK1ONP|h>>H#Ia0v{$MkB*n*$iR;w2&o#X?mf"
    "0UXhQeu>f7U*fu!jEo?_XO7*ab%QpQA|($8MJd4M?GfI6!tZLYQ_pi`n1)A(ZG0to`=VQ?w&&+!wK*$R-s90S%54?BWgPT%("
    ")@^S3#i2mLD(9oJCU)sN-AhP2~|n2fWPMGdNh177epM!UtHE=rFQmd(xNT-k&j5eBfW>S^ISN}r5X-CWGesMr%#a~WcVrk$f"
    "`Cu7wb^reM@yL%%1G0;rNUWew(n*Tb{sh=&MJ9*w*PoS$3zms9Y*W+&inrH?+ncI{lq;IO8(6C=#oCr(Ihh9&^t`&78aWiU5"
    "sP@8@^Sz$6ZX_@m$Q?g<_4O~^Yh9wXIUaa)fO!|v8H;(}osZXAbn<}D5$V~uCU@&&i~fhl?__(7OQe3c(AZ#h3)Yi!<AOiRH"
    "lz8pTIsN;<f1(&+(|0;Fz&w!GhC8lFQ!a}zbIvow5EpUD;vz;%6az6ozEHhsjm+whc_{s^`d1L!}uu7KN`>j@p1<>R3Ur~BM"
    "1flR_ovS6f-aBnH}Fn2Z_P&N*TFNh)S=t%Hl0a#+f8ax+XSMe0TW~acmRW1OC2=5C*C*u;>A;u?oV#;pb>wu)#4JZ+fl4Ml#"
    "m!{jC0H2DJyyOpX`AndXwrHs13$v93n$p^pn79pCRQ8~EPT=Z)*0hsfY%gek=9+K=%2vs?9UAzhwYZ?h%4<01aZ{O~dQS%&f"
    "7UU#sH>7iluf;<b;yDIml{F$6ho<5>7r>K+7zZ(y~IFaR>gdgHF?`I2|@gzy-KduYv;3n|pP8p%SwrWqm>lVBEEz`Q~daaQ("
    "=9R3|b9O?+M|MVBBstU#ZJf<HLHA7Cj9RKIKVo?1B6^Sa<$K{a`#5DHF{0Z{$K$)zsC+Y3O!h$~A83$j?inw`=MZ*~dCE03A"
    "h5^H?UPm$Nt6N#EYv2C>m2E*@CeWG_FB5nuE>w|g^9_{-H5bC5@7Uv_!hJD?v}N&Rc@=y0q0*dUGM%ji}QcuS+-`H-kdzqVT"
    "rt5fbUAB3?$<3I!)1J=5~QOao!o>QWNO~a2z}+p($}zqPrd;U%lNFp}M4}!MU&K!%@mW+W~F0uc8w3ykO3GoYuj0M(>98^{a"
    "OhnC}nZrAeW70%@%;E|uNv4BXABg?-^SB*q59@NerhGG>=a<)u16;=k>xMFJ{{Y-u>ovh}cKUFQ|ZK^fGh?bX||WP82goV(O"
    "a%hO>>)kY9}@amWYsSW@6eBM;ES^b1BkiFZv4#SF=<(sLNM>DI49wmha1)o<=ze~gcQLg?fYv$(RGTTQNCgI{b)ucbGN#f%8"
    "<Bu6gVq@71uwuhi6lO>OwNF7}j?R;MRLM_iypgti)ai`<7;Tsy^uJ!<I&T4`KZ7R)9+DZaHI-BN0et?!rjdE4cvq7g705v~S"
    "v+oAwtkmHMiXTiI6%E!BU<E7u-oVgrHF9YOdc@~s4ON^Nbu`#Nw?uT_6(iZ*wOmIf!W46wJZj3Exp?mo0nr>^AY}r>Yr$T2Q"
    "J8b_8hJfB0_eB5Qbd9%^K5_FuhmX6ggrFdz`^p(1MVM^<F$$<^bRE^0>sE;zPC8np@O2S7TyOm6X>a54P^VAnx!CQ_EjTLnO"
    "5c175OD)6?s~(GaiPpCJ(7C)@4i4K7_AZ)V27@LW_b7-P?RcOL{vwQ1m{3pjhsod)Lrp}~*6uqL|tzTBsA3b&Mhc5=aj==9@"
    "Xw8$q6QD&uF_NF{@qDW`APE(t6q{3UHzC7Lhxu6Mh^{ug{q7fl0nFgm;x?_d>&CVa7fyCwCQ^Lg7DT%u^ioT)8RCMue6F*CJ"
    "e=Oehcr|po;AbiuN!nVkVFzZK{lR;CYt41f6av2M$J%cLM%7YE-QO(R+DcQJb>aHBCDg{f>Da_G$UCVLxEu;rO8jBJ`@O&CT"
    ")?#Gcc>`2ozKB;YBgbUUBWfbO)SW9k$iSd2y3C7tE?6i=VxIQrhM2x2sI9ql|-CwNx$|}1u+kXS(!ZP&p)c0p=`%gxFK_1br"
    "d*cR}81$fcw0k++dM9FK2b$WaH%H_f7?p^M#L&Va&4@-;=QNr!PCS7RwX<BP?@+|J5dXeTj4fJ+=O<4E8JhirI~*<+~mDB`;"
    "(fy8+jn{bs(H3Prr9U0FfDlG@-p4FX`m`v93gYB$w_fQyojTQX&qGxI!}ogCP{wr{V1HiNxq&mOq-e>7YJdmUV}J+W=4v2CZ"
    "ZZQHhO+qT;njoF--jZbVfY<T<jd+uLY&z^;uJ+uGt7UdACfgVm|0DlK;SV8>t_F_YMr7K&na+>{s;O=8uk_xgyncnS@s(Lw="
    "wi6(8j3e--upzzO^7Ig%@hz(7R@P!sb_i%(4DqRVi0IL@KYF?X-n+tIxF7VlZLh#idqEWkG>Gl}h`sHgN9Zi!lCHq)mK#g7h"
    "i#$#G4$na>pPx$9bRNbR5+Vmy{Hl;V5wf5-=+TcI)8@|rqe|{m0V3WLRogH7g6aas*wt7u$m@qs0ps+>;Ik%KtYwhvkHIrmS"
    "O3#t{MtkLcsdB7zQQVOTmi^(Aln^cRs9?cFE8Vl{k_Og}x1Qhn*`#E6LfeoF0tw_*N@n|Jl^s_oo#dJNyRG{Iz1k=at7^!7T"
    "4?+XLpitMJCi8&eXH9`0nf_*-Tq#;6^W?7Vq*p#X{5<hUv0sK+4bHU}$sJmF;?1}M><@F`M*13V`B4Ex8jE@^{&@QULp$C*B"
    ")M~kMj)kq&n<+AS@apN?JgPz_ogzZ};1)X7}-kHVQEdKI)5t_0E*T)lJs7Q53OM4(LR!qCG0#}{l{+N?!?O>$jqOJXj1E{s$"
    "Bcv=9Bd<~>9CNpH_@!~bU3b23a)vn4#1s0TK^Nn2hKY36QWw=R=ff}6vt64sSUt~`_M_Zcmo7dp5cmQvo-$&6w4VSWh8pIk5"
    "A6)9fv;}qWHp>``(6%JOm530yE%$GRX5o*`DpYIuJ(BS@Mp`uu>q;)?U9Rr$Rp;_>DK_3T^E;lov<M7&vVUKDg;wlVp&y?D&"
    "<(76!i_Xu=tMjc_(|#{&saOl0Id;NOc#^fv0qK;7NJ1Vv4^Ni(ej(NbPvImEe9q<q7o**PqgWX*)ILl_fD7B5sb%ko&hp2bd"
    "Ng=qSa#!w3^|qzF8XIR`GOfZ0q3n#)$IvhDdFEBqs51w5qh6iD&Z9{2so)pSMJe<8s92LZXVlvy;EKWmJO=xBEm=d#3t_zpD"
    "r--smQ27a;bvW6a<dVC7^yZG2d{aL%3())daM|PA~$WII0*3iF`FXnY0AG;URLyzEmeaJ(on-|*kC#XQ_0DHaOr2nO*gABQ|"
    "BI&9xvz@WbE<ye0X?Mw^xg=V0Ge97pCf&Ivb8iDW@^;HCfT2nTzq96Se=&n{Ydx_!tp3gD3blPkWgC|JYg8V8U-P(m)t&dXW"
    "pmrMU&Erc?x+ffHx%BLjrwiMLGo4f_qe?A1GJX2*X0)PwE<Y$lBLU6%dpT7NAlsF-TW2Bow3B5M~yWX={3gmkI(XW=P;hJl%"
    "T&L5dIGYntE7UEe|iA@TO5Db-^^KVn1@f!bIt@cF9y#s)E65syDvN)pjrn6H2x}{u^>J>QhxM;2)y{Y_eurZrB4E!P<k2E_g"
    "->wm1GIYUOQctJw3iaBpirpN|--4CVNNt?U7${a^&wU*{e$d@1p(IT2U6d?2b^=Fs2hPZbF&NqT)^8En%$m4yFBRdJ-4qTHO"
    "(`QzStl+_fBt9+aweS%?w1bBQQ3-?yUz}Uw$eBa|5=NVDz4{LFW4eqXu`B{FfyV)+x%Ol?&*oUr%9=}w6sY-sCCyyo%#k=d0"
    "`lyxlsq1d0{PGX=+8!f+rbf|;Kb%4#r`)AHVb>&uBl&d3B5;@bWs6h-wodfZUfF$9@sq-WxnvzH^A2p=@nMOPFYu}p;O^)B)"
    "q%N6bbra@f1im>&b*bET_i`l$5|`L?ZS*!dvm+DEsYK~#W!0a?HVGsr3Am%Sh^yDg+e|zhOqi)G2G$(Kv&Khk=irkLjc8ah@"
    "a7#8FSv*HQX{^*bCq=ZhyZyHS`kHNkH;-|51!G$>SfMGE`3o>S!C-RNQZLG)3!J272=}l9x0i=d{J(EC`AcXm+I{8wixwvz("
    "j>uDdXC%aLE}Tk{EqFBB*W%r5Fub9PHXtCHkxq{&Pipi6x|!GCnV)GSc?>)AlEK}&`=wQ%LD6bU!!HnnDKloEk8I#hTXuBB#"
    "*(=7Sd$e9W?G(t2}3hf{cU-0}BnJAf?)rT@~(wcK?BMD0dso*nfcM3i`4_e<Es0<q4Qg;Ie3$Xab5qfOzKJMralq3j<sHbk)"
    "F?$F$!7ye^4}tupwpf9ha(aA<U-Al{eD#0&m})-sP+mHM>=oaG+L%Pn?|j>ffCPU8w>K`>oA_y!C4!?!A=F`i_&u^jCJ8u2H"
    "I-S+V{*yij22N*--@V98Ax-~qe;vMxdKk?cJN;sq<f~37ea#tJ)hXLnM-$Gel!G`3IR!{FR2?+ui`AqpKVpguOr4oqIEx6{h"
    "&W_w>eo8&`t-HprETMYpiEY$@AxoESt=Vn!%*ATYR8$TR$VGl(Fz;;&3~tEk=-R?<W41&D}rCN>oY4<^yJ=!O1`>u?CzAwpY"
    "BrTl8v3t$z*bcnL@;8}NW2wGsv8#H<GYM&-urvoZ&Fg0FT!ce~NSEV7ZevqHB>XZWe^l{HZ#apVipUN_-HSH6Myu_Lb3=imx"
    "yUzo|(w;k@k80tR`{@U}i(*+h0fkcG{3=gC<_VVL20pZ!TEK*G;{8v^reGM=$7YnTYu&l0P#*7Wh^C;Pi4?JJo2Bl^J=n6R}"
    "q&hSyn`v9M(xMZ84nz>~mrZ(d_``Da8;yEN7|(F1BO~&={wxcvKW4<-@m$4yo^?OHiCqGwucR03HzK}jET(`a#yUhf>D!F*#"
    "HZy(aEiE3R>Vb;fA^b7I!T4l4I-GUIP0Hj=_Z%nyFVrzhc0y~4@+p^6>29=sL4g7fRHQ{0_7<~>ewKw%1SUoHN)>og3~z$qB"
    "RJeN?guL>Jk_9BNW9ISXUN`0!+e)x~0K_n!oma?zY?Xpc+%qzI`bgghm2Zl9Tm+Jfhg_z`y2xlm+xQ2KIJ+hsO;`^5z{$A{2"
    "`4P*S9gkAFJltKIwLNZf7o)$oG<VufrIKId^2Pp^fXUS+n*%{bqwQZrU?0-oHzIv<vgTONT9ALAzNEL9eNUbp{J*mX%VW1nL"
    "4Ft&>yXzPld;T!qo)a2J)!b#C$D(aYv!%TzE_KAAyOvkIttV%n~>0Z7X>y;v1urD@hz{S`g%M=#Uza3(Pg`V(@1-6+uNKSLU"
    "hMju}uG5tJIiLpxgIa5N_>?RQGT<d|B-8pz;&Mv!jMh+)C9()NhSY3TIES}0ebnkKtdrMJG+|v%m98PR`V8Nd+uK$4vkvj;h"
    "e2DW%T9y_(BVGdoVgpzY>{`)H@AKI(m}9lBWcau{8)jWCd4&c_0H$5Oe{(TpX%^W;5UZq(X9d#9V@W8E{X&cbY_m%s(ZIfS>"
    "z3@Fr$Q%=PW5tpL!|7`zH3f;48m_i{e*2ULo`1o5SkJynTFW?8G&>_&q;pDHlYEDJ@m`S5f-1v5#^l<Ub5plg%Y7fgFK%4wM"
    "Nj#dCPhOJMstc>55$aQinZSe`E|h>JM?UW!rjPxz18Kxrw*t@7xFcUo&X3^E*~McVJ4q4`JT^yME-)XHC_rmVp=!bNc9ypcd"
    "wRL3lAq8PMCAU8?>VqaVouCwYI`PEi#IWX7LtGdg_>6s>OQ(H%Yr=T|a(w^^Y`i2jIidy`w4c{|DiuK}nO{V>=f-5`w&=wad"
    "d5A66XbMc+K2(vM@Cyd`TLNLh`D~x-E^x1Ev>qOs%E~q8QUY5iv8Ir-o4<%zwa*=X!<heYESi6-3gA3q4=@7RXMzygu>AXkz"
    "?pwdSBA?|JK@sqZ$wG57%8wY2x5BV<d&RzVsxzsWnZ(L_3e%^2RL=Do>DWiH=zrpuY{zx5&wM_%>Ndvg(sSW^#=l6kbq>vlo"
    "{5HfCF91uD%^dT_p^fEcA;)2Jgm>=9r<3^r#BkSS^&q-7EwvFxE*6fEMK4v%CkM(d<{oY6*7dvr&bWCP%;3*5h1-&F*?~Zgp"
    "Qvu+FpXww>)|I1nF3C*!HMxE1QgxTH1y=VMhP{Z$*B`9{;E2X|!9#@-6pv0R9xcx<rHwt!GbiI~>IDIZ;2`7MKE5?yDpX?jN"
    "81^0#xe-Kwk$1>vx5A-1u{-*;LUe~3o!_M#X*&xX~ZYW0kTxi*j_g4%bbX1Fp^bF7w;zz#k-5iajdN7A3&mIn%Ohub@{b#*T"
    "BkkVxJ)m`<!PEU%ZfoiZ`&3^&VuZUH)hLEcWXa2q885PH=wFZtpct$wJKoFu7B6R5Oa01`RO$-I{fcE@F5G7GftlgXO`9vPa"
    "tc`XOB*&uC58r>j4>N)zwq(ht(Um`Fe?WbhZX=}3K8~Zn_c{w497xc74jJEocxyPz8=XBH$E2Fj4o$X-WY9%UM(0DuSI>^Pr"
    "*Ucf6$$Q^&&BQ!>J?j%xRQ?{=*jZ6#foNlwfZ$<+brpi6fdi0WE+?N0LT2@aGVEn~ODuM4lF_*N7oDNz&|D+5+tul^`lnb-h"
    "cf|E&KsT@@&B4*D`)eBN?}tW<ZI`|T;c?Nh~5rRuh5)qHLX*0=oCj?!yVytx5kqX%m)K(4s5-0{wGCg#-q>l(Iu=!8}VT}*D"
    "Ww|e9=@QkeaB`vsA5pK$G_aTgSn~g1m6dQNaf9fUVBe0ZJG?AT7q3oKGuR(WHlcoWwxM2MtU0w1Z1)9wu>t0BgsbnRnIhKC}"
    "wwUQRuN7`((?10hLMKm)^TtFHpjBY@vPF<i^X2xbis?BAYh3=Ux#n)uZHA7^11<KaQYXtsu+EN~l8?$Xg>xswiy;#2w)j#O6"
    "XT#%qZ%pUM+>T9FCf}&@cq8JW*63!*k09mn?2lV>T&4u@T?$bHbG#jTX}4HL_OhnS^n+g5Ohj>RJmH&R~rc;kEytF`M6rsA>"
    "~;Ymde#1d)I+5N;t3fSy&p?OF-=wRt9o(!=#6^;Dgy-J_ZojZhlknTUFO}o+0w%n*fxH5u65mKciCELE+_~tPt8210p=v=b9"
    "{k3XY>aq@|_dW(d87^I3XZOUI-hmoT+d?vEQ-9AvX8maTYUC1|aFC(A@nNv?iHN1^g~Q}D&wd&VUA?`Z4)Zf#1@+<uQm;cgs"
    "GlZl>7s}?!q&_3n+R7oF!QfYH2l^+QwqnADD4hp5xO^@XT<-lP}n21CE@bpH!Mr8V})BE+=exIf<UEO6xGBIz@(;?S;n#zZ_"
    "AQ)+?r{{4An1!T27U`8R)j^P4P~T)&bPoURDD-k61i8E29G<cM&r6ES53AB%@F1z56hh0{Lt7>itCCXPP^9kM0JhTm_I2!%d"
    "jVc3&$`SVe?|I=4V&~<AssR-)txl=WArMgJsk)YTJZzG4VwVr>aEcvbum6dz?!4w{tq{XAv>utR0(vQO6B|b55$ZTn`1mobi"
    "UO`-_qlg{GRxf(BCX%@+HUyNv)UxSp~PIn;9DOu*^57e_f!~|0=XH($^E(NDWCq?!BLOy=vb~w(3ANeYO>%Rd%u+i}bGw70;"
    "E|>X^ywSrq>9OI2kjkKolAcuG_P45BeXbb>3dvGvi331qLJ`7FVsa$ywrr0j46<RykQ1Ug??-QDrA!FFRm9~YqZYWnilcO+_"
    "Ji&6c|c3A{q013mAIMiXqVm_Y^TneC2z2B`7XhJT~uYhEmILmW4>`M-KFcwfL<fN#Y+6q<1PC?wk(~T-t3~hLyN1x^t3tS89"
    "6JW&%@E0u7_C9Jvc#1z^SDP4uTUAJLc+h`j(GY3%`ySAwDwkkebYC(ozb_tsJx&Vr+ELM+Tgfb&({@%6^cY9ddlY-3I0ds{9"
    "?nX||KJgVD{kKK`}tS>;s2>Wy9HQ2_9{2>{zrLaE%QUTP8J!$$&yj6Q6*d;nY{a`LTf>4bKN}Ay`W&pN=<vtkco=OlCt*}h$"
    "qk_KBKh>@$6Y&Acnt`jfr%=q3!;@N31xhkQ3ZsMc3{e@tdK2FYvrz&v$EkXPWj~V?tLS+WMnSF9-PM@p0Cvc8p;ZHbSx|UWg"
    "2uF~yxrV?O9?5bbTzMz@{hlCv&!9ef)f38dCWDNts5iAzB(K~v!gI9m@SGO6%Ad))8U<c=s9ih1{_h2^LqzF=9Jkv+#OUPV_"
    "jkumRVQ5huBIu8EY)wD5PKg*n8;e9xOn^}h!yD*%5J$xs<yJNkCdbHV|&wun<vpj?CspE=BQ4X_9o3F|0s7RlDT2_ffHOw-_"
    "H1OYsktd7~vQfH+KuUz}W)juJbfU$iLUzI&_Et4b+d{8AJ5xiwJv)Sc6@U&c+APMD;byyw95>qs%?gar8(SjNVB|Fw<FBV5_"
    "Q5)j@$F+IPRR1_Zr^1)-mc>V)Uz+;vu;xncE<fmB<P+Ri=cN{8OhfY`GQ5m9Q9l^o@i?SV*S}p&rAOyP%tE@0+rL`&YN6!;*"
    "5vYtv2C_b>qbPay_Q<N-+ulp<^}|!>S4$=Ac}1twHhj<h?$ipaO+@C&D%x2_oL}ldM|uvpl+)GL0@-8t%M4pTa0RQ36jtx*$"
    "NC%p6oYUT=kPpT#pkU(8H<$)xb+u>nP%p^|Dn=d=I+xgG;k6@NOyQJg(2h7<@98pc#{+IM{V4=GI0=}+ujG@LXn5lTRxh9>c"
    "EL2*@6X`kv<io!UsH-sQO2=>)x3{Y_y9a*B{exx-XiUpGN<nZ#WSLGQ&+f`;&O&U|AkDhN(M~4SogA)yTu^B-Jhb+I4lmqBt"
    "X0{oRdwR6Zw<}5q4YZa4+Y%xA_9F-`fbuP}vqW=@7ORYmtpN<Q=q|xeH^sTL5^vH`Kx;{!>#)<xzQ702Z{;CX5t%f+309*UQ"
    "g~n!(kX&miV*yE8(+rZlHt4Yizm@sBA<CY`vG3pU6sGwAqPLBG?~1LM&LcS?sm0+vc4>(c#3PGvE(TQbZMp&&HR(jqUQ$8>M"
    "zgy>)rK4`Afd3JY+k*YhdHqF0_BBwI`&0<YcX|)wDSdDb0k6=Ps>7w;|mNzJI9F-TX3*Cc(=aL>Zy)=?s(q>?Hkg@_;v*#n("
    "p5;lj+D-mPz|?r~|b$UfGQlW-z00MFGFO?tSuon2MhJU;!1;hJ*n1zR#rTbfO?4dqsn2R*kjU!AW6bZZX1yI{>uP7r?$k(b$"
    "O8)!o`IP}%ocXq<=ia5;O0=PQho^Fdr_MbbdMva*1Ky*}oDSo-oHd#4jYz|#Tj^Djk4JS85OB-4>OPDcY_z7mrAt_y0Dv~4d"
    "SWZwfuGy|@yedT&qG4X`i$^?-|C|TyQN6qLU#I4O-|vC>qgMMC`Zwqe$@OI~0O(yC^6-)ViR{JRfxPxy8x%>Ps<>na97TkM1"
    "wKmxoDo0RQ7U+#sXa7=8}lJUFnwstv%L0TR%tDE76<Lx3i_hKuPLp<1*k(ii4zCvkhTe_TYmB@(=rFBJ2c<dSIKS+j*b#H!G"
    "au^Ej5Hq%Tq_+`=0WNHaiWgaLj<+-DItSKeq8&NJ)EA_;)AtrIG#B4WLlz)_HmCEYA<0qoujWlt&nY&w|%By!^uGMbruY==`"
    "hbMdF_w1nv#n`s@8}kevtU>&V^0DnK4K%nV5U!V$cYXJa3<r!ff;7yM^KQ{%IUv#jGpkh1QQh53Oz)jJ$t(7l29z5>A~Z<tY"
    "5^?~l^{4>pZW-euRdkB`&9xdMPT^qi-r(=g#nh9>?f3wdEroz>M*RnciD|ON7S!Y@~4_!)y?u3cVnxZ8X+4t3X&buFZjd^f6"
    "r)`M*U<6uVnRGRYM{mRT0xbUV|2fFoPEP)CsRd|7AS^xGBJC9whkPbEBROg7WI5-WuTH!kJZ00D?v9eDqi%?c8|&qs)p$cye"
    ")fHF^0KjB<=+tL<x#$3dsS7(&L<}buU<$$n>!5>_wU-U^wZ%c=@uLA+{F!^)X#S+?-yX4Wj_-u$HF<`Ppt&YSYZp`0}Uyk%`"
    "M<avZO)|1gbu+DMwmg3PSKLTL4y*DT?o2YgT=1FKm+YI|j^>#Va07tSEN{2YnqARt598H|(2O8qQJK5CdC(Gsjv0&p(Qhm~5"
    "U{kaCHu--E+C+x~@VLA%BVsA{zr2UocND@YoRM=Ld9X<x+fz%jq$DGHi<fVMDNo*m}_p*Ei2gwCn%U|v9Y;)yfsIc+kror;d"
    "*g*#flp1#}u`71#0*~hAH1NnY2WA3%#&W)qj539?|nOCmX%*cS`umrN)>7)$w;UO_}*&p7<ko};CuKdc6^iFoTTj~F1)1{5^"
    "enZ&$Poopp?*jMVT@}auePSAMaJb}TtO{`tgV1Z<tkt2uCW2pcZu8XNv|vP4%Q2eU_8G~W?}&{3pqC*ZE+XW+HxTpq=%$Z&S"
    "9AqWR@84nh5ehmT>O5C<T76THe^E_#{DmdP7xO~2w^1c6_&?Js+by5bx&&@FKtM?Y$+|G2;gwEr7`&?+Ok-^gJavmRki?xg;"
    "|lz&3an=<Uf^hMx$!oI{9l)u+!2#iB9DKtsc<U9uOzSJ+TuV^5fM;i*R$~8l=pRt9S2PK%{)uGN5DmQ1Xq6ydZ}y?Y1C4OuY"
    "WG7WF#OE=3=%=J$h&YE^p9?jzc|;g|?V@<u|^PcQD@6@V+)qYbe2Jq$BM-?;|b8vfCS1h%Uh6<>f<$P;?R?s2VA0e`qG=dj3"
    "y$<Uq0hEV8-(hhq!N5Wh5V~-^NlxxkWqfU1K4-D#-ADv<3><F+^kO&IX%kQs!bNZ*dkC1GElA8@*8}<zED9^s0!6NLcw|Oj0"
    "Oa9VdT7VBDcW!Y!CRLs@0FwmmtMZOMp(yP3?jr%DFj<Cj05G@_ah=Qv9wQzy<+?rwsTjpw!L*dD?&2psmQeQJ9E|kFgBk0`H"
    "305?0bBFkiqiwS%xUc5wr4h9=XP=71Qs2gM0~X2*!9(LN3P}PVl7|2-pjEzQ&w)3*MsjJmfGq*hK?o(o*FCpKc6H|1k#xFVy"
    ">k4LhaQ)nPVY4!Y$s=klo;)4TptGJ`Rl`cCZom*D7Gca-u|MS7)eTJiLl~qU5ff5{oKVqBuXcw9(;9lC7Wdu9EDY>&_T33)d"
    "WG$%a|vG5#^DRVO3C7}75Kq^K<-w@G}^s;<oH$9hb=9nc)|$5eQabOnH-vqFu%qOf)Tu55Cgo&L+m+OC=Rt2890l$W1Y4v~e"
    "*=CACL<6*4)RJ3#@+f6RP5y{?!kS)2Aps=w+U+B-=nP3NFJxw`>>3EYeIUD_xbz+ircUv#bbZ{IX+Q-`W{pZG%e0Ga*xZ6K3"
    "ELXK!?&2A`0?<M+XEi{s4}S8ug2;Y1M0Y+|*sL=LNN~NH&qnc>^^bX_1x9ZU1Q#(gJe&PBMkn?bjQE-kl$9GZ40dl@)}iR%3"
    "OM)+{Ws#kwR-kxT@<e?8M{c#Pg*@B1tNSkVr49JEAjZ*2;jl}?&3JhRN=o>m<ysItI^Mf*<GLw(lOfk&vZ>A$66PHTTiwleb"
    "3+)2y47ELXk<}0d6#{t(gSG>7P;G*zZf@ewD{80&KlKuRkw%WE(&zbz1u&orxAXw&W{)#)0)#g4gA{eaHk;+$^mQrcL!>j@L"
    "kDyGG`%9-&pPlz4m9jjF1Nxi0mJy%VxPcVEKyG6vEt=OFC;lIq6A(;CVRNjlDM#x&t;pV1&M9xnWM>ip-tS3=p>%GXp+Z92D"
    "|(itjlZp|ALUbvAsLa1#qd19fE4kblXipRDyVZ8T>fmV0iCwX$=7bcg}kIL;G|JAuCMBaRa;`TPn0KWY&T|v4SIcaA*^)VO%"
    "H2}{;kx6zh)W1f*-o#xeV<RYE+8w_lu^YAmqGP)K&~xYtky0z@oDFJoq);^ip?jQ{<rwGYL=|F36L(Chbe3^C+W?dbU;=&A$"
    "Br+cA{BLm@s#ypwK-5*p>`J$MgERdxKliLt2;m4ES~Pm404%1oO(RykoA%yt$39`)wGs+1INa(^<KT_*ya;jmb#YK*wkR$J+"
    "j5a(Fl#5%pG5)WXRspxH?&Xx0w{W-`+F~EPQwub_Dx=wuXrgq#KoBgWQK!4hl{96da9yk!XwOMoubQnP8y>m&bwEmRE~^?px"
    "`f(8|S~m%1|$e?q2K-dF;B(*aN6`cTW4h|gQ(3m$*|@z<Rm|BHKm@e;Qs*62pDb=snlY;1xtRq27T10%ZGQ{qOgCq^^*t`=Y"
    "t1SKxCIZKSe3!G7EBr;;VRn%6u-6?_iEK`mkpEz$L4`?I#I&WRc?hO5&A>kDd@Pm!RHpBA^^f{ZkIN~oS`q$4$2iHw(B3iu-"
    "8&*waA5}(Yhrukf^PJ|TYn97*c#D*Wr~h>!7~r3C*6<LO3^vB?PV%3367c+K8%wCFDM<y*Tgt*b0bCJc2JKN@QrWLx=_PiEh"
    "@Lte>E;fd-G#E4VT!9+9-_U*b22OZkOK_GWYi@hWs`T`fp?wc_`m)P58DH}kMmwXK)ZG~dDM-fsv6Oz5h^=T>hNNHP2*SzNR"
    "wbJDuIi8vldaxIq}W&fs8LwiIxRuAQM{PHxOkfC&PZGZptkDU(C?|5zMi4+TC+({ds#ZkZiajzVg~~ffM8tt*VBf%$<Cql~t"
    "OP1fHrQ!Z|};7-e$!#a5ayL*i|HiZDDV|E~r4F<L$(a5Zb|{WUULF!z^JePFK*8MlLHUTA61`iZg9O6~i#{cDGUyUM+h*=}M"
    "{K|etmRU1l!m!u*$Wh-fMJeDChU*dJ9`i}g)jQXP9NN)n2Vg)PN<k7b+K)@L+X}qpqhh+S8Kr^!FF~{Zt)d8`@?4lwdjgsu1"
    "l^lXCd?a?l*{v+T=_juAj4P(M5^0DrK#kg{o|uOav}qdF$H8*u(_KFj!*g^f`a9>V4<l@vcBOKLDnH7}W|5LvJfgQZOXEJ!1"
    "`;Gt<n>p0DE^I-X1}PQk<=;fuXM&s&9kKRX?~j)e{i^uDCMF$)I1CaLlP^j^5afx5JAgbD-Qlj1>y|O!jZZmK~W()PDdZ);0"
    "H%$`0~;13yDJM!4Qkd*>L56G48M$J)I&)Wn=;BAUp51|MZu=^=;)P)oidLH-KA_g+0kkn2RkUxK%(0*jw<=IZ?vqH&AEa!h0"
    "W2VJe>;w_)rl4PmSg=t|b=fv4_D;P5zvudo#Rg*v~Bs;lh`(6$ag*j(#CFKqpq?f3xpU$McRaKHH5s?hj@au|lH&g43~gf@j"
    "?;98J@WVlSb+~!cTgQSXDrqP(Vci@=PKv64K*n;=eHKv?<X9K|R8L$kD!ip)BN%=asm_@oVK^-jah)vhbztr>Ze*Rh+14x*1"
    "-2I-5md4;ouI4R9oeyE4#-V2-A#QRm%o#dlC;x^X@rBs(9o!t2Azkh5y@vPgLLE@Sqj3lN`t#Ru8}`7yPIPUS4YkVRSFK)#L"
    "&wwihE+dZ_j5}ad##&(w>-BTsJsc5IghD!(a=HMF<o~x73c(~*E|_-S!<V8ip=b$(dXS7+8>R@ix6`-sgxn!#7~^H>jPA650"
    "UBJSGq-NJ?}^r%CkTJv|&kWdwev=2Z~>j5RtozU<#(0m?svA@B-cMKW8MNNaBwH0zegz;E2+HymrEIC9E~tdEa&`Oe5g1zUX"
    "uBP%CT$I3N<2)EirRJ7#V$*%9NNR>r|gEghmhmwUcDgLCD&nEYTx9JYu2S6EUyn9;<8j5b(Cz_V)a9M+c_D_#kk^qgW|@_rB"
    "^_7?P9>1!T>!*dmU^-uY#OT}nFgm|$o@Ww7G$<#cS%6@9l!qC5(E2gLHZz`g&cwE^Os$yCzZy77HHj);Wi@f%20Ibq8|JwcK"
    "oTpSA6;@1Xz9L3G&?i4XUwXX%O-sBY#Y7y+`+8mnGx7!Rl3_o{LTkTI5~-$2L;?O}9ecVxA{~mNt>s&n(N(tH{!WIg{ToKXe"
    "E*Bju|7wRw0rQo2&m2liJMx3G;pM^W>PU&aA0KqTKO73PjU_wH%3sNY>vp3CN7*1$mA4024~S{4bvhxKJAb0`gkxx{qt7rDe"
    "ae*H%r6*m@UKrZGpqLjaMKG;v&L7bfRiv3C_Ygzvzy&kV!)2aDC98NeO!>S(?1MAe1cf(8iWQq&}8J<W7i!;KUb}IFg>n;G8"
    "Wf$7IrP#>wSyi~NPEPKk}vbH}%u6QvgTu%*#wwBs||_`wfW7W^x$d_V9@UG08Y3}1*_4RLYa<@bl>+bJ}K_z9`uVuC@lqf}*"
    "zz0GYBZW~gRRT(iLEPLa7Nnqutu!cKrgz1U`y89rA<|~?uH3uVs*tP|kz?Ru`gCZu;Z-=-PY&kFRMGZ{*Eoc=V?0!&ACv*={"
    "qZR@%5Z<=DL-ks7x!5mnIwxMfbKYbnI;(*z7V*iqJNiXLZgD!XEXmnV=>7t_LxQ;9h@^4<5)RWp!f_&>jTR;o46cs9qni&Hu"
    "t`;_$@Lv-()gGz<uF;4l$)t8fg{5E;7b)#1W1eD6GIV7f>mXi`hQMf1~#aRxfn<OCF9KIXMG1ihqy(4YKj7y);Y~-(?^eB<)"
    "%gFL9Y^lMeox4rd?he!*4w@%_^2(k2$@MW8%Pslyso$L@+I6H8%w++}ptggQe1s;-u9XsN2<fv`uZjK_9I1X^QVkIGZHJCk<"
    "@KUtIy{)6LLycnfV?mw4cICbs=O#6-P@lr@5c-zZf58~Z{(Q-~nY72kK*(=C^nkw%{fOKdRDzQzqMuu#FEWw>N3qH?)S@%82"
    "Ik0#=|GN@?<lXAOM7A@62Vv;pz-Ock^41EKU|5YfG|0&e1Gjaztl0ePZe2woi?-eI`SdWtkpS)&~(H<P%4pEC&-MgvV;4#4$"
    "4Z-MCwQI_sN7shE?P@f*rwGMoVug{C_H?jLKQ1_ga_emqI@ZaYDki<;$c@M^f^z1ME=BB*+S=b)R<SR8`uL<>jKC<-K;<;MK"
    "mWjQ3vnh~J4}@|ndbh4@@J~GW&{{4m^_V?+xtlpF7d$<F{R2i9g_DGR4l@Y*z6BsL}x5*d?PIH?DK?+Rx*0LV%-SC%~uoFSM"
    "|QWK+88sRH>7T_u-I@_a;A;3YR@|s~$D2*@$4-rw*F#ab?fK5+P4qSFwbOkTQoTN;(G=ZoeZGnBZDM{OiC8CXF<Ak`s;g+F&"
    "VtS!i~Ynd!_Lx@WAK5TfN;Y>7#oZdZU9T6_WA7w;Ifrtv|>(~<xWF{>dyZ%1Sx*_jU*f+6HH3&*NTEd(4lz|RJgWmZ>#ST9^"
    "i!9Px=$g6Z-cc$)U52rRVeHb^-FMS}+TNI%OBkg`kTuU{^1+OvpI4LlOX>vovI`U(=qeHm&a8Q7&6QDonM)q^_N8PT8osb~;"
    "Q{|3EX=1BTiN!a%7xX#IAiOUbfZJOouiSonHM_?6W8hhpzb*HKy?}kP1aKyjw(dM(pr}BFuON~QYH1GcuStM7mEeMWf^E80d"
    "mEd_z(s^&Qpb>g4e|U)o!_B7Ies&owle~#G`3OHyf3npU88pUOJCfEW`T~pp*pzZ)k6N_CH%h(38m8>{FzZW0HLFx^n5;%D>"
    "%t+p~ma6<Jux1;Q~JY<rk&BuN8Zl&KG53OXY!4*HH52=zct<-2@|`VlV`d(j~y3^D3@Z`<9Kv93HZqLMoE+Aq^+F+`FkEWQE"
    "0=9ZR428>c(?RMS}PW~d@)tWzIt@F?)U5b@WPFA;0fhA!zDDvzN$;RriDnxQi8ND@%u9tC|xZ$QgD-l-f(UA(f%s-PrUHvNa"
    "@rRVW2Srnims7z;LYh9})yDO_Rk!<?-cU?1#=@+>#@N+{!{dgoWOKSFS*J!f)vnu_**2t^H;ZZpF*>@02?Dzzd&rPQXXWmAZ"
    "M3YFAyMA*s;9f||FuAo;?pnE>#m;iQ@%;%&wk7ihYci20*^K{#2u>p<TnQxC+$aZDO%K4kA5L$!d1cMR2W6gQ#r;|cH`4Ogg"
    "NQ#1qup9;#pDPml3u!~`2*`z#1n5s5*@Nf$Pb20BlCuMm7*b#%jK>of)B`PJ}Nkqe{!mbdtyR8jc+6vR~NeaL2D6QnPnVyeR"
    "2wWf{AlN#syOUT*bYd!76nK%sMSLx*;tOjt)L$7(h`{GBZ9p6UqeBNB3HScCqV?zf)f*X#vQeqVPJ$2j}^8zO$qG@4wk?jBl"
    "EF=7=fo_Afqj196wVUBy+iQfF7PLilR>+5JL?SRbyTF@7u&j0xh@^5CV*uV|BgOSQ~q#6(q|?Dv4>S5SUwEWX7E)s?aAUZ&_"
    "(Iu|@?W{;4T9tjx|bKfTLsD9pbyk;C`nX3F3F<zr3ZhyW&{!QsTapGQ3%1pIN!k6Vc_b*%zxrGG-)aD0=WZ5&tC2%{{*JkP4"
    "c;Fd-pg%qi7y@0DhY+aN;G9Wwa7a*4_E#kFfQFGRI*2<?cvr+0;2aL-W+IKTn@t3hP8G-<8Ho2waKA2IR!!5$!XE`Mi+(Nev"
    "zS_IA~w;&o@^hQ$iG;Jqc;)bk1F}9BWx*YI@@gytnTrVDU~p(ZQv)bhv)i1IItVMPBS5E%FpAygaffpIB6&Q6|dnkhMHyn`}"
    "*C~07`Pld?u6%d4j|^tBN%J;b5+M-b2coXnKiC6~tW7Lt&Tc(dpI*G_d~}O)UKNBpyumPZa|@9cK@P+LB<*BH7URxm+hbtui"
    "s}Khuo$Ps4(~WVz^J?#0Pq9jk}ZWq>D}e8t=3P2kGvJ1@;l?~@l+cxh@tdW;tfW&@LqNOGdf#a3Zg0qf^*gLJ|N`D}?&PBZN"
    "_RwqWabg!frr|)Q*Z!G)g-6{2_q1BIT<z>`!Sw(j&uR4|J4ft|&G|^gqn=#`|zce;GXz2Z>!_Gvu?Z03NLCBb?>}VcMfZp%3"
    "M-hv$vne&Mqp`VyJ9e1>Uzn1@1XX;V|I$Lxmh_kpv-&W=>(Tv3$CnrUw*sV?wEovvsRigOd0P>GOKPvwH5RqA9!Y_>y{Rvd9"
    "w7{njdbbC3Y5@-C@NGQa@t;0Tex2)24=-{!R~8a05l9h`PFyfFJHGVcbV(Ny2+u62>(Ju@DG}z?=)AkkdCr+-soR41<Zc%5&"
    ">{}S<(8h*5>c|80A{{SE=ertK$cTIYr^DfUJ$!5YI3z>>|5#P^@D)02m|>8GoU?frJMvijc25meZ}C`0_LNPAN?|+t#-MLd$"
    "_|TmvsoJC5_ghT1Ly8|Vsg#cijA+7E6Pi>Gc*cIG+QtGKGfg*q`V*3Ovy?Asznw|1TE3C=<4ViyD!URFO&-zPPA4wg52QgGh"
    "R)!%2cz~=(OCX*fO8$prgiFN}|kmR=Rzq_7;tdMu5HAiFx7a2cQYgmY%ef7^>7$BhoCSk3MAmj9ZMq_7Z40PUnso4k%ZhY60"
    "NPGF**hK?W{d%^-wKN*~M><~+_9DBJ^wQXfH9eNXmxdJXNrwwd-O9J+KWRMH6rK%af|*`B)_#?w<062oqq6~^WQW9Le0kIoZ"
    "<>c_0?lN<BF<hsBD3?0P!(Z*)&&wOQKt~IUqX>NI_{`Wt&&elA9i4?5yZbW{p8v}t78M>`fcqHlLlqoYoGWxlW_1vg^U=3$Y"
    "a>$A^*EPE|*pNe26j5;&P$)a?BxzGur!rwz)#HA3F13bNG0k?ij#qEpb!8CH+y&KfJxksp-VmtEedHMR#g=r>sBTD+4J`&)*"
    "w01&y1>6B<OEKUybe#?wJ)SGAOVZN>+iY+F@0muToaMJ>ZlAm3fj`fdP*C}OM(m!2N=Wmn94Jj>@cJ>Er1AFNsGPyS!K<MeN"
    "^^qTH-D@<V4N!_^D8tYCQ%(d&bwdsD|{6pcG>bGa<PBMC01OR9gS~4J3&bHKyIDDfl4SA%6{#Hj$eajq4Ry<M~43nZQ6y`TX"
    "M;920bp~6^F4kQ&VK@9;0XitmedWVR62Ul)q%EhTH5^&*dZJ6Pn-Cm_h+8ZBJYD%lusmmk1Ds)%P2|tBM}K@D8Qrt++OjtTQ"
    "i@M{V*yu!?^dJIE6at@I{KGb$YUijHI}(8;reT-tYGaDaddnJ@?pvpP~<w>RjibU+*ivdpAM}-lthKyk2noP^Fq&~)Wt|Pzy"
    "zH54B!mejaAXPQ`;JjKi9b5lPKpJnj9cQ36aCGW-dp!_!P~|p?TBcK4Xzn_K7%rq4%#t{y`Za|E5Ja9%e&iW4z8af8hWqOw?"
    "4}s$7Bj=80?pr7TD7n@IH#HdG#^+D+ZtAxf1Jd_}_&1ujWWf^$Uv!_ObPU*HS^3L8qmdn#_HhG;Rde6B-gn+eJ=YOrC@ZsSj"
    "zEX2C+$isk6AyETFk0o-wTG<Z2_0C<|s$P4}j1!VsRjyLx_l(I|nL}Fg!mJ&f-7iz+j=eZEAtLbdL*re4@B`g_p__<`&Wx~w"
    "_0g>bLe7B*JYm`hZ7I8wk$$3Zn1V(|`<&+O4SBpxO!PD-JXh&^N<ai#1R1)Up~V!lZmIlRQ~&z*@bkKTk;iyI<{Iv%MWDZ_<"
    "a_{M1NdTdvBoD16r5fzY|zh@&qc2xan#~mnSdfM)8vC+B`bj?$*=<R7x-d|Arj@)SZtg4S+_-Xiz4#J`F{=4=l=?kv+b;`la"
    "g^CXoFPaH1a{y+*Ib-9>Xi~8ZTIN@7BF-l${F5JxD1L!3eB^5s_4eBep~X`EyFLqCa<?^8N@&J_;bOhjE^}IdbvSAEQN2v8$"
    "CrWjfxdNH%kT5S$g_M7u9MY$o)5MV<PN2kT$GbV8l}1{j`P4GmVK8_=Vc0wp}C37d)fe>F^a9m>V_te-#(v0B=ptm(45<t|A"
    "OrNd%tOn5tLo8ioWP0=Q77=BVff%HXbi|`{uaIw>e__ow<VCMV#C585(@Fy>!A_C3WS1ad~lIyEes%hct16O1caz~wSGsefT"
    "mAXN?g=|uq>8u~u@$}E)+F+0!Z)Sg?_;=I(k=s?qznCjji4y3Iol^L$#xd>zHkTH}KVD^Bya?%xAqxN7cG+1qpmGX~o>($Sj"
    "lvpM2%j^iraU+(;D863%20Z_@&b}a#Jo2CNuy~@%!UX^T#?v=2=HCTMSJOLUkF}~G-G!wzB@F$mjKNMtUT6NZZ(-C!WlSq$A"
    "wyLP*RCt)Bdor2RBpGDk-8!@Y!6e29XtTqQJ_OD`(r2x<VzFNL8iSKHssy%!s(lqPiCqPYClO7{sBuBCFI5`kia|_wh+02M3"
    "%T@$z_!tyX`!AMhB4nlPlR$;XNCJ5>{euY{I-&vCoxe(j$REtx{y2Nd&tqVs~^)1ci5gd8#~mZm0=FDV`|bI1lCWCs1MwV;2"
    "s1_rXZrB1N<Z(x@@g+@|ssiVgY7{YxTlV(*>q_?cJ6G@;gP5{>{RlpcAiy(`vNNNGHDo&zb@ofU&$3302avZ4Bvc##F_8wb9"
    ")#%uu#T3Pz9&ju=^xqsDPdi|=cdSU0&GBSIoD%VB%IPD_0@3c;Ahmob-`v)$LIgC1i_Eq5L#mNa>Gdbj19agFrLcPyPrZmle"
    "p}7*g1J{l2__uyP{05@u!@<`T>kwC?MZ_seW`aDs4r#lN$}mtPdYY3#mU4Vyp5Ht3z=zvDQ|BVZn8^h8evrlJcrGc%}PW<pd"
    "-Pk{)u=etqjMuiJo~IVhujf73LAbj_5Y}uUe3y*U0zWY9n7&(>{90*oof1zyKb+9#0*ufMC|DO&bDhU8Kv*J=OhcfU15oB2G"
    "vu0TPVK@deq~tmm@M5ADdk5d>ZY5a7%5;@<m%%_g>{G7jdghr>?1T6BD<rhz|oV`d=2<?D()$}d+sd!X@#_0tfOyO$HL3nw|"
    "UF`q4Fcodp&@tzIlSGodTNY+1ZLWcBl;PbRwXrOtHa1vPYg`d4^FM&3Q!p&F)aU!}yrzE(`UM1I9-^(*YiA_tKMJb-O9niSB"
    "#{g{;V<09n$wrNSL7LmJVKr}4){*MptOS_%cIsym`>9vw6p+?rpOQE8o==O&^sbQePY{Ay_wm-GNbvZ~_wOpSmYv*ndrya7N"
    "PY5WxrbR`{w?mf89#s305Rzd?z1h;cXy|*M_0)N=EmJT)E;<72FGE}k9=dIj0}&WWgh6fzrFECa>CCY2qLjF_I~mCuXxJOII"
    "d*tyfsIqB`VK*^-O)HpG_1=S;iG}VA>-JUVrt5-l-|WdkAK%dzY%)@@d-8vF<~`o}(|8h70G&zVx{K{_$Mrj$G8lq-K!Bbwo"
    "2{HzFeMz?}ivxnH9f%H=i1Aelza_V!b{z6Q|{?AhG|?i!e=vZfOB6lF6mT>tTI9eYiZI}(O-w$AIvLt{)Sr*Ij`_*Ci{NCB`"
    "Js~A+T&d&U9ew{{I?s=bTCPKSZ(RH<0IwaPd*pHl*A~Ab|XN-F!^6xY;GAhE}{sWx<7utOrG_v3E*Z>K?YDL~=VcIh>jKR<Z"
    "M3r|}Tc>D60uiY|n^0*cFh=~7!K|-Od_m@YiC#&wyE};D**x;^Gdj38BE@ujY6-mlU-SoU(9YfZyUl($K+RpGQFn{4@-KaGZ"
    "&D5fh`$o#p1sz!dlg8{zPA>2AqyTL=XF-|R=l4xz%l+XDQ(&}3?5t(E6WF66Y<4&+_#Ve&<e&IbRdjkYx#)uv%uH(YwZReik"
    "8*})BO&hh)-#M<8)3HTbMt~>JN{fYlswpEx}8LdBqLYzf`3WZ?g(Sbk?&JKI38wVK=L11vZ%H%z$w3{0kP8P*h*NbO6(cVCT"
    ";=mrr6888gN|1&Xia1RBWvDfEXDG~mkXAN~@{;J=9;Aq|@kT99_p@Rkdfg|OH`-kRX@9d|_EZ&Qc%6)ld}V1nUD8Y{d=a1^A"
    "R)95b`5yZ;GN9JHwS*CC6n<_uF7{MyUdRkhh+RK*Mg!Jh5O>|b_LDSz;7vrr>d*pw4wd-vcQ0;N$^lw;6G+je#H^qiDVzE6&"
    "$x!Yv$(=qx7#1^^sxS{!_=1ms3kO+a54Wt|&%zaFjuf2o2x%CGB4Vbah^In=C8%7-i<WNej2Vf{2i3gx2U%Nyd2vOCI2R^-Z"
    "joiH2(!`L=8Y>3p@fj4^IT=g$3(#_odha8S@Vs*)MV;axi!n}K$+j1yD^8)Ko(;sEy*0=i9h?BL6Ov{%7Arvo8umV{`YinHA"
    "<G)pD+Iw!>lb&nW-Rz``PSE5h@>9^<psX;cA~+7VN==-~wDU+oG<r6&g(~40bkI#cAZwpHbX?mp8h%O=YN$iJ0E>l4*Oi7*u"
    "X!_#))2?+k1Xn60{_DT7W@amW}z%e(<kdsyDt$f+@ZNzo|cV61OTN9U5Ze`>~hkJ-Ag>Qh8Ph`WV$-^qL$2}2hS+gc;Hy~w+"
    "{sr>T|twBU;Zr)Y3rA6htYI{m87@f?GCU~^fIwqManyAaZ5H;%El%y6~*5nIkp(8m9PqC6z4+;Bf%am_QKB)`vFWv9*i6M9o"
    "i{#)z?#mwD_I)AMm91QHHT%@P*fnMEP%<^2g~VAgmjDo<0M&U|{)nZ%nhg%GPx%8t>&tC8;_V-6ynZ7haOaQ$!M`s^`kzjPh"
    "^fXl@<b8rVF@HJyU0{nORuSaa;F8Xekh&(EICI|Xe&u9bs&(Q%{E-P4^-3QgC<$-9_fle4f3A$cpeX<jT~<@r5@;`mY^cRF%"
    "pY!szOr#ftZq<+>NDAZ>xAZoQJ-0{xtDx20P3aNlQW~tup5wB#s6ZDL`T(X1no+algEL+o;){m|IiJ-79&iWiO~5Vc;7HsjL"
    "EKr??KHIV@d8fxo(vBI74<{CQ{IBrLvC2z+Sv)~=Ks{B?m){AdOya2XNf#se<P^8j9LL4uOto^Y#(h_NC{(^4x&wj0E`F{mk"
    "XkAi0_TB#SZO-nAKzZubMjvIN3@?Xk4GA2779Y3esOlH`(!5cydSJa~7cO1BLw`E@TR&(F6fJshKLdjKM82JW?LV0K-TJx69"
    ")<Ov-HaV=yI9zcE`S~#+^QQkr(gcLd5BA8Z5m4*ofVh8E9!jlVO$5+Ui<!lZ@fjWxxF*|u+>HmdTbu+Dz|ncu{MZQ<-Qk$K1"
    "N&@9oYA<pyR2(oO*kgBnUOKwpjGq*n_*nJZT~LwHryo^&?}_g9QsL?v>#HQILD4=vH<qo6{_1VWRWRa-LhQ=mLq)xig}Po1u"
    "7_Q3j8c}Imznf=fDWuL*`$PheCz2Tk8%0($gmTNFc%)@jH7|;na!ls=l8xq%e<roqevThyWM=R2|d2C?P}eZBe{PCH6JdL0?"
    "VMb=GMv_>%fp;zjaS|7)j)#R*Ug=@JbaxIk4=()Q&26jr#xu!!f&73lUgQc7W6O#F$=k`m;bKnUH6{8B&&u?Tzf{59H^ci4%"
    "DKZXPrzo)fj$}`o1{#g}!H%<o0BWYw%v*S_ELOzZtamuN(*BGVy4`q9NLTjp70<q=S`2`77O$=i`8sokcQ*G><t5Y506Kj$J"
    "06q9A?<R((vnXXZW^lX+S=s?CO9i?*ieiu0JV-aQR2lWzRDV>^hA8@IBVSDZQ+kp2ZSc0vnT+0ME93kPO#WGj?DxSLt0m;e{"
    "hy^L%Zlr}a5n(QYK7j=dLXgq6cZ3pLwHzc<k`P96h*VDb1BRu8v^CO2_EmSXN@<-eHtM`CgXWIG(Y%bwOFV&^-qHYVJPst3c"
    "!kVaX*bgYcdd()cq8oKt*{|I)qxAfmjXp`ByA%b5n%q3;(8Yoz3kV7dhQA8>}+Xd9#chVwaUKOKg>QrojZp!)0cSNFNFy{9>"
    "n8{Sq8OJ~W=;*oAXFn26Hm$}2ua%0x&geFiD-(E*x|K~$S>Pbnv@&%!(*%#s=mK6s`jt!6{3x&X{S+=+m#M>Pv=@z^-SSf!="
    "Ro3-e0Q0HS1xA*cydiT3@d<~0;1?6x|akMTKnygzB)o?$g>~WO~)xD1cY}#_gMQ{GqMxzPLR?E*_xo)r$Rhl|^sgEM{FOG?t"
    "H&)9kwXYqkgkGK|e@Xa%ZjWn?vZR^XMUH&r(gg}f9Nge4PY%x`XYEhmIiIY#om^g>>%3N;p)6TQSh_47l%)ii)g<de_t3+tK"
    "^zHgo+`~uGr2JdIV-b}X2GCVDSl?Mt*D5C8qY$-tCPuLmR-D)9nI(O4n2;dSw;~eu==_6Z^vcWvJ=|7JB0!<drNn(z78X8cb"
    "yG}W1-TmF4A9%%_SD_7~wF)8m-X9ph#3ickdo7^otZA;NS*b4*Hv-WgZg0(>{Do5f91ZgK8>Jqke$X*+dRNKnJ*PX1k^hWZK"
    "#|!0`Xh$By{W!!^J`hc9<)<fLnpld`QM_V9jIRUIbbumlsJow${1a;=5=YwGa+nL4O%G*>E6{ye&aL^4ndW%mIXYfkWhb?M5"
    "+&yIP@P^u)4Tn1GoZxb@vd!bl9IND^Hh)`zKv|RVnZ^|-gOHhI5Cva~gEE}J%L=o_gNI;$nQ}Vaf`u*7)*fX~Hw?M=c;tGg@"
    "1bD7qMYf9Yh1GCi{?BU^i8VOY^;xzEv|W?F!o3?1OQ2h4NJz@?dymKh>h-Y7CeCuJiuV0PG>0x=2t$`ZoFJ-iXw{sE1PLgjd"
    "$n=In#lU#B_;TF@C&gIOU&E#%hK0W^(tZ2`-k4VtFH1*B@Asw5NwF3MRRMk<#c~?_tnmUU(Vr#jz}L#0V7CGAb-ilZw0W#-l"
    "e9D6<Z+mS7wa=$qZIVD$a<)Jisx-!k@KfFEy)Fl6DK*#_pxfI=#W6@_2$)Bu&XTb|L2{YcV@a{hqsux3-L$gY?uh)D+o37W0"
    "y`0R5g83eo7sco(6uFuC$D%+Rp6Y-F^6EnN1YtGKJXT}8)mJvGc+7v8i&k3TI~SjK3X-4LG9A0>w8Le`b^h4(cnK@t@PG{&g"
    "sDybwB?+cz6=$Pl_+1(jm2`exT@k+JPgykl8uW{4CVRoDFymO09brSH@J3`ni_A<Af_<nBAsB4;d(2#6sT4}k)JFP<zAA7PU"
    "#PU@VB*oVHJ6jndK&{b2w(DMSBhjZjEA9ClTs0q!)$!+KXRqP^(ezaTaW+k}yNkOM2<{ewySuvuhv4pRi)+xu-5nC#-9vD9f"
    "<tf(`jhuN=c=!_p6=?Z?%5dtrNk?Km~jpA|KJcOA}NpE+Hpp>FNnG(pAJ%SGv)2fh2)1PJH+7TE7vCktm{M_%ZFx*t2X4Wgf"
    "2%?NraXEB8A~EC)~;m65;=WZcLAQ0Y_8YyIMvFUQVUW#`Fb}lz+0K`a7UjrbaNjhPlr8>Kg{uSv}V5OwsO7GD@CYbmqQMMQ0"
    "X39)IFGg&*PIohnAZn>GuNmqrk}Xjq~ywoE#H{C;(@TMSQ&`kN~X>5zf7->_tHyD*uG|Jw*6Uj}CE7wLCFy0-MC_k7U;;FW>"
    "WCx|uP@nv0*;P)yLMH&+gUJ9{fXzlq=b!(09I-gv>mL*rtnnv0-<i_|h^2>Zgy8#d6N$Km!F93dd{-ht&#xMM6`Y<W?!O5>v"
    "-0jV`20yH|;J?j*7Wz-nmw|&B5noP&1-mZAQE4SyI;xh0beY{RTbU_=?xIKbDW*N#zW^DoVY1e6LAY4hLn6XLaNEYPK-@7pb"
    "%pH!eLqHjdvC>j=HXbd-)P5!x-%vkl^Z{WiSnK2&)>NE{+u>23o<Z=Y8Aq8B`hnrb~!nFs9uxc{4IWSp0}Y8ct>~`BbMGc`N"
    "=JXm+^QEI`tjUSuDLLb4_6oGL9K*;J!vwX+64Olr<pbu}LOo+l@l)*hLM$WEPM*h7gs`@`}`FYKGstpsAUHn=}5B?J=65mO|"
    "X$w|MV5lZ$sDkfr!_&M$J1bkJ~~X*<OhUNy&TC)YTQ0rfu)301+l{T>rHci?E!5Jb~~p3f}1rT*a~Vq`|*N_?qKK!qK3DFB~"
    "IT}T$K%}LeO3Ln3Me)cEw(t#VaY-u*AusrTqHte!3?#=Om{&}Va4SN~kJBiFZe^*(BCvzp)jallHm&I-umE-~@5_aYY-bklI"
    "e*@E|cEXg6UFHJlu&ra&yqQR{EZ#koo#T+oxgx>Qd>YI1Yk3g9O3%Gg3{cFkjd~7o?|93hQpz!)Gm4FVAzLITCBgpI)37kCJ"
    "EnG8AL_AAAZCA<+I+5Cz!!Ql3Ci>4E7YL4kt8(r$=F7~H^J!Ek~PnggCmErfdaVo@az(#^*EUi;4FAohuSjv6Fz0BIHmBP4?"
    "D-Clonq9K>4rJ)No_di;j6c``aPjmvUsOV0<Q%Fx8b-VPKZMrg6QIseC1n_W)<LxqjY~6S6Fjbtk5aR*D47)`8(ZFJNfl`0t"
    "D$JpUX8G0#j29**BB58mEVJgDl;zU-dNy(N72#;9Z&l3`$7w(ehKH`3(6_&j^|=L<>sxdY_X1+<$*+$0~UXY$!9C<I7Ho@q*"
    "%mcFH*H0vpspKAvsfFOi0nUQsUT>Sp0xa<)VZP0B^X8J8{rHAF^H_Cg0q?*TVQEf0!Fj2K2QrWc-NL5<?>~j{-UgMCcCOCRs"
    "Lol;Wum_+>ICC?OVgDqTXpKK|4|wb31#IEFUorpx$x4kfF7zDFv;7XUy%GcWsl*qNl5b7G$=PYysNJN5{Wh4X%{jrSl6-8l0"
    "`-7L8G+(*HE`r}rX^$n1s&Ai*YENI{8U}k(vr5-9IOA$kYu~{;MGKe@(SNqh2z3;L3sWrsSK}wvcTHow;|CJxdqRNm`jJ(Rz"
    "<8;9oRfMEoT^b{VV`uu14j!nXZ&+jef~fXih;2m=56#$i4gFyQ-Yi07;M1gnWJg1m+pmzDjY+r4h%Ms`^AVue-{i59QX%yEA"
    "Up8HR#-jzO|y&La0-!IKR3a;X@-zkJ#V|L(;+qq}`E1=70MW;3=Hpiq=cSOXz?7peiS=ks4{KrIj|X@O8Gp?;KY)>jv9;FeV"
    "vkPX>I0_)EmEHiTdAL3|HYEi$9iZm2#+AB)oj}DZ?dvySK*4vRD8Yf|k-K1r4RFG=&g2J@xKx9e@yE@c-fhsk?=||4i_O-_I"
    "{*R<Idg$ZkkD%z(aZ`08b+4j~9F+{#dM>)?%#+13El-Us<fs)O`^s#bV%XSm1phaZuWq}n-GA<of$Jw-J6H=k^$Rkq6Vnz#x"
    "r9{M)y2th`1*#jrRGdjbedxb8!SBE(hISUXO@|6E&f<U2O(m<76=CO;<DgFKS;YJp22C-ge=Q+^kqG^2V(|!&Nq6xcI79rnr"
    "nbra-qKjI%gc^@9go(r@iS+2Y8_D#RQbvklA_xtQy|!7m`7g&u>J38h+%W`^&#(c>7V||Aq#7)1K0f7UHr~ZZYsA^nlnhP*^"
    "8<R1+iVVEzrIT3UmBo0IH1>=b;3N?S#&=24TS<_+>x^<;$%>?9W69ltzz&tKZ1{tw3w^ZmmrZJxN@9;ZL&XO;Yk5E;mA+^9_"
    "NXjPM)qzW9#%Z(?PEH!+1FAdnn98Sclbcd5cEjMO$Z+4>3D+`_mQs4XI4Vg@O9`V{VX&Tz`b&%NW0ZoVDq=wq7=DZHUcG*_P"
    "=6UsB%aFk#*cKANpSRdFL$H@{!O;&aH%WEiPdgOf@IyZZAEc7i!*HT{;5l5hJSH1Q-pfzq|M-+&(NhH9;8L~gLrXEcthEBnb"
    "JMb2)p)UQBbntWYY-bn(QqEebTup~KH~f+_Eo~HZT+Nr6j6|9k#y%#@tnAydAtiO_wWATf`qnTs~s(DS59K8y%cqU%*x!k)G"
    "K996>p}`Tqsn!!*=Rrb{_z3`8wO2QAMgJY_cB2mwwoOfnVsdL4I>g<kbxPem??pv(x$=eoA!Mjl=QV<Fp7#UxZE#r~am&AQR"
    "EHj2!uFe3!y_Bt9OYxzb$?XW3Pr$-MQN7<KrW$4CHb&N@!jri_TxZ5-T#p1fcRie_N(cQr??U-XxH^Wbi$EF+XQzqWloXWlr"
    "}IL?iuf4(?mN6hc}$}t#!bHhzKJf)g(jGM_W*nlOR?o&>nW#1<|)Xjk5I3(1msjOaMHbDK8zCSVdcUMuAZv97lhj<_GBuhWD"
    "{Hy=iKelCKvagWyrPS`tc7ib$IiB;kyFkJU#nd#4I#xQm=Vk3g77?gu{MhK9Ee?Q*T3PymL67FW%&n&L(xH;<=`7gC7gqZ3a"
    "9$qsOV+v|V7x7c&Sn2#FjsT<!bo+vZp3u}qwf~{rMgT?kvy^WXKOs~!s@ap6I03Jx96*xcH!&n*5U<+2M?axw{_0x#wVLqxR"
    "cd9%}m$Umg<5(8Dx9LT^WFah|L}l$U1eDkRLI8{yYZI&F%+17}ldoHOTFoeRsZ6J|j$snS*=bq6oZd;uY(zp3ep2+7<iI^BB"
    "NE!bOY;VX<EvpfT^wHGCygF4K>h56^xw|Gz($AkUg=uYI|7^wAvBO5)v@2$Co&8yPQR)YY(Z2DB*J{cWipK~PWUozwKAcSFv"
    "*Pi*Q5xo{d_%ELqAZ$ke~)ysUAWwpg8#f@ZCYZ4_wTj+<-Tx#YkV0XBXFm&i~^u~EFU@_L_^n=Q!y*_udVo_JgUH3@`_tsr|"
    "_3zD_1`d+G&=O&-lhBkRIDF#MZwrfq3-jg4Sb)4CEuq?CE?$4_FQWd|K|B#!$36z*cyY4P78;7pW2Fbhn@QZULwN>$o%xTIL"
    "-{3B--A*i3Zj!#rq4*lHvfE_U}nnY(MP&hru0O#Fk?K)|JFKboS!4RYZSKFj#!C>i4Md;+nF-uXI3>PJ=A`>1dp6V$;iH}zO"
    "JjnHepB75axBDEA*U#t(!Zz6eag^Zg{X5nh7HIkZDuf>r=9?&OBrXx~Dc3SHB%iwifB=_Qs1-mI5S@O;blTvNXIX<=dP5c)I"
    "Io4%oA2?>kTVC6Lj*uXE<sC1rz=M%#f}vrl|RlzQU16raD@O70`SCK+#Hhb(Aq97cM15gUnsJgGOV4S)+-jFB%_ddGqwYR7Z"
    "`YsB=@@Fzq`+j(B8?3N05gykwanuh~=>%))a2g0vjW4L*&l|eK&0&aqG-w%sD2W+-prm1|R$ls1_uQSZ>!i<ssjfTRGgv)6L"
    "3^j+HOge(XP4%T9qLW3LsshcpWmhp!;23Wvrq|No9_qbJa$WY;`BUg@ZUVaA)!_tD3>O0+J#>yijB**mbEVkur41Bl@Un6le"
    "r3nB1q@gJF=t#<JcnJfoAdeCiQ?mABa?3RS+j<-<V{8~h`>;{JAV?nUOsgc8NtxT#Mk6U>^V{PzzJ5=66;gO4B743sP-+B1="
    "=>uSM<^kCgLdNp(Hf?hEi|sZY6n7v`3}!V##NXA+ukmt6%;&w{1y+)I`9}Dce;s7--V`MaK`7j_+O}@%u@=?E@Qfzw3WDcr)"
    "v_f`uw$e<zJ%+J77Klof{;C{~lFpmGzaUx1!sd>ik_e{!k`ZwywiaVr5cBISLk)P^;Lm-hk27DTW`vxJ=xzpig%Jvf*UGkfC"
    "j0q@v93>wa%?!=Y_c`->SnA$BM<FgI1%;Eo<e9>bQ>eiYFXx`(D9R)3U(}`A2baxizyV$J1dI&lYfQ)+X(Pbio4vsX_t;!tb"
    "aV~R~wIBHJ?wN|kj(w02UUQdCJb!%b3mt?m7Pkzyus#n?U{9xms7P?UnXV;mE8QzroO%?bk2F37|3aT?W!L;xm||8YR)A^Rq"
    "NQ<}dP(J5CHta1@#Avxy}F_PY3+X3&>6{G>;PS&0hDFLu8eudQMvC$s_YO9xH(1;UloDL4c^Llp&n6XQgmT=YLfarS*gJy6D"
    "@MS-cLs>s=-MGlA&y^I8d?8yT%TWoRe6~RKF~<%{wCmcmo<%AdU4Rh5k4vhj6aEzy%jX*N(1Ykrdrwb6<4HFKRzqbtPZ|jkk"
    "Bww8UF;woldAJhjRZjY5WB{Y|!t9=VcWe6J*!`jmHfMhDSp#4%<I!1XG&1Io#^8)A*#-8dmda{=KKSwFlP)QN>L33m0019rW"
    "O@6n@KCDb9FI^qwrL*#<0#nI=Wf43ko+x&NmEscYRLQwnuvb8A2XSU+~6Jy9{9w}g{>i?9rdU1EIuz3j;mhoz{0jygp?B=pU"
    "7a63ymh2592~G@0z7{FVR+|eL%3KWiLe+kX**;nP7N}}PM!kf$5)2>m@P$2m^`n`37F3T;KlZw-T(#Bn{S|^GL#ytc@aygA!"
    "rdk%<-mfxIrE!*$<O1FfNMtgKUy=`VuK*;MmR`Mh@mJ2B;uWxrl<QC5QhJJ2-`QPdcC&=2Qd4?8~T{TeE5lg>LszhQcKT<3@"
    "2z!FQy>l*;W2l`a~rFsx1HQstQ|%1TceJ8V8Iak_zBB6Sk;=rRlKch`S&fmt8|tYenHdS>xXAc$(XPUUS@g#OpFr65O7Mm?K"
    "g2Bxk71@)h%oizMn1Xz4QmvY^!Mkzu?`n<tHn|Hk5lPOFJSgGcAdOD~BO_td2r9xE2glvBCos58(l=uFt{W{TWDJ841FLo8-"
    "2QN$h1_Yoya^T*l8gd+ow67hlO?&Q1fTdbwO6Ten@Y&bBN6ln!k%j-SbQT6V|BMvBJRCk6i1V$)fWay@r0&X9$yL@8WzyA5q"
    "<zXxPGHMjT1sPJQl@4)>#5gh@L(Ax*fBYs+LRY6m1+f40NSRZiTb*&4_~F%MhnfjbTF558>;vmss^;agB}{G=8t{wJyTQaWh"
    "r0Nc_#XQCrCzp1$h+9^27e+_a3>_c8(wvd5}KC&oH%(EANq2dR>cAOfcoMTP5Yn|9sSk_I_C+f4B}L?lEN{m;V3-(yGt6m50"
    "`N#Vi6xme*4_#?6f={P+*=DXAQcrL<HSb{qbk;J}2MXFIR{F)_65tzud1e+0-^`7tEM-W?E6SESR_Ez<VV$PfSvf$;Y_@X5>"
    "!*o`G?DltGB#(IZUzhz}Qca&i#|lh>Y`l`+36JVbsQ5(&munjt7LNnKzX^|6I@|BNb-3oLk2@6R1BzQHQ0{ViK|*u@R6#3%2"
    "Tk_;f14pFtbeZvtNWUPyc8)Rq+oO}JzSN;0V@|^G%|7zbh4ac{IH<YOeNB>^`PAyCAhh`PEiZJGFp|oIQvGdp)Z(lMNB75f+"
    "-{6e&?F#>)-{(h;Js7+sL1IH>H^$S+N#fpHEQBtb5Q;({ltA9DoUj(Aa$}exEaQsR(V)>HXtUO&Q;IUPfu_feCyd$6$K8Va9"
    "MyZ|!Y~oWHR&%{+F>f&CSSZ;z7zgte7BL|?0YQZ#HN4J9uW+;(Q4apO%mc9^sJ3okz6gX7OQ8r|M+X&Z!(flAJEUDs?ZZTid"
    "I5+(B(qs)LIUyJil;UBzVGbaTaMjmEvY2|9d8Si{Rho3}N_c0Ex_@%bEnQjvvgiCmldSEs2;OE~_faJ1Mtm&J3l~N@=7X1#h"
    "=Up(4)5Y&P%;j4CcbqMP<8S*H*u*$H>*N=`dUj$VW@-t%<ZDQish`EHr*p<fahp>*x%i?-#%hUkp@=4gr_B;+VvxvZouCLR9"
    "Txb2YN&4oShK?jw&gl=bLH%^u}tScq%-p&eW>kM!k3S8E-s>PrAIaLf8`6mjI(9pIkD`FQ7Dhk}sWQY%ZA`(VFRBjSf{SF^0"
    "ajGFKR7q`FVK{2@)4CRMd)u8W0vhT3O~<4QXF$t;$|4{zeNaQ1_eJVKz_2_xt{YQkG;dMTxQukfCz-E){c`#*{p%fJ|CN1MK"
    "CRlfhEgX#H^f}&l*_%Uu-U#jf0{mafkI8qE{+FRGlpN0tFAyDx9P`(6ZlfIImjqtgl*f2o^lT~XnX`<*r^<<h4ru)uDJEa2a"
    "K8Q6bH`wFhTnk=fAg_knlo0Lm8X02M9{yGU3D8a?^qPK~sNB?zi$QwGYu7>wqR7Ww%voeOO`1JSi%y{f8+x)>E8|WH}CBT_?"
    "PAP1j#6?XdyUk-uH$?&B28yVD{rC-SYb^dlOVHXB7`_#7LcAZL(t&AzE!7Xv*SY#L}8A-dp-zZgXqN~p^8`Q!;g+r~U{Dr9E"
    "g3T74;-t0c@6q0?*7^@+KeW$(`RG+zj&rpq5dG85_ofF^<dEiPpQ8Ij$|4R!ix>&=D!L8b|5Tv>A;380?4-4QyR?Uz9f)rU{"
    "fm9S^M+5_vQ)*cFap~`;UgfPqWlUu;M2{g2Un48xfcCnP`)dI(O^wPqan0{@lwaFa&UicOQ;G+xJirm*4^ix(#qZyJ%3mFvO"
    "*mUSY;>khXWRF1Y&oHXyG!l%3i_e;k9NdLOenD@#_(K{VAdEaJau_QcE(NkhddBeGBjlse=iOlKZGuemCaK|xdn2oa;wl6q{"
    "zlRc5xnQ)gcFNS_dB~W>ntNlqSuFkq(zJAWh+eG$}$!e}M<tC3fl5gORyt%zVi|@07IJ=Z%^CJO3VymyG+afz6S|qucvfsAx"
    "sY!RMc2O(II_FnNO{uyl5H0K5!iJg{rXntUK<ZNS-I%v%|)9@&hqb?Bs{(2CGhMEaE+tdJyRhaAFTmsnIIPTI0J{p<X`dVZD"
    "-i6WhzT&=hr7=N5e61)L!uOPjpq$)#1*ICc+r{j0ze_7H3>~$Bi7bPe|gb~YaI^aebMAxy3f@-nNC4e935ezuFf(-S%aJ!oo"
    "R(otw9k#xEYoPB4B=vZp5e@AikqxPl6xM+$9=nPflIqCW^zU3f^CIe1VhSu&U$eJ2+lCQ{UP?<9mXo|<2}N#_#!BEBVZWf4{"
    "iQpLVR$gAj`6|d{5PQf{NXe3UHP_t8v8u~|DZL`vzAr0#S+pcu$6b?N+g8ug}shOHk~&@ZCbCNCll<(SX;&bJ_;sUS{$9Cac"
    "W3c6_J{!mCK-BrU)!WDIq)B9%5s_tNi=$(yz6%83zXr;7En~LvKdr^pUFshrd{KeNZHvgHP=Bm*F7l@r#|JqcRuc2v31`wOu"
    "`H*!m{TiY)Gkqbr|u0eFrqSbdAZ7?vGuDCmlfC)j7wJ_#)*HGdL}*UjStEhNAieVvMlEgFcAt&Aypk_6ER6D3tvQ@^ftB#XW"
    "EIoc>ydpzy8Dry-CsN^ZZ_pKp7TqhZIa5tbX`#>f5p>~U;TK+e&3=2c-^Sdb4`|QK^{BHj0&+~Ynu^xV1!aVo%Kw{%jP7E$e"
    "D1^T<d>w5enJNI6%#$GGdAU>nAvdexOwmD@X&0r#@HF=d8Uw=mRebw(b1i3uSPM^x&-A;uA@<Gf2=rR_8|oOex#RI|=eRot&"
    "QqT`%;8o_-n-o%X6iJvS<BfE&BvqAqETSef3_HqdOdAZvw3VZbtgmDSjRW-$56gyg~3CRsf_tSBdFdWCN(Ro$45yZ>diez7j"
    "zdree|Is_k-MnPf|Tzq@Ugw8Rl|O%p-9KtBNn{?h#Go%{SPt1;%_9R%_jY;~AQh!#S0JOpHCrKpU*G!nf85;7{p<6mWNqUSD"
    "@yEa;eyv~%E|?VT;`zz!wvy<~N$Du_GQ@S|XOGqU1uY0aK2T6VPx1=CHus~kHVX>v<NBHhZo1IHxuQ{L}PjXIVpk>GIIl%re"
    "-ov=2nlw@=Z9_7Qy71eWCmayF`uxs)h5$hNQ2CbWwC0whVC8ko;$5TIA{El_Joj-Rn)5F@EfVZA=cjd>1M)|{f(^sgIb4~iK"
    "915uTg1?<y^T{L9FWS8NdI4o#(&<MV7uX2IMAs~W2PVJeQ5x0IuF^J)H&}U#{f)g*Cvl+gqWvHz_>rkb^zg1;YTtBjma+XkC"
    "KMKvG*^VO1N>6H)k>wZwH}PLma{?gU;9#0$@Yn%;7?HWI>-Nhd<4CI5(uN@ul`x>?w$K@m4n>^4Swf~)wB=Fr5Brt_|FnMm^"
    "nA(SvV}moR31J`~sK70duo$8gMp0f#M!JxwZuzGKb5M708t-ou7`#y%Nb7|ECl+<Pc(iOVf{UZr{Vs@iTun9O)ZtuO-Ip+)2"
    "WiF-erXsRZ+lfkv`#zSXg4zjgf{Si5qqpSkjax6?pgSfJ@oaA(q>Mp<iQx$rgQ`$dhhwJaM#igc0tOh05%yXphCLy9h6HZyl"
    "U&!kAA`sRBEpHm4NKZl)CK}Wr{bF7LWwrdNa*4UJ|Ir0}D;?HIfN*xuy=Y33OP08w^;|aOx&+&JDh{uB9GE#_P(tg5K_097~"
    "2q6AOhS2@#-}&^gWrL-{e=i$jMey9lZe!On#B9&^;+dO)fu0IZ!bC647{;=tRL_b#hI^1@J0`nzjUGw2Y^Xqg<@QgH+3X-q^"
    "{6l=C)+A`2j#8i&sjs~^Za@4VdsDS%)~ouz6`vvx#Kb6is7jeOIAgieql=7T!t~~oIUvZBm42BbD^Gv&$}`mkUi<~!d{(VX+"
    "TzuZ0yE-buM2tki<IhAP(+VlX%|6iu(<Pl!e+=9iejDG!1%vz4>JD2Q6RqXWmz%w6+Y|e3*|4HmVc`GE~wibZ+EGW}h1)U#u"
    ")joD7bUfo54i#nq5A8)zQ?LpSGVJ@Q2*1W$R6i>?)ZK}{lwFpCHO!S~+}^*>FanD;p<PF>BHmu}~*<=+_)npO?jc`a3?WTdg"
    "#B#YU*$@w>eE33ElMWrOCS(;4hMUC`)YPOdrJWx!Lpd!;CcQf9ON1S1ByOQGe6CFXGunvrTKv~r4j@8=7l*_6J<>F%tyWG`J"
    ";9qre+5qgM^Dvw3lGITFB@F%4<IV-#VOdVyugABoWAOLiPiQ@fYv@q7eiXxQC0{H=%0NnLx1Bl^kQMbx{mtB=-|jA)I>eDp%"
    "&3Ab;gL&-sYButdKUL2Tm$GlMLlT9^fAL@pOZ{xOCFOhl@8{4+z*NO1{AWX0pHMg-&}>Vnup%>WnkXgS>u#AhyIrhB1`T6vY"
    "}9(q1KaQLzg$23wzi}6x%Hv?1W(y5p%Cs{YgS6TV&V2=~nrC9Q6GZrd%<D74gu+nO6CUF~fB@o;#Hq?~^w-i@`uW`Oq+Z^uw"
    "VnOtZ#^zptBc{DhjdcP7ufOV9>}c*7VP14jEI50o=YtOer;XTJ9zInTm~;5$R0%WK5#=qd8pu=1|;$qxWijBC7E(Duvw&aK#"
    "2&)yA^umT4N1Lfi@7YP-}lav@WnfL=U%0Y&nk21cFPJzQ0CHN|H4$$Pn#-`ZkHz^k$G!_?$ear=I;*B}R;*UB5ak432X~jj4"
    "U1ZCjx-e<K0EM;c#M2dcYb6lYVZbvl>o3vAkLB%=DPoPw#O2_HPx&)t(bDKRRA;f358~>*)wdu3E|b|iTr#v51OL_)cu1l{N"
    "DqGJnaQeho^DRaG!mn8<JQ3&vtfL^kUF;t+foI~`u1$jp7;YB3}Mz+s7?8CH!E-fZV+8bFo-%iL>?TPjJ+c!`1<-l*yUw(@i"
    "w^;(8Hse{deO*t$3=H1`TVJCnH9Nb9Bh4&aMZ8VCT>6M!Uz`{n@(yQ}@Yzmq+J>0UYxX7|IDYEX&0l9tzJ~ItdHQo3~kY-b<"
    "+4<v1a>qOvGwj<GzK$#RZfrWlb%Al+SwYL4+0dhD))Ms!Y*N=(U%s3E`~9IM!@7Jjb65b}0vMydTwk8snZ5m1?km=f@9ULE}"
    "g|2cb$5ZLQ<)qbbs7}TRmDNbihY7wr~UxgeRq|~6*7P@d}W~FJ9F_FodZci*vKNj)5rLixdzzQ=Pa$KO)uy;7uq|H96G!w??"
    "Wlhh`9z4S<kI>g0yDIfXQn>_!M{27k*BO(S5&-gL0g|2(mo~xMGw41kXbX9ULOP&e^>f?Gg#BuyJdj<dlS5l~y~N0$k%CBLK"
    "m`DFXc0UV*63_Qs(UT{hR9eY*Qxw+&d%?egLPjdje?X-aetWuQT`xa5$Z;Va?3jO?vd=l*5@dReaUJ^ZEXGQ)<XA@){~trxx"
    "`?zus2BQXR|3?visrqXwsor{fgzp{_Rcp#LN7UhMYLU_oNHAb?4&O6oskGa<UAFd|e11sHr+;vk4QY+3>DQalw4hOY8#eb++"
    "}XipiNeD2f=6g4yQ@gv>$L?9Ap}xz6zDF=X$6BAJk)7H$p>L+(&{1v=A-C;pVxlc2F<Q1Kql{?a|1O)8nz{)J`b<&mO^wr`m"
    "#9#ul6y6Yu!hQZ)(NOMdfQLQNI^I`il3Y}VO;JMCpqv58UCq*)*U>z4=sHUpWa_X{SF96@{XyWyAMrx)Q%$q)WXcswr5a}OV"
    ")9*O%h-tWM95mg{!Z0RTa#<IYLuM}DA`%pmDo^tJy`%OTobH)MqdI68Yl9uZkey?65MvA(=Lg&XLlpwnGB`|p2z11z8y2ctC"
    "8&DLOeGO~m$@N7iF!9}m)U+8cE(A5OhJx-vcxm4q19k^bYj;&^;(g<@*KherJGLtQ+&6Y76or~fesboM~iWu>Hb9(WZ8VtbM"
    ">=UE}XOD*-(8DPzXRe9;_tg@^vJFRJyj?c_daT<oPF;CXW)H3RQ>tcQ~Q=1&9glInS6^>b~+FCY@?O&J~Ti3acSC;^^rtCYJ"
    "`QGU~J@-b0$;e>4)?Kf(`!3oy=2^i)MeC6O8Qys>ko-~qZx=(u@US;yxYYt-;sV@XP4v9)Y34vtq1<C8PF?M+i^6RuZt-ufI"
    "SHY*jR@Il{CN5Bm5LCh5m48wL5!|7sgm2Lt=iT1^vSij~XZC81@ghhvck&oiyu7A%F5uV8biV&Ul?CVsK_w*c_kGUlC!{>e3"
    "f)4&N-VaKpGNdUwp~>BMFF~L>CL#G#yxPt+3*rbweEDf=zl1<}1b>@^pnsE|LdRYnKWD!{JwXAF(DM=!9)56w>Diz3DuHl=5"
    "%_mL5r&uI20G$zmSKt{si24v#}^<V5Ti7Q9yc5bn=H^vo1qI*AWoiN`%7|6O)XQ*fN#2L&=2x65`ZtoDxkp8JXu^j>)qzqXS"
    "y<LSCB6vA&?%_^vKm~KoZ07xIw>$Ht?Lff?yFn<XMo!4vRQuPK#7k^(u`Dk4728hL1KzHY<rPJ5|YlEa%-YF*>WZY~W4KCq8"
    "MO8DW_n!x2OZUl@bj@g7V9`D9d_(H;%1d3ovACF^Mw*wke$E*vD685dDP-V%`*r>Gi@G+eUkbk@LfKW!G*N%^>h@cvYycL?p"
    "`O91$T`BpLK_HYkJ^9|Z6OH+x@uquyZEy5mE+of{ll#0c$?AW!b+^FCY*Vb-@9%i+6tz~SA25){xUCeiZdOT~>{=7*uYdx#{"
    "S>SjIFF<0t6g04a6r7m`CSnmi&hNY31PBTff+?YqXE(aKAJxCIW%D_)`q8dS{uRmfhUL$YmdVJL&%C5+d94C~FJheryDD`qm"
    "^RcjnR(~bt5mG7cy_n_LOwx#9)qQBn1MBuNnkJ{J(~U+5Ro%-H{;;KHu|%cRF!q;y$oYu5}}0Ap^ZOXG;{CL%rW__9(CM(=5"
    "6;Xz<o>-WPPA%oc}~J@C3IpDKT1w2ix;wHn34K9Qiv57Y(wjv=)?6EuaSxxaj1@TFaOYs{XZWDeDs@xG4DT&c-@_Ju~sRO*8"
    "{>y;4G@qkm+I@8xsnhM;tNBd1ku97L_|*=Ex^#J#1Zd#KZ!yXh-wSOI!<6XQ}q(QR;Jf}lB#1}aABv3B~NQ&kB*+&7*j#<lT"
    "n1Sn-rMT=yq#Gf5fnc;}+JlT|7$up6kVZ>a9&yFc7Qa`81mr`V!t5^t%tY;!Y?(|kTri*^wy7|D^RUer5pm`#RY=vVA)4T=4"
    "VRXbTVFeSOikKz>GcZf?&_htRTwutF+VZ3ID5Ys0eX5zI<96GRR(i|DUl9>FFyHw~%+#3Xz3}$O)oD1)j)E2xd7H|!sl8?N>"
    "CyM<<NY$_991my?UA%UZG8xp)JFkCJIh6)`@$juGzkx(4PwRoXzMjcW|aF%*Qq(D&(w4d(*ubgr!yK|Kd3@Ie63z(`BT%i#w"
    "(rLB%hDgYR9fZrGUU;cNWG45ZpPsvS}GMOSoAPt*MZ^8e9up-A7RV1!W}FE3+$mFf0ow+!dB-%~GXSCszhgLWTDF_=lZcHc!"
    "3fmZ;tDdr*cE7VTGHWxyVeFL3e({5H*yQ@9!07qL{aj8m_lKnP;V=h?<Jxdm1v9DXm@8gkLVgx!H*0Q|X6An2**hXuVPzkd6"
    "~kEAED9xGLg4STrl%eBrwB_f^~QD(T1^RKWXko(>Phe&C`E_Pdi8+gJtN806?I-_`IPO`?J?7D!UW;^1<;)IX}vX~EO5+$X*"
    "uBq}~uOi*5T6g4FteIc3h!=K@K9~kySu$_WPS37b1!tD>dAA=j>9!rw3CXaxi0pqm{aRq{be|t!t*`W<S-u$GUv@JXwHm~X1"
    "9EI;+qLQSNCScC=s~{|VXu5}%G_x@?y{RWkn_cEgCDQaAJjykCh~_m&QF@!7e=SW=EOEvek-#sOSL+!f2Lt*cKiIItNS5)lP"
    "A5T68jd#droLqr9E>B5lc_%=CY%9<Wd1sh!!sLI+V81cCMHpm<0wA4{Il`gM!Kd{8bS{we2IgGzpaP1d%`ni$P=_Z#Yq=lhO"
    "?yC)WtaEK)J2hn#%lpheKF;ShlDf}sq-n~45qX5O#8?DmzKmqtKEcgmdC%31>*#kiB<8k;G4&P{Y<8y?0eRbOjZB{kK)-$TW"
    "O2n57L#r2iah4oONz9}Ff1~RnQ&8_{JkvLU5j9B3G&TGyjcBiSNLCW4eXp49@(4KPOSXW#yEHoH5J6zg#*Wa&M_ZaO}n7<`X"
    "Fe8~KlFcV7&a|ChVYr5kPzA*(9`&4(qvJ*&(gXJS8yQ+BgbnFY(!wwSXM4M9XkItZ!X$rNq4%73)E_)7D)*asZm2wX{2Kh?W"
    "2Key_p9Xm@Z%C;!p+;PuE_q-e3J{%%Fn|AVqwXQJ$4bRad$}5U`sqi+J~8kFaz<&LTsQ<Bju8Q8-~yo>uYtV-fsO62?;{cEf"
    "bdOAoC_&R9M6|R}p+F`SJqu4qL<}j}>AN>D;Gm`eoKg-vHJZu~|4*%Yx)s`G#3}n&K0uO46imrxUKA&ZZ5Rnl|1rE_BQv%#("
    "0vwm}zhgPkdCKPd0{kL4-L<`oWEjaCGf+!_hPLJS1Dq`KrFE`H9csKptCI(rsJ30=hAtZdS8x8ePum0PCLhCFKfu4L&M|6`J"
    "sr^DxzQCH?hRlW{}hDtt*9xjfhZ(nI#)1yZhE9d}GKLD$TK;^xsRXN89-VHs53Ry(J=4GQBKFixkbUqdpIgr$=A;bB`wkFPh"
    "aaE$0QkOPWpY3dc6|0n}d;(ub=D<U~L@Yz6JYHk>0Nafh!I~_Ue{*dkC8RRhH)1qg6#>^<Z&8sep8>EHm3cYv<u6N^QM)ELY"
    ">rgA5%TsLnkPw~4&V%Jh#>pV<gHs|_W`2cO~ay;$4#@?wizVzy+}oWkp|bjhw8))E&Y@YQ4%GEBB-Qlb_AK7C{fi`y%92?4u"
    "TOK;6j+cwP_1xL4X#?^_C~x5`7OgxsY)h9X;MyABG1`2kY}KE<YpuO@dP9GrxkRjH;APkY>fFmtqTw7r|9oe?uk}OlsXF3$q"
    "_WtR-d8rwWS-%km^j@<mn#E3^RDwJr@<CRy}m=)IY{GFf0_HDHR05o!@<QIM&Dn_F0zd0vA_&+k*k)`=`m?JQuOw<X=b6lNT"
    "4D9(+iHJaQ5F+1Hr$uNsK^v+Fp<QJA%onYe=LPn0fO6HC=*`^{kq7ou_HvmRL2MCyqa+k%%0r)a8`?JHPi*t9-9z3*tjMOA0"
    "&l2{bNGC*D&nfLhH2N!L5GLg;aFdj;UDRQwnl6G4oiB+`l2q~zR%Z(0&FbN9i3o3fW45BK$CN2kIb%UmcG1KZTJwv@o?5L%m"
    "MhtaNnk8yKp8zaloz?I#MCHW7=5${^mhXC@e=})o*=qx5c?GxEi^`&t=$M=7tC@$7AglvYs1@|rZ)wb@b$a+QnG|avGtVMhg"
    "5$pX)6+t60*#e^C>r%?Og}S0*J;i(j49F!&Nn($&*Fjq%sH{8O|4&IfTd0q(CbKE4VPHRbLcHxh-}w3}W0^oc3}`T~yZ~>*8"
    "<x%)y8-rb%x`z74H6wr-l<5nb%Y^nM*~<hRJUmTm#DE7{N-e6bTBrjL6H9BR@P2@yZ|zh{s-aC$Yk@@I;F%d?L=w@M!LRI5l"
    "{TJQa~7sjrEr3)5s2Rt#%yRO|CljKrDa(TJ&%un6FRiY@kO@yet!xx56f>rtspFmPt2`x)zSCWAe4Tsx|V5E6QQ6jqtm8-eK"
    "m){v%$8u4y{7SkCWY0bi6eCv-!7%(<IA9RKtn(@b6JQLD4r*X<BK>4-lgFCA^n-4PR%hqH(%m8|Lq|`ir0zyIfJ=Y54#`gMv"
    "2L7^qKM9`rLC?yRdAX;lJ^S1TA?TgY=9l|&BxaZ58Mi8E3oMf(*rMyDEX(crTt12TemT9%4tWWycM_Fp8iFadn3z3aO>g5w<"
    "fM;)Gm+UDWR{d+o}5PjB<XBGrg{rGCOHS`am&D{D~@~obEtXccVBzMrl@+nkW}F7hY9*%OM8g;&-4Ku~uSI#8oFf;=@BM>n3"
    "B$-})JOz#57E*`!k$_yQ<&G2s~5whrpl9hpM<E9gB<P!Jxr5@D%fvVkUo9s(;0YyBSDjOxfUqz{@rW)Vi+c|R>n`lzz~a#Yh"
    "Xn*1x<{`i&bytM@RL+yi#48W<aCV71ockPStmUEyodYWoru`CqWWrm`pWs&L75m=OHr_jdU$S6^c8@_SR>gw=@+g95gM|_kt"
    "6F8q<^4W%_t;&m+s7l8wDp=hEtg!j1EVabOY~FZt--`drM)&A=QWl|oZ42H8u8$f82C$-&qzU-W+BcBdzs?_uTZ%&z8~LKNe"
    ";C%KaMRzbNbl*udGlyC6H_>^b!BrXcBIKm3jcOQa7CM|wQ?LMw~>$Kp2B)#6YV$UVTXo6`xoE?xa0<(qQ7p-6eTGiACpxap2"
    "a=*$1qyy3&zu)r;Q;?_q3!q-{^J48C=314)yBG{DmJpw9*TWdCxB>GN{J)p#LLUw#1{<p;&8b*)FN9U+(Z>)5<=PnpdWC?)+"
    "9oYGW}d$?2A36iC)1<~ZO3kJRH1h7nrx)yN|RPZh6+Cu4xnnPSdG;K4n4-N9K<@MQ3bQ6k*RbOq}5Vsr8k89JS*b&31io9X&"
    "decIe3vg9KiAX(7DF2-@LF6XpGX6cNckOBgi@g68b6Cf<ihI@6IHk6&62l(EsB@B~8qZk4LtWHy7iTHUpbZgMd#XWYqiZw+O"
    "&#~_B59xGsCqXiEL@kQj4qNUxc{^Ia?Q<*4K|E+vSrA@z=tNFGuiX)yMg}M5xqB&TE?wG*6KwMpKDoq0L$0CnkV)^r%77cQv"
    "qfd(3wH?Nphq5Ll+yRu8S%#4INo6Fb~eELKso<=BIINI8p(Sja1%FC$a{|{N>WBE4m7gA@<|$M7g>5|JFq$S2#@o`f3Ry&qu"
    "(@Mkie_0?2+_AK`YVZ<3RJGfi;owelm=C0cqh$m4)G_aD|KI*P7%Y?t0cUXZ<Dq-2O;Ty(4(2z2vzUR-2KG5L>yK>P*fl4gJ"
    "hRi~xEScZ!5&iTxZ_>PnZDh}SMNSfbsA8TDlLWI|HuRDC-C!1jS!_acxH0}gP-f&X{C3L?1fJJdCSrBb{x*5Gac>_FAY7*1E"
    "YLEzm@n2>b$L{+Koql(E_zwGAR$lk$2&V%W?X5QY@g6j;v!{4K7mNm2DnQ+$)US)YWl!rc+Xy50==)%SGh-6Y(TLjS;s!zUk"
    "+3HA@kC8LHjRi>)&Taz3p^P_&#Cj+(LqUL6=&4N?83{R!uzx1X#DHWyDP4M(vHJSy-H$U1CiLpQGhL3;y}F_0X`vFkQV|-}Y"
    "FXo!>X?VCSGQieO_Ns;70DQoE8-GuEa1d03q9ThOt#zKcMdBG4M8X)LEVn24;2%3)GHLXbSAV$#6;^0YM+>#mej~wr!JyPRl"
    "ONEBI#tGQ>ry{xiPiJRIx|GkVykrDv%WUPpwHEG|88whhi%@k{-UB4Ld?KasQWr<&RYa?TkUbRmJ{%b+5yxE@_}1_$+U=vY<"
    "eWuirdmHZ&SE^E+>5xV&{D%5wDIRvWvadQ&#%MCcO=>en?~WqoL}7dQj=d96O;-Oy#;mTRPUm3O*JA6XMA)QFwh2l>X;i>3V"
    ">9evFk*y$RV5j<rkzQY6zA_7Icg!pZ=H(AC+Y0c5^(aenE)bfh`Q*y@dW|Bfhyvb+5#CY#Xw*zlFjqxsrk8uLZuT%52t#Ry1"
    "3bTM%Y+07`(Qlme+7C#9gUKLc;y1IPPk(sNgwWBsbCyz;U9;U&1dM;oZv(|I)DJp<yy5`+qgba8VdyNs6jU-(^YV#v6Y0WZ9"
    "aj&h7BoNF-XC2C8hEpc-RPWbRMgg{!iI6i*aVU%t;$apyEMct7BKK1S_344Vgf3xAK%dVnqv$pop2EPYa4^1!qK_S@=@AQVE"
    "YaMUN<FN(vx0(I`Y*HGZ5=^Q4$5)g7x)Jehqe@)7%WPBs!U3Kf&r>2W9;-hqkYWT14g0DA@efmSQrB$`>)Lq(`vH{6VJvqj|"
    "_>uQ-%%YE%*c8V&X_K+*$RU#AS2Wk>)t+O~U-4Zv7<<Rb3N+byJU@jCcMG(Xp#Btt$Yj+vP5mJU8hc{1h%CiR``#1b~N{CGR"
    "l73CE23TN!tHHym^9czdB3>Gg@uYg7u;o$&X5LOeYXAIt+HH2^FmLzwvPn>jjyWNw$J+?*wHNSwuST89dlCV1oQ5Mtv31+M{"
    "s!b!XgK`?uL}@3xcl2!>y_1bwT+UhByNdbS)nEIo7cz2=*N_;>)56zAHnCJrrDDH$X^~AnR4DkGC(h)HXcd5Z%>1Tiu?Vege"
    "py4r6EXvET*yFq8*qwzY8RSR?6v&s#-TG?#H*F}8c&2y$(o9bCsHumKuW5iVcPzPIzwD0BO)=!D_mW~%50sIs~n5ZT7=LH%`"
    "fSXQ$gn326~I+6qF;izy2--{N?s*bk|Qaz62ToJ=PsAb0kP1QTW+H6iPlxlpB1<?#O@a;kzR4<*j6P_*YNpMUXAJ?7M2!>p#"
    "X5^;0PNCxvlJDw1^lcxUViW_75ii0#=L`?HtWWIC0Z2t~oM)slPQyzwkVerWkFo+M8N3j$3h0O0$SjJSw;I|yzT8Uk1L2@Gu"
    "~d7;G{E_~s{DDG&*vWqOu`*}}b^AEwM8nt$wf4ov>g>WeLbW95N>HLcP$qT<g?opwSPxDmuEArT#*cP6HEI9IbH$*N#$oOM+"
    "+Hs!dWO0*t#>jm%F>vfUW{>~#D={|(_H*IJ=P&~Gp7JY64H)4IvQ*j=uQ`Zxith{&ZPHc4;C)%V@{MIl`0KITbTEEe-HG&r2"
    "Q|H{Qc059`b|QKCU2)7=rr51q_;{*Ukql<NA@1;W?0kN%~$Bt+o8$|k>T)uW|42K*)O<11YezL@$wCju6zCV9Eo41oL*uzKP"
    "`cTXfVY`P@TPy>2vF13mEMK4X)u1_nrYSrk2zouLwk&lY=&-cT_bJMD*VoaXYPGZO-=5b@t<_dw_67vb&Qi`=HG6(pS4|G`+"
    "FL;#~bFw{=Gouh1>P_CR9?oNOxy`Ij;#G{@jyKll&IAj+VbkS6}o<zZkSw6bc|=6y^enGAa+o5Ej6fd$;tVH0EKk-de-$B#N"
    "n{>Hyr(kls9lwQ<)gt9kT)7^`yGfJYjTd72NKVSR*Rcz7+D*yd9^(u8`9&>?K-t>TZpv7BD)-6mxWD?lLS0CyxI3-$iOu3!K"
    "rcK4?UU>b2<N8&XCVOf_#05*Cp@~T<^9hkX5R;uT(8s#!xdrF@NMSc=xa1GqpyaDSlP3jFXo$_e*dRI}_B6b&=h)(bxWjp>_"
    "OjVtaD*qqA4LM`@7zHq07$FLshVRjhBCDiN}M6Y9ZLHnaO9*s?&R~ofgB$G(!0_9h?(R#ZkMfa&{}ykCC)&UVLdNOB?`4NIv"
    ")gw`&KrL3IqlPea6Rwzx%#GU{i!aE6*ydMnI@3MT<b%o3><}^g@FBlT<)kWvE}=gg;FIKFI%+_V|+DT8^@8R^f2-qpR<gzC^"
    "WEY8a-Vz{aAS(w_HGn>>Sx@gR44?S5HYd+^O*q}m}xxnjmHRXIljYl%^{zSB1;;bJ|&JT}0r6_|zS;806Ws`$Xw{p~KvmF&4"
    "*fnb&Yl&o%Obeb_Z^C++nAi$?iBXf{de!OERn7zIx6JEM%Icdsvd%%A@>cz`)04=NP68{}-!4G!^|11vMWsf_b#E=pGe!x%e"
    "JkI1rVN-0T$9KywcqaGzomhFeiO3+T-d%5q(n&TyBR%q=cr=%(1?C<XI)?1ik$3dJN)9HI0sKP`I(#LW{`1P^n$qi*d7A)>#"
    "`-dAQq6_tj7X&B3d6L#4|S$APQ(f!MdFG0*A%!GRFo-$eaVM=D4>K8<S#$8e|8(ng7h%wnNH1C%01X?bPO0?LZc>Gq9Og|(E"
    "2<?zL#c~I>gaMwM{L+0>v&r{E=_|0Ulvw2I|$7_tT=>6P0d*XvsVm#)hP|`fedB6gF@k`Ub<;Y;SeN0afV_$&byn=0EI!mhH"
    "A5f7zu4&Gd6Om`o3+p8*28;Fk7s)H9z_=NX@AtD{@jvRTP?Zw21WfEgD{M5^+61xu{}S^;#2IKDANR@7XP+@0vY1;5|6uk;r"
    "U2#@O8QPRT@MN`+f1spzkGgSTJel5tQZ+19T4qtjm0Wtj)Unnx;`2B3XbwthxWkd(p@s`fNdR+~s1-y6Sk0FT{Bz>#9o-bW("
    "GwG5fRx8pzRB(sz)`c%?xEUhS*lANBSbl)f%OspJz}*bMg?<=Q3LYJfoy?a{!-Z~CwtxWjH1cS3arZvbqRYAs3mB^KZXdt&s"
    "3PPCh|W;*2a}U-W1a4C&XU<<3GB)Xe-*ZN-AY5T`12vTK%oAGz151m@rjtj<^wVoB0xa6DzH<&WHW;vkiylYd5i;+iXW*j-w"
    "g%3o7!MZ5pMzORQFu}bklKZq4f!!{c?Tu_eLSwbDx>>P0S!nov9JCpPAlZkq%i_%Gn5udBI2HVV4&~HEN5GeB&a>1GACwD5p"
    "5VpyJ%{=m~YzmH3tdi9thHJ^Vg8#!_vG!V{s+64Qud(;t%yC3sBlN%DNcsWEwi#jQ>J^lU`Xp^e+)dkx-$9*at=Jp<8ZVm=$"
    "DovUzN=zg13c5=tEM=&}-3yA>zE+1gD_|+^FXt@pg{I&wKJV3qro0=bvJ1}pLP`N@X_RpS9581Jn0gJ9z^oi<<c;{@2XkeX8"
    "v0Tr3;z>dKQ@$V`(;mp8qPD^3rm;!?(5PD?RgF@r)B*W(nH@z*H8M<u8gdM!f51cg<sfv{ST~A<YTm>2=o`OMd!bO;d5OcVd"
    "`Zxos^8klz~|#6Mz6=W#>pc6E4qxTMD|{V8QfZB<m_$A3}KpQ7k#?~rs%${V*)*IwnGMqMgJ4g9VXA6LmNELZHV2X1YE+Q62"
    "3%sC2i7$RpZ!npRG`*@?oJ@@NA@|iC>7;JBh*bAz%Kt57lzz>)KRMLUXMswF3FI`4JJN*cSU?GB#8uEyx_K_(`?z6)tdx_;O"
    "y@R0@v4!JZAFv&-l6UXLRH8<SOO7})xdLa<h4BY8pa6vDK8(AhDCWmJ1Jd2y_P#5`k#qwlVcI&nq+k+d{f(F4)daMtyzE<%Y"
    "It;)rIgs2)-&c0~*h`q5Dq4Fb`)!@2`<bl%*6w(~-0#d&totlTQ_^qyv`aO#F{AuOh_*-gW>9wEwg-@AaT9u;Z#Ox1y0tGd?"
    "YVqKn^-}&Znyurwu8^jhhCU>x2kp&Lx4-<2t&-D2_;1>wno+k0l_oj;7$hTwz)7Or-7UWGoXD=|MOumo?l-~3LJdf<#4^x(k"
    "RY#n|DJSgKf*E+{+|TdL019%BYin^rEb;rl}(vuYU<g)jFpGn&H6M<nMsxf)SK|Q=my-&cvA>(LEU5>Ha7m~E-{lQr--#Udw"
    "v?O+MhKM;6sR>^W{+bFe`jNUht36N)RDvA#o7O0;+rEWv87Kh;FDFvubYd)#<yf^dRu#yD2kbu?78WoEcg2s?l(P)09x+dLC"
    "vUp6rT6oqO$8^l1fqYQE+%NTw~8!A|dCAL<K<HSh1EPglA*2hdFAD3TB@&nYVAxEdf0Y>3Igp2O-_#KmYKVM7JyjJ9ni$XlW"
    "jG_9q6dW|^Z%4hWrkLKY3DS`6j>|tL}&k43S_0;rd;^aHtypv1sukpS6Ns2-ZQgZNRv8MZYTbtft>6;M72K<8u7k;`^+&@ld"
    "YEu*`vD!7|4M>!2S=_H`$DTREo}36#Mj(=^iW2QIfllcOB?yAkWr&o6DR9NdT!143ebR(Q*t)fW7mo+epweT~T1$<xdXhjdD"
    "37!~bW$hh$<T|0)2tr)%_}JFs<8_${aMRimm*3y&i9-B1u2DAm>LB*887FOhtxB6Jv!CAxnB%vs>4N?ES*!FZI+6Y=O>GwS0"
    "JxvE{nGEvra9-4L9CQMUF-`q|S;fj1_kUmD?uVyP=@I;O|hGVCs|O2J~Fg*7{cKnV^9Sl7*C0_Nq6hHaJ9P#6Kg9)V%8P0LD"
    "0pG?N@Hh3Ry*4-V}(#F=m(j~>@-udX`9E99U9-uXu4f3OhGAE4i2;BZcLzKEkW{?fGYu{q2tk!kzdL&&9|&?UDVq*OzG?3y%"
    "}=vdyaJcX+lf|#ZnAkul2*ToZp8G_Ed^3`gPRxDP0hO5b3lsl-Wwi59$9;l|tT>b9&p-;~^r+XDMa^w|BHJ11l?R7tN^5-2E"
    "-vF{9f0&H{@t71Sw}B}oDFYp{#-P~NbC_;nu^J^Mw3`|ISHi0~n?_eyoU~$88EngQ@%o8raLm*9n?e%OxG;hnxNL5=kw=FLJ"
    "IL3Y)3ktz<DSWjh+d1tl84|sYT<56CCUak5v>|wd?IBrb!mDc^LiPJJCcIM4iWDSf`VZrM)AMimnH8&pi4siM=|JQBWNAlpY"
    "lenMY_^I%T^cuAG>bV6<61Efi^CUdvJFP65Jhv6I?@ryEZPtArLGOTtaYncMtCFPUEhp$@6~aFPxh*#=hNqSIw$5YtFUS))a"
    "}0Y*FIwpVWe0_u6JR<+d!&8*7ZMa_C~e3Uu5Ar0K3GysMAV{y5^ufn(c&w-gPcXQBQ*zeX1%0O3<VlmU++GF_oqrB~;>-(CD"
    "(C4;@;zxy415V$R9orY>O<S!_d@{;9Z(hB{WK-vC_F)3GfwB5=cr@ftf2D&80Z_&A9k>|H=l102xRy`zaMo!6JUC2c=aVM~!"
    "&b%mD2fnyEaY)Ee(@hf7DGrLuVTSy`17l)uTXT7E%G11PZ@`V=^MKID__NK<cy59)-qB;L;KD?FphlDQ6ASA!W-U*IpQkI5b"
    "W;sj4I0k`=Q7Rc524y&Mz)h924aN&8{$ETO~gZP6HiYXwLc&BSM)=oKh{sI4&tT!klnX=Uhx%c=BxhHzVIFzIq0YUdYnG>k7"
    "s$bziC_;I_nB#CQNii(4bD4Y(xj2P+9@GMYaiX1dxPFJ1bCjOA1M}d|Tg>g<DpJcF`hE-YO<+k>gqhGnWGK_h!ij!zsP4^t&"
    "dAl+IwT!J0TE<S%sFkqXhRVahSs-`*8oT(iw~Bm2tr-4{l_6l&)v$gg5G^^5PW{FiS}s7)NA@9_iAk=Zkd{-nUeJtJknfRq|"
    "&f6?LqReo*+tU0PnTDJ<8j($BT?ZRl?MxShzAd!^+`~(qvK_E#eNc!YGTlP*FM9DcBxwJV?8ckfa31~`nlVXK<;D@LN^8xMw"
    "r;KmSZP5yDg^=V)d*~3Ei63Lm0Ejmj5#-Aq7wDbRS}^48+7D6KIi018sDgkWCO%sA;n7NUQ}|0CrZOJ{RA-Edms{=jCYH+%*"
    "Im#@<njt<lvSL6eDWpuy5!~(*g=AbBT$x8%P2Fp^RPb$LoZh!XBFwo<ll?;Vm@w;MYKPC#mcp$Oe6z8H$lqQD9Sr`&oYqrle"
    "`A59ARJz89knN>aH<a{@qU}=CdCYrw_kHV$^(f&t#;~l3e6Ow4aQIZl;cc#dOn#r?4TS<qKK?DdCn%v)Z(gL<HWOB;mq@^M_"
    "!e@-CQvBQ?Bg<*?6&sIjon#n6f`JvKwMnI^>|A~gq%Cz}bOLHP5HLHvf1p6CXWaS$=yp=uinBh)rkXfkY`*iT%zim*7j7ldL"
    "){Y+QOYSB7dSN+8`%k0(PGJb9Xa`&~gTqn$${N-p$n*H2gEy{q|oE1!=i2%32HZb0~TNZTo{#~aZJ)w(_ClimPvWJf(R{<`G"
    "#%0a8OuT`Mi!;KAV=BD?BGzZ!BoWlF{<vtl!w+!Joe9HSqyQD-iboNxDf*vN)Ah6Ty;-pI4H5AAnIG;vbQ4D=Kl_E@nN?pU@"
    "B|E;t`x=j{&xq<{=Xiuk(vP*-QNp039ZT3qc^$e4#V?vEl48d>sg}Lhtu-XYvt4L2sDj0;%(PbW@#Y*FnDdv3i>sOYK#LAO("
    "H{)PjkfLrpEpfYt<B=0~62UVs|9(IiFevAM#;3V7=j4uyk=h%Z80)W?5;98UG?3A4vtr+WoJv#(`_!xn*8b9=_AFi}@=KrDw"
    "g;i3tLDWmy@4t5&7&lHnlhJJpqxs#<nnFy_m|&)QT!hsA;%sGU#mCo)HEO&(y)FZ&Vr#K;%DV)kN_s0kf}bWh9=u8+xEchSe"
    "ezZ!od7bN%#F&D=l(L(Z^M*er_45JR(jpT$b2lZ-TT=E*Rc2Y*KZk!^VizL}5Z)KTFQR$Dxcqp(&L2+o}<WL_DAddcpN?SCW"
    "AWXtMOvdd>bU=#PW%RaI;rg#+3Yx3lLHIUGPId`pg#7fZHt)2u*3GG0=127L-;#0s&p|gC^ghN+a5w3H1jFc=2#B$qW^-{nf"
    "}c_Cf8gzg4&+l5;Vao3{An#rH|qpamAicKMFhiv`|ZUw=cnNIP)-4*03ai21p=T<d{QhC=v?X|;J%Kqq5jjml>ER=Q1`(60K"
    "AORs!H(t{?`gL&#Px)+*?VfDgT!$OoJ`{^p=F;6>lCxdYU9Y7h8U7!7nuV+DVAhZ02RK$_>(l&AQ>+%vhKl%!APZP3A!@=#e"
    "{^^T<KF2Dp@}bO`^TIs5%b>2RbZ+lX74BJsfTsktDF_27>+LcL11;)LV0SaX33xqY>a=nvbr&y0XkMY3Ebhq^zE{*`XlO!YU"
    "5h|j#x3zewvUo(^oe@hUx3i|x`JJs4~=h-JiKJdVgVIhFahizHjgF%vPN5iAc)hic!@zD@S@+14wFq!%%zYUGb06j^+Q4^!C"
    ")H;1S7xq0Hd}28^teHXPha$n!v+A0XA2YKruEG<*Mx_hnhOSdxWZt*gKmXx>4Niw4zm8e)%PBaKtK6?np8C&tf6GjbIi(^3w"
    "XS8%7i>jW^=bLCQEY!Ff8AtrcRy|E#6h=FMySz*QLLECG{R2KQsR_CH5X9T_fZW4mrTx2e2i1$=OcfPjYL-BQ<a+Oy!JbOY9"
    "3w*S~+4#W}xFEvDn~yD<}OX`blPNp8R-ipG<IP;>8niysJ#j;zDwGDKwOaBg8W;bGu`%M*CXN-(Zv;VL_QbGpn3mulPski8l"
    "Q{^HM)+1R7K%iex-=xABvpa7{mC(vlJ(gw;`w6gN&@?~$hvy47f4oTyRkA(cnc{i|7)9UxX5q%cR2(G1CZ+#(EG^bLk=P)*-"
    "?3%AQH2FD+|uryl!b}$S-<AgNAZ(U1iN~v^N^a5;n%7si-z&^oYhXJ9^%w++yXd44U0WS0xaU|k+ot5)&H07EJgkWM<f#<6h"
    "t22g?L2FBnE&FVqkc%4T^lY>_kYv`MmY*L;rpw%ioKL_t+rH9GEQ56=@C0psh%F874tIWY!{h3|3<(EjBacMNY>7y=9%|~RK"
    "3cBn8&RLBN85{QlpK{7Ytv8Wak$b0m=FTzeV-<dK+{K_HA7>Qliok^yuQ^?Yh~qMsE27}4CpBQKBQpCd1G#St~)EaH~Zu~2B"
    "?k2yHZvMT5zPVRYjo5*Nht$ni+^?rGF&$;vc}xDh7~$>~Jp-3ixg5z+@gUIdL+(C<Bn2(FjZ#$fJq}*A#KfjG<>s>u&voyTX"
    "ZM4-7xVv}YwrT@vTiom@oqG0WjA0A$tDZQqHhc)k<JXC_bh(Cyo;6iL?8W`A>8!>5|{h)_SSxS%6h6L<*K5B?pg%QJqi*sS8"
    "kDmH@rmDRu?16@l;Ku_E8Wm*4GNZG5B9Ja$<&isnZVg2INGV-<f8%#|CM-B7Q6z6@onA|Y=yU#lB5g3-}-Y$Xi{@2k_&_tMU"
    "Wq2rg`)E8;h0~HvytQ$E)FaHA8B!8ur(AfXur=az6N@F_9t4empB9Ty-L2i|&@bR?cv*K6bA+%JU4qu63$I{@P)kV=+^d()3"
    "#EjT1}9GjX&<z$a>8rPfh|hRd%84G;B9}ZfhYV~Y>fwyesaKSsAKdTbfrX%D(-%-zKGC7CPfan*r#w^KnA1T-}8?e(VW3bw("
    "<}<)s){3Ut9?qy;|EOWCLgvcH~Jf$O~GZ`jg{#XKks*Y#q$MeDYP&64sW|(UlPv;$RO?7=jC6A^N=aNW@nn^;S)v|0Rpnm#1"
    "@2#E@j5<TrYf6Gl5#IAU#S$063N7C%}h+^smF!DESq5Lc{FKw&N_-^hPLh@NhYsx#{&MPe6tqgXdiv&#6OZdI4_loEoUj8p2"
    "Ik<~g=7Hr6$_Z8Z95Z59u9@*+IoY_GRwEx!m_suV%hQzHBZjWqQyg2Frda383T-StLgpj5KsrvK*BOTM*u=ML;x!RBUY}B*k"
    "l_Q+SU30crnL*<*Y48oR4yR-B<p!@Co0&6|%`%4K6NGH}*blAc95vHp6VHtc+Ym5SlX`C6wvbE%|5Kmo@+thESi71Ittu_Cg"
    ";K<5@2FKN6$ii2rDy2MaWaVYe{i)x4`5J=qb;JYJyNEr>3~}(Mwgo=&U1$P=z@I}`-Sd$0<TF(<P)ZC(R(Q8{;dhx2L&@Sew"
    "G!*ewsx~tUP&+2H#b&q%7TS(J0N%>1Li=t7^t^=SJbC_X3GwKd0wg!|N+D<K`vv>px~&GRnbZm=8ViNoD~3@G=E)emmgc5`$"
    "ns(~6{}T70_Y7gwHc{+enTCu67b!OOIiwqT>mDe?EPZ)%GAf25;ydoaX0q}nBNR*O5`Ma2k`yxrr+p;<gw3_x-*IYQ>2w#|E"
    "1XW^Q&%|Y5$k9Vro<C8C=sMPP&;<xXhDAd$77?=RV26z1lX)pH8USeoCnhsp0Sag@?RJ=r<-jImhBph67YwBDZWiNh4%Sz6r"
    "Xj#b<V^dZd%APTd&Ui<d6%@}x>ssQPHeFVf{$S}|A6|#z$!|gf>#hB|@gVX(aoq9wxlP%iNYuK8xixicJoSZqWcZi_WbA@nD"
    "8>Ef>}`PdadI#qK`K=n$@wW(AY3?Z@uL?tHa}2cb2Yz_A!YLq{XyzQfG%bhPOBlo@Aik(gH@=3dI~s+?yB~O!61qzE}=v-%s"
    "8kJLBKj?XP2;jj5<Ja`!cfs7)I{o@5$ZmM-cof8!w!vBI@LbMCyM2b2|UcT7DaU16%xzrLCkn9sj}BAQG1x4MWW3$GEaD6$@"
    "<R(nC{2;?Y0xIclP+YRIe6?^n$zXNqSGC4(bY;R4@ISMkCS{z=;A0!1{B)O{qs98Z3c;AkbAKL^23DH*bphSMLb)h!QQu$q{"
    "S^HZ~C6BN{|Wc`z}&c(Y9a`sxGedbTIkdy*-V<Qcd;838?Bk}yq`iFkYUWdkgFW6mg3Xj|DxGms0m~dVY_VmT5b81mV?-JQm"
    "SL0e>*jMwFD5G3s8>eL)-}TOTlb}aC2R=jNo;y=h3pxq6O<~i(Ye&1ceTxR^e+FF~oZCb)cJybjRp~b@bq=jT>NAxs*|=n=1"
    "vHI?R=pe(U^z&FBwf9r+&#+*Bu=$nh&tNx;xmn8C!%O8KlxEaktD!%6+?Twwzv(MrUm%x-lR9i`5*=g=^cW%k(Q+_e)Vf?ne"
    "%I%h-3^%=qe!w+QT8O99^GB1{_Xp>vnlnv!<|e4_&Ikrz-{LX<_jpww~thH}xg<+fgg<-<A`iE9@Tje95a1blJ<Oq!jYIv(!"
    "PysoyP<XTDp&SDL2%d*}&Yh;M=d#2}`%lqrnuKn-)io(w2#sW9H*BEAl3B`Dn0tPW00N%%n2E-a<)F7<MFk-tR{e+Qe5V;Oi"
    "!g6~99O<3(29d7O~RSr*|YBSc`{xa%+zrX&@u>&XPBRX`da)u^LV=zPo>$P05@GFx~6r6ONyONqx(CyA3$I1b%61ekRH3Y!5"
    "IVT<#!SeE1*BC!;SnM@oNa(yQ>_6Y{^%fCIIG{3`qoHQJ>+~tYe_~ZDic#4f+gFK`^z|)?k^d(h|CjdnZ{krNYrNPms2P_~L"
    "YZ{@!ih5;n6#ol=DGx}0e7b)iO(YQi7_H1PKgZRNv^o1SJhW8Z84-n^_UYy4_Hr;SG-@7iVQdL-`F7=+KoJm{2!VT7fophp?"
    "~&&d!?oa;tgSYrl9|JNe6bc^!d#cQr25{`!Z~`=jxZj?gw9sEGf^Sf<u0MCvkRq>u>U7jQ>UhBB}(B(5#5;@TZW6fvG^>vgD"
    "^2lk62w18?@HbYywJSGcR(A%6+3{X57=z50@!RJAH^D)nC|W*Gl$A2}C_#8sL=fF0rT$J98FMNy9nVkrsPFa6@JTX9>kI}Z^"
    "}0rVT0uWmVHtV1jhl1NDdmjmwJi~G9=P1&d}!x+NVhC%<fnhM_kzd^Of-||cb9_yzE_$lOw`n1Vd&N1j5`+SwZ#${+cx96^S"
    "@@l)`nBU$$fK1U52#ZRlO5VMN6+|fcZ$Si(t6T|4teSc9&nX-+luKN@vH}o~7GXLPj+i{25%69s)Qk!0hDFbGj;FK|T)lO3L"
    "iQcYlOC#4r4Iz*{)u1R|BI#{143)k<+~3Id+;Z((YeD{m@QD+NLjd0Ki7?}U=c%Mwa;I6$U@u#KBxy|jNMMSN>sd{pB%?y|0"
    "8rF%>Us;fQG6XtvSgVEUXLOs|hBB7GQ+If%B7oB~gP;5IXh-n0PZ%<F;;fKddS1TxVzszx_Q>CH237fI)~N^&Fk^eUt=d>L7"
    "6$;Mz>;F#z>La#I+WYV0z^>BvtGp<_vb6dER4`Lr0NHTg9E5nea^i3Lp@!|mq&jf4X$Z2#|D3DB++>cNJ(+o<Ch;!qKZ&m}f"
    "5j3ub_b0`Tt&lgSsL#oqYoc#$KbfF#8eXO8=O*8%BKT{MG^7V(^@W(v!DxYaEDB=22j6)PT$Zs14vHww~l^Or#ybteF7J8bX"
    "(9ZS5Hwi`l`*r%XAOEmi3ivm$VY5vR+>x*9E^|A7U8%KYUNA^W7<M8)Gv6(pJRhHy<1i!uKQ@S6i`Fxv8~+p>`s3|soRzwZ`"
    "jIxr^`G@d6el4^2E3KY!r|h@$@9aS%qi&I1(w@ndz_R=R6IKp42dSr`rtRbj(pPo+&vDTnlO0!@()p~;r~FbF!(<ph^b+pq+"
    "W?VS=VGz3q<*BN728&qVL_qoI$VSqaB=H^TX*%@p-bZNdV#VDQ}EQUjNmE?ticML3!wkv4Ngz8rUUUqh$i@Umb?TVVI@-FDw"
    "VHEgCcPk|5UH$Bbv_{z!Uf{=dF@|9|hok?~%Jm`z-sK|5S>i5gA-MSB|o4R&YsITSk+D&iAI!BC#dN7*Iy5n-Oa4{ZNdeb9g"
    "SnWV9Am*#1;h<VP9jr(s|FRbp#`-4=OF$t()nEPIthIoZtRmGBUT3j9Q)#R~W->NU(O7S0L1Uz33UY2n@X{QvP5n=qV*8&g#"
    "K|Xp&7(vkc#DG5l|2?eMbg~>NxM={!+<z-m=6`EpE5tB=-A8l`&CG&j$0A-mOOU}SQmsAMTK{$M)3kC18WD(QO*!VvBBbv&{"
    "}*!D|3cQEI1=2cpKSSvU#hT6e@gF^1rTi!p?gLr)!9*<WgAzS%x{LTAAg;SfeZ;#ALxHQXG8VBo^zBDY2{DIOR9S2LPYShJ="
    "V%Iw}AGR3J;RFPso`=hPetv@APBA48JzQ_;<bMKl1Hr$X)W7w9ePMfT{U~%s-e}`GR2g`miv81ihxE<H<EA;g0f`a*iSDIso"
    "{uFG&8cI5e#_)JeHKm)~jvE@)@Sn4khN{J;BVWQ^QQMlPV>T5#UW|F0LusQVxOWhh1fY)bEUZZ7tj6yoBJ{Vit~r^bGNbo?s"
    "(6`S<!!X>96nNY6oxksbozZduZ6B*=D>d4blb7-S~k}hGc0^;Z1y>7s>%aWG5UR*h~W!k+<mTl~^3N0|=c>UM;=~Sfu7>?cU"
    "z_sc{?fUoWWN6EWLs?o`T%7ABQlS)ZHbRT=Q1P-h+3$Zv6F~eQ7`)P|_0I0EWrttf{r}L!b8SCv(}kUk*k*^q8(-lMxBp`)<"
    "o^RaItQxBT~t+JD9>O@@v27@edWWrm?TpV_#eWA|M$@bIt67=d?D46gu1g_6L&iiCd<29tvCPizlZSW?jHjjRe>rf<bNgo|D"
    "XTw9(E<iz6U@bw)5^^)v}{FwFu2pU7EQzv<2((R-6+f)}-8-Vy$5z97x$1tB%T=83oJr8`XAE-q!Em*g*?Ar|npoBGYKT5M4"
    "dJ!ra_%DXFOpv9do-9}@<@(5H?}uCHgkFb557DmoHB0}3_d{roH}!u}|w%frCHTpd@BO@2ccroXjg;@u3Rnhro9m2Ez*QaC5"
    "2j+eU-EC-ELrsHzW8`9%MWOjSS(<)BhzRw(+`lFa?aeuK>13Lfgd61W6wP|=<zvg=wMirfPbK|yRIBw^_>Mi`lQ_m*IFCcL3"
    "Y-B`seS15V!fm}@n4eJ;ez~AJx7|(l!mjv>Lu!rZM4i`s*+?IK+4RwOtMhr{BxwnH5u4OP1eC>c{=v?9c@FG5Hg-o$hF*7md"
    ")H9hxkoHhd%0!Wd)=8FjL?@=R>pdGax#k^WwNDOaeo#nQi8^}jbUYNJ!L9TPto?r+wUw2>_$}mxFfs%II^~daDuvC*9rc%qz"
    "p2w%<T4)>3rPt3H9q<6(Ng%ZgzW&^vt{^n?rlQy6JvLXt&%DD}1*O<N0uqfApu-=W%IGv)X)Y*3W*mMdy|zs`e%gn-rT}Y5l"
    "$9rlggn<%D&x44F?thR5!&CcabYok*jnoJHp`q3frJ$MAEETWnjBTh??Xb#?Xl4D&Od4$c_VJEF|?$CKuR75BBoN1c9op{Qp"
    "F#JLAk`9~fATWItvgSNGe%E{HbQkyaNdiWai7on(5g3xg{kJWyD(C|-|$>^hmZEZ49D(6*?y$N&S%XdNn)n{WQN%&ljkz_Av"
    "LO+a+19t8Ua-(xHGDxqxfNTTX@4Jv51A(kr-_ZDF(I*?~lCyN?w~lOqTH4850k`jCFMCFA;b1nZz7Fq?`Mq%B0JvtopSH-f@"
    "C{rrNqnv*bmza)AVmLyTP|?!-8&=2fxkO$ay{A~6*$$<PGi=sDL7f0OKQ8KdFY`N7UMMgOOG9Q_p-U_B!CEfy@72gUFWe0R!"
    "H;5!+Qa@+jb7Vtlluv9k12jlDIy(8Fhk!ZUW%|i^CDPOcn=|d4~{a^6FPTBUimnTbt~8W*XK5fjE6`^dJv!1QRGSaA@#t!43"
    "Chu)g-$o^8vk!{cWgnu$7k!0~&kr*%_;gY%_5%$Mf|uwe8#-{;Qz-BkOWwW5Afuae!Rh1ciyS1kjlK^om3dpDgCes~w%w*j~"
    "zf=ZRp#xX)S9rwkM=5F2{YgXlZeY%|CX}?!ogoJUu+!>)76}n7jOT#u+u5Evo_U-okUZ>h@LgZyjB>I{GNv|`*>!i?a&By&="
    "JXBbcogNJNP?Noc>YypxBHXQkS4&O*sqH7gu}!B)i(i!1hO>VTa0`>Ds{+k;FWsG;6_d2Q^(G}s*)@<J;D&`j?BJim=lq9s`"
    "~6*Y?Yqc#C}<#CJqodenTfiq^-BT^CEg9#hhuXQ1-6#6u2KG{kd2CNH1)kqKjC!8zIUFnqY?NhlgUB%!u|!pEXw=dr|b)+A_"
    "Q02_x-|FP}-ErLf0CLw)HC!U^o~qFRmU%;Tve|JwEeM;@0sVUtdV^i``c}^2-pMwO`SB*Zp(IP4uQG*cQa!nKO`tC$?g>bi`"
    "EoF5-=!*<V8XwZn|MYfd&sM2WuVd}(&ifsF6zth-hXs{`xo;i$a(n`Ec%J%oQ|U6%@b486c`d8wKy=LDFVvq7iI+5j@S$A~2"
    "a)7w+|wI$8tn|CvK-Tm0U28GXyOWm{YSMmESqvrPW8)hr&I<b!$_cC%J#f-B0<#W5DMdEc_>B-!CH#8RyC)05&A`kW1NCD(3"
    "c8;z<g}2Z(ukBqK?Vm()g1YMq8aGjdpYJe@Nn%F45cCJ%k)mMEk3m?lVAb=eG=zkXC>TPm(&^q8gI5zVz6oeTS1K#$mA)Oz{"
    "npMOY5<x5lhl=@ZsZx;cllsP6R&;`uNKr(0m0YMIRFTfoUkrZbi0?Am*rp_4SQH&Kbc>eUHh|}<s5hPTSX)B+1yUrUwvI?b<"
    "7W<zd^0ljrOn<bpOO^2@OVv$NR{xExXRmyvVcc@C^hN)d7SNCog*!<i3nB+heK+>Ku$Y`!bph0Il0MytJP85%Ck};`#TI+Wj"
    "$l+QhGQf@XczPBY%nx2!VRf!AyD^7OR0*dDwJX7d(1J(Ur8i1pkIr#o~bU#l?r)&?&ayV2<vYVadBsKAO8Fhgr>h|$AxB14("
    "gZ}}`kDH`4L8G|O7<2bKpmf3LIq1_~s$9QL3jxPN-ZUPXWRpac3PLm4*sq0cmPRHj^H~^`#jh3C4emHiZ4#lT%UWLb5`ge>z"
    "`MQsYUIjt7L^CfkMe7llHWebF_h>*{!;hD|`sinlrcaf)(aboK!4mV?0KhX)9DWhMoFb?a%0vk=eAEQt#TiUvV*Hm1gbXkEV"
    "Qha1je?##GbF@qogl<lIHe?@Nc4j@Dzx9dgic2+{ADPEY=6t<x&D!J4C(3bP<AXvzQu|mj1<Uk!+a^S^TurJJO$MhgibmXO5"
    "&FM0Xfa<q|v1pSE~Rrd^OAClbCfTRWAK<RmeCk(>eTJy!Ud+o(r1pHX|cpgxo3h?jrO63+N|b0FPatA1^as1wYp%Qs+kQ?&r"
    "p6I=uE#rkA?h<One1gc_KGtz*n*x3@gNi?uGpEcG3P>ew(u@blJXjnd$zqq3_(WnVQiIz6-czAglNz>R!Boj~&TbT_()KK5Q"
    "?t>|5l8cZa&ChS>Y+6reb?Hv7FtCcvYL1^LRMHT4#qC{*$!NjcLq_^vHsr`AcYJDuERYcl~ufmV5MH@*kzym61uHr{`{PqA<"
    "j3hmhffu;;Fjj`NaQFjGZ&xtTm6`gY>a3yTr@<B3G7KKt@dp(-@-pg=p(5sN)b~Dk!pCb7RqUa`f9WaG*0%WQlvL_*t#2w9f"
    "EvOfXKh`X=(pU&R6ykt;|)`y!TArf#>X{}@QW~GVjGucU8jzIyQkkJv+0fnZ8k<U%V4~`x6gmoZ*c=7>$K)&;Y3Yb_-^J+ac"
    "Ac+o;Dm|bCJvOZL*gPl@~9|71QEoNsG5;5pI%+xXomCU^g56tXp2Ywp2h-Xk<x3BJ+lc7F+Z1Uy)j<G2DPu3nM&hB^ZoMRr0"
    "nJ$o}bnOY2vQ3_`MSzrg__p=XJ;u$T#&)t&RZH_f|(kYG=twSBe94O^>~b6GpD#Rx*cPDsa6&Ur^<-1`^LpqKl-S_~D1C$PP"
    "rb6MMiRd4|QNlqdTu}Rk|!{76MGW1~tAqb&q#I#(F3P>>#0;$rHk$fuSf<=ZR2z^DY;!uGWs@R^(ZMn?99Z!RAF=?)3NWAhs"
    "h{SCbx(IcVKSAH)v%h59uDY-JaOZL@kz#bCvJovY1(u5d=WX6aP+C3CBD$+~c`gg*wxmfvG^;{4u@v+(l!4osp6i|;P3*rlj"
    "IHZxDcI?h2PMXcgE=O>aAwFDzvp(%U$mb3DEpi^XHI1cXcs#t<M$D3KFklECl`3}$F;T8_60O>OVJcDq;x+<3+$dfbiEkf3E"
    "UCM)mNg0Qm(W4-2<b{tRMn!^2{3coNj4Q@P0dfG!PEx(!#qQ<V5xBDYwQ+g|fnnpJRd&bLMR(n?ef{g{`<PDRw@Sb;)Rm|2z"
    "}Lrvr7`#?(FoB0Z^veu?<`Dw+wmzP>!BFWI*nm|vFHAy(E)eZ7Y#=)l|xK9X}qjGOHIlv)c`fvw;mw|Pbfe%cshF0&62>3>8"
    "P(MqW)Mp81#!6V#&{k9~L=Uhv+QF691mi^k{8CZFk`Ffvu5GwMNT^23wik3j2615-~x0w)Z!pL&WC<JPs5mehe(Yh1<q+24*"
    "LXdldDcs*sM=1Pqw%2W{lILdAzxaW0<I#*$t(?SU4|5JbM;Jd3R6P9}RJrH(GWJ@?u1qmVCMW|gQfcw+CnT1KQbIO3Xw%eVk"
    "}MVJI+~PEG+^}jzR-?+&98)1%YBLAm(g$Q)vkY!IENXI-Tt_8D&AQ2=~iOCF$~%mr(rL{%Y_)FnbeusI1S%_WkGw&qPg4@W7"
    "A1LKg}tkt_*31oJtrg!2!>^?dOg2GV}^**g|4bu#8}L#C-=0`t<Sf^VO8{5mqqoEH8`gGBmZ|fhcGfrSBSXXolPfW_>%=+uq"
    "U8QT$F8e>pK|yI?HXNJdAE3CTk>GQ8k)>2ztW)QxmT7~lP)Y8MR~GVeQ@&&k;dj|*eI()}dv`YQ^YZ?Xf8&7@vM*j|9ne`J>"
    "Vp&Oi&vTlDW(xOsAJKyg^E9l#Ubm~~nlrEuxmKKXBlPIW17$A=<@u)+f*LC@Y*s1;S+w<+3(ep)8yT;n<%dIOK^){$dV)4%K"
    "(lf2tV_tH^$I+I`&IhAbsUkCXH=v=C!fr$r%+sxr`YmTPsos%*xQs|pz5Qv2ZK~Yw+4^0N6|5>C3VPtTFC@tQxOZvX)3c14S"
    "mX1(2?99qB!>E*i9V}T7D&$oOz<Xou0zDG+S>i7`;a_+h(fhSbqJIupkoF9RAK`<^5Q$ss%&k>T{K;OL$7PX2OjxiYr3owEd"
    "`dLkPT9&kF51D&D46+)S8NCMYN&|OYSv!tHON+7fv_kjL(|OfmGfZRG6~4c%mv*<mO1tN}Hr<pv~~B_{=BR^F&u6v(}3tCS5"
    "3h>oIu)f!$TsNB%f3+cky9j74ZpKRau@xJ10~CSCn{wozdM?et<ohmWf5Mz-D&R!83@=dmp8@%w&SiEB>pZ6!22iCE{WP2+0"
    "mXSZ6u*D?VIsSP!hYroFp8Xgk^(#DtsNu`lqH!20}m}3ZUkA05mdyQ%GDumD%mb#B<GS)U{6C2>Yg<{EnTyB$#u`_<mF6z@H"
    "sj2A3gzKO`@4;5y|DwH*fkEB9Fu=sJxbXEC_m3w77g`jRfu`@rOMy^wXFvRznU{kTSp_S!s`MRq4PPEptjolH#ix7_q3A>2("
    "<lsa2c47BjaMQ_3Ylky+@cD;(+<EZn-NyC1!*Hz1`GX3>7scm_`*<u53SmdC0tf;s>NS!b-L7!ZP?TItO;r_3EMoLlQoRkgB"
    "VeQlb<d(3+8iRN&rpF2fJl$4c02GjxuO=HK~}^j;bZIY1jHCC7NEP<x>rT=mH;&suvA4uAn6lcb*1hsQXku`n7sef6CPr!Op"
    "I%BakDCZq9UKvo>!HE7GlaGA;eijgHlFkvyvN4E7oh=i8b+-DnqE2HE-f{&tp1<EU3ltxAkY+<mqJbJ(qPErFdk7+D)KN)Y`"
    "~t`3y_bm`thO7mbaGxtt*+-=Ul{oweV7}>c0uYUuYWq($+9u~0rj=3s<a_QOk5v)}oc|g*8zn57qd|jw)iC;$ly~v=9&I*bo"
    "udqKW7zzciovFN~>QAs=AFC8LP4fFhK?;YHG~4EkcsmxumgL!Tqw-Tz5OmB`-8cEU@9o%hB~qAl{!8s-byw0lD4Vcn@)1Gwd"
    "1JD{uU1Pr!rhr$XPESie83N++OVRQ_qF9dsH9M?e0CHFh#bUJ@5q^uz$N3Vkt}~wKCvGPB%T=DHLE^C6oQ>2p$tv2=AHdxeY"
    "Ye_;8p_3hBLC)9v9_}Yq5ErbuQN2OYuYjxOSBfTr*X3O@{Q!&UP*sTq_P*u2yLIEQEswHLuG!f;5u=b<;rhVu#}xq4VepTDy"
    "74y}{KSmnPxa_0!j)R_}4`<?ddNSyp>9ByV<W@_ir1FB9q5H|3t;dB~97NtVUg<EncitF4lQ?Rd}EJdF)x2fa?KE9VWfHb?b"
    "wLWF&2Akkdg<4JKj61t>*2Al&Dsh3`DC!XW>(QIjMs$Em~VX%D4!I_(vQ+4|oj38~dC+k|^g>!k^L(z%-O;2CBZ4tv(k>z#w"
    "Qtk~&a47(>`AVyre4*b8n0W(hFt|zRE||Dl-)>a+I<KjR7pKGE52ok7clWz>*C-df7@+dBF}A6fTO#C8%Yj|xg;SzoT)Azy%"
    "?Yx5baoU6-SNr4$Goj*$8Uq*FeQ}>?9lzJ7u+U4B$)kyAUu&v$%Aeh?e&7~H3!w=3?t}l>^@^2)Ri407`o9`eGa(Pp|OEGlO"
    "-sG%2`Ykz}nmmKBKZ?`CP8vHDvzS0A-}i>Nn`O^)4K51Igj66Co1II0^%@j;mY_)Y5?foo!5DvArmUxj_qsCIg$E|IS<sZv`"
    "A&OU%bq2UBrD?C<KrPaEh*7w$HVW+rQ+xgB#+EA=42mgk=*j~C{SHD%#@>d&u7W;fBP?4Yw<u;csF4;IA`No;OVU#w@>7_3>"
    "Mt=h839JTn&!2C2XPubzORO^0UePfL_Q)$`(_6ed>edKK*xwt(ZCtJemJiR=fA0pEGh0Q$}8nfohh7w99W%-c17~RU|J60C|"
    "ckttaEvf0+L4Kyv>lym1N)i~zC#FJ)%|}~N5#R(fOCcz;GS=YrWzDZSbFq<eGl8Q;r8ZGy<5ZGFVOc0r4Q2ju%X9~hBvYZ*x"
    "pwKBPqZTv)V=dE!f`NtnZ1zz){bdCemlARJ(jPnz4g^H!nJ>?#*V9012_ckw?jM1sWJf(Yx|Q^FgF#^yaU@YcP@!l5V!=TqW"
    "_B~{QOp(&~C`w35ZSb&(fAv1IdEqNTcAcrY^$#Y3N=!yJ~+=`$+ik{li(~yfwXm40K&}KgTWZ<K5ZAylG6LivN2_96;{hr~A"
    "wFCA;R*l6Z%F#?^$Zc$t|pbT;G$iSCqe=2WA*E_@5Ysxje5`UdP%hz*cR+M*Ajl^;er?qNkiw<^{wos4{v{?fuMO6s{!fpAY"
    "W{viu2LmK__=g-f=fQ$h?=hD`S>hLP#iyN!TWk)cZJVw}Lh0HT+^Ymr+4ORp{9#O_Lcnw9*tT6%}2dZTqaC82tT2_)F=U55`"
    "&p64*m#-!Hu<U)Ae&b{#M4BOy(x$oK?7`=~tEYM-4SJ3CoWG?i^9fp#n+|lMj%hdzi5ES$mm&F9TG9ctH&R)x8nnlzr;0~+="
    "k&PSMwr2Ao#@aWc|=EbAk#IEz4PnSf$w5@@FG+Q2lZIpUXB$-_Q(0Gz)Dhd&70uwpc~ylA%wFOA%7W;pG)nwz#CO(_vQJ~J<"
    "QrQ_NTVe5>%$@uA|%nYb{H|E-!X{QopBjm#Ybxxs~NLL;}|&_M&C)%aJDUH8BJdji|`4Nv=<})<4CTp?@U8y4j5I?WKLwJv-"
    "b8B_q}19HmLp&l#qu+Qpj-#cq<sBrO4%Al*HJj60;E`yqO?^`v|cgn6@d2VwcctmUy_e8U3MN#6J5$_X3GgeEj;D`Xzfz);1"
    "YLN2jI&AWnN_}lY>)AL8w#V7g4h((#{%5yL8mpWXsrG-E;JgnTZPt)9$r33r<2*eHm1J8rJ0^{r-Y{7?N2xQ*lzl6N%#1|&`"
    "oOkytlZ(wI4Kl5s*`Iu;kL2gv_1+x_Z!Jck*5fa2+WL+9?pov64d3LX)tf}^TI-<)NsJu(5*W@ejcwcpFOmzA^?V-@w{?b~G"
    "WF)?UZaa%u%!~P0P;#vGA(ZFMe6=@n03(piRpKOyW<7&#(LG#6^W>h{lwgLXI?k+INUc5GaNTg6}YXA*6|e+lqcSRG7>CkD$"
    "Fg2Ei@gInCF8CRut_T3(OK}`fsWlfQsG}g{R6h%VvyTOW1n>khIhH7{8}2RO`y<sok6!#4?)ZwZ+Kt0x_I<7}JD`ARh`#D!~"
    "tjxL#_Jsfc~puP>*sO3r(uGuf1Bv7~b_*y$^`+VqtxYriUr_eOE*ijbf-<Y8xm`eSwTx_~gg-`|I?+%<|zgNzb!C^l~A6ETL"
    "8ImZO!GrUgts6Xa;ZY^4uyS{D8*nUdkw$_}O>WRi)S@gvxO_H7@t;@6T2Xh|Y%3QqjN~;uF$!R0PE9kl;qNCVZ>(mdoB^K8@"
    "s=%Tbya{<U0W~AO)*^Xj1f9k|6T8~)_|9sU6})Zz5dF>BZLH{GwG;0CcDYbdkL|UcGv<7t*K9ja;VO9hiP8={RK6vMSH$qAD"
    ">G6Z&Ec9<2{eF=BJj>*I;Cl`ay|n1)YrI|5y_{K9r&piNO`P64Qm|bzqJ2mgP1G(V8Xy=rr2(oCgUEUSXdfpI#|gM-h_0bcc"
    "D9|tSfFP_(lp|RcOuR3!0jBpbPS7!Zp8_%glob88X`evB3=OzG3LEGew_9UtiW<Q%_oN4YgBU=>aFLECmaE<XtBLH&m>0so)"
    "&^Yl1=ZoHp!h0Tg@FBrCk>?idGV<2%>8yRK)%=WpFm$Gpc4QvTmpP8&`aR+ZKBm1aBy-Ii?Yn{1*)o)44{Zrfj5(cX!F1u(N"
    "0*WzN-rmq3(VIF<K1u_i=J+{SHVOII%Pi@Z?V=Hwpmw|-fzpMB`z6l2UO)d;RkYS~PK9Bt4>=_L^4-vx(cw>RoEWYGyK@*(9"
    "eq&sUcqB3#saI?aw;?>VA?J_VPS8BxHRepBHwjLInjv*t+PqJPC}iOnFSfMuyvejL{dY?qMp+ofjk$!5s{nsosI!m|{4DmSF"
    "oX_*^QX%(0d%3OAB*<w&lY`A@4n&<Sj`G~QEv3;+9Y;+LELIRE3m=16WYpUly?gSZkS?}>>HMscm>|9(v7BEDsa9P>9GsicO"
    "pm1<@tI}y;WU~7w9D%g<$BhgS#j4dMScC1e4)?F}O$th=j^G?lPn@xxK9r4-eOymJ!l&KCSi>SU%15<!r&IUBM_`S(689&0c"
    "luLA%CLl$e$T`uCXtZa&kL`2^z+m<$8`&`<nBiJiif=C$p!)cPRSq<|f*v-`_pjU_)DFs%Aa^O8K=+Gyihqxw!GH!go*_L#G"
    "TJ#w+V)VtR7-WKS`%M8fEIocgbjdc%bYHBJV4Xdh=`i`^#R`ro9U_tk{3iPdg<T2b`(%q`)Mw@aL)?44&{bO|o>g|Iu6futO"
    "A@+ZdoGBKlO%Er^``&?f!hyhR#mbK@jfy_HU|B@fREP<`OB&(tYk{tr7yZ^FaRkKTYEAQZD-C?t2i&f>8}&XT3E)A@83hD(j"
    "80r6)<?HL#<X^wHtk~@Fvn8<Xc1Mmbm=Zw2Hxkrhr6lvZiEYo!1Lwi)3)Ziy3WsQv$LAJe{f{dF#5~%PTODG+@3>wlL-^fTL"
    "vW4`1D6k8}~@zA_26vvy;`(gD*ruoXgQYo*4D(F%O2*u$D}KJ6@Zy#EMTsX|nW;mY?$0(8#DBuoI{ptV4~X1&Q8NqalvN$1I"
    ";R$4B(`IzNQR4rrwIZ=Qb%norsu?TTa|!e-;?X-_1dDw<b(!`D&hfWFwCW>_{YFiY2Og;Yv3jf29<$PqcP!ZjSXLKPXH#A?|"
    "+%VoE=pVT7z1&$@5+P>}HYz0N%B$Cv=nCnGTZysnWp`A^*Q>vr5z!b$omjTKlO<I`8&ePtTTb9{+U?^V#!?s{Nsgjrt#?k2N"
    "gu6139`l*UggWvS9Y2TS;<yp}&dU<eG9r<$Usf_T1_>cl+V1}S<*C#MbNOQE1<u>^Es4$EM)cwc!ktaTVPdYXI7hPv23@w@E"
    "LyvA*3Ajz00<=TSoQY>ANF&RQT>Jz7{1!YZpcGguk%D3<K=yYaduEUpC$qcUe|jpv=5ADF8;&pL4FoG@7Xt+96saWv2Mb<`>"
    "tuW7z^ktsurDhB9IZsUt&qe%o+Kuct94$PF&0nY-K^!bf24r#csq^g$?$gQdPzcXKmi>SEn0L5LA}Y*e_0*&K$!rLt0ZG6o@"
    "9MJCSKMI%pQR#ndd2{_dfgK}`8H2am`maMl5H?a5ctfrkB+0iB8C+;~j=7&v3RJC>;&BX}Wez`!8W1sUnNKMHPZrj({u{Y#?"
    "4E^dl;;kuV}paQS?qfn0D(?y}h!5Bvc<N*U|O9<UQqW6m}&WbF3N=G0oBkYKPUSdIryi#CmtudJy&3s(mQ+X-hKOCF$FIAdh"
    "uJ)&cYVN`L3@UFv;RjDDpf&)$J9$JpQ<y8<$!@g<_3c7*s@uy!=F6ZMhZMb%_QAj^mQ7-Zb=|h+h4JR8BQI1aBwwJoP&c$hg"
    "JH`GevZD2Si)Qo`;EgSPaSFhPFn>_j_T}~ygY@;9ux)ky6^n?ecfD|PfRks6jb@xg8x;&$V+V7GuVEr-1nL(e<H}w0pc<FGM"
    "|slYeR`pzAV4+U3F$mEyUNwg%Yj7c$31n$i>rIvWc2pL2Lj)HN*z&l{KGCvWoA+YBR4du=?T9Btv;kB3Wm7e16!(Z!cJ}D(G"
    "xDt{TSKtk0!2GG?n{RICw1tfa*sd(-}JM+no1K}(7>CPo<2L$>uRyH8`U_aX=9{bX$F{8iBLiB78E_b5!rAhCepj_goUMji<"
    "ZL`EckO2k?GjmZR6Jd;OmsxDt!e?}eRpPv}GqU)C^KyJJMrp8J){dQj=pV!B={Px$!b{TDxZlo8Jmo1T(Zm}-C?SV}}WE)A~"
    "9#TPF-}adC$?5U&G!kL(gai(NyCdCw^`PTxSUg#_x`Uu!+B#VxMcP`msps2q7yt9sRN+L!eomx|x0*&5Lmz3y)@Io|#P{=cW"
    "+Q~)!~ktWE0vrUC`QG=K#bn47?G2wZ90(vEz$R;0_OHI1m8(~vGZGME?v$7i&|R^=q9j(&a)5^+u2O*z*x1jVbu<S^jlHvZs"
    "bNdSc{7xneszKH}cip&i6hxOEs49N_Ed$WUnComHFbbrlH2SrAI@Pv9|y-$7*1RIzXSMjXmo}ZH^<2t_qk&44aYhpi;v5-2A"
    "FlMJ%Z(TNelb+VmV}ICLSQQVsgt4;yLrlenk72n@lHA3NzQBKe!^yQ7Gn^}X#F5}L8sFUd}Siw(}NV96@icOK!caRV<_r4gw"
    "V^s-bOR|3&T=b+}R0^>v>0?Rh}y#m3SBoe;k<<F?zT7_wTN*iw^d!Qd$Se&^{vXGbCglTCUg6N&$;;c=^R)w?-!|9uQ?xWIX"
    "5`hrL*F^m;xwx&_^c%vC7r~ZSw-r~dU$-(yZ)re!<u}YQr#bNJMtZmc2ljQwO5=J+Bw?yUl0EFrf;riBZMl!4wc{_Vls+qYz"
    "^HVq=e5<tu+dA^RI~vGVJwkd1JvNh>-k=6{ytVO6O2$25eqNa4qS&Zq1)v_8CFD71sZe!CYE&!@6Jb>UeD>ZO(gaY4mlRhDH"
    "7aW;*6mswhL8Kp^?#ZLFL0qZ0>fAJ9q}y9cbYd-PD^wzDv$Y#pvsoX=$niB$7}nreC3AwTG3$aAzEoV=dUv{l60B!N+!{9;Q"
    "XIwIxTtamxp0{lNT1Sfa0v8&JT<hpEgLNj8WvltA5`*?j#aUs+Ivfm?Lm0fWA;EvrN@c<#S(gM0FAqe>S5gzB-B7t9)`?_tR"
    "3-83??DRmE_ceRR?uRZF{AZ9)bom*bEPhvAF>t5^Q1mZC};ISF%e}w(3>GvlE!N2vTPJ}HAEeB9QVF=oQgB1BB8(sJ=%LbDK"
    "|CEgTU9eHE>E`9z(G(h7fq69lAw8TFd>Ihl$pV#0u|m*arjatZd;&sfl02&*DsDo@Z<f<v=n$8XtDti|;pgD`deCfr^D5#C="
    "H&%$<@EGYmoc(W!Y`&_HV@ad4T%y-pL9%YHtxd>9*RpNZSrbJ{)BMvL*!9@t8~8r5TA8AeAsp)QwX}qM9Zk6yq=vu3_7dNUm"
    "BC7C=PCfb~Lb~oPxeP7l2nA<8y54GATzlV~Z}Z6~$?>=5sr<2VV|PO<4S80)D1sIT=wU@H~XbE{jItCs!Jdz9I}$S9=AOD48"
    "cjKGd3{X+in3lg**MTeAHzj8K`wSrp+<J}r<aSm{r1N~CayFQp7NZcgvNt}nnq6R1l!qB<QBIBl77u<k2`^S}VHj2Z&c{<fs"
    "V#+`mEHI6;EhY+IZ_ezTi%5(#4O-r}p03QEz6YO-Bw5KsN><aval1~ycOOQ-eg<}pegV?-xIWs5T>+|LZ1VDkIR4m2edF}By"
    "$bX#e>8L=B30|TIJsww2hs`HacU6ScEke^A&(a{8ta_aaA<SY#KUXhlP50Q@SF^w^(@{LdP=`W-XS~UoC6)0|LXIikpf*)~m"
    "Ll-#GS$lS!ZwTvzU9PXDy-OAf5G1g$NS3F<@Q%1Ej46r5+r@xY%FM@<2Yt*qt8|%<WaI^jlYA7jgLit?EU4cQ0%1nR2U&oYF"
    "#{Xv=;`CAOEG#t$A8Hp^syEqJoUMXhYoZATMb)9UstzuhN}Z8pNB_a9P*s`q}ok5d8)e4PfY{^XRkSv^{ElWP>)Z*gRfVLN{"
    "->X?$xz1olh!5S?Ap<cDBs@*)x~WSwe*m|l{)8_e>i2WZmDjvKDxZOnIhEtp^R`F<#z83*T+R1x#E1)R08t#ahX&;zV+8h&@"
    "zh6u<dd>t9hLfz#5k$wmJRb^E0@?*o~+;^<?ZnBpO{=GD3i^J){2kz0BtykL|eFiW!t2e4nZsgHL7m#fnA}7SY%TIry5&v0H"
    "-31tLAFt;{>9G5zIwUV}!q&o$ag?lbI)7eTXH1q4sKA611ygMhUBk_Kx4eX_1A@ZU5yRp<8=wI;irVTRW}M!=eM)41!kxF#e"
    "bTUnc6fTqhFnU}(okKg<=<*i$I|@7!-P~p-w&gC`le*Opr?UGFBeIc^($^nKyySOsv`^{5L3SiuG|rIT?`Pp1DQo~5Usb{Q1"
    "S9D)~YeLjSexfqBtqY;Bhl3Ro+&4F>RclLR)X?=H4f}u5wQANf+n1_PY>I?{z0VjREL8%gG`9-+R@v7Zc?_wgz6v0&jzX9kS"
    "@jgQh;C2%rltn{-`s<ifLf<E_=kJBubui+6lO7jD>X1-v2Y`f|T#y%S7g^rc@}lc?jKI{`o}>~9SXHw>{2yeHCR0!ET~V?iQ"
    "ph>7bMBxS~3eEc~HE;nl?y)<mZ$JBv=Dlt7eH8~g8k}N-i7inAiFsxDwo(N}Vzu&m|j!5%$f<8G^oy)KKs`|-LY_0B7K+wB|"
    "1|1gWN8njgznUrtvqg7D?w<k7nmbKRMh#&f!S!T5+f-!Px@ITKjfas&Pn3$OA4+)}=EbEnC?)&a(2j*VhcKSLW3jg1kJwuXV"
    "%XtR$r(~3>UEQP9cP>UO;#n&)V6$Q7rJpX5TPizG^=){0}??Jr^3Jm>Y={Nw9c#`;w$)~gV*=7;dhjy-H~HPZ4Q9GU8yeMeR"
    "L@jDuy%y1VLUEK$f(SJ89iw6;O@FmXNKaF<0zt=k&Dg@kAD0Hk8a4G*VQWoy7~TnTnXfIIakF2&|;vSR<{ljS09unwu)EUyV"
    "3gJj+$q2phOLmchtL7WCjq07zK_=$5~1E;DqWRHq3d%FA!#U<7&6vNnTo5=+d)ZK=8xeL6z2<V^r>lmfJjQ8G?|1S52%hLO3"
    "cGErQ^7%e?~#N2O?#gPUHVcz3vLZ+5GisiK;x|5O=&w;6TXS15%X<gC(+4vEn>7``Lv?4{{J9fh1@Avqfd3W$FLHqG`)7zWh"
    "rJUV5tR7d@ei_7S0@p2B2x9Jd8lYl61jj;e_(A3-GxDjwgli6-@`fM@Gks+a`WEg(3HdbVhQ83pc~drdjM!iYFgAW4b>K(aK"
    "xExC6i=_qG1*tH`SaJh?6Q<Bk+|ES^hgFfhH0*_Pp|tjBJvQw7Uw$xT{>tH5r7=ykk8P|pDp3o=3iHb$AV~H?UBM|32oqc(C"
    "gAqQeQl0=#~5DV@rP81t$MVgDHK|u!=(DyBeKXsAGLZRhUqc2jftvjt3F@RY6a1?VQ!2w>xQrQUmE75fIzr>xjV3HPR8ZLL`"
    "B{jK0@9#vqW2&X?H|9jTq)>83eqVR5Y(-!}c*A0ZAz#ogU~MgIZ@T~K9VcJ=2^JRe~}GbtpGooBX>g-&wY->|kD8lq{Eh6{d"
    "2szw%GI94U7B(7ECw{QF%?PlTgo#9n}i3Zp9#ke#z-leKsLHc6}m6MgI7q3sT1}Y{_juT;Pay?+!W|U+uLYb(1q*}$x0g<MU"
    "f!2xyYX)8B5Q*~mBYT;+tm3cQYO?J#$B%wHUh2eKS28$!Lo{RPvx(b>q2+U{;$B`%9)^Y@Syw#SeToUP)PuJk8OFh)9vPVh<"
    "Mi(ZzmrxKmBakVds(zD|Ma#=sF=c4NYFoO_ko;|B4cH6^Ye~L<KyC7oAlbtjeDUc@6EjF44ufmTnfim`Cnhzt&A&HDsq-rJj"
    "m^>t*7MUlZ<?SLCl`)R&2os@<>b*ug2{-g=tI~;_P6<8m2nH{GiMh^Jg0&|4o43mcX6Y_2JBZv1?`5!=YAt5k^r^Wn*KbP9{"
    "3D;&J8IOfT*A7^C9^@zx<csUbC#hT{;z%=w~+&qd4eMU(oSr%7wW7s+F1LVcfqtVrB<4gtoOmy0qfp2~Hq;YsbSR$KHAH``7"
    ">cHN2<pyuF!mUp*i=}fE(*xe*osC?|jp${Csnz>Lao7`RhI8qaVhzcdqx`*m9VZCf`GQ7oP?TQ9@+V7Nr1mNH~bcRs47`Er`"
    "FY^f<^OgLQ*4xz-f{9U~TYdh+0@JI;b85XoZjRBRPgNXw*U;F={*Nck_WC_9NyY)Wzdcaf$FS2-mb>b1wCJ%K1sUiLqp%3Ne"
    "G-q}JBML~^0FBHKO9^ITNGRuq#H>IX{5WmQ#z#^k?zi=kyg4prMtUcKvH1orMnxJWk3A>!F_I=nYm}q^mem3jlRp9y574|_B"
    "q!vvU1ZVf5s^C0Zk&S{R%ehly3Sbf2+Fd-mr#-b#T@EGLfjNTw;|g+Wt0}IPY#eC|{{njxpp9h^_SR)eGe((m%7|sCY*k-k`"
    "5_Jr5`C#Kpyz#24ahlD^a`<_-;(Lo5AectGeoEj7finXT4sxv;E+B5n$a88Pf0)?ce?3&^%8(E#iD-uVle>ux;%{JY9hd?z1"
    "?7asLo=Ib%;xebJg+arYbwdTJhb42mcV+q-HCev6+{zd>Lk;zJ?#lQ|dE^;^Gcn8=3a*eg2%cgV$7HFdQn?StvAUc8TIbmz6"
    "e$zq4W#DC3X9)uWKg06!%M7isW6=wJn>=}9yTN$ZWv?M2Khj~W`xs{v9D)gq5vq9!+@MRO;m65QF`}9na+qsy^hB!W8+a&jL"
    "`OY*@;jz3oc8pK1AQpQj8>Uuc##92?wwt>SfF2~|NRrT%!Da=OKff(jU6j4`7V?1UzC<zSdLedw602d;sT~r4RW<*lmA?v+d"
    "h8#d`vjFOvT!s@PCtpem|>WEB>w$a~CTn2q_k8N9;LddTn!4l|Ijhn#^n2oM$OumjqPsek%+qteF<I<5qTdk+*&Hg4n00h+@"
    "Lu>0IZ_N!9Ur8wvfW$0>uceD(?YbW&^sCC7U`F6n%|nM7T34nHv?Z8(L2pBC1v>{-c|6d!r)>g+sn27nEXjU4n|R$>cVT3T3"
    "Gm~*gMPBbuuz4D+-SXM#l6sa|5sgon4f%GwUhnAP<z|cvloq-7|e^VCqZBmZ%h${Iw!a+gZ@Ksv7DI8!vZEeTWC7DUrNRaiT"
    "IO|ikxW#3S*+GB%DVLELqiK{5*E*^&#WhR?Hvx+t46`7a`yWmo0f7qRC&yUDMZNN$BuwnB>Nqg9-S6V0(V)d{F(b}_K0lzb^"
    "IiRh$`%x9Gf75B`Njbj1g}mjB*UAMHiN+D?OwZ1!yioZ>z9Nk;22O`&sx{WPyQK!)dF_#USKb&7=W|2W&`^p5_*D!$SFuq9}"
    ";D;;mjeXtq%Ie>j)^dL{Wm_A!8&2c8=)X=UhgjCT>1A9B<t{Q=Up_DOX}cf)+)W($9ft6l$fjRaf9ef?*9bWRWHyLha&kG@j"
    ">=wI>)$*Gh~s^K}&sPvl3uX_eu%!AtZO`BG2Ur^|}VRm&<L7z|w)mo<=q?Bkc(zWUvFUYC14D~%=iLs;}_D=e(Uu(U)y?l~K"
    "|%H?52^C3W_t+`o4%(S4ajNlz@c8`yW6HC8V>BPVIo_8E>p19|O;Z!oYSoIhVJ$<B6SxW9Tkn5rhv(G}JYAjr)jJtgrTHny="
    "4%z~6t8-|(Wh{MQ|73E@*O>Hl`oJFiS@}wpGTLg=G#km+{B7KD*N=7#h)n#(c|f^B)*Vr%k}X%QG`KtvTPQO)7dTCG$8DlmH"
    "Y11L+iDhb+5ZCFiDjRER~EX2z}yXp>zROaFfe%Rd-6TmuI9Kg#ieY7V+5+d#_}NIA<0&s3R~69VFh-6JEC)nCbb<)J)!RvH9"
    "7$FwzkKx<@g%tZ#o)*e+Y|(ZK%K%#L)I5`bw`0gV5$_b4BM*{Y^5M#!$SN`4UAq-@K5d{=q)BkFaWQ4n)%WIiF?Yw0)EzbHk"
    "zq@0OH-?`yr2_h7W0VB9DJmdq6e$$JHgT7O@r$0)J&>~<7|iIIa&BU9=aSE}<6Ts(A?8v3q+c{aS(y5~fxsL$tu-FMsq1?W^"
    "uth8{S&Sfj`ju+nn`Q^pt?e*C+StCFm?_(8F%TZ#{9FmoG`qNTdZ>du2H3A|QUNir+#EjE8W&PG~0Ycu-!6RLL@d$sN;weW4"
    "6VI2(T8pAuPR2{d3ld#}Z>^STxvE&XR(eRm9Qv!1sdn}MNePB7pG{9s?*!poVvWG`{#^(UAoF$Xd567t5hp_&VuFBc{;nwJ_"
    "4Z!`tOhdoQUE}on3EB@QS!Vm7NOrz+NDobK=d*x49-Mw#i8TzUstIL(ai*Hbxd^dgKx&0^$XT2+v@z6T7}Oz8@k~JrOgSy$%"
    "Aa#_8l7{(S-A_&QU;3=9{`pprVRhdjSzFxrQ2Dlvtcm@^{ur^{$aUoVu^&&Jkf^o$T$=F)^*~q{y6Z^@gSE`3Wd*9sH3p1n4"
    "a>Bkw8d(J$xZDO3neo)|sX9B<`nqW)o7XD9504edHUCgyh~f)%q_UO<*Z^>-M?4s%yy6M}G<F1(?vr>h~Xzdj}Sy9AdHNQ65"
    "#5ef=glj8|R79FR*lGViY4eO~EidbljfGT;>zZj(l;c{F}YnN1t5M6E!y+rTlFXQ%n6o)%fbeq^PXDDzVDz?ECEzA26noOD0"
    "brO3*3X0`si2SbWr4J)xoFdN1d4jIw)rUuY&V3NRp4(|*ZFZMIA%bs$r=rt@sJ|vs>k@iZF-YO?i3|Cwhnp|M0$I<&2>Y0iQ"
    "vwlEEqud;Xy$56o7S}U0X`w5rTF#9B3Y1AKy2Sg4F5x3z4+Rf<;T(9nbs(|C!OuxfW+t3$X&;XxzfE2t=i^F9k|&y5fGpYgj"
    "$RY!mHV0*I`8M=2@QPsn@e~*x^jO%+zJ*52~S%@-14i=z5qNHGVoyORd9XyQ&9kWKry8CD0YYRA}Y-9uWKOr|LFOiiJbd(hi"
    "C^oC%idOXyojdU|Xy*g4K45c9SXT~@5p2hhsX*vQEE*Z*}Dv336t$gYJ7u1gIbY6uaM7j*DYGsD%_$&>qrn*@5krlfpAH4ka"
    "(X2k$)GMv3rM}sH%E{3le1<TR&(}M=RJz0ot>pgAFWT2=;lC_nH>9#z1xdl$7z5*!gBa+z;{aVs#E6$rEEC)+PmOW0RQ&SO}"
    "K&vK(Ux1+6o$lTCR5t(LcNq$cD6w$|tdC#_P&;FRR1;Omq-;@?;{TYqqOew}^~f)NdHT|WAosFz<1Z%So7JPX8!_*r08=a?E"
    "+^Exik5#(NUi}`nqe43)1LlF9Y@w0+Vrh~t+xt_$^2DcZv=bM=Cs(6w)>3($o0~cdO+Ke_fNl{q{zk+2m+10b65Q@13d|x%v"
    "cbwrSgIb$|~vf3j9LSgD-#9;q$hY9N+y_11`;%DuLFH4>|3p9qz~7X9@!!Hh|w2M&THL%~E5lrIcE^kC%R7h6z1?kQkIg3hz"
    "412jr0l-f4Ww&&a4&BtYW`z%iL<nEgWe0Jzy3H{e9rroihPUo~OFh+^GQPKj7x`4ESgj%v6yBxSxpQ@&eKNHqrTJaBo1FhN;"
    "a%m&ed>+e0<;fi>Wj-0Qv57?P?*iX6#XFBtfLfNJ3nVAnjALbMU_6nR0mW)k;2hd?4_bot^VnP$2kdqb`BD~i5?DzoVNIdHn"
    "c2o7#q~}cQ+u*izNDo5@&BbPXc!lih5(;!EIpISepBHtDoC(6}p|PV8xmZHBOy>I)!z}7H9lYdr&5zB-3eO#@cQr_qEUjn#W"
    "98S2#<HYGzC6lZ{9l^CuIlsa7_fD|B@rCQ(aDonw;`~j26#!nU3Z^3M!f6qFWA&!$PhU2_{4U7&G!AlV$zFQM$Vq)Kep~GDW"
    "RPo#a@0`Jx@Eao^G5NAN2mvC8Jn=kzJZOs7KWKRv${~;21`YaOgUO$xjJuwxNgTjbtv#=48lw5?C*{Bi?HB*_W<cWpL??K^D"
    "f4W>T?U-wL=BzSj<sW85nU{|m;fMtf*wD6D8UZ4Sf}rg%FSfK3Ifw09e&$S%DFtqU%Pr_!&B55YBB`qFQ4s}JAZ-5sIP-yhU"
    "i<{K_g5LSh=#{P;U2-?Nx;476qzM2`mziyY+E1el@scW}H6OXEsU(Tlb-IIX4vnsQG|ND`%eXhd8^vuf<Fuggts1`m~zR(t#"
    "D6f%U#Z!j153EYMVh7f>5>aqF!iU{>DW$Q@0oGhoMlyU+{`B6Xc&hJCe@j8a?oN*8vEud>+78G2$>Uf~4u(Z0E$9tc+2^s{!"
    "JpWVTN6v5&s6>?9r9HhaZX1=ip90t5tTvOMeGp-5Ep&kOBTL=I>qe$UV19Dj>ySk6e_15(6}{ewaSEgtO1HQEJz>Xjrf}R(@"
    ">jSqP~ryH^v76u4B=;#f`F+BE3;5y%l*a@*ZGvhhh4ffye7uyeucj<4PFlI+0LWQH?&`SD~yyyC0@u^5JN>OxHBfbEBrVh-J"
    "Mssltbq*|_Q_E~TQx=#W!e>JMCj!L^}_y+wSO*R~$fZq^ge<rA{|?1yK*EPD^$fx>EM14!rk$q(e(XcnMd{4bOUFYuVP;3bl"
    "754K!-eNqzV<J@p9-tTmTkIFvEjkh%^V(j5{RS>`BSDdDc=DyE?7I#01OQ(GwR;-U3#>ko3DyT$A&bhcUvSqYgb7R`vk(|Ju"
    "^76>J-kZK2Cza)w&BQ13O6;YOM^GONSSW?)KU4KuNvy8vR3vPNLmEw&&yl$1Ly?#sQ@p@}ob7gs!s6<myC0h|MJPRrdctdXt"
    "U?VXa(Kn<wh7B=e%z4O6GjX%(q6<hB1DS9GwEaN7h=DCV3!#>BrGM`2K^9ztcVtO`ZaRp69Eb<x=8PPrCk)(c;sXGFO~Zy07"
    "m1H={5VauZ(YF++NN^f)I5H<+LT$Mb`4+NDQV(F~H4YM6RH*QN4oy%yWKeeeLRSmT(x}><)G2`~j4jQt<ti^<4VJ{nazRD2q"
    "z6_HdaJEm+8Ue`0@nH&Ohz{YLh%x6vksRZkIO!VO~QIKqs9EsFdy76OeAj09>ux4>>3_kt{;u{PbSJ42}P=nUP2(CF9{DB=_"
    "v__%=_yVFkiHd(757r}Ue)BAQWCNYyMtegH8=3;JtSA}}=E06xO2QrHx147!C&A@UkmSfkNAwl$2Z<xT_cI>ZyykJq}m_se)"
    "e4Mksl$B+%wsyyDkd*Sv5=;2XZFn8`D6wAurq3>B=k+Mb>GVCQ>~)=!9FwAI5DovWt2sHTTq0%GDXQ@7KSZ0HB(suTDIe20A"
    "dShuC}7PO=2Ntt<=GW`ihmr>>OGP3GDPe(D-~7hT(kDS=FMP>o>`x9#kSn}Ra#Yjx&`tg7#o;Pzf)EzHW(D1Oy$VabS)~1_E"
    "o!d!{iDjbhxF?CT-|C%OK_JE#I(0zTZh@^W!G?Vs^7@jNG3g#d7W6$Qb7eOI%BH#<By==hy@lHnqk`>jaXKjyj``B&W{fGBV"
    "$GPnGo|ZYK>>$6uy({Ujw_U54nnFphDEyfk?W5E?~E0tS_gE6->xgp~8oHdRO7ewrA0@n)tbt5X~zzLq%=yeI8N37jU_(S6?"
    ";G_1$2(*2cE21%HV(;29KMnDS-sX8w@PmlgN#W&EPaUE#`&r)-+i1D<uhWRXXSInDIG$tMaZtL5RKZoe9I21QDRnc^E<b08}"
    "{jVOGP{E5SFpF;qHwY-jczp)X3|F7di!~}3?vSbYQpp>AYK@s5@bdVp{T%>N-~tZ5M~9O9T``*|m#bE}YMn+_?asXI$5y#Qm"
    "a~9w2zJ=p2akaEm`$HsPh%i{W-Brhw@`MFBr{AL_RdgCh7rWT`f_O>s;t~hybvb^gI=%Qs9<>heI`!@dJ2Hlk@<BallySw20"
    "jR;sPb#!hKlbr8Z#~7j2Rt+$vZecC6yD7O-Ne7kakHUf(pB%Mv94L>TSZU2;nxneQ(tjt1l2^&Jm?pBNun1O{GnlLkh6x6)C"
    "j=!S&HTfQ917uSDlC!YDNO4v%o=b(;#jrHsFnPjBZSRPA!B842!cG_k-T-2}l)iQq$I)BGF6-10j5+8Q0YBS_kV*6aj-_hrU"
    "R#scYqq)d&eXx*y`;sji;{EOHMXby`x?bC#C3chyhKByhKmIlxf%dosxJ_x#1wKc_-(x+Vfii9R>-<LZSZ29a_V`^_c3}@#`"
    "k`i~-9{e-LUj2&Un69F&D=O$FU%afUw)1x_m`S9xfJgRm7TvFB>o5-5iX5d?t2Z~LqA_^Scq~QK|44Opc+XwyPrdy!TLv-W#"
    "%qgaeP>7;nd5OHrR1*d#QYmJi&IZy;5E2g^tB#zczGq5!Lst5B0@?v9}n>1a0JUisTB8x+lMBZjn%YQ8@ho~fc5Q`m|FK(ka"
    "!nv6hCMy=;XTJFP!kd^>V%O;yc2KhOY9Xs{g*G@R(?;7CBUpN%t+?S`Wqz=p-QT>D{2oxe^)|eO=Dn@@r~PAem5(WE73cis}"
    "81#D?~wKDZ->2qD}Rxez|^5dDEZ;t6-atdn4-iokZ`Yo51rk25M@;;es)<KJUR!Vr-gn*!^AP0;t8=Dzq<x02!w44u<&$<8)"
    "xmR(mUxyv{(R}X_B6OqQ}Deb$WARwG05IH-2+D$BfXR}Hh0BC}1Rn$FTwb|Cs+>$<ktIw7qOd+X^P<n{VQCPb_lqtE;L#Prj"
    "`rlMe(vvg7uzod3Ag5;DuT7fDzZM*HUIYhWN?QzTI|+x|X%3$~G6OT!%sFjvuZU|}i&Gs7+M#Bq>PW%iyR)+tmrF|jaZMP>7"
    "4z&Jq<_hj#h|dGoq-AJ`_pBXVJ`&OWJ~-uT^ay5@Z?LLOBTIMmu41#qTIOEw;=4|5TH(`vzMRN_2mU!$C@q#hQ;1gb7nkPaq"
    "Jgg>9ofl^JRK4@TV;1splY<_Vt-wqAN1@M5))J=`@$%?rXKz#BrLil{O|kxIZ^I33n>n%LIr+(;WAk*K*IJ&7^=LCnqQK<VN"
    "ayeAK1&<Pf{%b~r_#TD3)sa%D|aO~&X?3(Oj;N5SeX9Oj#4burLa)wju+(c)sBNZwG5Z}PYg1{lt5Am$oI4)K)QVjuW8w)cu"
    "j83fq>I!!+<Vo2o$I9WJOnGxQT(5l4rD$QCy5PV8%#Xw%#tl;`C(|l;+KS!J2labclq{nL7>Ci=RZk>Ct;Q3E^mnbARm&5u~"
    "aBL$so`-(DP(<cmhATDl;l#g_x@lc=DjuT%bYDco<ia*DEh6a}&RRyOuNRmkhFd<i$gXu;b~t6tbT%m1E8Yi(VIjG8wQdp8)"
    "P^V2C~u)9e16JV(P<RO;2(;OY3v^|4<)Uhr27^*Y3WwY3)TDCv5b2*IgL6-VY4#{lpM7)rh7%sLk(Crkif)kb(LbKp|aBT>~"
    "^wMMP@r4JpnHnDjh8uI+x}{Uk~p=1=Lcu4zdc*7W5WpvWvKN5-Q_mJD%&^zT6w`GolMXpmlYhWLWcK#OWlKQ{=WRL1NW1JNo"
    "K&ecUgW*5CL3hQtGfs9xe>aDt@JKj0SW>4N@|j=sBjrMrhUXMUNrADuzwx>xhGj3lIRZ6*Dm$E2z)E!BLX#22zw06M2^2AEM"
    "K|7t!om!6hEe#LPpNAI!iyn#4Msb>3}qu6S&MIg1FxOvaFZmWr^0~BFA4HzDxf40eAS8+nZ^jWIMYv?ma80D_6e_*79Hl^8u"
    "g)h64)7Xt$H!`6(;2E9#ZS?sYS-bJUZ@m<$3S>I6ETot1y9wt)t#Y&znm8X#Kec{{{3vy=DsZ9PmM_tdhVG)=;r81@biF8ax"
    "YfliQ`BnWf$C9i*ovEg`Zf^dL~oCo!kkD*XY56Vpm&$>lX*yywp{&_z15*<nL|ZVF2Ab8w}A*S1%P7kJGD8>G7Q1_pII1Bk7"
    "f-3Ai)Fx@zjIZ4um4!gEHU-FIES1lzcUV665A7_o$L&zQojSCM}>UZ<AdQQM~<3V>4dm0NQkGj{mi5-(lFR<W?MGa1b`Xto|"
    "aKe&68+uYB*8H^{&UYf%rJ%2;c0!@CvrIKZK;7-KdX8R;eOW@9k6ZVGI_5fqXS{(sMZpxyDUW}2})r|A214jBzl+K4-Kq~z1"
    "th@Gd({X(VI@$2o3{GepZUd_lFk9)5BwBSkeU$t^=Ar-`S=w~lJ?5sb|snA~00lH@Nnxar=!=Jc&glMaNcTM?_xHQ%^vCD8d"
    "8j;x#gdR%gly;iU#xbY4Zp>Edu#`4xtzBj3XcT$<cP$di&U5pzfI@`#<rzv`yq-K;jm-w$lTqpV+n_0et<!DaFj7!Pc4s$XO"
    "F_Koc$V8y)Y4Ekgc*yCt8KgnDUr_7ZxXXo&poWD<wL|5jTpKBuc$x!%EtC0E}xzQbkJKb`}*Q)J5Ri^U;jlh)IcM@ajxHszT"
    "BOS^gUBsyeK*K6HRJX(&hSm4TmBP{(i&Zt@~hl_Pen>@`MF5yhm=EiPh>ci8+rFgd7g}S(HoRg;G*~+aR437j^1Vipde<|EH"
    "YJhCQTP|G(QJaLM>>k_$<>(ecC2FBubxd_qg6+4sJ=T<Z`}wc~{7zRVMau?*~N@VY0^*yCwiex53d6!$qO(~AGj#OK!_s@9c"
    "4I6=VE5JefSGwbGw<-d@LMcv+;k68k)7Wx*&E)GU|vE-=?QQ}cgwy9rcKPQTWx~H|w>oCGZ8qz<voR^8<s`&PpS*rnEpRCeu"
    "Y$nzyl3=%2qBTlVtbt?hkEyr!U3h&#IQOq_e2_MUAKzKP(GtO}mPPT|Vq&(oi#We6eMzo3&0TF@==~`Xbe=PAV{Q@9)Vf`rc"
    "1jgiU(>v#u?QNm9|S4-BQZ}sRTBvF0D1q$-Tm(7qE7o@N7OgHeV7UOHDbYTv@jRm?%cR_SwEv$4O`<@UD1W}6=Mzc&z2~L+-"
    "%~^OcwG<4rqBq<RkxWXrc1_(hXQY=dt?oDNi5kc#TMVe$ZRc!M;08FkckrX_Y`4`*U}mBGC*Q-T(tF{21JO0ieVZbIHH`m6%"
    "iXUSq^_!_kjq%)L$u8>9bAfUxBk#Lb!$lxxwc761Df{}+t%yN!^2<u@XvvOHIkKJN~POf%Th;t{}IFK7E!Wcl@1FLu=L*U;("
    "V&VUuL$GZe~Sc~{X7*0s!I%q23mC2o66^RMUan%ti{%1|GG)Pg$*U`ES!Naf;SEP9iZS}Wr9r*Y2o`6_K#+8SWvpO2n7wjnG"
    "p)9AdBWaD`vuD{5LuX8UqL4#LlaHYwKK)Wbgnq2X2;p&=>MFp>Glsh<E92Imhnv&?F1<aP=ldn(((l9Qr(f>vZSPMO?@p@f="
    "5J@j)h>I$Y^;V4K@k2tB8v!tTtg}bR2#mdg~T}GsE>^2Z!=%@@G&tk;+G21izSToKI+ESe+(F)I5@Wm)o_ifv1+a_hH~9T<T"
    "ehh_nBR=%%Ck}-`a|5666*3JPV}Mq<rYF##1b;SiPyc%vTDURl6pys~Ho{G1AA=?%VQ=OE_*@!s^aqI#8c?-n!KxHa1_tMwA"
    "G<S<q6mO@|1&A7J>ac`N6dRp6VDs_vN63x)VIAv`=hc)iS;%g>_H=SVoSn{e$|u6Tn27v;rYG_p9%Lu(;ZI$ybMFfQ+gQnB|"
    "hj?egFHA50bABd8^k2@HIRAgLM_>)_cIpGh+U<CF$HSUxQ;bpsew&Av?2972E_uYPdEhdkE&6~$Wg6J~6-@n;IWaPoAOmQ05"
    "_yqoJpa4`lK$Q~j-a<moF7Rx$dr=-pRwQN_C0b7>e)4JC|8&W5HZACzvuWcuRME$EZWr??i&|F_&5w8YaYTQcxp>>5)e8!=8"
    "ZY?1%F5vF8wDv#>~fJBzG=Q2fprw3La{GqMrpcq)efvPw%Sueipw1?^Yb_A!b>wU8=tl8T2f@%?gWXehAdO{XV%E$b8^~!Hd"
    "tmf{d=h6FdJ8G)J*{AU-#e(px24eiinHpY1NbC<Kl;h54k1iVP<%W%7{9V+r%nLS;EsxiI;zJ1e0r@PJqXWfcEdhV{YqFYO{"
    "s#4DjDsQe`T&v(OMRhWEpQMUmFv75MBY;w6vxos49db*iyX0T|}GZ}a~dCJDs5SnC4nYkFv@e)jO5kQpw^`UB4^pPa@crV>1"
    "(Jo(ZmwYV~i9K3$atJs8zl_sMa^aY7JZqC<$<*5=Y_|<?ua!?CeU7x~3O{sJ&uiTOc1df%}$q1JZTK(J)@enJnu+@#cwnFxS"
    "lZz^Z`@6f@e?L0lr%nIMDrSeh8-2$@2~$ahj`3t+TNjS<4T5BaD6Y)zacl}ac-z*@htS=TODZw4G4KR)-RxgA@tVmNR+CqPj"
    "RrFl2!DbjLI;7e@f9WBO?`c)8&EC<u*a#QE9>>cEkcBsKHCH0vTj(&X~tZ5{f9Hg!x+m1r^PrZ?@jrV7yYhjaz!e4zP(U--z"
    "?B$iff9%D7+zL%<4n@LL`dPbJb$Ye<6bjWH00|DayoHtlE~LA^2-@xMGxNdK^)15%|KWyy@9|R{lyRA)`uT^dQ=aJ@*vV0y~"
    "8y5v$*uC?(8`W*0jhSnfniN}XKl9JS9cLObwjgrp+W_w5I#GjP@1PtN9tpV5Mmtj<>#ry-A^I=1#Jsa#Kh3x~9$qoXWgfVv_"
    "F-z!+8JvC{8vKD!!mVmDp8V1mUzB!9m2!)Zk9Yw`hLESn+2|BO9We&?%Iq>FJf&t|FCG`))pC(S+gE`#5=eM>Sot|rc(W99A"
    "<IzP3qF!U6qkIN93l%cHJy%}ckykUZqBOQzA&7<6X6oto;9XB(dib?j;SBAn1Nz(QqJ2(g(*Z*}ZsTLDet^%fzNy5;D&52*q"
    "(2*;-Vr7F{$~w@|4&f4uLDS<KS{5!sN^gw7`9401IdTa%J2LI_-KG}-E<*EC}=|Ac=g#7>#y58&|y5a*}%umx#f6Ek~Q^(3<"
    "A+<!IT-|DymT(2EW;aaJeCrA6^w-9U!jfw3-tQ11b88;ha{67qC$(*IDuxhs)oqvHS<F-76;}q_<MO{+eJ2rU|h`-Hpg#po5"
    "D{D)FK9bla)$j2!<610R;jKV`YG`m4q_{9GO%2J_FmfZAWb0`~oO4m>qn5Ht@ZC=kU8ZL4Fws{Xaac|YK-h}LQ5au=UQk}Hs"
    "@NHl4ymBsdUR(iL*n^;kv=hJ9mEqd9FeiV+UI?p!2034J0i0~`zKxZP|mz<KW(+KAM^oo?}%8`j)`MQY<{y$;$uhrRXw}?i}"
    "(yG}%()yt8^%7!#filvR-WE1Gruv|J(fD0Nz0u%ZY7jD*{&(8?v}*4>dpje>zk}Y)P2c*JIsG)S@Ako>eXB~p>HFUm>-?G?I"
    "6r^CisG91tZdSg$AZEcO{G{tLQw{rGcK{5!nQpKym26%Zh?n8^EqH^z@uLhSrS%am&{OK>)^$nRtdpjYXojg<g|uPH%#m1;X"
    "fo={0KRiz^W9gARj$d#>5}iiIRE}ggx?#i=w0q+o3t+gUcMsh2<al_GxE>oxkdv4{*I2E5He~?(+6uO*R}Jkf$cSWI2|p*-3"
    "uf4$ZqBR4PqQQ7*Sxsun~W<@+>NKR4ua`-wJIC&fon9K{OSmgzF$yWoEx+9(Dq9nAnMhkQ+M?{YAeU4H6ZtTm`P&KB(@Pv%t"
    "0ROgtd%1^?tOD}nxg7csEnj@CbVK=(XJ1YFR4--0A#;QVRYY(PV%Tr#db`|H_A9PzqT%E@M6hZ7W#cloR{OG7)X^F=e0J*>0"
    "LH|tH8{Ymc76<*4`+ZbPgdB}S2$tcF{xt$W?=D|ObGCRltQ{}X)rR+`n>xYmoIC}qA7zQA!o=ZMPIu1f&pCx6-2!k#?8~dLv"
    "?!xL|0P0Imggy&KCkkRAiE)?7-od3!<@59E%=TguBtTRb5Tnh6l<=KAk<R|b~{jFhq#_a|5h9x-e_tk#XgH+izCk%S}s5=I_"
    "Rlz^m@Wv@N9Q3`_sy>SKmA4De<LFzp9)e|JDMC|G<lstD94IC}Ct;OG6X)!L5`e$9q$M=bb>3*(HiTmK^^r*W$9>3B^&W6E4"
    "gHEF<<$|8U9^W{1*XngH4oJg2^yA*y_gaBcqt0z4WwJFGPR2YQ?KeoJ^*cV{P)PgO2q<W4CLy{W9M)bB#E@^J912(tP4G2S?"
    "t%7urYpU`qHJ6rR8|Im-$z!xjgx-}YG%5OQItA(x1)3M4dn2Et};u$^**HMfs1O#ue7U1oovYM@soj*Pe5`~L0EfXYleP^#g"
    "c0lFos=@JDlej88{3x&5BP|2Go4z7--B^7q_DN!I^zqOmovO0^CD|S1U+~@csXT=svGUrkhb-5w7))l3GrLbPp8fY%6KT+`9"
    "tGVTdBY&*muwA=Og=g|Ny{*QkSn6UsVr?jt6JI!h&avBkO<Eq-GxpF5Tj8)c#F)qr+z*%`T-tK4(pHAh(F$*`D_|sy`n!GzW"
    "6S@j#^%R{Ik=pvomXI7dq1uWo3&t9ObHgU5|$kCkcs*anpbHf7g|No4rhy)ajF#dwHXlDZ8u5z;dkq=fL&B=cq8sW_vJVq}^"
    "0Cc#w<_gP`i%^qHmw@SNP~-Ws%BEs>l%+kt@Qn}~!Q>Ct^HFXpDWCnolA-L#l#ou^M~BX~hEv){0|uh2M{%$PvDRuBMVzf@g"
    "F0XdRy=5p~R@G=5M;`S#%+4?@l3u<c{24COz4=3`WsKNLQA0<f);aV>d%!q))Z==LtLrem$Kib)IlcVdwxOS7{r2}BDs2AIx"
    "D=mWH!=(!b|9k9%2EI&#0=?J$;KD5xibZ}GvGkcG5g>e2d3ljFnBxf=bR4DVG=55;eLb!DmCqa`w&RRLG?sRig*qr&k@h$=+"
    "MDj0kK^@W^y|i-!&O;PhHT*gh(23sR*-eK_@DL4_m@vBl;YIgG|AS5p9;j@SsAjBu}r<kdFzdHEspYmiG%-Vvp#H)r}!#Q;f"
    "a6V3eNK*@#fOobBu{r4^_Sj18z#!m<lP4Js$mrt+(}+i(M5gOjZ@#$M<{M{#T3rik4HYXI6}Jy*Hm1=I4KJlm^Zex7Ot=Iaa"
    "s_LV66I^6wUJE1)m_vE%bGo|4Z3p|BaOb+2(}yKNvbQ=N&=CGE=$XicTe4yNbkAls{?;GqF(v-YB}wOkXLpE$wWs#vlF1a~&"
    "4_By~?E;QnoY)#wyI_OJXGx(w_Ihi8{eQ$U6C3a`9Ttv>9T11woj9Lo#wGDYC5N|*rxN6(}u@CSR1qhasfZUCVSFW7aH!*ZZ"
    "+!TRuQ6kfIc&T))5ZGI|#!1-BP%sr|7d^zaWDILf)DK|$1wZ396dDfd^$%hurqYSSbMd5T-N9JE{{2M17nDF278Yh@LaLW7l"
    "?l?wx$M8Pjl+YXj%HsP)FV9WJgpTXy>JGAN#b=sh}~iHdS4h-8E2oO4dv>ujj^D{M5N_3`ld|spcPA7X5ELIQ<6Vjk5QCM!O"
    "~8|&Bh-hq?e*Ceg^hv;j{!DJLED{pDS7a?e8z}@^^A_T2z2EW|B^2iKZurUbHuY1`B-78piBkQQ`OZoP(J3t^^hyMw;UGnYT"
    "5;R@QUFb$Nut!;uzs9vw8v!9S6sN|iv#jeyUiZeO*(-`KHtwq%YdJT49;w`U?^vb#C#t2-KYwI$q$Aj{2ZC@x$1%QOexi=4E"
    "-ie$NrAPU*i`qvex6gdvw*DQ7HFOlR_)po}4c{?tcz^HF!x_$XFtL4<e#HJb>iQP0SD;}vtflqN2F2Nfdp1mODXgwzLvTofc"
    "VcN5EYG>pRbF}Q(v*_~!e@)wWEffs+C83^iGo?miWt-Z~AO+E^4c?D$<wyCr7K2LMAl3e@Qm2UuCY8ZY0BN7%xvL0;h=jwLO"
    "3b(}x}e~mj0r)B`olPy_k1mgoq-8Pop#)3wu8rUmFN6TEbm{qh7A<*0b}Xo#GW2Q1tn0=$AQ~Y|B>Qi7U*$%>C6vYWn|Pti|"
    "A&6k;A!$A)>F=YxvV~JB@gfoG+r(b#~M_-1#OzN3SOyCIa(etk7Uk5<6J{vX;+g!2A;*8=N8H$dv0p5OFsxd|4@cnQ^I{-%<"
    "4rlDD=G>l-!<>5DO;4;G|;W;-yFn0`{3oW^{^?KIha8p1%m!rKVAma^m&GSd0du}y<+pK3O9<ALZ=Qbi=E^8GA5)>lH-*AMr"
    "v+X;;&K4+9pC%RZOZbp|1Ig~bnDU^hY9}vx<BF3nN88ybhGDhbn6;pxOMqQAq;>Z7V5$)_$HK<G}tk!}c*`@-2%hWW}jUPT{"
    "aawlfefwn!f0(IU!jR8SE6szRyS0~lll0{*K8#O;VXK9je?<nF+>IgdRv1+3c`By<xZY#7?gJ;mZ=3S{$Bpc`3}PD&YhB@zH"
    "=_vUkB9}u_8YS5=Y32buz$K@QX5j(t*DJ`t183qio+~K+JRXeBu4*2qh7*q<9tisn>iGO_|j<pqV~wSa(<_d5Lq9b6f?&U#H"
    ";b|IQG81>kj?Rd|ZaFL9O5m`YV-8^NYk-r`kxx*T+>oluMe}Er~Jf<{tgdfBOwsil}W2lWl}J2?!+x`goc5=7<F%1)f=27kx"
    "_ggF+t1rgFweeeX0*luTb6(-4~_IfP}7wYfcwTwxu1-NaO$M<b|=V~SY)Hlls!SXhzXd<cDmHvgki)NpoYuSuIQDUN(Elb`="
    "T8}baJOzJ${&eOp$ntoCwH!9IEx7?_6HHef7`$6o<?BzAR_X{%V4b^?6T42oo(?G^C38cB(4Zu5%l&|WF0HoTVIq5K;47^&x"
    "QgQN-|AngjbHAjqlK|k)AJo~}krl}o$P(kcn`&M))=o&K>m5z%b%&ovl72X*lQ`q&R-7^)%7h<fVZ*c!enzEy!OlC4pm^Ovp"
    "6>Q-Q}_066O;eOsY;*pLRx?kyq2fGzGr*Y*){nh!T~HxX&Q1E8e~w&=5s0xeArA6f}EQEy`~Q+;cS-uTu`0IU;UP#l$)MkMS"
    "*=0v;Fzwdb>5?F{y|iCQ1f1K57GLVhn^<AZqN|JB>5Ppt$T83GSRGE@zthbtYSBbHdMtQC;{$`0xpeV0ClP?ahPsj+=|6CHL"
    "LAUkpzF-t;1V))heDVrm=uB~Px9ZsNxn&wp^yT4i#2*>RW`E;ICB{5N`m-1k$3|7=l-L1~gcmA<DnFlkGxCzk(rli0A;f&B0"
    "7C+8n<W;w1Kp1?Wb%Wkdaz0~yA*dJ=K*r8|f*bCbi?(+)tbHKhgPa){*?eVNM7OO!)6ekN(>z)<IzC9s6Uh@^@_Wtd{=DcDX"
    "C`h>H<)ljZfI9B;#HE!?b>F@BKH_%>*2nE(o)L9I>T}qTv8xA)z^U2R(*~m{UZ9aQKPaF{Eb;9v$T3yQ3Y+FWY-?s$>ePx3m"
    "VtY_>d;_US^*Vio5E7U-@ogk?O&d+f{>cfbMdZ>fve?eitA(Rm^L^0hrhpx_~DrUNZF7U-Bc`>l5cw%xrru7jE!Cgk>-Z$5("
    "y7lK?W~geJHCNy0ejq55s(i;<9TAq(<P)JoI}5I(jcMPUGfVJrW(3Neb}Ezx)~(^v>iAV}qUmkC@X<IaLpYi$ot*wG7{I9-@"
    "3H2E~_P{6vTI!YCaA&|qnazLaZ?xJ|0Vp%lwQ>P{kRcE;)RJ^sz_I9@Xwl!rd?+!|$7?=X6P_wcjPHZ(LmZk%NMJ1D+W)Ud("
    "gL5=Ysnbgr3IIs_*%6h#=k7T6QsWno#J(w!~IGG-E4=`jfv9o553>)oQ@Um#FZ&P}vPM~jiV%f-1Y2U1NbMCoMyB!mM!`YNr"
    "g@@4ru>4TQ$S)_9Tb5h3621D1zBL?7tA^(OCM`|3fINhRkH&!W^ay~0jw^~2YwBW~;*W4OIU!aPK*deXU-*Q|2avRb)fq-A2"
    "WHZ>zK^b30~s3+sqUUjZj8cwt?daKFK&K0Zn0$~c%vb%TX3vbL}Zjwf&~IRUw?+rS#ET;_+7~5XAeFyeeoefdgQ8|K&KCpAz"
    "F_k=056!K0+m-uk0Y*sKBF&$h_MGfg8R1`?|nnG3Yb<{MkwqL-v%tK3qwX3h5(0IIx)1eJbZT`!r)}FuSn;6E~aB@zY2X&dE"
    "$TtpmR|D6p+{nZk2{GiB7m6c59}i$!~H{Tsb1cbKKSmeQPEA`vAGs^z&!1Q}unB1=5g)yMrteZ}(R5s0bpe(K!`GyAx5M~%a"
    "NDl@BHMPdC%!)w}%Glz^J5G$p0&F-<oAa)wCTK}uJuI*fr>~vz#-RD$A{=diN03-CbY6J;~;^{&3Di3w~mB^;FHOfjX0@$f3"
    "+bogF<d>JIqkj=lm?TSD0MmSf#=V-(F1gQ$z?hGfdQ0*xm6fJ_!F<M6I|`VEliSbD&sg3^oOMl2?uQi39CXW>yHwb#uA{Fa9"
    "eV89A9s(!WJH1MvYR)h3v*QGmMq(zAN(Iv4$vLiI=zP1&D~}wzfCZx85*uubX0osU;);{uK0&DXR-vx3;=1r-G&D`LX2KRTB"
    "LtcFfXPQy@g1wLi+=clV$?*9+vG*{k8_ci-UxwMf;cRwm*EG52}s-xu9+H10M<}*`Z9iE`!$#3*nw(xTv2AiKINuVXi!T(VK"
    "4>LG27uIA$hluO}TNMi%4!5DK}de|Est7W=V1(lO>D7@{Z^qxRVj$iv#=8<^rtGF?$ZWwhz}Yu0hb$XtDqIh>_oC>r9oWB&d"
    "5f&uAN7!=%&oQ9ui6M@4plYRE_$rJ7WnTtnAMQ#Ry9mik$dX|$7pMtJx*gD6$(qtRgAvK%ZH(UosIEMa`*PRmetnMRZeBPO-"
    "g>@R(^rjnHWnR9=rRg~o0Z=g0uP=Wq%K_CHK+0UFrHOdW=)Bn&zManIRvJdg^R0)4!egVF=BepLsWP8Z{>y?jgK$c5AJiFCC"
    ">Id{5TOg0QuNbqy=&Ttl(v_0P-_=5pGWTNji{gPJkm=4-P<d6a<Pf4r>o2*DWZ&Yf=|04!}twGA@wKeH0P$#7j;y7&fmUU#L"
    "-n8y}N-TYjuV7`<K^;*MUJ4;Ki?!cZ0xgxgcddsRoLmQ7`|#*H7RkQ~Oga-|ymIXe!0cOh33M90Yvi<!w0{E}=V=ll0G~vRz"
    "0{OrMxuf)@%gT@f%;7$Bd>#0x$Veis}p7agJ4VG-_1TJ9@>TVR_u<lf6=r?#*w$o^yTMR`xYi+@wwnCR`{^U62#w$!Qbo93r"
    "X&hjMki@591uT?s8YrKWZdxDKg)V>1Ag?Ac?*5a2>Hyu3B$bCgaAH;L$RPqWs+wSJozZdufZlR{Ie~X1Q&EI1_I`<~}M4F90"
    "{@rWA#9cw`D;E7^@epQBE<d>D>5s~_<L-ZO5C2j_^7<i4_$sXCG9#Aiiq+_8uwrwj#a>6?vJaZ~FaPAXzl_kfze(1mV1u<2W"
    "pVP+!~MR^L7cwdwDkAaKFB$%-{VHxB1v73Tu+ba!r#A2nSa#P_eZM5)m7^SH@?-{uTyCY%I#4#Cfc6%nRZ5vaPaPHQl~DQKE"
    "Zzw_?aNEgR%;MLTq2|j+-a%GU=>m)f4EHZGauhaTb#~@Gqw{&F*A7rX8k7Nq~vJpvxnh#X)g=p22^Eg|2A0C%Hi{WABf9dN#"
    "~ZxcZIdRd+6Owcu6?_2(A`JLk*UC8#!9ObF$e#A3%Bo8WiyStJXN!QiWR{QQcwy5`-wn{J*g#VJxHG6UZ&W;Px_>i7i<Cf<|"
    "S1#=mfaHOot>2upp;3B6FmDWu6!)nzu#hXjZzYYT1K0M`z5+ix*Ygus_t}eZ8Q)jJ|xAm2m8Eqy7X+Uo}m$ZJa5%%stIy)5Y"
    "9`lZAkKAS$A#X^DJ`#Dx{NvzcTT^<3^Xh^L_(EFzd1dBqSulmTq{M_F3(<g494!T=%plfw%t8MlcINk)o}TYWpW$l4pQVRK6"
    "^}IWGxu)s*Veg^OlyBhd%$MU6nH3<a80RBg>lM7yixRLWF%LL@+T`;d{}iZ%U?e4uwDUzJOFt?d68Yu!d6Z@IT%&zA4SeS9{"
    "vqy2P7>}ToyS)Hy#<%Cv76g8lAjP)=98aG?J2wPhT6s_?{HcygS~$!XQGh|Mq26epL^}o2VF@PRud3Okmyi2j_0v7&Mr44={"
    "hsI8D#<LH6CG>6<2Nd*EBf=Homh4h0rH@z*=|N6kKiaQfb8zdQoK02`MIc9*be`^nz~7}<vZ-J+#L1`C9qQuI#0etK;4=uv{"
    "CiH||}FM^7US9YTz{@=T(_k|EPBpduvJo7tFKG>BUeRGbeep408UyRO$z5x4v|BI|H_7f*$H7F4^+o(GDyXPEWr&nQ!V}$`<"
    ">Nfu6#_lB+?@o7p^_!4F=76MPscVo}OLNQT*Z2gX1Dk)T=XEn*0c_FNBtSgNJPns3TxVMIp3Yx|uaFw!<g0c|=Egswd}~RlD"
    "Yv(U)I7Aow}^I5wq-mb(3eP$J{dt*EmTU$r^GtrREi~t83X{4J%o_}1CC1xk8|4yfv*{xU;Z(>P`#}va=$ORF0bRAw^=xWr;"
    "lL+u<&8}Kc9p$^#IU<R?UWy7U~f@7`hdl-~(5)0yTQ(?%f15)THp=_{mAff}%Oq)j9Lu%I&iettd&XMOu>|hZ#qsbmbWOzWa"
    "qJ=GA(~%J;aBh5D*0DOJ5hLEjQRwnC6k+@+jg7UcLKZJ}3K&B9fM=dsquz>}A*7LCv8Q^$3Ix7nbw+FGa1=L3?(RUwSbiXXL"
    "f=6O@6DD2sa=-gFQ({Ei$w!5jfl|4Q0tgBo#vrIRGMIfCOd!_MHj2h+`t^7#FTAgo*?WJ(e5zDJ67`(sKcl79Rs{SnXmyro3"
    "Ca~&H5k{$-zbl0zZSyRT=ZSU}uRXz34zGNTVOQse)nqLvL^cq<rNVc1SXEpF9-LH#pLmCafYPNUuPiPrG~W&p+9bJlw97C&d"
    "rpn>f~*LR9EP++Py1-io8WF;A*6NFzvPOv3Uj}<_Cp=9iMA0r9_kBD<CU*svgA^WRsc}J)vGF!iYE8a*8hf@5UF5=xI44wXB"
    "-L>Z~IZ8K~Dl_G+__cPtJG=X1V$iK@^*1ZO9<+p?pjcG-Z+nCt0~@<V*aTKRnMYKS8$5zToq=7Tg9RRjpFNbY@tLY8b_`EE^"
    "X}Y3|-zV&k=-3Ei2(#lBvB<{8ewvZVTw;&}RII2cffd@Mn&29jo7L(!V*x`0s-={E4%G7w+A_Ga0BhSOxg$JPwod}*X?5Af7"
    "de`qrs<rpi}iK=+SDx+y9_9s1gouF4L{8%REG!iC9($9H!cV{#5&lw(RtF}yc(Rs?&34H@AMMu=@Nt7?@galt@4L_hQ;h`i&"
    "Wx{@t61VtqjlnE$B$Z>n{OP8jsov@SQx@Q~rrF}z-?P5IN_2wmsZo=q0W=F;qn*_A2Qh3JNN7aJYS@|^T?B<TN|f=ak7t>C!"
    "?hX^%j$~r!trlB(I0l6LciDpYsx&dG}%RxuaxOa3B`nXLWex$e%51HO0=ra>cI17mW9?G34@;5j9ms~7iO;nzMB>o5T_bhNy"
    "FO^$CL%`O7;8<?cxUpj$Pb+TJ@t0kVQw7l%jphHr?gc8@46f+=5&kHdmEr&tsu{dYv7NXsNq;Y$kEN%Di%2$=|-Tf3&367hw"
    "xJlBG+Uw$LCIDUPESw=^7}KevnZ9ao|CWMNCuLdmZ1-0sukVk5GTtN*wNP$X!>P1|X0m%d%T?+Z-$9(1^4R?E79Y@`MbiZG4"
    "3EDg-xB@d{3CU*nZuLVPdUh^Q&F8+hk=vZvkKU({D?Y6(98{KoJ?NxSlrRVt`2>Lyj650>HI5%cw$1teA`pMJtfAIG<6XO%q"
    "DLch2U{iU0i4cl5Sld55v0r*yy!GhY3vwEaHG;(1uT&19Mm|EWMC-wZPn+@^P({lKNal{1M=gC<T~<&Wu0PtPd7Na9K)A{`f"
    "1n8rBH7#ZJTv=W$F>c=lSlWJ#>aPJta}%D)_b68)5-cdMGYRfp@nb33EehtQ&ByL4%&F$SDU|c&hmL2|1WX3ljrb~t<bpF6="
    "&+@!TQceRW;P>d8xc&%e9ml<<ECaO*DXOr08AyWz|ID>=TJ6lqnweYLl1t^^bS#F4z0}Fh?aqj{Y9_Xc3sl-3vL^#C6UcPQ;"
    "5sMuHEFW=TZz7vmAft(K2of*ufv1{LPB8@2x=U^fw2RWV=x{Eps#Vm?mhWIJ_^(`-r{D%1U82t^3UXfHsi;1IdQCbU^1*y-4"
    "siv&&m&6+<n^+_XOO=<)bV>Wk<_|>j<60>+Mw^Stze1o3~m^;yEP>!d4LRKS9o~T{E*F)k+0KL8(PX8OgT&*{UZ)t5+hf1)w"
    "v`GtJB7KFeo*;YmE^+&EoD@=@Wo91CGEnbgt^tmB4oDVzd}arFugjn~p?@yy<eFl6eZQF0S-(#ix_FLH36CRIN}P>KA`pU(P"
    "G4KlJ;Y@xMnJC^XTa3FmSBzTj@3t3BLQ}I<x&tPK-{Ts`#0`)$(({?(5tpaI|Ey17{<wg!P2D9H-Bu*KIpZgTlq<=EvWko`v"
    "NTJ@z?syuK=f#nZ;F&G2O|va;F)F)W>`D`v!l>6%D;-jRbrwyhqdD3vlow{+B)S?0wxoN6Go=nm<R@_c|{-@&=L|<?zJZ@iL"
    "1cL)L>1X10AxAOVJ8aZq0c_yb~{BL~O%8p_yfCxrP>lPMF8WoH(<)4(^u_n={nytu*a+7RGw<~aQwM=`mSob?L4a68u3Vo`R"
    "kWIeZ)f5D5k0RuL<b)U;Fe=0lzi|rbsa8s`CXCDw-3MXF5DhVU_>?NU!W=|L~z34MXDw70TFkGzsAtuE1UpgPxJd$a#a?inE"
    "3+4ol;Z@_EJ>w`wgkGaa<^#78^W^_!zSS5tRF{41jQ_G*Z5H9UQ<_dN|2a`aCKu|7cMj*sg8*pXLL9FwN;W{uuD?Q83`^xKq"
    "7Bmc&4fl^SlgBD1|QgLH7Vz}_bcjns*g1Z)|{l0&OxRtCk@O*u;C`Z#bkiBWwgxN>T&VW!a3F)kMz*U%~p;VCedD!7eySpl9"
    ";pMz46u9XFGz&{{rLWf_yd>o~57P)HgfYc%KtCw&MpA?881cI*lv|fIpv3En6`+S?IVAG9*5m<$1cWo49TY#hh@nXK#eRm2#"
    "=(sNUX>RRTY5{UB|3M4DNZa_Xsltqz?T6HW9GcLkHZ2|u`IO`vL^tIWq>2jJJXke(V~*bavJJ&@iHWUW5H6`0q~iR`5$@;1Z"
    "-H+HVR_RQn0q9jd(TtU!4Gr5amJDZ7X>}}RgAlcZhI%g`~uBhw|g-2FB!dt|D-l*f}!@SB$|9DGMI)nrSu~>`s-k!Nt0+JBj"
    "H!|nAy!ZmsKO7bp*4I8{x%+|Wzq6m-p+1|#>GB6j6wKSrB>P{z>pO0>`Aq9P1$lB`j9-K)UMzdITQB||jBBr3*uLr*;e&df#"
    "9dsW+1jNCfzP6CxTq)h&IPRXd4eCryL--jk<DJ1E=&sa7B?9`s4VUNVw^JOyI2MwT^`$8Y&>qm1^;vO>~?>MkU)r)AJ<OW^s"
    "&Sdz3PV--U|q?DK10OHg^zsF8RAK19(PX^}M+7a{(dd;-f<vJNfnjZpsTBi2e2V&Zz=!uX2SF#=!N;WMt}rITe1;7w9tpYC4"
    "DFgxtp7u9fRHVJpKViFdctxgL>C7(XIQBnxVLv%e_d2l<7GL04wx{XI>V4#WXBmiOn*fok?S=)RUcaYjBX00Xq&wN->i3ib?"
    "t>y*|Zch=%%eXqweo`EWZXT9LOll(WJ_+Laq;|kt87m#v!5>E!JjeRe{#94H2kwwKGWBpD!pe!MQk8G{?+qmH!1@xNYZWiLb"
    "2x$?18=|kuhra51{858e;!9bf^8QIP>(0T~kZXv;Va7g#7}o9x-^R$1Wi>&-jBFT_4~CoU{HI(obVwi3(yM|1v=ATwl4Pe3T"
    "YnjZT=`CY(}lK|)tA~&Pa`}lW+c=<)xuOPeW<?fRwN`{`<h4lEF&kL(uLyuJd|so5Q`9{hvoB3`tNV>PW){QP!2Tp_xy8te-"
    "G%C3_K}{Wu%}v=h?QPEI}Y`7!+ZWTYd5WGb147hS_jEv1XIC0hshSVf$ZuU-{RB8?}!jok}V(LOKRYC^1UmOP9cC5RvX?ut_"
    "Ki5+dCxNR4h7rAU{A)IcQ1s4)hN!K2SV@%z1a&gZ<jU!QY6_jT_3T<5}Gt<&cA-_krZqDXJ==-9En#=>Tr=C6EoCJtiZ;cA4"
    "_GNm#ralmK*#qbv9IWFvRPI}e+VpQpZe({|f@}fl*!DrMCY>S^lx(x()-n|_9NVWZT6{yG(WI%CUZ66!Ds@J$Xyfl3B{mlu6"
    "J<#YZK~-z0_BN3{BUP+=x{z6pz8b7O-2w#Tr@6iW?Jd@S`X?|n1&3Z>B)xVw?j94-?+lf3`W&=vb7H>%t<*pGGkCO}d1l?2&"
    "-4D!?G1z55k&4@j!KXe7SYw@=(}i4O->SF-FJ&fFxwxF5WHggmQCc1UU~-1{5<9cijnTqJvpDN=_4dcE5I%~bG|=so{K(;xh"
    "?fzBpnz~b4fU4oR))ailoo1tr@I+Dbx8u+;M|KR0Gxb3~zIr2rZ%!;dygcm#=dHuMotvC9unFScGMHJFaFb@z%<x6j5nOs@~"
    "snl1E%$h3DV;kq=mL%0$yy`o|ZMa)ni$omDSPyx<V9yz>1cYv8HHZ3$BFiJZr(c6PM3MNIX<q<iBAt10K(M^Sc+?dCbPcOOv"
    "kAfjXgK4^a?r@y<G)MIdP^p4H5oMIh$7OQp@ka^M>+)*X*^{zFBa_)B)&tAc3Th<dC>n-E^aQS6p1qrKF+#2!e`DguUFlJ2+"
    "H*<9{_-`VlSlgB7Lx3e)%1?8xhq~A(=Mg2`gqDK=Q*rw2!P9N}XjqR8-)pN{BoMaBy|8Nbt!)6*^&}3ud|3I2xR7>TlTR>T("
    "y<p0?}~dA75)>Go&D9CX=gnK@a5m0@WGt8+F7YpO4Gkswi_>QadKw)b8*p1%ajC2#KuYX;=fkW5J%HNn=)1WdB?@i<&UjO#%"
    "J4!uq$H4t4U(%rzCT{>I*c{%?9rdz%5WzUYaV=1BdcA^zxl|?3x1ETS27eKACq-+RD{zLN@ufaflm5F|ap8(&v7a^`-t9b^V"
    "g@M~3ISO~#|XN*gGay=heqb||AY^kVb$Lj%ZMDcS0d;}GHe>2lg>X>1%zf;@p^d#lZOLFl&Q70BLR%BPN3DBc8;vI4V|0AAZ"
    "G#%c|^S{L`>n<}_IFfc~>sU({Qhh&W2Xm!Ne2BBxAXYO*HvuxkOKZx0yKUQ(%PTD;`5eVqh8n_PfSS`|)2SS4OKg+|x&C3@`"
    "H-~h)e*-XQPw^ut3Lop+oN=f#cYOqAu(+e~(sH2E1o1!<E4H-Vy_nFF96Jc!RpYfh?MJDJoEq@ZXTIeqreAdY{w#DWvuyVr+"
    "qLQ;0ymz~^7dHEp=$3fdg~iYo)0JN%17~*!%<woFDjV_V!@?v!On&Z-1eFK74NZrr-wXLJNehA0&Usyp;P7_HL>^BB1v==#h"
    "W*Jnk4vUE8521X1RLDC)LI}7=QZtL%i;%GuP7D4W=JZWL4g6BS=%ODEQ92`2~Hkhl9|Ib7^v`KRzo4D(fYmL8{2hxt1LV03N"
    "(jlM~ZaO6dzRywCELuddneyvI~5F0j6@$LLRVSXhjbu+Yr#nS=3)TTgSzVbYz(V&(n1wD^X*4tl34Px}BgEitSUpE*J(&`9="
    "A%Etb@qT2UJ*NGh5<Z=t**<`1$EVm8CdO3-vhLPTEuS=CT1L$G?l{7-qQzSg!bKm;_=H2b=l+E%&_Y29~)Yl+~xk0%|+i*TH"
    "n-hL%>9TS-TqAL}eJh-w;j*#%sLs}NaQ9=ms<E_iW8H6bUA*$y*&42Yy?YiK`!X-iIK$lO{$XOLIK_u~u$q)~smsO5tUtPGe"
    "p-!AMqRuh^f@Du>L>gmBGD%FIHVf;Ow?uqa2VSy*ZybdLZv9_$xG(wLX{}78#Q8rKfcrQ>-t`FqR{#?7#}|j9Y!es{>Lk9IO"
    "WRa&BHhCqG=xGUn|y|^J(N90*vEo^jD`q5f3uwZ6LE3y>!<mmg@%a4C{rv4IYEQG`=SyFDV-Svlti}Wsms+Mc>XMti)k?P|*"
    "x}MX-x>SfLsn!9Z8ksYSDAgXK)MqDr&Z`aCSl;^R_PW535!a#UQZKb6U=q)z}V!R<GM@}pGy$X?THQ744V2(vM?LY(}Oy9S@"
    "!a;Q7s$A(l9?BtSsY(4&gYm6bnA+bYl*V{lG_+MkiNW*UX8hn~Y_Il{+bCRCZm*Oe)K@Q!Gsiw=V5QbT=O6(yz{6!a+58S-2"
    ")R|aSVMf!U?j?zJ5TWUX+cE^FI1YqeXy>MQ{~q{YVaG8{ZRF<WR(o(9U<Lg&mGiY?mA8p_5T`|UcXfcEu&-<GdoviIb`X<h8"
    "jMkPA%(}@p`oFf!p__3>w_-N6XcZtSJ>I$)l?-_t^g-2x?YWt;%)Fk3jVnVTVN_&+Z1hO3$>KW38g6$u_|_^e)u@lV@l+7hn"
    "H?>W#QInj-(miJr}VfJ;GMmn0i{62bJe59oOK`MH|=HC7Msi-KA~jbitY|($&P@Qus2`#I#0KIdv3-tym+DlOx<Lt%s{DzY%"
    "aN8&|)bl**pNJ5{U4To!#d#Zvsk_u5=R0R-B)rz1>hVl<bB1vS1t9q8*ypaK&mNLsdKk~@Z7UFiyUqo%<TptE8<=?<zKvG-_"
    "q%`^Piqo3Q)9~Um(r)BfdAnC|yI7dX7f^iPeI?kFHFvJ%qCT6oG>{}Fo7(VkLJTnJSoN<iPJl@xyONjljSC#YV%&Kp`f?A}C"
    "=f_N;zqx3B%C@mwW>M%@Iio5@`}6_I#IjGA66~VQ(dU(Bo;#7PY+lGTEy`@yE{QO!X6d@0=OO}vqJboyEj64$0yfZuZX0WB>"
    "qQGI?a|zhY*#lIJ|xB&<F!pT9JhA+*^2yu{MmBfL~4y+6_1#DUz~BzuQ}Tl7<vNy;KAxRcB%Nx2@dE(3x*Y_uvy<MS?)&JBA"
    "+D;8{6u$D0(ATPKV<rW>ZvSE-+Y_?_VsCKh>9RBN&SIUcFuKm$0yHJ<7*;;MMxY=RxgcE9={?UtiC>g_ZW3O{wK;Q;j5P>f9"
    "T;0F^Y)I6K+`!MqRI^OI|Ml=6A!4Sz1D6p2}9@5myqnXF+e0GE};Mcp+y8~VQ)LptmuYJSC!#bRC8m(56gQ}w%=WtE?hKB0y"
    "5*qJHmJYszk)jNwj2{j1bDJ0wZn{ny4?8yoo&V=rwi#&nqFIfn4JjUr!(LFit@6T^^_{)|!YNjTea9OhZ-z=9^wVb|;yRHNJ"
    "`4xzgB%Bo_ysmY}XU%MNwUH2gS?0H|^uTLRK&1@-z27mw0dDgZ(omK5f2VAijP{n2k|-A|amw)_C9DM9<RvIw540QI=922m;"
    "jc=MZHKp2{^^6i?Mg~w!@hU*`$l5HMCJMd*`&3Z8eW#n*>`Q@^T}34>%;Jk5u?$tUZ32J-IP@)a~i#ZP9{5hOfz*h?k-Eh=u"
    "tbhQ=u~3++1@D>*5_No2M7$AOJaIs5mueDIMATcUP9cbCY00+b|9R`hl(*-$~vJYD;vn@BI`Ze4nbC&e8-+EK=pBx68Wq=y~"
    "XFDa+S1y9oNZeShOef=*il%e-B^3eN+I$rbIu??i==!W5A82@SNozf~vDl=)HrJ*n^e#mOgvc4*j2mETjY12)@#T7ujIjcIM"
    "0X(8iu&?DmZ?bVJXVlx4bS&WtUq0%|J^8}iy1MaI0AdVfDK(&>>r>K_ZVIa0Z!8ugGZLFU1spJABvu@{Wg)ONfpA65Yz}Hwi"
    "I8(keF>8xi6<8g!wNeE5Po~pBPj7*94`u?~H?V<)fAS+>=PPf{rxLMlxfcq8F_FHU42B#;&LS?$my?{Qkr8UZKauV0y}!9q^"
    "$g@@)f1Jj1r^U09DD_W=ut{w^dC$}DNEjZ1Ry%OB~xVyT(wr=4(i9zn71%8HLh7Az4-$NGA^Ncl$<qm2+hqnUdV5%y_Jp2f`"
    "^=gEtyvLH=^9&9gCTd9AhuXgSyrJ{m|EhEuPciTbk|g?KzV#8uRTV?S8htaVr;0)k9?{3!08U-DdY?cor2E<vLYlw)ZmPjTI"
    "@Fy-4@|rU5-0JCoZzvwIcEX5;Ux>I#o#4qEn+jY@;)@P(i%hx)fMzpr^ys0}N%nopRk*EZ+8#UavHklw=raMQNSyrE#W1k1X"
    "l!?>p_VUJ0AMUQ?fvRQ?qRC`5l%l)?kY>^S}6Kx<fU3J3r_*f%sjuTaM@ANr(&{UZT_E<fMUDI9CjAbg-;*r#o1^7I%7civq"
    "%Ym3ePb-=m)Y;$PX_s8`U28xgvA*ERw3`*<Z4GZb`^}0ju^O>&Xx<cLsTA<L5HDJiX9pFrO~q+&y9bNE_zPh*IBRkjZk}+4?"
    "ASZ4v<K`FaHf;rSZsAZf6<wx1b}NLCw4&}jcRrfM`!i%qU%t5pfKb2HWJeiC6TLooufo&fPAdIT42b3fS8c9RN_Auo#pJ!iD"
    "NR{**FQZmp1wWk_VX~ikUi7C#54he{ZO`@#7}<U-emDWE&)Z+md(3+e)^Fo%n-}OD|EIT0sp_x;tFdFN4E~aLC^Sug%5X8<N"
    "DF>%a8}lyBo&jBzHICgpb@7;B&}2}qyO1;+%{X(mySEa8kf93W%!)K*`Ce0%4*pX1VNz;)fm*N9g^<|>f0`ev*;R0#$3i?b<"
    "FA`tRXA39feQK%VR({$dKw?O;DV5^5deKHMT<Wa|koMzH-#T$}GUfVSfSg!t*-K;PB&*(PV_mle3qz-)`LWAx!ym;gyy7pYw"
    "Yvjb5osQAtY9(wjY}Vt?`IknnWVJ$?-~Se%eiHBW))>%Aqy_JvQ&JLrX1$kLTqr2k@O$Ujunayw!3L9sp9@m9edG9Uj#pLZg"
    "B~?GR=!y1dk{Xk83|iBVQ*H&953NNUg_=lodx30t1fQM6M1Ob#(_oZ)YxFKj_&3!u`z91P2yL@y13I*XZ=i_*9Klo!LuF~>k"
    "+Lx!7Qi@2y1|TWq9)<bR?zsu3u2F4KRB{joQuYF1jy}W&P|e@=U=3hswq-T%JDG-yPj=B3*Qm$)56{KVDDKO6&NUZf$8<OUL"
    "IRVzm1JqfvBVIqEcWX3{KqS__gFRp4r@p7u$Jrz?eYtp{OFL+=t8ZF~V?N4FF)`^GPTo!A!HT;$ajV&|WRuk&%X*WLw1YJ~)"
    "n<;1)Tq`JEou+u-+)U!x2kpm>U@M*T<sA{_Qj=2WqHI-%9M6DF&%Whz3r@o7L&3LF&{rLfBa7VT~#k5P@fG4iH_2%4Q*A+{R"
    "$Ahe=x_JVo%icRihtfg24pM`TXNi(kJ1Rx%7=%gURQW?v;#<@P;F!M3a|ja8NmxP<vU&Sp9^9Nnst;k8GXYYNGo7rbet{A-+"
    "wqnus5_3{l%a1%HZc}S`B?Ns25@msNq|1@Z(lrvxDeWFTYN~3>CEAD4^vXXA%g&l=ETzWY-7ZB*gca9w-J7HMfY(_%T5?oJE"
    "eBt=qdX)DK~9teAwn^wQlGZKIX9Mau+LAd+tSJNMkqiMYkPY)Ew^S*3rB}eSNIQfs7dvw>%QG70hV=4jm$XIp*bA7;TzNPeV"
    ";>U@WZptB{(Ht(8)l9YH{QVT%s_&2s$HzPTKlJmMAQIxHNHtR%T|SuC<Vprt5X7e`(;dd7g|d!#3Eid_Zow8ca_!Qgz~VWHE"
    "^39BN{w#_eD%tvpSZDc)5@>V^y%CZDgU8hYG0}$PBUqf-pk1DBByh%SZu@UIzhsPPchQ-q$RY%BmkLFVKLF>Nc2jqEIZLWm0"
    "&o#&0=S}g1>?;lkB5bsC3>r^1ALs<6U@sFA*-bOa`WDHAC`DOexO=c?!xt(3*29|$!`lrhz(1$Z*Q1%0bMTrKi8t<n@6*J?k"
    "*&Rbk>DSwvp2`4BC*%rWnY2gbH+@LDs*V6KU!5R7*jksgWl?c)X`Z_wJ<t!)*d%J;dkd<_kJgDpiiPMg|uJd@!~1~R`x<>#$"
    "64Kp(}9aAD|Xl?DXL!Y+fpHQ`c=BpoUXNa#KajDh>`j6=CjIv++`Bd6sk&m36!w<bw|_IbN|_X8n3>VW~eHC_E9}rH{vjbSQ"
    "Q&ES<CNgWM9yWY#I!gKY(5Xzul@c+cXEIQay>l4$4P|5kos<<L)t_xgw}I<x6GV0Zbr(oLA$zmZg&BCaSQfi|~;6l1#Jb{q4"
    "c-BFmly615xAXafsw4h0qen<!Vq#~de6u_P7$*o~+wxSN@E*o)xyv@l2`~ZGD51C2boUpiGsDRFOvH?!6QU{wtxt)Qf()m*@"
    "X^XTibb^xJwmykIR&F<_FGbU<FU)*}GQG<wxGml)R9hj^(%@jNmX$!Zf6Vem*KfmFsEJ5HqG;BCOj5bM^5UIkzlr%wLqm|R)"
    "4u*gq4cPplsRIx>7f6fCfJmu>Pqz%yeCo77FHpiUwsZ;b)HzVlylzrK6ZME(%u;sftTP`+3;Dl@uUh*+S_G}ot!i>H%FuR07"
    "ftg7l)H6pOwY_VyRx<5W3||?u<=e^Y9x~?pU_0n@6{K1~-dxURIWcU_J-WyvH0v@Z5;;{A`f(1S2hrbD*v&*Cx}Csriwz>j)"
    "dPp~Nb<&GoC_nDo3LIjSrlDmS*`VTN}3{e+(ABtqHgJF$)OQN|k*=zJ>X$8*hs0#O4{dRan(%;IvB`5~FlYQyWXB5m=u=zp?"
    "+d0{8VS)Rf4*B$LLyKh1HUOb<snR!LCxTu*}e!gNx5zSMD(;k!>e7ThC=rVVI8qp!doVk#0UXVGl@hdDr(ePs_&BXW57TLzc"
    "e1HVL`(Xeo*x4^BxNa4H;;rC(9Eu4Uv{GU-kmdCGrf=ul5hoLFWIGBeJNQAiYc1?JJco`Eajw|<;dcj#(QpnK2+nB3ru`sM%"
    "_8aaq&?vY6tFShqYS{F1saP{-4HQ(tcGE9n;f;xl7Iut0?dmi7b?ToTWPVw>4J{>zwnof>)q>@sRwLIe)1HEEhk=}Z-+#lVJ"
    "R;DXc#ZnMAvQGirC8d$TP8we|9^P?=tExb?b_cf^-Y;>gPM;s?M0M3;Gh_GoyYvgPoru#v!d6a99EkS*DvUGY!J)JW8`7e`a"
    "GU5WNYtyEOR<kf*I-xKlbEl6_49tbbuA23(O{P5fGzfGEbpFE|59xf${`VB0wEpBtczLqEJkU-wh-#~^RW8dN?^p%yRuU8vJ"
    "*oJy->DGqH;rY0yDaqsd_=k@!%@H3|N%`{8r-RVoKjjrQMk@2muY^JIO4M4b5uK%=VBMyq6P8l-BF0Mr(mkZ`iDP*71hO{fT"
    "{xO_5^qR%kw+mInDQc9ELDdSA+};s9>b90K$wQ3?i5U#ughKFktbotN)^!7OYJOBnaeMqxm)er%&h=jVR+CZbvx;V;vPR(Jb"
    "RWnTB!N(9?aQWB`thFKNZMFqAXYeZJD2ZtdIZ>4nVtvP`qkcf_`g`@B@0j%=^vFPA0*D<-E-?(v@a{Y#2W9#tbur?c2Q>UK)"
    "tX$E9IEoqo4WQaG|ecn&ipB)HF2HBJfU~79=R26S9BzK3CxFIOHXpSSZ%f)yr$v)CA05_hWc-w2%5T4L>@^iFxJA0JA^wW<V"
    "u3Io!PAOUjRm1oIZp+~#NOzCXA_r{YSW^sgWgNO@_sZp(3Z#I3#kod165s8a>dulYaXeW<F#)l{Tr*-SmXrAvRgca!B#6=wq"
    "(IyO-ev%CiVlQ}NF|M>OJalx7p2afFIX~TjjgI$VR-bV6aCOQwbgUTMG+5N_NK$1cfY`5IDUq51yZvOA}Tv}eev02*Kc7oXg"
    "@w$nVxKOaKPd72>SEQ*kk>0zKrB88n)8x7r3YUO8lBe>PT(WT@ysUOQO%Cz8PqiWPofeBrOR-BAehYAdTqi(~oNJ9u<<{UXG"
    "Yt7BOpCEg;pk~69ZrwDUi~~OnR*T+N=X$ee+a<$2IdGPP#tdIYF9)(`v+OT_nVRo>%lx`WVW)WLw}QY@?8MxD`!t#_r(@l;{"
    "*twQIf9qdUX9+Nh{~jGm93MC47JL@CnM^xi?9;IWF0)_h>tr%L0msk0ir=7g<&6)(;-T(JZxf6>zjPH}5z###qtjaneiG>Nn"
    "zF{lYCwzi)bGX;~S_06S=N+S$tXDzVralSP(n=Rx!!iT0x-e|&!;ks8FrQI~QhGrE_Z7wz7#-p95;^4(x{7&(vCsT=e7dFG+"
    "oIrJCK9AZm?ON9HKcP}Ca@f&BoggMOZ%H}2*2pR@JFfiMx)EG><-LV1mF;um+4Mj6}g7t5(wulm^{E(v8gNL7L1IH+x&{<5U"
    "zo{lBt%Jl38n#CZc@q_~{?YUogAT(Rec@eQYWYFN#tqQ95T#nEFr$ASyS3KSBO>LO9@gV8M4rdbQ`f-ca*K5MEAx*Z5XxWWC"
    "PHcP1V%-T$oc&UlBgWbyeuG_<+~8bvEO8OtM!qaf&)$B1u04(`blrYJxxwz@J7Ij(p-(T*k&gxy8R%dZ+v@UBf(4{$2*d<WP"
    "vAYFh$6?QF_)P=%haS8(*9{rK*W7{2Ii3#wvAr8G5RGyhe=E#4mmL-~GC8i0Miw82EQcsF?E<%+-VntlwcH3m=xN^hkfcO+^"
    "o?wrqLF*?P13uGI`c__0fw=9a^9uT_QUt&_5)MhEj8=_56%kds%#uYFU-9G#sdiZ|lxXiQg9vfnsn8EK|7i(8Si^uB8qU!tr"
    "(Q)~U@m~QP4@N!k}&|<RgH1`>heCz3BZ*ebnieFM@O@3i;jf;6kYd+qlE0phE<m{<5=;{aW&r_Gjw}bxE0LCr|%eYMc`5n0="
    "x*u=y4&%AD{Hw1>Y&owkum0Nv*g3}1H@+0{ieewdHkrrh9uoa+>e}iYfAx{jU%i^r*eDi9|LkKQ%b{At`;9(mc2+G-EN$4_6"
    "thSeEv2NplXh7hYw~IWLFHDaUNL`TnWC3)M_Kl9S#hy3&_WWrj+?agSy{EXYH9ZoA?yg1?ShO>Sa+vA*d4t69;Y-25y&B<&q"
    "D4jq%8Nxw8Yhxg2Ip<bab9xM@Rhx6?|{_K=>d&SjKaL9_;hc;8Z!|$1d&y^S5oDTv}QzAn#H9{*>=Fos=NyF-Idr(Bx}yr!&"
    "iwbo@cJ^$222g^csdKU%~Je+LBOjM<8BbTLi`0hjd$l$X+st<0=!H<;{wzZ?a`sOI7CH*d(TV}d!F&oOQtu%?z`*q>NL6g~#"
    "!K`EBG(F;B9XifZ8W$26vS3?Y9H3HaI6E=DS!}1fU2uygIL|*c2)Zw8RCp<sK=SQ@Pm~D5CP55SMdu!QJKL`RSD7cdk3YYs^"
    "{PACO^Hp<ma~;DMIgwg<FA`{<4zx$%$9j5_pfY^EGihXC{~MZ^_X~*r9R(Yea#~19YO)lq5@6{w3v%5+{3>2rDJ38y`xBM(Y"
    "=udqYw4>~mOCo+|L6Y?eEr6aj@Froh=`uF3+C$Adg~U^|Jnc9|DQIQev9RCBM~b6+~D6)^SR!$8dbZ<{{bxhZh`"
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
