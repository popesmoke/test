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
    "c-riERaYEc*KKzLjXS}ETX2UE2=4AqV<EV^ySqCCcMS<n<L>V6A-LO@=iHtD@Lts1HTKw5wQG%4Qz}A9K@t^-5D5SPph`=Ls"
    "Q>`5fd38z@V~+DBSR1X2mnZn39Gqh|9L%hGu2LANBrxR#}2F}wyzegjE)`~p*L%gx~nT)w&L=78+l~4lJ_$juPd$8qN>!=PR"
    "U64LCLRY1+116aQU9&w8??Lg}}7k>6akI!2<_#k-P3SvHYFXA43FzJota`KlmT~5B>-Lga5(*5B%uqc~7YSo$fswVcFyQdw+"
    "n`Ew!C&?hpBtc*Z8YNBcQ%zfeY=d|qAS_-~mc2@T-ib@6$as;tbc{tmtgu7tjeK+oH6RBCQ@^CrRe5VEepi_e5>qfSiO4s=m"
    "`a9c1h(}Sa3)!y*CO1#hvdQ7s#{TYCTONZ~vkySF~?-cNo<C@)nHy4CY2ax^Sn6F4lMMVefMZE!GFxDCjg7;D^ANf|r`(9@s"
    "C?JRi7~FaVp#|=_>=A%*7i6|bq4=d~S4C42_BH-aX71XlpQ9V;l=JCc@9B+{Mv5;3e2%@91o5Q-bLGK&M`@<Qe2)5g@MNUQI"
    "HrJK&FKG?!dLCzlO<yjq2dE%Zn0UCB14mz7Eoz2=J_W+sn`=1Rk%~EzPL4#-Xos{>3o)9KoC?Xm|F-(JUj>^0PcWB7omE3HH"
    "lS(5uzO27m83hSg3)l*5JF8aO#)`dpXgajP_0Y#N`o-YAB7{zkrUF&ap^5mT@v64en~jsB%`*#eXgD8^H{tXzGWd5l}`6hJT"
    "OLlwEu;xs&7i=GQVTz_OGvpvl;f$^i-s{I}t&*B)5FXLd%3h^&u!(7y-ZNcKfk+r^ZlFLxzaBEBTU!}gre-$GhXA>3uQNwSD"
    "5x1PuGLuUcP3<|6Z<^?&NY$St(Q*k`H2&nO}<UOonIKg!bP#tOHWP~WtLJDDf6gPxfU%7%_DDVL)rDKGS`d3opl?;IsNH*l8"
    "&Y}eOE^_QW52>w$6>h+iu$vw6!>Q!US0EhHG*~zTq3O1@4e3P~q!uRK)vuBomM)45e$3ZRU1D}JO(ct_3cMcnFOUK6h3VDK!"
    "x62u{i{EP84yoP+LEv;?Ut5`ToRe2d2dK<dY};Odw&Wk{BwIT>~(IDQXZu8twcp$=kQVv;V}XAKD67HdK;adpzEcLJjI*0Z="
    "k?Pl(P`yOagmcB3c9A_}97!B?{{Xex+>`CLfGyGOIY6YB(rgZM*|^apk;L#TWCI2*(3S6}Phs0&-WznoGN)ZhcS4HwbiWVRr"
    "Nt#sRrJ`*%vX=&zu`K1Nq#gH?uWu@UGG7fFHu6HlQ*Q(8WdD?1w{jACINj}O3T8ju(;z7^C$hg8*V_7$qp6<2+x@BAzvk8{("
    "Yh7FfP5rzyZDi($0>b_2>D=SeWd&+_Ty*w3e<>Yf8*j!N|pX*D|DmuxIa_yj2B=Kj{u78b~ivWzY_TT^FcA52iqsO=~#A>l-"
    "`|S$bSqa)>q2U@M4G<YZpDTsj@2=9<*%c6jpBvI?Sk1Mf%rH*&dmdm*23L5w*&@mp@H3V7yzWL-yk3GDls@>UlzA#q{J9Na4"
    "`cEnJ4byRq2EfQCFG6pt;{!|dM*RGy>INPY~-*kJnLF+0ua|aO!74@#L3Bq!9LoJX$bh2IQGo`l`C)~tu8`=-aau{<)hp5w*"
    "g%9UJ1|p>m&C=NIsJx^@Po7>J0t{xM)!^++byFaW5TH3?Y1rtZs?lLDdH6Svkzy@IF=Ne~n8QMZ3n-KaoZH<4CN)Ooe{92l?"
    "pxNsHtEqb4Sy2$jkhz!_`LvB{wQU5IRRTStf&I_agRd@Pk5Af7V7TJM|g<HMVPbq;?>Bl2L~lI8a02~y2wN6Z&1h9i(U+>bW"
    "Ry|Do-k<PY7sV1qv!%sQjmA6ea6Tm=pf8P?m8O;FOYA)2dEvDQI+e8^9>l*@6m{8HvE71CP+`kd4jtG8n(l7@7h8iL5<X^va"
    "qNph<p}}~H>j36*Ag0%EDlqm<hqWbeYD|Cv;wk_3)XT+M<&JcmbFN{fPbijf{y6vQ4rEB6OK{oxyQB_6pByW@?^HeworDA+`"
    "3dRjZLhz-3!48kz&CdAsnZ9`aO#W#%cKX|Q#_+%$mLJUL7uv@Ti1Af^d-zdJ3kL^N&b0hX}N#p0Ibm_!2j1x{grxhxMB-}1!"
    "H1qVLlbKdn6(<^xJqqhjw@caap&=kUjeHWPh~T`7eLb!TWRE*B%8;*W6%Y0erdyO6sme^qn+3#Vtt36QK@8x6Po|`U+H1vv&"
    "72EUt(LCkW7du3rC-cVZY`={I?Vj>HDgf5MP`3RnW#5E=Sff{~MUc{v2*@Zm(X#0Dssw}M{V#gvkzsGzBqov<$xnnToeczYs"
    "auXj`r1}9zjcG3WIy1y{j6+Jbz%CrCp&zDo&fZj5g=jpfir_Z-O&m<7I+up&CSD8B7q?gFN;Z#I>T+W_Cuh{Avz}wdrfrs3m"
    "+rSzXlroR}>KfU}>RUl4qku6T#`~wGquaXrjv&d?%A?c}UuoSX+j$zYYaIBHS+Rg32JV(~@?h_nimpFwSpeLs?#j~1?U32;Q"
    "!<27giLz+1_STc5Z^c(7;9eKoT2F;VXV(8q(hB>SaD3>=Mf@z3kS@SwrbshfJXP`)owxWE6l&8pIk+@a{rJZlJ8;A#5kyMk)"
    "ExihpPC#&vRqFz^7Yr)pH62nIx&=qf=I=M*$&UP%u(AoLT4sh6rBW)JCj6r(BMnrG)$9tI1C3j^0To<oj{PYu>-nKair%h1I"
    "G`pWQyC!S05^JwooXr?=imdH+1#PL`z2pN4aGb=D5RKkZ*!zWHe6!mUVbVFScJ+*n=IE>e3KCV+)3Ddl0CrwXzTk9v(d7W)T"
    "m;Vav|xHtbQp{d7uSu|ifzVL$4AN&Lp9RJElu$!r%)9ycOBH!+Dz^I@wSt%*YG9C{P^z}QVe;eGDTng+@)ycqe{JAA88;ha}"
    "wjHwwL8~2O*@kpIAq{{9V1vH)ltnNi)MIPCjNVp0Y;F6Tp|6*7`>gUWAd;(xbp2gTBZJVtsFbIzX3{|ADkFAP8`DXxOz0J+>"
    "VN}<QeIC9-|1#>=wv?5(xScd6-<VMptL}-t6Cc0ZvhAz*vY*BJ=E*FKr_4i`+ni3p+BdDU4AhgU!PCl(0w)*i@9Oeo_#m1W$"
    "l;l87tk?Nz^dCkDspv2Xh0B>}G^=08>y1AJ!bg)X8n9)cdzUe>xBqW)i0oEbt0S#w3HXRX2TX=;4K@_-moQy|GX_ut5i}H6_"
    "82kKMu_2`G|lS6u#wZ4lVb$rHyjk=uJ2@#)6x3j&dRx+`+tMn_E7`;F?F3pL3fE)7h_qOAbgSR5z+te|ddjO|)xgFd^7T#1&"
    ">fW84sdUYy9z8~GCqj8smr<(PNrAyAfg}+C3bK(yZGjtXp(tIXdS57MuoF8-;C&r8{JPA3fxoLV~BRImZLG{sd49LO7H*K;Q"
    "1{IgNH|Ni9?i|E<v_8+47l$&{e=7I79QW`nn>ulCPC23Eh=64U88Sw7CuzV@@7-U4fBKECnwQ*q^~S|=n*WjoetX^=UmP?)e"
    "?OX3-Tnhi>B&_w=EThBz?3UT1Z;xH+5H}enH)1hF~l-4;&s8|KTMG16QR^>;0dF~&3_yo)s(|j<>Kn#=cSv3(Dcs&fRB=cpc"
    "D)r9S^B8#yYUbCm%Lc7GV-z1`&N-E-4Jsb%mzRd(EhKB(SxKO=#I4x;9=ZYiz1^fhZcemQ@sc=1`b4;tmIY%c*bn7S^EmRb9"
    "KS^!mCs7(rwrTygX12+^u!n0Bv2w6C5wN)>!da2N4|{N$4{5qTQ7^J)sj*#W;`1_EKPO|a96h<Y!}9ex%7OdLcRUX%?07O`a"
    "45Q=@pXkna@^e_30NI2p(0bX?7CB6rLVz#cCUv|RnI1$N)1B1G28oeU@dqL;ZfY&IIvmcK6iDRShQS}D;9`CJbn<=HB$6Apw"
    "u%vJ2^yUQKBi_+06{3<nrhO-^2+RKWR4A$N7B+{lKSiy?2N_w3wJB3!nmAOL<R9WXF|kZZ_-%Ae>RZz*gt^u>MwDlTy2(eM!"
    "ve0YLTO0*>Xb@R9=bB*h?lNBNJWM)A+&Rf6-aN2af(|!ES<r{8rUWt0S&YF*qVg$)`OT|J+2Vm?Qc0g(HX^<NDX6#BIAEflm"
    "@WD@Y{;K^k2fg+!o_u{=LH}g<IhkahsAPBy`@zXmbdE4*L4`7Ia^4z-tW;ZmWR;z**GAy21Qbd8jJKaSR^s>1^h_VHtD-5yR"
    "5ixf#6<$GdTa=1}t0b%}U9(H7s{(C~hI#ev2BjJMU47Ec&+!LKqnDH){JbeC1eeZw1n#Dh0N{Av&VhQbr_$V?t2JVuHpy*)r"
    "s4Madkb;W_-IxIBpQlB4y<|A-_<8%TGErW-qQNt8nLEd4FvC7hnQRqsd7SK5pVTE!J5#*F!zs!7s4HA*S#eI4J%A`D}8Nsev"
    "lEw9@u|jPVOp0ffH~qa%E49vU<BzF;%J957%<+*8hJCXB)!%}N^>MAYb{dq@-gkuqH5Id={mTSn6687)Ka_ckf`EY%$l7fo&"
    "&vS6>%XK9v>y#WLMaE7_7HmiS?mVKYLCY$@P%O46aB=m0k-cVobW9gf4KR+9Le;XRfPx_hJ+mh&Nthl6m$8N>;M_KWUIq2xi"
    "G=RkGZ~xcc;)U{ZGLI^5MI)s{iyc?D`rx9f1<IgJg_se&coMbIOBNlY#y=k|0*C>tXG{b&IjxTn@hk{lrNwsg~BE<Z22#y&~"
    "07B31k%GROv#Zm$JC@J-p&6MAIcA%F(^a&Q6Am%p~$ZBKwco&E$65AayRv3}bpzZh?Ved~z)(t}q_Q4xVyxH)mAXk?BYG;)K"
    "ig?-|cu<4aqax#oDWG=G%jy4fN>pyq)BQ&5m$+A-vgZAi)AQw~|7|E-l+8ry0O(&!0V^2ET_OZ&@b=oPU=2HQZ(m4?Dv4%XD"
    "_;X2&Lj>#t;K0b9-eNcH`{eeYK3GBzB#tAB)JeC;qJ+tCvL4&)t=*UpFK4uQTZnV~$<@MpQoFMU!NhDud0jx>ggZa)cV>moO"
    "Id5%^L#0%b$l8PPuJ=vkhPm@{hYb+RX?7Cw-NCDtni*wDSku&fp__3`XM5|u(zns!Jt$7^Bqz3Q5<F8<*<dGo?cJH@h3U0C?"
    ")#GSDXkUGDdb-kH3RA5dnFyk(N7nmPws=WwQGQAhm>B*{m+};ct|5!aigvzKx}zDK<~`8pXixZFoYmB0`{fnC|y(sIG~dJY#"
    "e1hx~KD>L8!%+o-?q1`y}+MfA=CO}|y2&4Ks!1FKK4mUb{5IEY<O)LY1Z1ur@)Hr;&6#{ny+=v;a?1jOf!7%Ko}9C9?#J&Tf"
    "vj3KZ&H`du9ix{F3;a<(uuQ)U10*Gk^72UOpJZu)lBM+KW=>&O{h&2khx$#%v7lu)-v$K3vz8o0lu3&t7j}(l2O#r!MK2w$B"
    "1D;@c+5zt6L`Gw}xW7bg6sw|<{*PgUVDgy;p~3JU&f$W-Z!KlM@dQCk!}M5=!P`K&Sm%8^FccBs_c|l%ZsAI@+a~by3dbn-b"
    "U<G&zqKaV>gO~f=w=rqj_-^6`2p(M>V^un5FU_^uCC`gAU=<&aiDqX^SI9FLA4Dix(#bqIk31~J3BL{cV-EerUxMZeJWnYrz"
    "=hgB$RgQ{*@sQ(RfBv{pnOdkBqz=_Im!l0%kUd#=~V+$!3qX8iuR)c??f;j{4$b@z4DLfL6uMSAa%JcbeMXywjEtM)js&pO!"
    "r*K(LJSp<%H$uT&yz(=ZacaTeBoK#mwIRP}=1=J$Z)vUUEx@ArkP0Hib+BG4#g!%$|R>-(!hQq)hfLJMCRV+h>kYkS)`gqe>"
    "GcK(wuP7pjK62%{TV}+qp<^0Rxc^hU;N4wiG^@mjzA<Es>oV7-0Is)0=;h@U=xgd@0yK*#-V(!4`brk-jY;XtjKnz{4Sd;qE"
    "lJe)YFT%lGL|f}&=oc)Cx#s7B9Yz2A;s?Oq5QVx|d1pAzX@~A_2S+2I5mq<vC8#dE2ri#)D*hj<iF}<N&ksv-h>p0%yR2L64"
    "nxn|dYkw~587)I+ZY}vA{Qh*klQlW6bgL5T$!5$YY`Lm7C*ufljcGHJWvs0{c-U`Xw#Pm41NBH0|(ke_*rlsbUR(|ZA@R<;N"
    "wxFcA7KvwC}6?+D0#{X>uIQx2OL3QEL8)>}&k1@rj}LP0POK%>pS(zIqO;&U9M-Z~NZGml@a|&9!@*0i*?DGwuiViclY<5c>"
    "35yUN-{LCu^S{I|dBL-$qh3hE+~?;G=*vNcg@{*~A;SJ5Nw(;9+yWnHF%7DB$_9+s?995?#{+K9xA2eElQ|6I1Ai_+FW5^eM"
    "A9yxd97(9x<T$+73o0dsRe0*NEHViGe&iIDM#vd;&cDKKudhGK*t;HJ$oqR|#|B~P>fxl;rz)<mnZa|_dE~~QA)Al<B2O)g|"
    "!sk|2pinF)#pY&6cZV-J>877QgfR!upf=tXX$zmgWlqKR6a>Udc-D!k+8k6X49FO^AkNF}l|(1q32NiHHN_~k`;<Jr77?G9>"
    "Os_6H%8w5Zc2Thw(-{J<kakZLWQft^z%w&{%iLgZb5;Nn$Yu8@t|NbiCxOk^U1k6{}+^^+X;G5m54ebMiVm=B0!fGB(bq1Rl"
    "M2Up>wNxA4i33xu%K;kme<JmwU}UC3z2G(eGO4OJJKZtGib@D0lEw+1z;V=;Eile+*z*J<?!8fZy1?*q}ET<ULjjx=Db(UDz"
    "4GU*B3Sp7*}%4!obeRz7{4tA>Gpo47r<VDV5<qX{fj#qoaK+|&?U>^A!vu|>;2<St2e`X$*YTmr|aV7_nWc-Gy)jF2adba&#"
    "3kNZmPIjBuxP_A`_#oxv(_=VF~nFB4I4O#`W!RLgQc9=HBj3hVYk#lD>538{fw#Ok-@*5yLCuC%jERC#byD{LX>@KPVe%~Vq"
    "Km<4zCCIB&(HL?=pMTq$ICx_n4h&2m-(n>Dn*FvFy4Ld&(WQZsO>RA14clQh>6qv7g|uh{3a+=u!dsL``wO`S3H!$sY*=E6_"
    "?nkgxfmT|^pev%jgbi<!=>ujwAVEUUprl!r%?AWid&V26|{vQfX7)SIKp274`eoXYp-q_2+>b2KbU&u=jojjfTP|V=6&Xiqy"
    "JvJ54(?Rx&-`1*X??`Jo&=<w3KjP^ZTqV8J%9xUCHYNJ%fz($vS0-wCaR(#;)uAjm585Aq5NK_zn~d`jNjwMA>y8G>m{OI8>"
    "~#^QR+$Z);P~T&WM!c#iITdkX?q{D^FPZr*PpqE4j&<4ZtUh7A`9($1h5cYJ+}(++w}D!n*ZzILBE+gd4<Z0`6K$RuUuf1hR"
    "1+e#usIEi&dS!cLK$bP4e0{}29D(>>&89<Y%!rZ=?4~J`h9_+^+AZ(_nRPiQf*CcBsZ{_amIFr|d=qm3jX1sOpV0dU4+Kc8Q"
    ";xY*O|NbWc=LR0A)$97v`ve75aZAk=gy!u=Y3Uvr7`hguFhrEH#(O66{4&oEuZMZNPYbwU>EL<c5~AN+xwOGAbP8`*)DvTk!"
    "v4op-Sv086XOcIb9*>6+2S0dm?Z?(ndE`6W<rMFK>o?L#KyFtzMbq$XM*rB8`Je3gt=Cb2j9?nhjQ4DGrM2uYk44C(l<gb-a"
    "iE)n~JaN=)8}Mn}fd61BR1M&=@+xvDq_N_@}pfzjv0jC%<_${~*Qcpy%oD^GP4jeBJ`SpwS?s(GyFYUu&YlUJS$;RAB?U11x"
    "hCtnn`mSS_iw*C_?%ZaYGeP^4j`D74prpbSn!m*9M}lwP3^<}>v1Em-ATbi4TGoKp_ezZy_}YiKyQ`FwQyl4VJ<5F}iBg_KX"
    ">A5U7c!y?>u^AzQ14F=cd@do^!G!Sa!5n`80Foo+W5F*yjA;cOnjc*V$;M+6G5AdUvu1oEESe^XZosz@E*c<UIXhL%}1`W#K"
    "=g8(*$Px12H1Ne_QB*8kKF!xYFmJ^gheAyWthX`1|H8;<2{XFLO|>#*sR7oH+3?HD!mx+kn5+h2)lY}ETrOLsZ;uEb3+ce@n"
    ";RZ_Jiq1Uob2o#WLkx-o)`WiyT+w8F-kYSf!c%*;orQIP}P4eE4Epx(FRme-DgMNCSm$I>T-qJb*=d*ItrqkOM>J&G~kYPga"
    "xU17sxu1_+50M<a5ABbANhZ+ucH3CTy%)0Xhv)h0@LOd2K*F{yebdu0r!5fba#Z^C|6le`aM$bE5Kj-vO@uF^9AVkN;aF&q@"
    "bN?eDHEzjKw1wxMH5KeJcqP$ncVnvl*x-}m#ucSbK?xZbW&qpq20?yzadF!>q$m0NXJZM6H%yzjdcI_i5x>7!V{yZ%Qxz#pE"
    "#<iR19l`OQ>g7!L%6ab%r(i@F(RW&dXN6N_AW|)x8RWHIzSGW1<0rRhQ?P;ruCicDx7Sc@)`Q9_)8}&tAd8Y#R%ENvLGOr*P"
    "jP<#p-b(L`+-hIJl;5vmF+6Psc6if?A687R1qdCNY~FR9k?)?jNV(8$w0r-(e?ADXmm$opLqvCZS*@#O{fm{dt)W23TqZbVx"
    "@FVIkkdZiL2;aF8a0~<CEI#AQcu5U^Q$Y!X`K7b`I;uz6owxwgLW$&mTa$$BSH$iL@p7FIK*fc_K9fgW{lWCOQ$cQT>9s}-r"
    "AZ-qkX)`I0ky0Z>UBx6bH>?MU*lkehF4QL6h>i>Mpu+wIj(%C-7GXtUr3TPd{XQ*Anj~fo!Jj{F(OQ6Yx3b`t@wyNv{0IjS&"
    "(|%tx!j&V=*#xg!4xJfEBAXz-iYZ-KK^7UtV><OKLP0ShjDe#Gc#>SX`TZW*Xf%ZW#^(EPALM|hsI{`$Fd`u0#X%;W2yb-xR"
    "Cd$>T6WOc9e=9;@WgIa7rp|A@RBmV39f?t~GAlX9K;?ru}3sdND>eDY}?XI`4MGRsFbEiyqByD~(La#jcev*FF@vz}Ef$b_H"
    "9TfZWxI&qwPde2S1%t{O$#e}k38>S_!+>uk!v&%B>DgJmEyX6yzdHgZN%)~1P3qQZ)W33skqEvVWh2CM@XACZKBjheWxfD;b"
    "ACGbdLr57@<mx7bG8X^W(P1iau!U*p)w(xYL`%ojy}Eo0<wQX3L#$@!OHvU9<DEq5H06LzNh_9hOWlQQqq_iNs2$NEw4f6F2"
    "!-$#MR-FQFFYv@XTQo!00VEzMo4u3I<Ir{iVWZi8~6y8e?#A{T^jsc2g7$H5NIc=7hWnwl!x>$5<krG#vEJ+)`U}79IQ9whP"
    "P?EZaNf*t`pbqN1i5ZEfbJpA!qjbdjn(0(cR~CtZR%bEAGB#-pmF=OY2;4=5Kq{fG!rLC6myRjgHwSse!UHa`}T9!Q$J_41t"
    "3m2)-TeK0)J`TQXM5cs^p68{-1zMZ$)-xe30_g{TdT1gaX6K@4J1Ex<y*ra-;sE@edUlG;dl;IkC@5zbQPdx3n3jgHqY>(;y"
    "s4n81l+|zu9nphc>9^9Jn~+!xBKfZDSTOUuWTc79bc}e-f3!ldu%G?zpS@w|#e@91n)duQQM!F-f-<KF2(aDLHGA;3_q)jhg"
    "&2FN9?)Od$OKiDDKHT0iIe=nSP`fRAK+xtC?kybGKiDFw%_x!s*|e02h93CN&RqZ>r2qmdlCy>p^8uDQ6xwf0m{2VcZAqiw_"
    "3pts+oGOysIRGS+t5f`zBH5_fD`mxv{|?hPy_QacCr|&iGaEkwo*nQ;x~Fg&-?{O!6m(;L}Qm=GkSD!O)vCvdRB`?SBU^vqn"
    "tMpvmazLwZ9RzZ)juER$V3s(ZwbI*X>GIlgYCp*9#qdNn7+DxULg*ps`CqI7lGlW^?Xw0oVREyx^mEwISL+6PGtE!Iwi*Kgt"
    "wuh6lPgt|K%;}{6|f+EVCWz4roalc+DM(TaboS7t*A^Y@eY~}oX@a_@ltB&rmFIuYMuClz?>Yeg|w{Os3R~T{cM!5j@0y2*p"
    "2~KfoYJ19kN<Z-_Bh-VjJ0|MCU<<(s<DzR~b@+oS=|b!yAffct?&UPfc@qw6N>c$~nPoRW2ZbZoGrUnDp%tvY$&ih+)Yy9x5"
    "Nl}7!p$5Ty3(uEer22=)vM6`7NAfXB;uv(L!qVv_NHzl^uQzOgex;KZh>r6QW;V~tGoIn#m7{>4-UlR2TAE)nurC6Q^ave_-"
    "Kk%2eg;z{pv66w(HqXBf};PqzF>)4}42}IoFhQ82(;gyYHnQ%HwpC_)4EdcCNY+{8G#Lw)h>Ctc^q~k)T}Eh5YCvLm{3-{*B"
    "y%O3>m5U#x`R5#OXzHEwv~z}Is?a)a#<n<*wNxcFggsiMDN=;rVm5dk@^_~}|orQ#zP0VXQoh72BDT@<iOtFT@CnAF_X5J_}"
    "@ZZulVXC~JU+Of>}@s2_c$yG}YzGC!de{`;lfaC~7L~&gEvdifldG25bex0QwtZToJZkvItQ!dMkAwWtui!Q*VkT=%zcmU|b"
    "F1_8&Dj_~<_sY<Cl%$8cF!3_NVQzf&LFy9lLfbx}H<JmYlAlHr$w4KFoMRX@>=U*wA`DxZ8wR{i6|BnDeITsDMe}=kA+)u#k"
    ">SQ~sb6xYMg<{0f@mt<-kxNip1*^lMhD||_h-M)j|(2(Vpc}4X$DgwrgM^$6}}K-F$k=6W>$4?N`?4#{d~U|#mo}eHymufN4"
    "e-W)IY1i2D!wW_X-6`vPC3LqO|CPc3BnTKN#RLcmL8z<Fd!Q4G^}?e$xfH+!B>vA?wI5kZtx*vmsf?HjrO6hzU+kpWWB3lIB"
    "B9wboY#^2eqpk#G8wIq?o3<(?<@4++f&+g@OO!}Wc%)zT;~(@sN5#P9ULotBEa@44PlLh2c$%gjUP;%_vl%6jHXOtv6{jOln"
    "&A^anRh2cAV3YchWdAXPvlZJH>N(Br_a$_ru!wd!UPt>23q?Yt4aJ0KP>6=y5VKM<TCVkzh3UNuE4Wi^9T-jWzQBbX}B|Vs0"
    ")`NHUAp#32Pc4wt7Qf$#(PiGiQ2MxvCX=~jhfN1{QcCqJ$<BW>C!dQk)q@59j?9#wh%VsREF<Lm*|m(>gtIHeXJM>*L}n?HY"
    "(HI@@DreLBF4kvei1MK3Tz;;QTC7+il+`{7Os)-Ll!Pme_xDa`N3qvo5NgU6U>{oSMS&UPJEHa*88itY<pazy5BX|h$kXpVr"
    "+}_Tmb6V<_i-CT$7yOjo?qZfYMA7U;7i`wG=l!<Qe$Fu|&%oH*88;#TS$(`js<(-t+kO;!Gw*7kz!DbNt$X<}uTkpI}%>cll"
    "UI`>^%brixN>kkC2>je$Q7Vc8EY6B?0dh6J{GbW7jb=P0%JwMD}oC^+_iTfi+5TY)S%twjBBYNLXs+DZbQ*QLGqi)}W3U(v|"
    "gJyQhm+YFRW&Rn{AU2oqyU>RyihZ0uLX#!0@0!E5qPgT}%zdw*gZ#(nr#meaw^_y~{BoHLHJZD@s3G02_yPpjhkr%I?8wM{e"
    "pBY=Z!MClWd1{}mm#O3amEYNubw+i;>Q;MCooc&-zexJyQ{1WmJ9OLX)kJ)@McR5q>br%;goL)noqT{k3sg{7cJ$JM+rC=X;"
    "n5iKan%2A9i;-*>N5(~s0_HI>Ymw4rok+V^KD-ik;MUXE49?b9wwHfvxh2<>2iJE6M*;r67bR{h6VR_uCM4*mJAZcp^$x5WE"
    "lp?uMK_6RX;}Z%cB8FlpsA|#&6&&C4OCzxr8%|&cr9AiMy{Ebtvm{QjdNxkw^p-%OTY{u6yw=@pij*p;NK_(IQ%{fyV69K0N"
    "%@XG8~AAS{&+AVi+X9T-?2HzIoYVviQYXM|2yytmX#x4XPCPDIO79J@{77n$R<#CoSrB6r~qm4+xT9Un>vc#ALO@y<-1-*Wc"
    "b76v>Q_r5<ae{WtmH~xsL7>cSI%&+_Z+9Sz7DPNSm7q185{W8amm1k)B@9p#$`_CSLN5YB3&!LVnXI}QoiU+BBYV2Wi9AiU}"
    "^A$+DFhH22d$%ggul4HF-#@li#S&D;4b+7^0CMOtt7A;N5E0rnO^@y&^VZc4h{kX#8CoMaW$;!qG;}R<CBXhy-V^$omZpgQJ"
    "W@;uc@32Rw#zJ>t?bm+0ewG>j=Gi(5Ya`EV0e34X(ALNzO9^ukq4PmFKQ;LrYxmNB_gi#%h>bS!>J(l7Gf|<D-B?3xVcUZb6"
    "BH;m;Sic&mSBAUKDqWFNo6%YW-=8Sr&NDx1|XQqW7=0h7Y}etgb?rd$p5S18np|4E6^t6%!{{_}G-*LtQvcT=Ww`C9TPQm9Z"
    "ZgeMUqQK@@dq<LwV$ICn5i9AJ{hX-agM<oei35=%&E&sfF2L}SX@Lz3+&&L%m6Jwijvn)kRJ?tTT>VJG;Z$GlY0gKykY%;wX"
    "j1kp5Nb3DBuzs3Jt+wigmUTj_NV~cnl1j1tjW<W}`$uA~jUs(`dHypx$I!lRHV@Mvs0bR3ulN8`d*IR?a+P*9$iz#y@Nbtif"
    "bj`K+$A5RztMWD&>oz8)_N{lu>f&{hSWGqij+d0F$Ba4pJv#fk0P4`0zf0Sxb{hHC`&+qxm+58()WO>$V|sb7S+mod!&KE{j"
    "B3m{{*NlM>@mqF|G3vnBafv*yE^Sj>?TQj#Y*GKXUK<4v5znY$*+7neD2Ks{@54NaO4%cEmEXK7Q?wl3wIG1t|vb{T>5z59U"
    "<}s2oC~vLweaKKV4<#+QsM`kaE{y^t(G;@-nlGnJ}`jQL0}Upa+Z@;##!hKZ^tPQqPHsdH5o$YX%mDHOUq$p%D4as@gg}hD7"
    "_*=L>YOxnhSZDSm9MJGQ19t?l`|yC7m8^%h=A%gFETmvFje*2vX1`e1MIML5JB4H)IdVkG~R92<T;NUvvYRHu{H#<B#dLglN"
    "EG;uWSees9V2S@xVuj4lZD1@YJi<E0J;gi*iA&6^vMHXdFFpCOq$Ed6A5(%j8ncTa&pH7G_GS)Q6%E29Q?5djrnla0d`=k;L"
    "_apCwbtn`Gxcm_2GV1S+5<VC#CpP31oCu(!S432{QafLy^}JJz;gza}#TS@(`5D3Iu%!#S`v{>tNztj^hUl)aXYXaSClppmv"
    "L202&X`l6ir(~KET-jcy{@`lm`;h)hS#4WRizj^AZ8{d9EN^|;rYvn=)dcrI{2)gnJe7f7-I(HbhIN}O~tJWc(B7+(V><S9;"
    "AJGd7{XJ_w0lRixdB#MC>iMXm5ML_w#zCC+RgrMT?7F`p!(g2}`oJm+@_*XFM5-i2QPH*BLV_9PC;eCKjD#+N%0jexOKaH>T"
    "vy)rA5l367%9m`WWAPPp4CkuEZmU!Nk&BOY|j-05BY?O@`e-2t?0p=li0)BX-xkba;F(5h5f8(YS&&EX4LRLmU^J7%TXP2&5"
    "=*&s5`6%(zGWIeCS((RYyxmvkI-%BO*;X+e=&Ipw6*vV44@w`2IGU%h6^gOiY>ErX*X-r(&U|qiF<>n**CQTHdeyIMsn!$yy"
    "6-I$@BU|*Qt1^FnTSso0Z>zY!w)!aa{A<6-mCIr4d*@=ep9k4i+UWS9GgHk6*rrIbQ1xq}N2H2i6(t4)0M!ny5e1b)I1P%zg"
    "o25$wMY_-i9@uQ8c`5%>b%mybQH|Dp-$5-HN|oUb|jGcrlf-uxPmgH>IL$~EF4VHEdC>~NelEIg_`R|(9}reX*MMcDU%ssT@"
    "hbqNIB(U2vJ$ZxC6wFhOJ`ajHp@cO}-J3Zgz$3`=YPfw@wUs&X!X6^TXTZtem26RVRJFcq*SYM+M{Kp~oBGDJvVZORFi<9Aw"
    "4tYOr8fNMVg&!ufa6DIdWrgy&X?pE*>)<G!D}z57?be$9OlSWA#?#k!K;>Xy&7zy<QaZ*As&4S_J_^f<HhH(Mio+s!L(-JY|"
    "Q|3<&>C3ueoXb6bvffdiKq|&15)K4q?E_)M%;ZYg!bNOGcA>9i4^1FVUn0t%UOD_{6D;CVYw~YKkdG_i`m@kiSH~{NzaZI)G"
    "*@;B8P6`aeIf8|%yf)N+6VRLokH8fFEyxJs!!*8$ee^5_omDyIn_7`YDBFF%Xs;%{cXn!vWAza+Vj13IX!?;*QF*f}`;GMES"
    "sDJ}iYuOW)QlaWPWM3T*!j}k>LbJID*fpu;myxUK_bKpcuGef#2HJEW-456@l(alWNFF~;Jce;EFJvGuYeUhp_<=D>eN%Lz!"
    "Du3-me@XEtd{*JelcogmuS4`_TFq%$Wc%QerR`jL0SB633US*gTnfCCv-;ySF$(;0c=!b+W`Daw>f6;kJon?BtITAvFf}K#d"
    "pjB7p&&K8I+7R1>9Sx&nZYR*o#Q)woXT_DSJ$^W7HtLL^F7-3snhic3T!;3}F;zsX4fz-#8;)$UHfGB#mE;S~N1Bc@F%&xY*"
    "+_Q?D}5MoY)`VmogM01}-wU(&xOyH`eHugOR_VEGs&HbI^?O;W{3giOv&zs-N2!-eMI6yTy0A|-i-*0vp++Dm0FKyvb)5@iz"
    "Q=|bY7IQ|3fbyyE*`Gra#X3~gfR<4<R%#U!Rs@khQcaeYNDLman~=6ptJBe?dUEa&JqFG(ilpz-CoJkqttWyoTQg%g8!Zp)x"
    "Vzv1&rdxDq)bC4Rq?_nD@jZNeukFAP5AaDmg!-bx8tl*6%z9w|1^G02Vk6_8r%*gJbRzN9fj7Gy$ZbG-=Fxhpr%-MdZYG@O="
    "=1J<{;V`e&SnjYjgiuAJ8O>{xO`Pts9^a#4IRhS(}*`Gj!Jy@Zu{t`0ZytFY#R0g|fO3N)W7uIuO(GC#G=&=I+`I7Vf|R>!P"
    "IzKZ?ICWE`%rK!{=%e-2|R4zaR>#+f1{J#6?iQW09V)}=tBJ_~a8>_$*5b-Tj?6dokrn)HJxWsLLuajE^kPLM}peO#tHNzx}"
    "cH)m>1RI~k^5Q>}C0ko~D-g@;ycaB*W4yd*a-lD&E*&|Q_i>q(3B);RBm0ng}<2mq$$2&in7ZcF*AaE<rPc$;`Bu^;9VeXgw"
    "3X4F3X4(GHMdv)W3gC}bR#2>1eSg1Xd5<R24wbCw6U`Of`|OVhxY8>F#KO3HSR%b|&+|;LZFFnp7HZ>$_Z#U9$fyep@~Oze1"
    "P8(NR#Z%ccdAl#5~2)cA4_0&PziUXY@sjKZWo53*Xfz+<Rq{l;{0;&OrRWN+$!2(fjAB9Xf*~vAg#e6yxmnc`Ao5YI&hRzE1"
    "cTY9AqhhD(l~TmV~~tnO91VpWVKpqXPRwAU>bz3p+>btGQ2-A}z3nHI$8898Fz2=BK^65kg;|8;+CgsMBU@^Z3fwh|)E%!zo"
    "eg7M=z8H#P=(V_d3i-0JjA3Fk&1vwF<MHzD`JZ}j6!zK$gwa79lDLkU~+pS+|i*pSDl<g?SWp%KU0#7V9JbTfUzzh*C`0R*2"
    "3f~Drdpk$c)kyS{>oOFnE1b75$DZUop5Ghc(_Z}E#<bqIJ{;Gf4cu-8zpC|WI0+P8mY72hO|9U|ExKFC}@ts@Da*r1^UdOyg"
    "d(7fmX+;_I2bR1>z#}^D??$(ywiE**AFlgW8mCCCX`;5;x0!Q68-E_foSxG`MMGTNX<NK;PSI5@D!xZi3D3XO0jFY@Q;VW<#"
    "{KAh5<~Mmz2s8Hx2D4)mGl#DT14;r1M2Nvt)b7~BC^&>6AodSvG!Wx6UO1evaAp5%gF8~Mu?Yp%qz<PCd#X+1cN=#H>aj};v"
    "xg{lkR|wX1~!GWf&rg&qP)xv!LH@+?R)0JQq~5^F%_4fSnyiqE4IG6mrREY~Wfj42{f|X=A{mVqQ10?4ZkrBg1&pV3#)UPiM"
    "WX8_mNM^33yy4VF1U#)n$l@<R?QySFr2K;KWrKsLm7)2b}Ls<<jK9VVtPd|vuR55_%VBB(EV#NFJ+WRdkLW=lt|7w%TralaP"
    "o7mkf&iQlN9cutcdD=^+rh+nnS`pdE=dM{>Dcj{$?|I*{A1(BhHql7M;+2D$K2>C!#$rDVl1^7k<*5ijXpoN7qk;;|M=`($P"
    "1Rw*SEWnpooSrB36YLu==loHZ=gpQu8`S)wcG!$9fmj*!0d{HQvWrF9Fz5$*2vxP??$mFfXFxzkHgwk(k94giL@`y96H%#_X"
    "J(~gnCio45w!P2!`voldA&os!wC*<4~7$s*q70!t4)k~Ih%{eIqq>hdnJbY5fo*dAIW=lH&3!MWC&9{)D656D<r++Ir=Yonu"
    "5LKjQy4vI}y>L6#qUzcs>tiUU0L?!dABY#kqk8!8J2fPCGwGHqP8&Jmn72f0|1il)N3NLcoLAJ4l7;c?_t-Z1srckDf-%f6X"
    "MS>B~FU8*FNdktr#^l9S;aPH;5H{RK7&!B&-T|K&_vE5k)&OLlTQja%;f8-8|jDjrjA=8z?KG!eE=p^`bI`OkUC!!uve{tK4"
    "m`;VVqc``!u`86^CsXEB_&34_c&dyI29%q(MDA>V-KfX;o(Z}(gMMXfcy19sk3IMvt0ER4Gt>yLZjwUYWQIyvLu}y%!rezAG"
    "_yvq#Mt}6kb?jxfqR}@ZEa5vZ5$I`g<4A97XyHmidwA$jB~XJHRF_9VD3z5ioL-tqd~pT}k%{d$lmq!nsZ?-^778jO%~=9$N"
    "GlnhL^mTxt_%2*C26Cd6N2Dz0Jl#jFzVS6?DEO9C)(tLUD2q?Y{}BmF%<u*q3-Se4kSSZA3^i27`gSjxjC;I6;~oEtk*tA_i"
    "m^3Q@49wQI#;p-+;}FKCMts(dW=Ro5m>L##ENty5GvnuOCp;=jeQ*xnr1dOo9V{BR1hdshhRlIj`{!b>mt5iMj<8JREj{<>A"
    "_E(KZxQa9ty4=jDp>d!AvyC%R#sKK-Fh4Jf*I;%%^4inGph^uXQI&^H8yb*9V0)hi&eDhJvs8)AeVN#N$tK|6A6ULFtR*FOB"
    "dpvRmF=?A9(_P&o~hsesXnZlG1UyRh7xbMzcFjBMa*pfOJ80uA2B=RPWm}{V{uNLE}?!RA&EZi?Gri@K*K?2>Yqcz@dgr^Ol"
    "RFl_*v);E|cayUxopVy(Q1X8|ME!&e91maHz~YHpW-oleZjz|lo%<ylw!i*yO&`+V8^dM&4Tej;a{txiRz2%+`uFbgUnbmLX"
    "tN3;XGM_^5wN5HRyHZAnYSxkm19;a614vpO@u&K8`oS5<`k(}q(nOyfipn;5iFG{^QNzPS!v=1IqxFAevWmq04`PDk;(zg`Q"
    "#H(YWUEpfMj<tj-LYLuqr-PKd4*F%F0r9w>mX<ww6Tte^72r#~?D+8{N%(L79}4@3CN?*w$O?fwVt>CKMDXj@&TsJj1DgnnK"
    "^+e`Mo&ghB~mmCLI2R|Hf)*g6X&i0Pf(8q07k&bbn2Tp5dg9L*GGYpsSouVvir+H4K*@{hJRD@fzld?3#V=HHci_xZE+E4us"
    "a43+<nn?pqc85TCQU94(eT#!@ZCB5p-B-VE5ZsuESomx~hqoB$$rs$_j{!uS|s+~PzEtf0>Lbd^#QnvS%(}&*M)8=3G5va7t"
    "F`=TiG19zO9L6;M*b)0$$EfM4JFs2+Zosqy+<50N;oPoj1)mP1<|FCm<n{I5#P0G&!?}(#NLtHf%P8jYm=4jq6m1R;D<9`=2"
    "ygzt$@W?)3|v132WrSMcyy_WsV3Z6eHh9Q7ull`!-IQbx5>xcy;~t9IsdcMIrKamQ2Un%@rLP%9T6b0{#cyYm;b(en2$b69G"
    "w)|X&sD(qczd$UboWQG_EcOCZCv`+<n-i!lfCUPMr2y2llBIEL#^Q|H96pQf<nS!k~~yD-NjUr#GF;C*GWhg}s}29z=P5MK3"
    "dGAD46Sm2y#?OdG*hHGr_Zd^WoVDQiQQu*QE1C4UKyfmIz$wRg0Xpq*XQfz032(FCw<nPW-$q9K|g9;~X%#zsf^eA|ZI`0R$"
    "(n0U8xOyMx&NlAK7F2VrLa8!uEr@0z#k^$!LW{Lw#BAQz{Dcz}K{~Uuo0+iGY*^N0^rW_P#8n%Mq(d#st#+3HOb9u@DWRs|~"
    "0WRYOeThJ3#qsUU&KE4RR{iMGPl+Ht3Yoosy8CJFfc=?$gz~GuPJM!}Qi3<GZ&h;hWaOXEE^rM{3RD<V>0saNd?LvQXAd~PR"
    "tK2T{`@O&ybu*MHIzE|#rZX@K{=CMXcjnF@L!CK(2UCyn>jOKWKr{7W_09&L>6y;o^(kzBTIRZ!DS-isE(HLS9zckvZ-j9B="
    "2ziws2yeVoj7{|3qSuM;9L}cib{TrIdEc-nI@q#5l!-e7j|@jIbzG7ln1t!{gxP@<EaBixx?d!3s+S(V^r`eOR8iGMCB(P#H"
    "l=T?L2PSc0Y#IGAbTemrK8ot_>luUaiOl8pS(<yhwZTm)ntr4^Xm^MkSdWoeT1J|Ob@<WKA7*tt^iGk8|VE~>c~pH5T>Ntu&"
    "iz~`73Q^I4r)N8RZQ2$uNca&eIABpmyIcH4jF#OVOON_GW`4NHu7?LYhxoh)SeCLtygAB61T9yufJY3uaYqzO*2j3boB{Kw<"
    "{dk!5tjFO3B_iugsB!!#?UMnrKb>Q{XUSDAVmm=q6(!7N5F&;3C?D%WPaf&|pdf#9nB<#YzBGr&-+YiiKaVvI1t@6M8G06@z"
    "UJK!y)Z|$Ll%r<-XmjL-XuZ!R{vF$#uCsCPqidC_}T45gt;T{iaG_Kjh#b0RwAB^4(X>HOwFutI9t2V3CaOY$;G7R*WM<53l"
    "M?}Hjg^gh8<DJmttTK|0nJ^fA8b4_RG$gc6K(t<k~qUeh~tEdF&-}b;u}kiYj*!{x{_^%se&0jxcb1B{sySOgo1YepVOj=Cp"
    "WO6Zmn$gw*0gd}$OglkiCzi|l4TPuMVifXO+g*Q_=wERJ;hZUu?Nm5&dt8t=h1YYt%LEKa+r^pVwWTceVG-_Z^4x8O65lS3f"
    "3suQn^HKOdUiPZB)lm=p9@(4f>A{XjUp#+MLrk=3~^GNLccl%!~9P{s*%CL;Xlot-8QU!ffs*~rXCqhI@4ElVdOCGYxCGlay"
    "8?b&<8EMDfjWHgS(p)a@N<LitwXrdp;tq$l4)&KJ1IY!gF9dC?XvPK%>ytU_@wHw~W~k-s;E1x!_o)eI4k4zQrmi8PWV>ulu"
    "`HD7AK5i2D(8SMP>7f1Ts4R1h8ohi$en8ptVOEPZ)bc?BKN8Dt=+IVwGXO3m;7XtANh}lodyvvVf?#?dAr|t&wjHB;2ZM0nD"
    "0?1wu=@0=<;NFwj4i7s(hU6y_G1+ZT;(xO_zaOy=;*|X%G{Y2oM_^vZNMbiJW3X%j4G`@au5E&Z;{i6NQJXOxlzDR<n}aU(="
    "_8zngQNX790$pJ;$CTpIK%iR2hd{$tz$#!#pnv-lZBsU*$Eo6Z@E4+NXFj3!GWHZjAEa+4`5@cAV*-j*1g1%R?%-{mXmL}9&"
    "2>Z7!T@9eg!fxgNMd)!kSZ(cbc*9;80*HZ?UoI_+@id%=Lv-Y0%+_^xFcgXnYE4*K)2Tn^<S+T+R=pubVAS1z9Y5W;xvP0P_"
    "<JZ=wt~3Dt6Uf{y8e((udEXWCPmJ>usIu}x$!R0<f{mt64-s}lH)s#D%BJ_&1U{c9YROyh^uy;bi*?QS1=+&;wfcUz|IJfxR"
    "W-r?{X*2Y%E`QdFD#aPfI(LF;j9?BZuLv}w@qrKF~<34%4N;{V$HN+E&0R2Hko=c`lp>m<LYUVs6VqO_2Y%$iJ5mua`DL9EY"
    "{HqfJivp*$m6?`I7d*-bwuV&EiEeS2O(|Zx+urh5$I|F0&q~U;gfhbGm-v+mX{Vx9O@xj?=iR1o$1XSN`2?*m}s__hk29gJd"
    "CiKANrf5|mk}G6zJ<!6Sf*u%P%+w#2)(nY(^^U6HzNS%g2OxOMhM{z%dY{@jDmXC?W{(M*huZ{y)Ho6w+O-ou-JfJ@{Qt*RN"
    "NaJXatj`$>sX!#Sph5fa%;-;`k>@yy0c_`WyN=tL8<PSHK8g6IqXzx}3Y-@EW<vZFgLP)};4>g~71ZV7Y(zV0@cR$;&YtX$$"
    "s)NZlg5R#cxsDW-%RKUmDEBs#d6GzXvJ-}Z6xVSW`5_=DItNE<lta8Udm|%ECnJ=`4w%(bqcOt10u%&qUAdKW%RsGC7*nhsw"
    "ZlZUE11I5V71%%ruJmqOspU2Xd{pNFPtdyb=v3fWHxLQV)H{Quh_8OAbEavlt^ANLW!eLOg`oC6l?#}xV){AD-(W3q#MSmPd"
    ";8KiyyB<|NN%%;8yp^v5MKQZalQNbp)T~e6(S}hBMpprrsPOv3B0O3b?DAE|)9#nglOpEJU2`Og*g;u;w)-hRbbXs9W(a9C)"
    "UI%<}~EQX0202xHnjj+wFdIrP6s&u&A>qn*l&yyb?+yq#ha75?kj6bTCJ4~0nzVGiG)S~-9+vsB~;M1~4je=5)%st$;BQ=ra"
    "np`|%>^gzLrJ4y&;{Dop6j>35rTZ@C**YDNI`{se|SJg;L0#Q(tXE-PMCU(*QFWW`Z7Nj%P@B**4J($A@8R5x?vlwfZG@r?2"
    "mP+fBEaWmRM*G9dA`!b?Kt1htEjGZ@&*jr#C+1@(ZwlVmBg~L!HE!x9H(~!OM~hUbU;KxYzmRaZQ2yFwF+%YrHXw<stG$zpy"
    "5xQJooj{1;m(ik!va~zPj7fI+g_L{QbJN+syiT>a?!x-b6PC5jb3_Qe?~b0V^dbT4X2@N8#F(x&bfj(elI}d_F5zfKzI`zpw"
    "JM1Ejodhq04+KpK-8LUH(TFV7|3WS<o}5pWSfraM#!nnL5V-g=IAg2BNr*g4zc1NhOc8qL_9s2EY7va552nE-2OyB_Y^*HYK"
    "!Ymo^&^LT0RG8QX2bE_G-Z2r#sQH?gRg<&uDT@u@bXl=h$Yd){5ue6)%qkk39ICP!>2sOZuvT4BaDWJ0K$Ch7Hid%*T?XbTA"
    "&%Ali}<U(N`avF7jwFSa4Q^~)C{q_rSt&JkEfQi5Kuea`z*@G!(_#2b)c_~esh(9LQZ6yy-hFf77+sGTcSU3&l7F#eko(1Gk"
    "^+}?i@5b@inHy5>g7)j<(qYLqot~pISu!wKNFY5Bz4o#cUrM5Siox_7ojX4B@aa5<Ou$q{v`of*tX=g~@{VVxAENU7*aks?<"
    "KE2Qn5)^xBaLj1O6?N|1cncO_%7d5T?z0c_)07=;EqCowu~&hje~KQ_HKB(HA3(T>g+0Kc=Kc6MYbz!R=8a;AZ3Z!)jT&?{?"
    "J)w;5b5BPe-R`xrIPZ#<B8W1Vmvq6Xh(5VVqP_>m>BZwYrkg9qbdOoaB<m2>W5jP^re931D?~Xa3Y{0aS0x{Iw7*_W?nqRs<"
    "P@Qp5$o!XPN(7UDsv|Dda<uigLr+tyHY1sDkUGGWwI!~=LlI}GJgNHpL`$v6nCe^{@q-JZEY$qd4|B$HHK83yai$IeIptw)m"
    "u5cf&lLUc`DJlHrVaZI$<?SQYWPz4+lH*XX_&llMD+kr!Ol%XTR0l~eNP+EY8Z3bL+^V9^)L;sBQ%ltlGytQpX4jQWk3@20k"
    "op;>z{{eeIguies(?P0@SG{!YEmV7t_w53<s>o>LvnBw<)NEix+8kn2Y@Nni*fa+J`0+=$v9_j(0IACKjll*J0pvR{Bb68nj"
    "F-S^kzk&`jFaPSjLRspZbwbb+7g)e`)CIt5~;!u`l^D_fPZ8IHdMsOv0R-OwIV<g0QGrMPt2%$n`?gnd9EY@Y-li${!K}S$z"
    "1a=Ko17t<P<iG9QU`j@czvkSj|$bmA=2fYc0BEsR;n7@vwiH{9M`tYG?CW5g_d~^UVg%&CcQS;sQ=jO(WXvqukv=A}KXVyp_"
    "c;!6wyy4PZ(yftDn|p6h>A`4{C(9sJ9)>fq_%*xKP(O;O*Jnt&E1KyE{%MTtR~qa*D(%>-$yiPb#EA8*{i)r}Qw!KjZ$27|S"
    "IjXi{XJx+?ZjIKKduPz?Pt0zw4SQuf_0f{8O#Jj?I1&paA|A+Ba2>|IHQ*}%!>wy~v|8-kUU)G8^#CE%h$AQKF@$S2LnC060"
    "&uK8^d50hF<hkY;;Eq{?d1vsyzWqxqmJZ{C6q9A46&<9ho+P6=>QNb5a6r2@+%8ptQN4lF=SkpS-7N-A@>ppN7>F!0v`Cu`^"
    "n(DMIKqdw@8G>Vx3wxGY5)m%R(QUWZy~{qsy=@)V7fd#gI}J%h{dD@x3i0+$PnhaRwNtNs&QE(40U=%6k3#7t|n&wnAH%!+K"
    "l<*+nX<m^s=hHjErEar)Jd8s}lfqGEJ&8J@M0s1C{Z|Q`30V*~NqHU3~KJK34MrYk8_ku<c5o%yWSJoS8J@6Cfi3_Ywg!L4d"
    "h1z~zNSyl`wDlR=C|p2H4Ow5)|0WZDuS!H~2FsM@BMFdOIBlxj+VR{#jr)PQ02w6;O>*K5>_R!!5S6(`i^WHPNr)}lDVW?rD"
    "5L_m82yP?Gg_wM6QcW+_~rJi##LUY-1pGdx*%YR(0Gcz((1_tk(y@(eV<}u?eB55(pay9xJPnsyx0Sak*sm3aQQ)C^glVoy)"
    "4-;dOw3g#O2(asNY|3#y*2I6ma})paXcemf*0`4<gdgmLoUD`pFHcS5e|hzFG<LQzBNfr2L?Cj^s;cRim%WOoT(h+a+K4fYe"
    "{2;XiQ!ol0O|9@<jMC9R4-tWmN`tjiS0bYK+K|&7~L?&!(Ipf<H{90?sr9!sd8tjg0kvKzOKW+^j}IavKR*V^~H;LX?_t&H$"
    "@{&(U$(;Y=B6{`@v|%UxI%%zQ{8jCpN6;j~x4T5=@S9Nnn*j(?8#bT%RjChDlt>oq@HX4?4u?PlFK)*GSL{9I{4?&0Zf5cXs"
    "gSo7b@kQM{DcF&68t)WCn0YZW<S%p2=u<XO84ibN4G7lb%BKaWetPvY2E8^LZDrq_kdON@mfnns*r3pFt_`_4U2odEF0e{}-"
    "j=`ou1ZPIch3IJV?swo|6yeTKA_-sTnT_eO+mLpG^NZV~Z>UHr?SFYe*ZyT#(#3^GCdH#_v3H)t!jLWeumH%^NQ~1@T%Q)R0"
    "M{_Vh)a#>Nmg+0hmT47(RF6&Zz4$H~lhFB5n(E1<#g@vL*~oDnpc{o)Z$$XGvyK1XmCy0m0{0{vMhM}FK!~{1&U!Tf{{2fY<"
    "K@XIjCcE(%q3gxjnIbkWvl9?$e7i1>0kn&+JX)LEzi}BnV(~ep>diga|1-p26{z-QpVLt&zdv3DeFZsw!#4K-?@#C9^TW;wF"
    "E;QSS(YTNxpy?7}tVDTU^S65XajMymS5{&P`7v*zO?g^)Xfkh{VO;8suqTUCJf!4>h<iwDK5<TX~v|ymIYG=Bt!)jHlXb>HG"
    "e@GN7J};m-`OfRSpYRT;7z=L4zKh(X$T3%w-9l?V56?e1NyrKyhclSvrT{vv?~D>dY(2S>>;FfwREMg#&=aSNxXCh*GQ5~kw"
    "_Z3GCkH#&n<Q4=wul@Vq-=B#S5(H643mNNZ!JqB$gr13r-dkJR=_{C&U4AJ~l8$Y#1UMCmhO(%x7p{_fw*+kxIW7QS-^PO9G"
    "|G_O$-C)}Q52*wo2beW*k%NxHY?Wg4SKy74=kVsKGiv%5^?GQP;*(J#DGS{NrQIG{aim@s2gUzilngk`4q21XdS2)=ho*osK"
    "DKZMUGb1<H1R03_|Mlq!zWu?SPOtv>1`o|@I)X)SOlENq%Xw@{<mNL5;MINlY<PcJVzpCW%{VSUjJbtz&C9^l>pF(h-6cm({"
    "v*i>}}3!6@VlaRL2IGB+*TpB&XBDp;I{YW%hXzV>b+OePazD-Mfo>{qAtixqQ*_oE-GEkU&G^mlG)Q^1>p1b@>vGB{8tMtux"
    "9Sr9;^r_!-JliI<9?1QYQ6$jxRGS=#rr#p_Dr$Z_u#E#hP0kQ?85d2mOi!M{9Lsy(pCOrRq$izGrfFj(#O@UXXykM7>b@}N5"
    "$-`A;ve^&g-v*r;HRc3)=5-1)3;xjXa0xujphRerKW4_Tq&>H~VE)p3ZC@nc^!s(}Q)a_=vqKIFItUF~sT$gGUwVy`g&sXu<"
    "5Q9NA<J9xA@*L2o_|ddt6zJsf;t>$V=v#|TIP_Z$+}v5mKV7?mJG}w=p}~6YXu3&;$*sw%@;_yOQ{$8P#i_G6)gH%KRv=0<H"
    "N_MaOd!F(Caf|&Cgpm+-$!8OtoU{b0KL8N830*ooEQR1QN=o>&R{o+v7N-Y*6-r~^XbQU;DGy#c?cQ8Oc)^*=K!|=;NQOR65"
    "gI$K)k+%Np(gy2+Kl)d9A33q_Xtmno8$Kn;phTy5MOl1%a=aN(Dw1zbefj8Egrd#H2}-0Ak$KY+yO<<Gnj~ab^9nR7TM=k_6"
    "zmK;nCko6ZLp68taO7=Q7?C0v-EMk~+I%5o%mhA1x)>S0&aUPSIcTn#Gu{?KGh7KlCNil_FrkWHDNvn(T*B*7)g0!attx+$|"
    "jlAxCs!!b;Gqk)~+;P&PkKE8Jsceb}Q*cVlcoJFEFkeM5-`jcl_Z6<^J<V!*yQJ#q+U?Ga};?i-vaO^lHY=E%aRrOg*6a&T%"
    "6#+74)<%+4bI7s*%0kW_=cmhzoS%{a@GWYUM0#YWr)q+_y&&{sYGpkV9Z&A8_WgH^Lnp8Z=caLUYXg6{c>}k1cd%g$wj4N}<"
    "~d($q-{(p{-T<c!pRHA7V+B2)0nd{l3pLJyg*!(>M5g&6W<gz@+$RldieJkCIaNx9KHSE1B=R6M*M2@JOIkbVmr&R9$0KPTl"
    "mkPe2lAu9yaJ_LC8Ls03c*U1uzGLbIm6H<D0+0Tw0*r>0wgj(9#N^o32c&redh1{rz8LPy1Col>n$roks4L3aV62k%&J)j!q"
    "b$+e+~1lLvVB?k%hqPWz;Hos2{)=?(Cl`&hK9fa2wuMg0201xz}Ji84d8Qn7?ZfuN{IC3&g8Y|Nx8=+gmSKKWG%03Ay<bZ*)"
    "+2o%|6CO!XBb&RE*B|uM(%}~Z&Cb+-5h4=2>#+}ZV8vE^3=9Uup)7OGLkE(!{k@11RgfVCo4zo7K<ztI@>BI@lCJjvl1ic>G"
    "($XVi0Y$Y__;H%0%QOKXi8yb#Y4#-m<n)wEtFZ5!9!UU50^7F*1ga{K&w)~WX=EUXHR#0=`ca6jD8fHoyNXX&R%9}Ow&@J4<"
    "+#A-aGFe`QnE;||49IUdGP`+E*?i?kR#j`qrXg#<%YDJ$R0_S3o(1GM<Q3ImUU~(VOyxLn*eZmspo>s({zDMm2v2Ze~cWTQx"
    "o`yTetDvlgD@rRjzQIA!Gz500=n{NQnyIH%q7Ry9*aFvD?MCNZDjuQ(nM|5<oJ}BmJ18)D{1OuC{wE0{anZr>hbGk_b3BO3;"
    "Qe26>50#-G7qCosq-TDafq;N4rdaD8V7J;c~Rs=*XzqCbBw|6=sl5~Dv@ydfi(7LQ{-iqPoy(JBi>68M*y9&37RX|&)IP{xV"
    "^z<Dn*2_&lC{@PtU7$yMrrdrgl7D6P!J{$%`q2_)P_{*&Et`&2?hR$GKEpmK%?;bu~d59et>{^Gdl4F<%saXKrgasO96<Cc="
    ";nJ~VxHLD9pwq*25MWH&Z#q3B#-J$%euFNok@Ht%0Y<Bz`&xAl_|4Skv>i<X<eC24i6N*;sY5tX1q2p_n5ek|sYt1<LBHL?X"
    "UnVj<E@)mFCEs30X8Hl9snD1@{?!YRJJzx6Y2kpvvc_MsgsfvK$1h-R$4H685h2N%;lM1Zt8Kc_4JC0g9(7AS^y3t0EUknJ&"
    "wikU)o&400RSTIfw0LgvS8>)BEq^f%6HgCyaLp*#|$g2|1AA7FpX8fdBB?TX<=526lZ7vq6YpFi;hMx-_fNtVJ$HO(SD$4od"
    "(W4F2nXYlWsNrq<bUxwdDh1_VKbtPojsslip=h_Q_l8@5C*NpN$si$8pR73&yi)>{@jj!JtzI4(x|Wi@Xc!0%pu6&J@R(dhO"
    "uAsewQLsa;A%j!KL$Cma6?`^_{34ppsSZ|jD(pA=#{(-frSpB&AHH^#|msbu$tr&KsuQ*B22`!eh6rbF^i`(mKSaTV=Dj#-q"
    "6er|MRA}}1z-b#|5*ELD@kLymn@8O3BN+_PETC@cQ7PxPIGU*@M}sHt&*9HcJ#USS=o~dobNdnik(|uNx3txd*Wv0`DypJDG"
    "diYr5QXSOF*-?tCwYc{zVaEaZ*OQ-RoZyO!-L7^XO|@lH|~H1BP{?S-nsY!&P`2WW{@K4br3m&Rum%29ZZ(%KB;!-7lugyQJ"
    "5TvI=)K+z^A!@%s5R}^=yD08T*&S_@_I!@&3vaHL<MrMvQj|89`dn2q6_xMcH<e<+f_Nw>U9@b`qgq0?jx?CN9l^)%mkB!bU"
    "i3hV2)b)*O6{lfbHSQPYZyOa~m<unl@$gmHo-H2(YbOEe8o1klafYcn%gc=Ij1d*do@@2qRRHUZqO0XFH{{LFGfsxhTj4sm*"
    "{fnT0~K}Rl)X9cVzsx<I72&-w6e#7s#Oiv%PA^}!irvIm^1BMaB@HP$phsqa!+0ROtW&^v%X<|x}QY(26pFenvo2x5WE^_Vb"
    "*AbS^NwC087$IN4W59?{fT+24${Z8cVB^Y1xHdC~S5Kb8$+0o?I(;O0fyt-=WF<m9x9d@y)fqiZ@EsTt==NHG^m8E$d}2WU&"
    "&z;ds?mb-pR9ASD6Go>d9RBiOL4m0Li^Gsj9t5iE882g-e@8q3E&=63GmFB%8KNFs#FC47HxpPeCbu3XpieC*<iPWmURf^m="
    "Oa@V`Z|jM(An}TQ48=r@l^3@@VeK1p5^M2j4)wBppl|RF_4OY3qvmV&vX9xoEX;cWV<j)>hCB0`v==EW>q&kOT0fAmk7gz#<"
    "If>#xq8$6Lpbqt)qREK8AOC7MB?&go(bxK|PN9A^4=u=20BRe^q8S>1cS^vsQH+QLA`IQfdJ$UH@wY0(cHI*@UJ5z@GcPT=s"
    "#<NJ93{#~p}pjGOG09Iw5F(&H`S=I0V(&RYaK6ehso8t&NT};TxrNX-|OV7Wyt5g9(J&8i_mBMmp5GG%`VN>r3>`N4A)zFFS"
    "zfX|qV-1ko5Lpmm*EwXZ1Ur$zXR9mt<iUNNCEm3L+oe+zz}51*OnWBe`D5A`*E9}oW6&-f7UCGM9y^Yg7LH>|nsat`Fl`-@B"
    "KK1QWLiK~(H~Ns@_wz^uL989ZGF3sv}8Tf&jussd$qm=2B`?&qEO8|rN_DmLv)fRK76u*_wL`rqr9(UYP$wlW#ajnaQKg_bw"
    "(ur3nsv8OG|kD#A&p%9F4rhm;=JBr>&7uXc2}XT$<~CMZ72W)F@w!w4Qt&zIX~ij$B&Tf(V@;z)mB^X0wU^{Mje?cw<e~DGw"
    "Ou5OOF~01$Ej3ADGJ!x$W{+`o%6v(soMA$o&8LfIHe^-~;~#fV7^nMR&l_wnz4z5V~LLm^E99O#Afcli{$JTEH?ojRc3)yR}"
    "~k!wOLyRtb<;IP}>MKspH+h@*VYH9+1ym?d2qfFt%Y1)ZTG&A7O1|kg>$^Y?i43{P+@Yk<gMyuaNGfmMDfn}N^k?9n9fk2%1"
    "b20ha>jai-euJ-(f=Yj7?_U@DMb585LiLPN0|TQT6mqSwKKPeTf<a)>4J-zYMAavfe7d=_qlqUSRatsh<}C*QgnVN*oHH9vf"
    "-vV~L}r?$*t&Ncw;n&j8z;}=m8B(Y?QEkZ>wt5Jq%}ZBt_=-lYpUzjhk%A$rBD26!QMEn^oyKY5&*+#G^+S<I<`&D{<J8yr#"
    "nnybkYIhIL5EfT|~3d#_z9R0rEc9WE~5wTh5vAJE}|?<66$3jS_PRuw*0r^85u{n3_>vnRe;W3Ide<E*d)K)#+Lzi6y_@7#O"
    "*~+&c!v=cs159jbgPz7B`0EUPifvOX0#Tr)-%g}Aly1ot=B)DuaRXM~W$VFG}VLpEMb6S_^8BhFG>Uw(oUmtI8P&(Q01w9=B"
    "O3cv^EdsS0GuGbxEPbUKoZi~KXRG>@%kYs|GG6ib%RL@_B&VII~K_d+GJ<T){^wR<^+r`;r3^T94i4Py#!=G>8)p3Ec;gd!K"
    "_GljQnak3D>3}oMalCc%9A2HD$5^L>R+^$|48q*ON`fjKK>WPZw67i#x<!&rnM!?YS%2*qUg)O3K3b)cC_#RGR7wD#fxofH1"
    "L$Z<aR|=>i(U|5H;(YZy}S7A;XSON)ZkzGEtl(k-nSf*K?w0k+l*8)7aVlxY(E=d>(&iC*xtl%&Y#C13((9<G_BX8iRXtT0Y"
    "pjmMPq2y#CBwYhyO&7wjPoAl$vxd#PCx*Zd^8O$8JOc25E+|IKW^qfGc<L#^Msj##{K88`p4kdjl(ZuI8j%Z;l>QFitA_<0x"
    "g#!OK&#c<0P{9FG$O-L6*sBQZkm_t1<&6j_c)_91zWGRqN%GTajSZ*k{8ta4v<JStMq(Dt$~$OK4yzjxo>Zb@&K-hUa%oWv+"
    "fi#$rSa3dpTH=Um_!@>t4UknofgdD;{mm6_rmgVfj2TySM)LG1gA(EttA|0TgrMdu0m0hWl0DDfizM4|^Uyo+M_b-5Z*=^qz"
    "P*-341D*N}`t4aAO9jSzvrErgAVxdAROQ>_VSt9q(J%pixpW-I#>enapIwoJ29^say`1ie_ZTEcO!hBT{}~6IZM5;PUw8o*C"
    "uY#-cF-7PND7BQWS628kpo65?-JM>nd>bEfV$06OTW>cN@JwX?+}DCPDv60a+_5d@xW!;SLwuE*#^kq&^HDhlqi}_WQ`ct*V"
    "gb~-@l4&arT$-OI5{%8-GH+e<Z0^XbX_VE-cp8)^LAg3vZr2jmrziFqs#~To0`xK!OqtNmA#Tp6o#oY9(Ki#}cSXkv|S1<Yh"
    "LL|9dOJLahKa=+b^}NhR*Nts@5_6UguYM7Ds-cadj(oEdK+x_ANh<_);jl{&rX)+oO|GRzxs`FChK;FJyU*2z<NZE*?XX^wV"
    "xr*iifjhIY9k~JeoAWjjPPc+FfR-69mXuf@w`=?V;dwZX9Z{JfDIlN}gC$z0Ck?T?DbUo4oRR8G^%A^@<VA?GN(^I%}?=~Lx"
    "dk_z#Cu~I_<V#^NK**N_UegF5Qvu$bU%<bA`6Y~P?;z>y=<H@0$K+B8x~kwG7MZvw?`hn$qFOI<!x^|0hj{>eQ;MR5l`5~uv"
    "0aItDKUrw^x_cRIKZa0_`}uDaeZS0s}k5ra)amnkzp3bwcxbh|HYX({PyBy%;Y5|@*J%+)BeoR$#}}j+^a17Mqc`NrGi&`O-"
    "LI+W&Snlu58p_LJTgO+PmqT(an}gV)TkkTLPr_w_6tI#}Tr23->!a`1t-kTwh<ulhR;U+5pt-ucXNzAwMt^2wi9bG+l`)<kB"
    "L5OOx~X)rCtq-EN{-TZ8TQFdkS$4mvV0wg$G4h)9Ahpp@3Kq7eTy|2Z)7*-#EuK$RirC{{u~f4{T}WX_?860Da6w&MW1?Izy"
    "6b4Psv)+;s8D%YEzJyPtL3@pZq5|?IX@%HI6SPUafXNC6si^4=I|2}B<dzmki=6_u@X;38$oXic-{ZZ8fDXk=OC6G02Z!J@U"
    "O7*&s=`#*_9HHM7KZ+JMlLY^-Km7}?bUHc$kcntQz8oq52>Aj;KGs0tWVGJRmB+aHcnWXM&LbQ2bt9Ay`mj~Mq#z5G)ck!&w"
    "P(8I>#u%eb=a7|?}7=unVY2YLg&!3Qs;GWgA9!*Mk|Q%*Dt<;#mA5E-mTkMD+{#L7r<hN0o%`-W3aA?5;L%PVR{z7eeq??6%"
    "Ng^k1)*;N{^)$N__Rcp7X7!nOD{CD@lM#fZ~$@26cO;R9c)XkQXVe36Ykintqk8(7ykjEJYR>^u+_C5#!qOW4wFw23Cq(H}|"
    "s1PYZ6g2>G$tMsB1TKxFpvZxQGZwpOtG{wCfyc^WS)9z(m4AdpEQgTAluXC)$SUGuJgIv!9Y+?C;Ml@9bD9X^}wgS?UTZSN7"
    ")b&-QRnHo@P)mT4M(j31ze+lEwG5qoRRjjx|bw`}R{_}PDm$8#gDR>kPuN*(A$I!g7Xbw^}l#NT@8aAp{{Jy9Y3H2Duk$Z*>"
    "ly&f5%?;2NHu07zM44uQ)LHb5!v{C7;bEtv>r%Z3BZPc0Q~(h26`Taz2^qa+1N_Hd{1Qtdwcp)EJjiuZRgYitbJXi_-y^c@e"
    "I|j`<=!Zq@1_6<Wc*F(`!x&M*hP_M#=Cj04(+MTXAdpXMgwa_hTmWL9QU@?b&(Xw_KvYwsfR$5pAGYXlj{EQFu_X;i};I+mk"
    "@1jW4y>A^O&P7#aI}?iVRbv|8*<MaJ-~9`4Z|8VcrK||Iw&z05a!0%hi$D$rz<DK(8#3CgQAYk+u`u>+Imqw{PRl?yio>6vy"
    "v$wAY^y@{_34M2!|ZV61X&Ki!_dTj$Q>?DQ0(?H#nz0VZHnF<?c)EmHuh{_H}NhT<3CUr(n2N&>kys;$Najw0=C_5Id{I%X|"
    "R670$t&@jNRv<d|w9u9i=Zy$Yx4dd{{mFR2of}a;Zr{I6uj}68`l;G`)mvM1+4vk(PZ3+If923SMDoaf^ixK3(cE<0j0Pxnb"
    "^8d9DK&=4qm48vHd1GZiv1YGTK-88N9cz%b$8dYl#ov7R0qy{J0$_#586jT@6##^M1>LIBDe~$MAKb_I`3pc0!-ftvuPP|R("
    "S21_wyL%s<e&mT&DXwD2<3w~xs=g6Wtu@m0TV%}uFcYl*GY49^DbJg7TPbrh>!2y!PQ3(umuBKmS{x{*U5B@6N9;*$r#FGQH"
    "*w;;hl45@#e|XXzX;*7WGC^AkH(i#B3?cVD-53$DB7ts(LSFypoDTe1JbxqYNGYE88y#0$hnGiqz;&#wl$L`p6m$U}7BGSs&"
    "L{m+|hsTev?c^;{4`G6w#H{5(`@Th&@}%)+HMz;<UF%U3?ZFHW7o8z+yW5Mz%1Km|gvG1|H&$>KaK5ZY+}$WK)i)t&%{E7l}"
    "|;Qek4$~;4oB&s0t&hRM^1qcd<R(l-btFPl9KmP<}mda;_nwc^Q@H0pnS&K#~>N4Q++%dd$@iL~O5Xo*&N6EHbfQGh>q(1ns"
    "jEhD`#Co1KI{qf8+C<t(YG0ZWKP17AruF^*!=j0fpaoJ<swGWy!vLS%exQcOTlI5kK1;|~!VNzmUxQ<So0IB_vH0DEOL*(pB"
    "Fx4H+A?~n6a%)y7en6yaL9>Qo3RZu-`|cxOx~oLW5wvnyYUJ#qAAZLgKp84>TV-JH?qi^4fNswx7Szk`_DeZliXng4l-s+Dl"
    "~M?{b`v4+?3Jk4F2-Pm+{)MV+c34RGvBMN+d<06&qBuzlZXF{V?|py?%4P--Jnw{WRnsna!+~oWNK7g0O)U7Sb9b$H!&>tmG"
    "Nqy?+~@uB~g(zh$8A%Hm4?<Nsy|Azz0jz|Gna?J~#9(=+(h`ExkaXd&3%LNhN^t}o_*Nf5${mRiTL`L)ZN*zU=%>$R(HA*vr"
    "!D*(bcMsJWJ4=swoq6|aq3<gMTh+bfkPmJS9p5bpld>;=61FX4Hm1lHk|7imMaT}mfIy7Ohki_`q*>gBMJ%cze5DikyhY4Dx"
    "Q^UU?%K&K&`;usSuki8h*r$XPGe4h!8m>?ESmk<JfIij+7=#wxFhV&wjgOu@#@~MaDel6lGL6Y;LcSi{$Pw~2n6k!=l}-%-U"
    "ud=Q?_Yfbll=iEWJ4vrmZh`;jHm!cPB5<o*mL){-(v!xEJeC4YokG^GkFUgPZ+9$bLcC;QH*|BR7P$g%4UL&%duHHeEN75*H"
    "_lDns%$6?oyrHS*7{$H)kT@oeo1xlm-6s#TRjUd>rFxiuNGGBn%?CZVj42gtExIAyVn9`yM|k()aELL(?SR0w78ey}=(hY7<"
    "bx1tCl%Y7wC8EV@B}wB5#M>&y7_z1z6i?`iPAT_uPZ{1fu?X3B&vaJhV@Xd>~L4e;x8=kV(BB{X(Bh`K$r!w6Pn-X?e|xYq="
    "L@iPJH^~;uas2-{fZ*|?0K(P_438++MbK{UYhkjnbHJaEdOXOp1tc4-|{-Y0Zdv_PBuD}ECJ%8L|0&vpjFGUP#2RS!)48J&c"
    "0Sj>m)9oNg{WO^|Sd2%JR{bLb40`gZUuT$o5I(93@#@2GPd$EC64td+ZSOdf-Hdeemk8_Rws<TBfmZ!@q8RH*jKBNj6MVX}f"
    "&1cx5gM%LhYcSjgdBt?3L)R1XHFK-B^dnb#2LJE>J-|Y9$I;dSo`FB5<sdcb)TG$0<01Mqq*|$%L71y{ya~00hPs44ReZ2&D"
    "|y^CQ#(gySoP=%FtprPmx-SA`Z|GLlmtk+*n(~`!}xPMt55SJ^8xF&xRijk;P7%0Bz?m7aIJlmtVoT$#Gz76Vt|`CG(Z@9PJ"
    "=Ln2T)JA~rIIJCl%q82Ina_x6eq{dbiButxePy;0?GT%|S0MIj=i{^A6#HI9{{z@P5i!iUR`uneb?N=X37A-v9Gf{-JnCX!%"
    "p0#01s@#4Zf-a2s#i*bygH$XGb(JWB)ckdylpodMXsapi<QMZDuGlM+SDKw>(imfb40Zb60n`P)5i=GY8Z;fF)j_@zHZs3E5"
    "_w+MmfB=uw&W-#~Od7b*=^CR6q2o5f+vhLgg~bzy(mujL7g3%gf<w!MI!;!6jba)9SQJA=;lBOMNCD&fOaS<Qo2uQwSO5L^z"
    "Y>9}R03c94+3;zi|wR=57yT4kGHOAd&$GH;2K59H-I0$gnR>zi@XxR`J{z^_sXj{9fSzBwlQG>G>p@cY@t?2{FtSo>6(rT9F"
    "=7s6j|=4o~Ju1**=V6wp`K<KGO5P0Ec)G$l@v6t=t+N<0K|JS=2z<XkxYB$DeQC#Aj>ESclUM+71j>M}``b?;mmUmd)987-2"
    "TB`0H0+!?7qr+}%|rfK>dGyhJE{`m#}%t`3#-kM#N<GD@=Ez(+RF`QMV1lFgjd^}^<!QKYndq*08#*~Cho<Bxam;**spcr5o"
    "<!9Ud?gd9y~U|bBRz20K@b}9_<i!<kOd0`%Lw~w(RL!*#!pgAIA5e7!pV`?I59nw^+K4mSb6>R>pUdx=CkB&;V{iSzxx9TgB"
    "nh>2JK-O+!BM$M0YuEA7<9ljAyXG7oa*g@HRAtgmChN<D1I~?2;;oZsaAtBEjX@4G=%HaGxR$@F@AD5z-)pa`kP)*#{rirX@"
    "a@I@U)}=nRr{CWYme-W>I8ruZE@uHLb*dKeoINLhLfu(@z9m{n~y)1;|I$w7X<+KDujFkXaY#cH$Vh&(!;o%rug{5eav5e0d"
    "bmOAnkHlPe$yi3_rBh;^+1U|2SZF^WE7S;AEYQbn_MA!xm>-78)>0PoIoz3T=tR6kg_M4F1h4uVHcd5&r4Q6&+?MRe=a_kGQ"
    "b@Ak4zLHcH)~&064JzxEoAg%RT2T}&1Q8fA`_4RnJhRl3?wVpQ_48}faoll30RSNx@Jl8ITMC<COb6Bumv2FN4<6a^?-Eo6-"
    "*uC1)%A3wi>2d+>vB?<iLq)f=sW*yE<RQ8}!%atTx=jIJ;q<#G2>{+x7u)Dd5$OO7J$XxcpU{H+;_5Lyv)Yl2c!<Q}Jx2>&4"
    "+N&+M`6NKpNYsSZr8&|P$deeqK64sP3%vL6o(jBk9ZO4JfbTP@+zvy8d5(E&F;<j#<M;`@edatSvI6nWuI^Jzp6eb!r$W?!$"
    "-0g45F_KNCh>!f0vuxGJ$a>?9$BS9UKWU&O>`WzMKO&de0u8!wk@!0q~+xMeNTiu4=@2h$TvV_&@tdvU5+bHp5Rz}9Iq}MLm"
    "H-#5zATD*M7-?80erxBreM%3*4~oKQf~2yWkyf>uRtM68Dk<PgjN|Cn4E=c^|Ub3loF>&K6pYCbF``8w*P~HZh5R{Ol9l+1b"
    ")yFa(?|x*JRcd~eJe<76zCs7cPWWBk<{Z=p5FFxKm%Srl5aNt{6}J+{(TQcsN-R{N`#5|!h6*`(j3yL}tCLY^Ol$ch}LwHV0"
    "bS}hFn6x}cc+GF_O{$2d@_3L<C1^zO^Yo*9pO(EnNU>l{8wysoSDUsg00^NrXu+rVdn@h)VqS-`C9MuOovO$J+n80PJ4pVoL"
    "v=j->djix^pm@z_h2MYH=$KLeuwms`tOQLeJ_DjGu&Ou`Ra|Tm{Br3y665g42M=JXRwMZ$-+h9N1ox9g2^k|hUpoBe#g}klV"
    "g`-v4q8R2tsf@O5CwrZ-8)d}A6-92rxp1>eOc{czFX_!$agyM@BQyZjEp7t4{VISGf1Nd{W!u}F~GI86|BqD3pgD~O9=U9aF"
    "a*Kw=mRE!!|L~i5vJ|-ueY*OQ6y1qB-cJ9oBu724>hyxwp_sZ<}9WC9n&>QwxBf&9nE~=Be3(PiGkF*VH-CRnKNGD^NBP<Z*"
    "&-2y7bQ`sy<Nbn_Ng%N#4tD<7WlGvhlmFS36Fj62|RJI23y^;NV>Ans?F3nMgTlw&VNqP>`A=+N!|n)?#~($*p4xWwgOc54R"
    "{N|FE&UkDo~7|2ZJRs#dsjHAS({x1G}{~m5_ZDFPKZ6A{Gq2!;CXSX^mYnNZYfTa+4edz>VJ$Vk}d5LB(gY9(Cu(nE4mrwP8"
    "*U0*jS6fI~?`r>>y=0^}BTe%HaifJ^k?Utq-x~Boi(a#dYn@&E{imPci7WN<hcfPOFZUOdKT(s78(_=<@0`DgH&35NEF)wGI"
    "mXHojVwc;dlOkJ_NG15Rrvbv=6xTaqlNw7z1DQpN5tVO!-IVF{-tgysUENG2z#%q%?UPu`1%dv7;Ca;nVrUe`Sc^ayDF_}em"
    "c#T^gt3qz7bRa5b_NXCv*!q*(5zqd-#0$3Enuih|J}PqfmSC!#I)jHHyq{h}1wy)~L#iO#`*>YsuP|!S^rvR32ayS@>06r?x"
    "t9xj|DLfBQXzWdR$?40(q)<`-~mati-)?Q<ks+oFCz18`f_g3U$un{%?-s2xLq%L}vki_<63>h%#84zbMT9%N`miT({D8QoW"
    "iNLFP2UJ|*-=#=id{C1#cQ;yO&)MK$%mg?}o<4R<4gsYFA;DbB2@HkiFB%J^u?JW%c33+xA71u_Ugv=y&Tmt?353n^T@z&|{"
    "m<l2^8ZDG%iDqb22{0-Vm(QVkZSm%9-gCxJ2H2Z0QX}n0aTFo#chPLM5g7wpW(aeKpg+JX({qSldjo&>;d^KWs!nrv8O(j7z"
    "~7D}bY_DPi%Ao|xNr^^X6F&^b`W;^XyrK?P7*abzd=U^i-Di^)qhFlzh-1QUqvO+|IY0I`@N9VU~*(?Qj|218-s3MU=W7rg%"
    "&qgm+|rH6HOS2GLicbLcSeL01)ymTLElYX#M_^`*(42dI~4T+Q@ocUBE<gy?1hH=k}gNa$nFs8pwSchA+79RtfOGC<!p^=X4"
    "IHERp3Yf+$8T730AGaT#Jv#sQ`&&P+~X{N>m1@xyy~|L#4kIHz;yw;Uy#-;@RE&GegZygEORU!6OT*)oGkb41QyER12(!f%c"
    "x_#f@RG>80c<rtFDNy8&R{#_pxBF`;Ri0r>e(F-CB;t<^=!n?O`;L`{9RpqfFoAeOa&e?-Y$n%2udz8+5_=(wPcli;vx*2|R"
    "=>;r~k0bB*kme~OF$F9g!qQY@Zr!jK+{bCf@H0t1dZZO#6bUpXnb2;wkc&c~aA=CUKxF7rVeWKsd3*}-o4>%{ee|Iw(IuB4E"
    "emWp`|9a2kxYBAK%?{{A75WQj@M3}#IYy=*0&J$`)C>GgMTrA6&0BD)aPmSH}m854l+~(jNW$0{ofb$go%T%EeWQ6kzrs04g"
    "Plw@W<=d<k+aj7PInC$hU<F07AYctAJ?%ZY4``{ow;lpE{*MbYDm3I7Gqz(`y)zk7U!oTtN4Ak!*aGL^$9#@YE!L1O0xcv}l"
    "G6r1=1G9K*zsj&%wuiD169jhUp0w-!!fx;2SE-M)<n{T_@{*B!@}fUk#C+++;XF(bkMf{x=l8O3P!1}J66ljdkQ#IGALS&A@"
    ">{P@Ot?AFjk(pO%5_01bU?)}+oxvsw^!N1Jr-p(^M-&!kk{PQQD;_Bw6R{ggtL#6dv$4dx#Zden6QDwj<jy3u2CU!si0B@c-"
    "gR|392%W<?LL`NJ)))GrA_2ZnAXkc{vabI79&!0BGu65xL}9GbaY+I=k#`$|JWbJ#V_4@9<poTqhqKLb{PoMP;qN~A7$`H}-"
    "sIJ0{A~IHVpz<e)b_D?82t8?SMl=fF|^Yh@vf-KazxguicAcEgTTN@OPT)NLLDbt=oE)N4(><1!oxS59sWrBy^H}I{m!E!DA"
    "PRCwQt}YvcTfAJGby8?V)3VM}F85A>>=a1OOr50m(v37G5OPC#I(`IW~dbAVVURSDD#9?3whk`|r~}$1|!V5Q49z1Q?a?NuU"
    "`;5enI)4f+VhF}^I2z@QlbLB9utF)mI_VfGilz@P8l#wYjg>d%w`j#>DxHf9>HB$^kdrts#;Q#jph!L6<#4jdX`2vPcrYqJ#"
    "DB>3<5`}#LI?C<6;_y18V>%Ype+xiiY)}Uts<l{|TU*Eu=@7}?ke4y16`FhOFH6eK3+u0<nmo+Je%zf{pd-o>R`U`mB*fCus"
    "ip;MgNnsF`R{OL^6OMJ?zfWxMUw>q6k#;7z6jK5DK1mQFAN0`>Uy>}vn6w29QoJ}j54`#s{`TXKk(H@V2%s_G;iDZRS({Ocs"
    "tgxrrtnuUy@rJ#MzY;SoMuR}3=L_i5appH0jjAE@^=tbh6MjI5#rk}0i#|J--Yrp6+rdcdR-JGaSU--Udj6SX!)V;xpu#w$_"
    "XLQHB0~y@*NPFVhhH}T-p!sKf<Zk7ckK(P^LLdn(0C-)eqVHNY9;Cb){w7_}jfn&KEb*)n<TS%>MaId$vB6A+s^Mk=lFofjP"
    "cnW+0EL#_rVLQ)WSn2~;T?33;!1Py0dVCffLm)5kFxIJ|r3E)plEh{o;0VL)GiLxcY*k!b?>#nMUq?($_!Whvs$4uUe(Dwy<"
    ")NDF{eX*7t>GgV^<dG0h3V9H$GkWFZ+&741WO8L84|M!!b+s?_{ZHpp^F^D2`;{-Q1H}TK+?&DsbV%r2*bp_?Mgb-yDg^_;h"
    "Sqbfp!A91@&ZCFu8Q_i6r;wWrWgZ|c254EQm1n8qw;By({T*0Sz(IP-&G5@wp9qi&bE%(e679*N<IQnp?4Xk|bYTEfq)3Vk<"
    "yMXtW~Q-w;XL}+uGA_g_lTYV!+!q;fF>MfOsFQrzd3grFU-$jLDYuZyJ+-Mw2eh9im^P`-@UYg`L*2}%F6FuN6PAYQMGT>Zv"
    "O}J0ei&*`KyiG{uSrWXchl3{QD`<&r&2w1Y5{4BT0!;kBL-NCz2?#A$FWYuieCZS8fgcYB-{nknau?0EB!;I*?5faDR6j*Os"
    "5)m&cZnZtftlB?_loBMr>U()objNgri({YU2D_mzeEi~9L=@fXvez@c3lmHqd+T}-tSyu2`vx!Gy_>BfEB+T76oLh%KV|ItX"
    "!GiTvMo+-}EuPz+NuP<CcyVp~Hg&-RsLW!{I^_N6|jAYv1|0piZ7OoI6tkLUIdn;U_z5lXVmrLpQw~ZKS;ZTGj^00x9%=fkd"
    "KD=`mpRFw8Q6ZIoi%kaqgpfm6({Q`czVfonfG3Z!)9>Q76DM%8HHIM1kfs?X!U%DriQd4glw{J4RD^3c5?9K)=abKp=+;G{3"
    "NpR3d~J&B#|q|>%#`~wgPo0Sys>y3WoYsDS3X7RfCU4${G2BNrYip!NhZsBa=JZ+UthkAGtCgq!2rR=wwlN$xdYMxGL`%XF#"
    "5~(Li<_`D3?06QIf|86oUs%{k~td;?u}`)bFcFBdcu+a$6jP=(rL+lqkm9_<Z>>Zf&fqUxg$92qE7cCIATe9%Pi_j=$|nynp"
    ")!PEAkZL>ypHT5swm8==zoLCWGLqxa;xEO=j8;QxWC`^692Ug>;ibqh8K!q6uUN}$)vF%|^~;ue1Q^2<2(WEp?D@p)x+=wJ4"
    "EPXf#u<C>*ZYK-<}%I|4vFhDC!VP(d4zpE7(`I5ljS4?W@qg?upa}Y>XB=z!Hk<z--kKU>(ZGxC<N##UFY;9!)Y|~;l4DrF8"
    "d-(XteLRrF4UEo9X1fL<<cnBCY2>r3;~eg11N2u{u(h*;x5ZU{dJd-3#cq~kLe_*h@=7)tHCp;srl7RQQklvw%B66qVAC<BT"
    "44_Kb4>$Lxjom#(0iWrb4{AtV1QTVmM}P<<M%hOLtF$x3-|Cj?D?KF#z}HmTF7RNLEAaJb>a-(Idc(>ejgJVV0tOS%(o&2GO"
    "<A>4Fy59*Qh*WM#lWf?|!e9Y|ljYP=4V3Nh8p7la8v@gi%={mE%YJh>`?@z+uCc`0(x>JkBziQd7095JJ8yOaKt_J<zZE6<4"
    "wh@7}tB*-I~@?Dn+<AW{<^5#Jl#5ZMuPo$t!GQ4tK=3P$yQ(s!o@fg`p&a(9;d$6M*;4ABsKK=~O&&RICv(Bk#^W0;$mz#pz"
    "(!Hu0ARYODuZtXd(+DNq~c1|lbr^YAn7nd(%BFkYnchE8=B5~IaBScc&uf{~y(~s*Uz_1ddRel-Es2=|iv8~{2px0e#FmNSO"
    "X~76%q|E@!gC5@h{0?qzZDJD+JsV)VEY!5}C;F8TLXHS)&KYT4Qkz#mEB&3%uOPd8886NqL%zMO?tu*zv-x4NQpa_rtPPU1j"
    "C}G~1n1RSqwU=4?>{0p*Z=eDVp%v$CM|@n#8!WRs4Vg7;&Ip{!QXxQk*b{ra88U1@f^AQkHH{;)5`xb8{)Swzl<{zQ)u;iNC"
    "tfby#i5LplM?mX%Uk#zVa85-uX%?Rx>(z_{*jQ{aDCx5C*;#Qri%VLf5q1NvmY3Ehzm)jH}C!aJSo4!&*@Q5JJ8mm;fN;dqA"
    "?%k%bc({3k1`xNvL(7u#(Nx&w7OmeF|@G7`x<yIUJ-HTS37&1gG-&X}*}JP#e7_mTj$M9(_!7%cM6mazzJi9l!9OSJ(w+h}0"
    "=wKwq5qeuAjotxMwRb1#Y=_!?6;&ZfVYXVxaS!y-anR!k|X>D#}qRi2NjKK<!ipgJ`K-B&6`<DOe-@VFVN1U~_pSJ4r7rCts"
    "LTMsEUgoe-h(S@J8-y4%A}piCKU}$nySuwuE!i;!owAVY&&}U}5c1uql|nh-q@FMBMgQ&U=h)oY#_NkGr9B&iofP9HKqE*H8"
    "K){F`RtO!rnt?k_l@zlNs7P+{#Amrsyw@TI)Hq>r81AeA+`acK@X8FaA|%HoflrjfB*anT7GiDbHS9g8vM7)LVRR!eqsv$=8"
    "f0IrvX-a{rdw<g)zhoP)vS|%k;Xm9Qr(q_zsEj@LrTJzwe(q=s$?}MDiX<;&-FTBWut#4johCN!rK9j~}XOtt0@rjuG<x!2|"
    "#y-xDhmpH&{Vf4XxMi?6<gB+U_u8K5lO)tDr4aF<0+7w(_H2cSmx1|y^7q*u^y5TsvFu9rIeXH>Z$8$FpNEFT<JW;zE_39{J"
    "ibbutrJEu<K#OySF|JfBh=<H%s3<YIW;&T#!wrqr`%rKuc@%E(`Fe@_Ht!)H@0b(QOSF)qdG2U#c(|@1?mOP`sd!e?6G(q)m"
    "-RQ{+)aFeAx}pF`8tBF$Zf|YkA3nc=W#?V~d&Xi#Bm#sG@-2{xyCeZbsW0o*pYK0HmKFHbh07QZBc$CFCi7Z>hUomu()aX>T"
    "Z#2+hklSrGN4K<8&Nb>pKhTjnZ%hs4v=R#8nHN|I5dq#UKB`seY||~Bz9ea-(SCm`SRIcOQr!g;S8n&i|NwfmlrPJjgu!4c6"
    "Jfw8OEI?kqyGEk3jYl;^r@Ff|X>ktPL`8!D-uGp-%t%1OL55zz^Nw|4kH$M%TF<4jpL&Xf}{FoA~(lRXptVG@1RZ|J@1sv0("
    "y$knefJG!eqx+3Dcjd$;fxb0^d&Das1T&sV+MR>!@0NB$o+CI5BJ2K5mmZ^ds7tUB_Rd4ba95Hn}>1gMnhGPPcf>(Wdr7CJ7"
    "lX@PdLjoH`V#QV2z;e$sHv^63DTptFjUuZe_Z1iioGQ-mNB;L7n5vM1nkc&ZLk)zd&;Q9j$(gNdA1HFD9rBuwq>LXa&FFd|S"
    "voZt}w`}=iRP&l;gC`<S8QGZ2xWFiao1Vgx%{Bbt=1mR$SEXVX1XwA=ZGsR&zCBx#8kUbENfwvDC(Fx7ixTf#xP&Q{aQpR4R"
    "tE8$3pK)&1b`nsryp<f+)4!}NdWJ20`2#fM8Tk&B5bu#22K;D==ER`=^Xq1`UWm69!Jq=;lF<T5mq#r@a!SebYx8xr~d_OaH"
    "7$`ug+Y+iDnbyoerWjL(}Ctc_)@dA}`e-R(xWrEQ_B5B!3J^-m4m*QW*}%_KDW)=Y_0kr6e!{gF)%ATNEgh7!L;>Tw7ViW&u"
    "26@K4D14if-`e9uUqnv7NY;Qj-=x_An$DAb-tDWxP5{8!RP38q~=BIzeh0{F^|R|3epld5!O9;E$w5{CweMAKgy6#AaUwO3R"
    "CC1M#tm!+7DB25<bcYEqo|Etrdae96Mf4qJbx4RvrVSu<S-NW+PtV+x8SvJ8J&Yi`pFTRA%&6^0)fhK?o8Ea%M;-)l%$o@En"
    "(eYV(?5Q=S2By1cIO}xhEw@PDzsy5U^8&p97{n3Mu`zu1_#ysq;~MVdsX8S04Y0=GpAhmru~EW^sz~%ll8ek%SFyFz!S7yp8"
    "S`<ZZD6j`SCxQFi3ugB?{)PF;`HyYNPz06mej8F4uvWLq*|Sq8H&uRpH5pUz+yOC<hn+RSIUWnMa)h=z~<Vjd)AELr0U-m<p"
    "Y3u8{pNYCA_|L632oNjcyn1qC`u6ZMi7w#OMzQWxbVY4JxJ2R7Ni@`qFVHYmp>Rv<+i~pHuKJNuWWNqS<U}Yow$qvcST$TIe"
    "<te01eHR`Xn||Adh5A0_|@`JQ=_>);(HGi(3(##Q{^UwR$8S%xr(5Xs_Q7D(b4S>_k-uVvWx1$<R?|EuozukVu(S}>3ig}O1"
    "5|Mn*je7pL76T>1eV2x}}0(FDV`vU~ls<}@$%g|~zG4aw%c<;_#e7?GjKsI}@ZX2ammhcQA{fP;jyL<mWuEq&YMiJsfwsa*1"
    "X{pH{+4T0(9D$f9YQjZaucd0{$Nf2}e#nc7i*pnrlWI?+p?l|kUO+q*`hmfYDba0&c=z@#eDvfI9u=u3o}^E5{W&#XB!v91+"
    "y~6D${=ts=%N47dph3qg_%W+TZ^opA(cd^D3_#dOd{31Kp2Fo7L!D%d?t1}9i1YOxe`%e;X>cP?nG+f9QuP4r3AP(L?cO5MR"
    "x1{ee86)&zuYVJmADLMoeR8g8;vN;YGYKJBMVqi}C&dtvpAPOM<?t=u7cmjPf*TFRfrIztGk~@rm(Rq*(@At<!bj|8vt$NYB"
    "6ID8v&f6XU<o>a?1xE01w~V?+P$;z2<O`Tk)7fRG=6z6ClZaC>J9*Ed%2#_R%io~)>u-dGf?>v27k_a`3#sN;k7ZX3nFKdCw"
    "#{zkQf-Afw0v#{(%WCQ3*{R*=ZK^Wk77cOD0J%K;nxuyM~F+xPhos6{Ge3se*jK!VxHMp%Uymjg%-ad62{caa=lAzP?p-3}K"
    "#!Z#Vx-!=`0DYR){6)T54QHtT9_ol(XzM^4SacjPXeHP&Ievfr3a)N<@u(PR;4k;D7tf};f)Miapr;>CUL__zF~7fc9dV<DS"
    "LPOxZSNp=2Hio|o1BVMJ;dNG7Xuswfz+?1=ReX9x-bq<SRl^|6rn|0WJrxg8iweIF<i5$il)zQ-^L#w-qV2aSz#s&T_eviCX"
    ")X!!r7@AymR3^CY?ijdlzFxjxjM1&K)8#fUR=IUPs|4E@<#SvTpB%|N9vY{6|;Y5s$#11nv8m#5Y3pWc_P2(2oOra`PHCT%p"
    "GrN7oYa!@vXpAwQ60QqAx30`J|sgQbZ{OePJ@au-he@aiE;U(OG05-3#zz5I&mz|(C6Rp2`8E!-Pqr$$feap2I1LIi^xWp{w"
    "r=N2$GF@^W;-qI0uAtc*hA~b<pb<ak>x|r@sMdv}0BfotcySux1^VA8%&6dhL1MzDz7Fm(O6ygivd;V1>TW!YlPa-{$rEIeU"
    "q<M}~`u(L9V627Bz~Q|+ckt=f1|Af?>Yp2fH3t8LkRL(mB%j;zQ6?I;zDx-C{1ffvesOXJgY`{JYpa{D{OfFbHKX%uh?t+2R"
    "@&eEXj4%O*f>Bh%aF$*@+85o1A5ISZtra454UgP*6t3{AjE2+c7#WsNx-%80<$tLCJgZUsWW(aaY@JhnXMhP$`Wl0Bzd99d8"
    "3v6%9%&kTt8S*JN!r1Wk0iLWZvHh!z97TefFnL0*ER^{BD8(y`n_cXyE$FLtNk4#-?HQpO7DtXX3+@ke};FxETY?Ip8msPUA"
    "1no=0nI7gHs4fe*^8lHmU|E3j+`>abfj0i&A%S5+43dBOGV2NM!9md-!Udj$-8JGG6#0%43^?odPtHeG>E9AhUA@!6w?_~`y"
    "!thikJ)^*gBBu<`@&!nZ$xJK^$1~0JqH?O>g%QG{u8{23Oax`6uhBzM=snl{H2HM(wA#(vmJ{yWGHbD^v$b$%5Wr=cp0?R>("
    "f4+GQ?>)JPM+LBLfhRxhG)Y3pbIcOpjt2%yL4?0Le;KbGTSBwbMWfe8vn&t}a&3J>k*n`bDt-NdML$mwB~4_qW&{!PFu*PhI"
    "#Ga~IL2oy%lMaDH?Zc!0ls`DjNoPgCoV9tn*ITo+AX|u?mU*_mR9?lnO6kl-7Y4?TcIpeRp-}MNvhOo_Ilwi_EZ3ee82h^Rz"
    "L5cK1`AcUzPy)wqpaoN{8l^4Bii-kl^1~>^2fSuqFP#pMHqX`dz8~tEuw0dk2J&uYw8yLVmzXN#y*3|M}_@oIh~_i&2O;&s9"
    "3vP=lnOc7+p}z6SY+R05vbER1*!e=*g_y85+bw3F=p(iC%Xf+$OoSm2!#$8l`Dh4=2>#gkqaJ4KGJ7#q1~W6aZ|+?hEk;+Ig"
    ">$N%-o$Jjh~4zJ8D=*GvW2Y^&}EW+w<AUil4NL9x|^dpj-$zicmmgqzg){7K>x_b|Qet2I-BB{}&jGp|de^x@s^UELr9v2RI"
    "k>c;Kd?cKOLzC~<#y1$<-5nw!Al)S`-H3Ffbk}H*Zlt6IK}tGD!&fAvyStkKV|(%U?mxJmbKTeZob%kzVr9N<mSv+fB4-;im"
    "S}jyqY+>}{NYetV3SQAK-aGN#%e>()Wpy}XIVW`w~f>pu#GDD;p1G78L|47i+g%@60)5Q5_X~4v_)9UM8WXrbXts$_uqxZ-q"
    "Hjf)+io_SOs!DWj`rFLtU#~GL-!c%=5a)4Repx-Vk`XGcfs`PYY)~3ugbNpk#M2iN<3P_P^U8;r;)@f<Co3lfc)>C<^a<t@q"
    "?1?!XH(!ZDF~$klcMjIh$-hF?8HYLt^H#eQ%E-9nL{BYtgGbm5dr&`;He>i>!Rd+N=*7>{rF+5{3lN<?JnyX|EXa0Q}U?+jJ"
    "6`7$C)h<dihXKvlXo{v8#N->(QLWda3J-BK2eTHHz(90|yGtMdFUp={5UYw^~8qLu+g#L!3jlEMedp?{~>ukA_R(S3H<}JgH"
    "U9UfoZ&$+F3$$_WVlwZwl`xpbexIcUw#270uKJ?!V2+nBM=?yEj`C>fNEUejBK^?T4}Lh1TVY47#7^6QpoLd6oe=R6^`JNaw"
    "UE_?H>^t{%^*-r(p2(>ng}k;M)SXHnD2gd|Bj_VaU}e?O=!cFK~{+!>cyS}gL_stIrcqy{drahe=Z1rT?nJLbYJGeBu?8lJi"
    "K>3y<`#qp1>l`<C6DL{*gy$irODmmB4NoeiqrDTg~D?VF43c2(<hda4{9UN`69tu^65aWs!ua;LXR=?)n2+*hkTHd3$3vPET"
    "bWvrXR2NsvqECn_!0sI-ONk^eD1LBsO$#E;rZ@S^<KzzrgVj~tjE@k$|<qgxF=^2;<+p)@`&)JtB=^1fG&)8+HVyxqjMwFkD"
    "^Vc8faXsE|=0y1u*Yh+DH?%6NRQh&bMnSf_NYe}JAmLe~p5{EAv>^P8Z#=6ca#_O5J+@ojx9NLT=FJx)m5ya1hFJGiCq5Ls4"
    "IE5*W$TJ)ebbMj%Lj{3&tG&vJSzK4wdsvt3>xJAsj@l0ZzIyk>H8enX53dc;sbbncGW%&P1Fh4YEp4=Af1JS`jOnrE(tokeI"
    "8~xPuVL4<51Lh!PX-?i1a>vgC($-v&DJt#!wL>sI9wRg2$IG?&&&g8LN4Zu4_eLXaH6aJ|5^68udpz0=+nX4$2|XSwT#F(Ms"
    "1VLK>~Oo@p&Bv@M$$b@#hwV>}0-sc662{;NoW7qV|#dIY>Hn#9X}G>THG(U>Sz~&M1)$lV@R7rgpklRfo^e_c#mMe|ijsZW0"
    "Amx6S|~->P4ZI0Kw$$;y=VZtwz|m*wu4)L!C^dORVi$igFH>xOeXxe_G(M&eh|pt||x#C*-hbH*_H(>m=VGY|At1S~Ll!ok7"
    "7phMK@Vi?V5mTxaX$8Iu~vNG7+C~5??&LZX;mU;R2zaF>+YaMa-=POg7ecM}+`<)o@nJNTfID0Jh0SVF;h`~KJ&a`%BF3yoc"
    "EJ8@tOB{?xPXjOeSyhbdsW4_HFH;WD_~?uW7rl!ILNK3@|AQY({1&>ztawE+aufaMozi!^y0yhVI}KXLzWs`p0DN~{^M6DZ8"
    "cOFAo%?|bdUI*jDay;DE)~-ckkO*g+=V2c1cz!<4qM>=-s0YKX}6!t@PllroVVgyPR+vV%rB}0Q56a}2xYm}3`k&)8Mrw}M?"
    "o5=Qt!sw5Kkl2`;QjxuRRJB%?yxC7Fir^O8zvFFk)h2d$+g+S|TCN1`T*t?YAdd&JW1x{k)XFiDRK^9_wYj!;D)i9JtD$f{w"
    "N6v^Mf29oCbI=1acU?}-AcWT&jET;LT1#!Sp**}$8f<G-PRL9!zaRiNbN+u<^u-P`~epk}eJ>_MJiF7B6<w3e+SDtUs&7W@v"
    "kMm#XWX*8+s`;<$SW7{kfOhiZz1x_?OKkDJ(dpe+;=h!l-qVw*JVyexr8VA*g_D5A-X`Maxs%h$w_j<_!`p&naVipMhr`g%3"
    "=i~M_w@eeS`3K>H(^1`t+3UUYbX~ST*ZY;03lkeNh+9u=K7IKUA$s<g1t;+0GTQio>=4nAeDP|B?SF8F#Ax;2Jde|zZoMOpu"
    "U5Ti(Ya*)w1>QWJ0L2~?hv1aH<sXGt!QMZ_vAB9w}>Q0;rc@|%YF1)^wjy;0t4*x>U(;nJQ+JXGB@(=Q@(v(A%O&`j~&1Urt"
    "Oy@Wi!!V9$oL&)P(LW1qyof`g&VJ^am>6!yCUp&9CrTq^oB86d>XEQV8sVn%b=|jkubm%IG3UpB_8waQWT*qIwgmls<<{dtf"
    "P1Vi=EsoWzz}pALYMZGMVlYC>8Sm&>>-DY$SlY?D#o^w0s@z`99iyw0g$W-2S?Gq89KpmjKzE&$0?-5CB5P=I*=VTK}V?Bfa"
    "@*Wy`$@lBQf{Gp*g!NstVR1n>2YiPi7E+y>#Rs%sKMnrg(=V~owk0BD90Zc)rMZP#LOM{*c#@RbNTl^fERHCuO!5Kt0eSe2p"
    "ox1ZdjTzGJvp#wX=|bwcety%u?#V|mMDXYr#o0LWQ=SY}zUoWy-vNabr_q6bZ{8Ax-(^Lj_PwQak*Gx@r&VJmXh&6vFB(X%w"
    "-=5hYQXZ{F3aM7xW3#k*xY_<kw=Y_3<t}O5KxCNqk8^aWtRPun6L@UZiv~&pLbauFt(%0|0#{9KCAZ3Wcn;&v#~@8`;cd!w0"
    "(L_R<~ep$vNTGS)lt&RVK&jVQPYrmQ{CGUeg=YqW{Yn$fJv$Ij0JXwhFb;!1rYdUvaiMDUg}p9Wk~t#I=Hr1<-9=e^UIg;vJ"
    "vz1)z9GPQSy}OO%jIm*UsMMY-{n4+`nJqcpWoDynY^_Xe&~Gc!IXar!%GsD)tGPZ(52dYK{h<Ra0G|5XBvOr&SApw_&bjIp5"
    "PI@uHPw`84lF0mJMvkM>sKb;lShsx4i4AQeV^$hXxAf5Z>36~-ZggG+2lM_^B<CXqW!*OFL@jKV@g=EI!Rkm;lnfUex1@%dJ"
    "qGfEDm~;S%?oMgUqO3NbTS&KUz6fdLPj5g{Y|)>B-h~s7F)AXX;yi@LA-x%GVyBh=o1y`j>6OA&1}Lc(HohJCCLc?|npl5~>"
    "A8b(?E!u6iiVyG)owDVa3cR&qgmVzNiIRv5R?sm_Z{108mKzAB^!W^xQ^qtR966HNKZ}R?@&<I{|Vvt!cNw!?=;8zuNAxqEh"
    "tF=Tu1<}(u9d^4iiF6zL=x~wBp4RH5)%HU?9O-k|c*_6G%9-BJZ%yD7I*VZ1G!_Sb-zr)~92fmpkYkW<;_|W1#rB0c!JB+lS"
    "Y06}y%?0IhBSk0Enj=Phn-lcBN)l!51OsBpp4lA@?)Tz#YsmCaZ7E}b_Ih|+Yk_Dt1v_`FOYwzY;f78HvE1Mrtu^qB$~G&1l"
    "k<Y3-4!b|S770Pi@APGlrnF>{J_9Hchp^K=%W*(VjzjeTs+(gt(4*!e`O8P?q5QzZV=Z}XWfABNkVhM-*Nt|DR2!CSlY1jnR"
    "evr!cGlSA;=OrU+Nt4I*iIh6fS!DNvfLjVg2>7iKPryFuT2}y;#uc`jQ*!#a^7_Ue0bb_37PKBC0{<$0Q}H1oxaSKEdm{fZK"
    "xmr;*Ei_!Wo-7q9WG&A*+U)DU7D1adt95=wRT=xm`9~F%$hnQGi<HBdU(KqepiN-Ym*nN{Oq>=oJAVKIiVHBi|R@q!62A0NL"
    "On%*zbAq{(az!Z~whSmjWJ-7X;Et28J|XVF^<)Q)0JN)BN7Dv2}lKblpE0s_MR5UPB)!glbe-jmwBL`yU_`g#TY5D+qf_0r{"
    "B|`3eb#YHQwZ+`_>Y6Y<=S=Xp(^IZb0l&^}d7d&vx7h)6C#_(I&M9BUEvQ=4Sv6C1bFc05K%fA0jh#1+}p5f(ARjR$r?!aGX"
    "EQ8ixL7~Jj!H<`C*<-2vy{Rg>^SDb36?@N=!2Ot{r-b~-YC~x<9&^f1=d;k4wb$3%J4YFsVFJnw{2__LB0tWho{GDO^4%hd5"
    "?IUN`1?4Aj2s0)xn+kspMl2`Y-NGpYmh(fxJ^*3zfM~ccA9G_i%6S8=tmNu8U&lD>WeKadwYJvR)AzbR{dSg3+Xl9PZv|%K8"
    "CbvkcE-D=TPoe-Mq=V4dr6p;EZ2kh`1EK*hX1V4sE2@*lR-V#){N4vVu8HTRfmgfS!vXz`0tlc#ZRTb;1s+9R%lN-hfe_sNa"
    "Ew=J(vbftS`XNS57dfCjr?15ma=K-cx-I=buQ$45LSXm8R8WaDDz2Q|=E60lfeASeQ;vbM-U53YTS8k+G)`Xo%54z#=_*%Lp"
    "9JIqEx;Fo4%O72FrLF7!g*%+l*$Et`yGwnjcp7G{VrYsHl6_fE8A{r8qIx4SNp7_^zsgaMH8)%Xcu2f*@gy;j!Oda8@GJShW"
    "K?#>!RaRb+6hhOPqraWMe*)5!bH5O2}GTgp>#y^bQ@sDEubl`WFoU7o_07?ik<yxI{iWo0;<agZXw($1H1snOspnY&E<jQ0?"
    "c39Lzf6+30u)(JdLhu133-bD;K0?0yHbuVm4s+bYHy+La>x*jQDlcDAi!ZNfM^hbkB%=Zj*LwC}9~04@Ku!dI?^DV<o6!_2I"
    "Zvh(?gZjnl+Q*~%}gdT!l0ipe7sxy&dfm0D4Wj={{$uR$8tjHT-JLZ))BO~MGU3Y66%0td+qO>e>`NmCF^IwqMHyEk|N@_%n"
    "8WFjY22qf%K!y?PYhF)oHS24vc^$Al<AJIpTyb@M%Lb*!S^kk`g+!i;o$f?L|muL66iMBm@S|pF;q`{g_meGXGs?N3?M&8Y0"
    "vOU8y<x<V*=rt7NXzmosj6vZC{C`yg;A5&is}8vZ>49_+vLjzu)fm%bmlHrW_$#<9)~<#=w38}Gb6#^pF91t^2RMw1G_kGMx"
    ")T$=$Rcs_5QYZREnjuc&$b3boRG277e1Tyi`lkSWjc1#DLatXbA#=v#F-~XI4s#h#h)H5$8NxI}<C@=fPa~b44Z260D6ECaQ"
    "oEiI~ToKEVHEFk)%3LiK@KTUI4xaB#LgPgWr|=>31)~-6f*yzo<jZTK!a4h5*#`K{uDERMp%Kb@uZO{h;5Qr-9=itj;=`HU!"
    "pObg^KR(wZI_Z_J}$epUBP$l16>a2;a{Z8Dcl@mi{&r2N%Wl>%)l217h=)>MO~LP?iu`nVe&(7(w?7S0b5VL9a=-hd_IpXoS"
    "i-=qqu0F9Hja8X}#m;!h7O0;OZ#4yCQn*5fblr0nwcwE6&@a9@k%U^9Sk9*9T9V1Wr&WW%dG9VUZ{@_z_HmB8szMY^~jOW7u"
    "^<lAG5jY$D>5^HcMf2s<6D(@*no^^AQ<T)1ER=k>NKy5`FuJmrvWY`E%U3v<_e$-`B1gZ&Y@GPOm0Q?v^i?M@|v5QfzkphyS"
    "^b0usC<Xtmc-|t7?^F9n_U3^iHz&7Gxqwh7}jTL<Ob!FzvfmzT)G@>;OOdrk1dtAm)bCbz_Pu?h9ibLFDk~*u&G5C(Sc=3q-"
    "=Mc2EMRIUpTM@e4CwEr5fU1cS$jBG{uMSwoa1Q?cTAWJVTRPf)mp5j8Wsm5NMzO8aGLy>q6##~&)~tO|0eozoV?=k_rgW|8L"
    ";q_!?dvB6!no1cdFu?>Jpp4Ci(z}%;rx?fnBAq+i;1NEnTV)I$5&79!e?&o^6wR4ciz``Rg3TBC0y_{^se{!&(t~ms=#pnt2"
    "X6gGqMf(E6g~#QdzdszvJ3$E}OrI<=kS{CklpP10eYG9k-!#Q~fTrkMX4B`$iz><-zxEfK8C)aKBmxK&qgYaHPt7T!m?DVB3"
    "vhv?IQZ&)d{T<S=nRwb|g*+vBB2oV*To*@h=K1B3@be<1f2tS#q`i}J^u<}Ky7lTTaoW49*P2Q%dopv_P8FNau|;l$T<@bT%"
    "%$L&o#4;IR@PvuE7;u_Y$9=7+qc%Sy>v4xKEYC;JAW=ct<jTlkV;fc(I_rS_tTa|vAp*;2dhib%%#v#4}!Cfk`q_S(h{_rFj"
    "q<5W8s&_(z4Cq2ofsVRX`=Bex@KOOJTVhxQhUUcEyrfF#Fvq;>=Rj(?FOi4VJc9D_4!TWIPCoeAonlGjT7ijo#4rwZm1~Mha"
    "wm>pfAveSxjVet11j=(numI*XH=cS9@)j&zgkvas3oofKo4_$n+yt}&%@WQp7f+mT6%p}Q*Ci}rB~X4V=cP-3^E||wS_-qLS"
    "=r(2ZGC`!6aM4O`tVSj0;QLbI%c$2(=2J(`KGL^-k_D%Fi8*GGb%qVE}~ZDZB0P(8XzgwC~D-JnFaen=L6$^soyHK4d5ZUc4"
    "<ux1<ly%&arshz7Wv%i|DLB+aCanL#hT<mh$`UUFvmIWY43+HC!qMt-?K!1=;i_^8dVE_Pk)K6Anwfin{I^^HX|@|xMse8Z!"
    "Z@{MD{PyIn|RgH`5Bg~O(#qqW<SNH!{)tpxz<qg3}Dwr2^dsvY-iLX-n@cKJDZ%%+3Xo)FN4m!Yy&QE<RJ))v<`{n2s1-e2f"
    "O>$RUY^uM|RE*kX(taRceYcAZx2T&sr}`vL?e~yz2YwDuJ$qOhftR8rU<sFc0uF9bZcMa=T^3oB1(2pdp-l^_qOAgN<5P0yF"
    "U!&HFI=6l<WMU_pivV7<ff1B{)GY`GE1l;RuSZS7PC7C5~K0Tj^{A+=<H43AI7<m`pih*22OcR=9O^G{v~2#Cs5F4upj&sZW"
    "8E&X1#I<gQiX&69~g*y!Z*$)`$+ku{RwOT5?C8BVssc6L&e|O{Ev>$^`ndXG2bYNz4GzS@fzp=ylq#A=<*D27W|ZI5PmW396"
    "43$GB*m9`eCT;_<q+de<*!&w|m%wzE8mVc<lsrt>v4VbJ_GwDt@OuEh!zb_~AEd(L&eNel@WqE}>@mpi~fc6<~vdi%qKIhhi"
    "~SW@5B5&fVN@zQg20wGXxDe+)z(Hu7he5LBxV>t7B$A7@!5=YQ8U&xCcZ2>44SKkoIaxoW-(OPt%f6rAp$MF5NcXLr0(eL1t"
    "j^M-9k~}#ym;QZ4#2s^Bl0W>E1lNBMSRBB*vr*u(i1?r>UmWg<&!#B-1s@YmKz`PzS`4UW>$%6HGv`umy#?zLo`$&=|IY?Ig"
    "uW*|+v7(%d2|$g``bD^#w4ew(wTnb(?aMPP+4UNJ~N{i?CR=j$8>E)(;Kl6h6v}NI=5`DUx}D3V#A_%666o0isn@2C6?!*!L"
    "lKNA8zU8(a{c?ovm1CY@zbs*{3Of0ZdsYC&a$wWwsUd1(WqDT7sL+#h9XjtHUSa68)0Q#vdG<WRHBPMQ=y6uM&$ql!I$t3;4"
    "}2kRVE2JGb3kyy2&0t7G7{&ZMnJcQdWY2EjjOKC)XKCdrfZc2czhfy90D$A&Hfu1|-I%WyB#r(2A$i{}3qXg~UQe1CUA$j7l"
    "Fkse)hno?9*vq~?ejE0n^m{bDSA8p|3YUAE--6F`69WjjT(xbxATcfuHR~bykm>eHzpoq!X^d78u8{uJwAf2F8gDsz$)unp*"
    "s>)?xF4g_RBfDr3?FR!)rnT*o6fM}^Z^c&W{i$lT8Lz1Jw-o_}gbLDA3R|3CU_Rm7XYa*XW}hl|UEG5Mr>}Q6V%Cn=);+ph!"
    "keR>3i(*R;0GM^^k@pmI(c?lt>!ms_ck{`H!qO{W4qpeQy>6sGXJ9_VGCjsdpb7r*Q#zVPBeUEZy3B2iGZ0ySDrnX&?4OX{4"
    "!NlT3VD1eQ?&qyiRgpk8jVRi~l(o7%3+WW(?s+>XeapBHy2M7QD7rvDa*&Oxw2l3V#%WZl9XDf$fM!`AG|#*6(O@-xAWlq~O"
    "s9xFU(PEO>ft`#!5?s|w42=aa<B9%&Q~3JjwX2o>L4;*v~@Q0VnWKIu$LynF}@yhK*#i)P{Ve*~ks;H#(szF8M0%2rRR)8sJ"
    "2?D&H}ejGfV6(EH>v6*{JqQ0E@`^108E`k*(i>J{XA|(+JJ4%$+s{f;pQNHBw2H?(S5$;S_`04pv42`ZFtLLc_zORBBl}7u("
    "lt#{Y%8%VSo(7n8BpK^MP5)aVPXfBAtGh@iQ~D6%BTS|Utt|+OQl&bE-lN^u=Xv{<((7Ju{Bk1z$p~k>M-FD3tgyq)I`)FWj"
    "|5CAlL~)z#4*s&7kcP-Bp9277V*~c%SRe7d>&%*nb1N-%%CJw&C-fsTr^K4x$MIW?m0HxVz!Fo6A1)1{R&Hnm$YJLz0ss3{b"
    "F&>+v4i|+C7-VTy0bSIZ<;CXahhn|95d39`F?k<+I=CvF10<mKTWGK-G=#lpO8GQ`u_hldL*{JpS2QUJ2}6{9g9eOZZcbmX<"
    "~N7~0=S*1_+c_0!|hXgzgBV|o4KXSBte7BG09{CjMiP4G&0g0D-KC_ssAQb?dKTS)t#H(%u`qnO?DA8XtN<C=|`^%#(GTh1U"
    "0U_uWS5+vrL{<_6*e!hNSocdmVMi;@^DE5_SUp>U&=2GlL{QlSV`lyL-qQ8`43w-n*uT2g=;M7y`1Zqc0?7iyovxvxn_}3Mr"
    "R`>4(u9T$F!1LZ4Gz7nP%j+D`FjvO^NjBHUIT77Bo5QX7{Mp?7h<b^N0`2AplMH0P>fs1~a5Ht=`3ZcVfq1?c3HM)n2tia6x"
    "4;@Ci;)~fqi%86L`d~@ZzM1$om=YW)m^=;(bLvpwCfVaJrIf3QKWDN8oQp_{}dGPL7M{x&(RWwn_zVc*ya#Upr}}qV|hZ|ti"
    "r7SySd9Y9XpBwDNDIfh<uK>@ArHpm&XUc*fiC7k{-zH^|lrv$i*G;yg%0Ok_OSQ<&UHHmtR7#&r?oGlgryLU^`o*e+UR@ZD@"
    "{V<@eq+|F7ntP#yCH)5QLVY1n$-4#idbJi*{QP?iEKk509FmF1i|e(I@uG_$ujT6-tMhT4~K58PNGKI=&xefZ&y+Kyc?rmNY"
    "&s34gO<rAI$CL7)TAPIh@#?Jh{JjJh1M{90wehvf`KQ0S$NT2BP%%l&*r<moeB@Fm0`}G3(#G)5d7+~j8h>)f~ma9OLo)+S|"
    "H&(!Z)s9sz3mglmIh&B(oSMXkUz3?x2z!yQeJ)Hjig1YPF$SrGPxl$o?&!q-HWn$h)R;Zlg8fzfejjFt>xlIS%W}B{v}c0?u"
    "gHMU`^9IuY088Q?VuBpzZ;@2*@?NI)au!ad40;&hhNQaRUV;Feu>_LH}TD4%;;yo#TS+sW++)iT5MwzW*>&#`+hu;jbBJ`*E"
    "1yeb;1X9p=JxpfC@CAtSGMs=>3$qeDm6eHR>CrLwA+#n{&P4RG_#D%BGjFF;a+2TP>!Jv+Y7hHbSeBpR@!oe3<|(E=1uq^<+"
    "Ki8c3-RU9F^!3Ms%X1|r@WeO~a!Dq)WTNGe!-8E+L({}0Ql7N2nHyXa65lnCEvR>^PKGSz8?-;8yC#h*SS9YL?Usa~)=Yi+@"
    "BZ4J(tkOymic-Y|)TP;D|Q<R$M%D+CBjDtvCnouS%v1ee4Du?|+&K{qI9R{dOVI;nbb#%R@)NjCE=X$eMt3hWq8sTfJQ$I}-"
    "L6qnTK!1@wDuWWTe$}I)QLxzuWqu<sfNkJp|BB|T^tHkO3xxqfwMt5R@6?$vJsQmM_c7NNy8b>bWQpLZK=r}u-n3v^`~b07p"
    "HbZKI$bB`U_=CO)}g*ji{)n>_YK{fkAq71n@__@^;@9~a=1uy=f49>UIYiYJkTNYAV*?p(IBoahg&6iLn~&ZRQTQ*VW!#g&~"
    "^?@BiLl}{2XgXpLSLJokb=J=2t?c4)4VY?``+Zj^ant0MDfDT~F^tDH<`L0$OPK0+c`Q#IM)CAVD`R_+`Tp+fU0-8?Q*hZNs"
    "b$GkkTFf9BT#*sQexfA(xemutA4HE`Ei@y#IP{KCTiNc(3m75ZSZQ8-pGl@1zd5wa@^%*P@mA)bxP(sMy&7zP|`L;o;MqFNM"
    "@6;{hBm5}f|0+U?!xXpvzDZ!m!JfD^pzs*waDbjRjz)OSh8Ep*3<Kj{N=ni<{V*-ThE@jj-@#dZ&V=lwR%#{YwvF=0pIy;J`"
    "{cd^T-2<sFZUmmNOlDCx6)`AK=3)XPYX0XLgyZ+MO*Z-ln5;Ha1#`}yxk%xI6MqF($N)jpP$JTq#D{@eRSrW(fjUg-)U7aA|"
    "Nj95;fJ0W;zQudvPu8yDpw#se|!Z7|FW8Hr{W;-EH))ZAs606>wRGSDB^A&+q7B4ZygEDUDD#m!677Xxe*gkGh@q%T9FXNZY"
    "$=XLpDimzqirZZ)jfEFx?YrOj1%1l$afj1>HPkJZjsd=PK^be`T+J*Gu@)op$3%PT?fEEiet4O}d)(fvkOQtJZvAfSPWe{5v"
    "aG;@|9eB_r*Lgd5)`;#4S1&n14zIUaO*^!CnE=L>zl2It=Rh)#;6MZlr!%zW=x-B^3nb9(y<X(ATpaJj1MXBGxuEV^+wM`|p"
    ";p%FkNf`-|5DD!W2R&h=D@?k#MzubTF;e8%+A+W_fm^?IQu+$5Pl~t{^1aH_zR3kl)?jY3BjzTICRh|G>(TG5#xQzlL%ygk5"
    "t&l$!Y>AWJJM92|V=jBM!Sh;^LHn{WFa(@6n>^}|!GcsuCH)fHr#u)?bZLo#r(wkmO8E4Cffegd%Zk6UE9&@Z*I3n~o;k=Uh"
    "{nz|T3msVT_o`Hm#v_W?h}h!rwF60S24iT>=KN<Z=KE|&$9^F?bKg}1p3M=AMs=bf*hHUQhgg61Vpkmso<OBUSYw&7co@BB9"
    "l0J^m5FHNzA_2mc$p0m)W{KQXktQz+ZEQ3_B7WziWEo3RD>qC)-kYeYciL<aqnUzda(;z=6CbbPQnQ3Nxj9R>(&y`)c8L+#8"
    "D{LVp6;4pkoCA~VTMQX?nw<|-66lGV_l^6ZrF7iHE8`Kdiv<723<1H1gI!zoB<=&nYJ#>}#FtL>(R|59L5+aefx2&K4fzs0v"
    "}#Bkj8SNZ@0mkl4vK$?7nWr+o!d*Ex3JKB6ujjI^x=&FxD8^6_W73fAFz)a(QS6MmaY#MSADB$~Gj<hi*4_H5eIoTIzzQ;8#"
    ">sYUTtK=CHb#IRXyxT&@^J%_3eHn5VmV2As>D3s2K(YD`<wakZi&*BBNsd@j{19FenVW|{>1=DPrp?IGL#L<%(xh@eS3=(Qh"
    "E$Tr^+tgZcjba7wyv}~6B-I4{1Gj>$jc(XLPd;i{ua#oL4KEuGXWzRS|F&DCtE&i8&Im!6qPa|HLRh^0loZ>NnF{x{&3NE(n"
    "ZBx@1^jDUr}Ie;;cn(^^%Db<7NY6|0%!!P7^Vconc)O%^;4knfgk?p<@9%1)~)!gv(8&Xc=ociPBR?bEWB+gBqZ_zFYg2RcH"
    "Z4)0-SBH-uxVV34%|h(-z)@18JCHD5<BbgvuS&gunM;uyeRLtW5NmCK^a_Gr5yU_7Z>Zj10rxXR`i!%fV-AN%Pp&nTPy)|g8"
    "gJ)1&SM9_)(S_?rPay33(Q4B{0jAbvwnQ=Qm7g_^&TqPLp5iFI?Q^!s27`V8%=OxJX-1+D0#z;N@IakErbY<K(o-3=dt@t<o"
    "DtAy*IAEFe9be+*pXST+`?HPlJ5ra_3MzB8IfIu(6T*eRO7E+<hx$8`f?F?nhYAVK1+-L`W0c1r$sI*HMzue<@E$vk?}7Va{"
    "S$cYWOe6Myi^D1zF#JS5Zid)Mxii%p5V!*&1*C%2wXo%UD8!pLocv$DN7L2C04eq`AcdBHCxSBBY6oVihY1ll+PN1Axy9qs<"
    "_P27>=$?ZN-gyv3>Ox4*x`emm9EhwvLZwA|uSFg!YnovU3}{Kami=c4R*K^E^I>Ox6K7rOL4porxKt7|6_Xw1lN(j*wR-JLg"
    "`0REg0KsMBPQQ;luE&G{x|LnQg3QbCWe_vZC4!7FXZIXY$P2{VA)w{)-3!!A_*<n&PG{#~H@E^#p-B-Q(BJFP<Sj>lTIur1E"
    "e2_)}@&=YZV_eG?eJoFz+tmVcW(XRc~x4m%SESe}x4hK)66l<XkhoLd=XK5-@vEXmv3&u<q9XEzySu$J1@Yihh&WXYwkC|51"
    "R|hb~Uo}qi^!Te3%Z1VBq5RuvmZuMheexZ4>=fGH<E4v;DMojw3RMvZHpPT|{m9&|he#_^zM+1#SQbK?Esyl!GxiU1!Lf_mw"
    "(GA2Uwi1lUEyN6R13|1j3JeLAEpHV3DVvJn6*&Y?;-Yfh=cF{dj0tdnANB9x~g$$;-NMuN*zxLJKkqMd?g*9gygw=FYf!P8f"
    "GD#cV4*Ty@sM$d3R4plAin~4IVnB#MSf|V7(T$<M7^O6E|d)ITVYDzf(4P+%^MU%y@J772ajbprUVPnaS-dFR<uuv46|XY}x"
    "+>_F+#w%7lB)M(zE%#nGIdeakX>AO1|XeJl;|GjXf`$3~nhnAMxqz^QEn5l&0~_t!()n3N8`+X2lPefHr9|6|fO)ioPt=PSK"
    "2z`59W()xy?-RJvnUZ%gPueulYcJ&|LzYce)F&P}oHi|b+a&7rSP_1>Fs0aUCo?u@%h!|L&!xbNfXClJGp2LSw?>@Ts98j@5"
    "jxHyk7EP6^${9;zCMp1x%7<)CPF=DA%EZ0;Rx9f!!;tm1@Zo$xN)@*Yji)#q5i^Xw?05fDR3!bD4f{FR_+#JfB1ND8e-!iR!"
    "m6;irbR&z5*Eo$cr}t)wYK{&ArluOK~=_H>0_SK5QPrp44X+6rnfzl1N?hnsaVA6xl~W1sQv3moFxE~=}a1m48H##HmKWY%?"
    "45fMTN^JCn481Nl;f;_!oLvd5TtBEani^qg&>a;jR<z%~CzY=y3T)_s^yM=B}WY*QS}GS4tm>_9phrzP*vzqwZ@B^Uh?vm9`"
    "}oEj`h&0^C|OR+0SlB!mT?zX=X(kMYX6HfU_QFnmtdI19S~($l%VH1+p@VBDUB)-c4f6pZg^x#O!Vt<2PTWO4;p@(|44L-Pd"
    "ZtvkB;>usTB>}(+u*)>mngpHueaMvQ$&ynOx&pl30;^KTy!+7OEUQq?B=`z=nk_B9TcpyR&-rX9*rI^d{iZS#Bf&oJSDG>d4"
    "W<bcg=`;Gv>^Jb$BjzrL+?|$WUyJ3LB(-Z)yY<f=X|<wZiP?GHBoR=2N6XX*bkTEcG*atpy6bZbJIDL>s-p&^JN8OUu6ynF3"
    "v3Tz>n3%)5eBH3t;=U!h_ot0s8>ftDiDE#E&y=>%PU6^BlHE8tQ`8hpi*RMe07nTVgnSIWqAUGQ+z<EVITh$1tXp=zY(G>h`"
    "qlotS%nVDdLdBh|VvXPwJziyA3d!3-vB-&tqKt+!KikZuKNdYqEfyZX$E~7*|Yf9e0(Jsve@gbP&1x+wu(v>c-UtdUx9mK}|"
    "e%$(%Y*x=l<f$jdSNh#7qgouTQcSR4<3o6Rx9Z+JAy+HgL8a9iBi=KO8kHSNvM)>R1fS%zW#Yy@!lD1L7e8xb;Jm(z{yQ_$3"
    "aEv6uskhuNd9BTLTgW}5aS}!g!8X{o#CxjRkWiwp*pG8rX{>xOSdTH%JCSS=F1%3i#VkX;6aK3&{H8rWmH_c}&#05mFkkgl`"
    "12k}Fc8E84Kgl*WfYwl?Q#Tv_bI2>m>AO!Nz1ZGDvY+!}F^e#wk|ul^;sV*;BL`zXbRxz)uA!gc;;ddFOQu9jnia;QpAjR3x"
    "*WWpGU=6x-pRypjtak@jU-s3FPFgsa96<SG7S%WnAs3&OOnmUM`_>*dwgjp^~~f+Go5HxCb@+s3TLU{c!)%2wAXq4pdL6$7Y"
    "Qr_-S{8n0`<jp4>+BW5H^>*dy>ycKnGx>82Vc@D<nfz4?xZ+=1luH+t>W3w5D&%p^T3l?BOjoc)LPBTd6g~_Ky+pjcq9*4HZ"
    "$qlE;MxmGGmwCSyn=z)@y|63A>kyR<y`zAFmc=1!9479zFUg|$r*z;WK^!D#-mlKUl^Em(n4j>J*b!y-6=9;c$tc`xI8D&wa"
    "{t%;Dz7Qd^UIfF8hjr}hIyUEr+jqoPyI!ZVY1^i@`X9LIJpWPnyqSDN+>)WJXko{r&#{h*A<7&ndX2@TqPDMwFIH-+9guY2{"
    "|0x&j_Ait8!s0>mBlqtI1$;?Eb;Vd+{0OEoZFN8^J~^zwB`~aZ=)2bXTE9{bqjkOLXfFf<Ss%2gHjAYnQlhK%_<_jm74YJU^"
    "taIRM%Rg;OM5R<Im%Lc>X;dZ&xebACu>g$7PI#uiP{GdsGmzFXTB}-BCcEsAT^v8%f@TTO~iG_WjH$c5e;NegAvgTVt7A3oy"
    "Nq*Xq(Y{6jU!8{O=U(G|>y95&YX4j)>L5ubn5K>n+AQmfYJq<RSoTU$a(Sih!=zV)iQ3K7#->0b5*UK)P^&3>xYwb0{7^wO6"
    "S_0%-#J%+bmt#0e?z{(zu6;0`@kb72<qcsymJ-~@rPiLCIC`{L{LT9L%ZIJ*OG$glfLc!qXze@KU}AQ9%e&l>sR5P?3Sd6K_"
    "sio6ou7f#w1NG0<?@L5))+ys8*BQ*BJ*y^Eg#H~z|aY}LwB1gENvfC;|U7W6()f+WhryBDa@nF1^HNzX>rmpSuo-MqV+idt1"
    "pH9WA&!7a-_=Xq@e38MhCWSOtuIl1v4i1VR->QG<8MJ|=Z^5p62>LkbZV5ktpX0p{EW<vWKYo%2)2J(|gQE(19RB3H;!ykpd"
    "#-D+=K8HOD|*<!%^_z!Y6a#78KoHXa#1IK+zfRJH~l&$BRY|hygIh<#?t|*)8*-VxTbo)(>#gI5gr^Pcdwz+)1fCHh^gS<nI"
    "|{p*z1kmotHDTGRXsn9&`KFwM1(or-YaP4H@HWS|xeO8;^<~az(frG>)zMbbXM(tJmMRF}F%_y5`?m^9`^{OP4qpneG~x*5`"
    "jFjvj1Zul;)8TnRtV4B|t`PxQvMpH+NtzVPXzf46L-)Q_)BTxf%Rv%vPv*=4&H{6ux;;^Ou;+ZgWCC65$&DmVS|_yU#whhn@"
    "VFc-2OJXH-|DbX+|IWK-nH8vYfz1V!j0>@V*{mzFx`0|e02k5%s4Rq~?tXFnoIY)D)pF2xDHno(Z3Nf2+E<-Udc3F`aMVJ!9"
    "=N2tqpreq~(9IQLw^?A{Dy1IIjCdebEGXA{niak8hxwb>z~s`3UMq6iX_**}{k_X&)hyl_Wv$iEjPG?S_~p<ellM23wIU<*k"
    "mo8kD_gJSQFW!}2{pdVH^_oj!c%Vp-xLvuHc3J4_P=edXQn@Q$x*)hbQ<kXL$$V9{^WCcTB2we%@j?)hS%8f-%eUU4H;;2mG"
    "R$NJNzSnAOWcqqdTZGq>Z~fLLEu>r(CKrD6*B%h~3DkgCzQ%<~@Y{)#k%vw_`%NAL8nD#+_QE9{mGvbmt1YIyoDT?!t7=05X"
    "Z^tKLs63eQs{f8y0P%v{!o+;c91>Z$;ZW_~{`|1F4~T<&XGFp6R8Uu*R*$7Y>cMI^Ag8sZrC32Z2ir^spQ#c=ds7{*gSoPIl"
    "vZ991eixO)nBl#3!^*EF^9<FAYya`8$lOg5A(sxm`bC!S=^*s9kG$j|lK4=K<a|3b5Cg1e<SODYIEA&2#ktl8aaW*ob6y648"
    "z5UCFCW81TB5WV(qu4)bFb|oVW6+Gt2hc?+Dx77hY7I3(fwO)2Z!t1GCudcjY@q-eBGKDDG?bNBp`bXQwN9odOikHDUM#kLk"
    "GebP2H$6HuI_~J&QU!Kph`g@iTQHyIENaq^v<<z0b@@SvYST-!rkqjDEmiVU-ffQ0A8tuTcOEw?#D*2A~_z3FZ|K=sl}>5S~"
    "1N3r4`m_xI`9403+d^V)wN2fF#xMI;X>7?=Fc9aLuDf6NC)5EQ?trzXhJ9%$ddP4syi<fAk$_{)L0{Q?x$g<(Lfq&$L>Un1<"
    "IqcyV#9@Z0lA_5TuU!Y4nxo3Rv`gx3;(?lCQFmvWu8_&wl~mPQPt1KsNHC<B%#M6D_GTKM1Q_S(_P;P1?-&A^Y|f`&?p1%8&"
    "RNKGCwb52#rg(G~gt>W<#HYV=Rdl}_-s5u<s{2S=eUnRs|lLL9MH&VY`JgiW6xB1gpR7J8c{#}X>M;JPgpD$$2CCjj*G|%-J"
    "8{^@$Akx}{GLyxgvBr_9S<<RcpALWrF1PISPg|+T>RQ~C8!sX8blyb<+gILum)0kh{1q0!gniLE+h-R1fPvT2vM3)#1W-4z2"
    "Fdt}XsZ!M@cnteh~j#U3U`AO7Vql4r$|Ufn(hM@b^teXRKUt|*W!#usNNq4;;3|<%YN#g<eE_v^N8B^e(weKC_Bb-3;A{76k"
    "4rDh94w;q(60L;Sxc$PZ(hHd>>+qZ^_Nm3TcXTp?hQg`m@!bnDePgO4EmbcLYi?0zdJ^%en0$R6Y|UTzA>u%pAvv(dhmX_fs"
    "yh8w$XMCrE8j7x`OOPJF!2{ABW9->uq6xTh!?DJ6<#pd{x6aE2&TO8wmHR?1Szn1}yvL;EbS5X2iaabOrpAj)4%rcfsn5#?i"
    "#it4~M<X9D2kd<|L+Q4$cR=7(;Sy;P*bC6(~PLECpntGY8?7r$E2hc*#dXe5>Cv6T52>;S2l62bbQw{0`Kjeoyu1!wbpq;Wj"
    "F0V{PF<!e}1n%x%SWW8%+)=8exYB>7>CN4a@fT0I4A^eKrb|*Yzsr3MTV6HWG%zq^kK?ChBantPemt^%3CB*k?~Qj}cD$fSU"
    "ba99AA)t0?s(o~&Cjo5-o{OeoQX1xNgA(T0Ys#tec2KBD4XS4M~!A*U0qq;5K(&OYWLJW1vLJ)qezlYUIPYQ`h~XBhvC!s@;"
    "fxmQ>tY#e6czi1O^8`g4Vgj2Piqc35tP{xYQM9vSDBu{KVLQ9S6JNu<$74l}sBQtwhhD2E_al5{tX>acDL!X!dLIuXR<V$vu"
    "{HBsL-5#{U><Z6DukB97&9yMDRrdYjgvkaGR$`~VsXM-Mo~{%+h0F+q^0S#3j)`+~$(3BMJU?IgZrREI6)@A-VI0LURvA7tf"
    "`kS-~KX<@A&-78zGsbJ~RXonjQ9zZ>jy=_ARZ&3?AD=iBA=vkuWveHWk%wse6Lcr|QQSFlk%3|~eFhZFByW;I+dxx5o`F6pL"
    "bWxK=V+jYgJ0D<Ze^O**_*ABp;)?-8k@5BVHzwOr{{kEVS{vG<=n5ozUB273&1$9*dbCWfSLu6h{(fH@nSakw_V~7`rDNKtU"
    "PSqVx4h(chwM5DX=zJD5^vMsl+BpnE1+b4&X9dmEEut?`13o)5vz2b&9^<NvPUNLzGYj`1#gJfuX|)y4}VNEuqX01d&t_tK*"
    "bcg^1*~rp=;i24!GTGi$D3;rGMrP7QttM3+ptRChKZ-SxlcoWww;S(JOew+BEc+v<cEo6g4F%(GW?~o_h^4qt$}Opk{G;W1b"
    "hEVEo%t<MohE66ZF%kkMKOf1=hRmMPEV;P=x+Y+=R~{f;{F64vf-mpyaiRt9u-&LT8_=WoOH4J$b>zw;i_^8g#CV?=3uPYLw"
    "c$q`o^Fz61ib8QV%gba4vS5XOT_zTXpfW9PaS0O4ed5$Ey+uVWktgm>hakkWHZ>Il9i2w&K>ekK*nxt&izNYma+x6xfXvzRY"
    "Rd#$PFMFERCf`!l2!^5MRzZU=c}a6{_!}*YARqVZxsE&O(OqI@&Ow{Vo0uE>0N8cgHI&=HrMP)nn&p(9Rm%3;*vZ(PSk4&d="
    "PcjpOm31-Uc<qI51$?UyQF{@3~_+&_;5nt(k=}t|D8tePB4Rv<hTk$!?!`8*i!#|)e2!w1f_CW*sC!?`03qeafeSOR@if#W0"
    "5LCA@u0Oqo9p)Xh+}Je;&}&+0n04xU>8+@A(kwRs&A&(r=hi!0wW-k-(V(i+0;t2-wul<p*{0&L8OJaQ~|vVY|Ox=O`IY(Ce"
    "gZu$`(@$=^B(?XnaF;L=bbjiTYoYQKg?fw_epR_>Zb_)wSi#}@`5Pr(JqK&1=S-l6oYf0O9l{m;Rq3b)sg(1HEK)1j0ER!0r"
    "LIpnvSQ8sB}<Tp`I7wnRGAr&+e23+J;ewIxs>wLi|Hlq#xJ5h=^`i|t!Hy$w94R3JZuaR>THDG9TdF)gov)_xu<=(JEwebGP"
    "Zu%HFZ{&{7<2QY%_^!5KOC@J9va0gt8oi1nahc02`WB@VcHYhVD=;B|jx=~!kpk*N)bdc)<za0W#zY3>oIdfJD$EwKc8fpdl"
    "%tHapRa-*9x`?ZUEqIkT^N%$9lVvtkFeS&o}GB<5juN7Ddde7qG@OW1d4e(MuV;6>Oh0!a&0u$t41*f!_&1aMc(jj2dDrM&M"
    "048X2jt9l_|^^jTj;n$-n5CCY1@TMWsh04k8$S8KX=rbwEeMpITd*1{;dSX5O$X17z?`(|Da9(3YQq-b#jo+x=<C*u6j<T)M"
    "wNp=t!vhN)AUbM@8v3>ayg;k=m276Qu&(MD3NQss4U3?t;cE!+@7Z$9%eQUUYo58~<;*D7C-RGZr|M|4BJW3;Am{227DYxp8"
    "1(Hb4O%4OOi^s#2Of#Jzh27e9de<v(P8AWO*G!6hi9@7vZ&|F;GT^!5Nn#_*WYSv^{Z$*(<kGK`IT$%Gtw!8kY(9`v2f035e"
    ")Kylu)XW<Zxn_1q+I8OU&Rm#`x^n)fhe~BI_ct^8-#N_XwIZF`t*1fxz$Yj}b5R|}#M&e?==CZfjGkKWz-7i>x4NG*gnRFWQ"
    "?Ijl$mG$fxIm|%`UdKYw6mbawwaH^CKNzAYJ9pT<Q_VnZLd71=H0`md5DI*I+_B5l>s%{N5hBSfQT6q3m{RHCaW~Z=wuy6()"
    "^-y$sx{C2BmlU(1dCn6#gGl=0}C==R5%Y={Ku@q8Ell9zhSG50w5HP=SBJ0f0Y38EmWcOe*vWr?H!-_wL+kRMJvCSQO@z4Zl"
    "bx$;O?2bZ}!{PTMXD2z(mi@I5KE>o`Dr{_b#jM;q$R<A4^$kCY1fZ3}gTi+@*8yl{c6g(@3=B2!WZ5QeR!tCi8Cb7R1N97)O"
    "cLf%5ltL85jZ#bh;af_>IX7a2;rPN*lmg#!38ZIbf$$kXljB<;7FT3Jm{<OX$`5J0hWRQt8={nw<`aSXcK#Ytf5j}c}Q5-*y"
    "v<<r2lq*9D#2@E=uKA)R5{2{Rv+E=TH=Pvh?)`#u)r@iR^nvE@?N6=tmHtwIzvc~sJ8mhq^wBa(!$rLSt;DmFJvN!hzgKEn^"
    "FIDrChuTWMAkb_n*&~S2Nj#G0i}nzTOOJGi?tq7xRShF61@?Z*zvL*)0^r5GI@L1%asZm+CIn3f3GxMeQZdmMkYh{+O&UgVu"
    "ZPBc7REGH2+>99$<d3v)_v3&OSUV>b&V9Go5mvB*3@uRq<-WZ$wJsf@WnEZ`JqF+>?sVXIPSJeS(~p2ndnGX#m4r-ynzR()P"
    "r3Xu&x%OBzhZ<GmFj)!v8bjn#6B9F6_>`Tih-+U@_wNncPJ0IB(8NkdBG+XxU(m1v_!KSx&vp!cDTv_=&~^vTy=fFHJmTHo@"
    "Ax%%MU^7kg|SJ<OudE%$45g54t-WxYX3ZcIbA!Eb{nO6dwtdn*GZ6hJiKVTa>SyT8aQ9*eWbdXQ!d%g+U4>Hi6pKfWifCr}="
    "2lc+&{w1hmIfl@q1NI)n5D%?kU>KD24fZT=j_|t#)~Ni!7+ieo*RLXfbdNa^8ugNvD3@)4gXK-1Cr&Lr#=d^rINUgx{!0jOV"
    "ak5`jsd_MJ?7?G&UA$HBPFl%c4}){fT-Sm+MKT$Sone+Y--eZk9WRpR29mCXU!_TZ2U8}sOCi~{{N)@jt?ui>#6>W0c+s~hZ"
    "osm-KwJzg@!r`5cIhrg_t1yZuY3;C)%}5f*q|h122AIB1VNzX#n9Kh-V}tmI*K5jozfaZiunE+-Cp{eaW46C2NYHG;u?Lr*X"
    "Aq*>s=T*-CFoSM^!^p=l8g{kN&G3k!Xi6+jPVCWsbhR*AbU6?`c&uID%z5HLAL8kHf-(llv(Z-*2?+}R;}QS;$>pHuq2yN#>"
    "6j(6<P3vdG-CV0{9fdke;3ZcEX*?%R9E6U?X2H^L6=fu-SXKzn<KMkbBR66qFw84OPy3$EW1cc!fEH?@2NoL-Yn&$kw!<!PR"
    "h%agW1`w>y0lUtig8DntS}CJ7G0Q9*UJUVgzG=bWyi;a2Pe&`>mF`hZ2K5lEMVfMbniP7ZFB*i`EYM@7FrRjg>1&Cx7nb1Do"
    "F}88;@~wFPR7deBZqh79z!iQftd~IM8F$)@6fj%?C5m3X`0<gNuo{lI%pwpp+{GGfqrmC_EV7F6v?3{52eCSUfHcWX6SG=B0"
    "I8V3Bo83p8g0Cer>`G`VEp6@|B{Wl+-5NkZ1+myrMSEDV$4Z*8JpG5g)22y)5EO2&bZz;hQvU!IhE>h&m^uv-oeS{dl3w=Hu"
    "P^3lS;418Kg<HO5@vqg-EyglD&g)oF*GH}X=Fe_Jn&N#zh3l#CJdYuik54Xg_zMmTBS<m9M!6vstA$+jGac~U5q%TUla#B8C"
    "XQ)}n;mQz%Im$hA~Ft9u^iZ;eK_k|;US5&+#UzXamDCyPXpd|U~K36MofABJw3WP$?DM?5QF_W|kwoHh(ede9FwiiX-b*Sl%"
    "kP3R_k;nLPG1!q;Is^z~H8Tr@hE8xcmJRu+pw%Hs)6S5I0*JBk^v|CZhpu+^mT@lD1^JH){{E3_f;)xJ*!&!no%>0pOe8i}w"
    "{WI0I?8#W_|c$r`WM3~{6)3hKdhzWnF%H@otw5jzndcZW7;vEo1NJdlc8Xu>&?c$14w6oYa)=s-*b7f^|eEadH=o;d~KpzAu"
    "IP0K*1>@(wbiTs_4z~k-2q6qC!<<N=2A$PG3338-1(y!4D+CMjr+d{`<7D`+meBm_Ak7880&-*4V?m{oHy0cJFpvwg>cTO8&"
    "i~z(IoAOs7Jg4SFgryK#Thatt!1vi1e>!BKM6nu9G66W-yZO|g)*{#1F8j()(J{FJATd+6$K6FVMWGW9{n%;fo8k*@f^K4a7"
    "<+h-4sIaZqTzZT8rT@CFKh|A;8Kl^o}Nt|jMNfw*BFF8nG*u%=2fiMCu&%p-P+VVB34~&3$m{8I7xyC5~wRJ^bN7+v+@)cTt"
    "F6GzGO+^rh8${03kKYssnl@(yEW#WSw$O_7Rq|4>=9<(;{WSxTgi$Kp>Q+KU=lL&1+zIcIv*+wV45Xs3;Wrx$!K=$VN5l@uo"
    "TGj+_~X=R^qU43qEbY&7t2)!ZXTY*ZkhDIa8r=C{xH;$rZ5SSPu1N&4W+6uNS&b-HsANs`}a^~>RsYdkZj*pqOX`WC(_R34m"
    "i=S2Z)4eddhnVVBq%o&|v-EH;Apv%s~}@GV|sZrt}-}T?s`;5=GcpL&DNO8<Tu8pA-a&&SH9(;N#tUU-qY!`_{E3vgFpcOR*"
    "RVS$}+KY#;_2K-fiS!%=nY)uGzIk45%^?{UJ^V@Jr@S(rvEPIWwr2K`5SrMxhh9WXyLM?-5i)qGRzDH>;vG>|k&LpVN3uHQ_"
    "duKQwDdE6fLh^$m3nZvHRd2XQ$@S7d2w){+WfQ+!*d*t9H0267e0Ph#66&P{9Lo9*u{^wM*r?tNz0&KlUG+h|lb$a-*#yZIa"
    "iv(WP7@jwBr|B*Pwz<KN+!ggJV9bl|WH$rR+5g*P9(n98nsuY6;GJs_F@qQB8_ZCiA@!wDno3KZ*RV@C4ea8CqU9;A8}qQ1d"
    "2(To|L04({rB%i2YnqQFBfW3E>0lgK(ae0N8UVi#QuO&PTqm7q}^M6+z3?ke?(pLW1Qd9-E3^zjg7{(+Sq7g+cq0Jjcwa*)H"
    "G&evq?7g?%RI8KfHg!GtZfO&zU(hcNb|Q^4BC!gQMw+r%J|%h(3#`(|VI)yQ53!*6=v6ZfQ`8WZx5?tq?2xpOMn*Ap=W7qcg"
    "cGjUwkV6T(re;z@>IgcRVpi&Url*=WOC>!DsR10Hg4r`FMR63kut#=GmMdV3s{`2yG?@5yn;U)}mRA&7S)op^8i(wEV%om|d"
    "~vYq2tF6UbMw7EAOi<YP&D}_@mX#>%tj4`qETtkSgj<P%k?Wf2-LEhgyg&OhJJDUPk?;oWhY5zV{qA59q!mU~=1@1c(XuJOj"
    "m=TIF90#)>&s+pN;R-KQ0+h~9s7a~*0N;||APh|MIUrYq_x0N<A6EJl21mh}>)_=tE4<w{X(6blT&<&J?N%$Mc0_T3z3)tyH"
    "FYM)d9pyYOnuxib@~T*6!r6do(@jVkb2gyKV+%)E84La)nf$sBg_z6s3=ACK1K)SrF3<!+I9w{)xI4nNKQejNYMFyC|uF=`2"
    "6ezBLIZQnsN<si($H+0*p+w?i~#GG&_`y(n?WY$vzQ>{(`nXO7sfnsVz(+U^z=CAU5TO<mU?wDl6k%Guyf@<;zs!nLDx|3?a"
    "%20AR$8<N(t;PhwD_qW%$?w!D~;Wb$X;$|rJz{O$-;!yYPmEdc6BuMa26z`GdObSGpxU5@?V`fJpJR_ij-OrNzsw0um6h6le"
    "|<{Li@0>Nz^L7KLWBh7sv{TmD9p-KcW1Be`!op`i^`(w<%cH%v?c<tPe62xGoWKVZpo8oP9mW)CXNW1SBe$#x}F<BRo@8pD$"
    "l2tkygZZo>E!9scF-oIE(Tkp~{;S{ki18a^1u7C#!YEH7oaaW|zbk!K`9|wpt%yT~ORw$RasSPrrBRDR6ACC8FZk9>2rwWFF"
    "^K*9&=bzGoiSYY!yt&uJ8fTPmZZBcezA2#S8?ZTY;%M;ZYJ}|jh<?}8=$8bEeJZH_Hx4M-WG6&>`Ce&+TtC*|Mz;Hn=4Vfn4"
    "5>2q6quTJySfOA?J_Vrj46LssOxZtc<@|+xZL7hh_vs!mpNm8m^sTFU6JV9l~gBY}Z3rKpCbDni$_=!@r%pcpV?VdS)#qaRC"
    "-wNh5rT4Y<DXkb@sk^-4ht5`s$9zNoy}-aeXntTxb|W$Q;@DMu7b3qUO`?pry(QG(YDSQ#J3j5JVliz>k?{!+Ok-yGb()gKz"
    "!y}lYI1C3;_<K}|7<k?rAw+Dt-V;*nyktr*4vh<dIc=&svVdzrBh_8<Q<!hh;bJD#)@Y|<fswM@wCO<5qDxViDdK%{sV5dG7"
    "M$!Skt^s|1vE0zb?fdvgl8%8<Ss{MoyIUC;^zOt~w<L^wSGsd+M4_pRHHtx`mPx2fjhDiGzCA(xqW&S~2Ohy@maPoOXySaTn"
    "h+n=`}~lh+6jI?_tOv4n&<4ks2VlWxmW>PLpt!e{HraYe7~S~0ytEw0x~A0f9ok1a@SHGa;6$8vE29Rn+FCW25qe_7#(9L$l"
    "<o{!a;$Bi3sU)P*6&nedFOsp440OHymOmu#s4_p6X51ec#?E)ZeU~gYDlrOB)Y2ef5z~h07n;0Z|iM&RzuAuCCvEoXA8sx?}"
    "RmS@JGYswog0!(sslAq@$*=$cS(S(Bj2GtM$r!*E{2hqiVMSj-}^;k8tID0QZf5XbBcTGg+IEc8sCBN2QmL`s4%ixY*F*^-0"
    "p*#z8_^BzNjXMufwxC_PmPv^tF9osfH5g%dRqN$-^c6&cUJz>(Lf#pxG+B53*mKT}NbfbSdKsUA`*hMQCsi2$krBS+)!Z_!^"
    "L*VJpA7$g;hl;*rU~a2lAMZR1Q@cEBzM<<vzlH{aw^nM!<YA?GDmTOv+2Zgz6>X}x^~8f(uuNsG+a6v$cA)~x9V%c3l0|hgc"
    "kDl+Jry9lSTCBEX${Anlbf1&;Mvx~<vG|H+j}4S3vr8MC}IB9<1oAYL<YK`Cv$VejPi1o%0-oGjilti2~orz;?CBl?t@P}%*"
    "iKGH%8c#j}N=e=IhVqt2D;Js@k@PrskkHc|4n&#$w)VeOtpF!*{eYhhz8CzFyM>0fZ($AG{3Lxbo!Uhn2E~1a4{w5<F*O_R!"
    "=8A$JCR|EnV^4+F!h!2_+0@^9c9Sw3=YjtwQuQc@{a({5!+TgBv}w35yTS=Ed7nOgDQ{K+8^_?1n}=gXn_-2AJ6K=O`vTlQX"
    "BaOWSCS#S4#yDtUba|397C2LPtDnrF7i{t6elhh6kBmYE8ra@Y{hLtC0K>IgX>2{;XBk904UA)6h_NvtKM`c{`z;Iw-DLWC|"
    "lNtB}YkvN*5}Xf9cIHU$dOyXfO0>k^7&-mpghQ@1(2Rh$vMJEQ0$s<$;fm9ABU_Vgo7Y}qfXJ`IXUSQh*Y=>O=ycE;MAaA-o"
    "^@B%*0Ih{(Ni44dX=Fu2u=SZbL8j<?}(8Dyk4u%*UlB)zttVejclMbdgUE?uN?sQH(Oa3M!l;3sKa^@4T$==p|)Ebu`f4P*j"
    "*Vj#}{%=X0d#64+I<FpMj-e`wfucm`+|pAR=(0hgYxaj&LCmaX&2`(6vuB=J%lEgO36U{FCQSf>h{IaazV#D`+Slv4f!(if^"
    "Zb{>+w$%R6)97w_Y5JGmV4O95A^&|*|%2Y=WJi8eai5Lb?7ijhLO<P&{Rzo0iZcf!hE36f@@?~pJf44wa*D8@jeW?_!Itf}2"
    "Ar%Skg{z2XLm_<;?=#oWQViP@2ZU!=RnSEk{hp=JpGPT!^ElK$-N)3p_Fd0UhA6n;ZY<J56f~q3KPDnJC2i-7?+EYw;Cqe6{"
    "x;fP=pyO9`=fL)0(y)rb7h#<_IE=9NjZ5W0Bf>Ys7}GcKnQVsu&o`&~I7D+5O8@jxR=V4kLUcd2O6};w!?wVd&ld}Cq7)!Dy"
    "^~4vzSo2me6X*++e$-#;DCdy*w^=R*!d=hI0-mZSrdqOPz1a{T9mu;`165b;5)7-uT}$MxV@JM`en~#mFUj?hZFJ@BJN}Mk|"
    "5iU3mwj2q0ws13a(HNq;+{XO~i(tu82r<@(&Ygx{<KrUJU;wlo-!nl`7OK9PkK&VpUY6tkascZo{O<iodZGc_JsV_DWkP|KU"
    "uY&$)9|e?t1;1ux9o7sfMbK*1y^;3E&f@{6@%P45|wlc@l5J!bKhbN@w)va@4(u;^xQOx!OQU&c*r_XLvj7#tX==I~i^STNP"
    ">)7g-;pDUPzF^)FkL9arvKw*tpp16@iB|>jqzM}r>_A3met7BHAJ>pRWau}uFFJ^R=k_*WTNcaX&GI~G;k~NGT?jw`^@u&ct"
    "pY-4kWCD0#^fG0!!sMzsJmN-YCO<vh4!`P5gj!M0dcnP-t-tR|qN6>~eGbw~H%39?J)YS;dh>R8)y{>ns7EwKsey}N#5I$Ye"
    "A-VCH7Z{)gObF_H3*?Vh@|`vJK-AJf+{+vE!X?|(r>%-=Bv4Ij_j>;6Vwo!4{qh(U0l7BlS$r1R^L<8dce_vl@FUsusf)niu"
    "WSqFsTZ^=>?#EvIhI*5wI_RkO*O;qvO!6+)e0ziwfsaoNi)lMSwvX;(&*kcS8&a{%S|jQQ3WL0tfCwK}1GY>4RXo6e-KP17+"
    "8X-siVt!PXZ^sk-kOA>MgfFg7t)=ua{E@K|xw;w~VJReAAdtvGF@^dGiy#@&5V-qf^GSnyVnm^`h+hU8mg=regHr4>&L7j4_"
    "dAY~skO(gKG68dMagzAqUJKVv*Y4kXWRy~y|oJLw$=!E$DRaXYi;%hroRP;QS8`rJ09Yc&TDvJL_q^i>$wf`dMik!u$O>6jG"
    "k2KC=2+F($Ck8gJW#Gxass86(GLo;T<Ni}>w)0w9`nT^Hoi6VA@Qz2;Ou9b6J57jxejFa+x5kJ55RdqgW}HomQ;Of4#&eC3y"
    "NR)<*P9RE2fJ@qG+Ll_@cWYq@{q1c83Nc6%1=Z%hV7r7-U{cQOMKC~*aRpgBWX!!Qk>L<qi}e8nb|tSaI_%%I?#~5c@UHN4E"
    "0lL?=|l^5c9PQH+rSIMFxYw>@JI2_l1G_&b4Ch8`J6y(IYR<^;LV|5A6KL4(sNV0AKtW?+t?b8gt|Rq&-_WqV}Vi{afTa5p?"
    "m3)`G{ZD2Cv39Ap6>7kf&1nYMk@>&Z>SMrl(Nt||)KItm2Ye=e%OL`F@xY;zWmBtX|YI;Oo(Yy?Vv_yc3L1i2h2kl>2x=}P;"
    "Wb)?tM5G%+=`qcpHr3HAxBwP|&K&_}ACJrb@VHOml$J;_`m55V=*9AJVOeZX=_Ir>HOLD(mPy5>?28bEs%jsb?G2n)2=R=jV"
    "H9cl84qVk4jFdOue&^r_fzt#FM(wH=Qs5)Wrx)0tE*uq9PHiShM+RKpPMwd6#UwJ}MO?aY&Yo@CVy)#<%;pdXd4uEtbbPn`!"
    "SSxEt!UO5RB_OMD2Hu)@gWcY+&+#*@afC+%>BbV-Y}q~R)gzun3)`;>xo4!5n<7U7|G!Zef0jWiHYC=CYaHNwZJiRx!#aUDT"
    "LTjhw{*JVq!Z*xm@JGX(jugcI!#hJYT}$2Ld|U8^4|F6F<4QpnbbNDIx4p{!PZ1Kf&x79XUgh4pj83UfFPHbZqvK)hx|`xw@"
    "iy5@oD69r->6=gli-P&-^kn9OYYiKUo3`Im$)1sbYEDTcbBeRXITltb)iqnmTgw~Ol!mo-Tq9wIUlrcl{xnOI>|un^6lwC#y"
    "4$2zSMUhVqbvsD6_n$X{y(jz`-C{$V2?F>B}2*Zh@=jm<$E}9FRb-xGXS7)OQ-UVfD2)K2R+C}A2oHt4SJk<sI1qN2*S{dt!"
    "U2F_Su9)$U6KVI_?o~qG-VAaAC^jV}iwUxRRduEu9B6#Zix%!&>SXGJXZW=%7I}$MY6^}~(6<7fl8fO*UzrVdOZU<Q;O_e!g"
    "O$A@4Jn}Gk%^~AGA8A2-kAnrXzrh<4S|h@0oaKO5M`@1Y2k_Z-2r!%RgtJk^2|}rz}SMxt-(KC0IWjeuOo4#lwqLPGV$0PXf"
    "f=}Wbi+mYq!2=Zan+?HLT)mHhz1l8sSMe3N0fX*>)QDourq%(^U3~HV&2$qnq7}eS?>}-+;w)fh>u}a~bjBw~(!*vi#;S#(;"
    "y&+<e9!cZ3uF;zydP?e!`Sc8%JQ5JavBCR`2HucI5|^x$`}@WW!+0p_VwZ?$3@MUGa*2ccT-h}_|+2?jq8un=oP>=2hedmNm"
    "^IsY|YVz?!^k_qYdz&qisS>fyfhwPC?|CXDw9je4UNz1ZJQNAxVm3+oi_cxnt;>&WWT0((Nf|VI%JJYXx@_b#L8JJmdn8S*R"
    "e0=(^rg3PxC~OtstIlW_^b*xy$A&J+{;__+>}o$&{o{JiB!%frXur}wX8@;4k=Sj6&S)leb@p1kU(0x&T64ZRTzUkQg0jkvb"
    "&`VC!z+yAJtGd~abFCFCCWnuiS;*n#Y}qtVOaV<4CC1BE=wQoW!&Rh*@Ki<L?g(E#h2}z>BLx~jdQ|X8Qe&QuSdge`lTJMF@"
    "LGkgzCvoB>aA<S%u)XDb7e&6Gbx$LCXiF2*tdxdaFZ?;zLBrbso0+KpE4a@DwVkL36XIfSY*#s^(u*T$nOt796}B!GXR0#OR"
    ")$D#Zthts<I8>m^*Y2of3cX)`Y?LQ}y^Z<lANew>0a#>bevYY53Oh2`<YBhw^F9AfEYH=X_*hb(A$Pl29^a1-JtWsz)Xsf*+"
    "Fhtwq#f-NN9Qj*zgza^@aZV+_P|CK9kdV@CIp;wpS=zOh=MwH3g8;$$GjCh)3fbvK1KEOfg^KNwv{@*YT;RUJ|L#33>>i#@d"
    "2?eClONmi^+4_J4&86q<QhdmHqJYX14Z3}gTy0=D$CHapqd=$+u^WOB=i@xac}tvm|Hh^n>16B%gFh<cZ0tpXtqN;gJwm)xC"
    "<ZML<cn;W#Q?Q*UT5h~RKl3c7bv9sHpq9p6_eh)o_V*gYSX6tplo};r?521bonX>fFtkk4|xzkSx#57$!0-oniVj6E9|Ku9<"
    "o(9;M3{qMVyV0)n_VMLRxbUyZ^PvR?^V>7R$StEzSGw1c)H9b)$TKS}{*>kG3*a26|;$abk^EEmo?sz!pz0z=I)qvQ>NZB#Y"
    "=8+*Y~nHIzJX_exnx%HuD^dR-Zx*R+@&2{VvC*%q>pIZoVrQCb$akBZNe8MEktGpD}Mj+-m<e&!pRVVZne--i`iT`$J-=E9x"
    "58#ohOg~a3HLR_XH60H$z)A?glr~I*e6o1^F{Nyhg8(k1cddpM)(0+lZSQe-Jbuz1pq=?#b+8WLgu(dG+xtV0s2|HYArG51l"
    "$M^~*5BN8e@Y&XDZ8p(db)?yoV>&@;X8{@C$=xoRw<(P)+`i3=nZk)d5cWsb84=P?fez;F#k-JcKlL$FU{B|{y4&>B*=rSe1"
    "OaOMD;D5N07_+OMHM)9C?16<`JG)%aB|iyeW`7MeJD@skNUfjFEV63A#ltk-D#3hb9ZZm)&N7PX$V5l`sy2piT?I5ulaVgCm"
    "pMk(6Je8-CnqWhWtK4OP_jCfpoc3BR!r@a`~ACkazXjB~pY|IFNK?oL;O<g}(|Q$=$Mt@#z8&JjNz!>g<TGJRd8YWTg~vN?O"
    "CO&e(oe%|P)ma5%@|7jVjX#KZv)zWch8BVkAS!9(|YQDEeFgq;FD5`p!TQN>lAT$>uuh;8;n!<NE54f41RiNDJ3)(IUlJ^h9"
    "avx}QFmGKvqBQTnEK&&F5NrpB*>xzt%>k$cSY^)Jy-2iV^)GmgaesOCBESx5(3+^N>VrtoxT_eG@L6x_I^_e}!B(<2M<f<X6"
    "0D|uhjGyQ{6sQXk5VGbl!4Pz$5lXS+5cJu*WV+~-bgz(7Yuh0UAYU7;X?yM14-SFPKG&JF2TJ!SJnayKKj3=B4x3^jWysQ9-"
    "!E1F>&<m6iL*?0aDE16|5OW-^I@RgRz`wQciI>&pvCg{A_9io70p}~Fn@FY{$wiMJN6qQpbJeAyOSy-Ypuk`6AIAR+ugmy>("
    "loOll4Wdi+9BTc;nc89`(aTz9&iV{q)tKHlD5S>&W4?^LH&`=kn05+X}vXy4llHYK9gl3HvAEvOslDeLDNw7bNTf?{K(Qh_>"
    "x&rPPyyH6r8%L`F93ESshQ`70|l|5Klhc79di9diUIv>HLkrluW2+@ZgdC}X8C{i>ms&I+n<suWybZ3cV*;c^t~q?vs|B9Ht"
    "Qn_}~5J24NAI#Zt>`jP=&-G~69V+vfC%MF!h9r#{DB_?W|4vlKL9tmJ*I){}ORmnXOxXlSYuoHs8bV36)KCCAN3~xqZ7;v@a"
    "#fjK;=7<8F{vqk>@<BCSeCS;nh|;c5na9D??Vi#!MnaK9g0sH)R<%W~^b@&M^d2#Y%)j`nbWyv(<)h|1G9C1bLaVrht+GFYJ"
    "k4nR`T5g&aioqFPs0(Z2X4cA`uh9p7h;9rekN?w4xW#pO#2@zyc2?C_c`&NkPYDWNj%+AR7*wWjg7m{9sAOcay8%37Ie~Xt-"
    ">ki=Qx-x2*Kom@7Q@}gn2`K>gN*T7}ID?P6#1RcAuMPlLj$_Y-TG4_T~>z9CGr<{(vy{lz?1%6-;rMSo{il2yz<nmgK>S;4h"
    "cZ-lP3;fYj!Kk*^u|XU`tb^kNeQEe3=GWOcX9qyRPrz#aK;D1{<i*OvnMb*S<2-QXkli79bHB@Ak=n_X^X*Va%BUpOmSq8U9"
    "z@WqxS^Cfq~A3-53F%zw17>wx;DGJZgk2U$6wbdQ$Tw&V=LXn?_hY7SIRz~?+g{}+{Q3A^<P;+v4g}!a5N-Wy8JrwJ4{08f0"
    "_pZPUWT(&p+_rC>qL&ljwqI|11@f=U-6N<iVvjJXgoR?`s0U|0DTDT#%e``_d(ydZ8jiOe+;e33A~aby_=+l)0&&`>r}p<w2"
    "x558JfhhZRTtoJ6<PTRV{dx2l7otsgu3}viq-_imI4(XQsn{XF7SEO2o04$Gj;W+?Z1Kt;<-!KO)#5bRr&Wc6p#aoVT75Qhe"
    "_93#n|XRS;<8TA@gI7bqH{LvvqAIK(1!5g*zL!q>x0GTE6ZvV-3?-6;s8{suGq)mAn4a|C7mR1jkx58NdgI0g$hR{s73QR?|"
    "=M>sKUI_uMG2gsY|s!c_nY(USNgBU;CcFsw%ka7R|rn4TPVG5Z4D$R}C%9ROKNn~AO|P7xFw9lJ%`et1xQ9d5XPsbHAuda(6"
    "nVKV<>j|6UnwE6_YNK$L=Pj@xB*Ho-L%GOZ9CSAp6OYENCc$fZk06Az1<)h0hvmI&xB<5w<DyeY5@K(EsTdlaW7=dcotEKzf"
    ")z#)$Xs)8e{WeRVT5aP|{PteL)~7CY7a_uZv-qLI35JcF%#o2o%0>Cv`jmoXJ+wDT+rrw&J-{|)6bcRlpPEzu%F!|;7VCGa9"
    "4gR?=#?T#)|AgXE1ZL;cT5Xsr*ZiyFaW|UBqx}<n&_^E5w;@pA0^Vv4N8Q8e(kde!Qh=S9KCn_NN`W)oJ{ePq-xppJEK{Pb&"
    ";ac>BTSU51X2Y+L@t@zX0POzIm8NYE~MyLK`LK(GH$pH(eZ0>iwBKhY!6izNzYmFeXTjZQ^A=IIPHAXLWmQjreNC+muivR0J"
    "ylTA<^E)y1o^_P1Ub`@VQZ(Ouv<?wx+p(+_VRpxzmaF>>De@pREz-NEe%l~xj3(HgmG5tSorc6&gl*;^SCadDyGE2PyQcs~~"
    "K`}o<uJGrO9H)=Uy2$xo)#95_o1T9Z63P%Iu20`_Vdku$P7Rn=M*ukQ4m-*76ZhvkXFP&(;$3g{O)%e=8#&?~g*8hZr=~f+n"
    "ED;T(J67|(zsrYk#o`#Vb#2xc6@{TdDIu>UieC4Ev_A0e<;H>MW!jMw*fz1`ovh#a=6`h0<=H8YQKbH@!H$K;R`ad@@-6y`c"
    "Nv6JaLw?$A2|fHHtR$C7tdPsOr09sl(_rxk5(28%jCiX%F1{hs1JK5^sI`XO+88?lx&i4^2RZzJ|&wP?RBixNAKjj0Y7Ld{G"
    "|Gf7kcyjh>r-&)B4K$6u7h<xG=W+N?{6cSYlzN2WD`3Ay%@a^Sl_$-68lPEsTSH|Dd)Q9ql0A87s9cK~=)#QO@?hZpTxiQvd"
    "n1s-K6N4|KA%K<n@JLR2?9Ztwj@S&LE1AfXmqUPmXJpF{G=1_JL-5)-D+JNOX6Q+h?L=hEXjULkSGQoWUug3$Yvs^t&gBKN)"
    "}*wQ0Y#MP8U`Sx<c(dX|)o{h8$@}3NQWpPJS#S(Oh-yWNvzB)VM6Y2DVI=1E3XhKP=wXb{9&XGJgjqxEqDKX>c*Q*P>b3}UR"
    "tTx@rJW6kt#ww9RN(2-vQR;m)Rwl+%rcsqd1pmFM)Tu-15rzbD2a9HV{~#4iEy4f|2*}5#T#rF>Kd8@^2e}?poLdTSau8;9;"
    "V%4UkeFHxXl~X9Zu%HJ5eRCMNwtE{o<HaRK@0MnsHO$HkP`kB3yZHV{=F1n%Vwj=YDdfvRCs<OTx^<>#2U10H5<{dHCTtn2L"
    "*Z`qN?$ZLFH>PmiwbHtvOT~9JV_eeQz&<aJ>}%>B-Fjjfy99ZDNIoD5j`>;Ml~|8&GlkQ`CQ^`$uMzKwg6Ip{CigoVPr1$KM"
    "ms6U!c}yAZUDKy+4goU(?3Sc@qh^aI8U4lehv{!trrN#2|BbZ}h?M8*?Tu^KXd|85Vmie+J)Rv$KBA|Due!4T>8!o(k??OYO"
    "7aA}8|w=XCVEpx^FwqDiK9Na>Da~apS)3<$CFf*E7&(aMLa@U4EAqds#jX&i30XYVfz9p2>8N6p;GKgbr;r!M>3;}IPHJV&;"
    "d=AlaB8V7DOL8{I{5~+Ui}?$E2{Q@bqx=gs5Rj|;@VQI@b7~L{GZW>3r|Es&__8S#W<bC04WH+We=q_K;AHc}(eP3kka|&fS"
    "Bys0!Wp9^rYTZ@3j-=H_FA^vU57{iw<w5d%VjCX0N8erLz819gA92rlt2Zm84Qw(fC;o^#*804R6l*xphrx!AV8C_%D!`FQ3"
    "V;&XIFfc6nX(lYK<NvpXlYbf6L#45i5{epdj}IQPUUUsGZ@Mu8WLZTwTx)#dAD4pEC3X-XWaJHNq#*a?!!JCz7p;c<2$5tI<"
    "hd-en9z;!X+wa?lS)w(e57IL366sk-!MJ0P+<!JoRzjtCX@ab0{h7jRFDo8qbaq%?>3y?4?9q%=XC_6^l2Jo^L*En|@Pbx{*"
    "2vIKKf9GG2#|CIh!FOwKPF^f%e$<N8~f)M4Inf=j4t_TtpMfD%)QfcEN?4jjSL23xNnu9MEo39VeZuy}Z=<x_SM`%ICt9QMB"
    "9=B7~Y8nHvU;XZz2v9-qxWC>6)Hoe2t@}=Sqhb4!>G!I(zhdlN&EQ>c7LVz;Xk1LPK+_;n<Se?!0wEJ7TM%?!hn>+MToLvW#"
    "y5U5oG=;}wEChpsF8bB&WQdF^ekF+grWI=43w#q0d9idow~3AseC2JVrO6_VmB_$J7Mj<Y}F`I)Ea8ie`8yC9_<zLGwFqhi;"
    "ddv6F)sl*g)jk1D(678v>#U)#@KB1QQxIBNVX0GA)Tk%}Kdv*zM9Mab3_P4;|=J?@9pq+$wjsrX*ZVT6Tl4DZmZFQZB)=KQN"
    "d)j2z$$^1#tYUt1ku1M91YI7U3w+`syEuiCU%{VnZhZ=2$c$u%9lj)Z<upRk0oGSEnP%y&{^>GDSS7B!8bAYP+`6e-t30|VA"
    "0Cd6eJzGA{@&r(DXC)&LJcy)$w{iuIC!w;xeZm1?|X|ZCGX=fUh6eN!|C^hutpf@|8tor`u&bWMD-hr>sdat$Z1(z%cj+}HN"
    "Y8vmN**QawtOf(6HmLW^(zC1r-)oKsM3E%EQ;4ly0vORzPO;U`wleM@!J-)`JIGveOjq}cfNfE((KMe1p3jq(a_(VDG*W^nj"
    "rJ(uHV{VpidLgc7YE4hTgLhespFnW9fl1FOENDnE!{QYDYph=R5Hx<16o9!On8lAZ?G!^5a}&tzA{*wr_H=%Cx2O|78(r<ug"
    "+BxGM^7~qV*obn-h^ceo=sHMcqn(-tOV-=!n{V5H=8qTmDRn53^hHU(Htu#TI0v!La?1C!Ooz7jd{mv$1Y4miA5FkCQj%`P$"
    "j4DeIh?!u)6+C6Q<Ny(iwL&FKye8t==W>@TD}=9N}ckjqy#$Dr;ErjFP@jW~N0Vd002<!xxBO#-1qwWox!pOuQ9ZKK^R(Mi?"
    "du*0x{Q!(nt^VB#2f!9cVee4M_sxZyX!?~Z*id@iNx@l3dvs{(Od#O*j@0wA+f)Rg`e!N)=;Ah;AmV$zR_eX5muMO@OaJ+dk"
    "IHe67RtWpd^z};LILsb)V_j#k-uB$9p*Q>sY|TsizNhkD%f5{94=B^E{rz24zuP%?15!fqS?j?TY`l_Ehvos@C+6@uIA?<4x"
    "o5iAonGlPwUVtH+oA)sm?v*^MJ2eBB^Bx~!n$v&iH12fH}MsI%+U#mG}5iC25Lb|T!Z;nTQb-YV;|b2k^ecT|4p`2<j}WSW3"
    "<)Rrq|>W=|;Dv(Fp124wg1L8{~^7Oqv#pRfj61H;7T#N6VZ4PPK26CI+<UKiW4axa?LQvt1n*2sCfCpI_MSvM_GFZ_jj5iFt"
    "3_6a+w2|G+`sGlNYmI)!+2>BLDEW@RH<QbO#=E1G2bh4qPLLV4zL(O4HFoy^TpCc9Dp<WcNOiC5rg?kksBT<43t!ptq>EiU6"
    "#@eC(wv!{nZ47wL-2;Gb@61^&E*cRU9+gvot-avQtbcgq^DOOj!gdRG{t^L^55Kiz0KGLJcsS?U;3mz#EY?YLbUE5!7Z`sk_"
    "7w>*tA&8=U`~6u5mPmesjd|@YvUY5&dEx10$lM_MyrNAHfu~JHovd$D+^S+hLcB5bn?yQ4U;YO!sQDIXW$RBq30Bl%%@2XsV"
    "AZBFzkHXZwRcm?cS*HQKE|IgfH<*PgvI@GuXK+FM7p+$5DF5e|9V?e3Gg~WXHr71ozRhKwWu48wBMtFZ~L+t&gOPF+ytvK*s"
    "4buohUyo*zH=)FmWCLr9ZjiP#flXDtXkiE&5Qe+UjrrSX@6D<TLQpnuC;|ztvs&7g{K%4tYL5Zbc+q^*d?>h}Kv1K%xh)s;2"
    ">-Oq#L*IeCAj`lI6Gitpj#%UU2ZJSlNWbl5CcEMoTutHPUxZ<5m9ZNN~+T^EhvFXgjpM4uwbl*PR~V{M<Z_UCB)yul<kQ*cE"
    "}@VEyir93pwd|HF!&=T?Ya<d5*qx{SVuM;a6RRkHIBq-tJ&ZmQ@C?JRD;GJuyuV9XVVKcpa8~<lNzFD>aG`WRPy^~_b_EFC!"
    "908<RXF`mTRi%$+t&DBZae_=tPY>6oLh>KEka`oAOlw}0t)IT%naRx=!V^5;X-8B)x#d~B9jnX;4ap$8Utuf=DB}i@;%pN4I"
    "Vw(GAlIG;y%C>g`PI&hD0kL>!=CfT7qeE?hkNtWJ`^~&(g*^xqHtz3ph@iECRdEc({GFTN4s0K-1G(S3*dxMApG}x%p_~`TL"
    "_sg?LBuIQ(78~xwZNsWZGk6&ZZ7z<Ws+lJG3G<H^nVI(KRJM1d!>b-}v!Ya>KV2(o%|7^t=o0R^DVdeC!_d+YZR&hJSG=hU*"
    "V>3P1bGo=k_)HTSD9)d$L)F9kU#DJR|ZS$Zu<R#mPLn>9Y(IKT^LvOD|x(oeST$4vl>-^rpMD}m?v2LI;>D7WVD==O~fHAEB"
    "xwJtN9T5wJj^9r1eGULe3!)?>uvN-O8=X9Tfhl4R6f;)fWES<mmJer$<^n&Gh5rRAc)P9PN1NU_Xyyx}88e{wG75y2|v=&_{"
    "oh0(3<Uw%N{w=&9*DrL`{l}I1T{U4DmQR>%STOR@?9Lm6V(lxmVXkd*HXYE|Wadqt>`!b=kS|}d`rPAXtD|?(mqiMhVncYLD"
    ")Irt!&aFH+ag{;q*h$G4Z9z8&tb&*wEit72ve7wf$$Btly<Q<^mfJzW}kl#><H37X4^fx!;z7ZOP&;W7ih?oK4Fds0YF)E(~"
    "&-L)eju*Df(Z$nBVtr43M_enxkKSU6SoD`IWxy$pH~L5paS_fpM&3-tvr1m7RAOgvGRJWfbZ2LPQVTGACxQj6%G^wxKD988|"
    "F7_VYPKIxD$xRCjnTPokcRktz(Iqf^O(4=xuK*AaP7b*b7c=wL&Xy9E`>2rAAx@M138T9q)Y8OLf>G?e0MJ$PJaM4~$dy5g<"
    "_Jp2upAOs;0`GdAtDkOsI0Rx=<+n5Ze+c$3%-AILU=p`F*ccBlZDwK15%%R1P%ETg~2VcG%R^NNW_Gbg=>vx^{e8DGm!T!dA"
    "{Z~ShbLZ?IM-TR)gLlyo@xxD~F!L@i_8yw)RwX0a4*35H0_6Wn1nP+PI3EWVP*}e?U9>%b{#>#V^i?~#Tj1q??TR{0GA`i>|"
    "EcDda~MYv2S-q<yDI<8<=93FTDWw~Jx2X<?fR&8xpZ*>W5|W<n@A@1d>cdTrA$6%%%ruJqkHHb`Wa7OLp3gExO4*1AUktp{s"
    "vp?@~c3$4EhjaWYtd`m1LVY{9`s_fvTeUEt$`C)TuZvcnrE}^Ib!T!vTVGen;8M5esDNX%mWA3?&eTZS3yip!Q625Op*@jMW"
    "oLt_`fOaa4G({eN2lY%O(~8Q>wlV^-JlL$RhmDL{Dp3Z}Htpx12bOJ1Y}E2EyJ2#0nRN+y|duRPJP^7sI+ru0Lxd;zYPY3Oi"
    "^&;2oo3GO7P1f(usoc#qSXVFlJ6n0Oi@yN4r4~j8}%fa<h7-1<<)PTPLyvGZn#_NC|Bc31<O4t6&D1Uws$;ufmt(5n`P&r_p"
    "wJQdO>S0in@wnbNK6vBihvikcH=}^Nfu8=i*)*Mup4)D|zmwOm9{ngr?l(~n7}%iuC_@F;)&BfC^YcjGim{=IXe5&%Y)MAR&"
    "+QKqoK$}DVAvVK*Y{dc(e(aoy+J}aHZ@@#=Buc|88fc8Sd5XX#pMsRZ-kIBnSAhZ58jzbE1Xl+lcMC%SO^|se`Q1!=b<rJ)%"
    "tWfC;8U!hC;m6+?p>tJ_vc>fPuJ?6_~Npgj<j1V{sXN>4|l$^M_ejmF)dJL=Z=1S7S;ak0}6aPO2eOX*O>^hY%Z#WQ{U0L?&"
    ";0;7yu(lP^5j4=&*_9PXDb#>|{aYycTXS>WuBjXgR!x~7B%zF@(KdlCPKw~r|Z1#wF#JM!9j7W|&e+Rm2#X_g|QBA#g4W3(J"
    "3gl6&)tEEwiA3$W3h_C!Fq^QH)w*mP_p#*XWIO_w&%Qn+`hmh84h<SKR3+jOp13Fm#B$l}?w(JK=oNLST>+>~-ACD(mZK)+Q"
    "N+!eMYc3Vcu07}18n%?5JLgQ=95yVzBazk-t5)=u-r#(2M6;4s9f}jPg3pUSq}!>fMF$=}#IVXnzci6BPWWopiEPHB{dz1C{"
    "kq_H$t4T;k4Hg6um)*HlV~Rginwu|+92<W!_E*0fl(gbG>*1vTAYUTd-|9a2B@D&Jbc86Va^KWbcld2<8aSEA{hX$UKYq;3~"
    "Kr*I`c+;gQT8)T}`*X4u^x+=6QYllX3ahbxprf1P4Z(;=j6brU|Tysov{=cgxQ0bx^OcQ0Fa^1(Rflh;Ynb`S6{XP}+2?a8K"
    "<AUKDaQ-CAv<6h#bo+Rw>I8W<m9F|EE!Ek8Kkh!KRrfunw2eV;D=_+?0sW*5dB<6=`Map;k=b=?~6p9iBX`;G58Klav$vbfe"
    "%qazT91cNjV#-PB&CC?BiOZ?%DhbxRos6=xWoX?lGxa6_Px|BP2=Q^{${H{q$Dah8}8S?BMeVh&<S2KA#2{Y*pxPY05*4O^u"
    "@SX~U^*!ds{Tu|JWib0XoS^davWF9Iqt;0^azd>y3y6po_Z8}9c9@%_4hKctLo$Pq@0KkZSP$Ll*gFx787?0U;I((r)YrIfq"
    "`!C)w6i_2v0dfj-fVxW9Hxj*QsFGY+8ulKbYThe_u>8b#zDe=x#?=xxphFp58sj|k<FuZA<QhiH9TC)VvwCTB)hO*VUDEv($"
    "oTV7ga$ORMXXgWsh`dnYGK3n*CZW$VID%BthEnMeyTNUpv;@6?yT=5Ii@;GTp-qEn}_HHmj@}Dy@Xiuy()s_PC)5gurs#3G^"
    "ai`4IwYIuoS<SfmZ&-{PxSd#X@*VrEmKp`^KC!ogY3pK86GI&Ppw?dK--7%C;TFs+Cpz16}A&;}6^4b4x}g8RCD1w-`UNFp7"
    "^%v7(*@A2FTJ}*^0{ab4w#1qo+dzuNHn%GEKg%kzEdUOTp#-u*!EQIG6RgC1@Jyo2K3lKq#GePVOUqbF+49j2o9^)iaMKd6y"
    "Pz<|oecTnICDO-PNtiV)4-FkFJ3mF;W&b^;p!h$SMKCdJx$|BrR*79W7#Vw#LITL2tW2<YEiA9+4wz>`FYO$PfeE_<13EE!I"
    "8+ps1HbU>!PLZZ;5*j#Z;VG$xc1Ec0sKrxDM6b-aul8fck0pbBodc`weci==vxn(p|_@$2mL!>G(VPiVC<^_*2&WmgtMe}hm"
    "&kBs<K)V_Q~y12(LZc%D(p6S0U}AxL0=K;Wl%Sa`~~2s>o#vW+zI-GT?Z(M>5&Wn<hu3y9)y%Sd#J9Fyk?kdSGUWl*+j=N|p"
    ")0oLcUN`D)8055s}hc*zWY0a4<8oYB1CMFlftesX<xr(gETMEc<8@yuB_lRt(*dei$wV;*HV=f@NV6RKoP6dU8SMkD$6^K#w"
    "5t|oSOh8L_3Qlsq)zJ~J4l0Dqi5Akk}Ib>x@K_>5Kj<0mV;(EKB9{A%IsQlk*P?<?MQ<xx-=XJwI3zjt`ohw4ve<8;GFU0W0"
    "*kby<XxchLdz^#~jq&Bas5LFvel8AVDb4CC7d&>|p*{oyWr!a>H8R-WRDM|m(N3GA{amZlA@vrx1t&o+lDcr97>phVS5%Fhg"
    "4kEjX`#M8w$Wwp>7;*4*%M@N*FRU8<aFZ<&u(7u>go*+1F{V~wot(AdKFgPeupb-8MJIsvQogXK&WMbfo$}hvC=fV)O#+KW4"
    "WYvh3M=hV&}Kess(+rfiN&<5n1uY^oxEO+SiJyUR!*C2*g@@&07|#vfA9&LwD#9kCx-J?iEjPgkA82T(B&r8so#|mR5)t62X"
    "Dw)BDlQk-;L}Lqe*rAJA-;cRZUA-dst8-Y+0;+A1EBILGh`6rMBKS$!zo^DPYGTtZ=nWTK-s<+=F@)4#SODG=xg|7++D&azc"
    "W+3%BP-QSU|%M*V>zub$YOK=Ww!&xb(b@sQwvrc~XftM%7EmxuJW|}glZ(96NL=m(m6BCVY|G)r7LumzAZ2^w%uFfi!THYQb"
    "u~+*+&$n+7ac!%u7JTf{4F$z3eEU0FLML-Olnhzf#`e|;`{p~m@jo>no}HZqC~`%`J%iTxD4_Cr$IEu@YW4er*E7J2kVK8b="
    "ixvU`pmBh4S|a@s}>z~o?^(PI`}FhZ}*#L%Vlyyu1{{sr;)>4eC$Pk%!sGA8%;ky@CTgV&vU;5x+j7ImclBmu#E3|ECg*kdj"
    "n_paLu~|FgG*y2_yN5K)(F!N1AdY1CQ>^X{5kcvPi6vMTR5Pa}=|!q7>bVRSHz-j)ssg<)DjUSi7!`5t-!ge}RVlKcFE_#X9"
    "1%v@IazF|w`8!!y}3c{TJ!|C>7CU8&oD8^`!dXPYdDml;|XaJI}Vw3#}!xh~KqB%%diT0#o(l&_2z{tVzjI5FD1i%*mIZLkX"
    "Lh(%5jLwkse9zV9vqG`y%^B&&0s@S#c|4Q2C70JvVZoXil-fI4yPC-Ivs`tF={h5Bpq%~rO%|M)HQs;hKrGX#B>&GK3f<{Zx"
    "ElT8DL|vgJR~u2SvCBkx$;xWPFv<61=sU6#*hH}MK~VH1)-aaoY466|Ap5%*O)CNqkIFq+*`}0ck~Dp*XDK@aOXss+zlrb4`"
    "=dTm>_ZoD{QmIyIo7}VHHX>@{F3+c^HtyE`Oj)DPdTT2sXX?bB#dx8W-RPN^|<Tdg)uJ^!PRh}dpY9&hit|MGbVxYsq6!$ct"
    "Tt*sSx;5|MSAp?H<j>_e@E;)>-?=s_2`b{@+r<u{s=UH#L>gQVu|_+fz~rJoG<vSIA$UfIY3Ifyqaa@F|$D0b9I}h7Ns|F0w"
    "0Wt&sQj(t;QP&UvM1TkI4sF8=V%R!uFd{IG}f8T%R7-TMNH{Nrh1&~tdq_u3^Rk8F_j&>)q+DlR|%qwm+5B4W48*H6<aVRS;"
    "Wj}l%7!KCUgwV~;)<9i6!G@~}@JK$xW_V<*hv+7?@=uF|OzI89kwo}27xNp`d-U%GYQp-cF>lLt2dlX^Ksfjd`vqGSiyG@mm"
    "&4vnFC1dWjN1eNXLz8zO!&yjCV-T1k9~*kaQ!V^=f9kR5tSjT#PzC<yNK6eti7tG%o^k2I56_qwzZ{-jeuj6X$WMP&ZR@`c;"
    "Rq6gZRK@<IstDRhV2_N;tM>j%Z<^Q8NBO>4SqaiHyJ8<tRGz=aIIO%7&-u}Pn=NHNM#r*F?700sCtn5vA%kO;{0&cAhO6#yW"
    "<o8+P2pOd>X*`5yxkN3Qbdk?A(#fR`(w@q@cZ5+^}MabFoq@NPhj2ll>7%5wj!=MUewJ5eHk?u0n8!LzH2~J~}wp)#MU}=6D"
    "N6?_BPfS~ahFrQ3;OER8&$*<{l~wyn8%AfHQjv_R#N>^6-kAn?}IAeTV4tuMGSwg$}QW{a*_iz&<Dm)?|1F1<`h?wiv7hHo2"
    "L?(S_AcM)fm*!;<R@_mKe{GOiMKrY(|^c7A$feR=mk41#|DMy;B`Gg>j3k@_p1k5wDZ<6}a1OxfE>*OESLY$(s0MDQ4wr=3;"
    "P3wc{Jg@d%!(TU0ozCC*KWkF0mO$%7jx&YH45}|NG&fjB^P${Q4{*ShzRL$KBw~0O-v<V{+#1j-dVLO(WgbtT^rT~?A1|jCG"
    "sB(Nf>&P>V4eDG>}`G@>s|9#rM|dQb@QJwcRGWCMZbnx^~To_O^^hv&mzaXeWrvof~N!TdZol5$NivKQDpkVT~x$8pH=#Syv"
    "L6It{?mAaa0<R@{oaU=6$pnYf>YgsJ|fn^z=3)6d`Bk?uyT$`7R%o2BXs}YbK=qQt2uR!c0{~z@>p|>UqzTjbZk)FxJQnJDs"
    "av7`S*A(LQ_(58n;&0fvN*mU>%`fzN%j0N%&=!uX202zPpJL2Zh2H)Ogvrq+)5o?00V#eCQQ-cwQf4_-r*HP3#Z__Ti9m(2H"
    "M3)l(yMy!8Qz8>l1|I6qGf1MEM)xu0^Axm;0f2{^U0RZw+;u^uh(Ljoco1Zw+a1Q-vZodUy82{KR3e(63;fvNgoZLz9`3V$g"
    "hF}32m&eD?*XjLSc7XwUy5_A;;(Tc14h{rlADv;_>7g3d#YTMSv$gvOZC=?%wK_OAc(;mU6apWcC%@iWQpt|kJUIuYyUT?FN"
    "U;k@iQc>*tXjSMFhPOhBl%tQ5e!c&NX4{299a!Vj$LmnJk%E3i0zK?%^6HCb_EfEUQ&g@lWHPuaEp76zQCH6<%Ui2_k>Yw7e"
    "~>0Qk?pJXq<f_oEF#U^w7sW!TxgZ3;-Q2ngS37DFd$#{rT$P(fms^dmW{_8ER!B5wvDZq7;$nMt|HAb30qwa-cZI7Wco}lei"
    "b6ez?p4!A|z<s#9Kdh;7WLj^?Jg>V<_4o{upTyQ*BPMXcg9XochHj1#N4175?oRb1Ib4RkoIm3YmShZZde1V0rzc2TYSW`6N"
    "@c7{`oEu|XFb}E1=4zD~@VD7r1?Z@7ibt2!v#sa|bYLC2)ll~cP42C~nKyODq`fT^!Awj&$uRMF+v(f=5xW}D(UdC1k?G}~|"
    "y*;ts1EOi^db_9vGd{6?c<;B!#~f#*GCi_J>K>4tWrt#;nEve><v_!{x>s*{rXguy!J8kdUqBwDhxE<+%pYy5rTJteB>eq+j"
    "N)#b#ge~5Q8AXf%A|K;sQ8Es9un7QDO-$Vd~J2-uLET|YV?!IAU|{HzSH}&rcDL+dQ>uurmgB!>8;L^VK`h?h%XkHiTQr~n{"
    "?8SjWhdC?Y-zbK<w%0aUTIHeZDfAyt;uN{mZSMzScDZhZydgOYg-et5ifX7hwu~7`=t(-*_`gkaCjG6~?E9#X+*ve!cM#P!5"
    "hYJKzVhZ&W7o%m3Pj(Et4uz7P66x|6(7>a&Y((H`@IXDM_Y?LDzf>ewCLU?JK_n;J}&2@>G3N~w)zb+`hCQ_rL(bsNG)Kh(@"
    "f(N_bqKlK!SHu!@^7|M)W^^#i_uMU&nLlpscAFWvu54D#7aURJ32>j#?Cp@{?EqxmIu6rTUJpsxz`pWgho3|NpHZy`;z^(3b"
    "2x9TZ!v(I01Y2^MkbF_DY;Z<Ah1p{qk8XZ^+|FG6jLv<&K&e6FU{3G@CP~CF2BRXsvjFjmldA(>f43JQw=HG~VTc91v(4|lj"
    "}PhV@4l3;Mn$ImPTM=&uYu>!{1CEU{UiJgmUnM=!^chi&gF;xNNNe4p$l-$4Z6-%;+!erysQdn2_X|PNz0TgZ3LbA4L`9MMY"
    "LF3;PRiU3;w6-FusOz^O<*21ubPanzCqVr91hW65`X*UC%9|)G7a>KvM7UfXDq9=20G=L;;r!Q^+ItDeWwP#&7E>J$u<es-b"
    "0^_%2g~Q$zY(yGta(D6~5C%KJ)zWx$!FI5!DYG^*i`z<V@p?0-tAA2s*-0ihl`E?L9a+0{V=zu;WwQi3vD8R^c-BbRZC4e9K"
    "4%x(HZEj3gXZiP))ZAtig0{KlcMzYukUFxPFlPwnREDJvp(Qc=tmC;NE++mz2Pfi%>nsEU}v+5Ha{a_}D0D8awF5JBKeBiY3"
    "L4`l+Ol_fbw}`R9?vcv$Q%ZFIRz1~h{jo_i^Hs<^SD94%)H-Yq(oTy^6>8S<uq+&EX_6Mx)9zNi&W5dVZjQ;<`yk{H3KH!9<"
    "+~zJ%uD_f2o?UJY^#avoT<9w)($tYUib$-KI`t!RlW=)d49k4O^E}}A6e<!@7<~nhKHHU5?X!(F?v_)Ieov^AF9w`=&)>t%Y"
    "=C~(HKBh?bp9YVmjKpVi);adflK9>ZkdeilISst1$n}&Gwf@a<*ZMJ`SWn``J@BqmXx={7@1akZA1$6jEv^-%#D7l~>Gq4Eo"
    "$1VYN@9<e1LfrKkij&=_{bQl8B`*<O>W7U!O}Hk3<E-2P5X6Mlnb1Q>wx#)Q-g&n<!EJ4;0k6`w<5lr-9h88So~WcpmkS#WN"
    "HdiO|>S_i!-YLsg^sQu}S0i4{aFGk@P4jtR_RVS9W!!h!P+0~(VRVy7sx72@(&-XvZSBNyFv0D(ml7($}kKd@}mN;K?UN==8"
    "X-3+%VrO)?lJ8t85E}?S!2S#emqsBaW&eY9QnMn)L%poNA`c(^HZyRo<e|N-kNJtMo;>IM__r<=s?cC9xE^Rf@Fn?!mJ!WO;"
    "jiIQs5(U@Q%f3h*hE&qt|lQWFxH$9yt{@P%b%cHib+lAhH;S3;_+56`mnN39ax6ulLs%Xe~zn`HCR8YWB+IOA@tR+yW^<{Ga"
    "8ei?jbPX6pNM#^DI+(QJ!52aY_aoYHGZku*Y?rYidqC$Pn(mq+TVO_CWyf#L#PkwF5Fc785AYu{>?O-DX%($Q5;PmhEk(oN}"
    "E*s!Q@lcZro(L?D-y+b6KqjSi3F7Ft^!&7Cs;8Z%DhydHg#Pl0fS|DO&cY1VtrK0Z=SpkiiYD{ksO#|Bs%F6r}ah$Lb`xzz|"
    "rXIn0>g?76VLl!LaO}S7oPf@DGO`*I?PwDFbofnJXd_$h0K)YHn9lO=8sW|QrfC`tbEz23%NsC~Ih;ZmD6Vqy_<;ZohR}wOi"
    "1O2d=d6=%b`FpjNite_IH1TC$;S7CTu9algUH!EDD@reeKy1MfLPEaqA%LHeCygt>)z}Wp@Jna(H~Jwf0)Q_n%3Q2p^F(@O1"
    "kmyv(+MRPev3KT%GDoh@<U7~f{k~B?>nBiz#YBqPLh{WRLi4?yDMtdV;XX^4ZVwK10I9$6+MuVLqKKqvw98p<3Gb*M{nQ!k~"
    "D?>k8}hGVu%y)KexhbL6G$?>y4bOLAngqJym~%{*C^G(oIq>dGAfz{+po*?O-gZmeXw3GhI|KGhac1F9rk03(d0%g?O_)l>$"
    "Ey>l;v*X@Fg~uZJ?NcC!A?VjSN!=&K=?hnxEzf9OLz@fvUJ5OqGn9ouMbe9s$tI6M2)I}TfD#uN4Cly1Tr1v-864vV9;nFi`"
    "c&%(Sp@8fyCtR`dn&jG<aKuC(+mHh0BBoXboE%EB=>Oq<{*1%yW|1Y$--T4C;nbzP_>L?a#H@+V=C<HD=K~id`w+af+i<in1"
    "LLy~2hfHePDt5&`W$VrXYGh-@_g_i0p4qVBaef@*3psLEy$T?^kcOCSmMjO<8mGw=1t}2>MnHK=w6qTHE#n0k_{DbXpRbOm4"
    "0Te4sOprqA&O&!VF&#?#aH25>$QzIOi_kf75#X4;-B@&_aBO-H*^DJnzUP-ysE6mQTAhWVKvH6^l0YF^YcUoH-1pd>@jM{Hq"
    "!!r>nH6jRl^(}+HY&X?`ZOU+Xn~%6LtC2P|>-nqH8)y1eSOAU2mVP-P2&lOOVC*ki^qLFOR2hLKgdsGU`ol(2N2`pOld_<Z)"
    "OVxzLQZ)?y*@|HsrfM%TeM(Vp10ZQE93J53r}jqRkd8Z@@q*e6zFr?Jh($vL-uzkAoZ|DNBoX3y+B^UTa!4hf-jIl<K?C}K4"
    "CsGQdIbRH*stJo^U#U4++K%JxGF`5+`WW#fCCJOT++n5Kbf2yDLVU5%yy!)f85IfQ@fJzxV?idx~gEzK5WW|M<K^!*lCEz$Z"
    "q`N6t7Cb2p0rU2!$+A%lXd5vE?c$2kO6X<?-k;)mfA_{f<6G%i>O+Vi@n%kEE5i22`AZBS{;QO;V$;vPA1SHzmmsnqlFUCi8"
    "r5jC`@L|=rj4>OG3ni-{?3!W-kIcm`uXvB6^#Usk=ONh5(>$XC^Nfnh}W!Au`t(K4&W%FlvJ&v=@G{}*1X0I^)|9m-I*y9Fh"
    "wo?<YjzIa;`%S*9^0T%jS#xs8E1wx<0^kht#GfDpet=Rb!cUThD4V(8nse*J^|)(wb0is>dG|hiAVX&e_i6g}N^*#e=y;Es)"
    "^~Q0%uCO;HI_Wm}o|ez88-QSfA|3+R(D2OkHZSIxf3Vl9}aRez*5adr1baLeVpqbJSUS`~1?jfMo72nDG7pb1wV`ry7z5@p?"
    "e$sxDx{du-k->tejppf<oo#(uLJ@@$tR;Vy0I6sA-A>Mt~5mG^8cGEV{@%uptEl&`Xs#&5$Fg78JeKL@O2g1N$e|Mhi{pTNK"
    ")mA=R;RK-sLYb9}xXHiR)%Z_P%&;Kx6mvkwDp2)@BP3n&BoW4o8Fh!>W9>ixE|zO=`z@{w;YT|531fY-=D{?HEFfH1|IQ`=i"
    "Ld+!0~TUHCzL%QiN=CMHZ&+JGOn<qGjmP!@RZaN=fY-c)Hy0uyO22)s%k@mqQDhUtu}@H?@Rpzw9W50YiF2U_A|hz7w~!Y3O"
    "hzP{5nbawChrqP~QiE+pM<~Jq4#u_0InN@h&CQ_LWP9G!L>G4NQ<_!PtB~f8Za1B`ps!y&3-Js|3Nr&$7fhcrov<!E+Tx8Dg"
    "rE-SiM@^UjyLI<E){%?5hV5`aVOoW~3C*}~HVercwuFXOlU`tCKMq*VhlILvjmJCDV1-t7`gpg6(ZcBEj)p!tbppb2_->c1;"
    ")5+@q#6e!wei%P-jjHeFQrmF`;O|`X-8^m>{XX_qH!hvzW&xu}gif82bY=daB^TXtEX77Ms-O#*rm)ZTDP${McePiLXB1S3#"
    "KC7oCN5-M8K0ls)smBF*L8TuHH<)lei&1#|5!O42S5*T_kYF|5R|rPE7@(|_m;Dt5L!ogxAkhe@Or0AXv>YT!qg-M+no0B$p"
    "QXO-uT3ig`wCR;Xpi3WOnkh9(mZ?mAK{qk(^7N{aR?X{faNrmr=IVYwzlg_+^4z^bgwC~BF9*5Y)Lb}|Cj_`pegVkkieAQRL"
    "Qj%NC+vnV~P7z-3jq45SHOa&)e`vaaWO759!%+yIzB!n3?OpOttb?emYl>3S*XQ40I2}`FH6q=D$$3t)raQU<af9)7!3%12+"
    "=BTPmHFn=-gLw}4Qa{caBBmx|MF{S)bzCEA*=Moy>8s!HFyzpmb?;Q%$$P9B@e`Nc#dcYRTW42kfO%$#C9TA>bcxNS|7fvXg"
    "0k54$BIVBTf5zt{&z)pB}$ZLIXhgJLyLB2#e`}0o@6PF#u!Q}~YPY>M@sc<l0?om+or0&|?jJrk!_a<N9LakORKQRr=Bh7)R"
    "F#VdWIp1QX^rR%uw=bdStSvXJVF-|QJARnYOo_jHx353^Ofpg#t?pu5Xuaeaw88THX$jzJIItxoPyQ(z>4Z()9h|yR#mj=XL"
    "^v#sQ8mwneiU`gt%Vn!*j86;M6R;vj7Ndbv=|d6;J0OJ*k6jp@ZZ#<J3_3CX@$=5<301_>=|{%00pmBDeCN%9<)AEr$+zr{z"
    "B$+b7Y@LcVfh*WB3Io@M%ATddxSW#0KZH2ST9!=Mk+BN;~y%RLEt(w`NlemSYWQ3!bA%#P!|FQMRAx!dft0IbkBy1=qNOstt"
    "$&oik$f^BQ!)l#Lvv&-gkya#<GqV#0Am3tX%Ez5_TyKdrIDQ}ltUH{0=ZuKr)0P+Me?)UDKcDBQEY&W`6(UHOm0>?uqr-07D"
    "Zk)ayV(2wK7jM-?3W-QV*LVGH@u(m0dKrNn&o}sNz1_|XIUxPL>5Kd}Es7Y5RA3H!i(OW4{HGsG6)H}f|i4(<j7s}uiB#B^="
    "Y>Fj_tQ#9U7!#uY1TVdft^Un4IK5SaQC8t~1@jr9<}Wh$vgqNO@&EZ%8#%OEg%)G?3zsQ!t`+<ApqgbIYnbdOGv!?9LeyR5@"
    "VP|i-Q&{o=gB>))^W~*vx6O7YJ>)~yJEUE#(BN=uAgyk5BT}YDwKu4#8b$ZA-anT1{)AP3BJt2W*R2@`I#Llhb8LX&WXw|fy"
    "2H)u#w7)w>^g}RLoh4D&LNG_-q&&$j0(8ah^h=cP3eX@CUQ8ne?;ACwM0U1*9#mWq&#^CNC%hzH=Q|;=k-B0MHXC1Fj3@>1U"
    "YqzABL44p9zf>R!VIMoUAY>36+uD!&Q?I{QXf9yX1W<G>Vu;6R&i*IgTo5!~>Nsnj=1h(GBE5+HSi95?*_psRX$-ncktq(;U"
    "U&G((neC?D&4@X1z$3%f~5TfCd708UHFw4Fc1db=jZ=X{=uv$FlWmRp%R`Dxzh>A_W%_)$yFs&3Qf9n$sgy)~UOy+iD*$2!R"
    "Ldj11AW~kji44B0kt{Wg=x8#;8XsD6ZKH7d{;5hFhQ5O+GGN>D@T#Zdd4AgR#2I|)TNLR}6OAZP!*=Es$|NP}f9UXWsAVlQt"
    "Hdh42tgOMD8qP0<TT38IaEm|KP@QZ`4l=>DsTKjX7lHIsxWAk3LsrB)%i@VWhbCt1DQyzxVBV+yer?|C#;g7+h)|B$XcF|d&"
    "iX%<mAydkx%#8hUJ3fup4XtrJ!${_J;j+n~!n<NQzCEhR;&pkU`tt)SHl>C(@tNB+R-PI>MT>x``O-a`Yb?MRu%ik02xENOS"
    "p#9JyYV7D~foZ8yxUAXF0P_yt`cam>o*`m)gp$cM*fZqptqCgu;{)i#+;fBPjUk8Z0nCNyZ>VfXfmm3BsXKrh0oX=+r6oP$M"
    "lPwOM7@d$jr3doDt3F=eQ13$fI+8pvnV_Kl9r~DhSyP2HFLLMx*?~ihV<OoOJS9^XfKF42x)z%17)gbjMf=-#KfGRloe!9Mr"
    "Onw~o`GsvxP#inl#$#P=S|Zg6!K5xZC33*ctgI)QMmw<aE@&>##GU$(iLAvS$qfjk#|o%hx*rdA8tyxpr?37fnUph!br-Nj_"
    "<j$rB?qeL4M$EkG<1gM=Zp5IToxb<-+yR5n20Svk%p4{kNwA^@&E--nZyJGf7Ebxjj=YqT`?q4HkJ5;(rPl0FYEL!*9N?pm3"
    "U-V8`XIGt+7%oA}Rj#_yMPRb-p%I_fhQw-t?Gqut3i@2qTf@t_;-2FkzXzZHw-vTqi}tEn3}20qojCG5P>ZWdG^?PPQ-BMEx"
    "K@uXAAQJ6^dvY->lE)+(KD=)lvvOfG!SXdszn@M54++JJCy!OB>6kcNvFYKu5k1L}hMH@2Bvx%)M$t&PO7?E^Rz8ro5SzbIG"
    "2DR7WGTdfuvBRW5Y+$f9UK&)iz`e3)<igwdq^f~av9NEq$r`uwE&KDom!2H=?{bZ;io^%t>9zf5ZPXW(!;a1P5IxpaOj|woD"
    "*fB*zXDZx+5S?l0v4-$KR`b$I2Fy;ol@kUW$-A>_k`maW&30O!U{uW4Co{(L3Jd=659?ltsd?))@sBI_Q?9viEQ0uns9ghfb"
    "MQUC`qPQKL;JJ=aw1W@=7#~agtyQ?n?uXuAVF$_E6<3%vvo~gd83Kxaamn1Zhz?tSjfZar{6GFxZ-lD|C897$o2KR+gICC$H"
    "AVDXe1g%WD+|o{*flS>FghKDB-+=#^v$q=IFC0GF?se6H9DcUP<EHUxIHtAx6iMv{1uZ*1AI0zKCPlXh7c(fAY4xx!n+Wf4x"
    "9h{=#7qoZJ1T_YBMoy-U3jegmI&=;wW`#Pc#LG{GYJ^f!^vtt2AF^fmgUyt~MK$}==y+-)Pem=UmH47&NHb_D6|9-Iq%he0N"
    "n7L?HixH-=K1Ct~7MN&m=-jcgcb`#D~!DzwjSpR?x0n)t)pj>+EV2$-eDl!t5>*zo}HvEy)C~l89v#oj#Z-Pv&0UTZ<*ywy<"
    "0KIRbop7%Qmi~SshYwBqZ(mEMe+*%TG=y_Itl?xwZ5AQ#n|1?Ks&i(KTm|<TZMZUtq%#MH)}VDpomuIe1<a#5OdpHr_*+3dW"
    "3<wyzHiLA+c7#U1f-(d2e$8lHgC-Ry^elSxunVps?PN`H?@FB2zYYbFiwP#7U<M99BR4$Kq%Vd4r8BqRcKj?v?EoDIMW(Lrm"
    "AXICKy*?uD%q>G|@l+2YPXMy={5TkC<8Bu`lRv*h=&9!k^3ME;}j=fGpeGhB4ycoGrC^nRyVty9Hcbj9*8m7A~SJb+N^w>X%"
    "cNq+!^mQ=%Z(aI7}rqFg6?$4kTMt^FR(Eu|4&*V{jTY#$c0oHOwKG+(nOSegcA04{9bS8%rbUlI4dUbuxX5#m;PI5=J%*a?S"
    "{!w39_<tsCBs_Yhpv@l<%r*g)i!lQTLtT0Bq@n0#}dFv~KjFFIG2_81w1{IMQ)A0$r<)w5{2J-=9Ni-xaIT|=;&S=-BM+>US"
    "R)`bfC)|ec46oO}-7~7zH_a=JMS%Fk7~W~yA}B5m>dp44NkktkME2^g;^_t(nYqKcY1XUueEP+qt)l}`gGw08Q<>=bChg%BK"
    "git)wa@&E8i}Mr%c(urr#dh9+m{;$JH1t~Ebkh#zYFj1^qhD<(6RY(eFPK*S<nsgG0PS{d)*yye>lk=SCC7dk!ZYj>)JKQ7E"
    "9EET;t+LSo1EfcD6pWg*Si8Ncmj&Vm?hmfttQ(EApl<j&njpZ2P;DWK8Eu<p^5z#{aM*iB&KiVCr+V=);ph7lr;;;*#{b%I="
    "NaXXI`%_N=au@d7w@x05u<rBH9c0JBBy+LQ#@D+(l4AW2v4TW8lc58u*;k9=Cc3UKtHL`4}AUGN3iyF*@5%fKW!;^~i7iJg$"
    "`ctC=SK~4-I9tNHXf7*UbM&az4DoCs$Kd?(n!V!{kxstS59W}h4h|WO7;sT=v`FEl^%&Km)V>3ALMk?G1D;ADxHYIEZ{Ao8+"
    "3P@ONTlL_O^aa2EI5|2%RY4~na*aRgRz)=wJ5f^C0evPNZqjC6DBsD~Y`(r{J6?JRo!^0vCcyqE(S;XbVr$H@ljlXSKL@6r*"
    "(PU8P=gyn9kcdLO!~KRNzHg{%`-4-4T?`IHuFP+hV9u@1n^?|j*)1GoY{iH|MjKI8>5Ci)ksMDm5gMDmj7)ycuW4bE0`F1E|"
    "Tey@S%NxsB>O6J`9}4;D)Bmsr&+)AYEVs$|po|oDV^xf@YM&wz;@+xUaRq`pQng-MX_Hcv0_ly|;G_hLFnQ?H~;CglBG{I<{"
    "LrJnB$F>{jx)j^_cW?BaIRQ2Z=|(bv`}WuMZ6BflX`w%b2@roIx^ABt3-_1{+2^S0KCt?!^8DL<YrTz4}4Hj=@~$xP#gb!K&"
    "jefEIZ0B4`^r+Ig#w{;w81$|mc)a0dYn0?-D60Z9038b7akI6YD<w_WEriobaJ0*t1L>pE7kfHbc_m9(8`U#njB0#i;o+Izg"
    "<UX8tL+`l#S!5IQv;1dKmg5t@j?lekH_{s}z%&dYcz55hU641Vp)tz9D%qPbYK)y!cXf%5AF5s#J$(PaeGu+202JXWQy>wS)"
    "MZ*-&|`jhV_sWGQEW{UIfoS?luNVz0x6@`81|G+S+{aJ!%)~-h$i(;^FDJPEv}e|0r2GAGMrXidSG3vo>FLJ@6ox*N!#gBHS"
    "tB8;0zD63nc;P@pCm!P?LGUE|~g~+@6oa0PXf+DX{^x12Kc1D!cPqspJJ;U-YV43tj*?O{<toLb%$k(WWeS@FU(Q(_)G(VeC"
    "w@x60XajGpobJywI|eCj^SL6iQ#&qO$RlSZjy=;$#~)hshwnXmwWUxQ2YS$a=;F*RQ5hsTQGf3psX{Jisf#E$jr+E|m45Tki"
    "YDcS_rw9hKxUg5Zzev6ge&#yBcJlw_5%5p47^*Zoq?pIlt7*<OW-RG!iO8SEiz5DzhJ==T?TBp}?51u_%0W3Z%C}%XQFO(kn"
    "&KW2t9j2f{u}Y_|cg_<|&|6Fw<<hQ>3))y9I0L5xYcC!sZY%L`7V};Q_ea}#xDpNUDJCl{(;Y_X*$biaSK21cE5&XI4l<Hg<"
    "GS>V=!2CtwV2ema?QBwl$7@N)?pu8TW2LHiviX-osc8KF0K~XCdQqi4Vw}UTtfzppQ(`?7!wsrLl<d<=f6LRll+Pu`Kn^x02"
    "cgidT6?PsE!$J$*0NIF(1VnG0<lw)ECbD5hq&~qVuI8kJh{44>p>PZsUfX%Q=`A$O0~@|LH0l8W@@~<Pki~Gy?;{I;{PEOvJ"
    "~rD?AX7qNNO^Os5WCT_!YDi}K{Y5I^=vlrMen6#Fno3neE;``5S#;X}X(Ho!KePbjRUNyly+C#_b~JTB9lhuA6L*p~ZitCsY"
    "o9FKyI2QC_CD-vMJ)6esQRLgFHRA^wVEe=jK3gC%%nS;X%qH1k|&+~h3BSV|VJO`V#(>C=E|Ez3-O^b*_27h~i|MoxvH<FPG"
    "Y6gV<mAY{=x&49h0rt)uy?BaCXpBGW80UHHJ>IQ_J=TJt_z@=tv~aN!)1}lkdmVCbr+>t6P#E<gikk8549np+?#u7FmjOZdF"
    "WV~xuOh#pA8Dk~-h>}bg0fPaK4u;oS|Xez&N1L_hAo}Qp~TYzUjhzC;{_+4z2YVDBVT+5Y1y-6$GMqla$00%^DTeg+@s2WnI"
    "$Jl^o5!H{oDJ-fgmXG9p7)F;E>Dd!5RDf<cI+AUGXx;)sg*5WTbnLZm{?{kx#7OJFCb_Q`&t)V^ZE*&{S7BJV8;dR*M~XSWj"
    "8-MUWmoRPDdPruJ7=!=_J%t$~Xm)os7lpq`_%?ypAAb5A}(>aHQwP2R?v2P>MK<i)MZSLo=*Ln?DH;vuJKiDbJ+7s7T@9v7F"
    "~{Il^Dgk_w|hGT*VL1O1PBgJ?ApR3Dhx0V#?2YB~+B#+SzW7pb46U&bp+FHlbS{8xM2c6CX1eA9P5nx)SV7D|vt>S2)^~RA&"
    "Yr}D)opTx^*hyjd1&su82X2LE>KL+Trf}#f;PugiUR@4`Cg~;WJ&@DllP007hCl0R2|*~mv|4oIrk&ecV6l0!j^v3ii7Js$d"
    "(buOm55)A<$1?aA4DQ5(8QYMCO`Pr!i8Uw1Tbx?V*77FcW+)_uw7F$MtuxNI&uMra9S)Ut!UUS1SCIn4!fv1++P{a_uptYwl"
    "?w2dytybGNMq6aRig|<A(L7*6O1AVZZBvY7qpX0>Lue3AH}ovltUsrgN&cxHbfsTk)oCSPs9-9p?uGBX^2~=%MI=a{G~n*Ol"
    "hhw$)qfJOmvN;4C`w^cXUzRgsxh+rO*GZc>IbaZC_73Rr$TvkMy0OoAP(gV)X(UjrkQGGq=|AF~x$v6yMR%-rqdgH(KZ%S$h"
    "fUfk+lP1a{U#NZCMH{tSv&U5izS&PB5)(+d>pyN4k_*katjD_l6;atPxFo(IXuwiTF^Qjq_<IRRJT5|?dbCrd?@9>{=GCF$l"
    "tKQwac+N8KN)TOmE2T{FVN(tEa}aLPGFbOUp7CW<v3ZU$EYn$3;)|gH9{Pa7BIt6t9pc10?IJ)K3!RAs`s05j7Jq$Dr#Q13v"
    "<OjvgaVL)bQccXI={7eqg&^1ivE1fc?L<IZ?(>l+W)yL_2+ZG7C3R5bjrsr{u+;L@9vqu4h^Mn$$_FsAz^ZdbMox*4@s$N>#"
    "STo=;Xz@jgJ)Qiwk(`)w~OKhp;;5G0M;Dzq{j_jjLUS%p<XJ@<m20W^Wf3{C9>}wz+4R1Y-RtSE*-5th{d`K+j_BBNvSs!bJ"
    "^FT<ilO?HC!*HJ<w3a7)J#GfSSE&>pHpPy!Jkv-*H)TN>KMG}+$O9Vhpj=(BpCN;2Tn^lBWKoGZAVe6TsewZ&kRtS%rNN&Q<"
    "gwalswB`scrWVM`t;1e!x++xpha8gQ6L~Xr#*L8rAB6@gg#DBHaR`}&T#5QD&i0@V(l@B>Ri?N<FDH;vq)kaAPf&hh<qj%rD"
    "S7|Q!WFN#Xizint8%;yE>4m-b{RO&A&;b^ZV2I#Ljnt;iGxNUrYwI95)!;?U4l|f<_<J0q|8F-rq*p^4XNTCBMi<_}e?K!pu"
    "ZUSc4x!^*cnbjEA{M%bkN>)m%2H63tThQ~<s9pE5ruDv<F=mWOQOa`AbHKDkDEXL_fCKhCchZzrpMTES|B2?etuYQ%)Xtxb>"
    "S!C1=q=w4O2)9)8Jp>pHBUV%?GX8o4O;rn3(jOE*f*UoiLvBd1SzY{JQiXGvfQj3OL|}sq9R?$grT673tjRaeYz2IkMIJMz$"
    "e;DY;@c#6j1%q|uiHVrF<rwEs#wvm+D<=8yU1QzQsNY1us>@h0Tw7qBpnc%kS^Em1EPDyWC@UXWXeWUFB=!^NF2!tP~ripNO"
    "LWH=*Lb9H^a9~yz>ZY&}c;aAkAet*9l7~|w4?P#CrdpPA?RS+LLgOk((BQxr%gPB=HB+>D->FzD1otA*kjUkztyH{j^N`gXR"
    "aG;L`rkfPiO*|}PLT45-@>D(EK+wlyGMl3BgBP;@7#0;=G=b;n@GCTgZEL<Xi1RQxIaDlB+uK4=+)UCUL{<?(x%Osq0P4N{8"
    "UMHY)hwZ(LE-6iU`tSgeFVr!4&vSF3bI#}FVUx#WATdIrd6$YCy$v?|DyS1tN;}tST~GWVT+lF37Ex?Va&NetjURhkvO6FAG"
    "m~uFiwlFpW0c40PTAV4}R0me^c%|mt&4wnsq(05FjbtVA5dgCSZ){a3v(+p0(wxZ&V)}>(2ZteWd)HF$1-HWbnEe6qE&9-C4"
    "I1^$j;e3Yj#Y9#KUo2JyR>$nd>ZFr!sRrE+>FKzM3KqfIeoXJSJ@Nz70(7P_TG&y!a+YmD!+-1DD1?Qr=>b~m*jGD_o3%n^)"
    "~v`bHIT4mqc2giRqo%@2kWNMdt);!Nr1gGTN`970XK-J{D%mjr5Mf;^HNQl4YG5*bQpVA}^sG$WzLdggRWV3cg;hsA7`XE##"
    "18w??FPW#F^RHmecnWsFMtY;==H}0%Oe^eLr!I$Lc3xlRu_X$=a3LKN#~}zH&5Q?|5!U-NRUnbyAhwY2xdPTMkV0n@YY;-o5"
    "8he_V8qGPK3~=+J*2kj+4pj)Vpo_klcT+3Y0z3VF-KPzM>vYlf!a?)B6?`^xIJBqMMF1xa7W@I&CWTiT*_bG4)1?F_Ip+8)|"
    "Pl~fSwBcohN;tPs@*W=FXwLoqD@eGvj&}5E{(5G3(h0bZ^EZkn{qdllXQAPMyJIp#w{m@<v%X;_bZ=K!YoIKs4Y;St)9|u?g"
    "j@cL#i-PAdX?Jm|;JbiB5LqC>sdS&abq^zyO3$HYTOQaZbg=qR-<f(dfE8SD}AZtqOEWbQ{5ZhLLxX)rp#5tSa%3RXRu+5fk"
    "RmdX!hah)Ml1q%mp4=Rkg(DWN=P6gv@&Ygw!Oj<vXiZ=^<G&8Nh20!5Xj|4me33S&}cgR|hQaXiaKKV_Oo@rSYD8pzgjbF*5"
    "z)PrSi}?uL=dGvElU&x4xZ_i~BD8w83ShV_Tk~$io|8^M*1+6+ELi4%%}~|P8dn^?EaFqk4_p&OZ_I(|Nr2<Hbw)=`g%I(U?"
    "0>e@c~XzIZL9TSWP6?+1?C3Sd)=|FE1R#qU{~uUrz=B56~#f$lAih$jEpi_k<Z?qq+-JUV~G1Cz<eIVMl={qwQTJJK*7z+@V"
    "#36=ac5)e)KWV1du0pQil;aCLDBkDKOwPJVlB`g_|%9{O70Y?C+}v2JqQi7cQzlX{nn1wlx*F<2Ww4%lyxWQooSL7(U_kUmE"
    "cR1qC<op?j+dRUZGQZ@jnOoMpf+P9=Q+1~#5qN+D6RvKWWZVQ~NUiZ;-<J9tz`dHHw24B=+k^DonLC{)mKq5qVhzvnGvRW5I"
    "lO3c3{E1_j>jcqk^gSp-cRK+d%suMZOjGP89FKaKzg?IS1x`j52^61co|03Q%6lx{>F?gpV$S#)FX8FCK3gY)HijyD-4cgtd"
    "DYv6IqASqrL2#PfFqkm(F4pijaV98AQTJ;A>~*r^H6{1qQI9uYC(*k<aTxfJ!REAYrA}-A^crx2^qx52CXokMMJt}=<E^obi"
    "Xz(Qk7JL7hE8^lg|l^t%yY^gPTDTY6R&PF#4B?_g0$cov2DE}vA|~Z$|&EkfUZLFr`yk}jyZZw`2ZL4t|vLTNQe@7P<Zy((="
    "9?A#>ZOPl_VdoSrQ#qydc?vltr&34ZU*tlRd|}fjQlS_s@<Hp=ze~zDAXE!Wj@BXB0FdgK)jab1;GS#63UegBmr0eJ1q5^Bz"
    "5f>H>&0NcFAiy%hht*CXk7&a(l~68?)%8rtx#G<vw`f7d?vKjQbbE*p6-*IpmA(<bswV7=fgx;s4yc_-*{!+A$}hcAca+Id9"
    "ceOqEwisO^CnsP0(NA6IVt(_|U%RA4W;QEj@AU`CWI~c6S;jHCV)U7*?21+aC<Cuka&JO5zY>D>+#8h`r)C#z&kZF7VWl&RS"
    "LenhDqV{jy^9%yEl~5zOuU?M@;X30Xl^ldPXZE*f3<bv~zxpO_qw<^;MG;4)>s*)xBsZmG?JI&E<Z+aUi}p!8Q*g6nDGI|4u"
    "m^OQR$EZL@<oSL(MZjw%7qadq(XxLd6uP}p(Wp<9j}*Ml4A?6SczocS-+zS`G0rsC=&zsx^2vm824t77u2DAePCcsM(HDmr}"
    ";?=KLCe%IZz=9)D9)Dze&Op=Q}yBFTPB3lK{S_3uBUZbCiB8S*7ol56dWh24^|~MnmECmrZHjjG5jgDs%h25^6fPBBFQ3qf)"
    "h}DYUXKafB8}Ftu-o)0k}jA}=JyrLzib@y3T7|CdY+z3gHP{T70+-RHH#hQJWA#b!LS_K583_Gcg0HO_#GI8==gA!Ea{$p3-"
    "VhpCQzYstN?O&g+lot(n{xinOEUG}$MGZV&o8oq5y=%Ef$VjlBeR~OndSF>DE&_uy5NnYM-^W^Vhtu6VV*rM?FJADl*2X)9Q"
    "(-*3c2cIDpNyPWR_`rswH-4?5B8LlpZ|gK?`QJo!I2y6tTe;OV{p>fWugJ2-JOyX;D1~@L%4hEvt#O{CDEB^t{>w|(*?wuzz"
    "*}*g6T}^P^7F?DOjgyI9a%^CTC3{SjfJB+be@F>bE!fY@#6druv<P`#%#nT(`nxph0-QCzXuG8XZqbL+t|3QqCKpXTvWmA!M"
    "_=B7x3iQYKqUkLxv0mN<?{v8@zrA+xEH^Id<3bV$v)bB4)g7SoXztyZp?op>>i@pS(yIzo{fsWmj(CHjOb`7Ok(p8#_Gt44R"
    "`lXfYfpKamYIjt5hZaKzk{pYzQ!A{UvmZYO$k=t0RGyU&B!zOiNv@3yP<KOgT8gKu@2N`sV-Go<6zsdi>%7bZkD8XB~=I!sR"
    "WKvwGd$VM=Rs3FtgN}x4>-YMx${~2ST!RO(GmaRqAZZqz$)+aY)b;T<rldn!HXfVTL(zjlfKfII)XY^3SoK#N#@JrPv99e3L"
    "#U#-nXzAySk;22nKXYRc0w5sr`Gw6lD5A}VvWC&cP5R1`obds4I7y>OK|VE^77Y5r3cR;bff9J=P(O+w*pwoIL<7UCgFr-T("
    "%(*c#N*3{evoiN7~3lyb(G|L$8^BWsMq3P*3N4DntS}5I$4Vx)aeNY?z2`6^L)(NNztgg%;5&~w)@M(aXtj1A;h1C!+y>#j#"
    "saoX&yhk2J)95m*@>*XdAuj`~Nb%$6w<rhF2Dve@T5*70@lE`aWIIjLJLLfR&1WhA)%;#hia=p@rxD{#5hAfND6X&5G^iNZ%"
    "XJ+wkW3z>>qPa%?oKus?LWZzhj;m;U<j!Dp(?O1tUhC-nnL@OFR|3^cS6cQ~xLxOnglEKzL%+q1GVjEK+p&gX9?efx2<zo53"
    "@GK<h55;)^co?34wmvKStJn<zl1p-UN$seD4J_#>|_;weCxy`vvY~Q@Ob9<#>(7D--nrl)L@)!JyfN{BA<8qfM{u$hquqdDe"
    ")jpRuq^nym`Sdnx8KT5sYoqaKc2eL}+s7x56XAx|v8DR0OV~GGRH@%aG)9K0tB1$?`i2Y*tjZuR(<#<tx`%H`ET5Bqcx)S^j"
    "P!ov03#;sGv@al`=jLj-fg-%exs!dt(k6GEUTD;6d-J3{}FT##Q+-p;Wfp^yG<7METH9p3YE((HGd5|rz<WFgfE0ZN56><)A"
    "VH}ZU6MR{1LeSryv^Of9gdj1*Fx@<xt;;mL@2Ptekm+K5f!xfq6b&7;S&d=%b9LqSjH|YQn`0Rt-;=qUuG73f~IOpzwA13Gj"
    "a8bW&VE5;y&HI%EMC)Zq&EQJ&};tTvS6aVe%rR90}a)MB5hs#!8<ltPUEL6?W81gO}*aLCPat#B91_a+J3RrWH0jgoC7Do*j"
    "6Xb0Nj^NtpMvN?gOO-@CbRcO3M&bz)g^$0@St`!|k;F7#2TOJPD1l(j5CmOx0t|%|K(tR((QMek^k1bC-9*$Jh9`~7e(qDMy"
    ";>HYVvoUB?CwD+2d=-r1P8iy!>&AkHhUSJx2@Vbh=;JGS(n`Yy+v#Z*2ORNu9BS;7<#Y4IrmX7=#rz<5`NTwa)NvpbHGld+v"
    "67M+pXP)n)}uEXl$|eU{C#W>pO&ozL%h>kKV9wN&+j&?1iHw5BWAd59=Q+YzU_7kuIro{gjX8r)&Xji_83ePW|rO2C7fSGVT"
    "jW(DEDih$7bK1S>;`i?<i?$U}q_`akDr)Thz0}xh^SunIgx0fbzPoZfQjO=%bBlFY0fG-}-YjznN{bTXd7{W1w_^=CNbdB}_"
    "l%ikZKrK+BZJ8xzKkfPd4W-FjOqB7R&N<Vi>VS|(sD`>`b<t6I(5b|_aLrONJQOFAx1l*qT-xGiGHoA2LuAY>y(hR9S|W;aH"
    "X6CZMmFUN3qzHL8k_F{aAAaU~{9B=kZMVV^LNbI_>9s&a58smR%R2&UoB%2O{9{av+K*)=9IwJr2&Q?7`>&dKDwA1=II)5d9"
    "|52JqFk$v9#yow>i5PB^YtF#;7yEJ<D#24aRFzffQlrs)4lf}toOQtw2g2QJFR{^OHnA~ofgOjVa<{wfued>-0YtSwL#q@l5"
    "(v&ffxL{M?VUu|t(&qp_nKz*j;eRHAxdRqfrZ*J6J{(E_c)Cr!+^%qd1P(62u00{G#Jv0tDTH^4`IR8;RFUd>mad*ZBg^CKR"
    "-jW3o_ze=dp_*4#HJjEN?mMw%Vh+Oah{>$wYzs<ufk0yL2B>k%9Y|fWZ9tO<fM%k?Z65993kqbF2O}=NDLLXn*?ug%WHqb@1"
    "K3_uMM>{eCPu_+v1~G#}Ds75YXK-cGKEo*etfHD1Jh?6n-6P<z`}|F4#8etHyI4`glZ6KSQEj8DP3m?2^O#an2~m@o9l^W_X"
    "fI*M2Y+P40!-U!<w=LIX*jXSPg)-^jXi~aIJuu=A@3++wq!6hphd#buPl%sy@&&nq@2=2)a?1?UZ2kZ4z#y<6)@e)jZa=+Dd"
    "6`Qdq5ZNavbr)ah*!5#5<2k<Z<dIzLnW&QP_g~>Y7P<iFra?ZrDxqBAKh&YA`J!4&B!-?ZCOrII&r!?DtU0t$vuBnY?k4Li7"
    "^i>F&}KbpyMoBL_8lobM@fDD<diw9UcQi<EL(*{Ki(y9c>p0HAw?M_p~%U}3s4i9zF~h3>#%EZj?4C?88YqC{}Krce1k=r#d"
    "paW*z~(4<`Y;`_&tkbo`<bbYFa(8u;w$w|4~B)DaCihk1AxSOr=;c;4adJLu(W|An4!Yk79@x*x&1n-M)EGN**KuEOKVl$mB"
    "%~>J5NvVjO5zNz#T{S4XDN$V?4-Ql>3CMxf*Q(+vmTMa(TyW5Onaj?aR};QFv4C{c-xIPv8tw2aW8mHN&Kp8a3Cn{fOQl5@}"
    "es{j5pUEl=5+z~{~TqI<%pZf}&Qh_ru?nw}1Hj&fPYo1TPh-%&(06&9Fyjy!cX|u(q5*$n1HQp0(KDOFZXnU^0i@|sP`HALI"
    "Trt8gU?r0Fzwst9W)|=_5u-bjpB4=Oyi=QAIe3A|2r~Eh$7<Tz6@01))PHah_1s{^938$qE|bi~mBl4h)nq_@!!XZ<W%vB_f"
    "!$!ty_`A_OluYk%Fubl(+9}wlUE`7d)ksd<yoz=MJl`d0_9*)w)hWo*-`mutz81XBFY<6a^cb=(JSM4WBGZ#3p>Y@-5X<);0"
    "EoZpaf<d)nbk^>fa@OQ!FFbBILYm6O=RstSFcYv0MOmGw|4MKF+v=&pkN4aX;pe5WMHo98JcBD(0*_PA;0rWV+xg=Hm8txMG"
    "<s!2eu|Ji{BS#+2zrTd+0vS{+<}Me-4`_5jWNM%oq{?vNqNYg4w9aYVYgyLNpQ6O_&)nC+&E`iCK)>wi!JR(x~b2ov#`jiZs"
    "wk4wgwYorC7f{litb5QvsVspJj!9D>vd~7Ux_u~v&P*Fuy==LzB=9xc*v-ZfDgVp+b-ARRT)o`a7ZKmEG|2`_YJ}Jgl>L8i0"
    "e(rx=kTdfg8Nb&r77wx;(+U@`ZUn^lZT80c<bFvR{UzAEw^;sT@kTlLwO8luyAgIA@!qI0R{hHnkDW>oRp+bF0V2J51ZVV@1"
    "!T*O5!w2vd@@mV-np1+i}h_?@tIYw@@wmbs4UQ;gs^~Bp=DQBd$_Zc(O{Yik$iIT0#U)|7wT;Os(6$p?8K|>Q3(#|$`BC2qQ"
    "of{K46sSPHqo;=H~ZaN}TuGSQf~#+z(<SC*Ps}4@KhSvJwxAC-B{|%h7((iHFy&^7GhWl#f2{LI{_vojrezK}Wq<lVu&(m+9"
    "jHz^6~gEx7U}vZScaSR@aXQt=B`r=&9o#VQ=bW|cpm_s)1Ww$}%oz~t?=`4AT0*rVW0ezEN={~@057B|u=`Z(TM>{Nhf?Pif"
    "l56vvL3f5pZxj8Q~Ys9y;9eXs2pb%3v`{N$5Su`-Cn!hvdgvay|aEr613rv7|oGuu$RPVQ}<9#sSt=BZVcE2glZgV-Frzw$%"
    "w&;sO#!a;iZ>`mP85}{Zt%+DN3m#?DX|#^#zManczS|BBR7^?m1&kRwuxP%rpulh<gu?xE3jTjq*uj!3KF^4d6=A@)hU`wDX"
    "1!I{u<(_tw0ae1@!f|&ck$(KFz)^Lo3ZWDi$jPjk;3+TBwD~=Z<F9$&Ttz(i4E$ZPgE1ltE>U=-ev(RBbP^1&ndbjJ_5YouA"
    "|hv--X!}LWz>%7HpQdWrhxe-H%brDz2y9EEa>S;c3atigGDtY<2l`o)eWv*r<sujZm-^4COgLN#q6*7do^x;0e6{*(2yR^ht"
    "1(%j&}(oCoNMg+&CJU-9jdj|3|Dw+jkI8Qy2yOwDr&ruF|R5SP<86>a3e=0b1b{zj|ur%MF67+<VTc;sGUWdTgZk_WKH*{>A"
    "5<H^1-J37%<NKY;uC42ypJSQE_e*zo?<ZS->8&ZNf{+ELi@rvBUax(K=2L>W!5AdmE3hBA#*RU(_aFpYSEg^}UczlLy_-rA^"
    "W~O$FsCV3fMz7E=hONLJJT@1<UCcdhDQqI_57E8M(Mh0wmJsK)p_FY9a)9h06K<aKvsX6dSvMC_mPh06P-ZQ*K;mh-lPLqjE"
    "b2P$CnO}<*v-70p$GcG*@HMqw+%4a8;`%;4z>5XfKu^LetNy>0P^`zBqoFTMNA>HgOc&LICJRp;w9Nj_BpK;r&H$}5rI_n(W"
    "epYgeSB3Oj}k~NohpsgM&b08H}n==J@u1ej>cP9U_3<7LMI-M|rzP@{MY9xjsGRhp)WMFnkeJym>jCZ0~3Yo=nxW(Z!*ipqM"
    "X`)X{f0iysqkUw!7#Sw$N(jo=)2aSk8>{|<xmkH71TvR)h;<Rt~9Kam0X!{*b+#+qZPDiov|pYdW8Va&U)Ol00kQ~mvGDses"
    "shp9Ak?~MmVhrKe9lYc?}$9~YsI|i6<qa%4mjmgJH8xIRbdF8Qui?BgPcHyUYQP5L0zAkzKtHXn}EbjrgoRM&!mC87bifJq<"
    "47mjL*x3=4Bq5jd{|ta`8hHFlZy|4x5twfErwQAuq;r^*WDt6ddqeS<5;>|va+`#tyBi960|-$S83)LmjYg4?a<<Shrr11~!"
    "|`xMVy5bK-{WIHfuCHX9z=3bL}kgX5F%SKM<&>(ZX8wz!QQX<hKvJcTw{d|ek1%C?hpBD$!ae`)25Z111q}qyVH9#zeYK#J_"
    "1UF3^QXil_U`s7|IUhJH1iM3J&^B3$P;_r3BXc(U_P{Y$HPE@$th%Je8&)vQA{30b|dyt#<rN$G0MOolMBWqh{NN-FcH`I)7"
    "0MCuIZp%e1?(64**drYeR41TVHVhgC?B+7B7u+wY*g@Q#wH31v#rUGHX!<im?g67Tr<Wf0+HfbwG56wHKZJ<O&2-z|{SwUO0"
    "#xR(r?&1sAQeHRXeE9YhyE=1N2UwxA~CRh6e&p+zh#Qtgviqpp=!FVNm({{bH-ZgCU!yen<_yotz9Biovt}!ogybZn(^Q%9~"
    "*u6lC-`7%N##+-9Y$z1s5<>9%3&rx6xu^l8HI^$SVog$<tXGb<LaJ>|y{w#(4Bd1W4`0GbtW=jC*1fQRp|pPKA`BFT<^^m76"
    "E-lHPC^$05(DT>KF+l0X7CI#&(o_^e<ea7^){$pa=&~(+khuXrW;}e->9XMCL1#4`m3ayqD7#@GY&dBd*pwNz#Ad{C8_)+F~"
    "IrPg=!%0qtM+)<HXl)40M;yFBn;nPAx&f`T1g_f6^?GBWcWr5eSe1nPMgTY`ACNxAcY<%TY!^Jc<WW+eo~yce`pvi<)N>`dR"
    "`J!=7+KJw8Z8Pl3|;ws>kz$2m&aGeTw9?1#ZZT=&oWE$1$NU9&zRo;ehSqU+x!6PFS8uQyIe7unOZWM^*a7u*oir_8NMVkNI"
    "f%yzWGW0DI>`t9R|6>rXu1OqoVQl4i&xRRhH9fJ%s-#bcMdckNbb-QSjE3O@BlxJv3xG)BXtOiP6Uks-?e?WaIg05=*)|^@)"
    "m7Lp8!N!EGAHz7+z<aU}4g%v{%&#^)3h>7s1=SCHN?F1O+);t6H$RA^fVTkgAY(G$m%qLQofH1gT+c(de(CT=dQG3~a4DvWv"
    "XC%XbrOa!dq$55Z|wfq2b}lii4509$QU_VRw&UltL=B^hq0lb4e!a&hi+jkzVJ2MVvcCn5;&JxGQVdZi63!S{RH?1{M(;2H7"
    "<W~bzO``*KuGyC-6ZT0<&L}z+uk#{&D1}q>bwyah$FNTcLpeSCS=LlX65@2+Mt*{<tm6U?Z5}S{);b>L&bwO7vZYLYMGOI|7"
    "gWd32%N>~YlW+5GH-O{yz1%bj0o84DaSjV)?uJd!avdBX1NruU`jw~S8uSBKw=KwVh<A)0F00a+DwZ!bR|q#|gRP*>or-gou"
    "5I-Td^;&MF_Ts^UFvAk+~En$xlWC$Ypyqs-~_tcM_J}PC1Km)%U?p|R!8HB(31p0re0ay+ocEb%+KA63I-^~aNge_Cb$84{-"
    "PJ&57qgn6+ouOFxgv?|ARQhgNI4hGj`z65JTzns0^#lAY_`_t<Y#o1fLR_v<nt5G#REcnxZN=H_u-xxt4bz8zNtMJsG*LOC%"
    "Pqqtz!%oenT!N!Xqw{dNLP{KMLr+*VZVEQhx4s<_hzmam7<x}&Jr?Q7B~%&9v>mA^!aejyawfKGNi-Y%^nrE^Uuyz=RwLaS="
    "gv^tc7-7zQnGTbdE|Y>M+v1esnI^@MiAJ7%CgbWVHkGjN;JJ>0GO_ci3#<`I7r<ZCM%mG|V1wlQCXjO&|JxUm!_#j2o=!nk`"
    "LR#Y!()qK$98%4OQv)=eHUI=UJaH{h>Caa{}tZG+#O)lxKgZ^jd|#L!XCWF8akXI$K@aBXXn3F5!`f2sB-*7}S;F8PYJ62W`"
    "ys0mG4X8BT4%dM=AQ<6rsX5xtBBPE`?f3%1V@;)T&tY$ii70?CRnqsVT+&N<q2K5F)$%~3l5>}WdNc%i_$+IsZrtxgie10=)"
    "6#dyE`)XEb$~^|1lhHoATM2#|4kBf6&mA1BB|-ia(nhv5p8r&Q`r0d91(wX&ZL*(i_p>Bu;(pt2tY)-HEmkg5#-^xav_+pqM"
    "pvg^v9x9W9#eq7D<`ia0~_2|&OlP=u2Y1HlxsGM|K8jg>3Dt}&6*HWB{-_l{YuhlJ9}SDEk+#hUh(1qeG%h&uhaKe+e1kI7q"
    "y8E*(%muPAn(D=PteD&3I6YZLJV(ItR}__E3r|byQrijkgXbnMgLA06US>m+a^sIqtO^bAsEJ&qnuvXx-vo{%A@dJ~hS~7HT"
    "SHN9oN}i>2`DI#9*flq2$Yh3Kh>FJoqyXAa@Q^L6#%xfy&0Dy$8Yv&%RwUN(37;EsCfkZ=86d@wB$2_A+Am+IF&0wj2`m#6_"
    "XIs6g?(!cVkoH-l>E-c%*Z|M!{WPP=UFe<IwKBU>`c1PfnkEvjstzu+&+(kA}4<GZ*>N9J+M!skW#xQ~F(|V|kV*a{@_st)f"
    "C9zQ>B~s%=?;X|ip7^Pa*Yd93J?=7wCHWqXS9A#2l5l!>?m+2%KGR)4Y18MOm?y=xpxV(xgpPhA_zzq_x`Z+pwn+_Kba#@Yy"
    "&p)-hCZ6L>n3Mo;f00IL>eWhy;CxoEn}6}IeFi=k0}pJx?h49pxk;0-X1QS%Ae2fC<Sdp5g0cnF_-n4Q?S?ZqbCH7ad}2Pn*"
    ";qvD^Ifn!8Nv;ANQp`Ir()j_Ms7xY3D$^H1VnsO0vC)1Loe|?(q0DIC@FA3#}xe87yIw%k$Zpwh}`Gf=XAEfI)H{($LXdFNC"
    "-Pckb<4$Df)6sgBri;fX|l43E}n;5O{7;jUsrvkho1hfpxK&I7+y!vUKHbiOO)Fi`j`juE){pvn}V-c)qkC&EQHdO31Id^EN"
    "^rYOBBN@<RM+nEwS96%#V9LKoZn5w2v_|?t|YVkI5<oWAr!`kkFuhJeeYqa_SjjuvswfXz#pr2k_ItrS@>b>SWpH7K<N?aNE"
    "4#b4OszQyPAP=Y1cC(585}{sv9u5s*`~0;pp5XQW1u-BUs+ft(PjBLY`aJ45Dcr14?xsLY^>d_-;N;<n-2s}N!7y3f%THZ(j"
    "nAWlqwS!lKGXK!5sXM23wvfshJ<ttOHuSl(+GC7fXT!o?DEuZRcM<Xn8n7WPmVMU5N$_C4eiNA*?8?GyP}aJuasdUL7K~Z^("
    ")sqU#sK2XR(fhaKZ7m`?tuj^B;$X8hWIGLGP{_4!KXEpEj;>ie7sSvk<k3i%s-1J&F42ga=!PKoHsG+#hsPVwEC<WredLgK5"
    "<L$GYh^QHRwwL}3YyHczjgn3$YE4E0QvCYRBpR4ErzgY}7Ie32wEFZmi3aZ<+kTI!*~Dz}p(NW!A4I8uwm$7ucm$tMpV=VEt"
    "(evql9bMN;b0x9|S*9hcm!E$7Nd6ei-kdP{P|Kq1NMG?k4X=(YctX!?^_al;ly|N-@%zI~h`I^W+N~?Wj#53{QEHF=#SGc4O"
    "&ihW^DOEHqN-JXxVC0VfXpZP--;l{^QYUoT^EC#)cmF_3%rbrGm>Eb_4yI;v39!?sn95eoGZRPT-I>;0T-6_;j8!x=g~f21o"
    "~9%@`W6Xe(7mmvB5}TP&jE%N(BXC$7PbJr-3<>H*(R9}SGs8HYsF-T?hbWh?T%lOUWu3tLlobt>~8l$A7Zj+p>dubw`N*ATf"
    "HFm_Il#P*5b}yQnDgdbc@>sE7@8whPDO@vS2xSY(x#tfPIhyCVo*wDQO6eppSCEjtrErXhnO0z)pt*@u;Pzu3L43M;;2_X%a"
    "8-nF<8@61i*71WhzP`P7qe0S-JU7$CXjYKo!$nhuii|B9)xpP~xi&>4d7i+|~6B9i%B*qn(y3gB5E+dX*n&)&P5JSV>O?M>u"
    "^7+HUJj1RlSBDs!~$Pa9mBaW*Fb&v~-DvLrY>N+7g>iY{cQ!#ZMY%`k-ejMAM;G~VQL2k`hbTBagXm@e6BOLFCNckz5&VH77"
    "S40&BTlL5)VEq2Zb}=V^CeSA!?>dI0$MEOg2=Plc^@&iF@YK!VjM%=9_QcC`Z!_2}*q$R&H46>5NzG=^)W?i)d!s$1>pp`WC"
    "5oGj{PbbgN)oDvs{li0i*K-r>)E)ll%0gl<{>$3-en={2e?rd)m*^V8(;2geKjrJ&1M*!9tr9!OoPXCOi&!oTjQfK3ko4E@c"
    "hCZ4Mpk0M9}!=tvPtXXX|g4I7a(l3D~?OzLp5EPYBkv?N2;^wNyVogAIP#Kt&EtL{|CWhw+;i0j7QgG?$kZnzN+ZUsjY_;(7"
    "rw{3dTBgO%Rw1pp+?=L!*63h7jfY;LdmxG?Euv^R%`mNoUlX`%L97t3C<T^xyuoc@jO1i4k>25H}_Cc54<v6KfjDr3&fy=$t"
    "(kUef-efCFJgM500zPJPVmhtBHv@wS1DdXjS|JFNw7=p;Z0$&&3%-Cgtp_yqtLQnaJ(@G+;Gmc!3CpeD`S%zNF)q}{70v$Ex"
    "WtyA=%tr*&4zG!ZFtDk3$M<X~`9>4;+-hV~!Hw5EacI>c8+r%wF@c2pw_Bv3jyvcs!1A=|tr+U-@tB|O=jTMcr~MS_7o$g#?"
    "c@M+OJP`-_a39x#2bUZ-Zf1-@XAI`4iu74<N?ScMe$t_ZR6hrLX2iZM<0BJ@n=o~twRu(n{JExd}G>vCm?`}tdp$4E)qoh@X"
    "rvxCY$>1nDdn>e+37Ab6I{aZMTo-Q~XE)A24Hb<>vks7WNSR9`#E2C?Ox`7k&FL2rfZPs15;K=`adTLcq`25`?US&EFZ+3Zo"
    "QJwW2F*DbNKRTnE^>U#oM<oZUy9+gz?eY^!0(d*IL0gFdyN9RiB&tDMG+vU3J9bnEw<CNntjhQCEg;ge?f15#Zn8{;g-#zbU"
    "k=NypvNIAE#m+_gd`7B_F#}f&7Y`dX%EE{}m?HBY>vSsk4F=C=oLHm6mETM)JPnSFj+Tc-q080196@M&(^RNTLzh+GE|4M+t"
    "JKh-E?0}IUfT<@r_C>`v`l@7V;A`K$M_eIL7>PO9+5*DCxrj?9n>9+MB&i~t_vyKWgOM`<FS3_s9vf`Y#;xegV8uUYQA4>c{"
    "TU|B@Yl@r-hK5-L&qJqKD(|z-B6tsK$^j6hUJ@=%!m!YW<MuXUaI8}-?z6(#ixo!HbN42C@@3ranH=4Pvp{-8WbrF=ZDGW_H"
    "ffxozlQckoBz?=VKFYDq^NCqOJjnzw0R`$mNCcXaW0{d^DW2K=336!IViMco&eY`RVkRNg8LaRpAW1@-<2^deb+$DB0$Z*49"
    "m7#GoDw&;yB>4tH1eciBpw7@bfPzWjZ8FSO6}w4^z2BiY>e=e8hu*|eX1D$l)7O8k#^9oIQG?2?qK|6eN)soIWNV}e&(rIt#"
    "I&JOuwzrA4xaX6kkX3@&`8lZtMUm*Ha-RKraLJJ8<X#VqmnE2|yDEpx6C8d#WkdW?fknV1fM!KYPQKVbCyStmEyOEF%Daj?5"
    "+*iGy=lQ(<!1cpiGv~~lGxG(C`b4im7eE$~IE_1MN9{MT+hAWjV^3YNM=;euse|jh5^a><n2<Qtcv3=CX|+XCFpMbZGu~FMu"
    ";ihK`9=_5f%d`_)bpM-rL-jB{JdaFZ?3}fe!tn^(3RUA3?4Co-&DM2v_!#(%38QPmcQA#oEeF;L{WK!IuAwLJQH;z#b1fRZ6"
    "DnHZI~IIW~MEc_-TSE=bb2U5+oG5fus*)j%eJOTvj2%7e1J28OkzbVr0;tZA9I=qlU6>%p=c4zo1<Qb|lljzo$;7_}u)t@}h"
    "A)ZSPVC{|s9r{NX`00#JgF*P9GevbM2xW7GF@d-unMhnF^wwN1__V7}u<HRo5h5YoT?U)+D=WZ!P?M2T^7VUleObE_pvAMDn"
    "m{%W(Jn^ZBL8?BuSktE)OMsCxQN=AM|uTp1Blkqr$zi>R_q^)UX*`<r$o79?*lG=jrSk*Dyw2a!^c4;yIVhO>q>gu_baXr#U"
    "U}-<cK@TkUj1S~oao0&!9m#QGcbAP7oD$1C$pdHxg!6UhcPv$}zN(yaGlf_`M}`|ToQ4IA6gAe<GlK<JQb(n=h7Sii2d-6$6"
    "!)@IbWhJDV;(4{`)@$$_8?(6u{(ajy*OphAxdLItzn5)PA#<+FGST)5#eJG+o1c*a_Dss^%T&6!&iOp_YJNn$e&1;uGFP{Q9"
    "{RHFgTyj?AKZ073*u*oxeX>@##s~-2L*5evAh?=E5;O83|Vh$wHUn4qFTyUCg%v#{B>WC#$1mfpMgjIP;r%G%@GXZTVKV&{9"
    "w;*hOa+a_IgYtz4(y8-_^6-)r&4x2zGyMrQRHb~Lm+Dv;yRjs7J;+zHKrG~Y0ZKJQnz=(~6Cg8rGYs-#A8F05*<?L!hdQG7a"
    "=4g5msRA<YMM!vG<=RbsHI&HYy!<*S&CE>RBB#z<RdH92dFqvjtEMBo|Xd?#8r;5_qVbYL#<r&MngkOy;8)gNWtA`odU#&S4"
    "21>sq8keH2MN2a|_8lNf1A`*U30v`5&5mtJHvD@LTGxaQrN_eH%Ma__3izPc)rL0d3X#Cyvp%W<64$k23i*&ss_EgVvui&@#"
    "RYLDG^VJA4VfIPwtI*uuNhDi8vzv>!Lcw@n^LnK$LC}!8Y{K6#fU-^Oqz~>z4!5ji>xraq%1NK7IEbMc&xNX#7W$+bR}U`41"
    ";{FqGE6_2tDN76lqyyP8Tm!KRPgLSB&BrM+6~aTX-bQ4ZbHj{9Z5T;&bl)-PHpN4fT-y*F)&eeWpwhx4}GN2p3_J`vj6h*Pj"
    "?l{)15Q>Ye*l$zq;pF1lIkEes|2JV`zRj+i$9g1bYO#D@aYwUo&84FTMo`#bQ)z?-x-Pcp`((JINXJ;#pqiQR-mKGrU>B(g>"
    "=5^cjU;Jvcu1S+PA;QNC~<P$4BqO@Sv66=!7hk4GWTw(DDxycpSO$^(Q;jCV?u5Rbp8WvcIFfWKd$DEyEv(Tf@>(3p@z0ziP"
    "Yqj&{6Y5kVx%>9A9fb`{WWo3z>=z^J%c;2W{M#DXdlM(iu6~{vT<Xz8^hMp2g1>zB@v!YV5{gE5<>VyBS9NirAoQXV3W*pR*"
    "{OPRGEFma0PAN$!R=l`T-V6lC7pWXeJU?KkoYaji(97L1fOV&(>91vIjAA3&-C4=goLKOffxEe>Gp5<_u)nhnkUpUUmE;&`1"
    "_15f2u%>7%7Kplb>h-ORxrn0r6h>s>zWh<@0j$OytCBERoWjaO;*=G5Z}(RtP|y{cc|F{hbO8%%d8R1Y<WL#H)%*D;V2GI=n"
    "orMO={ia_WkcyvIA%Omt8<X{`q^Y*`wk-|Jzw@nGT%47JUE#}q1ej6YK*l;6L+5hSSMB)oFk#S0V2RCHO28?|~)58I$LdC}u"
    "HjwDPsoI8?Pz253teP+G0rP2EhmQ^}|oh9Y)fCKM+S`+>lyKJTTk6iQN_Zr0svuC-=AFcg;kuI>X2Oy8M+b6Lj33_6@3oc4d"
    "nouETb47c#%h$x_IUc-6*U-ga)}DZ8B&)1EMdxr-z&V_g?O^9ESmI@|H9oNhVXdoGD9kKjSq!r^|1Vhf{sYSok(_Qh^4O;Y@"
    "0mBUMw*(9b-m@X0zNV<F!$@T4=2bdI0|@FQ0#`lcj2=El3~sfg8WEM^j>$FX1VP3Fsu^TaNk-N+e)rh^SR!18Q3Y2?A5D{lN"
    "VHUb+(r?4kq+#eb3{>OZkrc+}dekdOhMil*Y0>Wy2I=`(`~WtB)WmmBV#5St98MT2>-~v&T{F+@DE)U;l(K62bFWWSK(y-Gh"
    "00mJbFubhgZZMR-MTVBv)<|CQ^`t?QDm8^m!(-MOnEG_dg}+fJ@vOXQAc!bT&p9d+}p$Qs6dvq9!Ria#*P2YeWVM^xZ&Kf`n"
    "zj0WF-z0U^gNj^?PXyfKZ8Pz6FsaRsrds+$>hrcj^U-rVNyjCiz(z179#f4dWy$6p555}D9YkzTA?0q{_Q1?OZZ8MSl!`Y=V"
    "|J2@iAD}IB#|!!T&1r=6=1B@hAyV(~!<Il1qeK<8%|NkTuYRxE2l}RaUgPca#mY20ue>YV5Y6x?4f?Yf*Hq>^=?iFm?(NTz)"
    "50{{!)WcB7{GjS<vEO~N!Pc^I9eBW{@#Llr(mZHnA*uqXZf4lAzj_teC;H;Py`L@lQB0Ixa}7!=96cL$T3v|fF{D~^p^MWoD"
    "nusZ?9Ji;&Gck7=UpCn}C?~yi(rkgJ6`KJ+KjiV3e6TU{o1{jGndwQxV9DmN&^*v}F4I^_}Y^AH0c!PVs1eo3nmeBu5o)Vo?"
    "(GRkOpj+8Je)niG>Fy?Bn2?9^7NQmq^b;XS77x2MV(u%)v}85Bf!wp}H${FF2`*s-Nap^kOj-GcnC2FAlqwUNRHxSNBEBW?E"
    "hvC5wM-Mj7kf4Uv)Z|+Z~psnC+GdS_Ff)i!LK+)+4E>u>w-{uKT%5PjbRFXh{eqQfSfJZ~MRC~<)4v1W|cfDGuZPSi&Ofh#i"
    "PhLdZ0;flJCW~06w-lx4j>b{m;A{Q+tOzTGDS6Li0vmKh$iZ)I2QmMkbz`*1E88!ely-Bq&804Gp7_Uk@%=n4$x2Y4u$>+<5"
    "Vg;5$OQ1Diw6cG=*<$tw<<#n0gw2gs@Tqg-6VO%nFjV^2v*44_x)U1^22}ILb-!FQ57M3G4^ddd~p%u;<ry~Ykr&?s>u@HEy"
    "IUAwx|~CpV7ep`S(9D@k%d;xjsI3Z>E;GA9}f$1K(V(@Yd?auBFkzqMy@KyDjAhd9{?Tn_2S@c3a!8ge31mseC55>)Rc&_{a"
    "eTgS!G$$N+SV`!#zaeS<OZ#Dw_|8YGFDKebHtFOuJ2dL7f;H1Y<s%G0?Yw2zSYH^DY6!~Ju~ZTfY~xSv^N{*dh-dO!Yw-Yc^"
    "DbLgd9dGe#ajM0#|!#75wRqPB_E$YaN{PT=U222=uvX;GX&V`7G_|+?id8*b}SsakZan3+}ztFQlB6AoMnDMw(jNNCb81R;-"
    "B%eK>6kA17V6JM0Z&NkH5397lRtR-Q5@*|c$J4tuKtx8j7`9`8HLwe)TGCYnF{y#V*Y3^KGVf*D^KszVPaY#>zXGbeB#eHUR"
    "}pH8s-?&k$MY3j$0Y?@try(rCrN!9@3G`WgYr5fj7QuL8Fmlzkp&Ars)~|{{7?Ybj&Z+J>=SI$EBq#tAf>lOWJ>bBV;-Yj&r"
    "!~{XLRJT%X!n!O037%gqNI!En5`}J%HsZ65aUR>9yJvmhkP{w|_S&VQ%NCYEg*?6O_<s1H7+S&{o)5{EZt;0IQ$!r;rh-e^n"
    ")xqZgJ_*}M7#Vt_<VI{B$HP``eeK_2NQIB63A1?eo|FCpHZRHqfgj1^2?)yTB3|2TL=>h-<S(o8gIeGW9NzViuzSa74dSy-("
    "uMdG;1tD*+$80<QGotxi20bfdNT2zs{5|!+>uN714g+)TD*5Jl9&MDA;ktU&pX_`A*AK)4$*E+*K>ySdT`Cek~3xk0#*REN;"
    "jaRWZM_ZQ6#-$5=t*R8%b1GDi_=DbfZEi1!Jw`oWj`?K<Aw6ahDI}3CVipx&l{R0t4wEq+^)53?hE0f>u2{Y-)yExG=3-h%A"
    "aoIQNs~R4yy&J$SRy1vjY-<OeR!p-xt(lXMk&@AO&<0I#a)nZ$i^axB$+!!qQW}=C>tzF-~?#a@8@H5zZ)!W_PH6G0{C>TCk"
    "h)%%3`5t%Hsr)(qugU6#(CU`KxEKGw#xiM=PSMU__TAw}xrrixux`{Mz@>O+;0F0Ve*O3L%3IuT4e4isFtNuyyJG+I>^!eUC"
    "X?%x5$)7!;`#B(eF<Sg{!+W8QcCn9g%@#?%$pFhmLN*fg98$B|jt(`EK-qUouCFr^!lJvh(+#u4?|%!jDDD@j6|E1fD<eSb0"
    "HJ}s*5P257O$$m3sjJDnO*vN9yAw912msh9Qv%{I<G?PfY8fKG$-F4vuA<eYB^vze8Rc3m}_o65f;3PkWSAD(49DmzKV`%0G"
    "v0oszGUOA?@sXupx28aOl{b2LP;?cCv7iIsvPJ?qqif3s&Gyr>-G}B?@1};YF%`WS(d!^q?5_DO$`~9a75CV#k@1<~O)sC*;"
    "dGqZUBpXQAMFUEU(q<`e;2UW|E-Rg;v%fDeNF(B(TB2N$_nqHVmug>fWlCdT(4=7-OV|qMBK3z!9bX$69U!;N`&<kxIiP5kt"
    "xLqi2r9|=@~O|5#H?OpGbsUE;mEtbMHZQA1;q2ezEdMZ*(?u(QP0n8)Psbro|XS7H&zrUl&9sAyVigFLA1*TtU<m;TgAVhip"
    "3sH)stXzDyEZVr^_IJ0g00T|a``ksL+RGooPY9U+0+j4PZDDP@Z)nJg0DJh5Pnbg>7clzcj5|9K9%Np_+jE2$0lp(?+5EsTf"
    "k-yTudD&Oqi{({z(-MIQoG}NLK%Ff7=Uj`cc8S#-MTSi|6$eu#?1&GkmlKNo+-ZY@SMDV`0cYO6AbWiRV?W7_=+J);Y@u}hv"
    ";fN@cH5?%phWbF7oVk53R~`dy8859Zuj~7E$v#RD{E1)hf0SdVz`{O?%3)Y=pkW?t+}L*c16rsI0P#DRcLwRCMDX%#pXNs_t"
    "}-(DKiwd+0$*flY$MG?-|`(J^M3h_#A^$v|5g?ix`&>xif4>*edUoC4Oa~#Sj0*2UKG?7ZlaTG<~@t|FtjNfuw)I#{g8=JM<"
    "@$%&fOS76WP4Nu4i~3`8@(fHd8f>71A#+2zR)ZX@R&klZY$G7xhRlK|=(_IHMoVJr4}6S_HfLbbnEMG*qBGkk?b+s(pzqaFF"
    "0N9+>LxoQrwdz0_t&Ni;EAK=Kb8MvKx-;PZYW<RA~XSfT&^4Ne8}#7)x09Y#>n554caxGZ31SL<CuV0z6I8T;g;bZtb=cc@8"
    "7j3ds;Cycs%Hp3tq7>_A?4kZ|4=lH|V8~>qVLlzEBZ-tbx4)&AfZ(FS9mRbWh?`0@$;VK(7Nen-o>KU^%Gsf_)+*v>DuhXEB"
    "uM?AjMPO5F951gHj^;X~k9gtHADkF%H`Qi2&J|cYyvVosj-X-)b;>gQg6>iBWOU0acgp?hAW!;A6iw}KpskLOW@k`p|EF-(K"
    "arFAE%xy@+2vv}g3*-V5gMxdk&^REQ^sev364ueecZrY6ZogrJ-S}``cUeZ?s-wVO#$0@r4p6|#FY=RDpHIAH23;G(E`zz4o"
    "(|W%|d}pUekwz*RG-?R;THUn-nAIVzL?i7b{!azf6w5X|pN3K|6-jk}+l%Ok$($5eivFI4>_<#x+~7xMB>@UxDEX(AJY_#A("
    "dOk4TQljf3|y>tZN+$M`TKMoFJ2#m>+Xja9%fCW?RB!=JMMytmQayxrMR;xROtq@@sJ&4+p{QxlFC5gF84g6~Gr?glLRK6b;"
    "ZA@BuUVIRe<h6V8-@0WDIKX(gAOTS51@odsKoI(_q+`9=yP;pk`(0@|=vToGdhi14LSpp22mTj%#F;LgDat01lS@T<)-#6W>"
    "CL`1V+K^qLadm)TF_X?OO=9u%<I&)J_cH51`upng3xVe@41Tfb$vtwQ2*P7mp*)vO$=!_=mJUYqOA;*m;RZ2H#&Dv4mL$#eg"
    "^H389*G7u6rbYk_q|C#L2TqxD%}J6T7O|XCVSa5bi)e)>bZj(%~N+nrDUF@A4-1w!oI?U=v~(kLZPEu2NQfa{jee?Dg87AcT"
    "b<WpIwDu-+e!HqNn3*o*Etvi!rdnjtl*hXKa-JYSWTfNtu-Z&qu#shA2r&B%$D;!e?OOG94x?1*k892$(2};;V0`_l7A$?yW"
    "vM-v&n!Kt6v)NuhQiht?Ce>@AGFgX3Sv<h(tEsK``_)@MI4yQ0Wj%`OpZtM97vIa_!@0mW`<mE)@OZ{t}H6Xn<o&HbC*ky9H"
    "n=3mHnyQG-RCdMc|QHsmED%-X4doFQT1wGD{O|G&ox<8FSG13OJy=K$tE+Uu|3T}_^=j&HW=%?_A2!CC0kh5J;Fz^Ul*fv<$"
    "TA#|4Ig_^xwEYw#TB~k7#}_B+!1650ZpRykhe9^+9=Sp%5)MIlW2-OD-rl>eF}P=b#SKHqMXz&vIg<NRQop6OL;+DIJRojsO"
    "N1h_R@L;Mk1PEzrI6a>$_U#nt;){?HhBogr4*oJ(iG(-dx{@a!n-_$7Y$0r`j9Rif;~0emtJ>%;;cWcZN2xc<P>3W(D!o5Aa"
    "v>fnq6WvJVMRurghH6Q1i{rF@A_6l1jD$uSQvAZ}^6JsdcH30WwY3qM81+H~LXNA8Ppga=<e9=8cWeyD0gO_wCm{Ig0Qbqi}"
    "hwJhB)!Q=2tbvWLrX+qW~>3$I{cuqa?%YS+1&Taked>{Q+K{v%8}L_s)TayUQ^|4YjzN>HfpXM5)yT}d9X4hj<6D31<aq#Ig"
    "y*&M@bVw1f$^F{<$-ezOo@-U?f#jzZta<?<=P5705oo%f>k+MQUE1vNylRXV99-p&~j&^}Eef1nN!?RjUl7@6t*O!M+U|EVB"
    "DD|D<)O2HoidXz6Okj=rkBh?{4Dvs%N9=!VyDr&tt-T+tO!rp&0JDp^K5GffIiKZOwY0EO9}%cy%G*S#$+XcrsA9gAXlsWQR"
    "k5$xQJ#3pYIX)Sh7G4V6)z94bqdMRSz9rVc=KAg(Fo!ny5du~k`_*)K6t;9z+GqvbE0N9YRp$8<GvOY)-=w``r2F1rUaxE;@"
    "yHrDs?X%yfh;_zXY#!Y!6NGw^^rsV?RNAJ?!-2$j0Q*);4#+kI7IL1-{l@5_yR__v}RhYZLA@ukOwIy;kGIVkP;46X$-szUr"
    "Jrc^SJE+%8qH-uPhBT72Ef5to8%?_fCb*b|j}4R;s2deSPmml@hKtCz?A@?0(Wdx4ww>*ww#&`EBtwH-~y!8fdmitpD3u@rl"
    "#`TnoMqzVnDO)_ItJQ3>62HvYDJ3psUtDKz7t2?7U>e<RPKuUjZb*LtGU&aq2pn{Fkl{uw+C=C_H5VsVi;XZp8UhbwE49yvl"
    "ZoYrZs$pI<`s6i3e0qbpd$BhY`+qtu(%V_Lw5Cb3p)T8Du0;&s*ZQ<Ftgxg?S+N9rS}c!@1$sm^l3)f}823(#{-B^nMB@2o+"
    "xfC8Z<uw69fp2N0X;f)Y5^gJC6)p@XX`iR+_%gxh~5v;S@%C2b@Ap41~ockgix>bfb|S25H#Dhl%n&f7=3g;Gs=ZmHUfO`&@"
    "R>L23%1KtIUYqamib<p?R_=!&lxS6T@edUx+`(dfteBzuLd(LF4rz(iTwA^)4n5e_4yRAU$TmQ2tQJFHsO60aI*Zkb&8=!_J"
    "PM@~Oc!T6l@xJce;<wiVxA$k4m%3LfO-Xf~sNV_I}%&55kc$>+bdoA_mrPlLQLh&PcujjEpt6ziJw!a`dZ2I8_?iB7L?NVm|"
    "Y5lbwI(kwfw?Ugwn@pb(Jj@H=!Twr$C(zNbCsG6UzlI5DWY|OwCPElfS`r_md?t<#GJPF}FdH|_jn5<zY#KRG<QP(*ym*QPR"
    "@=;48O+HJf(u4n|2+vP~9;W~io7i$px`M*~W>(`666!>ukR(A*)X6~>{~mWdP}fRQK^W!7Tv&}aMzIz~p~DolTm86AXe@CAP"
    "`Vv$G109dXy#m3kFGp=>;>OT3j^G^@5eUbZFo5G0J$A!`X>hfH)3@C#fyYbtsom)ID{Xe(jrMAKMbWQm#H~q%wRMTN%h_fJk"
    "f|(b?&4HZ%g2xl~^EF+p5aJP|~j3v?u59W?IEJ;~^aYeRp&mREX{aJ}xiRKjGJixWH>CKZfc=Q`jOxY}c*+FvceSe-3%wE!9"
    "rmmZY|(BC-nPh5vvZVcR2Ky8M7Uav>jSA(6~LGbD40XoNS<ym!v_=_$Fit-Ede<f&mWOG5&TC&*~qZRGIzw^tu(9bf+3>aLy"
    "&ED21{Crv7x@TQu=Rov6Mw|kvzsVVg@=I8?4pG?{OnN7n4p%wk9y3X5=H>5Y4<mPUAgXA4gAd%?~fOJL~s8ODGbKP5;+Ei*t"
    "tYu5agyN~xgdm&0h9~taD1{vI$;DA#7aCk>^Faj?Bdx8EJ1mDYXN59qKu^0$*lRYU<=xR8Yhv8hYv*N>_58rE@q)SiEoYh=+"
    "rM8eM&MIrj7kQeJsB4Z*oC>}m#G!5`yn=2+a&=XQ5-a?-ajtdb9A5jr`)#wTS|NzzLXdh+V|E<e{li9t<Cb6-6cAcJ1dp+8x"
    "~DeXITE^X6d!GAGD?f8?(p4!HN7T2TM_uJ;0W)(7nYIxhUL$0&yK;{i4qaW2+_{ot+T(LxoMHv&)l`ATsASYLbpDhVUxpYu>"
    "*PgJBb^3AdP8_U4va*cp%dToUT5k}}<hqX4h&XNV1bZ>z^iLV9B1p{%S>>kzWb5{B1Ga%c(Yed2@f1<#=w&eU<t6aSGj@mmX"
    "Kya!31GtiwYk#i4ZWN~U!(5>eoa8JM21cw?_@l`=%F6+J$`{Qfp8JbUqX)7~$V=v5m^K5r0kM2I1vJi?p>(yIwKaSQ*`2wui"
    "_`pQ9VCP+QL{J)4Z^6dmBO?+^rb+In@`B8J`LpN@BXsoREc6XLd{^}U5JbEBV*Q6KQf4W1%p_D%v5@Vrd+#M{EKqe=1t0RlS"
    "JmD$+0vGBYtX`VNoJ|{9tYp7p}BO^_s7{+w(;<VsgzR7n6zVII<Hhn&D-X4<~o5dT#sDNKh9&Gq=zm|Uqw9H7!q-4L}^D)5^"
    "246vHFYx>~Tdk!~~{D0ft?S2N}pR12q{XCbS{fQ=M%|G%lSYgC&ALAfOS$etm{#ASTJSWA0NKyE8FNVgJ^}gv`{I6m+ilw#_"
    "JPvPNe4g6E+2P_xdM&-|1Q#1hD1)5^|{s7;)omD6jyITCzJ;N8?5a{B@E&2+)US5OXw0K@$j<Z=k<{5l23Md7Oc(?Js0D!Hl"
    "I*Jkf603RL+Yb7&ag;gTa03q2QbS?36AF~Djj0sl%`Mg1i4-CEgEfOHYeyeOjh42tRbmCWV=QQLPZYsa&YeU$u8g(T-t3f1e"
    "wTfaiU|~nR2moVE!o6)rLfzO$kyCAUen-|McT9#cR4x*UBM>RA{w`t^nIGh>*>`(TUcD>_I=`@2#up!(6tBCQp+dJORZ`!bm"
    "{5e=4iP`Tz~LtJ=d|lBkDyVd_M46iGRv|&o7oaoEXzua_*%%^C#M!pZw}v_@9s^V!jv?UKEx!{Y%Ry#PWJFx2V{>?*}f{{^l"
    "sgQ=Wk5V_T`>*i3O<NBnPJ-<sG7t*VHO3xK!ud-E+^n#UtO8Cb@$RIcC&C4Pe<foa7y9x+V-#F8AJ~`o}%`$J;{ZN&w|h^A3"
    "6j5pL+h3SDNc)9Ih2f{*@h_LRAF{h(0N&AY_jJlUBq^rY7~ApHv*;*)4Nd0U|rH37@A-0z-2MTF7Mc$t-liIDPu*~0ht<Wes"
    "qO(O2+>5?g@;xB*x%ETqi2zB-S>m`|*_1jYlJX9e5^UWhcw|j`(h+MKv)?r%28e}5oM6dgvx?|WZLmrKwOt0W&g_$l>4bs|~"
    "YbL5ZJB?~{PB8XVIQR4E>3;fA;6V_-H?s^n0=$?db$ZUU0C5d3UAaS-pVurv)E|J&ts&5k9D1&Pw)s)&n0(LCLL@`0kT)~rJ"
    "7Wj<Es>(l&z4vZwxC<({nnpsxt!(*G~7BghO7#CEN&mxDdEH~?J$G(hPz~*_TI}xTO9`wiT;Q}MndA}`)3#iVaX8`+0K4QhO"
    ">?Azl|3R(;=1AhqG1|VY&M8iNT$w&|4{!aSBF-$-JpdR|(rFJ$)$nT(p2XDkG>dQkkCv{@2&n!)Bg!h&eHiJZvV7#7kU~G_f"
    "`R1*99%k*=@PC637IGZuv{v9IJvIfxY(<Qe`kq9sxtAK`qOZTq(r$yzsz0m=&KUFs-vlKsLHz`=oky`4L*#ns03dpYiRDanY"
    "cUsl!7%F!dXv6yLZl%Y<I*R7i;<;Z?B>fh{<+P&uS8f4(pA{Pn|-!RF+E=U{ieN`b$bEH%U9tR?CB>SXd{!8lmcS32V;hM_J"
    "ZybR_YY?*l#b+jBP0**OAIdL*IHc_5=1Rv%iVIwImImO*aO$@23;<b2nIX75Q8oqZJZkj!tHQhv5Dp3Hiv<3DnOXwEzcV`Be"
    "*$o9P*i*OD?oryx~M3~7XR0j#4nnu8s|4Z5*dbu%9DNNNP^3CXy??A5tal^2CsuSJmNfCE-k&@<f^JfnSB&xPn$=sYUxQsdd"
    "nSCU-HR*h2#73#|vs_?4#SY`eqw#yn_OaKNv2U1ARti)F@#az3tN#KrsDa``pU*8ib6``4GQ~C6&dz7C8paoxFht43Jd&Mw3"
    "90x$K20gXn0c04KEKN@O7ZC(WLHk{%8c&B$Xn424K2p`^XKB{Cug{Vq~4eSc!M<8xEX*HXVH&SUFf7d@^KZxE6ebjy`=zgJr"
    ">Z*CroDv`Q`vX<jj<Tec`X~8}Ir0|`FT{w1KDxV<YE*Cv>qfa~%=tK~qjr;cPW#E502K9>Xht{8KBfSPR2GoTS>CD2<O}Vjy"
    "=viKI!~racMUQN*l*EaMQ-tji^7=n$c=kD5uxDhM-=V|sDTO%a)@(nTKqJ32h6^AwGtqp<#v%p`s#n)kL_r4v+>Vw$lGrXSt"
    "o?uu?hasXrK?M#Sz%MO?Ks_eE*vs)^KKmIR8&-3^K-F6I3xYe9V$ZkVb^h{q{Q*kHu+hWGUUZuYa979v#u8`HW_uSMLSSe`k"
    "2HkA-Eo)KqoT4oSmL2{gI2Wr%8eS6(=gSe&KBQa8djD@)X%vO8{~F<muia?GA)_<Vz`<-V_hcF-TWmICziTOTU>Q4{(3dt(&"
    "*eeT~s(vIWF<w*u>!V$w|kgm2%vVE-p7!fUe;wmgZrD}NbF3$@a^irm2EZc@6C;}I?@CFiLiegMpFq<vB^=~wEEK~qoyY;8@"
    "lZA;2Yw27RaZ|_X=3Uay0DFlzkXZ${1gP{{>TEjVB+sh%c9Cdg9+ON+{!}5H)<k$tdCE!r&EJ|9lV_u!1WMyb;=kKpVcy+mD"
    "q^**+L+31h+xSr<{hqfTTD|&k9eZ%gtpb%LRvPgPIU3EDM26FR2-xw4i=$$|FVwO)LQ^6hXyS}GW=hn`P+OA@F@fG<R*{o#`"
    "#=GHE)w^p^%Sk**FdrG-yx9Va-zXu@#Guy2&^b*tjL2fJ`@eXP`igHkGdYIYFi3l9GcT@CN>L&gM~GY_(%POU%1s|c*qE&x~"
    "WFYv%ZFIOmYG<5jsB`aF)I7YEgc|&2vo)w@_*}2oDWb^>gr=7S}zlX||Ev1CfjLU*(n_t%Wix#^1l`$1tPb)|BQ-AVGkQ&8&"
    ";y3l&Z2SvqApXs}NThFQ(VxN7LvRb0N@7$?39`}pfHYkK+^sH4x^w5lh^l_cbs#;$`;D!LmzMkNZjUBo*gzu;hQq(F(~<y@b"
    ";d0GSvbb0<W|GN-hkJUFuVFAAms=ny6U2RSmB;W!$0dg;;U6qkIxHo>brAN{n<PJ{TPo=8$4ZwFX0E5;$`%i?eY7me~JYK4}"
    "nVDxOF<JubXg)ToGSFFI>@r~_`4#;Yl@})Md0UOaRFBBv>|7r19s6ILQIYs3Lqyjd{-zfnhP}fuJ;1m8Vk^Ga03N!V6X@ARN"
    "s5YBHwUCLwM=s#m~XMU++2SsgU(=iR^MY@(1$F(ik^%3g{GhIsm-lXQVI>K)`>cHtpjYow`ZR0v@r?kUU#v!@zXKUGNC)zf^"
    "Qe?^?Y0~-$cU;l|}$i)oS)hX}2#gO#DM0Xr!0U^7sA0Y-j){OND4m9^f8`TB&fg`PI>7ZUqn<vt(dro=naIGprAzUNqFSV24"
    "2PgzRd?)J79JzDn;NozuX-ecKHRyU^8j1-dEH&})-gv{tZxLzRXyd_8mtMRL<zP)nA^9tn@rd>xtIq7DuE40Np<&fDdP<u2e"
    "(IG8pDk<k3bm)ieXwf~Sv(&bV2#_za63Z<Q+kxyT0Lc-Sp28yC7uA$cKsaDdz->x`2lbZ{QJivKF7Z|}+Q%J=DczV8~5;UNW"
    "z~LWm&)zY+&7>Q=xcg-#$j8VyqNpBeg@N9gksC|9vcw19w!#*L!a`;-OR+tEgZ8Nq*S>_mRf9+&pzH<IUKeEVb}iTHm0*A>?"
    "Z|bQfpz`<xzde#Bwn&h9+DR;v;~5_kTk!nVSRB9#Bc`k2{RyGUXp@8lLD6(p}aqhl0Tg5kv`r;aNeC?CIPg{``=AmUSIP(pN"
    "v@ulc5!Xe`vnl12t3(zWG(1YubAOtC|quNwSd5tJTUj^;srV=Eptg;NJV0$<tIH5=ZzB!!;xCvx**|t7F;%=dY@K^Y7IX7}<"
    "9Mvj7alb`yR^^h&0Ph>EeMz`kQUA#ql5mB>815`3j>PDHmvobRx2odgdtEx);&)!E~bpF8bcUGdyZU<+Oyir<h7x60D)5C8%"
    ">?+*xQa8@l8!OSYAk=O}bHgw4N1}x8KQEZpHskyV({%ZmQ!rRz-lkfVMb!!SWwbE!ZDW_)5(By2Nr82OC!i!bTjDS_hv$&Aj"
    ")oM^HM9dMt7rgAcawfn$IYJ^)E4#pHo><PYZuw))o9Xzn_6jfYK$V3bDo}{~d6>CnZM0b;P6eEe%c@x44vI6$t=c)fRX!z*`"
    "e;44n41Jup67xUMM?`FxF0yK3Q-}I)WtK>rW)617hQ=4@-(e$xsy(mY8R=mpa_t5SjB#6`n$dit0JQp_2zF%X%qO9Jc<0$8J"
    "H!?FqVu+4C&;+<186;>$B}vNl-*Djiy16qYj$;ViY2y(=c0DFenAjfOycwI#(SwHrNhRDo0kmk>dv0d2n0L07Vz`e^5w&b4F"
    "Q>b;ej&xyvlAo_ysKwJ=Pq%$<(wpY-;}&%M$wt;+$RHPF@%h1!aAZk|=T0Fy-=7ejeLnW8UdqEeN3J9quU2jtQkNqBeu(y&+"
    "B%5ZI595HMqC3EMuv-#H`2K594aTKnXLn>bM?iQbCFWJ{mx3UNMak<pr-9$YnjkTpf_6g9I!x=gIt>;c=&<OUssu^z*56+t-"
    "%?ot1U!DS+$ApD}OcXQA!f(dwAi4QtBmsPBC3)0?t|&)(lUpeErcL+f?9tyAI6@5y<+yIBLQ4JoAp5Tt!fPA-u^cP=MSAtKH"
    "&;Ptd@VY#n{*kW5QmIj(wlg_u#`wO^lSA!S%a!^6DIV^GFu4blgO6E*r}--z07jT3gHb+N<vA@-vb)D|77XdJbgX(;!Zk&eJ"
    "sY`$#_x1tefpf>KfZ$LX^7ol0C+39#)v6yLpqRhqJ3fhCD-G%wlPxX{X6Thw}-T9QFkQKbnm6PZ<)DYmJ&K2oo|KD3|LA&&7"
    "`uu!;h^7??2jE=AE-_yRzt$I^^!@wCM9`UPYH{sDW4Ind80HLcgMzW7Qm73H|EXP72bOiY%^lKuU;(vfQK^zIZ*+n+JkBu9>"
    ")AHT)zJ%La4RT#G*H@W2aHsiAS8o9vmftlpR&rdh^lb_!Fpm@*tJ)0AKk1>eYS@#3DBa+8F0$@2<ffuY($x<O__LgDpJh5F{"
    "8rdPktd$<TJ>>TMXiheRC_>u11JFSM&cAq(Iqt!VF2M@#H81>rN6QrIAYd<r*gHu&WpQEaDLdmYt3$3D_vjnxoufxsoo~o;<"
    "K<NZ<MPTc^(UMZDF4J77kDEzwd#rLH4;FgqrQ=vlU!Zf9$-B6`S;mPM~wuNii?#ijH>SP+s0jFe%+N2&BSCkX7cme>YYYKRJ"
    "lFEm#)F2gYS!~^gJU!v9U(e7<E;pM2HI;Ty^hNZ<S`77x-%F?&jN^xvlV8`Zq!*Ag{+Lp#xb@BiV0Qcu~_ag4T3XTpi6|>?|"
    "}<fCBv*mr*Zbti&=y!0fM_k9N!%7wk`FO2w*)Jq9X^brz89gZi#O#uHPUMdxI-?w{g&JjG4PCra<JdLg0~v#I^YADRunuh$#"
    "mLiTsygx7u!l`wDw$xxt(==q%L&_9d$4n(8Z#UdV*mKI$)&r7WcYs)@+K0mPk##0ZZd!a-q9i@!0lSRLPsarmY^nZ8r^KUB>"
    "^4~3K#JLFEA&Q>E`9;5qDr~_AE6>(kQSUbwsmhVDs@KmFp~$d-9G%=kaYx6Ebt5wjWmqMBYf%kx7ZhT{r`3j^RoJ&gtbXaKz"
    "dJ~p_f5Tb<!(A}{N}~u<EN{p!IgoMDx<;0X~DsVwX<~|7&}GLBgV(QX^Sv<Lb$cwg*?(WQy@NA#+gE=(Uesm4DFfD1-n^3zm"
    "J`O8zx_<GYxOE{Z?Nm=6R81<fTa&%O!xRs5!Rm?px}f$NafW$1u<*jfVY<x240+yQQ8Ly(4Dltw@9Cvj~~P`+E9y;Wtx7s#f"
    "6ar3L8EG2}9*z!i3!2)U^OyJ@ohsn=)yeG<ShG5yCzaD&t{&!coiHe4>i1-$C`_t6^Ee|dC?&3{T4;u7GD`Os{CGz;F)sta9"
    "Uq(jB(@DZ|C(Td?kjSJ@p`VnRy^TF7>V=;x0eR}K@3;}2H41p(r2ZkRX@4hA1!p9EQWaguUu>lS9U6Lft{9F81+yqFvPGPd>"
    "q-*U=ylM|F_{Ya{B0*s3QvQ^@F)+LqpLH*6n)=sEPTEPf6@D*Iud-kWTP^dRLTPXjU(&J!5YD3r#=U-!!gJ8(awtR9#W|4ot"
    "~b$`&*FInP~dMTJYAP_Io`A-h+CY1BsSlPnjJZvTOTN0q5htug1K)gFK)3K-M{k+*RYuHrZGVVQ{~x6p)Bu0%)->7s+g2jS$"
    "XWKvLQeKn3i?j;jl=JA765(lRyKYI~<FuRwhLY`!75O|GmSZco`)VmK{j3QSqJGnTvFMMvjXnAvtj~fpyzu<MHa-q+XF=C<("
    "reY7<9tQFxT_uaR6$cbK^nH{aWV-^5O=%n?MU+{|;k`f4e1jowoCVzE(4fJ@f+5Mfym=aQzJO^Yo$tvkG;qnG-QbL;u`P~6r"
    "R-A&$UTGo09fkI>d@`NtdJ!1G3cD9~m@+RR;0r@p`1fBUeUkLhbMnCAGCso~NPYV>~KOc$f@yuz}ccI1^@!kyXU4MM2iz}?q"
    "+^|gg-sW$VbCHi9mIY)yQ7pcp1AIT%nJo)<1~npVN(w3LT-`LaLAe-4P_4Xgx>F;&mSfYn3KItjo~9_we>hbYtAC5YU*hH6f"
    "5}9Do;Ah%Q(1Wb#-Hu?F31|a`G*QO$45DqIX%h@fKts7i%u0ITzh_%U|SSxJ$NlShtT45qV+93*=GjS-Wd+hlg6No3py(bv1"
    ";e-T1DMFs^81<%C}86`L*P(HFv&?*T1*|SFvFP*Arp3U%=c=&AZ8z2hLUzoo<b7B0MpDeWEFNMl;#fMi=QFkX+cyupuTrr{)"
    "B*Q)*Vmrg_}e7=(22ZH)5t%frs}E!a6$Y5=}Wd-W<kEq7^4Y#z<6Ca^2m0;l<vY)kys0T5`#zo<;5HA~oQMkrgCjqG}Bvhj0"
    "xz*-eN@R*_Y{PP_nUhj1<IzT>_fA8r|a~VqKV#5?N6oGN-f;9EX*O5^EQ#j;AA>V}Lg@Jcdr0ChJnF5odl%by5UMgbDNt^F4"
    "1^yo*A!m_J*|p^(_%7wmqrB&V7AW4J;!?caS7dv&#V61P>6oH<+Xb~pAUE-K+3NK^4C3c$^fu>%H-2lbcYC6{W>C2zMnnay="
    "h9|3r++0EQI{zP<a)<o&++9KObf}FDe&*T9pkQ(io`FOCxpH}SnEC1Li>BOyQN>?aRpu4z7YbuJxH?03--BJ6C|h(fML=T{K"
    "6k!pDorWzi*4w%Y*ofq<B7+zxMS&tQ7$F13Sj-8TXp#h1(ac27A4PD>`4PChD~D+n^2zpdRnom@c}|z^t45lcS~i#Sma``y5"
    "o2KO~(d_~ZdG=q7jtDf}m>-1g;pg*!UqTSP}Yjx5&O5yA%fxAr$IYMjlo_DQ>J*ndfl^S^|Wa%WMak4Ziw^Y^eOXCPp-+PAI"
    "AU<R<t5%*Vkaf=zxNMlV^0<4%hRe1IYmsvkb+#Tg}!%ug#2y8EI|8hmePiFuxJi0wwxni*-_pK;oO%UNRKzZcf%A!pZGu|AN"
    "KDK60f@-@UTTgsU_)n7^e4>v`D*iBOGVWt8qi-bFv%t(jU7c*oL5*J#hF=*>mtagxI$2%wU4h{`+GbR-Z%N>|RKN+uZ7uAT4"
    "3o}{rLkNH!}k{?bT=RzXE!v=be1r9zjnGM6M3i3*rAKBF=W~Fw&61M--lCU#|q6#>}Z(dztaYc=SSj=^GjgS9SMZp_5tp7b9"
    "a`f&>g}vLEoztb;KQ4eHn!)w|~s)5aVF9af-khOD@QVR$YBgZ(vS%kNlngD?{Y~Hz4vrCV|l-ID5*wqQ-`TP}aL16xO^66RH"
    "%CH1hY+9G?HwL7YAWsTuvMi;KNHMzcy3O;_foeJxpR!9iJ9c}}N558?ffZrO_2ROoO|a7_z@IJ3rlqP#??{3fP5Sa43Lh*1C"
    "Mx65o(799%`=>%m)u}NB<Ts>&F1}=s2ZarxW<y)(2@du-Nqy;9YT$o0RtPuB%UcC1`JuT76xpy2m3{?xTuV_ItJ~~Xy(hRTu"
    "d$fW@FR4ingnFB7?#jUw0;y2ZES&_XDEqnN>`g;#9W3)joB}r&7G0yIRKn(r-r_u^0uI=q{OCwU62$#wOyg8Pc*=}IOjy5fp"
    "<6_l?XwBw1nFt%TR$|5+Ea(nB?>2Tlrd^huYI#QGS8eBUXjDkpUk@lEL@QllE6QT|L7-_gI*BSEeW0a8=lnvL@v6o6PUl{Tc"
    "18Ukh>=gAuD{+koC}MzC|Fj2shRqaC4P#0Z(M2EBDa~IU40;3||L-EXs$7Ewd|_ZIk9?l8T9%^extcK7cCX=eZk><c0Gn46-"
    "+<&MgYCWXo0|ovyKm_te%{jd{F?UY`!ZKc7i`g@p8A*Q4TuZ?h|#p@~a7n9C^~mDKJ^5y-=YoKIgeesRk72XC?Oj_AE}wny<"
    "!i2{Cw4WlmgDtvfD#I7tk+7}P=R(4h&7A|D{m&8x<12`H@O&9&hng)Is#F-X8S7%2&rq0flMvQ>{7{22pv8LTi3Y1Paw2V)m"
    "n&G#{f1nxoEAq%}Quu7zWCUrLTccC8=-H1pyPb|2lI4GHmbWBUB$h&EK@Zx7!TR4jZ}HxUZ3#DQmjLVfpJ%(n#nNb<B3fBTu"
    "4XEQR2kiiQSNgA%k|FagGJ%2+Y0i}6mETn27AN%6K%k{C^(zR-j2MFBDpJWv2aYwuDz|Qx!aA!@7KpUY2Lr(AXXbG@QEd^Xc"
    "83`(mOSVCxdj3BM-mF-i0;J47fHJYa<FHDh1ygdR^N1y%9m^f`og3vqCeQ=HYvbY5EUS39$ZM5=*1&Q!viUaX*M`ZeLQB0K9"
    "8GfmJla7vBbEhUs|L+soOR6>*D$CpdBCqbV;^6CFth#kUT;8@hujbagMQ#Ckul)aMUxsk-BNLc(BKzdebO02adQX49p#(5xO"
    "Q)H&ZDq{S?4?G;@|#y?3b>Bxs@2+5!PJR*Omi;rfC{ukxR{sXh*w|r)-qG51a9LEvJkrh%*@*$hQ6Jd;Bp5(vhRWX(W+RDsW"
    "g(FdPKOM};FeAVbNKs;JKbueZNcN_{zTO^T)jaRB(N_)s_ys?iC#7V?{ibiEq=*3F;*{D&n9aE70A4`CA%+{qL4Ege5Ur=DE"
    "4urZhZ)Z4j9U5Ynu^h6J)taQp*k~7Cz=b6ITMhLJokJ_-lt<)Wa2S-tJw1vglGMQ%=E^rLpnHtEl92DMMSHali%)ff>b+Wyv"
    "Z{!C=hpN>_9Nk_lj`lS|Tz~<q4D68psRtZTtmnV&D7p!GI6I+Dym(;ggX*Ws8c2YZ46%1RifH>Tt#C`g<ITrj!jak@OXLx7c"
    "Z+%WD_%{~wxdiGm-!OMT>_)4fB)s|mZ6`A6bL$ql?BwhD7;nXZ~Yc<u0?6sY1FR20(y%r2v7Nc>x-9D?QBHd=T42Z*oyB5d;"
    "jRyzxoAbB?td~zQe;xinUSCS3j-WgB9=rT6I9#10$m@F+Y2_CUu2D`YywO5ysc#%-(9SSL~3689Yh1hesK?W8p<?b-^P&;0)"
    "1+K?NMjMbG^5W!-&R;lyCSgy^xUYM#v57e`>zLX2V_NG@h0e?!(*<cc5{tGwV@rsCWx=s&{FW<?tmpL0?ef>&Pk9d}a+i-g9"
    "`h2>6OGq7k8BG-V(3$w*lX_b+sQHSg>++mI7#Xh`r+Ye+Rumaid2IqFaHFK|BVZ55hq4xNnBtKoGW69kLGHvo$Q4!p3L)xS<"
    "X|I+v69*82TkOqf5fD;s=B(2dAzfPP%R3Uj~>}aWtLx5RMw40Og~zid;MX?N$6hKggD_-HZ8dQ!5B`a*<2>ELvZ%=eXM)D@K"
    ";#D3gUKXsr02)oT^<dtBS0R`kO?wGpp=H;X&%<xq2F_yjDAbpn6Lm<~yc`9Q5yO0(Mgh&XQhcho?NFJ8tpFtuX9uBKzDDAYr"
    "XS8s>=ag+@?>KSZdft3MO%=4YTC43BAm+faBt|}6MB`UnYk0FGJ2M$e9IcRP+j)f6#FVDU^&%;QhWle07zcNsDnr-t#Q)sck"
    "(KLRjhn9`pzkUga^*cP*pST1_R?h9ZcWx1sn*CO164Xsx-4dRRk@hF6H2;RIrbGV|js8t|_6J3{)>>vt1OjmxTI!wcY-bQsx"
    "-g7)Lu*)Rr_i6??w5Kr)zzG5j0iE`l-oWJdXXwj57I%8&2AU5r&M)jtp)6H*$ji(Cp1CnFSWJIW(@Knp-{@cQ5AgXk5`k-jK"
    "OS0)bOzbj%hx>ihNbCZ4nDSq?6zgAFWd%9^Y(G>Lbvz1Uh(9#4LQs<M2JNmUKLVcd5D$2!y<auCDfXXn5}ip(6;x;}UTj2B8"
    "c=hf1NP7)Sh3?aayaMiDdbJ8SO7ZCNom4~hBrNfg5BUJa-`=pz#vVO(aDkHuO|af$xGFs=V8Q{5lhS~g!6WH|Lz^KNJi6D=%"
    "Daz-lC`8pm+kVp8@6=shw@SNZz;{Yi5RR=@<SDr(Nlz!3T+f+JE<|1TTi8CN&9Spq+SLZCm#{wtV6ZJ)KhSU}|`xCRH6@8V%"
    "2K+W`%jPgao2bRc*o~imVnikJ6WRS^wJkq)rkwh4%bplCp2P(B+kEiHqYwh3JttQW2ZB}#G73g)iEoWKD&8vXhz9Xq?S!H`&"
    "d3zzI=_7*)?3@>+a(s7ZgN`2u%rb=P1uYC%VJ!JgQ-oZ|NP2iLSYrAKIV^MMX-iF#m$bZNDt3FuD0{Y{qBYIwb#}+U6I;Pg&"
    "P@~GQ<?jyWW#j@*l#bQ06L`Pk+H<d?%c#z>d3yY00lUAk~3sCNEeOWr%;BxrsL9(rn8r30E}vB~-1}U-0Xe?NH>xt3FFIR;E"
    "G;aa$)-`E%kY!y+tIW%GE;mC#|)tz5CYC^RG_euDpcr{#W$e9W+^K!Wb^Jb*=57Qf-bnPJxJNK_+nPxubXGMn8BnjCICfAC-"
    "fvf6HA@kClAH*G&h+uPCn_cad9UO_;S0C*m*VBrWgnS>*akR`^$2=XDh9BJRzFgVm-U^e?4DG>qd1V)vs7FeY(|Gskf%*<Mv"
    "fcq;N@9FIfw`Q+<5!l%zAf`AX)(FJ;!p96LN8YvEs!V&aFSC-Ehxcx`OqGqz2&Hqjrr2y2iQQWTZ^<)f7GH}Ik?Mb~`Mgqv^"
    "1OE}>Ck5;7Fkcu{hCWknEey$MeK5DvC@W#ZaKz?uGup7@`@g1&yHw}lEJhpVOWSkElnW<Jag|g*N6c}fBMah=}#51{MRYfB3"
    "R=ZS)Lw<IJn=dF~n%tCm9tjl<T3vym0H{-+ExpGViwcn!VG5Wl2=|9U>o~#28k2of=Qf)Uo>xjvq?cs{m(OI0+s|lwBco=TP"
    "E)TrwS{Qn!~6wYgaswAp>h@VzJt*j~BlGLsPUeXg&afz1dBXdGK}?e29J#wL#O(N6k&R%9Tli|=-Z?C*Ljc+iv*u{-(32KG`"
    "gM@iEtCmZ1k#r1e<qK!u#h<><hqq%1l_8j$9?mA6<V5f`2jx-{)bDLY&9=Bd5{XHabpCjk=ENW~kBO&Q7NENO8I~r+|$Jd8+"
    "{e(ez8>fw%CuO>jg}N(IrGudU@khbWBL~kz3VMI-cai^EB6~_-Aj5f3a<y_A_m`M%@Y{{BkM2psirfpG>gw#~02>aG?*&_W%"
    "$7K5s%xBh$YVo?6hGK8PY4^E`v6ezCBf;cLP;KTxchgxgda*RBU?c#h2mmSAy9td?9>=8)+3YHA?o1a@8-_gQorkcQnV0{(7"
    "|E$d@g>T#>4=MuO9|ZuA_v!ID|M5gqUeE>KKkfu1uWGl}l`#yjNO$7=B-h>{v9yudGBTlNV>p;czdFHcKQ(9Z93u2a^XH_?="
    "t4OrMt%x{RAv$f9D^7<YV&?xFVqYwTT*c1JGHCR`Wiye{9PgVVw-+?6A&N!Yrcfc%kvGQs&j&(E91(>|E50g!X%Fks1G^c@K"
    "&Xef$V$}+`uy=;`t<{OMD(VNmDi1h(S<CGzOnj+`=M<dwsg!NBs>(Q4B13G62b(q_w1Sj50C;c9RW#9Ft@k%7T?J5%r1HMc2"
    "Fp$NmzLIoRB0e+oAj;4^htpofz#vD=Hetw<N^0X*l*J2%wYa7Q5A!MBz^Z*dn=QI%%C*iY87=#$!||Oy#B&5SWi=~$6Jg5pS"
    "MBUoRbcW(Io2h|J}kGb!*t=iR>976@{pPk+5(avF=QqTv#vBK0Koxq3QC7+jBGi(-t`%Q1&?}|Qs~^9=6B_}AGtC4yNhmD=7"
    "X+G9|rUwcIaP0#PGjNAn7{><_Bflg}+pY%iA%z)z}7G?L>9p;O}Ca(MAjxaV{`Vj^T1OqY$AtUXkirAAW-o7jYYX-_0KyWC?"
    "Q$@NVmlFiR<j*1XA<1~I=UudDi4V<G?}gpgI-pG!zR@&u(|g72bC!^##YKlp)`=qpB2Dqb5V<d*8<_vx=!6sm$FYyc8%iz6^"
    "x`@C_&kIf}!63sm%dj{7l(_23V;`Wn?0Niq4i}(Wkt7rk4-2L-q_p-GWbtjBB8Zlv=YY-1>)iUUeBp5pO6`QOFByAO2&W#Xh"
    "l(ED7YSKf(V=E{t;2L(1n9Ke_Ci%CLY2jA#f$&Us{p`P4YWcryip|JXkut8zTqoxOwS++!{3Utt3<5i!otc%r6T49nw}JC-O"
    "M71N-K?Y6Mbq#H?xA9u<XQnd<Tk>0`#xnsvTL2*ZO#9Wrn8KT@_YXNE-Bre(p}Qs-AF9mjWp7rba!`4NlSN^l+xYZ!b<Gk`1"
    "}6v=hu^KUUO#NpE+}8;>^-b$0GTUOzl_3Tt~*v=uLWqZi5z)p$O9-Ztr~phwTb|Po8#KhG%G5gKvq9#bm-1;Qf6rkntNo>H#"
    "WF;KjE_2%Zt!dK<rfaX;1%QFO37B>nT@8o`PRmY>SuTJF<6feVn$6OWcbh4u4%gZj&z{GK?ldJq_>XK>Js(@AmC^3y?(J2)x"
    "n(^Hv%dtU^Mks4j<h~vEEg#5ZO#spy!JUBFFaP)Q|DfRo`j`T(FE(OOg$Pzh@L#H3roCOXg>GqpVTL0@j?-D@~XBOUAO@-+j"
    "@$jmU>oY^$9uLbXu#{)X`OxSJnxGSxW1ea;X!EhtAOzI9$aQdRQ+XDEj%1<=baXjm%`;h~h<xstW>JE1F15Z-&Y16rp_@D`8"
    "57B|y+^UB$)wY?`FSEn0*w7Ftx-4~-L*A(p@gF6*rJ*zK|RbG?8mIe5eZ14?EzA179MJNa%z#}<oP?QT~R>^SpYYUk<_Tw*i"
    "yXq<#g&TYj4aHLXRk7m#r!Lrzjs|`Xd3b6}1iI;7XA6Y;HzmvegxL;6?u{k^<Pp20GvB>55b!E2*WTxtFe`Rj1#mkX?#5RQF"
    "<$)QWofKFj$qfn43`=VpYjYN>1UY)ycP>0*sZ*!nMkz~etXFPfDs$rW+?j=1Zu35L6;DML~s|DKj!J#Fo@wg+oi#2=Q5C<+2"
    "#cTi%ygrk_<KiG-{jWD=^`U1z`-TO{Vmm0ewN^rMNHrevY&*y+JcOaBOe}E0D{;y67=69n@{p@%im&=cTI`P7s?a_0+BouUF"
    "p%JG9R7;U2=X?y4nyBFYY%_~t9qeiXW)!2;<8QnWw`ctPmpg+jUgx}dcOyP^r@jlJn73U16*{>wlbC_eXmOnk_nk0O5aciB5"
    "!zTfI_T=4_PY2Cb$WR1B=1cEom_pwo?958RN?ANAInQ)_#r{OvqsPCCM+t=_Uun8U_@jV8d(sHpsx{IHq6}S^~!sgUS}>uVf"
    "qK!@&wFR=}WS}>7PD*r&ZQ(GpWmY5zJqQ+5cWA6=<7WG$dwW8OHnwgttK3rI8UmR-jG{?<&)pmu|6(jbJw}bk5_>0_%|ct78"
    "B74`W&-LC%O)Uu^t@+VE^#*d(-xK#OuM<h;@TKRb^z<orL0L?hyQau98E;Q?=7*#rd#O5+njIByaQGgE<8hME+zw`Ah-haDQ"
    ";HCE(=T%nXX;joq<{m?BlebI7r<d=C;dCkR^QFrkB+Tm|<4^i&JN`q>qXm*VRLR@scpG&Y3DBK~%>HHBv&%@>3lt1psk;-%n"
    "P`v?L^MKCrJ6|$z7SCcpZ*=yD^uTT}mpthA%g?I)E>eSRfUH7nah2(q#{}1X$vf!ZGxp`$SX}5@#qw0?e#m^K!lg5Q4!T~p?"
    "OsmjXV*UyJklV<Y7zs6&tBKB7+ZrM1*}uu{3J(_!I-A|PL8ODjc_=Q@dxm$8lgW_3WpI7taflP64tTD>ysXTy$j!pp*q2Ps2"
    "!$^Z<xC%aj3D`QRw{RZ^-xW`i<hhdx1q!z^~-XEMyFmn!VGDH3lVl2nSER;XA)NE;f6A|E%wmK5Tq{KV-R$HK(k~QSQLlEDw"
    "65@4Q8j8YjnS0`b0K3AJSaLP7^3*wY<02&5;iDZp7%<@nyggl7@Xbi=y~X;ytNVaPns)gHPwsO1m3ot*SPvGTcazRMB^NiR;"
    "q6q|)1k?ouvICuv_MbUFhkoGDIZC(}(DtZE};C02Gkrm|_z`~>@q84ovl!teJy7P$928+@W<fXSy2%r_y*QQN_dc>uInK}py"
    "syAJo2_~&S6rSaN20=u+NjLpUeCK4fexq*6St0akE)K-C6Z!jC5oN5BDYpm`q9cDy8}Y#1iLhZ_UR@3TGHA>}{Zc6ZR}^u3b"
    "^VRbWYOKTPGcCq>)H08`cNFqQ1NCd9?MU*SlZ=RaU-nm^nKJ@Dd{i8^Fd$vcSj6#j`<HE91?+jm5WUqPWP@TICftfnKY8tRY"
    "Xc?FP40bY8E%sGvUSJ`t_DwSEywG8TI&#RL!}A&C%DxY1Lp?cNC*q4vQL#!S|%ucNpZO=^;76BVrVyL(^eOjev5T2RN0>+@#"
    "{I=W*tnMBz##m-iY3Lo65B8Ix3T3$MD<wmDZHygzv63+(+{O<_C|GR=B^e!k7My{NYH^u8pd>{Um52eL>fnzJ!fz-Ba3xD^H"
    "#bX#SN>&<|kv}OquWQ+&F3PL|XoR4wCv1Wf`1sWURECp@Sf8LU6*iilpdU<Zfjl(xD<<Ohb^bc?%+A{3@5=JAVi97b_ryint"
    "`TNEY1(d#XlR{6Zk7K?o%E1Oy-E~SE*eJ7-*8UP}BMp*F$U5LvQQg`mwRmddgw+~>^!toLX-0gZfE=kSPKl7s>%f2N(BMBrc"
    "aH1w`n*+*?1=W1srbS6K;1qfH3oN5;ZlB_e;|pU1BBBwrXg?2fk!(}(<bVNgi@>Eh~~R9;?aLCSqfMbVMhd8xx?ZpEvX+8S2"
    "i?WdzK7e&JFb5#Pl)$tZ?6;!Q@r8NUxAPC)|M@qup(XM2rOQ5xvWoSh)3jmsH%K7c0hQGMth}#we=P*I*j7rRG=t38tRm6*7"
    "!6&QtKIOx{hL0M^njoQWNC^v0WV4C`S;=H`h;WKBk2S>suM@1$Rp+|hZbut%*21%G}_ru4x;erhk&5&45gG)auEi@O<+@2Fz"
    "#$D993U0l9rW40VAjKywa8T9?vk5pi`m3llF<+Gm2#=M<6hY!k0JAvM=3+u0S+S<hpC9_%pp0-J&0N1rm<wUckL4?^SLs8O~"
    "_!Gs726{dXg7(}_;nqHHIOqIdV^SB7p1Lv<|6zOG#f7=g4i}dy<(V%$mfd(@^60RV#|yqz6Yym^A_2%%E6&Kz6aU6_H>NI_m"
    "H+}wL{F@{i#@rv7H^`vTGWGjY(7W)``C#4VaQyzCvKGI&+<X%uh*uh8K)bZ=q4S`E{QtO(_|2G*o0!XY$|ZLAD}Cg(k8+aaS"
    "@WI)g8`nRNlXla)}<evC_wPcc(rKsO6R!ZiZ3mc7t))+=SciA~PYU#<x+Hnp61NmA1XPfVd2d0|Y^(y;K<q?lSSin}b#kQ%5"
    "vAsaYy#>Wl{+7r&6B4`0uqBOKQwS+dMCjHol-7ZYj-Nqy!RdQ_tbe#p7sdAAD1Ks`Hf)jd4I!Yiw{pn0nM<XF|pQG9PK*h3_"
    "r-5ZB<UyVHT`E$UpD&1f3Zx(x@`;Uj62WDMQx33-jV1tbGVUpiz8^32)D)peNi@}=!NW-|m@VC%lcZ3hVuSDfwadisBN^x*l"
    "PBHNxW=G6ba*69u`ztSsn|<HQ%3d^)MeSS)J{p=NS@&TS53v^a>X{g94f%3|@`AH?UE<9FNl<CA`16GW7Ipf83fBW~2_Z!T#"
    "l)yH98v6IXB)Trt6<q6r|Wj-Z~C@h<Mp@>YHF7UwsOc;Db_Br-{(lx<^-zmKrejT_gf>xH}^C@e4o9Wn;7#691~x3W^>uyk+"
    "YiS87y|x9>ES;3*fz$YOwzeayerb(Y}0)2xl_0pOFCKYO2BS=T1#@ZT$CY7B9EnD&O15W1t+gknL@aEY(%L%zW9EGYKLTD}Q"
    "%k+Ovwl-1TSG>zM8CA}$EISxuNWu?F+-Wk0&tGpyJv#Us-Hs>w?KXG$2dkq`E<ez2r{W>oQJOscP$2;0<ggg4f)B%A=;jhNH"
    "QLoBkUa+Sib#m_<7X0F8{E8P96CmdI?LMn(C!5A~-Mav;{I$Pg`{}IJ(v<1x%?2;N+DHbuZYI^ADHxFr1v4TIlNY{tP5jKCl"
    "=ZpzF=^0MDS%Ni!6&W7Or)U)h8Mc2OOty72e%-hvx86}@)l3P>81YE>jNuaGj)KDX$=o@JBCE1+R~lQydx`<ez7H(v6ZgVUx"
    "0c_&3*}$hE#-}#u~;I^#<nh|U4TZY@zy)nWJ2Gt3BP5R<<bs&H0ma<IgC9$<9c`iPxi%3XVmsjMC8PPSorglKr>!qc|$HnJ1"
    "{n0x_sCUy6|dbwuV~7;YdRZq(F5SE}w1V5(%5UK%(*MbX#wv`O3s}EM3Ah^8GFw%SD<E$L^yKqZ{!&R0X@g9EsO2;Jy@#;$K"
    "34{x4+q5=q%Q_U)J?6qr99s(2I=Hbi5}VNq#GYCtDFdx)0!p0L=VO~1t4iuU+dTq5Ur4YdmwqFq1RVa?==N(zx?pdf1Me9o0"
    "IkO7-qzQ#hI2~5NZ;LFEhivCi}AWh!U-<9j;2DUehU=dNPQdjAYsoog+W+*(mwnmqLU;kc{*Rg*ZMfT$q6@Jp|QH^@2k^-(E"
    "C-(BWEwysld0DZ6?rGzO%_F90zzfr7-Y<jSm6Jh<`S=|zoEr%a>@H`wT<N>08adOV_P)!Q+~!{8W!H~4)({5fcCxncha09}y"
    "^mF|Ra-9po8F(eE8&tmH>E$2i_+fMea7c3L(_)Gv*Y}IhKBf!+X!NT>KXd4AM9Zq=ZU(@^LB^38O+dJ#6c_T%6Yg()YIh)|C"
    "xYoPjgX{i)EIHl`Dn13BBP%zN~6FUgdt*X!M#1GJ(u;H7P<Kub1g{FXSGD_jRAbp#Lv4<ZB$~%&rUgbOKLV2d}*NU2RqHA&r"
    "UdaSpORecZuT5`W(aB2Ap8z?L_8dMrdLw0nN1;<qR7$6<qm!Jfu9l8yQLKVAS&FNbQA4Slk5CO~Zaa>6gce8UCEes*QD3ip6"
    "t;Cj`KM+p?np+LsZ>92^V+SjIC*%8!f^Rq&N-rQ@n2^fi=!zwF%Ci#oWiXyzcGGKDZR&@Me=~lz@=R2<M0<QRAV<ah_YYV6^"
    "Y{2Y`pC;M*P|L!r0l8FrpPprLm_!+BRik9;h`Lo21AD`=-HxKrphUifsjIy*F=XR}-!0YCzqcd&Z0iMUc##gl=RKBBN0on(p"
    "s!QS)5@}UYf$S7#uaQFoW;H8Mr85~^=-=7ybG0`IgV_+Olgu3iU>~(m(tDMYk}46&)z%1Dv^o-mcI;Zrth!fUV~@w+4d$KCf"
    "nBS6q5KQ^n>aWrt~azqCj*M6iY~0^LiTSpj>$~c?5j=0h#pTQ;+Keir&$M5Roj*$wYzekgqK9L}i>M)Q0)CldiER!0p(feXh"
    "j>E&${G8Q*|Z(~Q)ZPev)>VLPcD4`<X-H>{&B`~;`$$N$Bk|D@~-+iaq39pUz02szvI)C5c#PA$u#<}V@QFGy<{Fjp2S!X0G"
    "HD1!qs^zzM;<+vRoz(YFxdT!3J5C{;TjFc8}2h)fY%ph>aJ0TiqY&2|hhccFoTjt83;2f{@agkDKmzoW8Z*rqNnDldcZzLhR"
    "TTXG1Wwd-Z-*o?(TUr>c!sDwk#RW@$f%9hnX?KCN(xoaRR`7A7s~mpc1kTH!pJaxgT1vm2e8%8l#PNVMm8S!{dn>NLpT|BW{"
    "5tx`s_^acjG?<w)tnNCRslQJiZ;~|$L<?T(sA#`4(81Ay-VF9r0M#or_jhACPu-bVfNGBWf|={$Z+8HoZIjUV3!}$P65Kpf?"
    "d`4x-1#HN7yux!1A*4ap#V;RzkZ;j|GHm7f#U4_Qrw3U+%0!C1n3_mP3)r7&wLUir-s+o(|(~7zMhlnKk!m$UhtI?oqpuTz5"
    "Bcqz#>~vPk4hxAj5{g~>K~tf(j{w-;ppztQ(&h=v}QbZ!pHWHMR4H0d+E4o=Ll7<K1jJwOSEHM{|;)N}gf8J17;e>+rasY!c"
    "!Tw$xlUMX*M;kUnj`8^DS;-{)yaDKHjdQ=U5EOUrd42fNEI-<8=2`nSrlU$A$+BcZBpWicIGf5B%<x7ET>@eRG8EdO@4|J{a"
    "`zY5+=@75CHwSk%Wh7pG8oy6W-B|!ok7>5cl0lZPdIq6;S3!fOnS%mx=!lTpt}|ImAuKnkZwXsM<9w<F^R0v*7*kJr_pHk(t"
    "IflxqHbQ<AM3M@Ai`D+bvv<t95a|BX%O>WD;P-+ab4V9fdy~5`ydNsIf(pyNv^Bqi%#imV_;*!(|1^^vc8Q&qrCu~Q1hMRVG"
    "ebsuhbRgX+RK(k<E3l|Fa0M;qZVMZWIMj*s9z!G`<CV`s8_R#)cN0Iy#;%Z;r+R@$h&gE`jig3Rui%%nR&CAL)O+aEp{PAUS"
    "5-_DS^o2Ys;rUCDj^vhZCJmR(+fJ1mog?B1PU(||fohgpW_8pQ&1mk_vMqoGvQPS?Mf18~b-8OKijxf@eP`|_rjUDfg4V_(C"
    "3MR0S1Z@mb<T3U3m3B+Qw0FLXj`;c3HWBL8d0=~G8)aq2M*tUQR_MwL87nxk@tixb(65F7?Dj|I`VKzB(*)a6wuZ{PO*biE0"
    "x5weHW$pm@=H>x*p&an}U%?*x*11ou>Sz&>WmPvi2a<&uHtNg;8xbW>1+f-0CA{?aHRm0$m~)PtUt3g#0g1L*6Av~0A+??_;"
    "N5m^$p9Rj%qo);D_cIK2*$E{VV($sj3d{8K=LL9mQ<IGi+(rguQ`{>oht)NZduwJ%H6x-JHKvrQg{kuMZ6{5aNLM`h6&_@(v"
    "jAL{Oycar@7ZUgu`Emqcw~1=kW@N>sdLYE#pMe208K*id4ia@3a>Ee88f{0U~1pM<kZiUvdw8MpCFGdZ#!eamlZoECxTi`Tx"
    "5Q-Gu*7ZFknARM4@I#`Wbpelmkh;0=YmU(HptkNl*uv^r8UG%}dRcm`oe7I%umv}B<S-<*4?KB!*yf08$EvHqgv{s9BbUud0"
    "$v+%ngAog8kv~2D3ECnhj(QtiIMgk_iokc={8UfxO_aoMyUbe_ETC-e2XF(-Kv>ZF)k^1GxSvIot3c8zvT|7spnyAGt;j%N^"
    "C5hpYc6?mO9)!IOlF@6yr78b0Did*5d)w*~XBLTh;jA@@gCc070*Mnqnxgk^usGff$CmaMH*F+x)#=3_+QSZ6iFHjJNFaXwp"
    "_%!M_%lBH-sFMRy0IZ{LX3S7#c5$o>^c1<hJ$G}GKjb&rHs(aFH!+(3Cj`GznF*A<Dv8raSR3eRuij+(IOg~5y~wed)>^8Cb"
    "$6N^4C3PyzWk^sLXHJk0ir7V`AiQ4PRXEUBrJzX6hu5_cujdV!Ih07<-Mu6B@0}$7q_j3H>5|Wf<r_a+r6V94vZ6PH(yYi1R"
    "9(MLccbwS{LrHxDmcY~z`}7)}STWVpw4%4lu$i|f~uKbt?bZHG&nG_lnwPX+t~|8fQT{)p~jrI}zNBsXG7q?+boYiSg_eaXr"
    "iou-j2H{X|u(z!?u@>e`3fw9RDgowH({|x8?Qii*5FIiHHGwP|vp};ys*nSoyB=@+P{&UvW+CbMB17Um$PeWdIN3Z@1c;x%R"
    "!6_EO9go#HK_Y}KQ{-dj3AZihyx&D-6+GOINkCdP5ji9YLwMZT=U$g*Ufr269dc>={<kY+?_>II%z*=VcS3urjIps;ys`6){"
    "*_y%SrMCkxs6i;brdYCReX*%#LuZ6`^N%DyU6m>%QxU|L1qy^7Ga239w(DOEGu^?C;%$5=oIC|-}P?gngZU@Rx`XQ_?^-PdN"
    "QPMGTW9Gqy`}hm<&-ciHf9a-wO)PK;q-|8N-jn^DY0XV6e=pRC9T$R7!o7M{$IQ00(D?>yIpz`o=a|FpR@eNA*1CB?j7!gk*"
    "#vxtAB58IsNsdUHeu@2ildwWEGCw5{9kxpjsR4Go}Dc5{)A#lWkUWPu<9hv2}AEdET2MB{091@0O8UX3`p79&gUY-mO~luOW"
    "qi;*o{!2H5!7>$J9E;be+*XRBHU6~GIP<tRwieg?>uJw$>oJTy)jdOvhEPLEs3^zh<wgVb95+&OCDCesmPNw7>E>sgL#L0c|"
    "8pRnLnqcJ){<Ep3d9AV6D^3s1Vtg^_eIka=^uC}$k4ReU4Rta_j*Hw~f)_VM=RXk;C8!-Feni*Mc+befjf0bm-PHSwX}K%3*"
    "g<%D$36#qX!tl<aJNesHh(<tOsiDSd%UxGDA=JskckZDzn%-~TjF!xKK+HeiramUzW=IZE~-Lno$U50DkH?%mOQ{_!3~mhBT"
    "*NX>xEg1OVTZhVD|Ke_t*KD|9j?n1=oRfRue+c&RgHs6&oMV$)HH#IgB{g+zYy1iqV&KK%!kH$w|ULk*^I)wq-sw9ESt15fo"
    "S)P(T@D&ds__k=yjXeT?m4zOl3+sqThd&&!syW)1i2JpQEvnoi0v&qO(-K6E4?7`3|^O#ytP|5U+p=5SE&B?+3@edkKLQ#i)"
    "CqBxuft@v%T+<<V$->uh&OpI8+%ncv7vEH{|CUaj+dchyUhNhfEt;DFsVJbG0$B7Z{>IGkv`knp<CcZfBI0|0Avtu7Fz7jHc"
    "@Ic0}+aErooUSZb?GE{(n_NFtU?2X<1CoC<Lc*V4L?IA1HGCgRLW?C|B{d8)8~wKoj4nReJM#+{61Gm9$uKBBy8HnhT5#1n`"
    "lE&an-;I=u__8C%diUwUfFJ2t@RU?*|~{!u@q7;>u^`nXg!0i!&#gV-c0RN*B-4(7HS!pTR;=AkjD_$td-$<vdISfmA)}it?"
    "(}qCZ<crJJf$==g%-3>#cX9`JbE%W2tdt$Lu}T8~81@*OuKp{O$cRtpe}EQ}vh)tWggeQDZLRm336zeTlAb>Q5AZhYa8=`u8"
    "?Q3p<z<;!ZGN5!aBciSi)yT>-85a~Vb!i)04d%;J$OZVu9{+T-;r^vEv<nRtN@rZ<Ck+UIh}ul$m&++%rC$(EbI4X}K36S}G"
    "$=(@=khaC{Opx3+$w`5I!6ZG8LySMe-WVD4wwqi}ruQ%p_a#R{rsP)$`)3Q&9__bf?>Df|3!X2GY%XHfN*VDT7joNfuZLD(q"
    "WY@K9r~*tz*|C<CC{NgxZvM`AKbw~+%>(=P9%U`%ZL0xF21gm*d{s@tv-5%l*cyvupIAUhsuo?5%%a3ExW}Dg24aQtW-Rpo1"
    "n3nU{<Wd^<wx3w%8b1HFLCA{x#@)hV>Iv;-B)*XIb(klSF8`{E5MoFV3UL>9J$y)u*>bME|fC^4CU{4zBvrftj*kbI}?O3jE"
    "KWp?N^vasL%wI$|LimUy__gli2t~l#b02AA--~NZRHVIS+zCp1vQ3RP=@w?)NT%f&LBQZswZtN3+Sb5;+6!lA?E}M#aKC7LR"
    "zzhh@1_9jownX_A|<8&kdca;Eh4vQ7GQ`J64P7&x;qW=}9UvNAI3buP8Dv?cc_HeN@}H%8{Te}LuLlL#Fml7RqvBn%`p@-(S"
    "b>4DH<<?#8eGzp5W+FGt?EDvfuvH4GEVD&Z{W4c=iP27+4u&yAP7XOg&pglxc->uc&tH0EX>r3E<`0=vQcxiy3@XC5$e62hx"
    "*2+iz#($RkZ=0w$y^91_O%C7<ku}N~eMcfCC{JP?VO)fg&DiSM)%xxEoY?X;JF*C9FWFdk6c@3aXz4S71Q?~PN0GGE5Q+ry9"
    "m?XScG)7H32GFpguU2cH8Sci(_@wkAAp7+%1YGLw0_OSfr2{Y3>eR+)W?nb2N>|tAmTD7o?`_oj)Rhq+EC`e@su3P({oZrZt"
    "SH|>U(X3Bv;Cfoar=GP}JRXsHUv}yb&m~iqr>z)P`SSsKAlxI^*sM+^(F~n?BwkQ`%*gTQnM?xy+7?n)2@8o(6KaLtUdSwJ("
    "_bN_M@&X+!`OM*Qx%+9t?D{T<rDQie2YAs`qrg6*REwKwp!F&C|<s8NsN-X-WFi{qm0Un#B&<G*Y!RPv1kfWf!ekb+^hfXl0"
    "BMr2b~(lF4AKe$Nb+yzu<PV-+=Qxe8Y=K@3wrRtqFU$3Omf=pcp8VU6P1lS^k>d4nF&LnCNkEV2j^KcB*ecnFJ;>hJ4l^#id"
    "pw6(TL+yW=D_79_VR*v^LbW10VEvms@c0^WaUMMCsCnV5<t-NUUz&eJ!<K1S6Co%LN)ubrzC0vs4kdl~Hl9NR762*!dCdDTb"
    "_Zn9Qk>UQCNKgie5@ox<tU=|@c5eAg)qpCK<#sRj~1B>zJ95JS`YGXcgMvAOL2>dtz6H`0c>%VX~(cpoAAjmE_OzzJ?*mRKE"
    "JnxilJ+IpNf(E+A{3?qQGF+A*1X<C=@<%sv&j4fL^yjM;0+(!30yq-QU#B>WC-Bp=I+y`QL-)O`QJ(z-t2_cW`0^;bSMYhm0"
    "y`y!y*1hdr{(9JMwXfq0<ez&KLtkdDhBY3m`one6B;Y#+RC-|!%BE^%ZO>GefQ1Ys$bn;Gz%1^O-f2N)P(f7oe0xp%~IoYCw"
    "&_#k7`5xbY0RTVQ}eUVr8GM~;RP)s=BYrxU$60wL)L&niJD(#%LJTg*eSr-#JtP|+wyTr%pWya=WI4ux~mTUO34E7b>Qy_jI"
    "m8*KoXK~l%kAwy13Gpe=c;WrA-g6S*EfKZm-$DMQ5hN0Z%*?*>58$iEpb-Sr2S8UnMQ7UWNwLCLJ^L2grv`1}<`&sv$|IDSi"
    "1ML|x{xv8`c8|l@Y=|vL@GxC$M1oKT9y0MK@NWCn_qRw<<@@wcfIY7GLM5;-`4wty0-D%R=f7sgWOVizN!IxtV7(sZ3&N8cV"
    "T>Nl0w!Q2FHT^&cgw1v!us(*a!e!L{E5Q15ZHVCu8OVPQwj$#Q18_K2Z)?4=(K?2>Yd6IghAT!A`|FlAR#K)y7;h8&Gjl*?>"
    "raG8X=`+eXbyh|Ce=+1ymOFA8^iii5vYKFDXUyDF`G9$>m|4niGHOn9WjheV4aEEbfq98#6h_OM6c?nZ{0&^ne|JIv;GM#z|"
    "U|K4)QE_W=P{VUR{>H#%Eb7T%HXl=dr$eiriK-StxP=p@&Vej$wwgtjA*@b^=#y%V4&e3S9V0+4`^D&Owr*-r<=tXLZQUKhG"
    "%@OB>i0WWGlx5-5kpBxyIR9xF<36f5*^fCP`TY1Lzi&~4efybl45CD;(h}o1@hgAWJBp56Eu|zW%h(FV*dh7{yb4-tQ-w|L%"
    "C%yk@S~mgGaY7r*n2T~q%g;%9kXKqH35Dq_j~K8n=tcV0x6-7xciM0MW%(-FisW?m~!C53B06*#18-Lu`|Dc!9Sjk1X3ROY*"
    "AwJ>-Htwhhy0LR?Iym`~%=`l}}eVFL$FLT7ea0ZCYY~Mf_u<SsK{-<<C0fbTc#hsaA~7ITWmAFwTI4r5mBFUV_!ZnG`tf8jU"
    "idXdRN7CnNu7$FLe^VT@s@9Q=yyLc@qM?%o}<Zc&5)c0O~NM7f1s504Fa4k0fH<KyTitPj)Qlb~4P=<Dsj?)SNmzm_pZ|Bb;"
    "B`M;(Slm}AW3T+YF^&kjLrmfQb(rjw-XUANb;o+ocb$s-O!_XlKJL|6wMR3&&2;Z7&b)~%cQ^#o^FzN|M+cr;3@ri52Bf9EM"
    "S5`gIh0^+0A()vxp+$<@$+&o0RQw_qre0`Uy!Jn&OrkUnpO}l`{_@**nY8A4@=qJO^eRXc*%No{4BML8!Vu1V-g>Wz?_^Z0j"
    "eavd03(`XYX<CFXKVy4lHt;ll9UhC<&b<^##Mex(F~TC0w;59U-#~o?4_*;3lgLA-cL)P!9?XFPT$xGV;Z+~BkiG$TJJp)_K"
    "&E@B&F^`{{B6w*=rvSPi^9`fZl9rxo+&Ij>?+4Y$r{-y5D-|7f`WNo{Zn}aAL{C?IS>54g$1_W;u)7L77>0FMH$2#;JJA3@G"
    "5XLYg?N9KLcojtiFP4JR65_L%oo<_rp$(R7(VZf&A)DiHZe`UO8h3~!Hqz|RxP<Q5VPGc=<21iYXc5llh<nOy9@5ZC<$Etrk"
    "vM}$<(#l`#l(>`g%-PpFw^Z{d!6fDxaTDh3}Y<P9{0TML#&fk*7xLjIMt}D7rb<`ng;|Go$uw9AU>)a8t1jt)r0nyXNaDpj>"
    "{9(!5_EDB4JH$9gYHYXh<tm2jd_AtzuXFeMzXjdV6H4UE6Vn)l;k&1>4x~J)U`$N9M;zn{c`Bk{l|T`L>@&JIU9A`*EB!$Fe"
    "b25v2IMQ&kLS}CTOR&fcy;Dfqy$L0_jlC%i-!ESdUlpz*kcont1q5RfEni>;vTU*l|!g^;><65H`JVCr66mL(C0SOJx4{Ld&"
    "9`qr9Z;&i*Y}#D$+)7S?yHMq5Ye&Q7IfP-tJ+J#)qLXl`y9G(2JYNRl(yZ$-CY@f8;l|*lJ@qD|`!gAA(_Yj-%HO02ujo5}t"
    "I0^FPL5cQf_%>mqPz`#ASlDU25VcSvBk=3-lp?W!RFUF#zkD|7uWfND+;>9uP;O2skkY}jB)H|x5AUwB|K=PzW}ioJ?b^~jO"
    "vJ}LA*GuK7jC^=y|woI2HM&F-n)YLCG-XfYyf6GdN(hakV0%?}18`EJj>qdH(??Vo>9LsO?)Dh~9@WG>lCUYhE`M5T!17Y1R"
    "w$Xg#DPG>r-(vPHX0Dra02DA0%3;~JSEM!P1aXQV5YQP?a9>&aPwNw){`bs3Xju2Y=8YX;`a@6nw^ye~@hd8@3}P~eeL?-W2"
    "XkM0&FV<~W)_+gD4(U6Qx_xWO6<#aAv2F^JsI;a33QzlcP;;vtnh!V;l~3he&hiG5?Xn$J^XNtY-XpGQgfH>-7LQ_=rm%nvs"
    "#Vn0ZUcgiVCXUMY)?d-a7|@iE)xUFH|xIb~?S6gSDPFw^5<q{uBw1UWxRaZe@unz8B~f6$Pg`##-{+x-q2_N=dF`F_bM`jF3"
    "N>!jwGXlQ2Q;J}4*}ELhek6~D-n{J!2=2S2uczJ6`0kS92FHDy5sNmzt?54nCAlp1}x(e>lxFbBxr4fgUPAo0?<1R$o?;&-@"
    ")zF7l6G6J?%WOygW^c@h-NZf=BUdR)Yzr!Z0rFBc0wl8<S4yZP3i~V3UQYL@jPYEmT>xO=uRz_nbytXpn3l%TcIAe+Wr+*%!"
    "V;b?_yoaBf0qDxIS)(YtzABwhQxA$x9)fb;+%L)^uI+au9FjbYaTQn_{9q}ZKz2GXMSo}z=KMmEqLt|(8pyb9z6)Q7j$8kUG"
    "%&E?OV`2(Wwf-^CmzNotkmfEuDEX1t1U+YEQlg;1yPEmDzt3~x=xs-$Ym6=31Bsj@%eI=vH(7xFLwTxXU-mH40xX4^XT#GiD"
    "q>$rKeAn(~mDBJSSs>I1mID!F$i&%Y?eg{*V{Au?zMlNrW%lZkA0eWoX2GH16ud$T8sl3Y&rlBg*!tS4+v}^5={N<8<LOY|>"
    "(Ls-*V58|g~dC(_r04q@KcjMRv#+mYlKpX@>hvPD0Um!;R|W!JPI3bg6`f0d3t86%80itwj72kh?uyx3eNHokx6aE<;_sjf%"
    "Aur{B5J9ieS#xQM<FP=^-ze||ZWZs5*AkbLVw{^8X(zTfRv9GHp7nY66Hh4Jq?#iUb_wB<8sw@@&mm+Z$)K##JFGfgUE#RIo"
    "*SX8in4Qj@317|^pZJ!i4CkkUGDu&L<`oEWu>y4gyaQOfxPyX%^gPua0bOG#FA2|&SVq|y2;x|-4;OJ)*-PAkFWGz5?1ix<c"
    "I(^=K|Qi|@k|pm+#H-=rW^Zu^M%vLp@Gxiz+-C9Dex8_6kd;HPo}n<1Hv8k%=JezBe6@9WSQuGpbJI?%mqn4PxM~-NNF{C9R"
    "D%(2=(?wo<R%{CVL3w#K{(UgNBO#dntOgJrIVnSX(tT;sW3iflskaws9(1{j*HY+8?jxq|w=4Juxt^Udg~&N!=WS%tuG((y}"
    "m;3cGsLos8m5OBg_#kDW^@77#81p9GW1QhTzuw+VgXn>}Plr|9d&R(-)>4=oQ)2MhB4EQV`{AL4r-W8T&%sp!+^63Lv$`^l("
    "-Mn=VL!U;>2o6nnNN$2K%TfB>G8P0UdVz0-f_bYYpquX4NYkWZ_aIs*4CT$_eml{`tB{qX1UvyAbW<w0;9ovY5Xx&(0n5XRc"
    "R7Q+$eWs=DjXoD`b7kUVhrC5&GHF$`VcSy3Qc1o07-=LmZY?VFvmYTt`AO(W&|3^SdEb@uPriJfZH`0>hD8*<@*4h~i4vgti"
    "L3;&D_;!EF-R0ygtJBMR|buH#D1TsjHjI>4Ixj4U_t{Q-HXgLkvW1i1O|ZL+W2*_{xwVtUZ~(+C@VL%nH~<T@MNuWNjw}afJ"
    "r+!ckNA0<{SkR_&>SuGo@OIfdeFn#IwsKo7ho87>e)o7>N$a4ia@}FO7Rp?Xy#~;^FrLzNiFy68>Ap?yEq9{%ExUSJ+>o43S"
    "g9dDdU(b?*)?0v1X`d0gZ5r!<FO)Z_?<uolCm{Cgji%lo?uE;C!l72ol*a^NN-G-vFh2DJx}Tr>`aws5=xHM3K1iJ6rI*bfA"
    "&=SW))iJc4uL$h#(&F^gtoNCBOw{L!;KjfzDk^Or%tIxl5Rq$`fDS=P7?W?Cd4#v`w1|1Tr2w-<eiyYJex<cG01HJ@_?yW&%"
    "FXex+-MJg!$xA<8ah#B{RUkn;4my-AmfvNXu@buMs0)U{+F1I&xY&?{uneop1k@xiE8weT`&{sp&}cUJlc$hz9M*68({-%lk"
    "hZJA#%&Fs6#W$Y7IzC)<AIjjj)QUu`I3Q{FS(8YCp2|jb(#3im<-p)`7U|jGGV6nO{IvP9qOB8KGhNySstZS;D|I&)d)?N>5"
    "0a)VJu!I37<&Xb^VynCDIen^$PJK6vL+%q3;R*Iw~Wx8;03J&k;J%)50H#^YUmCG!lr5^rv9HD&avA2Cj=29O(Yp4Ct;A8@i"
    "OtX={h3+i?9D5vdh0`B;}-SxiRDrjch{Y!yR`9ic)&d)}6>+1C0%x>lZiA_lYeZ=(wCf3tNecrU1tl5sDu$i>3P_3IVF-=ie"
    "(3)pXZDbovN+r|fB=yU<h&t|_fc`$`Ir>DCjahBti3She2)MGGfS>VSd{Aj)QwjuE<-mBbGh%G9s2$jO6kMtfPyz-xs%pfet"
    "ia(k*fkO~?hmWI+xozP5wLmR9RK&8a?m!MItmWad*y%t7Kdtg`!qVVSy7houh?hz3-u-<zu{d|2bS~2bG=P8G(ZSzz;$GYEP"
    "+gDRB^Rr|SKx{YuFjR6`H1~&Ltk;dxB8*xp>vrVFF#@zT4I6k(xf>4=ca;$Z;lrsszE+B$XRecNYu;S?uB(EjCnq>)C5rG>K"
    "gmocu5U<=0II9@^5_3f6~RJiUsflta*62adal2C0pMkq;*f&L>P@GWUIzj{hTLN-Po2}4nCXCp@Pj^=*PUK@&nc*)mxzk>Vf"
    "+6VG*z@=aK0&8Pcj_7$`8t;6LNWu@0Oe-O?k;(Mi9afZ2ehS&MGs$+~U40&!x7#<+1!GwA#x*ZF;w53jFmfh(&6Jvz%3317U"
    "0YzarUlK$MGYsNLL!Vw~t5S0<(w5sdH^!)y&PxM1MilU&_Y=e;T9jvIR9=PJ?4u(=jLn7T+)vDaTGEz&>Mw>mcOQ6HP02;=)"
    "?}=QpIpHuz9(thBR$n-4==;4qq5lmH!uap6?HNvoA?kMi(EG|`eMCizF_y=qFKgqr_fvAa>!)EK9a%NCikz5UPM**VRW&_WX"
    "tsp6&A%#RtG*UoUW}F2oO;Z*$Yv|DMU{dPD_az50}}SIcp&@AfA12u=I3pVy#`?t1I+R`0N*TrM#BX4cq&-}aQ+P4af1Ms9_"
    "Ptq%^hEj^l<H>4P}<EFieR%{5M|wv~jkDTRc?nIb67<;JM?7ES^fG3Cmeuz~@B9nTD3^Yi3W-xduQR5g-Nt@j65IXpLwa3zP"
    "Y<nJ+4=me5njqjG*odd)?%)pssOoTL2(am`@BZ8w08M&#c%dEWnYz%TVhm0;MT`uUCFJ7YEcb~dM^S@sc2<fMX7#xT9($-up"
    "tE@p6Md}BH=61PvFR3^&nBnOad_~Z0jxr;nIc^ktfAAaZJZpO4H=@79G^N6@XDkl#m7A{#^<!J4nEBc*d=}Z5Tn-BZ~5_^_)"
    "FC(TO%&F0mq+wL~!^Y=L->cpn6x#qf@UOWWBy=JW^6$gjdRwB*h%E|p*V&Z=Ub?=Nv?@0pc}zeBdto{t4rCVUI_5A(bo33p$"
    "2$>!c#6Kbo51-SPC2m71^t3R*Di$g6h9~nZ1KmecnAXrB&#Z*aqNArjH+cjIXiaI&IR91yBR|92LHD!uFvkjF{7$!9n)cs1g"
    "iLaTVg)%gyzCkv{IiKV7E(iul7)&<=zqt?-<;_8Dq5K6S#Ud-bo;51Sdog1XI02cP@E*41AFJ=F;Im1OSfnjX~51h8>?^Vh5"
    "Xm%kqLOu`}*CeRDEBY;@Vny}CX_6gDE<%?E_YdHgbn$aWg<FEFlu|8_91S`j#q1{5E4;clB?kejzMm}1j~(j@Ejjcl)NtAqz"
    "r;5hplJ8r5E%r|kjH}8gBUrcB@_9Oif+wTkVw{<837wGm;u$d&mWvBDlHZ@cD^(JF@(qA4A1x-ar6|<d<kkKmU;XgP<`OReB"
    "n-beitq5nq!oaZM{^tZA8{iq(9KSjFH+IJS30#tElR?&@V1;1Nr;Flrtz^sgd-s>;;^`jhlv+wW9Q+~4j85YQ;8XwPd!sS=l"
    "#MFXK=0dk>>Zu;cA@J;`{l`cJRKWNK+2dai&dy~KRL*G;*X!<y2-&Ygp=|xYqT8tLLLX$g46CrF!p2QF78THz8m%;F)?lrx5"
    "F#wAm}R(F^7$i{rsl4%xuY!?V%@koQgpHA%)oRJ7j@R_YJ1Rik)FpQP-0(JTDzBYzt6*Dy-=K1XN?#rlb)H=k>nQ7J2#C8Kt"
    "BmnG(OgNi?}ENXm}uId4CE7TDCAsug?PBq-iVNE!pZ!ls+(-}%QSIOyhnvjl3%nm2HWvnS{Y&L_QiyR;7Uj!a6cw|?wsk);^"
    "D_bLaWaxpU65IKYWJImhUIZSz>B{HcCXFv5MjNO`G)HIVmQ582%N3(s)5NM4{w{tP^In29ukc<abH1GzpNx2{k?O11SMzci7"
    "{iq;lqme2wNf5=QG=Y3Euzl6)Y&HS1E1xcCbbuiNq|JjrIl(_$x(s1?REL@MQwxq@`VMXhRI>z2VJ*BTM)QUbdoNaST$r6Z5"
    "G3qNlM?jl{lnFs1-XlRG*%OFQ2R4{@;oIIDt7tDL_3cmE$NW1v_ttjh(#J-<Gq;mFY3_0vOloPTo9QC)Mge-R|fs`ZNYDm!J"
    "pwjMOPUTv+^Bbu^L(Id)?mBv<hky9ITaw?38bXhfq2^rx?LSowD9HZR??A0@!y}I>4ltio`xj9{6&i8SZb_N6dU25$~F2_1e"
    "_EoPlWaNk)5z!9m}hwvVQb_U#a5RtF?NedV0UdPBcHI^@$%ZN;Nk?k0uQwz}qW@93WXSvwi*adS|9Y2!iPQyHwu|3I#2yG%o"
    "PCtB#(XN$7O#DAf#;jCuVw2<s9dPWLq>yk$T%xnEvEm0ebZ#tIT$%ymB#UY!MrM6R;qxpMcG1Ki6w+^MqN#ZnKKTDaXTdw6o"
    "o?zerX@F=uf(BI>_hsLoDwiB9Z;R!N_AmG|+y|9c{EI7g{F+c3vg@Fy!Hh^>M6N#>?yQ<FNjBdiw<3W|DEwy$wcJ(I5%Xybj"
    "=(hO&1z~z4gR>0356SIT^gRSb2HS8ha4008i@5t;NOD+IFYj~K<=jv1B1cDm}0MRLq^6IM635G^mulhZY5ZHTF3I7?#g>pPt"
    "$4ebPKpCs_!o!Y0<VvezDMr`vebq*uog<Mb=2$y|g`$zS3Zev`=!~z(zJMlH~4Tl(hZ)(B*hoN^s*PBUFMto{lvkf`eNVcJY"
    "vSAOP{cKtSUeMhQ+)&o!5d7)=hl!f>cQuHc+djgCG+&lUxAUFUVFPL$_0)R(80Z-YR6T@$71H29W`GD-5prAWiiBxo#gVGgY"
    "vv0B2btNmgWVzO#>sF-0VP$F^r?whT=cDwcbJc1+Ww;Ie8qmM*M#5`AWqTiFb05bsFpNKN<n!IgsNd*{HigZw)Z1cn+@A~$z"
    "X~7G#h=9v~!Wkp9=@#;@pB<^K%}+{v8}bt&-xDK|9tj!kqa%WJk}_1ux_y+GsVWQbL=)kzc4m#5!i44lqGClA98uWe3VTPS$"
    "DLbISRcHVi@eQ3es!^ZbTqS5PS2q(KFq{<OAgR41}5agnnU;wg<SJ*zBfPeM<*V?YgkMkn2W}t`T3rSX{wwE;(Zq`4MRuKM<"
    "1$n<!P{6phjLuAY&@om$>lTx3R7i$z|~y#8G)M>vCOM*|n{Ps&jw|wz`%>mErU5>-0Q;M};Gn=$T-rm;B}Hg<CMJE>*AmZK^"
    "vmZ&!JXGvMXq(1~*_H%d#|Dk_Qw?{2F6f?Anaq57JTk4R-cmEQ4Hw0wIWmrY4SwVCGO>I9O$1Su%f`d2bd5&vILn7=x~=Tox"
    "J0RPTgxK5AWMXV<m23i!Ma79gqQ<}6plxklgJJ8g)elfQPsHlXSu4d2%B?i2gMv_@mkpUzi*zkQGeKna&p#E5^%>BdCI6-S5"
    "fiDq#fkxCR)rwICQ}y?W*Jd>J%(pqL#`$e_zAMxA-{}r^kkmEWUjtXSdZGbee|NEurl0|`VHANff7SA?`|JemmTchn7*PX>&"
    "wFQ%PH?SM@M-<;4a(B$KV|~O9Ie1s4zL)Htu%~b-x2-lrrh3v)wiEz*I-Q8O$Oa;h+Un7rvND$v15d0#jzip<1<}udn{hdB("
    "2d_oMfyt^kTj=&99s9Zv}~TC5ZG~{pQO2pTqq35*1u%3LBg~TG0CWdN0Nkb(KglJJ9Z+1lS_EgX)3X-{&$ywI-iobY|Or;KP"
    "W6ucf1|9bdzggoX&dizCsCZp6U0!oR-h8|NeeIQ&S}>#NEunr+}vV2XAlkz&i5kJo~XQ?@TV2RVOWtVjtzhqu6DM3bp<3kue"
    ";;?xFBoe>6gyP_<_q6i;MMn(Y~0gi&(Cd_JyYCojuxW8@8DdbhKL~11DHj;3K*_%Xcb#^~WBV113+*P?o#n>Wl?{DgiC=%y8"
    "x|~b*K_B*uxTRYe9FWSOa--N4P{8*JBFO7cn`2azsc-M*DCH!3(G>X@;4uX!GTG&(x$V1{a`!qjq>{@-Z|GE{cjppt*4LK%V"
    "&+F7Xhro$l44wMjx)GxUKjjt13T#t;4nOUYtVP${&LQ5f;h+e^f<{ymFgd@L_|oQWrn$fOIlg*<hZQH=Ls(uBoXmzxkh8%z-"
    "M`Dwyw!i)bs(H<D0-bNi|?QOpo6!p_<p{Z9$@NJPY7-66h3sMDW)U%sT9ZlW}~2O)5jY+$gO{G&BgK&>A6T-2T*`ZI_ek$*>"
    "&}hbFwdIm8hcV38Oe#BCH~!T6%2rQqtRGq>NDQzdDI+%9)xtj$z7YUh&PH?6u$F_Ujv7DPFPs7NXK9_-qGm(xSA4hei_!{Ol"
    "2ATCYo_eh3G$12$r3K?xS!zOEA9ifr4tU*;_9L>9Owl0n%@QHUW5J|CML#uPYlE!|^_2mBvKMEOSar{0MSpUcKH#tFzySy%t"
    "n%hVznSWFwc`*xo;eb(BPH&bqdnsl)<ePl2snvgRu{&8Nv!0)uI=l{NGz`l|^MkY-5FA%E^f`gNNN&O@k73TX@zvvDw&ubqW"
    "1XHB)?az)?_(TQU8tg(l*s5V9Sq&7Q!`cEl%O)<wr1*fPPJ}Bq}~glT&*2R{DT}XB6M`{d6^sjmPQiG?!H=*MnZ6U`}n3W29"
    "kQiJK9Th+jOiu6+rPEfFA{iw&(p*<7XdZ5WA{NkPRZ#`z;=*4@8<<-2XCB?_=gPAb@HCE>(YS|C~at?+ih*IS`?pSJmTUITi"
    "SQ6lyZXm>>-#f0CFj)|5kvUHG<(8xk3aK@_;DH;Q60jQUxG^zQA9C4|;9p}(CmhV9~33gA{<cb}Jbv3<)d4}N#ob|k!&LQ-7"
    "<)E*xsch@Y?9Xo5^a#~<eTFQAOHC4fBojcIG^-7wthnvNzr#b4j1;d6)h$2saG1@7lcSbI*qFe}9(ptRA3{h|JOWL{*{7~D?"
    "t5ljXB5y8b-~FcO;}is!Kl_27^E&k=^jVTsH*_sZ9*}&JFmC*pGd>2Jk(TH-0t=IV7>qUk5I#ykdetNjQKL(u6TkDsElTtBz"
    "nK{q!vU1jHB^&AwxCZ0KjQlHJ*lkzMzYfuiq@@cXGaY520aMSO(5f-kC`UT>6T7u;7TPGqfYMZ{M8+G$tM-8#wyF2eL+<CI{"
    "NGfcD={~r_W;Y{Uc_J9jdype}{_03)tcm42$-!`MWr+C=%!RCr!<KX72s_z|z-+B12x%)6ZGgY}QI?L?>K0gdWN7v=oc-j=="
    "u*2ti$4G@pJ}ez1fMrR#%-SK0qo(j#XQMI*a15vnuIo2<UBjVcr2hu?XhR4?~ud(Q*>SoU5Ft@iKPwE+>b|8%hmeIAJJREPU"
    "PQOFFAW`weuNjU=_8o}O+%R9Y~m<WSP>@_>_;afXM0mbzKUC|ftF)e|uCOdq1XOa7zNlToV&QJJFxxi5`|DAp4gIP(VM7q^2"
    "=|XA9x8GkB436#N-VRQhdzx~@j@{*0aO;33Zl{;XEA&nKxAE}BC~%n)GHANaJMVW#qy#xs&$SGng_77oMbmFNFq5wg(wl<_f"
    "EV$zQ0QC2xfw|Pa`SJb)ZG6aJ~SB-r1oA2jN0QvBCDZfW!h{jv#aKJXAM~iP7KV4$iTH{4n}sgZK`Qt11D6-4~k`>@T2VLD|"
    "B;h2<!WXltYrfv35taj84)kxML3OYhk9VJWQ_ZfL&aNpK37WJ5>Qnb=a@|fM?H?8go3*ZuG~btfDjr)&!20$4@m@)|aCq)Lf"
    "b}p`D{omo36<@qS>=HS5vzry%K{MIhYSH6ifa@Fc&DIkG-xce5^&u(R(+D_CzY{~w(pEb)IGvNT=J=}jJhmJ0gFn`BHv?HPm"
    "L1B^C)Omz;qdZ>lqc=W)5;`uN3ZjTAsxaHau1#1efdP=;!1=HO(&_A*LEU|5wt>DaOpz4+s4J@jJLuKx<lRS(tg<j41JDDqK"
    "UIM=1ZdbxmMz&pug^YToQ=`Fpd<C@X>i+GJL#jfng!FzKX?_^NCw(bEr|JrPLXB?m#P3G!5;CRLM|^w^8cnH!#xF)9Yh(fx2"
    "+eyI`XzfO6(}@b3E+0DsF45?n8w5&cWbVFRnx9EuD~dySqzwa5u~6rp0w=lXlqX?-og$;9T<f#osOg2iw!PXYl8V^<)^faSz"
    "7S!$+ClC7Ng;h>w-OwDE{}?SY9x3qEXV}oXDDSt<CD(Fk}Nsd89r1<9H8i%k9Ea3k=de@jB@{6-#wHa3DCrgvz6Jc=3Kt?Qy"
    "XH;W(ZgcU{D3O=c&|dCt<G1sUFS)nCrESmAU{^iKma@df+|U8$-nco3nz9YGk?VenC8ij?46q};(auJskkvrePLW0U?`X!zk"
    "vbzwogP32vE>)fBxbD>IXc;#9l$qqbn5yWL{Sg~F|0;TWUr@b@*a1!1tW3LI6@7VFG?hokt?icAk{hYa;)-++nhohNs>=@rX"
    "YMM$@)ZIwGfclbQsGExOd9e}`EpPT8Bysw?T*B!3gyU5UD`9UFHtN{{{o5O2<<@c-!dI8S>{(*BBuHi4T^cqBAy5U1;rhi*J"
    "{P?iUz59ADzUVUi!+`X$0AexpzHolIAO8MLSW%)_wbg=u``a$ppXLr9^N2r>8X{h$=le1C`8+|F_)%);Fr&*8+Kw9<CxD&I<"
    "6LWN$}ggzX^X~KqB64Wg_)02!8U5X;sVbZ^5C*qGi;DT4;ND3RiZR#LSV0VvBi@gH(RfAP2yD#97D8ujH{_J}oC(u)Q02FOC"
    "iPO4;@CINWwk(`smUVHBgGOvJGI%f&!(A(54)v5pmX-;MNR{uS5XuUdnR6-VB~tH92?8SekbvRQ^j*>+uc7#O;{yBnpuQ(C%"
    "1>F)0CMya6$=?<llkPhh@a!_gjk&*oHdB0zC9P?{t-)o<Ht$p3szMA#>w`W`IN(kISalEG!BJX$oWq~GymLadMNySFXovQE9"
    "yLh7+R^r9u5{7I__nxDM|M=+nw9<p;$xi0lK(Xjaw=?DgT?WC}3bP`imEj5OpE~n$n<~Zc6!Y{;6(VSpCoxC-4(?Mivt9A|Z"
    "_M<=Po|y5B52LN>KtY$;Q1!ge-#QASF3r}gYj%%@Z?;w!&$5**{JrS)JW#1ypoY)mB#I}lNV;Apd&J5>w{^N4LEV8CLK)bz?"
    "8Zrc@|#yVekDaa!Mp>BrPR2BLXezP-zp$cDGS{u;{N*h4z4uwl{&g8G!IXS1-o3#jq_oDzwFvT?~O0Z-5HWE<iH9BTCDNz<n"
    "~;LR|h~Sd+(M#DSC=Bur-p81v<tUk~VNk1)Bup0i<4PEoA+{(fNyg*<gR!5(nB<|w)QK3vJEP7aLqhN;Y9fe;#}<o;>v$n_&"
    "kWJflg7{KIxbZ-_cB7`NdsaPTwRr4pBWS~_P8Tp1_g7KYC(Sr1zM56>c@H4vj%1PwtTm4G(hlPZ{A<|Yl6c49&PNaI|^_%qI"
    "R1yW*(vdzW&U&2AUe#0Ao7|j|#d}<z&;#V-MN}Pzf%+UKXE?9`R_Dfm8tG1&j`RY}IAF~mZG6a|DgInRp>V~nend;i`vU7*v"
    "v#j1;{bwBe$dyGDsT3wWTCu?0FTBrjx)Z8;|IMr>`{DZfHbZIo)rR63e}<2J^)Qz4AeD1d!2jMQ~cx4Q%!UKNVjC%gmla((?"
    "Z=WRQt_GG!+_|;@w^j175rl9{IOfqoS<#PuA~|IkvD(8DcSj2k>8{b4k9IFCRKN*%g-Q4Qf{L^_+vo8IZ+phx7Mfr$U$~*-C"
    "R-`=BB2?pZ6;<K{qxA7d;skC_8pq@Y!V81<1<{JNjxWB0AO?!MlKLRCaC4REo50v>!s=hvC>Y2*_H<$Hn`8U!c<rE#O>5T++"
    "|+TEr_HqFgt@df6Dkh|Hw0-U#8CyDZU3tpe2uIf2ZHyxC*A&?_zQEO+|j0a-A6WJCGLC-U0*c=Tu{sKs4BGZEqHWfp=I$My0"
    "_>=q4EQfJJ3cPMsqoM&Nf0%`7B|oQLY_L>G*KmJ~8ssdJGs-O`8yR0DG~$sli9^lAwA+yD5*AD)=F|`$L3oUdjyzJgyZpO}d"
    "5S9n1SnY65I^+xhcuR3U4Z{W%O3i}KuyOK2G6(nxiPO!AJ1czjK<R=pWiwKX4Ar$ULhQs%#@x{GPe!hlkm`;SCQ(Ii%!m=%7"
    "%ZVFl%-?F+};>{^w0^4qC}oNHv%PU1W9cI1YOb152_vG+Lp+<G$ZJ<V70!!gqeWFKvQxJeptEH_rTX<_`JOqU7B)^Zk1k!kS"
    "}1fQ*odcPkZrX9e7C*A!W^e(T`-n~BX-q@i){bWs36!8cq`?$nF_8j~e?=%V*8`HT|63_utMPOyjRUT4^;RZwg)ez~@9<jf8"
    "d6Ho3#_GXAo9h%T-+4S8({mz{(_>1+k<ex-pA~)3!5$c2C!Moozi)E!d-OAeoU`{AP;$A^5<-NCwofm4KOZnzT%^jS7tRK;V"
    "T2&DCv5c94cVx!P<z@%)?>QL4FNqjp9?lScwDvd1iNe39H-#~Az7i?s*11&)8OIpp9uvo|S|II-27aD*Vkd|W8Y@WMT46#i_"
    "T>+L^fH!nnl8d?n-_>9$maJY6qx*><CNd{4(E%R`0A!23b|QeBy52cAsCUGfYn_eF$^|%Z+}C82?gyjDn)%UJr0yEvdi6;Iw"
    "s8`1#heU(VA<-*!FiJn_VFwQfxvHk+lCkjEb||2?MvLsN0_^&nUg9GL{j5BqPjU=U;UvYHKnu`-z4jg@O2K0yx|NKm`&m4~x"
    "YJyGq{B>l*-jxhx5BDG>KL-z>|`omfxUKddh~3A<owu!48hw5v&;B4eP)Y<0Q@-*q~ZG-<>kM$S9V^egY$_2U@bIxVIPr2aV"
    "WoZSuH=;?#lwBUDP&jFn!&$O7U4mw2Fw9bXn3An1lhGS?ro-3%=m~Rz&1qB8J$y3<70?otT>-!+2Q$a|sF^)laIs^kFc$id5"
    "^%-K5_olk%vCrpKJKGPq!1P16DoZ?6*_7}`b?lG{9Yyt1!^sE;OB%K1u&9Q0VD4K&bK>8reBbYQ(ECFkMKuZl`xOLPhgy%+("
    "rGapeot3HXeI3TD+K-hTGr{ANwgt&X>TaxZT63k!y84+Sbvw=KRu(GV!kwW&i{y(_(tS6<kH@YszfSuJTm;lpK(Nx9bqKvL5"
    "k~MH?o@0qh2j@vq5cXu*|>?&QB;DS&MFl>!U*|2ZPOv1FX#tw_>tKw~pQiefPhCxSw1y)cy9gY~Ll`GS4j?zpZKhD(fHIdQs"
    "}&qNl=GL#hjE+WeEL#<Ljp6aX%Pf2pqhbQk{zZF<SeAVuy#oV!Fc#Y#7@T32)A+L}V+@bnzw5#&MKTBL3}ZOl+ncmoBS2VqZ"
    ")Gi&AG83z<x6A}4k;<an;kZ5*`1ZHB3KYrcBvc$wCUuFTH<WZ9iJsv7dIoHueD3Ba@>nPL0GxHbL)3OuTgWdnoo0kYj=;t!b"
    "czx@TuBhGzp?Z_SOq^~<#cHx?lP2$UEOU3<IDbmm`>Q^&M%DL7<HvNhzDmO~0As|x$yR)kT=f5_IFi_YiYgrlppgg-?>-mY)"
    "S@8MGfs{avi%E9hyFF-{D>U&EQ%m~*6p1&Qv{G1C_ehMGOVQ!>3wZ?d33;*T;3)?k;NTu1447tCXrqV3jPb@OH_>RL-ednU;"
    "i@F7ma9f_y=F5kdSo@(KqTzHKYtX)6ZonRdwW9OnOPZ!Q$7e`B4O1LfI3KviWZ}Su7#}%YidtN?V{NAY^okpW{RqT+{^wF|o"
    "W^%he2HOnZgN+7PxvLG_p%Exn~8y^_C43}cpF(LUU<6w$mKnc@#L1^sz-|BO$zxSrKc<5O$uh_%1cXeQTMLVx-P?>(FK1s+G"
    "r>e~cL$*!9<3puY>m9P@uLxvQT`F9mrN6N|88~qg5t?<M0G3R?_-?UoI(|WuY!FB(yUSr~5W&Wi1_HI++qq)F4?RZm^W2nfT"
    "!(C3e6YTm6LwJp_f{YKuli6eqNJqI&P1*rcT*T}TI3u6wjO}{$yC;ftcSLr`BwM-cY<^Vq$ggA9m}|8QLEh@~kD1B$mJ0=Xo"
    "43aMD2UHyscL^qGVO9Q1GYfTIA#uxZ=ob;<?~ZwDO2*@Bk8wr$b_B-IE7X2Z0RW=)muwi;T*fOL&)9DE2Xyn1M}qE1YWogxo"
    "R)+FCbX-8FI3DyU@35@r4J$+meCRl94N>Vti7y|7sNt@nPvq%y8m$M_75kk-tc?%->ZJ*T<@}PKz)^UEX|mYB`0}j_Y_fHfO"
    "Kp6mSZGsny!zp5g5-nAASU9UJp4CEX&qt38sKReXO>P+Gf^XpL!Y<V$bjsQ_N)3u`G7U@c7I*KgS5y<ay*ID6=iKWYqsMAt8"
    "l&o1b1yUe`$LHT6L=&))4CD30!k+bAg^dl0>5Uy08H=3@h2h(-5Hv%O`wPz1n9G7r#@UtZT7ppYoy4ts=+pRb3B^F|;m=o=P"
    "S)3nk5ZimpH$l9HXVg<}TDa<sS+i^gsfy9&&AmtIdih$&ZY3gVv7Po(P?N-V_EI^7WtP@fLzazp{p83^*<)krb8K%^<&FUZu"
    "BV1J45o>FQ<^n9j4KJJALVZZkv0P${0=$MsLZ1tVJ@IfgFN`1LILY@zxZ*Wlm-Jpb=Pm(pTcgB)T%1#y*9X#$XYKo4sV7;Z)"
    "|mOc7Oe{bQAM#`KrC5oJjJ+hf#8)bYyaqVnu!VM@`)5;e`K&K=z#a>#buq4oK@E(Ufn;92Q|BZ+HT|{-$E(+|2E<Y5P`z(Gk"
    "z(L;qSHE5tJVy-;iR7{XPGx@j@#m>6_spE2C3BN1O_V1GyytWzm$AKcX)!2`8hD|Q((u~lqlrRC^aajLlTw3E6;h<RXf8H*W"
    "Y_fuKJ8kEE5{G=qqKfSbw8Xnhzja55GAD2?((&P09Qv(HyA5vUPO4}^20sx6`t_{{7g1lv;dgdYA;ZsHxw!4C01DKEa_osA!"
    "oyzC$=?qcOoBe&%07|Q2v0zcLB(9O%Fnpvwd3!D$yA{Ie#}cu)Ta6MK1{Lrkw|9oL7`Z!}&_@?-QHVCaF~JWBec#N#TTa8<0"
    ">I#@*Zv30^4`|?Nh*;%P?9+;EPZsPEvK<#bUM@_54nHohSIotPbr76=I-%oSAwvf`O9{x1>DT))8i?LZ*5FrA(zxAuE|LN9X"
    "eL_G~OCv&Em*xgT<Ir7J)rtPl_r&WVHz*VUWs3d!HHgI<05Ty8pcF$^}Z>5EvR#K1)Lb|G0FhSOiq+-jf<%jNCMaq*{FCIGZ"
    ";_8PM5ii&G&;_P1n@ht2%;5|@>O&RoaV{PGreo0_(k3#gbzeWaBx8>ojL5SHB(?@6|M=;n_dB}vWE?IYo)XyyYFT1_9TCN5a"
    "gXsk<j#%lbO`$rR`{hyLKn)WCEDiTPEhLP2C?rS%WlW@XOS~9rM31@~fed^}5B6fZH!YZ7bF5)7?z;locesZ-nZRGwQzr3ua"
    "+U|Fk+A=SKO70Oui*&CprKsZqycUz#G&8cofo<9oYH=cubM-Yy54cQFFCS^uA!~Hr+hXV^MrCLU`(VytQM<@9@W%Hjy`JSWH"
    "GCLdT5;#Y{EQeL^#N)&O=wQZNZW}pJGgdM`R-tvx$`_znHH3i${s?9Gyo$fZ_B8SQv7lWt>N=S4Y%vZ(Mc;2pFJ25dVC}t2;"
    "1_7iTpU%ya#VX60d@-gCwrHd1gDqDMgBubRGCraA<$-PrtS^!U(Th9-S5{YI=5c4rE<GF>0dj_lJl7Mlgi%l^UJ1DpHP#7ic"
    "m_f4#3E#{o;7TH;$aVL(pUpM9VxX$rz1s#s+<GBN=ze(O51BpxWV3408fU7&#kF(>AqP$&zti$v|eU)~UwsedZswsx9F2a-A"
    "-Ro%wWh6~bJ0u395jZ9MkTC#JVc4WOJr$hVi$z$e~+jd>c(x|t`9_zWB<s!bM*dEBelsNUjp8ahGczd}48(_hq2HRn_R1Zo*"
    "MB}>_l*-hjOD9sevj9=YW>tWvWFZ|7LDgZyv2uV+RUCopzEGo?or$z6FkS$186kh5qo4v98_GPHDYX|!k3%3#0A}t;@HdtU$"
    "NR0kopzm+noXCg4|q7%O_TWXBO!KBD|hU)S5EoY&mZp=&n(A@;g>nJrdCWL;ZQ8ls<&BJXJ5q6Gj&F*Wcoy_;rJyu707GJD}"
    "-n|?+*JN$?)I?O)+br>YNnZkS5?4@aG}u?zcUrXvApMiyB9Qh<PgKv!GuPqpMzF`+vMIfekd8^(H2r2^t5)vZ{1BF@Xit7`R"
    "aICGM4iCQ|cykv<$od&#&wC!RWD`Bk_$q|8E(<`>CBY?}V~0D=D|0n&ey;MfTH$ET{ql3_cq#Z@${j?W{@x-ywHSqS2KZbeG"
    "fpSL<6b`0D`j*t4c!|7-7v<EVc<R6jF7)Lg;SYYL?(A8IouJoExP{&WOz2m!<a$CWZ)*MQ`i%eQs4b}4;Foi)f8!0&VmOY>%"
    "L`1W%K(?k30sEff*ivZdh0Qk?B8;a@(ttDZ<aT>vY;CELZeI)nE&Bk=w#*}cbFG~As_?%(1JG*>!zd+kp)Mk+@^kQdpL@7lA"
    "hVP@)JlsWl8TX>FHn`iWwfjJOC*oJfe5@R19A6I#)dWfTZor6<%*)>{I5#WN1UP<4`PLn^f2_%9H<ae6v~<H$&EUdWH$evlJ"
    "QJLMC~byU-r<a`MTRC``6BaaoA!r{}vUY*!Pb~w5Y(Ww;ifNB*Y#;@6dd`NzE$LS9PM3@DXeu6=cKYKLh&=5)Qy;1Ns$Y_aD"
    "cMOX~?^(UUUD2I8PRkaevB0ssSSc4_;Kf3q2&Ef$?>_xdl{)J>qWy)PxY$kKy)d#Wdj3EV8HC)3l+p@ve&XO5<kJG`a6H?VG"
    "RC5q^B5J0Mz#m|Hg8;L6i6UG~XL#`Cgiv#eC0iPGdhc4Z15O4Jj()q2ir|z~HuA>^GYI>uHb|yy8C^j+A+8-~@DAv*I)8`Ba"
    "wJ2(5c1do}uUUa<AC-yVl^)12!iRo7(Zrp=N3LWdV(kUFVUf0MMfsuT3OwzXDsk~nrrpjs5U^4+(WL;$Man0hiG4!yagAzYc"
    "ye=LKNtA#KH@JN-W(qGdcHu;?SCDJU-tqEAXs&$D#>fr5ovrw?$|M<xHh}1R?S#s!|3y~)UIE~%xej+t~FVEAphs9f=|I&q`"
    "&X;e`ELG9&L23I$He*OlE6fRl$ekduOF14hV|7a&cRZv1$O*DF9oLJZq1rxQ}NH$Wr?icoLFo@1BIW8Gk?td{7R$->HYEM<X"
    "O*+RXW%9FP_AA~5&R8>B$L#4Q);5=OfPq;06F8G5D0!0+DXRM|oXETjx~B>Xq~xZx}>zS>wWTpprR-fY9~%Ee>dpzL6Zmh>_"
    "!`8D+FpI7#XO`eLdW#xM%*KN&=3|UQJU$7z}9Qt8x%=UHf{0x)5C9AJ2x&gH40cJjJN7!vY%}M$LAHug31PgOAaAa^(2{Qq>"
    "NW0?$L&iUbihM8EPWiuBg>$AFCV$WTC8XzW7SQUNyuH%VBQ)HThp)UynD}k3@SV(nel^|(rB#2Lu6Fe8Own*QpFNyJcb?E3l"
    "ge$a?_~Q5n43j?0!VMNHBZTI!WYI+(C@oK@$Zn>oZl<Z;L2OKuLM)eEX@mJs`06x;8mcFW{<Wfu(j>Z#||BMZR@Jdco~f8^r"
    "r=>sg0MDhJX%g@E^;iNKixpz9xMo(}R%yr+g4y0iJ%Vq-4Q|qZ51|22>uDUkhc;^#tq#n%ov6Xas`|uCx=L(Y8OKoJm71y(P"
    "?p{e!pBQCn6&cI8}~u|<qPj#0^}JoWb(R?dzw{e591t=u*d>mZf87Yu#-FF7iy;-=SaE_1>z_m#T3d%~#`y4p8_hc(SM-Zqy"
    "~^bR(aWB$E0?(iEKWRIxgpIwz1c*pie+cLgJW{bN)qi~?WZf0Mev>Z)6bYYD3G{~paciW}FYT9VCxMWN}gN|<6t$bC@JOfVh"
    "IRvLI_+rdp*>Wr{>g*ZC4R_+Adn-k<%CTk|L!%4?<2Az0V(fYq037DEm!S(p=p<uA?y|wyG|C^=&nQFXr(^<^;6p+T9uR2!T"
    "NryUVUqf$GlTu8&%Kn);0Ip9QQSQi1B?BWj-B<v^jD;b4Ehgg<>?&HNJaZ?g8qy53KA$Qs40LsLtM1yGg~zL`n6vd=j-g$zr"
    "~ytL^uZfUuuE-AD<600f(#r*yR*v$Inl${`nyT_Z2A8(`$r1-DU>2Ek#~ht4WchzkWIMr<+U?SuEhtevH^<l;+^!eM<<RuT<"
    "+23;;5?lSU2^X4Cu~^|T(cvZXN3AhlE!y5>+b{B>(M@)ebyIJW``VXbHB*JUMai#D55xNpBt(`2iiLHf}Jz1qG!+N2tboIfz"
    "@x5o?nq`Cu%T!i^|RR|z|*MUIC;h?(T1XFGoO%&1^P=2&XY^1Xwo(kgEoS%pL2c6_4Zu@DbBf@I1zG#Pwad5z$LvqBj?EhH!"
    "izGf*NXZaqH>PRsDdln7Oa);M(p?d=PeQH=SG<d%n|Bt%I8@OVBHIGyIh~^wh_YrfxuTQg>Z`sK|8BheJmn8m^tiEjX(v|tf"
    "5$7Sl(pf;mjj7@@W18v`ICXp-{plIX691N;#m`gSxW`qxnN3DZGEacjf@7j$^Jrz&kg8N?;d!W+lr7Mc(_KC@>kYKg$D0(a("
    "}~09xO+w@ujA@>@>)^nJ|icyW!SQC#$Yu-P`1jM`blU$X!nrm{%bWaH)7zs*2)aNG(u$<QWV-TMK^PfvG<eMUKoNvmZu1qlZ"
    "niZL^krnjv$nY7knd!y{BI1E?45-Mr4qf0amJr!F4mnT@b!x7d1YAJc>9H7S@7SHpT#f!!Xm7@(<wfsX8SEW933AG&4BX1uD"
    "y%CAEwGDf#TC#p>_$^5NEA~2eZXzm78O$RM>_l;g;n0HFwrt_{)qlIj3e-!v@%BSg47h`l^9X~_undcyd2EH$*t>W|e+1#&!"
    "PbDZzE~Iyrl|CUr1%g*2-2^k_>0G&|Y^KGWjd`eOUZ$VXe{1>-TaZ?*;Mmp;QSgI5`CoSmh1S9A{@8~B7bEYA@Yu+lyGxbqr"
    "9Ol~UeDmGR04$1AdG!%_{~bgzAbJ`@7u36;=N5I9O5L^o&~HaKU1(a&5h-GB?n#lBr&^(`op{{TKdF}#`aE(5Bk?-EoPQ+60"
    "1Qo3>{?Tf@5io7K2U5ECA*buazlsKOg_PDl%8`Vj1GGar@;Bd)t_IOn$}pzKrMZ@sNU)S~NUQ)jq$acW<YnuMEASl_ys;)T5"
    "@EowZhHbJnH54Cv$CO-N_uFpG<;MH<+-gCRCNpooc)E>PEizonGdxw37J2T~vMHLmdXD!BtEFQ}YUu~`XPkd=)I3vo{e=#mQ"
    "He~UK!yLv|wn19jYzf8Is%G)5a7wz%!M|JN>NLmz*Krvd6h2*;QF+yriS6)B4AEtmiAC$LenQRgD*uUh3&Y_6+{ZyPc=I>F="
    "w(a8QPqpZO3Ut7#j({KbdGDe)QfWe(e!U95f>Han#W@M2>qUlB62fH51~YpJ@&3j-xw7H?;Y65x#22RRkZyJFdgX&(6&EXvp"
    "jD+?%o5^X_l3}6N^&&V4kbbR_`L`Vpo~@?j0Gge7{~B;+^rssQZ-2TtR*1#`4S0~T_89XP2x<ROTavLtKYxwHacC!Okhe9-c"
    "?xCM_{qmbd1^wxR6VhWtfp5|522AWUrL6P@U<`jvUQ>d-_y!i=v92ey;S6$SCl;@HzS<X1W5o!|T!Bly|`z=dYLUQ;#KH5SE"
    "?sAKQs*dNP1;Wbvnm<-Gh8zl_d;V~!D_Q&79B?$XYEuXGqK?ivwttz_d#Pws}a+7c}M1|a_Nk#c496O5v<H-Qf&86eDM22d)"
    "NoJK~>|LFreJmo*tBA_xBi(Qs&53RAyY*LbVErnWSL&pR_2Wta#wGnB|yC?M4|6q_~m7NT-Q%aT;D_YC`mKjRr->~$p?LjgK"
    "#7P!E^%cVGip}qeFfV4nl69ttAu@nutvR&Z+guJxQi5W}3~={wJ@MCtLSzCt;osX&y2J%j!FgZ>r?iIaACGz^olBxzXA-x50"
    "qFx4Tf2k87O4>#cm00iva<B8lYKAWeI4GHZR@Mpf5|B2|8qzSM5bQ`ElLxUfln)2VurfZY-vE&VvM7`uqAZWoXx1F3$Gj`aM"
    "~ny_>~}ExU7~TrkqWiyS)#7u>YO7q_`h7OZy%;_DD<Vvz(!DrWR8gdmz8))!HUz?t)~?IIU1D$JcgUr234l0Drw-fFC<S>wn"
    "lw?caaIe~*pIH8(+3<{G<FrLp%g$2(qjc7UOrUx|L)qH~W<?cxGBvw{on*{C4UF!}I{iJ!+r782IQAk;Q`LF|DC#N&~;y>no"
    "SxUOd2G$n@_J;-03^tX}EB;z6qzG2i=Z=y@gx)WE%SRg_jyy!8^Oo6YH^a+PaZrY0-?@&P0lWze&D0BK7#>>{t*?<{-VYtOL"
    "aah1DG4WNQH?=TA6W5q2ZZyOHSE)`v@%&);(LRVGEZ~{@%QSL}eiroW>o4Ca@}I+WEJwMva-`sp<W@d(Ic-F&3*7f)iuQd0R"
    "Z%z^CBt!cJbOr(D1vW&$TM8S88Fzo{3MzRnc<$H*sk{RQg%)%i5Kj%{>Eaae?Mvd0`C&VnN<Jm`RoJOG{>h^#m6Kfmg)=spk"
    "z0SRl+lCfH5HFqPLe?GCM<;Ku?UqR3NFD>-ytd-5QM2fao(RWr19c5&sR4qc}!f$1;ZjoVvM(CmTQ4{_2NWizp>N7yo7q-}&"
    "N;B_$e$AQv#YSJ&LSSx=;^SAwrCdf;Q^>-knC{7%Ah<uGCf%5F8bo=e`1tW!RZBe%LMDET2YImkrpR8+1=cHxc(b;twEuR!!"
    "tpCM-e`)?TD=kQq`%d)khpe$XO%s2uX(J|s5E}GvWRazPsw_%^GaX(9DvHoZ{`v5JNpy!(VA!4ei0-6*m`Rvox-jVpXjvrwo"
    "G~lZ=oLY-$1<(hA{Mi)W77rlTMQBfTivB@AMFn_QfLf16jkk94D)e1x!p}#&=$c+?YPy6*qnO~YQAxw)UA+9s^)uMVlp))kz"
    "#5Q0Ia**>bHr{l-_xSEIqj!@b+%|iNCwFM=JnUOOabZN#hSsCr6i=zY%!YD5@i6bngN~&m0xW@cUgxXz5x7-67dB6&Zu40vC"
    "0t_s@$xO8KZ4@a6Jx(*^1FdrT1?zHg)|39)S3v;!l`DPFPgm{3<#owTtWC=)x<Otd3f|th~#0kPL39eFdU4ZnO=89z0MKQqW"
    "!^<sbc*Q)vw8_#^l&Vk2jtaFbng;}!Hz#a18rgl)i(pyk_BmoWr`yD0vVXl&lX_wetP7+s>GZzQ30XzsFK0IA%@UY4DOm0i6"
    "}04e@xd5VftCJWVXdYZNhaL*^RZCM;0mQ~iD#2mEjo|tPusoqekebt;I01rgG^aOy`p{=B}Lc01sIeMs%RbFGzoC(&ovu4>i"
    "9Mwpo9nYDlh1q`TZ%2XCxh#Uqh>{6?yu}E511N52tYEraha-jF-mKucI+x`fZob1`qZIr}UlFaY?QR`sa{o8|Dt)DI>w6Jk!"
    "lOkRWQ(WfiWfV3+n~S7k9=ah&vU+cI3bl1#MtQHqKO;5AG6u}!e&lz_Y{@^jCFur{OP1hsA<u;Y{#*TMsa*NeyPVv`SkNASG"
    "2A2mZZIjbh%un@g&T3DCsNmlrjkTJ>%qMt6JXW=qeHmK#|a(`au5@wdK6f+C&<i-0r=M%Yj+>9K*AJC9c57x0VNM))$m0WSo"
    "o!3GrtH1Y*pT!7diJ#(rb;$VWA1Rx-w?>P{Z-oGIOkC3Vq&H6#l}@+%Q>y<Fnw&Q=9F_|wQbRhE$eE5keg>_!l8_VIUgBpHA"
    "Ws|utki)fsjFVh!8D37=qfyGRcC*Py;F<+1qetQQa4Sl@QOMcHbS}3<c9N!~nD<QjZJnnVAytW7-?HSpU+E$1RYeP3P2h*~k"
    "*rY4cW%^Q3L=1*Ko)U=9ESN2YeYht<+7+hz&s}19XDJ2(el(~FJ%@QbQ+Gt7_9`a3pb)N0E2+D}KS5mFh}(1oSVWo{zcE+xz"
    "Wo`X;R?jg;Fzmmls1OEA>HlV2_$GtNwrF@tL_P+BhuK7V`+T<)gU+`je0YVj7CXzX&)Rh1r)`!!u<SQEIO9?xVXQ4OFMFgYP"
    "&`(NtoX`m(-RmGBmPtrtsZ#GO>7)U0?jZ3ekNUwfHx|&g;%_)&qG<Z9-nrXisVdE0IzH1%5DiUhNfaYO{lvH!y1U6V3ko46>"
    "+J8T>ht>@|X7;qcPD$3sfz&R~8k?-n<?ppq>c+z-{XyLk~qMC|lyx5V7q$PCWm>lRL%_GekAQ>`H-GH1t>{$LmY!$=$S{Bh*"
    "H#qSehBpLtW|IT4-KneUVB5?v1kfbH12TxbzB1ObU;r9X;QzERtkV)gEy0#4RUia6XYvd_@Q4wF2R9y}SGfIo>i(3PF+oLji"
    "1{y8C#x81q1L_UyZTy;CLmav_5>v@Rf(Kg>r}_C>Dk)~@66L>PtWH$E-p^Lf^wW$buv@?Exb6RS;$6(zvd|X4NJtW^2>bK7b"
    "(2dDI=<>9sg(PjN#0@Vj~~o3ga|~X^b3f7{IK#4KRq*WRC?Y&y~-7UXvdG=2r=Q>G%+7iN;|h6F>;<{dmN(GUb@!mGqdg5q#"
    "U~FdqQ4!_@L|<825=!Z_dKi2R~fMBvJdk7H%L4xEV*eaUfc5U6d;m$gGYqZ;hBeg1S3}V5#YKj{PFg8H#-IKUCc@cu2de&A>"
    ")`!tf&@sp6nyO%kYfa!M(Q;;};tW^t|La?rLR)_Uz@%^W{NFyuDZH{u7Hv``VTOl~Wx9>aI{K7r`|$K5n{!Q`$9m3_dh$)zc"
    "L_q!o#GDk1`us7%!2_cXj;FCM|k#3NeKr2X$Y!dC8!NXGRb=;_3^@yl1wYDps9a*U7A-hIxQ=3Z=!dJHqG0EJLH?x-QP2)qP"
    "Mf6ItdSTRhsJQv@UlCY;*o1`h%Byni)+0+66^#Zr&T8N-AU|1?8YF_AM|UsR=UAV3q@K{23zaxHcxwdqhFbF(#Wa8Dg?PGr2"
    "HsaGoW2_~2-r|Vqg}LbHghH)8{bgh+}IqLt)gk2V{lN8KQ5s~9V7ZL=W^1Oa(_uM(M1otgi)XSb~G)bW_-i)woK=UlFhSr4I"
    "&4;8!2H|xH-&lV?9Z6rKn9L(95T<S`AEO|2VIK!jdz(6L?Eynn?e~9}=x!Xa3l78v~nOqo)vo&g+rmbS%5u1)yylpi$c&&?U"
    "sM5mvZgIF(!)<cZGlJT6Z1OLH|D6{*xA4p0$vNWbRbC6f0)`=)|9+)6xfeV%Pp-b`EHyyv-TWTv<tpYah;L)MxUmkK0wXU&G"
    "rfT`D>Ky+8Wh<*lnd@E-#Okp1a@!5V|*3ycf^4;9-Z1F}gx9n5Ktn9{CKC0FsI?V;M6a6w`w+cq=Mg{XUq62_*k=c?@v1lLb"
    "hn3gJ8*_#R1K#~f&p!8py>3mZZ#<@cizCV4BLC;3$3)SZ&LsqiU^`OxNEiyKT=nT=csi%;k1Lq$ku=UUTOk_l+U;x=j@dfFy"
    "6YXpDXutq<XjKSH!Fr`!Q%ma4n-B+2)oK_z;kzurm>U{V|DbJjxe)4hA6osFV;Ufgjj%~C92nYpj?jTLreg<$CTHf2p`@6Y;"
    "RHj>r<mQHKcN=xUH%KUXsNPr$D&(9pBLxF;3)s?R2Fg=?W}h+Ef7J@*pxo;``*owm6E{i-xzAsD&`=$Y-`nzF$<_u~-j-K^K"
    "-2#@J7By-JfJ{NQ<1S^h|!Zyvl6Cdki0U$~>@ZjX&i76mL2KWHB>UMt2n=^H+*K`petO3^qiXOsru%Dk{9@jrvOJoiRu>l@D"
    "o@cHD3Wc3I2#xflSmM3e&!#pYAvn-CQ>6$ngL3&WVJ10lO(IYhq7q4AdH>l=@RMpdzih7Wy@0xoihHq9B=P!v(2=jw`h1RjG"
    "4cpJ%%OmoIarc4rE@1JGbBFulALY!N8>xg9X}er)*PB#wDge(nV38mvuXAMST)H-F-4wxw5|Ok|g7G;4=f;2oROyH<)ndrtu"
    "UF0-ii-5u5fL}P$B<e1L2=Z5L{?)YU3`zYuY03!Xq74U0-i#EW;E?I5u;624Qwg>H&6G%2q_t5(zWBbpV%6U(y{XxZk}`w`!"
    "Vl6f6>%?d^K*zl~+R$-XY2-?eeVQaA3?JKyLI}kp~m@_Z0JeQZmPL2v<4vOMDOeFTOW79_c7ll}CIy$9`#J1<6;*RFxT8?P;"
    "g|_JrUsV>`X9=N%cj?TivIi!TWkxjH)dnpsE))2}I_R)dg!2UNwW4VS~WI(J69d53TfI<xJ8lyucV<-W_$*sziPvGF0)KK0k"
    "bmXo|Sq^*Vr2!GPDdt}|(^*98>jziYa!2Ap5G!3jH0J)mIz!=t_yJr|x^RYHEoiNZtfbFGnnQO`Hw6(~zcAGJ4Sv&y(A?`YD"
    "G&QvXzR+b?Ysv=4$-{%Z>@yUbDcqh*YvcJR>*&s37z^o)SM-+T*LrzQW)&*tiaBeMOVtFXzE}5G8IeJvv#fYpU$rSu59lAU7"
    "jBPHkhgd(Jy!dB{Ah$$47%i^JM<>b&|m7~WghVrUk2CQryAI`8?LAM>s$?9a(iC7LM_XKIuBawQK0;>v>S@MP}%&He4_ZZf0"
    "8b|Qau9{9$N+|V_nsmASSET!eIle)Id|1L+{s}x&Sqvfz%l38sX(~=xOpCQ&nPJy)Dr$(0L&|QEX*SOOc6{uWl8l9u@4bn6k"
    "Un!q+!`em%VQB|xk()vZK%T<nBmt(AsseJZ?LugCtP>f;lru%xJGsQOtX1{Z;xIo5;Rw$R==Qa{7`+k5!5P=nQ568nCD5}*c"
    "MSGxb4@@a3z%sD@t>nYKfAmp880mEwaV5Se;K9pLmuMo8JP(xe|LzG>S!+&77&CWuHZ>==$%YIGpDCZ*w#kZ|f;g`Cm4C$hz"
    "%4tMVY_gTt+^Ehj@=nnHpmY22ePp@b8?}8`Uef|}oR9lhYW1)*#VKiQG{o8dNHG$K=jjfT@hAFkkK2eu2+(2~c;&fivNHfxO"
    "Hw{Ql46YUi%I53c<X?rXhN!E=BfE6u|_j!slv0m|EUfAqDw#khV8NYl1xALBDuYJvxg%I2S9PtZ$%8cXR52%Fj3>suAaA9@x"
    "6C1fA)$Qe#d8wh)63lL-^hpCBVeKbeSn(^?hIdtX4Arp!!ywt=LGiMN=$gQg||Ft5wdW(4nJS?kK<yL5sE|YouJqzo$KB&3x"
    "#3M@+GGbT}2b@ScE1A~-&-VB@&v3N8heI>|X|i!5Q?(s6Gl+r0>eBg_bW95^B-cZi7hW>`(B)EJ-+uAAj*Z(OioMt1(7T<%I"
    "`0*0}UP!(WRoFRt_h^1)0x8sF+YG6+1tckw>%K-Rq&cP<Czv_zdtOZP0n!w?gA;I0ean{u-;;9+wOyC97GSq<LyoB&Az$eTn"
    "k$8`HO|x={U*3SS^_bJ<5HnEHfc!2I1RjX>(ZO|bmnbw3sL)|%jr5`RWns3D041PFdz#xF<?9ot__48Y#iVt4-!a8LY;}YwK"
    "0U%l0X}R`t#B8uMeunXSbi-!0e0s=4g!$#KrY^KNL@5#-*`BMB5x^1n-kJfxR#Q{<X@aY1{Yp+KC+B)s(7vD10TLi?^d8R2-"
    ">_5Txzs?lsEQOoHh{{G_v(JxOYo}SkEr8$~E(@uuKVOmJDEQH*${7KT6ADrBvRXRaG9YK?pfNLVn4z(Fz4Eq!sXhmvYp|Pz6"
    "N(6O7Y4PW@4O?qLgwFLApWg50AFq>cg^-d|A1JH?X?yPRoWoRE~k8fck_WmbLm$N8I*3{j#g47k%Vi+wt&u{osu5-s|oC+Yc"
    "e1dDSc+f5V;V&q}Wo)VW^_7TgK{Uc3S@(FYX(t}nSiMmXLn*DBTd`ly}s#|GpC~C{#a~+C$DhEF@FKf9-zB~peZUvjUQ~>#{"
    "!E#f3@Aupfv#nS`6yQOso#^5E90k)2;W#gbVRz8nwAaIuSxW>*)4tlJ)^3~~60H6Tue^Kgrdj*pXyc+ZCn)(nvDGf_Mj7T)?"
    "Kz(Ht+w`Ln8<yj;n$d%(yRW%+n<pp<~3f9kVNa>S3rr%c{c%fFCWnJiMhkA(%7nF6qe92=-<1-4;k41E)cNkOBnU!T=#NN!="
    "<GD5?(7rp3Q-2K+0{q;56Ah&(Ut%#`f+7WZEUKK;*4-&w&fe?6^zp2%fHKBNnvSBuZT^`wMUP%K6cqM~GY@4yHzq*K9DuLr?"
    "Eq%mp@+T{U9(ZwBI`vDu5Q5kWMBD^fs8$|=bMhYNjed$X9Vr#Q|9*yTvbYL<SEp^bRDVj%mK|MMnDk|b6gF8f=0S!S$dfQLq"
    "6NWVN{S~1yTW(IO}B+B;Gdez_dEVUExya?EKP20WY?vGfM9MBSydHtRDfM{>COlCRbhml?**}CvMWAvsL6ab6uW5as?3W&0@"
    "NW8L`)6e@xW&Cxj2s~`{WcTIAjlOZfn@s3^hxYV>9MJztBXWFHj1Tzn;f>Fe)Z?Dl!#2eQ#4`w0=A*POXyPcohC<!szE`)&A"
    "VBrHir>aKCu~yiLT9zU?v&X6Be;!>1AVmz;_JSc2ou@~z@eEIk2Kzre(MXQ)q+jZ3;VK`PVjN%Ss`wkn2k`_b?}OcCU8#UHu"
    "aOnFjoc(gP3magi#wa%HLnyB5DcEz<-(2g~+4dFqD+9{)BA8cxP}@tm|7xtixx;;O3P>ypW5!Ml0t~Vn&+V`QJ9!4`NHVCD8"
    "t7_E$9%kg#uvRk)B|0y~%!2~XLF-*|^&;(|mZ-qWBxR-`%w?d+AUt?SP^w^D}P>@H6e@)YfUY}8W=<H^=ld9Jt~L(o~b&;$k"
    "ihjKn%k<m!no}vG;nL%!V^ay#V=+Awg^BqP1N31t<>Wm41Kol3uF{hyU0rO$O>C)W#YRa{<kT`FIw`8XxSD0F{8#=>ffLCdp"
    "n(iG$*2nEabLcetyEE9-exjx-mFQ%8tQHT&xP2=4v@NjTp8{+GiS4$jBe3~_O8c}Gc-oGNU1lfBj{+*;2DN`1il3`u)X$y|Q"
    "?Kk<X(x5~<)Zv%iU)reak)-@I@nASzST2_OFi!~JB8ZLG%JQ9J<p<`KYYH@Bxk+QDE{VV)}Ok|FC(8sKRJ&shm<YePVIpUE@"
    "7e^)eTKKdRo&f$G50#pm<7d%+|Z<_bi6+1f~FyLn_yPz7y2ElsexW>QOg>rQu8b!_BM4WwZDfYlQGcYju8Lcn14vtiE6s6CV"
    "MS4*<wcRFRi?iz(_69!g5jgvaL6m6L7K+s$CvU-Px>^WLwM!_|S}2-+aM#aW|C$7SY8zA}NxGi+whw4E=1$hV6{BNii$v;jJ"
    "DB-lKJlse&emQGlU1qH_-WCw5t#dHH8xbE+V8}fjw=w}Z+&?eW^ogK<^l+=r-bUbmjkMaf2PobNNdEn=bF`FMNzZpZscqFWi"
    "8BUJNggnRD5yJ8Sn&&JmfQQo|g@>7wM!M}a#UE#M6R+B^5@e0x;!32f8kvIRDUF3ZH)X40vv72Am_UrIgY5)Z6MCdY;e-x9{"
    "B0vXb8mY+h6W(Jz(v~CQxbhK)Bcr4zUJD8Mb;fkDkNbyFzV2gUjoSrbiu}!`N5S%QS|e#%5llC?9`Gz_kPuKysxq>nRu>bBy"
    "v%)>Q)P{8TKww-2!k=^Oj*PgaVx;LcRZp%i4gcB@aHV0AL&2HfJB0y@n>kYvLG02YAl6Mt<Jz@T|z<4t8fte5a5ZPsI($m1z"
    "Y*ELX<2FV=L+#gTIU(g@ROS4mCyp8nb&jFu5#*IuQZ?n;PlM{OTU<2L^`btHOW^Km3>J05;?9V1WmeK+Da6*qZGiCI_lt!Bx"
    "f)<WEOeAinRAyf;)WwTO&jEYLQqqeQ{?wHePZA+7s{})zI3lG*{1RJ0~`a`drHI+{NT+HbE-2FVS*Ik{hBiB#-+jL{5xJWYp"
    "3WRG&>O7fKKjtU6e3=x7lY!Z86&E+ZNUnfe3Ng;wwcO75+{R=O-on)${G;-f0O%f(Yy0homWRq$4|G)F0|?DNq#f9DDv3BVg"
    "~K#Gw~{mYxLM-p;8kWd?CISoBm^<oDvbEW4G*MYms8kR5Ju<Y%8<&PfGH6IJ`xYmiMB||!z`+5inCkTp{=zS1{V7jq?9O++-"
    "mdmJSo#$g~{YyqM|b$;nrCJ!AQ^C4k`VAm&M>~m1_1k1pL>8>gx1i6-j%(orAVUA?IB((>cF_-s!ZTHqqDid!Dn)TT8T5NAz"
    "qdc5aQ%+EMQxjgseDHiHyYm{e+B%<?~qAeBbDVt30{gl|wd!6)x;n~3chQ;-v@5ePaVlzJ{iW$}&%Oi|60CdGO+OQTE3_7+8"
    "L))f3G(E+jViy6+nJ&eg7&R&AVQdb0<aG_Qvl5m|dU}M|5m(|@V0Ppn{cP6j=4(Tc{MD@MKm=x>E_+lm?E&?i$=srgU)&Rov"
    "Lo{}(&JzIC88`7Qz~P1g6T2DDxp6^{OeC?EoaZlx&yJ*fVb72;e<x?kP#-Ffj{_`b_DVTV6HMivZ>^x18puDaKei{u+Pn)h#"
    "uisSlnC1ioZUD2;IpdodbKNt)76R$J?s+B*SBgoR#y%w8TG3uSAF^0iv0f`Kf67$|8Uk}!5B0N<7*MXM73N^Gv216!&~U~$B"
    "dNyvwl#aL7Hi)wK}__g`P$C@q)TDBDs}0?Kw-n7CMwd{oxEp^4kUh3-3<}6j?h)R8jAAlVM`<+`=)I#WYne00C`;qN+@S-_o"
    "0_tR3qUt%L9A2ug8oi{sMwHWoqv3FDS2TPEpqVEmm(Lvr%|uVca!D@>}rg9Ml@a}DIV4cO3W0`Gr<vvkeHTXp#HTJguW$rd0"
    "zBR9m{v}Y>lq4=*ue+QHEuz}N~MB8K!2p@z#uBOU9Jj~k!cef<#bp;m6>u0`T5m5G$8zXrK$fdJ3C`&dCO(C>UA#Mv9ZC29C"
    "xp?c}*V!C;n?qBB;#*Uh_~MVqV}f?3hX)0EzIEIEX|-3?923N=boi807{xJIANig}of;YXpdNN1R7r2~7GYkMlZEcev?KmCo"
    "RX`n-zYXV{Octm>sFwNj7-7KxpW6P-u&06I|}9ChC3W&*C-jOFiBVsFQ#^SY-FX^Xep5}D-`zUXX}fHPjs>HMHt`wvul?aeM"
    "gn%3UMZE>iW483^l7xapAu+YwJ-`9$O<0_li%J(RZl8J*<1)?$&7}yL)QLm47#;T9UP`x+|fhH*;S#jVh*{+}{;OV&TeZGaW"
    ">Jws+Z(*Ch7x*s%qau4m+5Fe%a^TLb_QTYA`d5KD!*<M;+6ZOwtJBIr>etn5%?J;%FGkp4~VD<3XMgnoRRENWaeD=#pvRD4W"
    "1clUND5JgHP3=KL=I*i=~hE)9?{Fo1G0oTy`#CQ|BI|U*qENf{`ojrGl$Sy$R-J5I<jkLgj)JG|Qp<M(Lf-(Q_`yr54;&G(J"
    "Uh@`7a$~1Ke$6p{1YnGy#TBT4G;P$YSm8KWp=S>-Q{iT1e)Fd_s|xQy1ZyWuWr&KV`PKNn!y1<W?}lb@mSRZ9gRb<RL<_Ave"
    "$46*^5>H$m*5uhxOW#n$+`c%d@`h){?AlJS9t^HdXMnKc~)|9w-@2l90pnkXxTTUDGXio9CrFBHM+lbIUj@!|JJ#B|I9#S?!"
    "bA=S{O4goy&~6hdat)+sjSg*hK+h$!nm+w1JN;8n%E09scM!^`D}DcBIObpKppQ*)|@YTEHJ2W5Ju}>j3Qy42VoR?eiu)J*H"
    "zKJN>?t%!_iYx1ohW(>Q8<CGDzPYBAe<QGr+{!qMFdtuX)R1-+^5Q#y|jeDmKGy)bKwBAB|#(}t?mn+VXGu;*#N%cmb~NChV"
    "L8$dZx>E(+-)?aYcbS7_p2Ta-{c``E=zI4(uCurY~59Po5cQ77y|2Bi8O>oPVPMp1wN+i0HG;>K-B_h9>RyzIDz|a3Uxa*V&"
    "@D3Akqk4Ft#K?WT%W+b^W1G9MF^s6q^Cobr`LnbRgeAOH0gj{sylraJNknRm7E@d;#f?YZVQKtPzq~I8yS+#q(;$s6gK+qXx"
    "#ya(;gAiUjd*)iYH33{09{-Zmf}yAM#NIsqB}qx%=8mx52n!`h&p?Y`i>wd7d)gQbFyuW@3*+QOoc*6K0~L8Zz>i7B*`0XYB"
    "#d18ei)-6Arcxqhostf_M||huuTQ^4q9)mj(AK(mDjC*Olafp{bD}BV&eQI8e&q_U#Ese^2Q7jc|8J(x<vRCqmYkXC0e49Ez"
    "qh;wNa43EbWx6=b^7`}W0h;}*yKTfX5I&;OzVhT;uWU0>TryZpPP3q(3*F>#iwOi`5S2p7@&{hd9XvCg64LmfnU@XM9VN?%>"
    "<kgRsj4vI6GlJG_PJ2ELAeFQ(`3Wda?Y05lu^>1#ysmJFoQ>V^W1jXFjl1t<#w(7J!KW^rcANG5a{+6XBG_z^^I+!W9;x{#i"
    "HCI@!7{n!hL%0@?D{VPeJE-NT!t5#*u-8GkkMdf#D1gzYVBSQBeVv=DF@6Std_~>>_%UB1U7{aP;po)ztDk@YVBfC^Jo8r!Z"
    "*Lk4$&CTq<W$3rW?@u$W%*IhylQ;1HaZSC2xcfJWTBoKF^D%KbL-!8VyYM;R^|$&^_)A5^&f}|Iiz<!waY@YmXN#ol)2JJ)a"
    "y=AX(WQ9HFJsiG`|b~iz&E$cuHQ%+Aq=pwIEfS|BWw^>Pxeb42(Aan!xYqj^Q{PU~4|;Ff14$BfXE{J8)eH1haSTO+06D4<9"
    "mw%=*WL1C{OO***C)C7GQgb^@-|dwlj7KdF|uV2Z@?d7%0KtoU?_1V6ZB@RkL&86OjYP(&!<y2#_1iqUaZiJd<7(PLp>LYi("
    "%eMg1uak_90C)zK#tn+r|Dfg~cg;@Z`dXT?mPrkd~->|{w+2JgM{X1X1$@-uFhzYACg}5LNZ$~KtO&9hrtE1xTTyLrx*zm6?"
    "9?s9#t6!;QoBF^gAA<0clYxvf04d2t*VY87?i-M#ndyKyr(b+}QWB-m3s3AAr~ohidk3Hj_=cX((%k>o!Cw!;QdPxEXrKInG"
    "?BfROs@{JZW>Q9w)U>FQ()^uF7t8f`(nSdx|-$)v-<E}MgR^PA@P|aqQW^ii83pNIW+K)TyY4sGnbgx4nu?DTezm}`AubpmV"
    "yo<#un9PVZo>-vqq`Pa`<vty+HDfyI>rU>fSTfh{LR7bbl$<t`B7tMfnZ4mb58gIA&DLjvF%ni#c%H>ON=3B+hcX-}^lTY2c"
    "#w2AdlT$40o-{y@aI0#T-j%UI7wJ$K__iy*7$#-|zk;iu8ZEa}veBjJRJFMtD5Fu%#&;WV>;3sT9<^u9(|N@OVZ)6Y8=)JWR"
    "k*Z<bCkuWS;yjT0X-%En=KrP)4wvSW~=O%7>PZtGLZO5Z|3J4ON_gTGUwKX`art{CL+Wd||AzvazC2EOA$Lo|9#R?renwHKi"
    "=^Y{Up9zG;L{fS33_P41iqDS6+rz12@>&HyVuzX_l+3=_Ul>Qy7{kkSCBdSit;>|+3{^s-Z}dlkaD-eol12?h1amhDf09$)-"
    "&v-cePv2k^3ADg*3!!gflJtEpC>{aq`8;teI{nb&z-6PiBdCgFU4ax_O?m{esZ_}h^ubAqmme2b30*R1_(+}KabeMQDzv{M+"
    "=|WP8+TCcdj|5Xv)SxW!S!}z~cKc+TsPj=ycuFUKq|@C?qW7=EO@NM3R9Y{g0~@vc(I8_9Y9jZba8QH|edfaTfhg$cn~%Z!8"
    "9@LfW$TlAJ#Kn&)=g^IJB`<Q$p*Y(5WQ>h}-i<S_TC^)CK2$84$H9onB{Rhe#-^d8r`X8zmv74v=U=(MBvCrKjR#69cUhiZ|"
    "3f{u6XvM~LYbNM`u#P`JIKE6k-lN(3^W5%+w$y=wsb39&p=SB%89ATU=awm_Nw?BMG1Ru+5fNT!|(~N!tc+f9+Qu#odf}!P#"
    "&8s_K?Ra*hI1G5-8djfSwG}By&tPTGP3anvn<WAd9P~S2*8=I0A*cPzOATya)xtUTCfl{dD!XXIv4FoFrruYleBd7r>;DTnY"
    "9++59Yl*;iXzZ^>64+?{~h@Zb=rQvJgX7nzwK>{cK!HbB|_4u5UQ^QzU#KBEUkZ)pgUPVcNAJ}tbI;(^X<O#f$Ss<qbg{-S0"
    "-nnr;xItO%aLQZBcShUM^lkJsg86!><0OsLD^?gH(V$g!mxm0LbE+gK1&@w{}H>N5+VbTmpe;1}uQOC?0~d-rr!oHHw(s=W_"
    "y7+BEp8$!{^LH`rLacRy678fMDbinw`_*#?9pcuNTti^eYcZxLqrP3(OF?eBnc+NdikxDGL^BGf(!ZvblhTBD~FPJ1<BH<#P"
    "ccMyv->3~B&CFJoVo)zSf@_7t~Dc>M?)<!3vZiOLoN>tNcKhpC*S|I$}oYDrPjK`*ZdtCd|*cx?^r3t%t>q~f@LYhLqPj-?1"
    "LMDkzW1TV43SX?2v9b%y&CzAa)!&mU|3}nShBf^_>oI!3s0m1ibSo{5G?LQNDIncB8tDef5lTr&Hv^QElI{W0-3?d%-uv87+"
    "n4>GJ!j{<?|X8J&_s-PBH(0+F;<6qoEB^yC>u)K&lGnoDY1Lzht(xN;h81Lt*k?`;Ai?Rc37OiQW+U@GF<^*p;HVE;!2578q"
    "=K(<B{7^tT$dH<=1$WmO8CRpO%X$JHkI2ms~4<sI3-yj~3{Y4VWOJ+yV$GuGF(Hb$C)XXcJ!v|J9amYrdNS?>#LC#mZ+_6nu"
    "|k#?<aEULTsi@Q6r)IN9Svn3al0F|b`%u9_iXqyveB3KoZQv!h7D2H30%f$LIhz*brvaxMg-Ls2V0Ekw3W^r3f1KmAmY4>lU"
    "ubt76JFYz~Q=BYXU!&Q9sY(r!&BS_=&Y-hmj9vbDjPu1F*&XDuj+mI|aV2b5W+qtc&hSp<tkyWpylzF2?ZMMl7d{}i4Xy#_5"
    "rd&&dIr<GvSY1zg4T<tAt(AxQLqF(pqc094jLU{y`{)m%U1tMHda~cgc2}ofFwqjZ0-t6Qgj&a+2`$SKM3s~Lj6za;m)3l|p"
    "5^%pJh<a*i0GPOS`u`LMctCg<9Z%eU7uSpy6pJn<gtaAa}`(2lgdmtk~@>`;GAofoFNFnFa(RtB8XLu{dKQ!ECzbeMLEJ8Jz"
    "i&}_;i1)#UQesg(&U79L2@<mIx{24dK+DK4NUJU->@5g+4O*sQHg+iGTlxuOieA&L>PokDIzw+e4gV9nLt1iH@^#Xko7K10+"
    "amO;-~)8#sL(Qwi1>YV4pOe&~={epj=dU|%Xv9W#zLd^|FCh|26}CFq<{dk%LnY>g<%qq$oj;;c%xN*|qb5DI_y9%x9yQ`5R"
    "CEb4y;uv)$aw0#`;IEKUY#wj??DB&wtcxzZc1(wQ<_xV=N6piZ2uFb==D`=t|G4X&SeS@)nQUv9yLCs?4BKW!GaqD?_hq|Df"
    "-pfGV>~$<+_}MYu3C<6w9c&87vf(>wap;J_N9W;h7-IsVNC$oeN@hyv$EAWAHG+G1uQ2rW-OrPHP|IT$*9;l>FR^k`fhDd6S"
    "o!fuW}mc~lp=np9xZnf4@O;GpYa?tVH-gC@ox$L0`J2=;Pt7N2O||?!gwf&1Sh&>`?7jpTMfgecRPs$M|bnfx5H*7U&nD_Ad"
    "H)CN^*V=3C-ZBYVgaCU$ze6f9O8_lK>hWa(12KchdTBx9_p^Gkcxhms_lt*t?z^<*vF`xg&l!J~b$yu`Xtwb?|EJ4<_}H3DX"
    "g0xQuaEysUtsrVjWRzBQPX^DG?gLjsK)M5ddB%CJ2$MfP$uX(N>?g!|c5pFYn@(_#QN9NlVo^`13tY>N?N9J@SUTtARdC$J`"
    "~Zz58OeGr~Q2tcpUTv!c2EYG=!FbBjE08A#tB{!w<Xt98<wVkotS62@rzTaCzbRm0p@zycympmhoe?jy#=MzFzObGYs?a{i7"
    "LYcojtn#?FB}^ir_xV=*>BZn^v}s5W&9+Bg|50m@?L!Oy*d)#g)LQF$zjK5lpJ_F7YeMKvJChsgiF$x>?PAxb(=<m5UtmY0A"
    "F+#cm*^Z%finA!y1Y-jYL`X7m+#A0F;QztB(ZcMp;9}=F2RMQB^zF~*UbYD{CTzA!o?Vs0_lY*ITp_u8~XHfoGr|yFK@Or8o"
    "9+{lv7uD5XAI(=h>fs&!JbqQGh&Zi0H^8+scmET}B2x223Tbsz#%&{){oYH(zX5MOr;z5O@;l{k65tPYT*^hj49<x=gm>_uL"
    "6dlXT8Ajh|wF_pLJ21B1oduIUf#%gvB-Ds?dpDqma?|8<hi|Jr(8xIern?=yUeSfp+c99j(x$7ItL8i!)ZnBV2)0XCU9raHN"
    "Y-e%LCkNmhL)>HNG=D)hX-v{y3u86^P!t--s_#qg<Xv+6nvRBR~lt#Zs%oYV}o8~r!V^AZ~=S~Sx?128w<K6p{&sxRYKyCZ>"
    "f*{Ff8k>S@8a}X&$Wd`DU79I3gHpU21+-kOS_ffY6MWC=u+s>GKyI_6rO+syjsRR96fR6ph4!{TY0l;(CC(h&n0JEVG)v)ND"
    "#O-T50zYLI(fYEk0uds?rI=!KjQs%3tf=29ya<wbX`F7*!e|&KFwJ_+&c_b_?y~Gohr1C366_AbAhq(Tl8V|f?ase%{@4PK;"
    "MtsN9M1`OiDa0ykdw^+qUm*is^p1+bmO@8Gd=!bG|DuZby9%_A+VuqD2hB*76vOWU)<oH5KSSSE-Eg&NPUt3RQDWIG-!TbXN"
    "k`Oc)F7?&HTp%AE+j>fe4PAo4Pj?A3Vs{Okq*S~|fF*9d(ZR7{lvhD-cPJH=`ga03cq<5?075Ls^n94ikn#N|sY)U?9~ZN6_"
    "@I4b~0SvY?KGYBkSKudVLUi>`omtV*<g1dJ_5kaQR$q{7ek35@V->k>2g~DI`RnWfYq!rO`^RhRr1#r#SySiu#I~ml^iwd97"
    "BNe9}lDBA+5W-YbNna_@$d(?AJC$)5W=%M`g~9g>yA={-sS9?KJhrv~6(S+mt#Oab#Qa>@=T(@&AJuODx{jy4oTcVd?L>m*P"
    "K{UFM-=0jf5{hJTUG|&&6|XSoRrT@GXQkAy^(=Tqv`)}o*dI4G|_jOl?{x>G-=|UK7H%8VxVghV^&DH^&y5QHvR{`sNWTUpL"
    "pXtxEG1#lP&$^T52oj9qc_oxU9seJ!n}t;4|uE7%2Q}&ARZp;y%E$TK%?W$|xJ=or<sjoKn>99aPIkm!~2IQPv@wQiu6bPAS"
    "%I9r_Cyv!uHhzgZ2Le`@;ZvB?EX@o2(}E}Lz{SfNv+u47#>uLINK=wkMj=jq<_XwMjdA?~j@t6dUFeN+Z%0tn7h`xNz++@xf"
    "~l<5qG&RhZ>;eIuWUhnJp8H>7n&oxBudmv9dX^j7ZIAf%vhZ)7w5aCAly7_Q)@f}tWwXpWnr0QQoMRtyvNnHNo=nc3%dA0Yx"
    "J?v5?J9K_eyoSkGP3xX@mdzPR?ZXxnl<S8SAi|)!=*xKjjU0&!Z8&vOP~}xK<Vruvy&#ZhWUSbJxL-Xcxi!H3fq)}d;FHl?6"
    "*IwYQ||4WQ7wvTc>+XufkG+bVgb7%PG$8yU62ZUwLgsmT=Q9w-eB9;oKsK+MUjoOguC<kG+VL;mu@WVs8L8X)K<gldrfl$N-"
    "6=MOG6-UCEVb1MB#qdC}c^{hiF<QM(VP~x)Ipi2XpStz(VT#S`8hyK&WI(4<}CMhUc&SfwT@HBx_Vg;|P$F@r?6+H?JBE-D("
    "VW(6cJl-?AnNl2G&vH9fyOzrRhtjGeommC*nf{>7eC>HlJF<hlA%L#&J?#ly*p-&qo{!|9w<Xnx+2bO9Cb9oj4po#D2*NFD9"
    "2pae`8B_4*zE&b?9NVzqq7w?M1W_qY5K+TgOi)&gvJK&667tVd%8Q$2^3gxsa;%=$wPI>38fq|q_(?koo>fVy9{h%zu>F8n)"
    "W;F64{4f>_W-49{yDZIr*s(zx)vK5mn9TM%KVgbmd7+~QSr{S+spS*N?=ppu9vTS5Z4dDlhFUy&&rNgQrjXaCJ~D`Cbv`!10"
    ";vpIqjwpV3pD>=H1O%hy*LBmGg6iCi=kT>099dPcne8>C6|4D>mj06#DoXS#Vn7IyR-uNXimb<XS`+DFUu1$p{$Q3NJ1tN9S"
    "^Io7Ickz^F6X&Bq5$Qp??13Fk-;a%xOrw$B`|o&Oy8YLR0B^@XC9$8K$ilf%$+ONJC5*yY<u*9Jjb|eb~8*3I(67Zt3?op1P"
    "F`b&<t!+_9h8EN<^4=+^@(O|~sXFI6X271sduaMiLv55^)#dru4xBI2X|Gal^~_tI;(YCcE;oa!qUlw|^UYWmo6E*z5wq!^g"
    "CK^^sry74r4uDoeg@1~ec2#8GNWwBbcM`WT{S5$ixppheDb7H=;V=r=hUwb%iJur^&)m}%I+pTwRovDdLMt_(<Lg=8xEA)Z%"
    "yioXLrxrU?J~_3zoS@WiT6t1o(VKCJhIKPRwvHjt29>Op(#LH}EVZd{dBPBm%|B+$3MGP=CEEgjEW#7izX}uO@JJ6JYiiwJG"
    "r7d8EF!tSt(l;J2^;A*`UIm1w@R)&bN)E0K{|itRrYCinD60cihV)RTX;8D(nNahNm&|_JZ*1EcuKsBoLaJCe(CW2p<niDv0"
    "<s}HRDKrP1C1zz3V7Q3^hW_-%7DeAkuFuY)<oZ)i?NUC+*}8>xE`QnfRDjDd(YI?vGYEx15b(W(3bYif)dSZD?+GOGE>QK_?"
    "?F)k@DE4_``eGkV`h`<gTv;#NH6gEPuZ715<uD!2cEuo7$7P)UXXV5<A~LLDDhSZw*)k2n^z7gTXhA2V;L8;jOi<pJoGau8L"
    "Q>L>yr29GHL3_1Sm^NL)N;7nV^8M#-{16Lphm@gTa-BYP+t?oOa=jDR#drC^?vWGS>t$tN`E{(<GfPM1Z<?j86eDT2NkXWU*"
    "iwpYvttLv0QhUG+0|ng_3Ktp!XjJi~xsbR-fgFRl7}sBA5;bB~^nF!C%cSa8H_}rI8};VDxaAbUMED+zvspcRc=X>@{Pyt>Q"
    "AAvcINRb{a7Tac28=(_g1Drl*q3IXW}%FJ{WhVizPZ%qwp8{bwd;K$P<0r8RAXx+C->(z`jF8Jq-L(^2vD3Bgr-h#ZV1p3aL"
    "@Z*&<ohn>_c3W4X$sMUAC^ZTiHH*<_A4Q)8(+g4ypru)#ElKBb8oGn8}b024}D%8)>N*naOC`_WH8Hg@2x#HoWd6(NQq~AeD"
    "`3SYba$SLckWoEu|Q$(3<!Kuxo>_-Z$5fADNg$=J81iX^z}vn82Wn=h)iOpjyY#*GhV7p;U+inl@`#H(aaMTjnC-?T(T-H-|"
    "#Tj*G%b}ye@%so+On&%QqJ;61xb13|BGhR1}qC8#}Nr-et9h@ub8=*glHG%V!LdI1Y<H=%_|E0aHAx?nOyzlW;i)<sq#vgsi"
    "Ixc%M(=o6mzu?b8qy`-0A!uRqJ$@3O0M+X(<-Z&4^-#}#By~wQH&C7FdXyp}sd!J&LZ!`t)SRP{baoy>jv}E^YS0?72TV!_y"
    "VXq(do$+k<IJB7fKqeLfp6yx43$ASUub*NPF(~}hf%sDkv<3Ktqt+nYH}%Q*%oed9i3VX2Ap%pir$f;&E0=eS8K0Eo`^+O%C"
    "M%X1laK60=rWJc5-MAu?SFSb}r%}UozoZ7M<5D%`x$#jHr*Bq}-ydp3fa}gg;?6E888yA>i&n31jA~kvuuJiCY$Kofz#Z8#%"
    "#2Bg*WyHwxLX>qwCjcD#5D<`~;QU_tVi<(|VGYtO1J3FT`7Wy#2{a`_!hk--#9cJP|rh!=!UVG8~irkJC4_hIPDlDDGd^$q-"
    "0XM?$G4a=Uv^KO~uo!QSKT;jf-M>Nf8#Vk!}1%3&+IfxNNJ--ki^c37Q7>U(pZ=0O%XNJj7KGKG>tMl~JQ>)5(e*xW|yAu-o"
    "uT3A9-CiF5Twv3mRwIC^)$2u_&ow}UvH?ehl}C;~WFGul$DLO%%I12f=%{hRy@RB@Abe6fvny&{8;xQ0wP5s2xYtLm*FmnVI"
    "?_3bG=;=4$V+`{ZM5d+-TY<?{%083h1xjNh?KxLxZA>1)8gI8-3lv1<5tHj>rn!P4R~%Xql+AKU@mF!azmDQ9uMKqTZTxlyI"
    "y9{?e19q%er?1@zutdyGrlWaau}>ycZ%W@Oe@t3|Nz+zq5#s=${oYc04m<#5nqSM=t7rhBvQpEH_3ZY#<f8Z9{}2Awb$Et@D"
    ">p=wIn-9`$VZ7_zo{ouK%;uM2(sCNZ%~r^F=3hWFdA{zSO@&=;vds-2!wdSYPt=i(pq$~{eS&3RWRu5GvH#(JoPAI?s(Ki8<"
    "L0i+%lywJ#g_7#v&lvkDW+H+PSYQk}=4xC>w{3vDbB`Hk291_I2!bE;=&36>w^XQkQ#NI;~u9Z=+E<$BiMsXr6TikupsD%lg"
    "qpZ$KUw$0($jiBYs1Q~}Ir=Q75|rL*SaRR$n|&5pyc^17Ja|m(O%MYh3C?km>&Bby<FXV!3h=$d5>_TO%so92V5LuvM$Ty!+"
    "w$gC6KQwafcW3c?Fu~a;d)I`3yPv4c&tVB%?Qd-X~vwma5z=BPDJ?WyBQ>lK-_@hhc!oJ*mvl>(h4zXLjGuikY>FCE1r6(;3"
    "3r&VqB`#gE>;Zm3}o8KY7xpIaAO-X@?h$qQtUJ+}c}zy2Zw6=5K}G;dYIaHAcg*O2U_S;e*>fr~jwlz#TY&)3T1^^?}(6jAq"
    "ip-ui{f_*&zP9Q7HgPAL!#t(+@lZOS<6y8ti<ka<rT)EMYaZn}4e`u=m)4@Qr}mEoS3q!Q67w9-n_dVsRTcm52YfZl<f@A*5"
    "4U0y|~WJxAj){bYfQ*XmjS;X;F1MUnrWxQPDGIbFT;u^>K6^3+f_3te1)de-2@?jB@u5z%K+p9G{>Dj(uHYANR4LMa_X;e`m"
    "TdVz6WqnUY)}3iJveNYjWp#meX-T|*X_Puo#TMT-Mj&#<AdpRQR<jF5O?S4aB9aBRX)9CLH}D2-nC}>%5xN1UYoB6r{%|A?q"
    "1Hh2!!h4yXqJeWAH=#cw?up8HGnC(LrS3k-|3w0?<1*yH8Ob}nO}216^$Av#p*PtQSWO;WitU*JolCegV=h$2xQz$tM{Q_B1"
    "@cnv}}CWL}6H}p}OmK=g|BHcO+MxYp<Gpk3j0ts;L5)J%9qf4e&c0qid<)5~q~8yLL`RM18Rk)-md|NjSz4MKx_>$vgh-j=+"
    "ab?8qWzX~Q4ax-T6?$Yso0v?<NBVPn{{q@!PFE2Itmlor450GM(!(}GS?jMtYA>3OdgQrumpQ2M$s7G)xu^22?yKi+M(q5r9"
    "ZQ=TaHdJbiy+&PwXbWVrb7Adb}yI483kNp|O&)&2ah~l#ikAIslUHGB!$6-xs;kjg|SoZRgmNH?>bVzlEk^B2AWK3uqIOgP4"
    "dj>ocL&P@WC(VgFVU%v<2+@Y4j|HZpbZ4O0wqgA9?Thah-~ZyEfSw%sQ}#|%6J5|7Qo6IW@_372AgZrFvem9!nYhCEo&E98X"
    "K7Xs>u`MSm=t<s2e|dn&M|5e%0&GKa-|ghN1vKj3)q+K-6r;rXxkpDnsM)@x0>F6(&}So3YFC#?*m{~B?O2xegBZ<vrEBt@%"
    "n1(z(C2N!bBEnci2f*T=P09^MO&Eju4{%(Hk)sikj8@5=0Tk6fF^NTTBi8a`CYoc3qY14nDWLz<vIs!>$n|a#X#u^AbOdo6N"
    "v6RQ3Rxb2-!JVuu>W`l~KOxGt57zbEA)(1ZL8S9|_v9-nBVJC1gdGR+PnS2hJt6p$t+)-!Z8NxYadDX=hCb*2qrlx7-Wo+uv"
    "Jmaj!y<W2~PwUcGl4!h}anqb?P-M;)zC-s>`ZX6=W<6ey|y&z86n?Ab)XFPRj>}Zn67AL<uqzA@%c!d46qMDTb@Y7HLGaU~n"
    "Si>Fp&D++18y>^l^sX1!b9}PhRv31j{C8oH_BJc&>zA0uO>^2>4;OQO9xG1J8&>~@o8A<04osnto;`X(rssG}5IwqJDPT<d%"
    "PJ@2Opab6wu7gCxmh3|x!sU48T3BDhSjfp^y;_<X#)ai01rn)mq$ILOmmB(VddR&uYwc^JWCHwzL)t3D44+)n>zxU1n&;Vky"
    "LlJ_73feON0RV>C#)@G-lkv+3tk%Qg842gY~aGosb5>Ti_Q%v4eukL1=9!G+*$2!lUR4o({{rr=$qqzQn&!j}D{hVzbZ}TN4"
    "2?kyIMX(fv@X9?`}Gh{Xeng#fLaz3>c?MLYu|WQD-7MQ;%|BTw|jh_NA;KduX_czn@gxMVZjpj=UZsLDo>JS17n=sWEh<I{1"
    "|{{}Wgq(G=c^Hl<<>n*y(yW^MNQ!kEd6t$h&d1Hr9XnP7s^1jqBW|cvgUhC}QrB_G3_wmKm(rvmASnhbYv_I~`bj4{^$%}<j"
    "O(w#K%QOnB4+#pzAX}ni(7fQ0HWu#5cpIJD0kvgRHnw!3X!vT?=sjD>cGM>b_3e=6a>NB05`z#^tH9w_?w&Q0?@q8W8$Q&9k"
    "1Z9*`+7P1S6o}h68X>{_Uh2mnJh;jfj2hYul>EhAE2EorbCdRKJpMr*4*=KE(djE@F+Kg9}lk&3h?tpTjrP)=TevIJ?OhCYy"
    "FMfw8`iC(g&rG^_jX;)()+Tg0^3Z*~Q<zIWfB_kX>DL4ET%9;NHPJmrVI2e4y{2>9epGoCW=zZaFCJ%JU0&Jswqms|-6mVPM"
    "REJ$JC6;t|W28DWg0vESrVuU}tb(j(2WH@1ooGQBa6%2~Jm5G<~dX&=;={H$GKXMj?Kg_H`RBc9@JY_IYx3pTJ!o#BSWByeN"
    "_mpPyPhS<DjTM1|xi*~xWLv7`A1A16(aJ4mu@n*VUz48j-&$`sL2#(MuSBMyG_iU_>Wz8h>bU1mDsEoeYD*ndQzE}0)Fw?Y2"
    "#ehx&BySzh)U8Jt;C2a~l4m+iw|=Yi{Hjl5v~s38ZsN8wM<B+7)1U|M+*>vCaSGhChGCK;WhI!Q@V$;I=4cd@*ZZ42pL915^"
    "k`4lu>sBPkQ@`161jK1VDWrg(q@w~7OgsYFSQ7)cT_bAnec)XcHof~4q@2Ntu6hgwg2@iZ;csq?faS>;~OErzjlfR%03KfJk"
    "2(myz5Nb<c~p7N{D!06XP*r1po3~9y<Z#DJC^8RQqfc8}eReg`QU}ZEq@JR=o{GN<#3NwIINoO@H_U1ZIb|ky|c<0s=8ur>3"
    ")Ex`hP2fwzWEqBUKxp;&hVO0=1P$i%!yo))ONOC51I0^kKE)h*U{o!w>kqOLN`Vml&Bq`C0Ni-VT*U+iHm20V$7kLn+bE_Ub"
    "Y@<5247vN6<?MnU_Wbn#6wo1XFE@*7f2-m9D$-@!e!=GV;J70@flt-?Bkm(^<3YF%4CdgW9<@XF^smT?UxOlQ-I(Vl@d=5SP"
    "bRV9~fiFGqEI>#~{zu#t+OF3-(}eXkxR{J7w3(cuWM4d`rfPxSxYRysr?v77s4yl^aE%qe3y>#)5u)j662&#YzB*e${&m?hQ"
    "zFA9bd)$s_?J2)|4|3N$)Hris-WAUC8gYr!MDYZs0L-X<A)|J0bbF_!WQIdl>|$ow*{s3{-x)dj!~Q?-WtZb+UbMF9sUH2$X"
    "jK5<Ay_++MUn&30*Fsk~uFhf}qk!ZV7ZCWFBN2;$i$hsICR5n=fm7iyR+%*L0K#7SjDAJ`aNljL^jCxZ0soVK2RoN<W~+S5Z"
    ")eHf6If=)eClQ}W8rqp0|0i*}DlD!CG*O2lBY?tlpsCfw|}6^3NlGT+$rQX4f(wz5s^n|&kGQCt};U<SE6uxovM^Qb2@iewW"
    "1B!+$F+AEqbgR5Trn-tOVne?zeiM4fss`+zl)Jyb4u7%E5uo*FH8r`_0(a7<of}>OwOR=M0dU#c%Ak6Iu9=+Dbw35ZgV>(}D"
    "3b}Uh-3JA^W4G;}2Wn3Zh1-9{7`mS7aM~8}jLJiSsE1YZDR=jyrGAY@KGDED@osv9_99$zyhM3`cH-bbz%0vqM$`d>kq8YJt"
    "FM|CWH2JPLt@HQIIlt=2JUVectP&km=9%r`9{H{c=iw9L2cjIS!4&FkZ`2S;XTP<8~ETCr>UhGmcj1mrJy%cJiJB=e!`lJ0`"
    "vMn+PTERcJON$F}Fn`6NFb<W!_&^x!O@#?el|~_4n;5*+QgYOqsssyn^1Ib+<BM^4*+(sXT4z1%DYlxAdM)l_W}^ZS}IJWL$"
    "uIp+|KB+E3oq8l`12xG59|_X;T-&fTcukYxq+?;s1(&jdkV154)~4*UyTnrhYALXnu$ids$He)_#yNsbTOw1JpEB1u1@<*r4"
    "(_L3u{#==fy`Xl(*!m4;>=TCX*V*tM4FFSrF3T`n&eX1g;{j0Rg#y7hyv0Qb%c72^Wv+Y{tZ-efTEgJJ`ZEef-bp!?KI;lCc"
    "OwFzE^2p?4>2DQEqg#^b@&OjpZFEDd$drEMxAw?^VReP#a+qi!7IJOYI(72asw>YG#Czpglr5fMFkNj1yOKe3^iT~riYznTQ"
    "1^#TKzM7HmoN--v!tuhI|SHvh`de1gVd36#@*2L$%S!*dhjJmv(oQmB!m8(%<i#dWb*ePC$?1;CUD$gsveOWAlF=P%`n+xPY"
    "e7w4|jp1_ky&xLBIgg$vh6?j9o^YXhJnID~2A&gCCe#l$0iUV$-{MTkbRc!9pKM17+Tn-+AfHT|WaSFxd9RkMLT#h;~?y978"
    "&sEmTJ~nKUm4bD##-VwAW{Ru7790Scta{m|<1{H4uz=loSYFe;QSX`0j<OnY`tM9(ULfrG&HZ?Di{#lLR3_TL62UM!a_W#ru"
    "`XQH?m=o|ZxnY}HRLyl;0!-xUY9W~xU&c^^nI*<XCWDY(br2k1oe)#psRG_PoLwR`7NtqT`25A~5h-=`v35aAs;p1mv1XWp%"
    "*-Twqq_Fy+=Ain}QeFu&oSVrGI6pM1O8W88>39Og-}wQO>P@j=q}$mYqseyBV(ksi5=JGL)^!t}l90`VQdl^;IAKmRsC0$X="
    "r<)CW(>Rxi4|g({9zK3&s0vjNLX4~rwmZj6F-r?ZEqi}amJWr>Ki}O%)IX0#4Wux%LRo}UXdDSOD)(@Z@b}#(L@T%Dk+@S`Y"
    "J^z*`B#ZXP&a^oXZxRKZXQVPI1&dxF7<Y>`)xC1f#~K=-4i-z6EdZIXXv&@Lt~qn;s9tOLlBg=Wo>Lm%RqF`CSEe1Ia^!Ix3"
    "h0W%~s(HaFqz)zO6-=~MBiN68_l^|c8v$l%n*_kc88CPMhwH!(qP6q*yuU}+*M2Zz7eA*J!6{<jQ3W`(#m&(nBmEb4#N3IQ}"
    "#A0E{G&!>G!9DI}_U27>8tv)NX95E`6^oc<cSzS=t@G;U4OPj{!c7zNT0XF+ZF{L3H9WtiId&qsAFX)kWxP#O`_{K}9b>6su"
    "6nWTM3s3@O-yq5HdMp$Ma1X|>qc*U{Wxo#R=P-aTY!FdaaF{vy5Gu+Koc2sG1Z1Hi%M<3UQD}{$<c<ulG*rHqSwbeQt(3nvu"
    "q6Q<Fd+&6>gcWfImsxV1g^hw(osB-gog&Hd1xx}K@Z#KW6L_8aS&1p@9ggGD^p7}Ecx7NxQX_?SV;<%Gi6a-XMb^^ZP8ap6I"
    "bjcr)U{Nm_){Nug*=AH<)}xtE{iBx46(_-`v~Gw^zq>gy7t?zdSTzSUqd^3aB`#Iq6vAAkfx17+CQulQYZPBkC((Tej@ND*?"
    "}}#=UzuEU#FtnH6MP$J8qCuIH@6`E4qoS3vv(8{-L4O@Cjw1LtCyM~lke=90zq3AKs}hEf@{M-#>nb-h@RtX3wp&MbI)VLIW"
    "Qy-uzZHs^?^29bX5IMulZZ$Z_^Q0Iqh00(YLZh^`V6ko2Wzo0ZGLFba*MgYT*+u5*<_1RzSaUaB^kTwu+91-IlxZHYdrlZpo"
    "0aOmaY50i8hnif3GlXt#iGzaDE-*gv)s#~j8tO0U@>NHKz{IUz6|(WsuGl+taf8{)k93#7iMCwU>9_l4RnthS_ba1;ftN&vt"
    "a|=(DKZ2oTMhc@ZbXm0j8to}Z%g*?R6PQfko?t=re%7LTO3-0lbkTdcj*RR)~0k-Vd9xHM~0x0K?N`buJg9)G`<*(>HhU$x%"
    "DKJo6@!QONv1Pt^Lh51+AQkB^At;wuEe<=fs+3LW1<9N=j1{a;;Lzn4wjH6V}Cf3|c4HR3hHcc~(}P%h>sQk5b)$57)$hz1H"
    "xbK;X`xr$X}m3Ki8%F7GZzORUor*3-B62&L+{VCa$Ut*WVx?n{J`gf4@>b6aP`vnIy==mp{!eHwMzZwE0kHNwP0^9k%#{Uzf"
    "YwYwLv-Vb=0_Yzs2y*iU)-%n-9uOfMc^pXH)?*h*nSxPdDLFV*M+Rom7b^M$cEED^x{~+2eaD-Ci$EWG#H--YWOx&yF8Ax@H"
    "mrY4QqSFI=AQb<34ycXYosSyTd>c>qLrC|MECiAIxP`Fkmzy;7(otdGK~uIpYm>@F*;>WOU2F+P)pv)IZy+9Bi+x!y1uU@rF"
    "NYeAHm*pj*EQehA|-8DOVWTvT-A=Qa2Q9dQHtiwz9^#mz3GRZcuaL=sVIC`qm5x=O6f5JuB(dAim2+lCu3&$%VZ!SS(6l{6*"
    "6@Jtbg<=0cy$mx-mS`HjcLoZqtWcz&FgZQxuRJ!Y5pK_74|ik_Q%ia&sNOfCPtV57{_OEsKJuN8bOiwNj?rb<5MFVi_9iBX7"
    "O1W{HU}i#o4#5>7IZarCAZD0z!=Ind`bX;6Bitr_6Iko#iBFQXwsvOC`jg0jOVA@>R6aBK>Vj7&eBoa*P(>5cUmUa*a``Y*A"
    "s5}1O(cq|}2lKtOo^!J|^hPF6#MUi449h(&fH;>YcO|NHATcXecvsGM_8}yGCr4FfaBTnSTqvfy%vMbvbV3-B*Cz{NGfrEJ8"
    "?c1q*;*c3Fc=x)6Z<Bz^?&sjKZl!mgSr`!i{S(di`4urkAEQ}=h4=F;Xi;7ye>TS$MDjP6*4w#EqPJSF>NFtFxsa|q<;ga2+"
    "r+6m!zEW5UQ*o^8@g-xy;DQ*?gi73<n3o6>3pUQ<%9{LGt(Ff(#|nbZ&wn<HcET3*0|e2EVdKvx@)uJ^c<tVups&AAM<h7*$"
    "CA!)r`Jx2oAmVaI*5kPwSC!YM$-tALCX{q~0wO&*<`w(|Ingu_dNz@f8|MS+b+k%dFYKt-|a=t?qwsd?Z+GYP43esvDn9EiD"
    "elsqQHIvEnTs*v|ylvO?eN?KvulN=q0Kl`$1TXYPGEv|a^a^%uIw*j#?(_AX&Z-sqxLB}F1@3lPad@f^5R7!(i+6Eh}&CJL)"
    "uxdq$iKV*&afbw~5)vYOxNPIc~b~S-1-{Rtms7#(wilEw2ndV;Cp!v_J6N`u7avJ`4V?QRRQEX3D5E!UPkkeiCMjNBM{EFvR"
    "r9Uo+op<{U%y_9AN66Vx6agQsa5tajRV}$WjMbj#r!b<&-rA0wzt8>@&zsRF)lEkf*TCm=c>3Yn#jVbWM#YWB(Q-+1gyCq#l"
    "W!Ul{Hw5|!UUJPx|4*wmI18uyXmury|YtXO9Fo2X~rV1DI3~4q8M^jq@m2y+6Q|eRC-V#f^{=lR~S#zqCv}}^7gTe=ugJ)*y"
    "xSqvJqx)8hU4KN7PJ~$3JF>$RNM|%s`V|mraO!v&eh0OnBS1V4*1bCqxmNPEqwS_Z|@D81G7M>Fu{*q~AIEL%x_t+#HLfK({"
    "ZZ{Q2bg{4M%5pBZrZlOF}85d~(60n!Ci*(Bs{-1~UWNwFD6>MRIwNzBicmYj21C>)@ZS2!1eZhi6C9hEk^cbVXD2vhU?AuMC"
    "o_mz-=LmKR&=uae$hmwT>qa;-*NjPE<^i&0?WCL8;t^-;)u+}$u@6K&<HGr|_Jnt;Z1Q69w>L1EEoj++Nu9#BCAswEMaY+G%"
    "HC2X?zFHHc0j0V7r#8j&e{;Z*;w}^K3@F*1mucrY568CmjgLFo7mP@L&KIey&HaIdU*GRjU`yjiGrq32sesO%338QeG>HsRk"
    "2@@7YE?X2M&C>uL<Ed<=lG*bvrqjdf32`0aYJ0Z0%aR19*BVwf_b7<|DbZj#H>wMv;{u8?_x#6%}(*q!<LClyU?Ii)1cguk("
    "Ihvn|a=tw7+eP%lN|=TIO66yq>q1sUXArzfJDs-VnCL6|&~lg=0YkDQIbMZ!8Hj>*2vE7H7#aBP~)Q!OD`EgsP1bq+NB#%(X"
    "SZ@2GP<)DxiC1v2cR+oX?lnEa&ngDOd)+Lyu9tJinGH4E$>H{&}faS-<<xWzW_dNXq3s$Ycw1Duij`d>)eDhomM=mNt(XTbF"
    "m)_Srzoy<%Evmo&jd1hE=*5!iU^-q>#`R_7Qh&FcVO9!twdH5x3-Qmy!(FUdc+SCAnp_m_mHsjY(MFO63NkuOnc}t}fm;S={"
    "2hIczrwfV0d7w|f)zYBc3rlY~fNrQs!2w^4OThpIrYaRLwUO`IfBEP3Ex-ZtXm5@xSw2Q<ab*}eXqF@}Yh94(9<ROuv(FO^i"
    "wBThe-B^epsa8}WRGz}S$=((RksHQcj+xzwY++qTnNzB)aomZbYbq&Mo;l6AV*JG$36Mh)-vx@#VX2AEqVE7xAVkd!7UL35>"
    "y<R%_b!_s#8PM(R>Mr;#=d6>;5LH5=&N)1sJ{RUoR8LqvNSgo-XAex09HPnPg8btp$Uy-VT#X{9=E_b8lM5S}w4C$CW|{q*6"
    "qe2Hl^nofZFrb8Fr4Dlk;x7~|2p#LnNo{<Ab@-&vQLzPtqQ?u~N{u)tT;9llKt@>jr)=YUToY0{!RU0C_=1RtKEnvKypH(Uc"
    "g8{Dg9MW`6p(%8fmM`h3y>C#Py5iPm2OVj84rfPJ!MqiwqcSeOA67LL?WWU!W>tG>7<83K_oDASa4T4OJLS8Xq3>=P~emh-2"
    "SMlEtJI4TInp^YGwz@n3QxBJaSgu?jivHR;T1GGR#YM_Ve3dKg9T7$KfHA}rr0^<)(mE8MD%gNGfD{Y1b`sL`V1;_aiADHk>"
    "yO|Gb%+BWcgOcn;rg}<H!6WUCYFW54o4gP;{wx^q1$Kpi3KuhFnkjGk|MW{YMKvNapJZIXj}vEM0ToN$WBQCq4~0`0YUp{Ro"
    "|>=QtX#dX*B_&ivooXdM719_)i>jDbii}$j`ISeYsCbGNohP4!r`@s~!AC2v1NCxt~(~s(-1zc9u}YS7-+N^a=T?SM2tPSa)"
    "ci$=%j(>8E{Or^Ni_eY%(6{l-t(_K{z~cp)^^{#5t&#N|wH=wb)nKv`Kw-?g#jX>I=2il3X=#S1A--xGodIjxJoLVY}w4b=>"
    "n5F5%X|G8cw|6Yeo%EOlM6D#UzEbD193PyD9f!%7)FCPEX1=KAr$ztdWc>!*X$%t7Bs8#1R<K?^49Fn`~Sfu6G+((nJx;xoL"
    "QMKmM?`=1O1Gxoe%DwZS@k+<UWtn}sUr8-8FC?fl7J=y)tuLtHh2Z14l5vtrQf}*m+*;Org;1mYnAXwerH`A-xVolOK`|DIz"
    "i_UuQYvum+T@W$S)ElA!}ac^&g!Hj=YYwcw!BpmYlJm}je`79yheIAYNni;@EsZ=b;y%<vHeFRc<G%sHz;nXOt9r$<Lg0AM|"
    "*41!<-K2U=pK=L7-tnFRhgwN%|%i$hyv&WsYvhnZzJ6b5g>z1WDWgsZIfq0v!ZdFZLTfu94^bE(Q!e&S$ZsuThH+jxM-H@DF"
    "Eou3iwa{?I=Z(d5TH{dRR}k_q{Pw2+?NX<MZHT>$zPs}_i}uONcD6oCA29A0uV@^(X|3bnBRbVBgO#K4jbqQ=KV;uF|LL*<f"
    "Lj=UWapw1dC6vwZe`{Nz?Z+RfW$7mcu9)KWynSi4QSMpwU>Q6G=(;y*Uwz|u-%I^o>%q59PuGk-bgl^o)lW<{p4(I;<5Q~EB"
    "wIn7!^^z^8G4+dQYb`X><y5Bu)!n!$ing+s3A|YW`G2a#YX{bWDt(NDfOh3oi~Fm`L!3^f*BF&9v<Q?QGLSB(#Fj`@&h>%`6"
    "GoFJh4e7{&Yp$}l2~1-i(3cw!LH+?mKJdD({KioKegu<fPAOmU^W0p0prX^VA-a|R>Hvo`MHkZ(TpB)BBKw+6@BJPRH)b8Tq"
    "u^~9}EN=kig=b*-w_nrR<%rrA~E8v!w|z1F@N#A&D*A5yWy;W;%)MCzvdbxgO2OH|d5(y~HjS=ea^ce7M_oLT-K7;{~UUFNK"
    "3HIkIKx2J=p%QQ1nyX$C=tmEW4g571p5(e_@FH=rh)eqwW$clS?eNBh#c^E|+Lwo1V%@x>s89ZYQtz#L#ihb3wEJQRI*_v&u"
    "UkL{VD{`DA>cyDBO?h_Zd{zs<NzJ9cDuPo>$!m4b!`)<)EJ?nGl?Iy?S!Vy<b#>bEkXjW{kb#@*^YJk!~-N)abTRGkwT>nf`"
    "27H>CT<jMf@rNarBO^PAfSl3$D3S-qBC(f5UBHU3F>mfEN8ZE%bAI5&t>qQMW9OP2eu;Laj59iYD2!RU;RCMYH@@_$-fdKkV"
    "$sra{-yX0FwKB(C*4O!xjxO@IJ6r7b4RrOp1%HB)mo?KLAOFp#w}HFSBuq%DJ@1`gNM$w*cn<owcou0Thg0H>;2bQQZBdVD<"
    "szSk65m%m^W(RujDJmX&m$z#bpfRQ2G{eO+A{gJ>qrxOtqa0J1hq(Dr+kjXqeZ>H(TN+sTT(oM+Hv?5q|#P7zxIRIjSl%qNJ"
    "n)Cw!<dF7&p+u^E45u7A8ynEO-GKE}Re9upwxi#19H@&vRryU@l^5Rg1M_M0lF^Z^2y8vkP#s-^uYWv%{$4RKMVwRs=Dc%Gb"
    "w5|4hP{{}gqmF4J2%K}3{RuUH-n*St_pHl3{pIrx&Lj3OY8=kjDVX<z+0OAYQpO45kcVGP0#Dl)1T3*HOy{%1?tpp!j$_RqR"
    "Qyi7|RC&o9V@PnPwYjEed+O0|KxdvzNdk<n2-)nPjo{;(D-@2HXbHD^{LSa2EaJh){^9WC-Oq_e(h>wv3+Vud(3U{KfYjkXY"
    "u!d_2&kAg=#y3z_t1HglqB>Uz8U>nM+bkT@u;YovsmOu><rWgtwBiCe?}twXQbr_?_qyrN)5f+iqowZ&r`n^IR$v(SE^)nO_"
    "nfcS@&4?&_oJLZIMf!e7h8fcR?-oG#F3@@SM4>s6v2rCoM%yk8GUAB8rP9Op!A$_vb#z3mfWoxi5*Fl^!pr74D!k*0lyTa2j"
    ">1mVJ7$eVi%qap2%Gp7S+e$4}2e%r06EGqlonN-P}%Cg@%!ET*nHkAvfXjX<)VFwYK}ks`e#Okm~8M~-GeWMge|=L_o*kzet"
    "<MbN&*i@yoTp`*rEQq~jnG>EOTHj5vl(|laaF{W!XSHROLy<&|?4hoRUl;9klnV_+BuXj4^^iy*9Xq*Ijv~>~_C8j?jenJ_F"
    "|3w?#vI=bBuMppzK>I`!3x6~ZqBO@3HX!2OUMFwQbmT7#!qsdRnYHP)K!nLwFFPJOja_Pr=#~VOc2IsM4*8Bc+Bhm`vy{2&i"
    "}!~&L^e~jN*Y-tu}4dx<2v`w!NF!HmdgTP%>YsL6F`{OVMqHZ-r8YDRGxS@qhB;SdvUAyySmhI473@kcF>(JE{v_+#R{<R16"
    "F0mb5kkbJKQC|Y6f)JA5-D^nq#&4>v_-H+E8%!#Yox!3j<{uCVyCA4W{qY3ty_RAF8~1<~bWry}<<uGYFjK%<A1vAW<vAnpE"
    "-3>KFyHU??WEbBSx2w=PRoKh}Jq6xZG6XR;Hdh5G^KBxGq`ZpN$kibG%#rY}rF&S`sxnoyM-?2Rq0ureLlVrLi=hLD4@gPsu"
    "R<9|c)K}XqnrR+n?Nr!@{3>0Z5ZeEm^sl-nCvt4x>MUMLun9*R|0=ZW@n~es!%}Apo@vOKGJd%Wt&_dJDDgtC`)=nW$XD=iw"
    ">-5p83cXbNQNNf|x^B<=U(9x#Y~N3=d$<pQ)a=l8|DYB{)+@*AA%)XL!^q=C%uMsvkuFP=!+zEra!6@~&p~~$46+i%Y7%sHx"
    "`uV(3WsFEkva%!&&|`t750jh`TlJTTB3NMD}DQW9eAn7Lfd!sw=c<MtlPj6PA_-s#u-h1Q@)$p90)*wz$a~Vp^wfT)g*NLEz"
    "}{HUFxHi)lz3YE~v}ex4}ZROh*k)AryyPZS7&<wq>5J-$N-p?XJ|v#ONf%f8Oqo9xy&>B<ue)63U8?#Hx?J=9lE43DJNUSD;"
    "XO?!ju$0=9D9yyyO}=kG<GKsYvD2d?;GltM+0a(NW0T<gZC`4gDX;Jj2PTd!e}XrMr8qB{JGum@K03+Y$bj!ru$2W%V#MLYy"
    "n_a+zdkD{YF`Jf}4xu4}tAKp_2P^c9Ij_SIO2lcY`*~gX+@^GlV<3JL|R&C-+wnzH%@}56>SGWH`J{$0^bEDV$qJwlBrY;&<"
    "@|IMCTGLnku4pBONm3!es3tJ;^1vjo<)=K3w?X)48X|zJ=jkea^iO=(24oG0aY6tNQ@P-=>Br$XHZS?|yAR4NspNMWQ62oC&"
    "&bYmacY1`%1{SB9hJ4t6WRj~Hsgxvb!hH;cA?3pH`%DW$<kLn=t@t~m-A10hfpbftEg9`BZkJJhpl{1+SFNCfOik!Wa;a4t!"
    "orH*?6LK521B&g$%e<IHD=k@EWLkT5pbFLtN!7KcI!y?4gKP08C(ca(M9>3*|qX#<*Kuwh7$7T5-Lh1FHIu6Zdjpiho?jk3-"
    "TS8g3C33tx#M#wSAKs3QRbt=Hq9K_ZA$$s5zAe0W4V2Tmao>gyd@*jGK|dnm>1=(sFc6TsNJb0)wi(LaAosH|ViQOD2;FX;5"
    "fT+jY4%lUDzH5*=g|Hy;T2MlB5ti{x9B3@H$v8{2W#M?p2IgtaraV9eIr7F(!)laPO#Yyo;<q!$4ajDRb7>pA-vUxfePF_-S"
    "a2VH3|0Ei)38-{`!vz<*r~T_e5?4qG|3WRe>$G2!T3~}2dJ<7qy0Nn%bYOpAJY%iIYxZ8$jX<M-js(*zBo!zTuDTxK7qM`w@"
    "F&)`7?#L-TRuJx3Qynol7vlzy(HlCH%6zcX6K))7K!<*{>)ORoiI86c_++~BRUv!XBI;ueW3bB{&~9kqLH=?H1%%7wg?axRJ"
    "bXZoY4Nr9y!p$@>r*cY>SaBA?6oFIp~n`IFuzTvFdTg_yfP$amyM}dALlcjhS=5?40vj&Qb0It8pK)L-uRr>P|bIk@^69!RO"
    "|J@94LBm7mQW6(fJTel`HBe5T%!b|=SD9=txpD-45)agJ(&MAD9Z#bP8?flwY^&s<?2NvVHm{SUQsY+oAJ5Nt)|;lb%7197m"
    "vxvC2v*casC48K)gJ=u04v6Uu~3ErG|MW9<?!wPA*8Q*GNO90ro@e8|9#2drvNTN(z{jNc&9d|(HEx`c?|8kl8F*j4{Zo$$m"
    "P6%c0$k594h>=9RRjWh4x7t`wKLqrHl>)W&!KE`JX1f&cetthk4^p)Od+^OBIZ`;iOr#CRHFZ6~7TJX{_ByUT`2D)@Zec$N7"
    "rYXaH@Kw~n73KGn|UF*i<jW|1yfKBmB8d(n2`k1j;ku0tMywH;-0NelcFlQ<Q|)baGz5bo&7!PFO?cr*yy*Vq`?Ttv^{amfB"
    "en)PyGpdD7g8@;e$#Mc;Yl)%>i{q^T0t{*2bp#*svM_e$iMg4MKreJV6OESRYI4Hw51$IJvz>G%j^|f-)e{m}4sHSroZHX2<"
    "01?AenR=Dv%RCeOgK<yT!Bh*F)LPOt-hUIhia)}t1RXE(4|SH8O`5rn!uD}&z8yDKIO0nK}KwC)s%18*Ak?(133p_0fVW~1D"
    "ovNlRluQR;Y3TA^XQdE0<gHA-PUMmEo6Wk_)jZ`KPKQ^;enPCE+oPFPEv31s9m5`eO6L&uf+_cp1wc`@GSuYU+GYyk=Vt%d8"
    "*h%l68XGGz|Mf$=u*!|os8Wz_NECa$?DWwUuz89>&Fx{YcWp^f9sPaDwN<h^w-eOf1ezSz^`R`_S0$Y#%mQ_DXbLz2r!bcMP"
    "uYd9cHL0evfWz=S<JB-x7kE<vw!w`EJ*~oU~OICy+M*BD0YGT84q|j`?XSm7_dVLlf9>qUPn6zpb=sO=Y0#_F#BCZbZtpULe"
    "VoKcAXA1{N@!mDMfjg6pPwcf6Az`dRC&rbc5OK6{ZDoITzIgr&cpNp*#!UVm%^%{B^=&IW<-FTP2<awyWq7Erjq$*;;XWR{E"
    "6sfW`i~wIM0`{Mm<hP`v{AS5QiAK0Ze)Gvw|$V;gG{tD>)t7k`+Q;>(S#5g;rI-qGDJeTgXhD>PX`ZXmM3)8(1=gJQ|a%^Y>"
    "l+V<Gla`r5KQVDW8H*g^4%12NE@{+81e^H<Fn9z^fWx2YX<ojKBr~};iRt){2(EsomNHIWun*&Y(<SB&ljy%p=Vi^=TdVF|("
    "IXyM=HGu%x4Y*Y$Nt@bj5{*U7(TR#AQ~?Nz55AG13mQi&%jV!4M=4{C(wUq4q0rEsf!4+{bC?isq<PF~^AY<A$UOW1+rE?#F"
    "fRZi)Q~{=#dI*m&ZHWh*`*)d*<d{v7i$!>B8FaWZlNFn8#?=1HS1v5ES$`tBUry|5Gt~V=CT~;=K0L~5Lv+Y>`0X3?y5+<5<"
    "Sz>uBcd!F)-^H%Ljj(>&?;m=HCquK41liw4k%<gY!#!wzh*h?k%5i%DUcgB)+z8&V$9gjx^+zNxIPs<q98%wtK!Fm2B}0{Wo"
    "+4Gs7<n+c@}Ar@vR%g~|>NzF!<EE!P$~Q4(`Q@x;7BeHu;*|3_F-!Yr!psBb38QZG>RCurpYTNc3{pwa2@a2am5RUU=~-LpE"
    "W1$*Fp?`tF|%S<6k|J^XdL3ssY|2y}aiDwBGBrhd&t&4P_%|R-(&?y%n^n6$0Gt_U-4fV>;G@#Da_-(P|pDC@2pg%mSrO2Zl"
    "sTqI|kbDPh`{7@v9NTo7q|7ld$dR^qWeezZMx2H9^u(*1g6qzo*}2QlRod+q`HAVQjG(jLhqrY8Xa7*aGhNT8cLD;rA4~aM="
    "ki&OY>J`fGtC^mkz&Pa0luGuPBa2L1qoLJ9*<-N)*u<#96d1nd0>yOav}++onmr}wWeLD%E|;@bXc*70uM|8l?OQ|izl^+cV"
    "2i*#V=+{ibafm;Neaxx)STS%c7b_6A}i$E&%!0j*091acr_!M7bF(DbGD&`708%(H_HR`=49_4@~>tt&FaORr#8UWJnd74u`"
    "eE?PQSN&RaE40y*Et`mp|2n|SL)_rk%|>m<??tx5J2`=Xk4duh2TKOY?C({rB*x{^@Gnz`151mxo2U_H{SMeK{Ot=+~|Wfeh"
    "QP<=+^&YY;~--pPmbp=+|crG7Lr9H)6tl+=6i<MP}dAiZn(2L_BKTPdmSH!A_lc8!rv!BV0f|n$&6$;}Lk@TGS;ne6Y0I=5G"
    "rC;0)1|*&sEL3}U3$hw(KqVlgcKGSp+8o(Sw#zddXbKlZ6vyVv>394EYe({{dLsCfa;7GiwC3<*-d@>Q`(Qqi`d0z;z*8(97"
    "okhu)dllWwzfXvM3{F(+|8e)bWqP~k~deeJpT+7U;x?n?becfE@xiGEs*ocX{tPZ>5#O4;t6GiBwp<qB|L4=MXoyn`FMeZQm"
    "^RR7u4DGcA40*;@wfe)ZSwb0HOVTs%!M{GJ_B_g~BD(-M5BeG(2ov(${ouw0HR5bB_M$RtW(#9VVhV#XKh$f3T%FHb-QFKxj"
    "1ERjtGhD8vLq3KK~`5(t(w0LG#me3La1$<n@)>&TpY*p{v34B&&x6!Xv$(hdTw=Hy(XoBShvGBbHjN5H863_$shzc6|MMS~4"
    "zI0C++_av8T#0kCJ9%$5&umS)B2CNQE9w7RuQ^s!xTxI@Hq__yZF&oqahIwQD{c@klBS__9B&JaskFU7vzpW*N6uh{5x;BDQ"
    "3H<kKhM2*<)r#{^ij15DMRUFW<}%Vm))f!L!!)t9Ij2@4fOU8Nk@=;=(q7~(uVgNmDAHW=6jO5OtM)w%YW_g3kQn3_5>Wk`8"
    "qeCMKyb{9)?e8)PtWfn{3ph!$qA>BQdr?Oh_Syitdb+onkPZsHsH%rB~RUT8U;WlX`>($Spi~AfPI#et8I%h(GMU16fVzeP}"
    "a}FeXXL(9+RP4)2UwnEW+}C7K!+QtRMUH($Ur_wguo@gDJfRsE3`13eN(aJq^Q7-|aJYc1W0rYid8XE&oqDUm6Z&*#141P+3"
    "#iw-ibu`#xk#iIjcMlCm$2ZJ1Fi$yUjhoyu-P_GL(h>=I)qJA=Vs470rV^gRDB@9}<rzx?MI2M4Zu?(4kH^S4~rIfLfNWu7<"
    "=RW7i0_3MIqg+xnV<f_~Z+@}?-rhbyd3%}d{bFZS^O)#4K_AJ-;A5J@@F}}9hJTw3Fd>fq@^KAuCkEIRh?Tc_^>9OM!%?BIM"
    "wG*v;V}|=mS{v%;s<`<Dew2SXr9N%brFdTPtaQ)+b!DAnR`po8@6*%Owzg~9B1)ebK}9kl9w+elLx!HK+!Dr2I~EX{5Vv>Ng"
    "l{rT+5GM83@w8KAbuVDm4p6Yo_YO;6xb6)T0Cs4Rhnq`St7O{b-WXxQ@5spT`?<6h}4J%{XUa>6SPgclf6Y}sF^!-CX`#)S7"
    "Fx)a;nt&?LAhq+qUCB6p{O%)mJ^EWfA`8lvWQ>^6437miA8|LkB<F$W0=XuK?r8CTrUbkf2SdJRir~zFSZhy09BpSeVaz88&"
    "CQO9JG}4k%+Rpi2ASrT*KBO8+<Q*6B#yr(WZ<ImRXhp7Q6s-<h%x9>V_6YSF?STLf}nYGto7m0&LnbcB99P5=Acle(SV4ued"
    "qaS=<<#(DOC*SIf=9s3u+IBy!ImX3?++rDKBe^Fw`s*&+7=dVS6nV(Iqqm{=vE`aoI(0rNCiMgf4_k{D(!!x1$`A?K~Lp<r~"
    "EK}<bkasC5NfYpY0o?qb0N#v^+_=vLiZl@f>w**B8Qk2{>fr5YCpn$dvQ&(eKk>c2?3h|YxxqAK$*bZ0?MvjK;NVaijU}acM"
    "C(6OWg~!2|L6ABd8$_F1cQQPat_%Qcy~e>79-n2>6Z?>1~1cSl@Lb^E{=sQo$1bf7aA=uKmO;GW{%^}#es{BL*vgmr@;U2>("
    "akw3F-%rUp!M<^Z<EkzJL)w%)(qX<i{APWBs=<2tMhtw)mr|icWZ_n`NGt!=jowXK>(K{XA<k{eSZ8<$rb=gqvwEmpr4duWo"
    "$HSlZkD{V@v&QA~84Wxaodus(mko%_>?(*4)j2BIJl)q#cCo=X<x?)J}Nqe}mZ>c_CwKmGV(=ghZ_JjJK{!c056i#+?ZQGcG"
    "e>KEi%Q)oU0`?;RJT|qOOw<vX-*X}&owbg0v%DZN15hcBK>R(KD%Kw}5&6nO;&E5Lz2Zf$>yxu43tvCKsPmqT`UhE^|CC+ak"
    ";R(=&4DAB9&l9F8(@5!ysm04e8LU>x^Zzn5f&af5YWY%1>&rD=E*i~@bd>Y&=Yj$&W8|#wgE+F;fw+65aKgKgSa09wL41xku"
    "FsQ?ui26h91hR^tC_!QBLBhYkXL@fZt%o|=>^=nwbul#-uWK}9A@VWa^3wfNCQEJoh`8yRonV%<wOWp`AFK~FqZxQ8b7|Den"
    "%tbh^8*ZveL$C9}-!CUki=C<+<OY$Hl5qZY4RNWWe@q94kUoPv@jFNjXIwe*4mYhj-qdH*90Gz4Lcq@66jg#dDl(3eKOO>vP"
    "ciZHXN}dNWnpTVGw9aPVN?<nez-GKv1r$nlq!e|nIAHK-qu&B({+C#o|}f0ayU&)LSxBI=Dg3J<!-*J?&`{Lq8^mqSng3y=t"
    "5&&Z8iE(WKLmZP9n{-?(BhCCIAJmsynC<A-fR@5|}f%cQ9W&bU^sljajzn8sm<rV6yv`lq%l*wcFck!$)n$knwir?OG9gPek"
    "+gQ&Jk`N(<4u^A+|Ayg3kFvqi|9<3fyYT8vE>Tq-rXUxOI^rIPi+2%~+?kk(9v`Dgv1?y|{|CM!{=MZ1(C&{e{vBm7KN9eRy"
    "08$IE^qsIFCI?vGE)AKkvIMe%GcioY5qeNnbSwVEMAtbN;^M(e6f^7fAuUwPs@L<$MxUY(#l=n@s;aUVtjDG^$#uo_xb<r`O"
    "=c>po$W?*f&Q|gLlDq+8N(0a&HA?2-S=cHCFkX@e*$rJmHKaqw0yDlast39~_M$V6VXBMR3aEp}<izWk=|^)Dn?D>hUNfgd4"
    "@}<>Lce4*j0PhzAQuUSifEXD0A@YqL9rhVsDo4dBlt61qk)Xd?K;of7BB<$b_=qWZx>$bBHQT^dffOC;n_RD7oE{UscF**d3"
    "ukz17QIZ{)2-}-bx`K;1+NYf006dJaT-Yp}k)u*(cjY3ikkr-<Vxtg3J-qPB>s=&)aZk{cx8K0c|(bvbkvbsu8fgifVgUZJG"
    "l$O~jJ8UE<wgvx#GSj|@D_e9#&Z);APaewWOB_!kMFw#QlG++C0Ro2akg)UEyaPkeiq@6iVZ>78u_SRlhrIsYDlk>r@sP46L"
    "=vU?)2E;IJaZ$A5l!SHOa<pYOio_@<z>SiY05HE{TzZ&k4vQNf)6b#?6i?{@Rh*zqu(mGS7|gJTfct)o};XyV!@GuflGDaxO"
    "WEBut&YA(u<Qdp32a}>vM<^|F40E)@aAD0sLQUG`!J0;+#p-EI(1zp7NAs1Py$3osU(A5xHYyV~I7CV@FD9nTxh^H~ff=(yq"
    "2j)Gn)Oax6?l`lubr8Gbm*p%7Q+h!u`bWa1!YnoF<J7k=)$3DO7pyRu;JAsmY&rcwf)By>`66cT0cX?7?ks}Omk?i3g{qgXE"
    ";){;%B2A{}LOepJM4SB@+$(}D|3pt~)y`Q#9*sg^B-X+zBPaWXwVH7+8pL2jafGlSaiAgXa5^;JulcGdfnLC2-u#wv<t(E3p"
    "ss(SW<Bmz{we2oA@9YyDFR=VGO;#W4l&z@^Tn$X)8LPCk^a&D=C(pjO@`Mw+;F}}zGZ8FN2!bJkGOrji`|E_<yP8A6!CQSvu"
    "%y7(W1I6(c5S>roP>r)Tps)OEeA=#Q(7s(Kn@Y6>U>W|N6nGd)wtxqgN(hh8k|n6W%v}FG9SqLz;W>6#fwKIN)9mzehFjE?m"
    "=ElB){=>W}qV+_s>tw8VzG}l~`T~g2_iNDif_D6!IJe+Im`aqpSVwc=h2)yRH$7{XV4=dBhdHq738-i48e3F~LGcKBaZqsTo"
    "z05Q^A;Pl=y9ir2wSwn_paBo)s5oM=ZA)M-BzpsHz`-LJ@C_;Nm#mrGHobJ9Hg73qntAk@?-z^4hVrz3rFfhLWF@?yl@13Y;"
    "VPE0g#j+m+Ucfm&#8b2P=7Yc5gai5J8nr1}e)R2Lf9q|6kj-*m}4YdD+QWq?K|AYBKdz&L6VpaEI{KB~?Q&WHK_uMr8r+Lro"
    "omZfJ-JyNoPg{PY`vzSfb9Y}G^Q9NUZ@rx5yWi{Sa^JqpbS>itx1N5A>964@OqZDHZu|)*Cu1EO9tH)sY*cJll#ofvi5uJNV"
    "fF{JO^9vM9F&63Taf!Q1<|mGaNe4%xq0gkfuGjayT%-Mw3z5S3qjjsGN-EE+h=2aXvP~^jwTcxvV`Ys395@HKz-JQE+<<mx_"
    "saA%8^Sm&+ut{T6&9Lqts30s^rkj&**!KR;qkA7zLiayEWFCpte1(YT;rohS9x^!>jrBaEx2GgdJ!JP=dEf6)RZs&dG`n5?W"
    "7)HgM+Gs#f52`ceL5KUlEPk#dagU)97n&>aXu4~k79O3a7f2K-6n5Dqj=$drhOu=UQ{kk$1WnimDI+#4A8d??f`h+)RaZmwn"
    "DY4o%*gbdZxkCN=&N_WpzIgcKVSDGD%vALM9VfF>x=Y?BmA7^;KUWiC6aY@vug$SgG{@VDMcwbW-;}2k6Z`L49?M%>=0+O`l"
    "i+Bjb%&LhWXQh`oKI3B<V<R*;CiuNY!1oJ;6y|nbE7i9$j{oE|OZxy|VvGO&utD7leWyAqz&NO{xL6LZv@*WboEZY^i;2U!k"
    "S7?yN80X1vCF-wbt?`l#3p4n6~^YwDfQXRqO?*Tq|oZM!}mxoN1>4U=X4O_peC*ibs-f|BxtTsLK%5OF`)4^Y9>)sc8fEs4}"
    "XelRvu5UYFe^XW5ZX~%0vB@Pu>Qm<0jM)&sEVs?Ksf}t9IMh&#EY?)hZ8!n#6W>OZiVeEi_NH53<Io42Bv9{@LET$tb&|zFl"
    "wmGbM10u^osY=N1^}voyAa4JJcVMrDPx>QA<tN*}QkWEVbhOQUbq;gSe;RpfUnTxkMq>N{GJ(mK}C7%?~^+!!Xfe9$+qvKS}"
    "#iLxh6dC;=yCe2qppqWer%b6q7)@G*=$ed8;y-x!eB4H2?JBarUFHoSZlZL-(<piZY1~ArFccE2+Kb^kF*7@B70u9Gt{247X"
    "`b#{&N3svUKY4l0Zt-ZmOLHu|{j9@~@lvYN4_T&>dy3&z?=ycblDFo_-oi;Y1%t*PZQXGOUyG%#W+_|5nvM=Mp0p$mewv!6j"
    "Ga&(sn6jtJ#;uIu{58fknyE@u@_mkAo8Y*H@2^uj>+Etpl$P2`tPH<r3TQ$%0bN&dBKAsgM0NiYxj;eE4u_WnHfKV+L+V8a2"
    "Td?Q?GQ2>8fb(E+l<at~HTC$R$I`*P*E@&DyBfW#X>1J%i&yC<jP+>75S4-nY4cUa5FQ__Aa<$E8KL$Spnj$3YWrsUB7{A&c"
    "?x)Vwdpr4)eo_=9?P2LI?;#|pj}cmCPeu$rwVs~w4rz(V1_n^Frv3~uyo65SkPS9>b6{Xl8zG?6@hgymGFiu#4Ohkh9TFgpX"
    "X11lr*L}bjJ;YA_J(Z*7eiN)0BH?N7Rm82ZvQqUqe+P70a(m@~ea@s(#Xix(`ZP8K1d%rLTc3j^Zd~j_RuQ=uP(7TneLJi(d"
    "G}udn*GB~xP&~rlN<6GXYNW7v=|A}5(H%j;IQmL2e|&f+;Irw>RfqkHpl(xje<2|TPJ6lvHqhf(AXwJlpO|89UTe?N;GKD90"
    "b95kosL3dL%P(yZb8@zte^xE77oXZFTI<tQmX1J9=f+J`ty7O_hA!$7Ru(e2(}CCSBSSNtr<AMh|vipLZ=r?9@RK^z8!N(pz"
    "TJa!&LUfzS4SqYiB6W>HM_jcruADu@9bs6xnuDgUSa!nHaRe-lVH)m<^U;$%Xes-hr{Qa>hrX76fVfF4oNR?9E_db^Ze?tKX"
    "xA(Ji~FEu*Htu1jj}M#$emJHkmDo7IDY8$HjEQBwX!d)$d!e#Ik9*9RY(ZKq1vTChYtN!u@dpP?fDdNkS6VInN9DwU=__kkv"
    "4=0jTY!>oLwuFO?^di8ZflebG+qXyvP;k;H~dtgrG^ZE>rT`<iia*(W?)DEj4C<~FU?HLCsP5W-j^{3+TXCT*NvL;k}jjDEu"
    "Yr_dSEnD8crP=uA)qcWcXRO11{tBQ@ng>eGF5m3C41+-52TW=`&UR=H+10|6@wN$y>*$X!CVFDoW0Z9=du3&Q?)OBx4@@Mu2"
    "%;Z2Jj^-zDSpXtekl750(MY38pWnL9tI}}$|2uiJi~Y?E%ZY)k>D#JnJCy^QjR<T==DL1-;K{z4Y(QfyfqmxOpMT2xtUm;pt"
    "@1yQ4!0~`I^tC-uMUd0irk8HR{SW{Mn1wi(cy?!$jnqMiXDYs9p!s(5EGuo9Eo|O^p{}`I}4Uo~H{-C&JZX>vtV_Cv`&qzT#"
    "4Zk#RY7vyKdEw-AQ<Jhp`NRL8R*P}?6SP~SJv1m*l)N6LXC{5R+q%I45GadbZC$<{>3>>PzOXPMz$JCRuq+5XnS+K+BMtidp"
    "MZJ8+&tE)7JKRl>RyuAm(l-Hr;WAoO7dR`_yOlF}x8cc(anp>KeT9kWa^>UvYQaR(^jJaYE_tBQ@lf~dbXsT|ww||T}32mM0"
    "^P1aInW@N=Wi*($KMRy>Y3z;0Cr_}pIiyW@+pf!BU6%c?rSg|U9aJgh#_v4JFxAtqJ43n(y@>9#Gmp-ImM{X6!e&Y!0om2TZ"
    "_QZKQAC>q679^mmJDjUuKf2Ur%gPeC|57)a;kVNTT0cV-*>Yk$Mf^Eele_W1jJ6b2z1pB?8Yu;u3iF<SDU8kP+Z6-f1`yo`w"
    "`je-@^_zQ11-{Cj<q~^_Z*lV7`>iC->^FjNM%>pW-L1PpVSLx+u>#E4alFH=bWP2cB=B{3qkHdnt8hP1x3x`wTRiyD=v6+s("
    "LvjmpFbFU*O$@$#9=5PiW>Qp<x-`-B>Z+(erxG9K^HTWmAIlz@$P)BV682#UH5a=OS5-K>lU5~RS~G>-m3Rt&l43Z?PanJ^;"
    "EOxY#9T&i~5Swiyn!`%%_WMjj@m~9<2UW`}D^cpmIPkkwKxyTizc>_t@>$bUJ23{fqcB8@n*Ok=otpnMUo7R1M7KhK=t@%-R"
    "!qZ>+=A&jpMqGQe3>pG%B`~a^{jVmHZg%lMWGRheRV|v?8GIeg@ChY5yNgi=kIZy9ipMM(onk^ApQxDMXibRpa**T{umw3e("
    "}Jp9cNaP_%pCnab_iT;@0l<dX*Utx{3*6ePPd@NNZG>R23zWdy^uJP>yP?rr4DSrFD!78TED6Vn$BxMUe*Z#GspafzZ={TkO"
    "cm;{_?=?kh-~bB56<K8Ce}|n<)D&XlwE?3_l^WnR*?O;Z<dL(28&Im554BwF@v54fwXCp;3`nnXqMr^0<%pd}|n5zLKJy+1D"
    "jAtT==AUB#?V@6Ga~ZwrptSp-yYqd=EIQTISjDVhE#o_L_z^6XVMjRX~joA-@(GmDB0Iwh{%R@?gi@Sw-CH2?^BQYC<(N{+|"
    "BQ)?4!&Cd6}4p(y1Q-WqziEwL2Qu%Ro)Y7q>LGf153<N#4=j~<!Xnwnr8?F_Rm9NS854r(jwY$8>GY&e|7Gk`wvkKzGj-g5K"
    "I~oe6QJVNUIK{(C%I15K|3Zv-Euz5aOd8tS-S3NC@#pGx`|O<J{ULOVu~?(#*T7hpj}MIkdQC-CN~8oAd98h04kp_h6g<cJ4"
    "%ZnX^W6AnuD>N5r#gf^E#1qw@I&^Ig|&9hZEK#m%eKRQF>wb7I0;kQAiNUPRT=A$r<~Hl%oe{m)*$bq$N<PC8cE5x+$o=?^2"
    ")8+DT|Y>I>*37jl-hs-8gqMDqBo0%k(%MlDp3NJ}P5?z%<@Z82_{&lPb5byq~*7DX-S%S-1%kujRhNu^>3Yqt!hpfW^iY_C="
    "g?1Y<)7V^1ssJKtW=;d!PuA4$inG#la~w~ZVOUy(x_-nL1oUkhRxWhpYkAB;+|YmCmW`wU7Otp8NtF1YV}XYBWvyU{DhYgdH"
    "rgB?LK7l5Q&<C{Cu?=$q-u3t>p%6sQFcA%QvRK)IDpd`s?s-5U{L|s6+*Iz9}Hvt^;)W5jPziq?H(*J0BX33A@HMF#|W2L&?"
    "1t#y_7D6^`{&{HPof)=KT#ithc{cKxN4Y0^+zX_4uHA#)yXu!%|G+H8D-#8U9aiVeg#S*;Hq%&D87y|dH=^|_;x}SU!kyKeW"
    "XA4qI?&QsugG#4gi~hmt#vk)&Uy-Et@~f36`Y@Ttg5f7^vha(h@X%J`K@LJCoDnqG?D~V=s?Vssm)7Q`V9m_Kl2EN@3fDh;l"
    "xEDTifs%?-PJi(J&(dF~het^s^_|VAxpoCm?6wI5zl^P9Weuw(vr8tNulzaPX2p06S{Y$Kx}89W4E@$<WoT=;M$fYV@I>g6A"
    "TFad;#p0)6t(-p!gcNFkb_c|{)qYqC|vo+Fp#mhVG|K@>E5*Nj^9psw3|bJ8}!*Z4RbR;8-sw3WT1b4mfU)0}5!=t_Dy!sU("
    "2<N1MXj8C9MHCk3sZPnYSvh(7oPt%rSm5_`9zrSuxI|JYM1oMio?6!~JRx~kN5Mg4MVuwM)I$U=ZSgT>>mSxdzjRCC`CaO;x"
    "eo*S@9iJKVcOrCdJ-iGWpRBXwqKaZw+mxxoORXgMgvvHXw5FaEtL4Y9CpEk{K4^Gyhf&5h{1bCzF!E$3zPrl4LTCoT7EQGyy"
    "m|nKSqI{0f^+s@0ingrpLOY$#%z7djaAn#>jXaH51#fnaH*RK@@&S~V?9zcWSgMUEXjQh?;Ak**ISpaNc(TnfWAHlwMAOhdR"
    "aqf;fE_|>(jZmY(F069RKkk6A7Z|jM{L*UhDN!$uXRZ^<5H?%8X~ZZfy2?zBI)zOT!yDdK2_jdbDgB<ewt6Bkjmi0cjx65S$"
    "i7=iL6{RD9ERV`<B_zu61uugBo*CqshIhO|c|V*a+jSFRKa_^5Zo-~!LrK`<q}h4QNSIu5m_wvy(;TQ?nWx0JXvxu?QXm?3-"
    "rU2jV#4A3uJ_ZB5z|8=QX29Yj-WSm+iMWTNkmj2#J>rxkc{XNm>?2WGqu8E6g%gu}G7SV!XPlOyq`lPx9g6*K|KZ_MT^1Xb&"
    "59^Nt5z>&wUk62Mi-2Ubj8&FDqDst5ZIag-HJ(6pJJnOh-j)$Y-%SCjltB$}>0fpoeBrfJ;n=^F_i?)`8NOpDY#MJ(<=(4__"
    "P8=gW9aF6Tnjng#0GE|Fy$My?!1zICI|u@8-bkK_#^g*%O8D9Kd2K5&}|oq=6}G_w3at$L?Wpw4)44frZ*6Pm^mJv4jjIcYF"
    "9O2_TJ(3^;L~)JwYpnAw3VXWu*|DukWQ?83BRT7-=GD0=FAh6)h_4CeT;lvLf@ECz~TZ*^Vs5bZqM12>XTLmO>TO%+gKGt?w"
    "fxqotM@QnX>?`qzxH(<KMLt*)kOvg}S%v0&g7NGs<wh&i`2ma9(CMcFHXzT2&8qk?rvrAx!|qE(fvp+cGF-uuMwg4K91dP%@"
    "{YpLqyZ<YK@36I2Vn*jw-LdUA?w8Tpxtx54>(tcQNBPrxV1x}hq)fmxgqZLSsB+W~zm45!XXt_IuNUUgj9S$2a3DRZhxOuL?"
    "F-slP5`gE?0^q@65m16pEc1JNbh=UDGb**#l?h#Stq0|!DYiZ;&k8_?lb(owMg)>#ScVg^v#9U6>{gkm+`5ZR59dgm=<(7N?"
    "|t&IOI8}xmRos^Rc4bO#PFw`QE0jZWZ-KRN6%gQz^?FzK+7}_eaKo~w9QnNTW`suKB5pd&x_dQUtD09s-B>CSXO4=RC}CAIZ"
    "EWdkoSe=;r>nso5@v1En~hRNd_0r^K`jF)C*H@4aEg4vc-ckK${?vKi}ZRPT+D{jv<oF9Jj}vqF8KL)&Od$n1r2dML#~@R$Q"
    "1p8TZo3js0?hPL??+-;_gxRM~m6d-(kD5p{FG9$>{M46`(GtrCt&PjjEK#t(GCt{lI7^ranawNIogxCL^Gl(KL9e!S%iw=K7"
    ">{(6C_`%ZwxnT`FA%ir+C877c!!4XigW(v%T0IaVx&5^bb@w=1Nh2M<n@-k!XG*SNb+l`nKxdCMzESxJV(Dc!D4yQio!?=O<"
    "FElxZpx&z{9G~exxkzA!<K=a;lgjI#lWcmO^_G=|pj#K-tS*J)_or7i>n44XB!*UV09d+eqDiTS$+x7tMEEYaX)Se&CT7;6S"
    "pxg1&@tvx@!M2fOJ(fi^XsL6s=&&(+JGV(41tOe@c+pX??~FPEWZkJ6IEXA8#5h99u%xC%A}G3f?*=ok+`s8thV)MfL#!w@`"
    "9$=M{&9Djv!Vo!G+nJJc(|#u=nr05Jt%}shtk!h3q95xpl@!)B%#7vNa6??Wcp<*sTCm_iTk;p18(Gf<W6`j<v2;ul+0j81Z"
    "c7Zv~)>H|)ke>Z1d${xl1|5c!TKiBT{l_X6n6<=AKLYhVbK9JbaKOf4{%*RMlKYVeD07o6A$Ui7agC_#m?-;BYeeN=NO?$aQ"
    "gj6*+VH~E?>m6Maa379R7Q3IfIJchgg-0iojk}*(wR$(xwf<XS^;qG?1Fa=~gw|3&j;gqk?`YdH2oa5n4Vh`(#7f`3=9EvLD"
    "#i=I`i9TW+eX9|alerumBPktF4=-sZsZd%-+xkl^Lmp~97~YsPwEXP-ks4q|cpIPrtLIvu%Hl@`2DKh1;y}!5G?5}48e>#PY"
    "n!~Z_6UQ1VEz6yxM~wyHwU9LuT~}>E!tug=q^4aI3>7TXn9}x=@zr3=Fxl<<3`JmZ?*s($n{!(Z0D~0DCzg?p_oFvtWe@j3P"
    "o*>FmV6lhz5STI`rsov?T_Cgh5}W7(GdoOm<x?_xhPEDHIpXRysUn<<6LOf+4mB!sUkBuwsb!j^w@6e(JzR@-ZfQp&6Z*$J8"
    "c#4#a(qs^k{)V{dp+RZhfQu<L|lYj`LQ@Q~bZ-lDggu(QMrBq77X#i^v~mf(o+0>%U|nGvD!ZIqB@NyiCd7o6C&0aSdMATF)"
    "zdyh@UA5%-?;TV*YI(dN$$^EGVI{qlyd=QW|=%@3mMFn1<#Ng}4H}AMtvFxhCp<)iU3=s?5Hym4=!$wOT6t>`;pcPpa&}*;r"
    "T8AGF3jFz<;iiwk05g?nbNo6T_*q99Ra*A=6)_b_bc5^<8?foVqtowP1ycxPxAVD=b5tz_cudkqE@yMvPA66%$;Td6OPKA=("
    "L{Vo!`&W4;GKJ7u2Pip>4iC*19;Yg47>5(#%Fo12dOkXw>gcPbeFcRBc+aLI!`&rN;MioxfS(kKr&D0L9cK3y;mnJB~8WD9x"
    "F(zU3)~?VWZq{0T?Iq;4S)OjzV6k&ORs$8Y9E{<Kudk^Yvnn_pd!yLK6D>0X|T2*@j=1hzDsYzQiPex}jDn2Par0@}N0Zx;5"
    "kp>&_<y&&kqQDh>+#k>HzlQ7GwkY71$9?xRY_kTqq-m*=uoomy@S66T}$llCQjf93Ly;!m~h+&tyf9S$Iw_h$8=W`B|TGVyn"
    "@gk<_nbut72wO7b+zTtgCbSzP%#QJnAKu0CimGE$q(W8nz+>j1iIn_}d`cdk+l4A_zBGFQoh6#HybFuo*me`L7gK)v#XRPMd"
    "@pz$lN)?B#`0c4^eh}xjZ+^sR19CujZ?N9@QpkC<sgY>R@a4c)xgbz=J5!{{ch_GZEM67+un~0g7qWVTypg2CQAvm0x7K{8W"
    "Z-1tiX(a1v6h!DT_CK)S%^(z|2|~?Iip2j%-buZeKeee?zf6rYQ$8;mMb_*RFk@DQgHYJuI5b|gedgIA|Wwi)1{PpP9ac|#P"
    "y4^(4ya=P|N%_E}4js<8VS&HwTmBclGI)u*P*Uv+&TFk0bh*m}Gjy8W})NV%#(`FH>&VPrk|9gCAJJN9!UUyX_VgBzT;neXJ"
    "w@yFmNq#1+=Aa~JyVO1FG(+$bsiQ@c`+ZeCI7uWuDKwU;+5$QujII+$Ek8HT7jq~HhU*6S)$dihP#i*6vL>#P*z4(q7Gl()_"
    ";N{a5?gkLPS+5njfau_%@IC`(5d9TMK?dQfNo}X{<S=ysM8k>;R1&n#9W}zyJQzKuof2QndCt^AGsj9F854;B`O`jH|;{h1p"
    "%5cZh;3j@qYo(KYE1voePsfwV4L}Em27XPQR|ViBW4K$w5k7;~9L9FGUb?H4q;w4z06^gs_ut<>pIM^PxnI~@3fAq-K5*b#z"
    "PYs=_G`71{rF_N389Lg4vgM#?tNL7^)PjVKWd#7bnhVS)5iJds#rwkHB+$<{HNSPuNpl1qk+vrKLG2KhLQ7=X1!hC!dYnwx@"
    "O#OcZMG(OIp@KmwV1Uk&dsG<#=fJ(^;rX5bC8cLIr$d*U`JDio=cHzI-486YRYM+?BV^Xs%P3k!7OfLr#1)w-h@~Ti}37*I)"
    "YoOxX*Nz~vmE27WWvhJKM`NElSsi9LQL#6jI1P=+z@L2_dUA;;^5N-o^qZ}3Sp@phL=rp9=Z2bbOevoVRgJ~Zi)<(Wk>FAP7"
    "BO^lGu??aKqdq`l?2$*GNJ-rv#;J$DSNX5JHA#d!%*1yC{!**l0T<uiOD~y&$b~g8BM)4GY@@WJfGC%$ymf`h#+7r<-nVu`h"
    "e&15XP51?)O1=nH<&W%_@aU6nUo(U+e_N9{sXX(G4Ym`N=c&MJO$%b?1jr!x$7%8JRbt?sHoC2BoY7}XOZg)?5gRj<=)0ZYs"
    "jc6sE~+r%yw+v6-aF5((_FNbW~q@~w+a^+jE_Wl*UeZ+0i3YL%W0I;T(NJ&n$Sltw0zJ;$Hw2Yr|RH~7hd)SW<g+h4Y2RKlf"
    "P{6ab+L?wiAs7!;XiM_)FC=_gigGbi0Uz_3wZ-QUv}u2+<ePHE~LC?M6i??S{E9`OELf-X#DYxbUDxE?m}@WGB0(^F2`EwGO"
    "MwXWqwAe%BcxZy7-{R`ei!*YjGgLkaIe!|dB%7B136J=t6h1i~aro4-r?UZ^1zw*0l6Pm-2-Vll_?Y~a;OhkVQ~F%vJ;{*t;"
    "8qKYZ2UJ2haKLxW70QEHwK-Sdi>h(?3cYkgy#7YZJ?s=R6^+|<Mo<9-?$<V?8U83Y{*p>#)iO+0|&wAo#z-IRr5!iruVkHeo"
    "Hya0BMbq}=v`1<Aq$Hc`6;;PzR+eosgX>G*qeEt&wLI3B6wW`Vbka)b_qD*S^z%)kD7xr0%vlh(E-grOVI+tA3@Q<BrXHxOr"
    "8Ep0yyH0`X<5-5z7QjR7;(O>OY^YO;&*GziwlqdnkCPEep*XAe?7>ATWY*flrwu+lbWRsw?%{cl1%(N?tPKz23o^wShXzAv{"
    "kf9=c?`8vBg0ny2WS5<QChqOPSMSCI7h%yI-FJ(?<d@h3k{Pb;xAfR%E?ce)w3{p~Cf^!NNUv=0b_NP|d&|*E$YkPH+7$G}U"
    "?_C*5fvN8*!=Rf}s<f?(hF7dx)-{sk)6_W)2m2w#PtE%@1{hR%z&-=nuo%*}WUXn9W5HotWoSDEBGOh~5k_al1kE;nSlCyd2"
    "Fd#Dn6V-x{9$n-tkc{9e;GBmsg<i%qo0r7lhv>aTRKQ+heDT%Ao{YF6X`DXt11c4g)%Kc9Gl>q2QQJqit56<kN5;Oh52P)0*"
    "DrX@;cNUfi1dZoOBLe^acva4DOMbl2X1&i1<Pxjj3AhpERlW-{BeHM<V}UahX;R2Ugb85&Hll=xxdE#BzB|4!T*gK-Zot-E@"
    "8iHQ%`$#uG|DRBOh$KzDA$AL=t?p$q*+1a1!#8`0bsIba~R0!60m||yyzT4pZl?mN*u|HN-}e#nK=dOzg#t+26$y?1(?CKkI"
    "cTO@)AI?Hdq0a+?f&Xun3b8mFfDx#`~<;!OPiM9XX2_AcVFr2K;}Lb^!HLG)p1l&nC1*ZZu<Qm_;9g^!uI`W{n;FGJ*ZJxsW"
    "@+f9w-r?CW(m<$C%anH6{)3&i~aQf3Krz)z-E0Ns}=%ZVh{7E40&<ldyZsal->B{;*x@DpEYA2i`M3g~R-cnWK}v<S54#D9<"
    "hl=cSH#`Fmchk5Ensv3ftuC9LdX*n1h1+=*Qy2Xj1c-9{~IO(92x~Ex=9!u=;G0TMS#yXls3&HA9;66Xl73@vZ6qndYJNcu6"
    "xUSogo)ryW!$vY@&9(qx7Z0c4;g<Sc?|)%s*+C!~d!USmEL-=IQ8j3Xsnn~W^!qZY%W8+?F5)#g_Y@~S69$4?tFuUo=QKx8-"
    "+y-Z(uE7FfL}G)P@s9p8BdnzQlS;@ap_xb-T860v<^wyx(O-rUrx64I7%$AYn6|Z0D(pT!=Wn>&@B=%VPdw~d&Spb=LMG;b<"
    "1zC0F<Dzk_NV3C>El5OFfWP1!R?ijMK%hCQB`U3&EtPkoHqtKbi72q{$1?yuQ$>Dc;o_cx!<5Vp<BmJ@Xa~v*5$-NK=v1^KT"
    "jfi^@mcqs39T9#tm}dp|ot#>5jYfU2Ue9dZUj6IC~gHvT*`DJR*~jyuP$+-TbT{fU#G<`pyjGcu`iiMUW{A@^q0!09>I{Ki#"
    "9bCuuD<DE<?ztqK{4b^!U(f;8P*cN<6^-6?_Qmc=ie?D4%_;{0mixvzkf+Q>wbqR6w83gQZBko}JLjds29pYM%U^K}y)srmg"
    "GBIpnLK(Gmv?m>Pfh&9fqoFc2E{!ecoN?^>O~CSU7x2tq?KLHbt8zY*)#$;ErGqXwr7^?Hvrh-o=pK>>?zqW=@*kXI!90=wv"
    "z6C_LUHCC{oJ7T00{cE(bQ-jIKP2yit`%Z+y}eX?x^;l;1ldkfXFWe)Zmo3^oW>bkhR0Yr+BGW2SC@?JX`<$ypep#po@BLzj"
    "4(h^iETpTj*fd{ot6P0aMl8<_w=k!>?hWND;R)ZA`We0d9+#fdfw!=$(57o7YIaf}}>4TrVSCI?dO`uz5P6q61z))LF_q;y$"
    "6jA11}Lhgs7II|jCrWj9(W<P-E{m)#dj=Z%1kyWIhta|VlqZ0L3|L;sajyWb(`rrFVrtV9NQ!u@VjT5Iy+0si+?CQWn5EOZu"
    "^%^m8(avivj%OIJB!<pbYR0MtoEr_z)_(H=TA04n}D^IUUAq)o3XkQ=Xl02vTO(Z)h{Rc)-Ya!UB7nw5!_=Dw*sX6kY)<G-l"
    "xp)e>TQ-TN=!uzu^pUVhY&~(Wm#+!i3WavVja$~4pZvM^gXhv(YQgh-X6mv2%`;l;TGn)+*KwdW{+$?;@O+Knax{b1npcqlo"
    "$yyWT?>j--E_dTewzbyYc%}VU5DQuk#P#>hE#LVt%lj77pKm8v;?KSWmZnsE@FDz>GJWpHkCFM4gvD@=>Mcp?qoZlvz<9MbZ"
    ">x^D4R19oX?C3BJOrs0wl#rpEf^E17hZ-iBxg=_2Ei9_qogq<SKDwLeZvys3vE$p6~oI1~KQsZS?*6d|tHRWVR~1?V<kb#+d"
    "FZnv2?zM@^MEY0wsr(Q7rHU+vSsOGZ7J$k1H#tj!6Y4UO+$12-Q)5}JQq$L%_7Fn|Kj8#63i%4Hu3b&j21pkd?}W|DcOkNgR"
    "*R|KUQ(t-kY<>~VS8iTebD|k?MRsJ;aZ}VTE*x^oU5E0%r9jt1^UkS6j3BmG8Q(o0$bA9^oZhbi7!ZI`cG_YosKl4yvxl4S%"
    "c$#|}_6gP6cmP7HcB$t#2aslR-^p-#B}`o<Kz!DdVIe?Q%cjcp-`R@^doCM29Vl{L@kqhyctI|QV6@mYNAmI1go%xmibjJ|S"
    "zhq7yfZ|hY~D)4QgkTQ?H_v!lP9{HV&<fhzPTle^}P)EV^l%^j^*zoCeX`MXD`Y-PYg&zPee*vj-=gASG#Pm^|9-+{`sGaRA"
    "je#?ld{a+-Lei2ejYo_s3~Hmixn8LxMLVpXMFQv7NJ5tW<3gwF@9<nF6qu6K>rE9tIta{5Z(xy9QS@cFt*VTRBMcB>|G+yXt"
    "CY;653BKlo*r5!O@Djg9Q;c1U@oeo^SCjgi+qJM=O1RKh@@jpCk~TNJW-I*5UBP<b(~o{M>|Jw1O<*?48L+XZ}WIgXOt{v+U"
    ";Ex9?NZ|1$|HtJeVU*<sW)0y{Xi|@th)1-ja=?36srXB#|spNOCeWw*htMs$;xlybh?sszf$URbryYo?OwO<7?{eGN&2y2nC"
    "+ybB>{(_{%_b3lHo_-bbL^r|~CMSH3<zu|!WKrYMLTn)^BJM+`v8j>}U5BS^d<%au=ajIxz$vGCCQ#qaST1P?ckAln9tV;;_"
    "+(;u$CtVT+3&8t$g>6M5YO<}KqiQwhP$n5Jj@}#4aL_<*j=kz>+!zfE{l_%2ycYP{R*aYwo6PgT@ryU`wvz;XiN_gNOIWBxP"
    "lv-Z@LR@4@R`GU60JF9Xag$lTF5!9<-9i=i6NA-*dI_dsx=7%91?qhJj$Ht7O|doi7+>%d!*v>R`@XwB>0cwY$V+xhHwcfg("
    "|uUM5Eu)-uht;BamkoQ>P*V6(LKZGk}g70^tye?E#<27Ebxd$}l6!nPuD__wF{X)R=tcb~S<@lZ4`eirK6^Z}f#rKM7Mlb1A"
    "nm!l)Pz?7ro5ISK%h+vgWAOVtPu518I3Ac9{5^vh9x(h+u2iMR&Hyya-Xz=mx<}gBXRXkM%Ts!eNW8=qJ>GSkOBB{z!mT6A%"
    "`<}W6o8p{US=BfY=yB{Mik}M2V|(^rWVM~_CwACWUMe6F1vuXn>z=?TWqp(($GSNfRJ7{Q(ZBP;C{@#VMC#Lt^6|Ji<!0=LU"
    "76ees$|Y(=ckSH_JwB5&nP?J4wgR-3`H@0YTYnLc%TM*Mr~9FbzpPl1|j*8x3X|k4U_?fyLGF<XP<nGxzaUh$?*A7QD$PPC8"
    "7c-Kdi#a9WCK7vgo&q%K^B4r9_v>KBwWN?ETNDDaLh?+I1NBGPJD&-Ar~4<oWJwupQQ|HD|iV+){RTr(bE#jx^5*=I+61W&{"
    "4E_L$m;G9^tH+2DGxF-kpza?SFVMTN}@k$0kP21$!Tl==bO;>jFoJGj5b6Rn6YvmR03`aZIM$@m9=v%fb}l~dKQ&A6eQXrPX"
    "b)|H85JknR=v2`dwA`1Imu7D$aN<Ky-eUj@Wf(hh&{;?KC)!s1v!Vs8G4sl65nyh?p3CLFKleA@p2bP+?WhZW%rBkE^+}w#j"
    "80$uPNK%6wCV>Y%w*Wl#7{~#`B`S&~E9&z}vl}q6goD|;))o1E#&`lYTq?`fdH~~<HJIq~0a1PZ>@pUGW&;!baIGiXo|+iz!"
    "B3+&a%Eyf8MX_eIL9UvoK7nfEoE1~V**o5A1si~a}uLSrmB||#F5>x@O_6(fQLjc>_%$`%s|izv-nngO&E7UpT4il$EL=>_`"
    "oLtE9cfSdj;_?*x*MUqkGG}=FhrRV9Nn-8;o4K`B|3Fmsh6v@q5Bu4oZR&DmLuS1(cOfqjllFRjQ8I5M)w;$X?*%x|yKTl^3"
    "$6z9|U13%P-B?N=-N78R1qr^vXPKQpLFg9b_^+4v2|on4sHv|oqEM=KKDKYSUtcF!7pLpU%slwO_2AGd$(kk?_oSEiO&Usj}"
    "lN}S@u93z!_@v{=?lO*rz6*&}JlTUo%uT9VMc7E-r;uB%}1?5#-G?D6PxBJp^@7<klP+G3zm;JWiq3;o=0Jgc`pP}R{&uSGt"
    "@cPg-+mUr$8kt?RYgR}zQ{Jv<5#`lPf}G&jKcFAMH1)n+<9*p79H{m&?A|w(F?8`%!&=Sr*#^j2_InV%((L;Tg}0`C^Z&vRM"
    "lCG?AD21G`aHaa)QG>k!PIvVVAC7d$OMs(LOm07+&Ju4+wio<7x(&v*x@IuU`i;Y?`GE;DVoO*Fn@}d#BZB@ce&cebY?{(ck"
    ">=|gHOavkEg|&iSpl<8(G-!)!Pg-Y1Rej!d>jM3XB)XNul%?rEHe`X!c_O#lXdJfExrOXK<FR>swdS=gd-7db;`~VAK9x_fF"
    ";*$mk!h&hoiu`s<hSqe!{TpvQxjipLm5axVuhhnX_<1gWlhS<1%ukK&k&KTYIt5)EoklM|m`&lZ8PoqPL555fcjUI;WgY#?M"
    "`UN;-I^{7>@LDSn}?Gj&5f@b}}m~AQb+*@;#@uv|h-YuvFsAz9HfWFG-9ar|4+!Eo^BT)gDwJkPWjt=#>?9DpQ(2pF7aa$*)"
    "=POFkOQFCwmfukxOv^1eJX?BiV0=QLNxMrADuNw#2q`+ZM(9q;<vE704Vb;ULUy1R&PU(8M2;2+N~@-=UMlyE@cak#$rOnsw"
    "?%LiEhNxrDIkc4sr&U5b)(h;Z~<KOxrORCJNQ9smxYHk#`*D7Ml!Rsha@w}YYCkO4F#;_MJsLto(%GuH0XNj3faPy5U=1b-M"
    "Ds1=ujrs0T7(>7UedhXSy}0`zrHJ#+)S?qL<;~Fr=NmQ$f69$&J>d1rJ2a;W>IIyTu5G_*)>S8*3@9Rq9AL=N|qG?0BI-3eB"
    "+zD6;nU?+X_We=#3ql@W6Xk#!-v&hGRKTGwkX{!(^%X58?{-I$G6QZlsAXd^wDa2>~S`%UEB)xyjNE$jDu&(Y^zQ~|B%55g0"
    "8se2pw54EEIo$w9SdQDWJsJ`~_++E1Eqle}<Odvpoo6jAgl)}e5KvaHop|(G4H>_rlwFsxI#N7!M+uC$HU23$G-ccX8oXDa$"
    "E}SA#=0NDNJVPt9*RdLX05PenOt}+x(h1n`0!@$%3q8oHYr;KerlicBJ=c!XR82cVfUF+36bH8Yr8~)>gIMpT-he0`f8O*K@"
    "azpV4`#v}U3ryhT-j{z;G1M!t&#ZD-Q-B3>F;YkUaCB?X#fQX!l(Iq2*hO<!K48f+ryn@mF|;Uap#l)SyMuF4muO6J^ZJ$mO"
    "U$YFq$L1*o1=<w?s-v%mRaT>#UuAwb$BMf5FWRl$yyF?gG~R#n$^0mA@7#smg+(MhotR*<l_EPxcNDFgE<P7#?l`T2R>{Rk6"
    "g=zL{;cJ13*L-*YAGR{FcA`8{^(N>GYy(Yu)TNv^*Ig60wHcOBoVwC9sZ*TyOE0mw!sG#w|^6oU~SuvJfZF<>eM;T3T!P^3i"
    "2(!6{`^^x+d%JY$j*982fbe)Q-{gd3F&5IxKv3oZUxlY0+N3t!l08u<D(<5x%j3038YgEkrYRzzrnrd8MK1fvPf~qg}pB6%F"
    "LS{?Dcp_vo_PCe#YL^H1FvVUFGOTXZWFI@TvIG7d?)syA0Mk2|U$5kDFS3`g31}iZOQG(;KjB$3eL)09?m@rsx3UEZVDgd07"
    "e(lP{=zw13zV!)jw)ZWi}}ieikqk`AA7oyQGO1&$EnvWb*J~O=eBQJ=YyoD`FFgpB8IDOWuggoC2bMgfjOSKu!Obp#P{c|t+"
    "8I0f8rtf`X99;%ZR?MgcS~Y?#3uym2<Z$vLD<ioV@2Ar4H2&#EeC*jkRINA~Q;g6`kbj)n`+>Zf=7oA}jcsx#@QstK&X~%I~"
    "#KZV~?&<|`#Lgr{wIrukv^96z26a6I2_q;Ao94AEgo%4Cv66ewvIoKtk4dR)EOf{pOS@eGFOH|=r>{c+QgSW=%gJ7iix6KHZ"
    "+NW@SJn6uFPwbj}wADrR1f&ajU*$0d<-5dQm3I3$!i#qDYf2`s$a<kCOrLkT7{SOo!RzAEs%cUrYukTU-Q%}MT_FYwscOey*"
    "9|&T0KT4kcxf^~mHRlkq8|&z`UD+k569|4Y+ry3(Nib}tczq6nQnFYg2Tq>WY2B)0&;=xpBxPh&Ykl*S5Z1S|h6Am~Kav@C&"
    "TWT!Z1q~3;pIZa(uYs};9pK!Dwm$h(scT)x|iW>$yvMEj`$k+!jMpT$`M$*x*qxX$B<Qo>u|naytWi3bYO%2d6NL;5zjB$IK"
    "f~cl)x!=A>-kl*z6P87)u5^Rd6#Z_KCaBwH(fq-q{KT&oSM$cI&lj@JTh;ldWsJYzM;Hkolw+)hA(QwvhI*qgqEWwlcwhSmq"
    "V!+9rI+LCMzm5csP(6vw-o4fRpuagsnFBvw_zo~XNFEg8&iCEOSX6sL>AyF8xL>@1DVN+@Wz%frGxqd#Y@3ZpBx$%UnOf7ug"
    "mEKGh3)B8HW?jZ-L+eMc1w8zO`@(I?rWtKbQJlfF9ZO~7;WA~(T88YduYY20k73!M&8Ww>f#0O@yS3hwQ3g2lT&F#?&2^ah6"
    "iS62DOk)W|Fx-{OA@3LRP5Cr=%UxT{%VeA-{55C2(gz>xBKjqw9+*uAw0bF)tPJKj0;p$C$Fn8$csO>CxC%yUs5h8p=lH~bE"
    "c&MV_0W{N<One8we~c<>gQ)>;da#%Y662-qa#^+WtL!5frA=+d_MJ$a8zC?wX9}-<C?e{5-QQtMa-(N)AbY6rMr5l;yc^CLD"
    "gS^)c(dt={6s*l9qRwW?txW9>7v5n$|Nt-eBI}S#X!Cf{Uo*P&<=Kq;j^uw=SJm2a6K_Ck{ij1Jt|bWV?xC_`5zP0V=)PJcS"
    "LKol}J)1AiJK@B|<Hpn-xI8Bb}N4a3Bpi7SrevVS(*mO`L5m15$2HdleT7;bACt*Olsj01b6>b&sp9$(4hXVoyh@{Re7Yof8"
    "b{;RdMg2aS=1!WeX7@AhNkVl;xr%ghByhNhQIrvry)CMAI&qWCTM&Q8@uGVi2&Yf>P7UPwCA{-xQ37Q;k=!;56IShjusNMcs"
    "fF&?Cu~z|D=aawv5=od&@=HMLrd6U_LBZzpIITzYr)CKQ!Kjas&oxohekmOFlnZ}<wek(xQC#SU882ZbTWu7cWAvckf$WeqH"
    "#iu}#H{Cc<uyeppj)KUxnIkXYn{sE)V;_pOtTUDL}<i*nC6BtP5NeNcFfgF9G?>ck6%fL=TVyzcsuTkhfVZ4j2#;lacbqP9d"
    "!*VjXOm>hYz-``7h>`QsrxZq2@txIm%W3^_U}^bV#I>?XR#8+-HUK<^}9Vl-<}VbtILTzi-;AohktoK|T5FFc6d(Ro_rpz<G"
    "U@R|U3oSFSy#HYq^>6_NO}A&mMSgSgjF{-n&NneqpGU6T52u5?Pgg-UbbxJ(~n;Y`p}InS??fVcM#VXJtzgvf!<E+U2LOD&h"
    "^82sa0z*L_H0fZR~(I3{qH#<bcfhjofFZc)1Y?Ry>GMM#!PPdss-hR__B~zWiGB~E0@{HV4Z=k0mX)ym2(*o3HNwTCRD^bBT"
    "Y>{tnJPxB?Yp3T@w&+-wr<tYGb<%+K$&prx)9fJ}pdG>TtIt-mf_)x~cbg@+Wm2>ScR~OA_}|C>KK@@1GtpHF%|_DS>s2sB1"
    "oan&dd9jHx13)5A9V>dAO"
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
