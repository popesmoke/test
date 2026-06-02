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
    "c-ri`<x?C^)3&|K;!bdvB)Ep)wn&0Q@Zb<UxNmTm5G28aySwWy9^73Q2pVM3#oyok{1<Q4byQEyr>?2#>FPeaYN9`>$>U*DV"
    "FLgFJVgaLO#lED@P7*v{l6`cmLn7Z1OOD}q_rWL|JE@wtrU%U&P}si+z*6j`5PMkGqH@<waTA?(tpzjSeV#Z72jf_oUwh!WW"
    "q!Tqsk=|s-yO>SZ}ehDp;qEn|s-KS@-o%_+LuwYj>&7i|pUDwVa)tDt6EYn5LbaX0$)th?JB+U)KZz<^IS2_#gk{fBgTBM#i"
    "Y2dkh99ru+s4l4L8fgl-fw>CY3}#xk&a&d(`$Kx(DKApkb8FzJ)h3(nYL0$mXM1J-|z)R@#>|9M@rHmCyGzy#;C<jsj6*psC"
    "N6J?nbLw^a@FLMSQ{0U?_!?ffCDu<1C(;>xV!0|7hm@wQsQii@f=pEAA&?ziQQXCqqTM_Kj75A|V`+Y{xB8me}f~1)urZRXq"
    "<s0*($PHIiRMY~i;LLxg#=o`sEUgc4fGNo?Q7-Kj;Fz~56uBwbT(YK)LT;jY%sEfY#$0QKvOf0I|7_v1<iz1dMJZz_N}oA<e"
    "|}#u7wTIyX12Ljtl|XTm!ASXBYW=o-vSoNj9VD7Ne(6@ig<VKN|o)N$M1n^&EhIPlGdc>&ac(`|BaCpI>@3qqKXPLtiqw-z|"
    "+Va{=T57r~{1w0HBIv|D;=6b$qNqzYO>_dx(dqO00;>H%WnXO4DlTlsCKKoE8^I;p*VvN~6-s9l?bmV$R6HxogJA#VPDV$P?"
    "VG?K49w+sj9MS_S?M3=nn`GDqcaz4hP)b4~m^?)c!5L%GTmcQ;<bEXME%#RAwW$z$i&T&tq=cK)gfMVIkJL5t&3!IfQtLz&-"
    "DDdnSu|4vG~@mIO0Q}dDBdjd2lZS%`6_FPoh3fSBFdV-s#Z_3ZVvOpYJn3zQ6m;TJO^9k1JopkIfacUnywzgz#1voH&%R_L9"
    "r>Qh`QxZdyM?hZqhaN=X7nlJaH)0gc!M_|W{?ze(5nD1ZN+5@CnGhUYo0*^ny++gYN#I5^ddmQU&43;t+W2Y90T?Le8(<{l2"
    "|Cc`!<7yq#3?|%Uwz9DxL58@xkKa|_F19aFPmH$i1O!FondL=OufR^w857%Ren<6v_4D*p*Sjk(Y!BZ0COdz5uj*W22pMf4T"
    "Ir0#6tNR=@GbJZ3W0b)l5n^du+Az+Dj4<O;ei5DjkRFXgaaS$8dL}NOiaf(UqbjS#HHuXuG0^c!?x#G<UFdiS91&JEuD6$&0"
    "koYJ1ZkX;bXcA4ROB(Spu6qHJL`LrY2#Y}fb7VpLPdJzaF#L!d`UZOwqJzrP{Ub1jVp<8jywd<zbk&K=#)9l8yy3}~F-ooaY"
    "8UzVmN#5{`*1>GNek;qK-;LwhqJ6e6kXiWi+5dB#pD=gZ=3Qs9=>9@Dgyo2Pf_Zp8gKi9jwJ&H{{U%`PrGMYR@A82?FkS=nJ"
    "qBudHRy)zB+Xq5Z7w|X)^53{Y)=T57Qex`uce-{Kci<Rju*YFv2q*Ehi0-FaP3r@^pXl%UDAJcg^%k9b1qNuiRZ29-1mz52H"
    "^E-YJ@y<B6X67&-j7r$cAxi-RlX=}K54`d-=tEf-DaG`=d`SCNt)pE9=KNE0XT1s=2<8h+q<C?6j6r^!QFZoL<R}w*1>qJ<h"
    "8Rw8DyB6U_9WdbF+(gSMV))c39#NJ=p&gLg7{mVkm8>1`uT#fB9T=(bxK~+#b<MyxEI2In+TXIuXE9Whf4@^H+4#*jaUk`5J"
    "m#*s!CCy*@Xa>KzR+w$+Qv74;+mXvsw%aE>_Ym8}WaFT0ADc(HJ+b+mG4^yxU^AA(_*q$}MrTWqL4u72;U=k4x%U^yXH);HH"
    "fr;OfEW?_*8ddni9k25+f7u<Vj3AjRM)2%QC7rg9PCUFsBV0nPSfh4-0of-aqKIaVAHpu;gCOq{O4(^CPYyOSQ^#syXpw|fC"
    "3A|uF2+MgG&{S0Vu_a8Xn?0bV?&w)V!@JUPwR2tEo8r6$jUe-pkk~xWXbkQuvBSEO^4mWch<-ny{*Vl_1-#k|)bjo-MCius="
    "pYNwibqP6CCVa^r@8#<pEgnYBSpZMXF;Q1UalIVp&G^>lLU*01RNN$-Lah}b5881IQ)MW?e0Xaq-a8h_#cJGr7zpC0hKqtR}"
    "*Wu-3#f@+{26XSNvi0<n}a2DnRoP6dX*mHWWN%CKpoc4?%qaIQ%0+eJ0d_e2*T;aeY=OI#eS5>tEDIGMkeqTY=_sT3`A|y#="
    "SC<TlPhM{<@7I;sR@U=x+3W=rmGd6BsM|92^=Q<Lk_0jhxaI{km0$k5DRXT3_RLwS^Uq=Pcve7XP0bFsvnuTwWdJW>~#Fn$V"
    "~6gurCb)xcJd+*g|XNdwFCD6Kee44HtB3S%;taOWjnbz1ZvOV4JjIbdQLk+I!N8=R2hN<22kA60<(})aDeYv`ATvdVeBae7j"
    "5|`)W)u;xB3axSA4@yhiTVmL==dLyl!G=#{lIa~Z*Y{Y+<kvw$qh29VDI;p7T;%IfP=}2;<pk-GhB3hsPx)=A0S=_Ea3lDyw"
    "274M`gV`<aXf{Ng6R*b35g#$e+VpO+H4!&{%#J_B573@K+Jzcb1o-?Pp*$zWJdYmvSE_f&eS%a4%&BtAev=C95eb!MX_GSdC"
    "LjK_W?k-pr8Kd>EHfO>ZZC^qMml>1wK<X7zNX4Uz0;$kaaeG(&B$f9*QPUyiK7)oO<rLw>!Cuh7)Dnic!k=5pBSG=jk6`vF5"
    "G?!xG?K_)}gaA&ntQKms(!HO-10uCF{RO~kf(CF5T}tk!Wvj$X@f|D)?Ws&44#-e%Z`a`QZg<uqLJwYh3I`R`Tu{8`BUWNo1"
    "0F&Tl0K}mDjSR6Itn<oZ$OFczmb=!5+W=IAR1xE*RYz^1M{H*s1&VvwUS^2ldhh~qu{HWWBdAsx51AVdBJ+0Q*GCADKFmF1k"
    "m<ejqVH)H(b9cS(69n~G4{-h|R>@0vrdnhg%g;6C-Ohh?L=uV{iUJ5V@%|KKcGnxeejAew0J{~))D>n2adVfZ;vV>puu-2R$"
    "#8MGvf9GI4bfu1RsDF~DSx{Y0INh8(!O*^H%7OnSAD%55ZX3wTCFoI<RcTN&=h<(GU&HuAxXMbV^eY-p-=uP@|%CIXDkM9m1"
    "!Ht{OUV?h?6;q;VL(FyJh3+sVSXSBQr_btz&7@oC+O;VoBIa-2<eP*pVr}@q?9{p$2DWWKK>STB=Qb>y&C=GK!j^S%$|r)ic"
    "9d`Nr7!@$z$#&K-th$)a=YOPgA<R0cX47P=M66?IsS9XN0Eq{2VzuL+JsPcV`XzIchr%i%X>C~eac+)liuum!*QNJ~%IO*cM"
    "RxNHuy9|LBdyk1F=v#X$@>j2a^N`%=YkECH5kw{QePRgt-;B<QU6A=iNi9Xvn60mD+qQjO04K{@t@~^9qsMmFmBmtZPVMOZA"
    "<D_J}zcjz}U~lb{;OB*BtO|5m>>7weZd2P%6Kz8|oI14I(yNd~M*&936WdH;p&`y0*N<pcvWM&2maP$;ghjXBle+{|=N6=P&"
    "o=hwfyEylCyE<%YH~M^xo=lExZZyDi|^eILO6CA5)8&q2~e9gQ{bjzgk95k1VlO?I$|X2v-9qwrjbdWUQ@Sr%=d3P`l48u(8"
    "I=liqRiSp%P`iZDuVSo5Jser4Ka7k1VmgbIIr(yWda3`<&9|rwt-_n1(%+^COWVD38RQ_*3mep=k>(b7VSe_auJ$YmqV9=pv"
    "ILR?B;Tbl<@;FErfWWQM@7R{P}D)OMb#P<DG20XX8%(F<MmA;}>wI22UN(d12Meb?dQ+{!i@*bYcfwE3Ba2Xh0c<l$`X81yv"
    "#S(+aniVlB5L4V5Le8~KJYI<51YVxAOZBbIMvgLpQ)YZauZMz5g2-oD({0QjzwUI@rtw$u?)%n_JiO9zFKu@bwI-l*$9w$B1"
    ">rb8_BwKi20JUj$%{GsguSS)M?1FXB)|*wre9sX#9__PC+nvbB(Lc?cyBTB=o(i81gQ2{s@x^C(**}p+{&YOm*3$;9G5g|<n"
    "Boa`PsF}+^l?aJ**5Q>#Nya_4_S~lCJI)Ua;n;`99iupEcKZ5@z+Y^u<Rz_O$C^^$}pV^yUew7CVlYoV<e*A1E>r7T#A|?sg"
    "fL!HAAnrA1|~|UAY+)@QKi@==yH7D)sCZ`8S|gS{k$MyD>ml%Q#RV-n1IBb!gyZ9Vjqq%xxiCxouzfMmX1-9L%H)#=sFbOka"
    "7|77`xu8ZjTv{@kWHFl6{4*GuX_L+)77N#>+|3xWJ{&-mjW-<sTSR|3bv#azV8LnI-n=)Bfp$Gjt!o_NvhK6uhK#%_go$z{5"
    "og|~RE&K_~Q+}Aobxh-C}bu`DNML&Y_2%AGMWrF=U=M&uB0yds+6lft=ugJ#eyR!Cy(>`pw`<4mx>9D1gE=b>4OYM-Ng-rXO"
    "M$~tzqhlAT<0^q}UfxZhQ|Zu4E!7=${J})f{5;vU;fVo6!e;$!x&jX+Q)&L?zt=89Zn{l;B<ufbQn7h_ZH?LAa*d8rh{bdq*"
    "j;h8M^xJJ3L}K9d$tsA@t4Ki=?3#_ask*EKVgjfwSjvkpFsVwTjvMb!Rt2h2!m$*;~ad{2rlC#o}U75NUW11*%pUPC)Ibjsu"
    "*+KgdV;(nxC5$<K^a>ks~Us!c(mVUGhd?^Rv&*q#s;8-vx!d!ftlVvr?SX1pc-Q=b7NyYT;jm=gB*v9914EHIhYd3nq`Kn%V"
    "BYdK?_nbG2iR>C&Y-EDrzG2*1PTdaF9{%qXnTLzmzrWm_zKhtRf$Cf2mg*k1+INPD8E;Jmt;_`(y=E&M1+K7Oy%LB(n8y!o<"
    "kJbnr&Att1}YItkfkuyI>_t`H15Utdx4aR1uC4D4O=}Px~MDL!i+zu_O_@oa3eBA>)=*iiKi3R*z>Au85#;lCD&W*zyv05F0"
    "qr`s<$&3~wewoJ-CJM5X#C;cZ`YG@TamVf16@p04M)ZPy3&#D^IcgXX%|1;@_=>YjLpz<!YXK}8^*a_YCKK<<iXml4Z5Y$t!"
    "uYRg^NGcJA9zfBJ0$@(G7G;R8A;Kg+XyG0KO5Mo7csK6`E=tb+&;T!$jY{gdoR$zzY1Nu@r$AF*spj%1M2b<N+bhdhv*bOse"
    "sD&t;UWB7=P9`b*GM&mHnzDplkDgeW-h=jQi!__A<=$m^aAeOMWVDW0*`|a%nM&ih-n)<2<7If|%FeP0G?8yOiF>H0FRWfg`"
    ")dujGf2was}aLW5+5>@h+{u$DL9=E?KTWKyVxEeDn!W)z^50Y)_1m!rds*!XTj-0z+yNG7P%=o-a!6y8T>l1VxEmOWIXi#(T"
    "YFP}eHhXQvh^St@{eosB>1se6cn)9+YyT>&L^t3j^rN5ond-mc|QFJ)V#@J=FNbo6U^(0BHeBo3zN8`#!;qCFrQ+vq64CPrs"
    "Xv?f(2fat2b8fB>p!V0iiRL{T>OC4rmmhX^OP4vk^02$JYiA9vT=*Kpdh=j->kC!Wf!=c8b>N_4PDRY<SgU|xBot%V?;Bn<s"
    "0FEytL)saT6~(11O~=AVow)*z^!m3mmta+6%VV>5~0buF>47nhr@K+wUaRUKa7{rouXAV_)-PGHw+6XGVYnAqeri$2Pf}yJF"
    "<%B+F1~hmu*s3!xtl(nY0#HeGjXE*JDtVSyE@5s{GYnnPAex^uK_^U$87`5WN^*48bC2Za~sL#&p2|rS3BP^1RdR)u!PXJi>"
    "v_$rwBjRL1@R`#9~eVy$-7KjcDKj$vXR8#t}Fhz~tAqM7L3a&M~)nXg<u69P*l=j3g=V_1R0&J+p9b%)*(s@f$T6m*-;_9X3"
    "cgyXQv?YowA_XY}#vfn?AaiFoM;LKc&CQ)3iNvESr^x&?4Jh=HXkRzpUFOwe(Xu#yP^JPtS9BTzW`v=fDxA62luDu3#pf_GM"
    "GJ#O!Y>dCk;hil->NU~#);O$&IL!7&QxdFx7@3RWD{-`mw)HTc+Hd2UN|HQE>6f+Lk;R!s!c@p$j5la@eQ;@2YV||KBWhXqC"
    "E~(5okD=r(Vz4UhtI??KUz8RK;WEZP&uZV6`Hj%eNN5T4(%Zh-?u9#q{`+SQJea3V|KlzaPpS3zFD`oMthbC_J-%bN3>5T`v"
    "mFxv|l!)Tj@6P)u)@0$Gf=KU(t)6&}VJlg?46Y=~L(Ut$kULPFPytR@_{e0TSlflqScyN1TO4eMcYk-`H)5-YyiSm|CXb`JN"
    "F`H#-0b2_U64n(p8@IJvr7ynin0Gq+EM?&ofLH|ah+XB}DWxF}w<ChT?n2xV5zq3^bMXFyjQ1n`uXDJCs;p!aT~LaJ2+#|!("
    "Kx8N5D28KQH<~LZ`cKEm|Z4X7pAU9;NwA{1xkEJSUEQ`>H$fM#O!iv*Bi{FwbMebBb@(7Tf*WYO@ZM??xbGlWeCZMKUfxKIt"
    "&v1viW4{*WQOL6_>fLZ&%b3@DVO{AECVDf4kJ6wOGy=FR1Kd_Hn=tV7K8`)vj@JqTrkA&cWtEoR{!lZD))R2zZ+P;##g{l=e"
    "BdiFPX`8;&&nE#cF^MY*2;+bK?UxI!7#T_El>1A`0xXUPT85sC_O$G>7y;U1|$C7;_(N=h;FRS>GjT$=#vq_(e+!d_RPbV1F"
    "nB#D;}g)KvuL#zYRsdBUIoosqfi$^6y*cb1;;gbD2~CABU8#_xIq~d(BL}P@R3_`S``)5Y~j;7X{bt<ZfdOyzM8-t78^^L3C"
    "*R=o8nko^0vc+u1XUgO<!bDr5@|zuGTg953Ok2;6p%rYb5k;irZ-zpLfOQ-rz2{ql5sY~0AV`lDroO88OItW`YPu{)|Ypw-N"
    "X*MAv}EUjv52^mhXEDNo$pTc#Xugl7$)a8W4N}Bo$&s|ezVFb<G;LCnhFsw()Q3V$;HK^Sw{p4x>O5HtXiCc>~e2JIbFKc0W"
    "7Cws?g7r#atOCG}holTQ(A}Qp=Z6$f$sYeSgme>T0f*@H0?f>9ZCOl?>H6GpUQ=8+G_GQgM5b#@$T<Hk!O-o(I(VvVr0d?yt"
    "=_aqeW2^wEZJNfUZl8k=X@3)p7ZmMp{qO&^x<l|TSFID&bJEpojz{*t6DTx8DOla4T}Coxka&(20B*{w}IWRVisbsflz~OBy"
    "T%)^AF6;(D#%SFpa4{1bWY6rPL<PW0fixn@Zc@9@yvKIdU#FJ3fo3VaM&H1@<cKu#~^VGGZo~G4eQ&I8vjH$_&?Q5R$zc38@"
    "IXD+P((yFbMiR*#nl8C~5j^n?wV!Eynrw-2RKvuE-YK?>cs!_a9r9C9D}3_rCC=Z>{acae1>GJ+Y@wCl~!FJoMK`N>+XdV=T"
    "UAMu=9yz;(Xs5vnzc$CjreBI73*(x~kJ-_lJ(v>x<K6=gLxEoeYo~YpaeR3S4Z|fJEFp~5`^bi6$Tf^$?<6tUv*^U(C#<#V#"
    "sBbP$#mDM=BNXD#6q?^?hC}@>0sf1J7H?tJ4DmkoH0`%ouRu;PHt%Z`&O(&J?<hh|_K*+vUuZhcR>AJS_VK3K2p7^c%Y&j%7"
    "Pn5e1&w}=Gi^2}RIE^FHXnu@2ItaIc$T!?7AJU{xP}8wpuxr$H`2%Z4|rEQ!C#<5xF&R4jJypSKIhdoyNNGj4$x1v4#CZAG$"
    "nfMY;%l!ul;H8#8rCxWX};q;-FwtP>5)ugA5v%0u)Wbm?jVZk98vnQ}rJn`mA)zib@90*koL@!+7r8RHJ2m%of1vL|=Ujr0)"
    "LRM{{!;{AL602$ci|T*BSt@WvUj2G&cC1BRgIn8;;%b94m?Y;5QF28{cvPSbVQgw84<G?}W4y5aq+3dP#rR`}RD3YlRT9H2j"
    "(E;SC@n;bZh9GXZecT^beDrJ5$NlW=As{v%WpX{GDo63X_VO8x^4z(#`O6H(B0Bq{plvJz2+xP`Tn85&|<cae;@n!fjUhqBL"
    "R--E^U5R8$R?qCa51A}lF5|XRr*DSvLg^ld)D<{?=)fxtjl&Lqr)P!}H%A6$rVp&{;=kX+2RfpoMCpDh@+zxZt?oN}4~?;3q"
    "hT(LsU*k0zrwAh+Z_OPpE4RlrM)$wJ&Wn@-AC~r@6piPp(S(+$IHe~)Tq;d8g$Bu6`bgZBAcK-{jKu3TQtb$CO))qsJ2k<e5"
    "G`$Am?i2FD`IX?pP2M57j53Ch=MIx8@aXVhls?Y8c_C@_O`@>-u-nK)YiQfY1)6CcDIj`P5XOD~Db*qbm-*w!-b{<#lkVGfE"
    "1NWz14#a99fFl}2&TEahb&TnxpO1y)qCO`X+s4K28hO6zvK$=j^|6<``^h<Q}2%4IV66KFsgjbVvnTCRJ(f7q3lBZjL@uMY}"
    "T&u_AMD0-3YVriwH<V=~WX49^iF_Mo61Cg>WX^?5@RZjT*KpB<EuOiV*2~D}+%RnFk_lgn6TKA`s-!`Tr20@vE+%_FPc8c3J"
    "GgfO`Bnb#K2cdGn@iEODD-J{U-D1uVY0kA{O3+2$g#J1<VPTMxD2&zw^dfH9Bd-yb*`2dbs6jsfAJs1N0Gcdz;w`p+!+j7O$"
    "&SsRSw${SJG|uT&q83#dTkq$0V*{cBu^%8;mePZgmu~<pESz5v+EZ5@9#~r%1vXtQ<`OD71qvLcyZ_x_j3A8AJjw6bQnMqj}"
    "?sP)`00S{TGHexhP;Rhwt{^!HQUg@FjiLED5vy1SLFaVKf-qPIyls+^?0{-7Mqpmoc~TnS{nhv*B9wV9B^`f5yt-a3&0mQBI"
    "=6+i%eQnn%N%KnHIIMT{Tp_ffT=IjvW-&G8n!eL@vFkKb-IwM*zjF7|RC4^>?q2)S%*M@f&!2S~Do1VbE0@ObjL%oNCf=(L+"
    "egGcHL{!MJy$S<O6mC7+Dw0|xS|NeJ}xgx@5%n`VE3Lx=5$c>GS#d35woj-CMVC!t`MEfu)^YH)x?gW9oQS7{}o#$NAdimf6"
    "byR+dOuDQq!ptkkp*xYsIQD$RpY`c)+MhVL<ubCxia)kU0io-yIFn;3y#JP6GT>XBG_~RL+vF9cx5@`}jW^U43V%<#0;d*3Q"
    "2+<N874JnZ=0zdu%n4nBH7>>S5MziAyf8n-W4SH{v)JH5%uJb*Ar@taitP)<<kzyv@%hSB>aqYM9}iEcin;<$X(p5`GW9qVQ"
    "f7UKeqlp3)Rx%Gt-b0H^)>uo0G)pOa8*{HOBHVmw9qUKt$KG&{D*lCJH}UUO?2jt*{zUJQ%<{1RC6gmL&KUg3rchO0T{1bY="
    "%o;u|(UW-Khk1b*u3`o<H`Y7}9M-FWos+h%Vqt>c{o`t7SKFr(u;z$?RVUcZ0HtrE}ci&*<Y79SNm1Gxcj8pP~&EM#S<*V0D"
    "fjN@NM=m)KI$qt*j<*dTR00##yB@AXVEC9kPX|*5xC>*f&eo;Tb?W`{DpZfUYT47@<pXW!!2Hn34mN5!6UMf8XLnzdh$a!a)"
    ">po%eRxSoadhT|h%eBV^rVUo%i8|hoPu)m9Ypb^fG}Oayv4rq&oo`=#xVz$A*Pdz#YUZ9OA+ZjRuX)h<7a1QfSPks_2Fu}7T"
    "(7<U{iJV#Gr?@XmW1~n2z;7k-~N#9>&i%Dv|C)au4XPL!g|n-5^VJq`yf}V^&#lFB2wPWNICc6^MQn*?y*NG4&rj#pZwPVcO"
    "NdX1Z#STb4onPC|R5#oumkVsJBoHxLF-V5(I3Fwj7*~xfBf8d360xjJVp?M{66Jt-1YtrDk(z4f!QcEL^-~=ht2)2Zus1Sgo"
    "+Dj-s=8-tQqU`R#K332Igw+0MZwu{{2H_gQ|llWehDy$rEGxQ(nn=mVGm328-qIfHl~<{0^7<tbQsLqT0`FwJ83J(6&JvU9j"
    "aBE;}5hBm=PX8!owE}d9)qu|B=B(zq;2L~LZQiIQj#srVoKiaZ?;@Ld<#vEN|bg4@+i^vAHAKzmXncsG+A-h(lx0ELjj+r!6"
    "mCZM>T~wM~KQ+5Z`912mQ2GT@#p#4Drs3G!jtf|2@4tvJ^I8fr&V8d0RRIkFGf~2HWSFIbO|hJM{(7PNX5kKQ<uY(tqTs~gH"
    "hj98N%Sb$kUQfOE?qK(#)r~vKFxAV+Dy5n2Bc%d;|N^;OHQug&t#S+@QM?5lgw`X>ya+-HEZVrNxaC)RP$Lty-$H?2>Fj##`"
    "RYaNU<aK_oI`iup+Ie>w+sQ>D$>iRMJ6}!y772PbCcDatujW*uQO9%@!_PBW<@tT3=}q1YiMDm#6k%5ut*SbMr?$LuBW#4;g"
    "<TMO!pCDG1IB)N(1^!|<Z$8V@L6uLB!)XhByX4;Iry|CVGd6crqLCKi`|r=5-}(G7!kl1QgJp=`ZIg#HeD%imX>`TkN)W8`&"
    "ug+HAQT>OIHIgp6`H$ToE_lexNNO~cf2ZjbsYpmB_l-e;I5h=drdEMvk{?*5M(B}g~Yyn0-Vx%yTUVeIz4<Z}|$SF0(EMg`?"
    "odv_B7k?)&m#zKtvaDZ4T<i(e5wraxD^rUA8(<S}&g%ohty&oR-x;D-??L|Ixm}~T{<^)+#)%2$@ozqmPp4(tdi@8$qDklEx"
    "QIyk=b4rv8MLzIdWp#`T@btX{Ww6gt0aItJB^K@l)aG}Tf~a7BId{M71e3G!lC<jYt~xcvsd5nD0v#NK!A~7djTv;07us7Z$"
    "dD6GG+wE2B85C!c8qdHXcLF5r3hS-2qDU^8KlGZRE?`BAbP1S74o1i-$=`NkY=WVLw(bcOUkqPubT5oz`{dt(^Tm1fM<T{Lb"
    "ygV}9&V)~Ca5uTC0yglu{}TW``uxMIh|@zd5gl|#qmm^CzgHlX2RloZ|Q#G(U)k8n{UKwe8d*>-Ih*dWHD0glRgCj{pTQ-i?"
    "9bGl>SsheV=xe~J($`JP4D}cQ_$-ye`3^Dcu;lF>V0U8@I{w}qvN*29teB3l7AZq=x3cfJ;gbhcA)#Q{-Ef(wf4%I6hlk1IC"
    "T(@g7t{<s|VVjevB`SF^7^iBTV{kEthN_}pS$ELpxbctlzLyD$M8O}A3o-M@>+IdoPlG$_G$B+|4hjuoQB!D{9bV4ZljH>Nu"
    "+Om@?4zaxa>m-Z(P-nHMgeheRl0Q6ohv>APe0*_%V);lMM9pZ_IlAn1>@HwuTvcGCb?qGeEGvexZl4eUo;xb;^L<!siBSG2a"
    "T0zL{{;8MW<o`nizPG|GY!PsjBSXoSfJeXku(+cHR;BNFB;wxJ8iHc=EMVYdzw4P5h#%7BfSwY|d^TzE!rFYuA=Ot5sH<{n+"
    "k}7x?IksFP-@lB(?B8Ru$$`P}mM6rZY9{ixTU?z!?>7?y$hs1GZ5iM{^#x|#i;KtL!sM|m^$lHuI4B#Lj8FCE}BDoq6AB$}G"
    "<_asxk>bLTWJ}9Tjc(fjUWO#~O?N_l{^p9y`yMi$rkq|Bj+G1NZ|MZAKArRquw6~%=!*Auss|s9>W+{cTP5#yogqExP^VAmk"
    "bNE*hQ9nL0Gu{d_O&c%b@9^-oOvxN(wI|l_2Q-B7XFfZNVP9wVud34x&>y*ReZS7Ib%$?-2_~=gYt2PwS|CkydcBfOj4n47l"
    "^1>igDmNJ+Z?r#3hGL&KJU%hQI#65Q*$&+t==$eNoF59_w6DwJb!|-?Hl8gwVig|{L0^l+h@|OTw<SqztF%J9L(phd-&6p-)"
    "iNijuIZUNOo)j*q^^5#PR8?0=c6_P(M$-WCG+rP`CKvJy!d^*1lw=YEo1PWHeI8H!jN=co3}q^*s_piJU|wR%W+(YktA8b!2"
    "2)hJ}`!_}rrlfb+H?X&_`B3q5!8pZ}T4GXsZJ2kwZ=VPJI{O0o=`X#V2}5e2(gtMNP{mERp{Ym73U=-_U<eiuHCb=?y)$={@"
    "HW8<G#RM0TeOPlWDNJ$xYcr6&{BeoyczpGMGto2@zc+qc$zCakv@fPu+Er>pw3jOF7WJVt=NG?d&*k;*WYWhbX;^{=<8`7A5"
    "$XC?mE9UA7PqRFNVgcUtCtHnMTpjoG5a({ArzvBkjUkb{WA8V3lx)TQ=qH5?yl29d=k593As?&5E}uv;i(zD~f4mmdZYNCe>"
    "2i5$HgWBtK{A?tre@Yi!)QQIHr@>Xv#6CpO;!MaYb`=_qbxf}_m~k}^VfNtzbbHc_5<4JlqbloO#)JN|Bm|uddK?v2=jtmhe"
    "XO;f=UMxk^_^C`Wc3RB6r60rkNUH>$AGJ>ZE<hKDIII)Fk^@p}$|ANPJ7tjk(hWVaN(eysN?G;H`1ZGawO}=SF$>+sgXcJv%"
    "(J`h2r&ky3Tx0N9!IXUQu^%ieW7FjK-}phF^>mCy`?G2KgA6*Db<rz1>B5Rm9;{9l#@g$d@YkseLflZtcb4U(BonlWoh6ny-"
    "ms4bFypMy!*FC7fYS)SlV0e?WXEqtT-0cZ1~9Ab6HPP6hNfXc5TP|(D~?-fi%*^M5k-9f5ek4^D)ML`)yWT{xRyVyn%gWyZM"
    "y*=l`{Aa~8`?sbIn-<%KS9C|g=_iYzXAuq<SA7J=7QC-V$F?~RxM9?ovI%;#c&Ww8^<Am_y}0ohnusN~;ZJ%|0-mzK0g{%^D"
    "OHOYH;r@0B%M}q2Fd#?l}@$c_;?Net%DUShHqop)dA_eilWFOoXl|h+<h%zTr1sknP5yju4&j|=*xIFU6tZMUCcbs$|bU_j?"
    "u{0CczF%o9xYCSg4=TfjYn4i#d3a$j3i$j{I1(EB{8p8AQRAJ{?c&!xqFGRE}G_g^o1x#OFy@0}1zTr#G_IY2=QxcxI1~Rrf"
    ">52`s$D!fA_VQ`5SlTVD8c<oRD*uY{dkMCo@(8f_i*Y3$-qnP5Li!6ZR!i$f*FC5W2^!WFF{z<{=efrXr650|;+!vMtUgpT+"
    "PwX@itW={U&obO)R1oj6k7{Z|oQZ<d-K5buuLN)WrD{eY!r{sdL3(J0)G=Rk4thVaRBXsZN-cw;Pc3A}NW*>T#M<ivfqWt~A"
    "khmHy)B=qg5)=7XKl2AkmZVJ)Ol(7v!2qVfJn(+JL9g{WqbH#`@D8{deXoGtPZny16Ar+TBQ`CaJBM2X&pE&ks1N>EOAV3p2"
    "Y0FPs%@gjr9Zqgs=-Ggatp*uU*!GkC#)%^QB~aBK2Gl5j*=Z$%4uP00}O4jQ16>OIv8EoE>z5rC85e1Qg^Cg*D_p3H3v-FL^"
    "jqX5e9`F)dFC423?OyvVLYyG<BM#F~D7`^F2dAR)42;qd@K)-mf^&()96xzx9<-L4q*11PL}-L?rFw<r+;ub35AnjyFFh*gl"
    "e#qjewN6mIuu>xG#bg=>A(O}UHP$2TyIF3xw~Izwj1fp>u+AteIA*2=!-ETKF1Wm@}wS?aK(_Ws=Gn&dtEEwJZJm~rSuTM2&"
    "_-YN+%D%`1W^t<;CcA=|md(d=BD4%c^yv2lxaN;?#Dsn@~t9BRM?RyOEK?CkQ_@-9n9X|tralQQdK(<AhW=l9UgH+tv3+3cU"
    "V(mDS&fS;$Me<s4pVf&q)n)RvPA>4Doaoq}x#Oqt-~P0$Q%`JNNYj_u$d+m}LQ<4}BNP9y0R8((0i6?ogm#|29jEu_<gs?0Q"
    "05@A20pvXFMuFHQaC=x-^1lmG~g}!^#Fp5TT4H2rcBJ)y!$f+AZk(9>n2LAIODCD#k3kq%)E7hntmo8p@8<KDAzJRuTitBTq"
    "7d=P`|Uw1nll4H7V=kpuh9ga<vH(8AxBP{+DmTV+$Q_@B*pL<2YKa6{Xk9o;Om1z6Bvph8MA*3uT#j3JnudCdW_)lz)1vYmv"
    "+wGXd`&SIof&%g^!<$!UF?m|xi1gSeN*HWX_2On$8X{MB+~ubVB7P!B*n1gj1#rMHaa9M;hOmZ5K`!>ft=V51Gq&Gy!{+=n$"
    "q?k+6)0z<wmtlVQzX=kr_Nv!(#Bs?^kWJ{v|GK|jnrj#msDb%zne!Few_0myWTJ|m98^?xN2mQ&%hiS9Td60kChAD<WsY9YU"
    "rQ^$@;-Na~;5P2~#@meIz~Tq5SC=XAHAqtNj-MZReZ}GfSLPrnQ_Rh(T~2avk#r)XsK(`qF}dvVBxsl>JOCbJ2N-?}Km_V`R"
    "P$G^RN8QX4D-_J;5H<ZI_W)UDLj3$kxm$7bbEIS@zqzY?2c^|&;<xUs1SRJx=`cFL5oJK=2{*9)ArpkF9GamMbe#*VXDGAD8"
    "vfmUfDSw{Q;8~jbQfN6-Dx<AXutjYr2$PhM|NA=?Ok+dNR_LjgJVKk@Xj9B3}OY4N~;PWfa1B!(in#7}Y}bg9GirAEUhin1X"
    "-a;r;4>cB`f_iFx70RTY^gAN1AWi|F5-)f4s&?QSam+h_h&8XxV}qO7CNn4GX%9jAdrw{J^$!5?+<OC4I3(t`9qCy0C#tt2!"
    "%ZHKA@V5m5~lBp)&zs))A_`A;{73M>}(*Lbf&!AEVtn@35jGM%H+r)3nU&vA*97!B)To*Q`%PgkvUpDeBK_Gy?^#`#h@$eKA"
    "c0hQgMc%2x*sdRqHrHd{70vV9KHbEXEgLI`M6l@}Jw&AuonD7X6uTJ)uK-`Y^_~=2v1Y`;_!qbhynI9$kRZNP*ZZw*ZRMr5{"
    "oDL56^!I&HuO2v_V?BJEr$BXt{cLYZtjhKH5!S9h$MS;hGa2%9yjM9$wC)2w^o>H-;IZ&^e8I8gBKi_Ego}^0c_m(D>w|$hr"
    "UJWitqb1q=+hvMS$ZKWMJ@xk#sAE!yOqU6ms9I0iLLnQrPc5Z|0b*5otiC*Ae|d;!}}EyP0M5Ko2Z+2SabAFWLQ3hB?qM^L+"
    "#wQk=0Z0=h-xQ@MV;CKivfw*NIG=J-_{Xq&j2H?r!~FSR9T<YdKH-I6(-RkQJLBu=jBrTbojO-%!bSR&(Hrt<u8s(o`mWI5R"
    "I74mr4uG4`r{wP`uVlvZ~NXLJiz9}-(8*dqDwutuI(GH!3*xDB=_xJAvf_ma6rn@0^^swb4rT+piPe9co*RjWoKGK@@Qo?pi"
    "@I7LGJ_g<r-{U|S>viRvy^mc*gogHW!El^O%!AQnwH-^n9!Hqo?gwgfS)NANbJ|$t^!9)?T$B7MIUVl=8->$)^?(ZWWRG)2j"
    "q8c=$}&l@py8{yJfjW?vRZFw(sw`4ZQJ_vhqTT5dH7<P6j1}RZibh$YYxi(Q?r+|ZS3GAF%k5#(brmWc;N2G^IvUKSF)^L9<"
    "huYFY-6iUB(H#=%{@ZQRu==vL)WZ0%v4MR0cUhe7^yubZ7<zrNTQ&#{-U--b?5_?NnJ+YKer48iFEvfV1l{&3KLBy!Ppy9zM"
    "2z22V^tJZ{`Q{@wwg^UrOW6K+p9xaP+b6$s!r7H(<ui4fk<R}y0SN4RRghCHF{FT)QH>x=evU!l*Ex|5gJ;?U}mycX}7`01>"
    "s$f-e)Egb*-c}WuoVI%%QJ1xL^$$EOlCYdA?3$`A*sk|A@5+%-jB^Xkx5f<)NQflq}J@EG1ObtHRZ}cmU!wt6>CVfRdAj5<#"
    "f$Oty_Vqd9(5|!O6yUiqmD^wjiEKx%P$TM=S6!>J`l8wB(~DtIF8M0~3o|3n!?NELiTMvGOf$_6jj?kLlPE{!$CHst1tI%6E"
    "<ip!q?Uuc?d*;sI7~w)treK#aXJ*6AH}#V25Nu*7b-^ULs~W&eeEzTqVXhiZ@;O*tg5=#dxG-fWsOchcG|xSe+rtMQxSDfzb"
    "HBqxS<JnBNUb;ja`ps$)FPcQfrnjJP`b(G%oK~$dXFn!Bg}TapR9U274iDbWKf1+@7a4Wq}`9bNAZR`Kz>KvGY+aCx$p0FwP"
    ";Cu64<Ljw*CygK!2=g_h~-1qr0-%vVk=S&O&Irrzj|W1_&{-=Zg*_7Ev%G}qx4m{dby;UT|D>vI%1+$!rYtkQl8xDFG~AFs+"
    "ILVju#Qj=NYS&RITTu>Dw)<Xz|Klzy04#<l93}42gd-MJI?L>5Qf-ti<O|u~~@7`pt#2M}JwRm=P8W2q4I;mH~-Hce7(RH{s"
    "E>uMosg&su#%gcnW-w`PUiwuzSB%TPM?y}XWcwX3n-b4})5!m7({TY&3_o_=4L-|%H;{#LaJ8%4G56=-1H^bo(l4+)>}PRkr"
    "gJ*wp8?93f%JeZx=IiV!pnMnhy$Ib?+KkX)W<Dmf7%t277}l9?gCKt6S9T(&98&cc>!K?wjjqkyZF9|e?6mG-dpbqUE8t-)Y"
    "7pRr9lck??zoxCLS}$DO>`on7!Lus=;UOg>0WHFqByM>Ef0g9}SznL!ILDHRhF_(mZ7=G(Ht^i6Pv-kZl@{?AYBgWtM}Rt$G"
    "liKc(zlVVj1R@5)$q>Mw(;=aUhIN|SYK*G=!0Iq92MkaAX3&RMQNk%Ed5UI4fs0GMVfajCkO3jnGslGhp+k;TmRO9L)F*C?v"
    "$-!)*p!R2Hn>?)26J0=}})r`hj3cyn~Z~V8_x&zmmorTEr{%Ct$i3cuW&e|*q;O+`aC5fz?RnJ>VSVAYaD%=LuHdKD7=~@gW"
    "kU-w%jd}U{=!0K+<STu%E@mbZyTs=eZx`(*<fjI+Y`47LpATIOmueFLpNCoJbM$!{r<0O4WC(T9bzMpB9=SV5JJ24q(H|@aE"
    "kOqZ!mbM{w}8M;8ZgU_Uw)5Y01RL=bmTpm1ZdTmn&DCM<lu3!M{0=3S`h{n*gwZeHx|Cz(i1Vu@4^05DnsIJTpgf1zEcwUu~"
    "tmM!fQjGosboiy4RtGhW4X$5>c_3SZMpFtRJJv-;Hn9Hbow<o9lq=YC$zk6_DT-wE0BSeOHwv7;#9cyWo$qysAl<)Jn?^!i%"
    "mA7V+w<Yvm>>02UOt=vJbq4#>54D-o+wt(ozIIWy|KqM-9SAGjCKHf1Zg*cunNv9mf&t6!r<hW7qghNE1Xo7Z(I$Y;H5Q1-g"
    "`yYf@zie>f4>;p~$alNeoR~6*7Nb#<XR&=|C`<x&f^cNm`6Oa@HP%nX2`kn6a5?MShjmuU_i`;xYi!}GeBxejY%H;=`eFYr+"
    "718MRm=uZW3AcX8u7Tr1pG*31%&D5^vHpbLVZ_u(MK%wQ4U?dCGgd&NTZpfTZ&8l=>-UR!f%s45;*mlbS@FK@_fg^zXQN3jZ"
    "X=-vfaU{{z#+lqSl2+sMX6>7B5M@ny;nsCK~v$uW^QG}hDh>3%)!G!K*k2*%gi+*uZ_)bYBbkaWUM)yHJAle<Ckx+k8EAA9%"
    ";*$Kkf<jT<^OWDs}Dk&CS88fg4Spv$-C2oE_`w0cp_@EY$VFWDF$5NzN&tq)6Jec;@HrgZGki3Vr1|TX!nsg&SSN6)30p0^+"
    "U`lDnI6LyYmAYCU05H*Z@Wc1^3b4{BP77ixY7LOQaSZwuJ>V#>zgqA!$4;UF@n546rC>M~VcQrcQ2_d@ym?p1t_f<E$b=9W1"
    "7I|5}L2)Y0J-lL)0&S3L7SBqy}zcPo9A(4~4(GCxj?7-JkH-5p`?9&YwXDJAjcs^bGmh1xff3lFif)B|*YL!Q-P4RiEX4w53"
    "zrxv4iHWlwVhus$kjOSRiB|g?hW|6fY8fs#GL26rdVU;Lidm^|vaB@_*kr}o{sv!OON-(6lOB+nmfqBMd?%I40`?d{Yqkf8{"
    "C^RQznGxc4BV8AI$jT1CYP`m(I~dmZv1$B_4^(TaG#|MLILQK01^-|Qx9k}K<$qp6<f61upk-=^nFXvW(&`NEQT{W$!-1Hsz"
    "S}Ss!vW>HTCgZk?vLv3xSa;=1aH_iJ>7bA8P~Q&}3ZUIO5wsteCkNH1{17Ot3!N|C>o@=V6gweF>3~fMH|qD4Dl^t-TlwTPa"
    "?Y127gDBK>vI?buX|0TT8#-h`hGQbEQ&EdyLAzNxtV%Gh7JfFT<`f^cwmG=K$e@opb3Wq<=Y`?KS+J0%o!qsUiEn3*K%2Lr%"
    "93i-f^=O0cK#YObM%ME;D^tpteDVnYgd}%+-JY@(okUZ=0pz#jXVgWL5N&|mBOU7ZcSgR1TOz8rTn)``LVoQo^ddGraC?K7$"
    "9IeIKqI~}H=sGLwAs)9W1~c&ASsQ|}%CytEix=zBx<&!IqD|=H)%<N#c#nx6oK&PZA3x(1D&|e>bCG-}>z*%%6Kgdf!K%{pD"
    "eB{ev6E`?<tp$movWhXONwJ$j(fE!)uq#dLs!{uN<P^8k2{#1Ihfb{jXT>Acv%m{_U}A8d32J-+mr(ZzU2WIxKh-6CJk|Dm="
    "<6!P<)s5MZEJPf9Yeh81q*34<ZsS{$zG5k|zG*(*XDtum5Zmdq&WQT5b>T$+Y_isKE3SDc$;eXMg?&&I97YFBg2>;rG+$TX{"
    "&TBYoeucj3ACe^O*NEUV-|z8q?o1o2s)-YsQT7I~n1Kox}?-(eCgfK!n;yvY}cfjtzHb~8{@sDpFV{Z_Q}+$fdSavk+K<*}s"
    "rEH~rMDrQ(%6~;@}4SSo{i3$jS*pdqHmpCvrN_E6OI0zAG=ih6p+d@}JMP1PkpPU%q4&<?%lKe(L`FDI|CI3S9;XM25HKbTe"
    "=2Pghz26@a(qo}Ni^suzMV#=UFHMvj9JGsYfZQU{)G-f1UU*Gzh<9VnhlT)ZhBm11^bsyc6c+?>E}qTi2Fc8jFQ(=GOL>fq%"
    "Be?g*0voyn$y?LkZZ!8@I3|hFyyNbR{TbuHS_+C#Oy2*vX1_Ht;~Xd__S5GYc#6|XJ`<<NK&2*U^6vS5GM5L3QRDfB#TVE()"
    "j(yMTM?G`8(UKL7rj3!$+l>yVL}kyhDygtye9jq5-*0<UMnX!9i$N(f9D&;8J?~RG+_}aB7Afds1KmJr0JLt?$&#skKQ?v<H"
    ";2+hghvuV3~|{5#4d2+`1tf>WxUI8gpn_NHi%o0e&xAMUtA0woBvDNi;I96BmP!1O%amH!BpWK(yXU4^(ml9?!f<bQ_Wn@gB"
    "|ZZ8oQJ$^^N_*`8~+-#J~uqOG5;PJK~x~AZ}l%`&uK^q2Uaoh8+gQUZJpSQy4v=FOPX}@?K*k7g?KSFK{ilYu$`Ll0rnxxkO"
    "zIEY?=v^ubJUi0^n4W|h7-(^MjuY;_n8>k5&W(SLvK`glXK7zd-ClDf&!2x=+}0BQUSj>-c7hERFT8T2eP&+yji;_<qnsu^7"
    "BeAX)v)?PdK3;@#`TL08-U?$VUbE!I(SjF-v80jk;*x3ZhuHtoI4tQYgl?tPqC*9lb&aMtE??w5gLY(<S7C8Y5UK^IEY^)Mp"
    "OgQkH=&*Y3EHfB8M@qjgw@1@ZQNV?>DxGzD*-dIL`#vR?`OA9NnGZ<T0M3+@VfS_yt|(h-8?}U!|pKm2}Zpq9>-#>m^z*6;n"
    "MykO=5)LV_~-^HU`5C?0Qb6^f@Ti@&%e3PDR=T*ed(<CqxpH^%3s_yY%*n^Ns(&Cb4VkU9yP3hQE_;js!mEpC+7jb4jkB$+k"
    "fnun(KbF1oRzW3?WA~CJ@-0fKJ5DJR+e_}C3pmVy5N<MxQ1wv52z8o~tQKP}*NIx_g7r%{C==x=_FYPRh?WK4muu;`*O+EVP"
    "P2}+FX@Dugm9MwvcP@Q&7wpKN`cApZ0Mt_K=wc2;lQrq2^O=nQjUbqh_rrTko+UZZ$)~oe#qEM^y0rrm-fgizM<dOy0N6jr7"
    "#(XA+*YVPb;iIT?*YkJG?l8Biu~=8<>#wG6!vTzD*a8}KctS0Gp|g`xwcwH^>(VAA5F7Ysb>=E6Z+yD$+wHDLXpd3rDg4vcz"
    "t|!FRs9vQ~baSmndJ`;nfFHOhZxrR-{H=2w?Wym4xn8cGlteHhWJJ85<h(<ty*BzEv!nc}_ezN&L1!p-LVsOCkMa;VKRYzX^"
    "UyDZUnq*ID#=k=B<%U@A))NGW{;N=cN6q0zs?@GH{k(F+xoocY6KOY^0pLE19HtGr6Ark}p$X6LZ&)h7%CfoO9$134*TR{uF"
    "$)4Ju&_~l!phUd*V?8^^B7B=~Buu-p^9u{58(d-IjLc3*V@m)%6w}_i4ABTT%XNiEYieHHFdSe8p!Ee!i4sk?~nq<-rSTV(D"
    "CzNJxc-~YB0;b$Y2JkH2MP>VarqMaO8rZG`t+z(B9REd09FY~P;??$YF=|8vs;TXq;7~%`3C?LYd9kgH&u>ojc09*3&PiIL>"
    "Y76@f4;jtqHI6iHeGM<AMSacse<}|fKM~eegB9h&P}7rL+SZGJRd>qcMKXcFn}~@bK>zL`R@4+&3Gy$UhubfPe_f5Fj|GYLW"
    "jhsg48F@1q=!g?pqu{|LtvdJJU}VLeA>_2yhV0;W&NRpwtq@&(aG!Fn`GKf@1Q;bAtOs7n<;O+f!`NB`>+>UnM~Y8}Ap9+N&"
    "T#bvciFrd|>SU8SD5`#135S60a$q=Kiacj~7;B>wB)9H6+v2i?fMgNI|;#yxc8!wqM^@@Dkl-1-`0v@KfaC*mrPU%S;h^yA}"
    "jU(FBvJHIqjxG@P&T&ac3x`09bi^^2>ko7<}Jfp|l?CT|ECKQPp`b`J@QXe`sb^>yT;k3H#m#mBdoV|updVQxeYXc$8)j1wA"
    "5))0D!4D_z$qa%IA8iU`jAK$vZ>gP!3p=iz^k8P6Qow%D_u;UsnGlTWULlRXjNcDaPV^tQCevrkw{A@3;zJnGNVaxww_^`Mk"
    "a{gx9BiP}jn_#gxER||k1)4mFOtjz)UJ&7-O3AJL6Uj*1DX`I%omTjo(CJXZEwTAa}MwNas84^$J8<cQYz#fLIZM%oqPxQw)"
    "wHgvu{k^pS52#P7$I0+4UoIA7QNs{z7Rrhc<JPn7xFVDt+V-3c)J;=bt+qRjEYJZ%6N(E)g6*2g)5j`5CR-8}oizDf4npSy|"
    "HL7j@5F05-9g@J@Rp#PqSwJ809l{B8brNj;t#3q=B<jjw!gsP&eG!5tx5u*`DrNdWE3em{-mj2dH_m2~DcyJ@#vSATY&I%&k"
    "GY7q*JX3EE!&Q&=m$#Z}YKL%O6P1l5}y$l@KSWAz$7Ki>^=*iZ(kcH{zgz@nzjZjuem>3zpO_Lo>Lua$kOV&DtHFa+)YzU=5"
    "5-U&KT6%q|XW06>T2u=Z{ZV}9!AzX?7U=w|qn6j7Jc#m!Z!!8`it*Pki}Oe`cd2Ui{c#v{s{ZFSS7A8q1d=6H@`&Um0PD5?w"
    "Oxs5BGWMC(|N&$=P+ui>Pxv0AVK^W8r95@A3IEHaqqmMhtPn(<s$910a`Yz90!%=AJgx*HgVfS7qS!rO@RE5WyF93eZ8uQY0"
    "4#P)T!87>f+s|<PZ*2D(O}=twI0`i^~||{4Dlc=kj_m@ohlX{-e(}ZkflPcqgMkOi5A9(s7ZwviWz-!4GYX10)-}LzW+-scH"
    "p28|8hQqB2Y40_|_@Fc=`I${_`}koOgl08bj2E1kMrd>JE}4TYMIP=Ht${btN7Zc=>`)v_t+RlghRgBq{n$=#j4#nKO}s7F~"
    "Sme{S6cH4L3#%US%f<b5|uNPYDBo@n3o8#c$UKh0XPi*y9{(k^pK%l>8cAK!3K;E)o>i~eB?bp@)qe}lu>belU1^xQH`hY)w"
    "GJBwF2|&11Ae=vmmq6<885a~xJXR@83lFzjb$q|x_HXi=fMn2#Xf=3YCR&ZuZsnA&#y7L~V~0#(T<@_S6~b98Y7^;~?%#c9B"
    "I<pnr(oDH26_t|g~e^(lz<lmm=!*(yg)S{;5+Ra-ZXX%4&3t%cr!<N?yq@6DqY@(x2BHaX-*MaTCS<;KWb+F!z$gn!>#Fx;7"
    "bSby`B5s;(ltG0Dv;-z46w5ccFoAqKZFkToM-fgHHKp$DU~I7*%k0;}yjtcsla9R^&0J9Fqy4+l9q*e7UTkenEiMJx2!t^z}"
    "#w0(=M9Z#VFY>=iij&{w%l;2KuC@JZ@V#c@0>TSTd8qgs(DOB-d|22623JzJkx?iei{(QyE?{a?~474=Ile@xZ_NG=ITW=r;"
    "FR4O!NfRia7A6PhvKd7aE7I&f`S}hI&h*m3oiTb^K1<%QkV24VX?U$Ah0Q6)6#EqM7K;w+IGdc}*wOz58il-9+0tHJ46-=R?"
    "sAHylJd8F*ha9Ae0v|d)iC@=Q+f6PBSj)1*Pf#CE&){n0Fw%BVhHaK!hW`!!woMcI(K|s}eU7Ex+7kVavt$bJV&;H~2LAV>i"
    "Ep8X-)>)lX7wHb6#&z0H;C4(ZOSfQiZ{9Y@qH*^7t$DoV}gXe**}BzELmGIJ0L(C%4`>S0v>!Q_yRbd_wbSG3_e`9pqdOiuP"
    "MbLwd;!S!zXHY;qh)BN2l7R(4Rh5@+r5|e=u|aAg<{r6?_?H8!l;6PB8$mSeGJx@x*QcT}vgS+qyCZBu)qq-|(w=cD)45f0y"
    "kN(J9~wL$q3{Eeh%q{KME$JjpF!NIGVXnweSYJ1H_a0N_QD?67kCnVg2vdc0&XT?Ykp;~iJX)v*9b9G4#atU{@5<D2y=UV;l"
    "T^T=&zRJmo_+A^ZXwq1$e_7CBw(!;Rp0z<HoF$4dw@Rl0|0rZTU?nI@Q1OSqi{^Q$|Gyj7+^vYEDKL!tn(88CnfIq44h1a~7"
    "1An6R!W~fv&cpv2I*A*Q$92eK0&Wy2>=zX5E*RLIEtJe!>z7Hic%Qx==`9I0T`xo@$xUW`{7r2J@0rzYQjLW|*MQM|SE`?{P"
    "vYfU#!+h7n40l1t{iN2QepLeolYpD{(~-f+{psyUB8dhUjh&Z0L;tx1_0uR#Hs)B?Em8Nwjg{wAX@nI>NGy6<I*0NqY<471^"
    "|do>5SQ}UNzjr^RmO(D>5jnXxpVuEr9N={T6Reu3-xYXNxD`8Jvcu52mvK;+N5%2PVMaroz2=+fwh-E6`99Cw(8;j6gAG<3Y"
    "6X>G>Iau&@V5@B1pR1#5tl8B;?;*WzvM`%T)v<-_bep*!wj_eT%>15=n!2an=4n1hmZy8{6IEOw}LC}A4DDe|Y+`u|b-224-"
    "i3bZH9Y>R6<@B;3uOtdaoqY5&QZ23z3u6;YMLe^{<ItCX-==uQmlJj40^w+(eXe=zsrdzIXu~F~fe{t)<w#iBgw-=m*XX@oV"
    "kZR$x%~||WGY!9fm~G8t#3}DlyDq&Rzcc-9+*l~WSr90BHhfQoTl~p*`@ZC?d-UfrlL}FPqcfSY+8VU|mqO}F|KUr;wJPH8v"
    "E1t@v_yc1MGODdn8&LZMgad|AYf)1(W&5tnCMivqYCN0__Op0JR?`agmO_<&SF8p&KfltwQ*5n+L>@s17>GWQ*y0b{C&)~RA"
    "|Z|O49=@ov9G*nzIlDaBTrA4>SrA|6W_b8%M9j{dfE~P(8tG!eeGcjcmUj?`YkNC#!;4Vxnj5;u$slht=Kic;koO8UI+n{?l"
    ">+0o_@zA~1u0UFh#SdV4=_H@wQ7daXZ?2cmUtM8Vx-Y6Cn4Ib4Jcw!p<OY!u;k(y8^ZJ-)7(?bmv;iNb0j$@`MoMDezR;cI!"
    "FKmyElrJ*y>G9Lb}Ig9tBjOxt2yskWoTv1l}@jZBjeFD!O9mY<PLaib()V5JlHf$%HEP!P%4)mjbL}%vT1O^iAP48@dbaR&#"
    "{>uFW0EwVO*XzV}0whjaZR{6K{HVVdwVB)DH)fexLUf9F5hglS&URHCyB?pg?!paD9>unetR3x<Yog;}cgb|7;wrWsVFtiiJ"
    "q6>}>)n#DJ7X^K?ZRM14dLFoTSi?xBHH-y@kzY1k%l+T8Jfq!=<Xj<pKc$--gX9ADKKm*{V&d}h2oBOuij%S*+JJi1G+$0xU"
    "X^;P_R3*b$alB1Rice4Zn&TP^;Yvc*g)a&-Q_6!#Gdb#jEhg?wxo%a@dVD&NBr?7q2Ng2;l1`&fJ>JFX{~;_FFoTyge2+LOK"
    "&*9zGVb5?}Eu_^qIX#`K-MzC0=lsyu!v{<JWKXXVRiR~1riVQR``l7o8PcS%kp7-8N=uq5*%kp+;f=AYE>u!(hVU(=mI+55n"
    "F`$1jTC{SoxJ`THWe5Nvk-&xS9|3`#CS%qOL7N#Xyt=>E@B3g-mR8(f}!k3#B%prhh>FsfXXsz7h5&+$3cGCXCJ9?_vo~8az"
    "R4G^L*Eau>FCRDRy20*lyz|0FzHQ--N9xGb1m3iBJ3caIVPww}SG$QJoeg3{>B0Ypz5B4O>7pbplcwvMZg}z->Fs<kciYl6y"
    "n67jFZkxTG_!PpDfD*_n)osn@XPh9P@DNO(7IP}@K3bSJR*Y19e8bRFTQ{Uv$Kb;^U;KF>Wb*WzlZ{a;Vgeryeyz!yA^In8e"
    "Ug=YYBvb#&NjVh7<}73*X}w@Q0}d<hNX}Om+gDJMOT$@bN#0PY%!H2XbZ1&jd)-1hzUEWTehqObh|yV#Zy6k?`*=gn-}aUnC"
    "|NR{HC89WIG4lKqn<i`NqUB}>8c1HiEW{ZS~iY=s9^3vaUbnZbYjSVohGP7Ti)qSI1PR_O|SIyZ$IQw8MO7K)bJ2>|HSHa#H"
    "M`{;H>w>trV-kIIg(5W#HHk5j2fj}e%d-45U-#>a{r?8GdTS-hx52>7m!jOgUv}*XJ(sej^@7LhZa9f>o%Gse_UJCHj?htnQ"
    "DddzD&HOv7I5w7>dFwaj68@`2$-H`2PH*k^ZPf8+wTsYh9g4R1tFm1n+F&fJq@>L1{Y7A<%lL)-3H%W9W=X&p98>*0W3D^BJ"
    "BSRL`A>d~ze-khj~^etRvSK!!!tMeIfc7a13z7vK(l%`*KeN#nH`s@-%nNWlfxs(*DaIsf1WNM8$>mWT)ieR+CivS&y2hjve"
    "UOPOFLv(khas8STXf~<wa>-FS5Am4J}V19W7DNga4y;8y{Mj#5*c3;BhA-qSM8W9#Ka@ozmbZb)Nd=f{&NvN3chwO<G;iaZS"
    "ovJMiIJB1!;Atfh=I=gw*XAPOw#po7kmi`QS8`x7+?;>ShX5Qa<qqWkTzgSOxV$doJ`MhpKkH-|q`+tHXmhQ|EEyjGlbJJjn"
    "&0zA_x;YvSi{$^W|KE-r@^G99gdnE6ZX0L9Y@~=DM_o0c;c{O~jIu58K0A~0%Cfd--i3+u4q=&D?yTq+#tI;iRa6ZyVcY*-@"
    "wh8Sw@LyVoWNAjyVunElf!QW7$SZskHM~Ua#pEM5>yRX`KWE8~tDmLb=N-i3Q+cGD7GzDK5ZK78sPLmn_fJj)#Lw(qP8j{og"
    "-T2==xv1({g-4$K<}Ual!h36Y6`@!EnzY(r!5~}Z&mR>=SP6xkS<WmV}|H7@#G;o6VB!8kIM`AiQF*CZ5yMO1EJTdsYJ)AGn"
    "sM@0szU*S0|fJ^=-hHek-#-V7PR_j5QV7DnP{!5M&jsyfE1SugYDC1GjzyKns=*GPF5RJY%Vg)vF5g_<45(W1eF&HgtvVFl9"
    "Debs4X~?H$C&e|j-+C0D<C0D6nAFy&tdcfN%h-cY|D?bcl;7XXSCl!-Q9Fd&1>&?WeF>wY}mY!{d_%a2m#>Jz5#FO?kW^_Cn"
    "RR2v|9pF|tVT#K4niM!Fn&$jlVHg^}`v;NGP$WH7~zhnn^;n*lHP-)Z`Br?8*tg?{O{Sv7VNCi9k+_W80pFw9VF19$`%Ne^e"
    "K)MF{t62kZ8iW7Np`x=J!_3BG%EN=AjlZeR;?HJukm?bRUx>~CYXA_P33&{^Dfi(4zXj#OY_%5_tce@SINBaPJgTT{oaySv<"
    "XZo@YHlYhpeOY|TKB*BEu;HPNqJqvAneGcYzL#tg;f(ccGAOjb`D>{0lag&4Tw?5whP!?x4H74rl9n{C3o1m(|wtGMPVM#c8"
    "1IrOhd4-)l}nNyd3M*`g+DJnYy3sY%l(|x5FJjCl(i^lvqH3{b=GpQNeFk_o3bVHlQBi;Gbwy(nUT`i00fac+1Q<zK$vmiIy"
    "3d&+FPYrW|1JwdB;wyoaq_GDr{xFjKHiU4T|Y;WC-QCsO-S7`_6)IBNo&rr`@7ul`~vjkoOFj_vIfCZ~LCl`hKCK`JWtr{7#"
    "#2mJL`#68RJI~5+175JCT<|i@^`|dZ>`}i{<^bZR!P^d@=-%<E>vx*OS=L4vp;cF8SBWOftY=`>&5rLo1j$pfVkx>?et+N24"
    "1~O4mcd?r8V&r{^Q`saSnVH#D!FO?u|G;k$2M%-qAdVRX3L?q~sLKEgRsbg}kS+*(w^he4rLV+&cYGOWpX9aUbU0V3x0a^ye"
    "WHxKvQUC;w&T)U{)KO-o^@Ny9?^yR^f9CF?Y}>F_pzmQj<4u%-G;<5c(?;~Gx&dZ<vb|wz=~V^Stu%r3jfYT8(v8P+wh8!dH"
    "j%F!X+vLSL!86IvXH)%^6e^p!fb**f{ATgWBS*CX0c~`_X`#6}ZQ0;(4v}Fh6xGAem*hTItem^(*NnUb1xz`>YJ6=6yJApd@"
    "Vbw==bX%v-M8^|+6qxBQFxC~@DRE1@H~G$7hPxbr9NE%Yb`{M}bNF8bVOc2SCNi+<i9z)^TO>a_6;brC8@zXjn{_2#u~n~2T"
    ";PavW*We=-V@kV?$y&q3b6;SfSG;T{r-MhBt3yTAG&)%MC03gv2cLD%Cuh|I#^sM1DOEaTvh2BWNnK%wRZVMt>5|9(vubTLm"
    "**SbzZN=2lTY3FB74F6A*NgLb7RuOzG;#<709n}PeRevDmy3gUeY;*S>ns}pi0V2-Gj5C9H7V2~@d(=ZHfs2)tm8w~ZBYIL("
    "d^$!gMa<H>|_yb3Zkf>#$Xq&z`Ihn;R(oN2U1aSz}}q!mMaR_@4kLp$>}SW-i|gf1xb$y57mOibLzV>KY0rP2AP*vP$N68z?"
    "<x&_@Po6<+cN>4rBw%v@K?UZ~hF?Am0S~6B&tN5uorfvS)VR{28OicO`zrsrqL*0MPj|nPCu3PB_33tA)>0XYm?c_^)}8{SK"
    "nDfF}~s8A>_Bs_l;97qb=odVUN$WXjB*WK94d3IfF2^XX2{lA1|fx%sDdX7;PUwCn>1%;a<x1B!wPi7dZ{@-S-$NEHP9tipd"
    "*7x3EL6*zv|Kk*u}8ukV1H_8n>#~#Lb;F=Eg5FE4CHd=?V!XGpq`1gBUTr4oWO=k`0HMUJi97M~c_P(KY73z)sfIPY4;Gc*#"
    "vk8?d?8B>5_u+d{!UafU0<H;GCKn(royCo>LA?QIiB_~bKx)bT5^cTw%m$|5!*><#aT<7@+=IE9o1j{(O)|)yD}F@%RqFt*a"
    "C1oe0t>YOwl6T|x`6I`_<EMV&)~dkw!gRNU-Ivn{1f+SmzJymIE`i{Dn_W6s99E`-(l+w3Z(fpba3d9)5g;m&PQ|Vs|-pLoh"
    "9rD5}hqWk5})uPU3mx5x7l(5mQY$F=H#bXKT^9_Y496XC%4SFY3UVjzKgijr(-b;=s1_aa6R?PATLH7W|CD4?CCOq5a=Rb%w"
    ">8263{xR5|}d++4gD&3U~QlU@O<%WuV7DRtIx^!fYr>zE~bUcH@eg@&0?^Kk%8d_|}H%d4?axd#aNHzK0dG!0|Qb$8>J^N-;"
    "BMG^auK@pY-1lXP8fW7rclGm){z*7(JLOKJW`}!7U0fdcAfCtfr=Stj_Zs0}!4$K_=GW)1KQp0=IOH(zxVqy%tyfm6siE2|~"
    "#CA}y^~gDTZ}n0>Q|PZx0ANX*GUzxsm9ypa0{{@w5fT?BuwV)j*DZ-j+rtOvC-Kf|8EEh4@j!Hzum~X0*-|};*QkBCHK;G{l"
    "9MdTmMG9?Dg961_*k}QOB;UEUx<sz>7ale7YUR|Spp-%G20zlRe@B^!Z*YL{NAucY3DU8-qeT4OsKJuYw_>dJFzeypa>gzSV"
    "(tm@wfQa=~;U{d*4&xG4Z(GWdK&!k^x;fumNcX|Nnw{{9a=l7AiLZ!OU4ZYKUlK3JaGO6x5XP+6VA~#t@z-FU7Y|HOq;ro%X"
    "DE7n|guzqb&nu1KQ)*RQRMUZ)+H&xfTA+Y`7l$l<+s7$e)RXS<S6-u8I)u@Qwo-mwE?br(lx+YmmmCFP)C*7V1J3ms2UD=Zs"
    "ag>(My$MuJzSq9U*g-a0hr+WF}9jyl5IWqyYr_S{cL$s+d06=uM_zOV&KKy-k0Vjorw%#(&G;aMO@Vc>E1E*ilB=h1=6wMsy"
    "VnI4OAFatN3C9$M$~Fa>a}raNK7O(|j87Kpxa5h?Q*M5b67~=~ZJIl-UX%kq?c58mrmzF9Sx+0j?K-m3U0h4{{o^G576boq;"
    "r&$vI2^6_|9@D(yJyEC+XsO_@0Gm3nG+&fmM*NeI8dJxLGxZwpZ^wKA+N@NqiWLhEASDR9Rm72Ke<t9@3pF58hI4dOzD|miI"
    "Qcb3>$t!;Tn;{JM5Dvjb5w5B88h(K^4lo)hoA7s4tAx@x%EcG-f1%io&pROfXp&9`33G)T!#5EDGFP8)!hB`Oy+*M8?NJG80"
    "a3Nh}l|k!^ggSp}d2*jx@mbT+Y5NOaciRv#Y|cviNIap}M|jdR@o#%u25$0o7^9*Z;66bOup{v>~psPCW)(7ExJhMf_rE-(~"
    "6Z$`DDQou;T!Go%WznPuJ`_t#+=mX!_)Yq2$@J{st+ry8iOW4^;p)76eKsvg&w=*18@Yh{x9Ucf*+QyqQ^>*BPduriqn_gpk"
    "6m9%BDtLu@JgU{30q=oL{Wl<@vqX%kRN+eezIy=QgCZ_O+GI271p$MDl<_re(Ea9x7c&Y18D^XT=2|ufAFZsyooL|KaRH7Wx"
    "oO3nOEwzE9#-4-T#esoAHp*VMQrm^2<i%%z(QW9`|I{wzi(zGh2B|6^c3)m8ttx0h~-B6y^|G*r>sbvUI4%pCyaMRTHMX%nC"
    "0Q`YqNOuOc79bZK}UJ(W7AvOhFQDFk%kBntdYn%O+~^+O|#yD2jLw>JL5I;-96{DTq?aRa}uC@bqo~@y-Hqs-Di+4D^zK6ml"
    "&KM<&}SHEq0lVgm1TCvo0o-?tWiyT^p>j;MVXd=H+LD`2eQATMofN6Nf!Iz@lc;#;KO?Zv@=a^T-@ONhm#1N!y!vVp^Bnf3m"
    "!7EeI6`b`f0iRkQ6Q=;9t1OID&C%%XUJdCzk60jH*?p+GdeSKTG!3)AQ>rv2P3=X#FEeIO|m#Pf@m$x6Kk&8CfUo?~2p>|*T"
    "bo`Ne7(Y=O!j`scs{D^C2YKP>=se&>!4oG61|$pl%EiIIY32vTUmh!Qzay>#5dS~|sMrz*gBISBx&fBW<!eOe0s{a<XPcT6m"
    "8oyzKN|~}ls?*eLp2@fHr*v1?d~_YTLVl5-b6m2vfxIw3iLK~ixq{V1$w4<y+YQqu_Kj2r6O_UcpJ~o4dWZRNxb>|?aCV3vB"
    "rMMbGLR@|Fcn2Ip;k5+@b$QzG|C-e_P<dgF+jD8Q|+G{qeKnV?d|f+CA&}7uV7zJJrcfH?V*J_n?W-Viqq8c4KbltAO_~XG@"
    "6a?DD4stV8&n+WGi2W^kWqnk`0KUDvZ@AUS!x>emeDol5+kYg^d9=rXBeaLsZvzp1b@Na26tVE{WfMSD^h-=}_MD8PTahwuY"
    "#31VJA)PVx*a9pov&0Rh4kJkO`ivL|DWuonUd-ZlZy57xXt)fS<dlL66qQFHUfD^*QR~r?~PTmFSA7gt)bPg~8Ky)rN4vM#0"
    "7vW*m#*9v7)Z5&cF}8}v*lVR9)92^tDoz;g{~TuPMUOR;G|`lTC7`5&@`3YQ7u%$ZqbEH$3j)6~z6BqjNaOsgp1M|k*>k#fH"
    "vA{xx6;@K*Hp~b9kwiN69CZ5DQaCA0KtHnvt*Y!xu!Fu)BW`t+>>bG09yDr%;AmoZD`E@r+_-j&Jq!w8{RSDxAx;*^}YDCn!"
    "$Z&;$gH*AhKV+xQhO_WQ}+9SiOEd=p=oI&qxLl^nUjGIvOa2l74)yu;Kr*6PG?oy}i)HTX*k3eNLiXQ5X#zj94x#y|bUrl+c"
    "5JJ?Phk{`3sGt(WELXU7u^eKz_T_#NZS#K&MxqPI|?lBgiSA=$#)ol7D8<B#$WM6`K?6{(2mtPAE2;$KQWw&urB@NLt$+CrE"
    "%HjoN-GD3g4!?sgeqt{RL#7?20=(e~Ymb^dCT<9zZ&>4u~=WdiSP!s}bWx=Z}%(i^|^ymoodXxCu9TVzfD4=rWz=}U<3PsgM"
    "WnB(r_20KpC}IvL&7Rk~B7fdg{<lp>SZ9Ek)f4bLyJ~m;@xu4GI~>rxb(Y@d?<71k`}VJx$Dg+^g5NywsQr#aw3$tdmUp-M<"
    "Ats8OS8BhIb4r|+1*56<@#T_darTuZK`M4Q@6Mdjs93MfzcW^Dtl~)dZ82GC)5-!%?#n>2@hr8HhE>HeT}#GGfjk!1SHz+C2"
    "w7HTNDh4R|j;81om55*7r};Z#l;x-GBSO#DFPC-7iuSdS!#2F!^j{0kwsDb@9J-*$*IE510W!bgrl>-e+BkFV`z*J2Gl}bwj"
    "5E_WI*l2)CcD>b-G69`kw6EJ9~VK(fkkNOw$3=OhXM=u1jUS!Uh)*1$z|Ho#6Vg<sh^hPP)uj9>VqWq;{BhSu%iU-Q(QX!+B"
    ")7cJa`8Ybak3Z5CX>t8C)rjP^wc=5b{q8>vcw{ro$DUNjzEqnp<cu#E{^~UW{_n3(2+*84ffPatpliDc0i8}5;9rv3|0G-mG"
    "%yR0z#&wsR7fY^jo$mn8>^KnM0km*C8u+BV0KT{Ju5%W~)zJA*RBz4#uNWJ})glL{Do|?MQI&uFF7;^=JDG(2{`JW+?Ajrqb"
    "K_b3O-{4f)@vGcpuqx;$Tn_i*6|nh?STKty6p!Ltp_~8h|VQvLS@FEgl|~)VV}w%r@~ACUGPXr3DJqLKN_?BtNjM6h%T5V0P"
    "(<I_3S7Rc0xR%*LX_IBY=|=m>5stJ6;tp%J0LSU;c*;eeFr5_bNAaG2ZRojjNHvK4egeN?dn$!}`szBs<BAgZ~-=OvA@LXy6"
    "N2z<Zk8AnUhm==YI`*0}WLYH0W>{6YI0coGUYA1QOK6HC(m`(4+1cL@l?qk5^-5w!6w)bI_|@qy+Rpm`XO8*e+)^DqA~^;iC"
    "VxG`72%v^waU1H2}kkQNUl686djo*{A|AUql_5|(w1_1iKtLjuU08VlC-`u9)1rn}pV;&yvR1JK%K8uf=iGQyBCpwol+{Kh="
    "%}HIN-dAYgS(y^fS7}q=s548lW&!|<`_StZnY#OCtt!PJN=fV#@j*|aK+B}|O-Ub<wukLoQgHGDA3ZvW->w%?Il7Uz_Zd}A_"
    "DZ}ddq19rB6cE$Avh*gHq4s9fYjIIdmi4WGYC$=!+tdJWmNF?`E7ta2&nlD{QeQqx?t~6!y`A~-N7v;;JFJal;I?1uH(Udvd"
    "HPu0D#`rL<c!_Ho;wJ;8z-#Kn3>#?ZX@EI#*07D>I5$xe71YGKTZL6i!Tg*nt$Xwgc%)Sa!emAkki!ApA-L|K7Cx0ki)D-`("
    "Z11y12l()XcZAHh@7EG0ZD+W35H9=|$M27-qGbhmA~$gZxlv-)pJM9bmHM0C!Ls`S_s@mJQp_})|rV}TR4ef_HR4sr%<?`pq"
    "+jQR^p0|3i?!?=Ty_yKhWfDUZL%L*I|?I1u!258t4xtwJ(0>0U-;^n2waPV6jI~%~xT%vw4H-{UM#S@S>MXj>1kbz~21L|Nv"
    "*ijZ;;TReH9dv=MSp>Kj4g4b(@PYX;AUFYFaznpwM6`}rTU4?96uev9f*VmZ75w$?G5Y$Z>!B=W1fXvzdVMWC4$lnyzk~(6u"
    "e}G2+FgL!V6*<|F}3}YtMKN=19)b>giOOiV?m<q*%))u;bU}_f74Bf7K@qXb<v<cZdc;~z^e7Hv(UL~$rruBgMNhrPT^bkxl"
    "JmGrjVFbKJE#c_@DA(ES&rnpiXS8zd6ww#FLEZ(O~UTzdY2!i?SowtI}p|pC$UOeSE9}0R6s6@*DMb+@j9JzzKqIO`jG70c^"
    "cbv683<5^cRSz?G0W;6bZ}|2sX4_lsR<&OQt@H)a)kVeM9h+;w<&>btlKIgG+V5w=<1sViaYkKH9%q$wb%3t*juZwCKgK?Q$"
    "Q8HMsTa@GV9ty|V^l`me8KeunfwaB3i+hjcz`qVSgpXuFkbWv148vNgmI=+b-K2YC|M)SKH>pJHQtL*4ryv{m`rwtczzLkPi"
    "14aS|Wo5&bwtgd`s{ZlJew3GIqVv&m0Q0WM#4@}=k{JN2=x0PViq1(I;(!2v{ynCZk9jx1C+DZ}rrHRC)*Tz`?@qKv@kAqfl"
    "sJWJ)Z0>1_|g0j_V{UJgxgavX@Eg(cW=9XMrU)MC&x4SgEtP2?(g@5#7hIBy+-_KS%3|+WjL^{2?;NwkS|#HMy-k$;tEV2`3"
    "{2mM%~ALLS+iq;<r+_<4R<)7a6l%pk6QQcFmB5zrNln;4s>_6LowJReW%648RFMa^|0i)}pckMvy9Bjd$6%;HfB@<p3qq2!!"
    "oKyc>!i1pst*(?K+GGwOJ&cO4q_{Ro2NkeJ(0?ZDWsr>Q^0LwH)gh%xD4rsA84038T68DLf-0Ia0hUf0YKn6LGJPWA2ReS9+"
    "IUoCyzegS}0#tsIH0uTcO019)KkFR(Y{7iKZg4%s(2ODg;2hkeE6OHIml;8S;>hsw{xTuxERx7<&Ko9)}^HJm3)c{Ac?q((+"
    "QGl=Od8b1x6X;(i0FZp18M`LZJmc7gPG>aB9ikbHsH4%6Vf4RZ1=u$1;-ux_{l_Npr}Z>s{lN`-Z5mg=1YT5{#M7Oe2?T71i"
    "yZ94ELm6xOYb0Xk7(fU)g0b4KLi9v0c@~zSR&dGEEJS9YqSdrsZqeW1fR_u#HGmMJfuwR6BVWU>t$woX_Maa?H)AoO;qvD+Q"
    "pFV`vJAlvcL*zc*o=LPvsN1K2^Y>sTPKO8(SSW+&L$%0~8g{?X>B-&6KOj&O1i|fK#de*Do``H2KK_!MzVrs3;%ptil_nkKu"
    "z0!+?K;Z5+{~WP@F3iPpHxZuRP16R#<4MX6<B$Z{Zbm|ylr`GY89GVUCNA3R7nLPTo<br2x2?N49*Qum{;SFvsHQmail=y%^"
    "@`e*X~x(aYYdMFlcxFvzVo1MWc8)Y<Whk#1|0q^=Q2vk;<Jp^g*z?%w(@njTm1#%dIZR!GO52A%zQOD1<u0ykZCzPj)BCXfo"
    "mxwkxy<>gQb&Z-(+0ylRw{shwj*<y<>Y66{pAG`tk0w5cIlK$kU~cX~1acBUZ9`q>(#5^%jpZhuGdzOfmIJS*PzWrPoH!$*w"
    "^=>ab^WV#np63GcL7KQ3_3*!<Dc7F?6c_GEnQT|6g&!V>%_MunzqDA%Qv-vo;x!Rcn6u?M)WA!Fc(^)^&&O;boD9c5qwXkh`"
    "ethE1WO@pl8ZWDquJR+%-^+D($zRkTL;)xI}PN4Cs^^esKl?fV0d5KP1|aIIcX@Qxd}^8~3Ot{?FtbKA}=*O+K{br*u$K{(7"
    "Gcx62Bty?A-{D4v2GE<(l>&eEOZZ=s6+LLDEj3_*GKuJ7NIh&Cs&U6qF(k3SH%nc62?;F{%MN72SDsN?ti3(#)ek4CGa=Yu!"
    "Qb<WCdRp;%x4sU7Riz}S0+5N|A0*)t8ww$ny?<}#4^k(y|1xuCynj3q*><IvLQvT!JfTG$3CKE8cT?&Oc+sAi<IzC;S$6w5("
    "04#0iiRj$n2}ks(yFmTgNF6UJjA55dqo8yEKrR;eiBtO%(Rckn-Eq?Y54VtuL+LAI0Q7CZJ1_g#Ujc+bGw|VB!W0Lb^#i2S0"
    "_lQ<N31sfc6J)?Nl#$*fels=Dk-}|Wm1>n#r7RI503dezuUbYGbe5baB$=P-bA$VITNaoy&Nxe@4_%FQ{42=?Hkc-9EDdstW"
    "&->)U1E@yxnTs&L`o$lQ)|sUZcJPw1Ge>SVACU3D`RD-O27-g9HCq=dZGwKTo1V5kFk_YwSdZqX_^=c(%d`%fqJ^X7IY{a#-"
    "7jyV?*vsy56;muTG(;|k6N_+a@2empy5wgt4LfQYuvQ%Z#=rrroxE$)x3izb;Z<KjqrXKcS*0AQKoy^nbSApD_B-#{tYCi6j"
    "H!S~U$B;33}s%+sq?HYcvK8o3cU)#9XD{Dx>8iC^!VCi6pcM|Z9ZQS3Nh&GWi<+w!%JB2{DA%g`Vm=5a&Y@orvz4Ze1>uv)t"
    "7#TyZVIfzuFk*K6iQ0B3w3R|ig(Y9RG62?n03cCYpqCl^hZ7q*+pq3O+!ZwNgTW=J9Q`J&j0f4ATH|j9(Z<3Pj_5Ht^R}wo_"
    ">=Gj`(9isvSwSjFasblQa70Z;S7NiVFrL}W(|7Q;4S-omRYv{m<IrQ#5E91M?qpi`cN65Ty`*-_VD&cj^WQ`8ja%{wLqZm3|"
    "mo1WaD&-iHJ73?N@xC`iTD!o}4bAIVX|!ER;<UABkeVapB%R#qri<03cc1FaEvajzzQ;a9qexe;!EGZHXhIjn7tQ@f!;nz(2"
    "6Y-vpwKi6<V>W5vBly`$K`_oYg>!p<Qbh%g4AQ|6E;o@15+#8rC}1$L5Ouhv=&0GQt|s)lSjM^VSYkf>Nb>RE|eM&k38dHjw"
    "X!}Q^s*TPRuL`0j|_(j*LU#uU+j|~msLO%nqs&Jl4g@t-MrFvAN?T%{vtl`Z6Qw{)h*8In#{dl4xTFMv~{)=Y+zuvCmxxuBV"
    "pZE%}!M1xOS}zhCj}p<N%0G_ZQ<vh_cHL};CrvxK*cPg;tpIf(AX#ANH23FC7UEwEbjL{Vf2@C=K!&sbcHChKgCIp^!&(p+u"
    "GsjA^e{e?uHuEG6Dl>fXRZ7eL`1a7?6~Hc>W?vtUme+sJ&iQvJTM{Ma5<kHZ{w%iY%40;quaFrN-9WG^mnaGb~gId8%pk8(6"
    "!Dm`e!;ZVO!qT#s6&JXyD;%%_{11_i^w~^cZ3QfatNJDxx-b7ru)o4#}2DjWg|L5bg+IIuYRm`#xO<4A#9)!9%@(GO84;0|D"
    "{w209zU2S$~He9MM6uW*^l;!pN&$M5Dm<R%ydAR?ki*OlM%T=jp|G5lD5*wir;HG%DR3a;MOC$4(0+qZa!A2Z+&S9u9rz|!s"
    "Ax*%4#Ij;5}-<VjYXnsdwYW#SXLfcW;?=|s<%?p5*F8oJCkCpXu1tQw8gnNnl^Wi4GKU2c4APp;s*8iK?g2Z~dPD)*J+nqIb"
    "3ZL?iv$&Ii4rnY!B;(nGNVE)MK?RtUJ_<PtV<Qg!p+1M#*gNp>-FE<TW{tfWL`1ZaWVb(F{ho6IKQ}fCry}6j6#`#ji{rx8E"
    "m$0x@3i6Z%zq+PzSHcj;U-I*LN(z|_awP(apL#26sCobldgxW7A}K7a}(e{u!etmqK%Ik07Q>56`a5;g9~wcP{*9*_YC~aBY"
    "K{&2HVX<(ErqQ|86E@GAex7TPR82l!t|JIB@C$hmN)II4g(0RwwZKEonF-S1X8-^^jLdL`3UJVT&5Q?1$7R3Uheg&?qX?0dj"
    "TAr2Oldf3rJ}ne~rn!=rXQSsA~pAmAFds<u3y`H$-n4S0wUsK@{dR)Ehh%)_tV3&`2C`~wrwsak_038GEN9#t<YyLfqS1eYO"
    ";Y~Y5S2`gF_kgWc%E!XI-rz^;kVup)b14dg0M+E{GvjF0>O1(?KtO$_F3#c6M|0?tN-|j`2JaPwAom=P;5z(2;ZofkPnwrMX"
    "kBwr~cTlfN><}rWT6(R&ZDzQY-t*p!cjNW%Q4qfq07$lVXHv-Lv1r%(WB>>S2^GyE_GBr>#Q=5PA|Wwt`M6!x@r>p+VDi5>?"
    "jTwNm;pev76jAcqwNxIYSu6%bQVA~@Q>>Nn9qCm^IM~Rhf|_ELwzzD%!SGHpAwg-PTwNjHK63AuuG*d)O6s@DLf-v!l&(r@Z"
    "!8ecKo7^@a_;1(PL<A@6*+LQdPWgWDG+M2SF7WS1wZ00vtQ4a33|%x`?f5r{Wu;7wN<RdfU1+I2IOX(2kqmQwIhB&twNk%&P"
    "zuE5O%lRbcksv;XrF(P>$OS0AFyYv{b6R-ci#;c>`eSfrv^1T9euAi0)Mt@kTPxaFY~5<ZlPaX5M}1heCTzFUMv0regF^R7a"
    "~(feVx7Ygu*YNIe@!zl`UY<dc>ucaU-5AqsEL`0`1w^eQ1b0hv4_uz5q66U7cs5c}gT-R(|(+ngsrr=+=#hq!NqR4e173_F-"
    "n<az($GXuzm977J*Ze2HjvM2pHHth)69CZn>Sc}J_G)-eV>g1i|6qGev_>!kfM^Y=&EJokTQyW%iKfm3=xSi&wehhv(3TF^9"
    "cbCdF1c}0w9(-rGut2U77%?jvn<g}i`hNELdJ1%VLFTYyu|dBkLQn!;_Exp*m?brsMPkoYrMxrL_}*vY0q`)*UJJ2iife&Pv"
    "N1X4cJX!yPJlkgVO<!arNL|F78&NnGI|N?09#Z^`>j^znTX}Ep{B_h_V!I2n0}QS`rmY;>)cng394@_G1&#sapdh2qNlmCRB"
    "Or4fvG02bYN~&R40hk&RO8)}5YW!QHpT#gdZiB6|xS>Y4xO_wVeR9HtoRo4dbJm?cn0fT|rJU$Sx3ZsRjEGx!6091DkT<@Jt"
    ";hz8nq&5x)z&)<co7mDyI3hB0mqOve-MceyD%kreoOtZtL$I?sH%yxgh+vD}@0I(Jd_%0g&SS|w~`WW|3I?EKp$5arQiHtAR"
    "7x4W01W>ylkdtft4ItV)m;pevmiWiT!sK1}d~?AR&e4r%NS&>+`)Ao|r~j9Ex*_@m0+IoOs0XEIT12?7u*v@KE*N08V9EtHh"
    "CIhqX&$LNcusKy?{(&}=W##04kIW;M0Bo+;$HRA(Fyg@#{Kw#Y#C|+$h0h!rHyP<i^e3i>vVq|Yj$i{mOxWV1c7d+lZAPcS$"
    "pBmfMG&FqD@;9?Kf7}uQ0`T`!t`u+x;c_0&OVFz{h`jb)bEMgMXqmW-VTUh&Da9{5bW#>@=R`lyN?EEdam|6kO90iPpvIDez"
    "9iyAIY7_S-@@7N_?o>l-BR>wPWrWjw>u`xZpo20~#T0cv)D;j)7%$HzxcOyaGrB7&Lyy!H_h5wa6EsJA=E@KZy>$h9rBstRR"
    "cBMr-J@23awn%U~lv^PCF({yI``=z|CQGF8bIst&ruM-aHl?d1Ko4|+pm{|93vL1Bt9s%VC<^lSi6PAa+Ys}&`tqFJwcLAuf"
    "%_UkxctR4bNu#Q?<7xPkeJ^&&G_rw(oU$PFpkFt*whjU$_8VTeSC%taE7_B3xfna>p2cX30Ehe*hDtWJjJf#q%nV*ImqYvH9"
    "lZV#5p7nPF*SbvHTW<d#M5&{%*^<(8Up91(mh+#>cV!)tZlcJB+stF_IHrwTD;!Og}84K1pzu+^O~EJkBdH<LWn?J1_&I5hp"
    "jels9%KY$*%!8$+nhgjo}giqBSYN!jXINAJqjsj5b<IMuYz-%`X0EB&+bQL#CkL;@Zm7c!BQ!cHWNgHB-vM`A!Ory2SqDP28"
    "9+;45PReq&;r$`n~3kceor$!@t={Z`q<f2EJ(dN+^zPBdY)1kO+E!N0YnU0odfuTv{EubslWy0Bqf&>-I8&w?dwK>zE!H#+k"
    "{La6{y0RmkRQ30M%xLY>y*@anDPu|ACKhYYsPDczx8=NRAs4}e5KKym|FrI0butm9@ZS#5_y!K`z2GtBg@9l{@PBjxi49sKf"
    "PGvN&tFWMaOer6}t1yytU}b^7oSwp;l`g}912+S$DP9kWh&C!`NFh6f@$)XgTbc*)?BXz*RfT3#Vp!Q2f`gQ>7nh?MrUGr^M"
    "UuhxHPYUms@@d~UD*!kv-NOK(-;@~vlIfQGb6&#NHYjfPf7f3a|SPOj04pJfShByO0)*8>wqTFhNUV(U;(oEfGMJLShg_}_|"
    "f>kvk<S(6O*$R>mV~g|1R;r)6NJ;1`&Gh(wP#bA7i0pyVxO8nDAX>8x}ARyli+2{=$C{7hnC%v-0Z@5z*S@l(*nTsV4qL9l?"
    "+0hTzR9l$*BMZD)&>LP}TqkK3Kj&O4pOWox@FJr$h<!o{6+LcP23tgz2-B9JeYLPba%kS)A<_y%C%Cc(i!(b~lT0MQzyuprP"
    "rEdFA46yIsr;H4GnItTy(C8MG|8_gLm1L*FbMKuyEU8qQznh9ykMhQ0Dwm`mZ<Kf9Ro|wwxi}GIl&iUIn<XcKaw3(#}=PA2%"
    "g?e+khPUmWz=bl6$tfQt&&H6lkwvt{pIWYWoD2+X5KFctjMn`33&1Cf?wXHbu)sF&o5H;GQF8-)vr)y#!#6!DKRywiz6}!2B"
    "-+Tfs^a+f;PaWgaFL(ExNuFhU5{&f3*N149ra#J8m3ys5&$il>0i=Wi8?Y;K}uz|Z3+Vd(Q|BtLtYD`B?sA(g}<Ah!RxUT58"
    "eM|UK@#s);Uq!sj{WZ@UQu>(BJ;4CWHs<NvGlZx;?PN2S!`Vh8by50KnARF|QImCjN4rECE=y73*2bVAlQjJh4+4Fu8qU{E)"
    "=+rNmLu#&=P}OYBQ=;=!*1m|+`Aw1zPQfN0IDp)z$V{=PPgrYliVz8S-|JDrntY`Jv*Rn-JYq$l=`g(!G>k7l7@xzXiL@177"
    "pApmwcY5f+XIV<tp!YKYFGmT%{I-v@q7j1wyn22a|N^RMvek1SWJLMy|8d=Ou2iT+1INwUa^7JF3-E`u?e>?+jg#qIwy4sla"
    ")I6NRvcOK(f1-{~@^|iv8-x#@RUW2=kAJCGaN@ylLFfnz5v^&A&=IW*MP+3#!6%C|_}+90S>HlI7c1&o!WXSoOs-)Z)LB_86"
    "BxY%|5GUh*zfAq*{6AN#v+J*Ned$Uc8Rn{2?fis%;Ot=fQ)NF<OS{%4Scm##T$Y#96$UWUMGo&){*gxzel~J^@yqPe}PIPs4"
    "ECxpx`)R7FeLG-FIh<$*8@En-A9%z%vhs9*6a-Z(AD;@RvR~@u8;<Kw{><6$EJ75)Z33K3|{58~sr<7j9k8?-J3b!4s8ey$}"
    "=XCBwiAGDEl&S(K#>S8olt_<+UqMf2qv+#R6T8SerxV4HzBAkwp}bMaA8TBD^a7fWPd1Ge5~5ojqN)l7h(pm3*b;AfiKFmwD"
    "~1hwP5UJ?<lWtpvN+eJ6vul)TuKS-H^uZ6aSVO`*_lkVTYz+IdKuPf}Bwe5x&(B|~qw_fz^7sQhWJ%Nt6dttWtOD+QtXs7@+"
    "N8&-%!q@6myr#JevU&#qR{bYh54Z$?XuVL!#fRsI@vT-3Gr~tp=q-38yg;HANJu@Sp_u^vk_CHfGX~Ia7l2dM+bQdO8g5@C6"
    "92+NPm8lUI?FSo2mW>xJP~1`z+&4*Yg*w7Ka2ZE7w|hHHj2BiUW@M_5fN!am#VjpI5?a>ip$zrlxjB0zKxO|_?uvPobIpdza"
    "+P~3;$WsKfANnef+U|nc8C5U>!CIowl~8ZcgvuUw;hZC3997JP`s-DNz>zYAK1k(7?y5GkEoU2C~M%Khb)!4#Ss3o0zjjmAB"
    "r2zw!6u8aIbRV4)N(1<-?8Qy5T0aXo!Q?+p7!I^&m{jY+0$_I+Nm;&IgZ>DdCgssb!n0cIQ@b`iL>UB~OQSK;XWH^FZ_vXS0"
    "NBBFK68Q!k8?|B?P(!3AXIyubE2FSN9WTl0&qX++q>%0Ek3~r+o_^zdLkwH7`MnnJZd2?}YirhY0mQ?%i`Pvji1Y{7Pf&evJ"
    "Vg^3$3z~SoxEA%fTY&ljwueOP3{P63^(MVf{bs&`AI%J5hfHBYxJbq8@;V)gKIx0e&c;SL^TlenI7(JKPTXw8>5Yqbn?Q=b-"
    "4<vB0j2{VrL2v1O5w28!oSSV;luV;9C_rHjq)xM5v?zxs6-}<p)GsyYwd^dKSzf#<k@If6-K0ktg?{Ov)1O?E<4FznhBA|U-"
    "Zs=_m0VXx0YT00jvDk<L~__1^||P&qOsp69`wPCQet~Kb;9-CK3S8k~l6r+}^I^tL-Y@DK3RKy&u34wu40L5Kmm9^~M@k#q#"
    "C&ed_`IOnwvv&w?*uf&luT8Niyy>Ed?i-_h7GXMXR%e!!Z>c+G$3uH-g>(fbo;Oqgu~CF+4h&JNd%dirZiqLq`TNZ`L!=kU7"
    "L1S->q&~C6c01?rn$<FOm<GUY+4|;dus#F$kOTcLel$4E>6tHb)aT~uV(@Srk>q8-h<aV%~Mq!2J{k?<reyIa%NHW7<PyxWM"
    "0Dwdw^!pROHM$SsNd=+%6t==~<>70MDqiK@fY}qb0RBmC^+&Xht>LQ|5%nd;%n*Nk+f#8@`XI&w7j0jfZHv-EuV6ftH2C$bH"
    "+69_J+r&mUvHXcl=^Qzji!aneQ}2=st&Dd19%e9DWv+NrA+GMVb#WUI}11=TKFIKJ{&#xZJa!LctgCSL_}*{vAjcV-E}>_hz"
    "C$=+c>h&Mp@a|DqOhwdah^wO^SbV+qx*g8x4$uK*Bb)U-W%_vc=-SaIa2Kd5tfrivs}tw%FA=_ay`4iyzxUqM?J{j>Mhq2L7"
    "=+k3XFq29zH7Pp{?QoQPI|Co$2wQ&d1jIO)sO2l911Jzd03y_dbOv)L6gQL!G=0TLVetnZ!O4+r*30|3d##9u}Qkj#U1fupD"
    "+80~AkSRiS!KvcL~AVA<K98(^gyg+8i!pBZb;t$kroH%+v&}KFO5z#r}Y*mHP^YJSC5&Z1vD28he+BJ!7Zc0yJBV~%!Sz+5}"
    "3gX1q@wnJ*bX!~~w-X3XwiSubyYBC|v}_Fo0pj3wvZ!C&Y<2ytu>nf~J0%em8bV@01UO-N_;R&^*NH3P&)fwBQvj-u^>0i>X"
    "8})SqIIjJ;9i7JjLqVyb`hh#gRI`;Sg!}rouD}Vv0sN~wFd06w|1<eGq&QA%@ry@CAU?KQb_|y%p-u45h#>w+~qg$(UVhnUp"
    "ozd=D{`lZV?f!OPQVOrFjoOKR$%rNF&`8NVhE%l?A)AH~li#@`367r;*Bk*4o7ZKW|UGdf>0M-1pb_nPqM9P6qLAJIbW`3%%"
    "n(ST%TYvOp-zM+5(Ryaqnotm1F{UGORo0jk2mKhXxljw;c5=4@3HJHHqI)V>{igEU5j6Q#5dC^B@aXZ)HE0Gy^yTBJIoJ(TO"
    "ZDzYPyDhkY{0{p|=EPh{X!O4R+ZM1ici0Dx#?6NA3?8dLzlX&*<Fm|bwS?lk50-1QbzRoOoQlHuT&WmD=SRnu~=;s`CUvIOf"
    "2mg9-AE*1r8-MF`2_ew-BvQ6z0@{seiQA!|h3~X#ctfxcUh_ey<|KgmHS>-U(b>V1nrJ-}LkjjTd~|rhECtx=yU4+b($#zR{"
    "O#LGS^)z9%LV|HrGo$xCp{0@yoHew2Vbl&;HCB!9J&3gyuK0<oq_V68`OvFDLgGx1S&wPEsztoF3AEn-tu<w0^Qws4T|rs*8"
    "qUIt<MkNRj(jX*C09YkNX43L<u3#3_Q$P0qSXquQn@qnYa@56So5%>)H@)WNYR!NJOW}x<KW(UXRb&x8kxOi&5!>1?*%P<qs"
    "u_-VI8VUoL%qqg^RZHv=GkZq(UoN83xKEen&LhgrwRo{2OLS}pv^Ba`@GBLHS6H`=>LM06Guq6={Ub>-Wx`Em8H>Hv0lE}HW"
    "S6UsFe{=@bCv1P91XJN;_H5&lvT_%uxLT8J^cx6Pti2#Lp=|iP~2hqa6Rp#+qt*t=)AP~&0xp#_)&MuzhMC)B@LcuTM_lFz!"
    ">FkKf0w@S83jQa03CTi7t65XH?3PHIH~^5)QqpWKm370yi!Coe%a(A8!fYA%PqjJxx;2KAcYkN2y@NzV=fsx1k5ezIAH@rXM"
    "ls%Yk!e`S1_HM0nERy{z;g69x5-g*PZ7N6rmnBooE6%k<ZS<vivICTf6oBFcjudEXB)j*LVwm)5*f=v%T~BcHt_G&dAtc%p;"
    "bKqwC`K9?-UW8T|C)|HUeu@rH8M<Ke`X&N-Kw9Wg{!>#k9cQYQTdA`tf~n<>cf8H`3MOECm2M>6B*6DgAe_P3DEE4Um>-7bW"
    "(~CjRgAJpQce0M$7bQX(Q+axEQFg`qKQ-FX@Q_uOrGO16mMx{Ylz1<TXhvf9xgUvJH7LHQCQE@HQCQvS~%0MPHbou|b!`#nq"
    "jq;8YKPg+oD2?<ZH^_M;l_$~ZvYXKi>ZiiPt0^r1&eV2&n?BfYfv{6{Q)a!@Z_^IqL_DEe2&^257n8|@S{NL3{SZNI0Gkvnz"
    "0{}}pWAUJ0gdHtYae1-$qW)h60o=SmGcWP4)p@+ET}JicTQ<@=NknwU3fnGIua$H7@$xV(Lk7*NLQYz6lvteYkJ>Pub!C}lZ"
    "k=iF<uB!(EAEoK`895twzps4UMyDm*KA!QL5AA{*M!83?c)L2!hhBm@cZII`120{{v&LUh&Caf_(U6p7*TL8#NUn2;9BG`t{"
    "kL=g_NHCHvxdC^Al}l*U@jbzhD0UW)1)>I}?+9597_0buTr1&O*>eGbfQ5w(zZ>hF?x!fI~NbZX>;$L`0{pu<IK2-qbw)N2U"
    "yKUSX(dqiDHNy%lMy)O%1SbzR>UNEr@plU57>oTaR<N7V{T_WBI|b+e;`&q4G!y-dxr1!{JHuQsZ9A+E#1@vj5mz@KO{V<(h"
    "oL)oUvJD!Tq2Djp3D~p1(P_i6AhBE<+9fhbs;F2OjtGG0*+u4+}cm?e2I~|jHl_dhD%#4*V!Io%-$`)uy4@X2Bsj>x?2R=JD"
    "i~lw6Aeeq&$xmRRpyYs}SVTk{Mq!)!<*dT9N(Jmj8l{$vvA{tYZr6ZaUtQaJ>pB1~L^$|Yr!w=uM)d}kla>5eOJ|!|%Ix@O!"
    "q169fx1ZTf*s)Apn?CWE#U3JZnPKf2NVm_5^Z*C{qjgerz&;1dRt)*&(05H*mp3h9JoRU0iyA`nK%i;4FP&<18lad#+e2HI{"
    "mf90D#_}%GPhP$-Ibn4Um{uKAI^BD<?3Q@^J_)ygIWF_ulj`8|fV-B3e;-$K%xNaROI3SzI8}7z!NZeG4UJLzvn9IKUkK(-{"
    "EzCL01)=lZ*m0{|;+&0})>qnjk!I#41NTw4c71m;zM8R6rmW)1((ui?Yh5up8u&PiMA?+Ot;3V0zP+HgiyYWVT^RQ4bqZ{<<"
    ";Y?O3Cz<5w<&iVkIKw`fj>RyOdZ+X}Ewn0x{^VOHnMgSn$7fZfJIsr4h$=4YH`dyB8W2h>Lnh4-#1XKn%s9N~^!aUxM3Ctb6"
    "d9A-&L_}xC-KBQ#xd9)Mw_%q|qvYFgeF0kn`7m_alV#R*L!#n+WFrIsdfV7Rj|(5%{dxSQDTt`BAOcLn$HS_P&(-JfUU3B)G"
    "y4HG&%r+tt((gu5uFZak9u{fffwXPu_JJimKKI!M^)<e1A;IUK%HR#V9Db*NdREr)=Xgs)r;OAovtcnlynh2PG<_VATcijr1"
    "Jvxw8WR{6}(35!1TfYUhD4|5z*->?^AEiR`K&AV@NjyaxDvaY3l?kr1Y%6zD7oC*%$RLw@L&7R$76!p0B1|f%bmO?ex-!#pX"
    "v>_^(?M$Kl~CwF-XCzXGj={eYYTFt?uH2_iZNcu^qQkP6Dm@52YOGk8X}h=OlpL^(*Ar2tVOz<Bmxr2==omJ0xM9)tDai~|7"
    "4*HK~Zzvz9n^vr)8U`fu>#Qj+*G3ooTbHMPZgIoMMekyYz4t?t%*UP&{M6@dT-A_;-vZwKb`LNKR(-Iig`BCxW_1=K02~hWB"
    "nk@-fZ;*Cqxy*nizeD0Z5dyQmhqkTIbQNy%>iD;M1s^o&{zp0RC!!5^c_gBhSQ9EY`V{<Q>P}o`Wl{2MWONolv<yJWcpv36F"
    "<`2{U%}<Ic(pm>Uq9Yi!F&;JQ58*4nVaG%nq-irr_fVi1vqAVa0>!nPT_M4^Y~3{#q`npfa>g8eAkGGRwXlWiF$r8hv#n@!l"
    "hOg^#zIHwvD20i{e>-vzEV4Ksvsz#>}TH>|wi}u9$t>h2;IoFS>&vdd>fW4A68Wjw=set5@-x*5zpES^w73;<7|UNxVo9ZB("
    "MDfC;>HxQ^%LN3m0;%vww6t(4400A`wcd2t=0fwTUnnCrjRt~h7>^Q^EFLcjN|^OnW+7$llXqG3yjtbm_U_<FO7H;g|4hwuL"
    ";swdf*Bck<1WVfi1@qKu!co;uc9!9z;5Y!cN$~IfmrW{)rN$I{m_RjPtYpv+0>PAcX@0Weo@BIkx=qib@fB+AQHg0Ov@ZF$+"
    "_qQ&DsvQDwWWBu$MD!Tog@R}!6Qe3MdL917eF)duITU;g8NDrF5T#l!nW^tHSnaIKj5;UrEQ~mV%z(AxOn#oeMVfm$tb?8xf"
    "1-miCe>B12#}~CK+}~7vOthk_|S<-yhm+C<=8E2?VTec>dP70r?&6B1|MtPhD)3*tQvqOFk!o98I%eXL|nmMs;<ocPS$(xR;"
    "!(X@u2GXk9GU9%H;_I3;YkL_#b6K=ox=c*O$>XWQ4?|@bQn8S-dT{1daK_0Q8%Dob3b=tqLy|L>t~#^|BFxpUn*6a+$@jNJX"
    ">%$$gaLRDgJ|z<7(h#aU{7PbXoZGefh|_g<@=wX;>UaG4a&6?Skk^xweLWLSK2Jt@%=3N<^x)}0xAZfXY4^~X^;__ek0juFu"
    "YCs0rd)ziA(h%J|^-?QiNhV!=Lp_6Uo+7{AMpr{Mbc4oW>r18hwr!09)*ALhCseK=_O!G7NMOOL-i5KrAfLQ|?l(?W_qP;ZF"
    "34`iN=|X<WY;Cx-*kSZsTR<v>lYxhtBhhdqZmQSt3hzqPr*GAj{Q>yEY5u*4XmjEPgJ=`T6rZ4e*FA=x%Z*~pbCK3F&vEais"
    "{@m$z}#7n8Qyk!0f04r1xjY{pI&!2{IF6{#Fdr^n4$st^SFqBezPTxh&F~t9Nd8h{$^?hA80x7rXP8%-!&qlZiR6*yzNqaNF"
    "2d4vn90V6~+SxwjW*BtmQ`KtE}q3T#cE2_pfNV0sd<5?;W@&8<j+R8m2WYJ|+tKdVXMbi!s-K)5u2eRUiS^Le=-sv?Q7-iF>"
    ">zzEoYnJG~3wRSp0+!M1>iP75y{M4Q5Ss=Vzf_&4izT%ghzRSsOG3o!Kz=DU^xEHg9GwLQ@WxB{K_&#{Uf5tjX)eX1mO0ul<"
    "-(npX|NaZXv(-Qw#U%=~}JvesH7uU)=M?{-l;R5xlY#qNiK8o{Y3SLbi<69^RyA#_Cvz;(t@O+8^fR)OxEO&KWRaU@ie}LqR"
    "F8AUJQjhC9&x?X0N&-%_1}ttz;v_s1Fp-!QJ{}M)+}y6?H}j9f%!#{z`YfPy%0FlQiRkn=r};c0T370*Ru1DUsS3&k8+Kb@%"
    "xqH^&FRPM)y*ul`J`voKe@L3Ogd@HyuflZ@oRNAfzuuQM>;DplD||UFfeR6sJA7m?EoSJ{788S=lMtQciSh_`#cA7lGy-6^w"
    "=4>==;@g)$hd*6vwdLb5U6c%=Ug|$ARiu-jrD2pJ)nB^BQ_)m)^6Wr!DIgDeT|IS^a)qJ^1%!_;6hlLF#}&m<_Ptdk7qbZ#H"
    "ZAlDB|&1s6h2ehrXZ=TAguZY_1CiRfIiCzL4f!^hJP<LPz@6M>7A((5wyo$=I6Vozo$1duvR0Lx?vM5FnxPTLBXkR@3KJ<sV"
    "ki}Pp)0M4`!;2C^hy#_Q~Wf2Er!WWg%`cT`l(eeVMZ3{IS;JENm9<m_|3ZI&p!E37yf)jd|fKv36Eby96M30K?*Zqw8Oyf4}"
    "2vVpn1lXcnjN8uA-A|&g7l+32(kF3l2KJ9i20-r%B^t9%(cJj<-T-=^-#x0yQwcmwTRwse@b|N`c#C@_s>km%MgD{-0my4S5"
    "uG`97Kt_!cS60e2)w2^hTTC5#lVf$BL=3*un7osvKgbb>E`pO6Jx$Uqeb(}=qZ-;XgJgFbA|zc#pid=B(+UxC?KW7FM6-+Ap"
    "B-+OX9(x1-BqDJnZ00jRm~O+m5*d4<MCw(XJihHJymg4QH#43M0FH0>5QV;km;j2y_j)I&i+7LQXhlMmrD+wi^YLO&}myD<x"
    "Y0J}3ZiHm<QN1proh%&MrwOZ6+@*Yg8Kh5x$mU)%}C3j)+F36%!E)vDsz@^NUKxEb(I0+{1<orumVUQ~!So5B_9&odSLK&Fg"
    "6L0YE<m;gYaXPnJUbi52e>#c0x(|bCLovFk(*%$$U-dV8aet@2Wi=GH~U1$dq#gq$p(d$?OEg7ID0?0Iw9uk;w1AJ<78oyP^"
    "Lr(AKHJymgjodEv!fXpaIa0(msT@QNNVO~sDH|@LK&4J=x0M;t>camztKHnE|H=3|rvDRHJH^=#0z66qfTiDbwJ#cH(@C_T;"
    "9Ck6E5HHS#8>JSyvex`{>*;BW4b>Pog3^d5^Xm2m`dfJi2qkSfNNC_CAeWRA|z7Lm#o{5K8k(?0nhYG(x)T!SOfr0t7AA|7l"
    "7oZ*2_LO5hUm=tx#CH;zG|7iEzEBsS*uTrH@(HhsXgz4)|KFg5OMCfQRn*4_?=a=&W(9A(a{4h1aGg@dM>Dc1RaiLtx0aQPN"
    "ps@zSyA+5|r^YuP=W$)t29QxpJ*GXiuVIjViPYNuKtaHZEdXIIHYrT?xUx_2F$Le&b)zXcKC_EsIAZ`bgV_Bc?zgV%5(I;U6"
    "!kZ7|Bri9;mQ2nbjhaEW=fv+%Zx$ry**NRdS^|X!d%&9?pFAc~9=zZuw$>;YzSQk@zl$QdW?)Mrrz+Y{8YuEQ(d|$&sf0Q;F"
    "-x6;T74<6%!h#(*s8j>|fA;<ZPLkxT^M`*CndMFU@iXha*BWW%K|0)>ILw{UA1fq;(QzON1cC#EbO<335>9}SgigYp;|vFP_"
    "rig^R=cb9-p=gI?D+QOGc)4-L}W%*RCZQ-Q{DZ1cYC_4Dl02pMaJWPPopL9Z9~Jj3a9X~J^SRR&r#%vAc(cYv!ilo;s$(>zk"
    "qM6OrTSj+UU;)965W8GXk=DoKm5GiH!Zab~49O_`Rh8>&a59T+ff}xlft#+b(l3w!W45ASD7R(Bcw}On}GzCcadg$NR-)5Hq"
    "T^-_dp4K!PBMbjZs{5WA8wSsJ|+ALq~F8}e0@I~-M>=}OZti1b?qd!z#pb_hs12@-GX%L+sUcWMbh+;JgV5sQwgDF?8P|M)$"
    "L_KciC2sN1$I0p}vAqS-)jz7CFiJ$8XW9Ha{G{zGIu{w$e<=DZS@j&GySOe(HOWi_th=;KwrSczEg&9Y#HKy4{aa=l<7|*cI"
    "833C)+Sy}t)Voi2Jg|;~rKb}x0gp?x)Hu&2ni+vF)aUW{?FK$GRZ(^R0M65RO%TMUV0^IzLF_6fS$+0td_gpD9Bnk>E&$Q|L"
    "r0pUi5p8!@R(lOPa2~(i@enRoZUXxiH@yxDB@O8J-_YtQqj}q+^7x>;3!HL7qdK?lLGa#0&g3dz~@IiT=|MO$?Bo2w!C2$K@"
    "i)Eeb>BBer8`5$Es)0niODjz@<EgAtm$|0K%8>wO&ag%{^5CpXrB6Xx5g_8!YU>csci{=q9IT(T>tRh|08d7KDH_S#&JYMc}"
    "|G;o&Uz@O4?oN2ku>`~5xm%$!<*Qc@Jip+aLdK@gk5ppC!;L2MdjiP9DLt^5UiXKn-&zKbeTSpcR!)0(K6qI7L@sy1~30VFa"
    "#QIHK7VUh_5>#@$IK5H{Y02dREPFuiKTre5_8H7EfV*x=W5-5FK;2ug<2U9s8|95s4?{yC2!qZ=-@tz=vMafn#k%z9l6Ca+w"
    "2e)QQD0Mi70|!oEYWSmm^-<fp-qwDJaVu87SGp!D!%6C_v0l~uW!k*U)Kgs_R<LdHIB&FEBBP%%$Uq$@)g(b+mIpX4+qkdQz"
    "`OFdp)>h7(0D?Bki&;17XduXvkLNZ9xWQH34+*AXpkX@-3%L*h4I_*AKCM`o)vHy*+{WDG&Z|!i%qgnH{~%jLi>~e#Oq({_E"
    "~>#M&O8Tr2`<%*k4Lq!PKCtNx6(Cq75nFxe{)P>5_o2b!vEX<wiX9(C2{pb2RP~1hIhXp*!TS;55FaG=#B^i*n$ouszDURUO"
    "v`EpsfVZ#+DO4q=58E123Mc*#sMYn)pyX-?n`k`Y)odW;vkgAV7aWotJvKph5^@;?I~=iuXUuZb^o>i9$dFwi~=_%$GyqOq7"
    "Dh%JEzAA;EJWG<FJS!v;i@}sy?=22CXz9_03Hls7C>B)+r<wQre(de|*831~HEY$(f>-(_Yq>TQI1KA0{R76gtp{h;+09rCY"
    "n@gQ?Iy~y2Rgn11*$a5zd=bIaB*1(?&e1)9Aa*;>h&+7VEAWS{r*H+!Bj4cI6S&9)99$XyiVTC-_L0dtKp?^-044SpI{?CQ$"
    "4O>|*{x$2h`X*Z<9(|Q{xssc|1fK=BLo5_(NV@f3oy-n{J;4*yt{QN&^```X+X>j+FlR@vCE)Ah#&|cf4lsX@_BqyW(bEx7M"
    "wZJWJ{$bO6>q}5;_3k2(o0c{}Ln3A~QN$MR_NR0GeeqBH;wEC(w!4dqe|(rst!OQFXZj%|M`#b+uzaO+?!&I^_W8rH5>ZV`#"
    "|17ix3(ad{EW9D5MxOwv7oAa*OfDzl~icxQeNZyX!NUf)H~07jI`zfdaw+-hkmbS=9G1h}ecS7V##6U~p+@6$dsIks){vUh!"
    "aOa_*K=Sb9?0Oz@nyIXbqW2b@7%nbp-c|cOcpCE|AfF^$gK>&QOEbo66{=4@GUc!qQMK-iK<LFJY)|2lZ2f$*b2b<vl(92ov"
    "rFu3-bkqN%D3linIE+PN)J(UW5?pCa2dKLNhN=#Z$qxQ{ata@9m(ZAemhJ-tvD;una(Mquy1n1c*&;?g7bAg-s&GQXUna&eG"
    "fFsNZM)7mTA=^3h$yUHmn{ys-VT5?kHd0GsQTSxmf3bduR_98`Em|0%YEG6Y2fa54e!rf4{`o6K)gs}EI|+h1r16BL1>(zYv"
    "g;J8GL_f9OG>l<2>7&l5P~9wFs2z=gbn3=~av{{pMbSGBPENc)PE)Vx=kmNfs41T%uMs_1GoEt0FN+ElkZM>PozkOO*2tyn@"
    "6hX3ygz!<XRr178@FBTf*+CUEi1-zood<0*`LE*y^`A219_H#Gix1z^HAL|sR^^bPT+vy?5qV*0J1k5jrwpfFjAU^^!4Hn_I"
    "q)zUpM$3ov90@RqmwBzFi(Z;>4I^J8j4fB&v0F5)My&sLO1VIcOG%yha5mVgv&GL`MGk9I5iV4p}Mzwr0BZX8N&N31@GI{`O"
    "G=K+vWJ-(T$0@Pvpn<T~?gk686Z%Bt)ai<}9Zk1@dDq8WCBUOW6aV$h96mX#1ivU!MG!j{HZF7HNANS*(|E)1F!nYw*b`(Re"
    "IO%P*Z9{C0859Yr`4aGg|tQyzcte@a^Ei#A(27VFM*+F7o#jIh03&2Ix8yE$`5o~!<H*B#e6*GHSxtx4IgbD1e(VIoFA0C7("
    "o!k0;1VHK@bGcn0^{xEH!akwumA)hSlUJ7XPy*d@G#$t(fJmdn=|`%Q5`pW!JimRz!a_T@Yef>h3Q!hYft80#|6Z1n#Jo@Y;"
    "*3c-7=2e(b`{vNiX->Pt<NSAy6{WcJD8=r#B+)faI`ejldid=vzSkP<E!TodFrPQulcZ7s%zlyoJvQI_#x+Nql~@=dG4=qdf"
    "WDuam1-Lx}A>J)#jK2tI@xxfX-$0>C1XtRl*@NWTTo&nftGX4pI7<g!sM-W6Wxf|qPRO@)TTh`H`B9zjzO8HkWMy=-5<VabP"
    "Y>P*j4PXB<>iCzvuGK`vQXByB)7G~2%K+#}WwjeQNc~n{O3bKk0U3dbkqjQ_)bVEbCLDeGE9kUN(EWiRwmoH;D<8%?iZl3${"
    "d?fH0Ix1FEM2&a>Crta)$hpQRm5YBo&IkaoMAzgHL3Q4N}x9ERMV%%zsGr+682|dnUoT|RsUy0Y5&l_pi14;>r$YG03GEBP>"
    "KEA$CukRe9dp-PwE!~?ehSe2PCywB?w~hp$q_mAbM%Ph`$fA809XCjH75GAliCNP7s%1HBsx8u<muG8^~6)u!_r9t%<M+jtS"
    "M-i(^z(1OzT-Cj(qj%;SH%kK-@L1%5a45_#e1{eyf&34&OHYi|1{yz}h+cx7%3m06CW;P8BjN-m?t{1nVY#nS})dW?VbTtaJ"
    "P;7DWx^oR{6OS-~es=!U{suEBQ9U-d4Dp#tidViJAyDcT^j=)jT#{a9&;zPk@@aK;K;u(N@fS}ANf*`gBG`S-PVj=F;^1anL"
    "e0O#fmm#OR0ixhUnE*QSzrqRNW{ot1KBBR8$N*p~(EzaZtIRs=l7ML9FC^MrV%`ZLi$JR=w3yX9GgssI)As@G(}R9w34*Z54"
    "_zcLzUCEp|Jl3o(rg*oCc{3}-Nm!AhP04tB<!lQ;1jj+QR;hdqER%UtgC|mDu`3}lTRj`)X6NUp63!Gx3QDfIu4AX9R#TJ05"
    "w<Oi;a1_Ew~A-#<M{4#6XJtU3B?X@`Y!g8o2Eu2x4%c0fHci6ozGf_!fN1c>%A;RWK4bsH$X9&VgVR4uF0m&Vp#uE*{x7LIk"
    "i!t05}c(35&IfoDJ<bY!aqfs7IdRN??xVDESq$7LITbmkm>vzCFFJH8!{DnSf1F3QqJZC$@xrM<Vv59O!uJ;S4zn++hFz<wv"
    "Avwn(h<j7T+GOjo{ZaV<FVtRw=0I;$amWAnL6R)7_0F4iVwWHBkIT`o}auUbT!GD^c!bj%!0m1pfYVDUfDD$~83b_nMN2>sD"
    ";kl<Mdy625{tV6lMi9hc!7q|OGu*~^=0<R_%wj@jkmU{#Bn@`Cehz@NWfohP+=7v9C0zhkwB8jipPD_8a)3?BuBrc5lm6)B1"
    "ww#xrqf>?9<_H=J*~OKH1km$a*(Yu{PpY<-rgL-%+Uwvo<R@;%w;e89{I7E2XGB9U~0<80c0@3Tx24n-IjIjiI~UO*+v8E0E"
    "oxn$Z3%*Q&@I)8dctAy~kucaA=2UiwR8e0CzWQcr&{l-r27!fxm$gN#%QPk#F@+<50%IUroFkBACXB6OW)-8z2V-K@bB64G;"
    "uD^kG!8>XrC#=0*JT+%PUh4w)blM^eV3&IDL6JM3EK{RH&l?14p$=#@ADwyP#Uk`=WV?3aO&tPfaBc`)HYutl_#&=r%I<EkV"
    ";0u|svzk$!3oyBKPpV>}Fl^}Kn<%_SAKjlr~yM{-wublyFFbo9_3TnKL>~%eC^oZbhT>%Tn1i6ehdP|H|8>$`1`erPody^C8"
    "4e>fmR#f=D4g}^AV3PZI%x~hZP7S{$E(7W>0NxC+&e<BPrMTxxnVYy8AF4f!R~E`RTJPXVzlo0)uED93Ux(;S4a9a51TmP<0"
    "6`E$AIcKh3WoN-9RIQX2ySLY3=0Q&?pocKta@^`j?wbnTnez77JuC*t-sSwN>TtTTE^4>+i1;4fmt44()Cdpa?r^O{O5C1c;"
    "DP8TC=Co?vUa&L2MOyHX>QJjL}Q4!Uz24aBH@NO54G3%R%1b$i>2~k%4Or<+#qh-}umHyk4mTU_-GT0QPo=ivF=rz<53MVTh"
    "d4X8(;QiWdAAm=!+exxfk0!Pnb${4Bd3e*Jl%a|RHDQS0vvT_N`!xDG!#^L4zmT*5w<0dF(iq2P<1dHiC11g*J;2Vz?Zf*4$"
    "=3jje7eW)>XYM4F!h`hU8!*I^Qb-aLlTuW)CPcE2lEF;Rl7)!l{4M-P)fur9Jrzv@x<r2%rodVRvm?0+_hT9G<ob{0}aQyht"
    "9^9O*;rmDKz^P;RNRShNAhv{{G=ZNf&g1*|8H_kp%+ClEl#wd{x5vokz2!hQ%hp~oY5(R;13<#?*A+~V;IV_kauOt+oK{=gh"
    "6qq&0WP>c?(a14j?Ar?oP7ugzB*7Mf5nTxS$??lB<^TEjfwo2s#DPI4{L#d%mPofJ+zwVwt6!Og4hNO%)mwv#Go=JdG$JcB6"
    "kAcl&fOMbC3tuE#y``4_vQ0dbZ0)J+?xDgas+NCNh?IT}`ZY!-wz*?t})!dEZ0L2~e#%C{;N=c>FYey;gxgcXpsA$^@~~$?m"
    "y9{y}jb-&!5g3jd-BOu&U>qW&sNE6&tn3ytOl-`2&_{|Ei6Ewz2GTlq1&xIu^Z6N`p*{%V)%5NJYxXMkt?HvVg43Ll={56F|"
    "M)_(wYx+0Y#YxT$t_)T^c-%ze1-{SBa5>?^A6%0O?n9BtCN~eY&oX!E>69cf_1VIcsG*A!(vBW4*k*YV`#Kqr$KX2WSE0M>z"
    "%%G&>EU{ejDn_3^8UZU>$6_z`32p79QEy#@1EU9OQry$`+oaAiz!!0<tX9Ql61fsbW{BbMW@qrO+-*4d!UI74>78_R31YCQ9"
    "FSlIyd_u1TlbCNGLgglT!0CdK|yc?9T~Q3T`;yLGkuayfPTjRcKA9+LWPzCAT<6XCx~%2M_ElC1Ux3S;osr{Cj$>(Y0l$k<x"
    "P<FrvU#fAhurQFE@ON9G$oxzf^k|uPauuUuM8MfETrKEO4&Rc{?L<S5U*BwP*0BGXWq5!Er$l#Gpe11wjzYgI_M+JKVsx=SO"
    "f@WOcM@fr_&AYjLr<jU2)HO<*m<cBhPdYjFU?@9)+Kht;!|+IN&r9JURVfDlpdaE95y!+FQU$gqp!vV;FQHI3iE9<<LsxKoZ"
    "UK@1N0ebODi0>7U<j@OM;;j|cX4Tb|ei>4>E*dJ5IzaI&(>K1>Np&!@p8|;>N(c=XyCL-GJ^~9nZJ{qKDG(?U|J$6MynG99^"
    "J4~X@1!fW8-ew(N^BedB|1!whv4LpqmmRxY9yoL@-g53fyt-Jyp&*N~j*G0vP*hoWoWnz)Tek*6f)#;3o<E15Zwv#iN4I?Y3"
    "4+)j&|pCj#4;I^xshA&arZfVqf^CU)hvEN8>Qq3v&!s%bus?!g%Xq2oig&-2K)lzV*d2^%0xS_u4-2A2biZKqe2EET!J%QJ3"
    "9#<g(`<AN&H=X7C+;SV*1#9JLL!y#MZ;d<y(hc{OF!hT;=95GZ&!bb5!6Ur@oD@YR@Xd@2Kj|qQ0{(5C7J+@e)Dg-gESi)eg"
    "Y0K+tcwB7p<)RgX6#DO9L7H$a04)Oo1z|DxZ)qn#$+DUZObJrB{Y11tdK{MPME{-8W^<xBC)v-jhsOc4{pMXBSU=yRRwug|k"
    "?)hf}3M4JiB^8nAVHr~LmK<(650I`_ze_5#o49LkM2x6-t5kP_<mW9Iuv}@1f^OYtpa`bcrdyzqgIepswVTra(i?NK%fn?@E"
    "&+6A{p0g<ttc_-wSr|qjOr|(WRODYjrJ{_==@S|mML2LI!`V3xwRV8-oEX6!yp7*#?3154N9_U$Vr^gDigbq#<2TClc-y`S%"
    "+Cgxp7SvrxEOXau|XIb`qmfOI0UT0%QyhkbIyX#*{YiVCB#ZsLQfl0lhvet3(T`XcQdIw0>}I|zSNq>2d4G{_)>QRwnW!Z8R"
    "bPBxaKx|$a@mE;~A*VJ5CKK2?u4tQQ%fdhX@@x>U1fG##AQ2f2qx&HuvZf#(!GNM}i=BGuwV@OAy3nG9sBfio-{4!ml?T#A{"
    "H&AtgU-QZ5ydaoDvxB?4(`GZUh7i;CDSqF|r4*ix%mbh!;KRoE6I_%gg5#?cd>Kd$uwJTCQw^aA%WG3ugIl=$nZDZE>bV*a@"
    "Y=srUbE5PByGT>Dlxa<ym!haaIW{YUoC9)l+qyAYiWVmh6_4$g~j#=BtUr-LP(y?Sc+N&66qm_lEjrL@#(rCHZ!0&Z-=-Z7B"
    "j$2s`>QAj(Ds+a@3=i-kI{0d%hF_Ccpg#E|fYVz#F1e*6a%lV-{5E?UuOF%++u@k62Pg#`<HCgqfDAYL9^GFf0mJzqKs_(;x"
    "4{g4x>iMF{y2%S5(Kd#XktbX#0n|PQgIj~dv3+YTTkFp<dBz4*Ps@o9~QM-GA)_HxmhB$T$6AXEN8yC5e|T5mn#fdU%{=|4A"
    "VQ?P7#j81M5&xwg9}$&?!hf;y3V<rE78gnXjWWd2&Dw8bJ&)qcT@Hh#$|K$3L$Q;S!cbvE#t)07KkG&KUkq6#ZW;lD-mu=B9"
    "r;`{)bwWR6+O$zCzPc=@D9SsVTmb2323kvPXZJnl8|`F0&2tBnDj7q`w>cK6GCWder|UydI<cQ;;Jso((1VmNT%dJL}5w74#"
    "$%BoXuh%&F@-Hp=!9f5~r1K*py5+{%U4UMY=L97@WI0%AR1!W0$1T23DZ_ggZO>Q0+Ia%zL8H`I8<H#VVCo(2-q23dRangsM"
    "o}SLhlyu8sz?716xJ+iHX^qJq*vp+E$8*e-=+tf=!PVj53_%dUQKbP6LnjE(WCAP?WJ(O@T_2x1e;yx^71T~Vwbffp5Q9r)S"
    "nfY^D}Js1JYJS9Va#)pX)_29D07ay>uMuV2pMT{_Hn8%cX-?KZ==#Du#(ezG7~I=KU~x*?>CO)Naw&r{DnYGiT!bbAS3aJ*T"
    "g-|8s5vVg|DLia(>H<|IEl$a?jzH;1@4^6*m`(IP7Er56JoqxqxF>6=taYQP`~uBj;)$gx=K}3ox1W@i+Au{OnW?z_VL^772"
    "pbe$c={5X9PWCL}U@F*JH5-rKqtFUgj0m}PaJ;*#V#GXRpObfSuCG?TUbEUZ=SW`Zts6s+0-px?hpdBKv91EBX<hUc+6H#h0"
    "L3>_Ju<_4(c1d78P_qOZ!F@6vy9{e2LcL*YdH}Bae-?DcY7X>-UIxyrpC<?Aq{(HtsyJTrGq5c8?rb#B@Luye%HQvW#Nb+W3"
    "qW=2n=(pO(KnWm*sqt+;K!*!>uEYzngNNG<e9mv;GmX7K`wSq@Zq3nP<8tE2O?aPt7OyE+Q1u;nEvZ}j4Rcp#%w?61PMqnGR"
    ";nS;6oEcgvrd4oi#mQl+=SY>y8xUT@Uu)1#2`Wg2SE_)L{-8WMRw#0{IYl)w<$*evRWu`NIJ-<P!Ft@a<*FYg6O)*0!T!G*g"
    "DQ|*P}zhR*#@t{rQ}QT>+FIhN-`m)`MzQ)t$`F!o%~jjcfMh(aa0{&WW@5kT;C>na8(!>j`4Z;m(B2RuAGML(}+IqoZim1iY"
    "HW9%Qs}80w}(>HgXX=2nZlsAj(3FgEDlFl#(lIx)Ij%yt0uR2r!+2PyI}y7Pg+j0`aE1b6{${Qnwr_&{qfWb*|;PBA5>xY-K"
    "-ymUwwi<jbe^C$4_!^6mTI4;b4U_QgJ<LH)t871&%_A|bvS?5&WGeZYQOZsSXfm4o$KWj|lL$jkma2mi;;(r7|5DTG!gCK}?"
    "W>lhZ5T)wn_*L)gxYEhv5+{dII4DRJ&EmTKNY+el?HbM$A3*A8wO%9FvPA+{&?bAc*{p3ytKKm6x+Xelgt&s}HD$D98C2}*X"
    "wXJ=$U&~m@pscR_?5~nc=4%w(W)OGgri6hn@(x?a(UpA+wt+{{kYuCBdAFX1rA1}8%DRIY?=kx{aRxstzO<@;J;P&28!M+B2"
    "zjRFB%#DamIr#^w)-RQ>FYv;H>m<U%QTf3L5y+`4PZ7fvsqJ$A%8c!x!I#cTGQne^#y{-{!iEqv&y6-=9~}{@6ikm6oaJbV8"
    "d%2Ldh_c+hqB2o~TtYvcZ)f$wWwg4XOK0I1UnK@h8B;BOHGL2O4<d!sDCN+^t9j2{i2!L?3aI|B}~3`V7kl87clX+$D|))V2"
    "cp3H&u5u#r9GK1;>*sN_yaR3AmaGWTL<qIRnt<|?-+68K%GS#<Q;=J@AazM50;2ihxnF|;2sp1iwefI7_I+6sj;T*dBPWkrc"
    "34G_s2*!OE^}4`l5T^V)O6X62kD^Gh$%N`L7Q@JQD(m%aT8ZH5s#u2lYn1jMkNmOPzr-B#ah~~j!f)a$tr~ud9YHYpEP(c=8"
    "~=rg%jAJeZ^Apyd>uFEiny5NfF@A%Iou!=_jA<!PCG^;k8)JL5a^LK3i>PQTn-epzJb|S2EhY-Ma<*BwP)}<Qx!0rQw0GuZW"
    "08sDroQ^2x8-L_DW<A;YSNE;&$Y5eYSvuJXAkcVu8wp)ajqL2$YTj=|6hKp6%c3F^Vnr{-rbnw|oRmI7C*uJ$CEH<$RR=8PV"
    "Ld;|pX>Dyt>N6`v;~;;2NdAaOSEF~<Vz8_7UcB>rY*2JgvVjx&$`!<HXSg4j^pF$tN&p382)ZwJrdRrv~nhD5f_P?Zj<+9B%"
    "n5lpo`k+wQ~%GbtZ4y?7rX`>wg_V)Lz-?RiYpKWJ6g!c110!%qRK3AW|+nt-xo_rYap5NRtgpWv;9l?Q%uf{L79>X1_5{7&S"
    "tOZn+Gbd14Z%k_(!~%b^w_5?Y(zFrqbO}V%`Y$@eTH_`<)zglL|L)D;t@ROL{sjP&G+q(}v1(`lAqZk~;1d#}qOt=}I(Q8}-"
    "2NJFbxSyitQHH*im;WSsm)iDJSBRh$m)y$YZ4WYVAe!=HIr4gF+r;>8(FvFbCdgPrzLBLj-Bor)-kuFz$^>U$O;^q$YLfN;C"
    "Amayl~%trF#;wGvQSUS;5av1o+AQdy#7~h&nJL9qs(gNM<s?d%bK6z7Z-K9)7=cz5HS}{*qlv*61KuuW_SC>m{mz*N-Eu13m"
    "VK#&VqrOfw&+nTJo#PvH}tOCW2<0lc`mV+Wg%`F%Ixley>dEh9s4S`4$b0A;~ZR*swi$gt>~nw{%uW!T+cC59+uD2CYMw^5l"
    "OOkz&>xRCR4#nceQ%$I14BnV>7&_F^E#O6+dg$rczaPvp-Q<-D98AV*~<}e0Viv_BTfGlG=5@IG#jxi)nX@E{OPfQlqD_XTu"
    "U4XPK0k#`Pa$A+$irB>ySnGTltWJ*-0`ol3eYz{d4qADM&z`%0-_0Jv<nvDen4|j>u>&Ye@CruuUx^R9$MFs2iZ=XJy8nn83"
    "w4*2q$AT9iVKSWdmk?K#UC^WKr-Vf)(z<s`Bz?G^}3_RkpNT7$DAAB?q(f76x@Q&+#`_f7dJ26-x-x~MsV<w8}T#qU&ptPjv"
    "(tX$QIyqfC-jC)={k*BmI+Te-_*l;_Nnao=vGo;`2CAM}SG!$6wc`@UA)sS})MJND#!Dp@D=Th%MxZER~O-Jah>Ew)rL8;+A"
    "lwlfzz-L0&{E$-2#)QkOTWpjIR$b=I`h1bCT~-qmIiY^DQXOGj`Oor@xK#sOeFHmZo#u3b(&PfF}cLU4&$5g^C|#VW@GojQJ"
    "^ax;!S^%b;dPtrY#*w$o*FPCp~YWS9N1((Yl3Le+#{z~CLuZ%^7aRAtkGnR-Dt1(bz3Ft+mFIu-(YA^A(W<VVP@kd9g{kHQ^"
    "zZN+Tg+#!FE*YA1d^{Dj@cH&UKHNG2v`zrx^yZBZLl?=thhK&dPTzw&awQz*Suh_6{7|ECNNb@uVa9@yW{Ac`8I5)7tf}*-B"
    "mL$l#s3k$H+*8s@o*n&;M-;oz@Pg%fX(e@KoG>vga#6VAO?VO>16hyI&v+3!M_W)@glCw<WZ3h@{vY>4yc&A$ez^KB_^@!;R"
    "LWhYq6->u890EmH}WgH4?AKnHnaw*JN=p2w#9_IOYORl}BSX8=zGX_}iHoe3%`?>0^&!vs-u(#M&8_<wIBEJ>o@tYk3&s9T&"
    "wGM->jT+VC?<_jX!Lim-_?{-X$STq3Y+2f%=l96PN(_dS-ceqITQ0>}I|UO)#Ac@6xmyawLX6F_Dj@TNCqFLOhe%fnZ^1V3}"
    "`ZrqwJVV}sL;yK6$431!7n!m2wx7zus{Zyw&cS8v^8<hTuuIukP$M$(P0tfoQ=${q~aLV=Ysrq^R`b-uO6#XX%Vtp9Y+XO)n"
    "yN;>^a)2|8(&#1l$>0&ZG+V+Emc@Q#Q4w56%^b!dr9?dtC~NV#WniaUt~CP2255xc@)6t)S0(EG<3EyuUiRA~wR1J=<qR$1<"
    "6PjQT5^B_@TK-V-kH4`&prCTwtP<sVkKPl(l^PEPd|v4WQu6bNEH0AHe3n`=5n-y06CS~t}qe*q|j!Po~ZdUzW;0+I00fGfJ"
    "uW74dr=d{IU)n3>x^!(ruVJc^A+*v1xn6iu>in{u}V?ou{<}r{Zz6>QYDj3!KAc3^_G+C7qsH1U2e@qQ|yH$~N@NmfnFmw@N"
    "1k0cx(mSG^kkb$u^7^+%DFJ~~^_+K?cKod*ph1VIcYe80?=FT=as=kUr*83$MvL&8CsaXkUcf+G{Cl-M+(tYta?><QR%AqRk"
    "UED~aWas6_#N4aI$*zZxIj;fL%2w*y7sYRO*I2m+M8g=l1U&q_nA)J2db9BEV2Dt5MPXATicQJm}J%fKSJdE+Ci`q<pYcd5u"
    "IV&ThP^#;lub@`n?v4^ZVZC<|Kjxr*V|4a|HU65iDF(Eq!0Dia7lID%@@x2o)+InwWdTiX=-zO5L<(Q!=Vx)`+S~A++GBWqr"
    "3x_*<eCg)!bJs9$%e|~=gJW+q9l%lchl~M5<5lH?mt%PN34&a4vEARe4KDQ`18gjJ~ESs6vqbjY!U>q4WR*rAcz4M&>BLfd<"
    "buLU%>4wkE=6z>_<koSQ>|`9RbT4$<|T|(6gT9F1SRwz<RJ~q;NAb5Ud&r)1!QW3_>E+)n39Z=mMSybUJPLoP&n%VcPML8{+"
    "tz#thziwgWUaS?QY~mP`JCoVfT7e6;y6?#Px<>~Q4U9HY#ImNN~a!f;1ry@XNT?)S9McO-3iTErL7cbP#n{uQPbo(Q|Xs9OJ"
    "L{TA+R*Kt4E_~cX(U{ipc+3-E$g@bbcB{$<ewMTGgp^PKQA!tgJe2#3uk+U4lCa+1S{+lr@&gPIh%R|3zJD&SxdC2g(Fso7R"
    "0M(-BxrhJJn!!6-2Ot}dBapL$d{zm9*k;gxLJ-9Ez&Rk1IfS<skK+#HadWPSk-)(aLY;sNqBerbVT~<W*x!A~7F#r0peLJPF"
    "$aRZ{06a<F|er)0IBO-RoSa4%;*ujN)1(-NT5I<1RR$``k~mFnou`YNr3AE!@v#ALzsW&@93UI3>+-GU%t64@ura~uI2?4S{"
    "#*tBd<zalsKF(qNuP+cd;CUJ?Y;`Y^RzPSxzjnaAWKRH$&ua8LFr8%Vs~KOdu(A6_Cdz&Iu2Xw43;vSHp*bE76{P8o;TI{k}"
    "WnGLs*{#DR<PqxHw|vQinBupCA`R~!DSY(sk{dXA@c&aCmz2>q#NR2Q32u-5GJVl8SSXHax$)MbE{IvyDhFR5RF&eT1CAjc;"
    "`5bFy~rU-)AMpPwO8M)FZa>axARq;43ck(#EGnkMW3=0PpZFcgW6jPN_+0#WJHqPxRn-$H8=}!2%FGVYkmrG9W<ig*JjkG;c"
    "z@-EY`@FZ`>l;qW#JKM=X)i4i^<=;W>46Oc4~quA@w5-jK1cU0VxZW6`S;5I5<GzYeg-4bK~`{-^cZ9bVfK7IdW0|*K4rhOj"
    "A5bg`_tC7t|Z64<bH)E4??N=3yF-%eu%Stl))=7?*up|+xSvr9`9z?qBZq6Af`6FwVzu$A`AO&!*93l$F1d(zISBW3>DwOuv"
    "YVrwpH&+a(qkF@hg!()^&b5GR+a4cz>jK0JobR(vbqw%*XSrjlXHl;5TN5l@kOI6#XX%Vtt{B6hRQ%m`i1D&kgwZ{{6T<ThM"
    "}mW75^#1M~!3i!xc0xHuvcJ!bt>?agy3HSG59o;r8)gf(kVopjsvyS7sP3P$8)fN#5w<UP?!JJX`Oz^w2vnelPy;R4?F^b7d"
    "pg)`fAZ;2g9@xZO}uiQD@%!)d4T-H(lM6S5GuH$;~xL@Y_Md`QXTah*{_I`h*i0b5(@sF-Ew!s8CuEduc^Y}+^9=}t&2<SWu"
    "U~=R3#2J?eGMG4WC4M`50<SJqz}rBhDUkCR_NdY_=JwR%_naf`2uL_OOa@bw{iHI{bOuw;a&{LK>v{D#%J`3*zYPR9$31-6u"
    "i*#g4+G6-0J*_g5ClQ&N+LxQf*^=(2%kp#+}H4PtbpRkLHrb+#4T<SSFunhKsf>m!dW<BGlEREns$#EV8YPvG3;&ZNnL8FFW"
    "u45yD`11OD>YeYL;7#qhZ5I^JIjEg83QBxH#SNFg@MDw~mzYm;6TAIQQ_t>;bX6d8_v#t}af1H<S#ZY3~QfK&69o>w6cL$Y|"
    "mC*pS>Qq+|lAU&^*sB@hZvpvePm_}8Ssl<VVfXJ_!?-1V57J_^X=YM~9=LU-&+IWl$~ezW}`URIhyrc(xH0PaC&Z47f4StZn"
    "HBJ<iPS33}PCD7+C8l9MS?plVtUYzL(b?;d<_ZQpIBNyHqqHAV4@NrK1c+hJAjWYmR8+JShg4o^cq&pBn5W5)_-4R1@ix=TN"
    "xhHX(Q^b{S9z)Va85}vK6Ch33fapi`iNM8?>BL0cj`+tfB@Fn!qiWLdPjfsZEc?{#f#miqLO(-eP)7c^>>-+P$Mv=*S{lBlY"
    "J{H&TBuAo_|WOI_}F>M0wA^?HhhEpkHZbz5EL-sWiak$!!~v@G!}J2xD`e2urSp-tDm>7{k|Vywfswc9a~H?A|CFKZg!v^va"
    "bF?zy(f95A$w-6F~?6(4NCb8zVsL#D=E(kL<fvR>m&FJ7*ul>#J21J&t-^U|2f3tBlfVP%Zt!?X@HJ;cj`>`BA4rxih$m^6O"
    "_zCPyUj7-P412&4bKBYXI-&W2E#5rQFrkE5)OFSTlTYv*Ff`6pE~#0@WnAP8c2LKy%ALF@>epbg1p;5X~|HNOOw9l;N0PT-|"
    "Z9yeu*7#FUN^o(*>&*YjNfr4XVHr)wd7dv8;$QVdW+U+^IR)1cwb;*o^)YUBhdNN&p*$i;B(aw(OaaLH)7b%gEjxOyecpTp}"
    "RKcfn!?JPm$pPIdVpotGlm9L^i7WXCiY*7@dR&QYL6h>Xa>6aTSGb*dw8&?yv_<J+Y)A%>8R@K)c~x~~J}d~d#oT5R)7-}i*"
    "~VRsI^OHvjArd=z&pKR2Ch>&BKIA-1@Emtgx8A~P%VsMZYBWpfdftkRp!8z3@mCz8tz8yxd<IOk&vl2)FY$6yRoKx%VZ0rq-"
    "8~s|M0R<PNCjiWvc!^I>$32z@!`CYqANcog!rX69lnw&;*Jgh@DGzkA$4STPl<IMyH7D+yV*#M?rGz;V$w@=t-yT_N)D8%g("
    "LWb6*w2PBr)Kn$kWQ1q;^CRyJC*ZI}VD;24;cY11+*6cK|LppGzYc(xSaUyfgm=fC=22Wc;eUB<-4ua*B$IFCY&V}FoAg=M;"
    "5ek1s%qWo5*-(y1Cm)-6dYm@*;{m!Snz8-#r)Nfm~e?8--(LRxA2@$6JX9OPen)sjXIefgf4+zcz!Rd|p{_;^-K5!l0hhzAc"
    "!y~A898Qygcc7#F1!eH-iUcJ}7&&dC^QA-yl@Oo9SSVO%w`w$HV~ZWw9w%)#{a=+2AT4vi3EQ8lk5Mg8|ExZV_p}ZoXg&qVX"
    "&T=Mg4i%<fFTHC=i}~?;1d`by8$0;--T<k1?-a<j0zVO=IH+OR`R)y)`T{ws`d;gf$DG7zI(|O{k{|B#N*V-<0g;PY`_u+^h"
    "DekO*)hqrVwlOaEX(x7DN@eD^tUp&NP8p638MppVG)R@&m;>exNdj`mDeqo&{6lf9mp80)V==eI)MIV>lWyxPIfp1~~wd&zs"
    "j)^VvQ2ZL-a&y;6Zm?&GLv<8!Tf{G7NBXgmXSHmHk7VZSWzxe~wc9>=#<hrpW*q9HLP9Wb9EtD^l}rQ1hY8u~m51Trj9aMWw"
    "2O`|dV!`3m29H%}nn2dnvT!;Dr#`w2%PPjx<2554Dr$q~|oVf%+<58uDKy!0~AT|^#0U!us=i{Gaz&T8xnUy~-ConQ{HGY|W"
    "8MnG6?ByAh8Ao2}1PHEcJY6V3CoT14Rd|{d&P4PsIic@oMfXg&lXd^QeZChdghvrXGgS^J>QN*v5ZL2n&<F&sF68m%OdbDWt"
    "2dk2ePl=F@aT2;mdsO_obz#nDd|7U5LO1Hw((4Qce1o4axkWr3T+^4BQtjvmhZH5&3`8}{@WJ=&4&Q7&QX6pCi9hj7};|%-r"
    "0B<FVCODXi&oZWPp9hA{Q`Zlw-zdzL=DK(;0?Ia2}2}I?dmY_9My?Se`Rw;rZ>p6t<dm?AMJ$C~^`gLBzTf;GgPqfV=?6nRP"
    "ux1VIpK?DknFK@hu&vQ%2#`iGT~8NUoa9Xx;=ogyxGb2ucksLD_nN-KKnNxVQ?)uAh)C=>OHg#^udWp6!bPhI;8+00CUMf?@"
    "ZVqJU}=6FhosGXLcwD&kpr0ylICh2uo;C#Wy*_?-OJOi{RpP>5~v1ybK+%Er=PvPa6GD_{JXS{I=CQFD+364y!3y<@TR$J@8"
    "R0hC?BK2<7g+SJ2aFjrvbaZ6B)$!mLfIpkNfPW*dhMav6kZ0HRdzv4+MppM+hxg9ji(3mNOh^}5kD(NB6ybC`GQ^vkEV)qQP"
    "2`Btr^K%Cx6&LIlxdj`0JgAS;(gY8v>>Ez{b1_D%yvi!E^yBA@K5bIeBbP0p!GC>4JwTw2!gPn3;=>4b`eT&suun!0dMk*{I"
    "D~QO!ZRyT>CM+EK|l+ZXP4jMJHg8et?q0k<+Q6(JJC-l1lS6bN?t^Jr?ygj(`<T?w6YSrKRz%CtEr7R2>>rx@@wBTK`s)X!Q"
    "q2)ANz#47XH@_#wQAKiR@fCUze`*gk>VNB8Jqq@o4n5{mEUcbZ;kQvO4~zG)Wwx}%I+*9>u1SCnjy<D_iiKC~fg&##~HpV=#"
    "s9l^c>SK(*t_v1Ce;}|IpA=hDWI}9bkQDJWAxHTFgi9D|G`Ox9mi|qig>Fv}IRtA_{r9M?(v7|}lG}c-W)*I9~Cj-=_!1J9p"
    "?ow_4f>V+3A3+er#zUS)f*=T1m5>!6cMv~XI*vP80XOH17!6!hg@dBt$Z88Tn(eB|V^1r=XgF1lf&~-$b#wqE*K0?(R?Avev"
    "E~eb-n8NPCl0_x$JDfI<P0;O55Xm}6^=);4SYv?4CkKtGTqCF4aeF068Rr;Gx!d71gs8}T*s>Ok0Se0>eg{8FTl~FmJ6f*J="
    "gtO8~|II0boV94SI|WFq;YR_sv<nac%-=sCITU>+<~^zUrIhXT<Y(b)f>@0w(8uUACp7{T1#YtJ)4Cp~R}klQ6SLp|xC+D~`"
    "n)lX?wdv4$Tx3!EMu7-htp+Wuq)Kp&k4Ynx`Jk8|9^|7*?R?eoKcd;##+=Qt4rK`aGj01yO0$T<eg0qt4&C!JAzs(27TAfLs"
    "p$l_+Fh)diYvH{m=u4Tv3`cb}+$ms~65sd107}FG^m+CUG9Cp%NQTC~kHdz+oB)TI6su>4d0MF01aqWQu-g@CVe6V^%VvdBf"
    "hz*4AmG25p;o8g?+D(BmH=9}lWUk$w%R0Wa6V~}Qj{YmSZQyE0fW$lt@RZ-e=R0*k*VK27+8oNVz3jGsWr<7%nc;Cv9K00oo"
    "Ov9t%bdihSH#>@fJ(q|2wDBH+6a%M?52+2^0jDRX-YZ30<7~98S(ZRic7#El)Iq^b1z6Es`-~vpv44cSb(Sf7VbwI@XoE9lY"
    "}4$VmZ)&Ll6Y9U}UUFup+Y6!*H_u@h<=CxWy^qGB<}Y;p)2IGIMnOt4e{*@krx2PV=-TpfM|O0I*FO!Pol!b;|%qu1LUR5*c"
    "M;Xa_)8U*X9Bj!LU#9JRp5RNlu^P7B}bUWyAR?*VF)bWbDJpWFe7>=FFq_%tq+Iqd6Xkms4m@Hch--P(TT1PF!SOj}Dk`ft~"
    "puh9Xpr5OOMcdXM1QUQ*!HvXnDgP*QV0G+1+Ilrp!q%(Szd@Gy9O}QNIESGVFXA!g{T%TbG4*VeeNJp0r8BLaiIIER%zhK)_"
    "pEu_xacoW5fc<20-7K{RpesJ8*AZY&1ZX(|FUSu5XL}kSoS%U3o{!4Y2!bFs2O4k)f*=+nGcMuogPT2wcRLT`Hm8J3-JEs;3"
    "^NxQurLxNpgRe~!>TR#WYFaU`j5qj->q^0tTZuU-5VH~l?i?Lbc9hE|04P<m4Xqztix}|f)?B%hQF#!;pb*m3GE5GrxEK9ze"
    "Ij$!owTOqbRmG_OL7<jOd>o^-YHS`%1^JkD<Pi4uB=~ODrd+GL9W!3T-?poA}P$OE7ipp8$Dg#ox!w#HI4cCAZ<<oVp7yFH~"
    "?b&!Xfza6F)(TP-rHjbHTndVH`3FH`?-bXk@quA;IxQnDL*ekb1+eP%q)TO~|JDAp=T=)gyv1*kg$U+>iMeeFYN%sfcZe}W)"
    "39V!7J2!dD)?*fC@l79OFJ}AmSZUjGEI)RsG^0*O29AQ~xnQ{WC$(}%-JAEdk$rT$l=`|S9sllz4SntXAViW17XlT;^qd(&s"
    "WBnkCqzVLq#28$(I}+Cy3aDhpFh74{Gk1X44P?gT(CFp(#-SJCHW&&44;@k3xU^c!#n`RhQm%1Zm@aNjw;i$dIygEaz<KWD!"
    "BzuP^N+9G_~)Z??2=pYLH`-NZ1!=C6~-W265MAxqe5j_^$4zdM$|8*Ba42%SMk5MOM`iO;lQl40^+uPN$0_W&#*HN?1dto81"
    "tEtu&L5a5RQ`i3-Ex~Kx6({GX4pI*b>MAKoA76BsB&Rbq{El<){4|KJD(o&y~*M4pzpId=_QKkq<bAgg{BPq0)kY2}3`6*gK"
    "K5Qbg^it-8^LtV8<nf^8WD68q$Egt@+9docvjq~GCigg`|)2)qDS=JNQJ_DQ^ZOSYNV$>a(X_;vm?_R3*oe1@FqD{rU3C+q$"
    "fe8<glDa&tTls0GRpOcuE0nSPf522$nahA7&!X60}F?RS${Br9_ye#t~G<{=Won6!QImt<5+qP{Rjcqh&oW_l9+je8yPGj3<"
    "W54bFeBYnz|6GH$*6cmAhcqEpzDV|(Q}x0RYDD=}^Hz&tV;;KSYldbAMsUs0U>v|U*QVUv=0$#9dd$^vMLH1DqvlwR-^9LIZ"
    "?Fp)!T>FytUk8{9kGeJ*c1yG|MCY&9M8Wgpf0ZEALV}_sf520L1@KaxCW(vvfn5#q;J1ZF1q<!%vh7+7k#o~Xf#RaO(Dy<M&"
    "*Z!h<YB9n)X>Od*pcpeK$^LpJ}&wE9`?pk!=kiA0&6^wa&yD_-tZO_=;0&d*1zrcmES1TexV)kdTFHQ0BJwzTJ&Oc9q<g_o="
    "B8$*|!f^E>5wP-INE_19g!Thks7<IyWa_s_;ZQ5V$fN)tOTp2&N%;>Eue?^>#E7)$r8;XVt2Tco?qq1XD>folZVIw8GP2hC^"
    "Cm2}Y%@`1LkLT)dpT0|70#GCfe#GvAxvr8zN`%n6hucbMkJOC61awub~+%S~CNXgSPt}&|ojPvGsq`!WQ;m~@Dw_Wkm2opW&"
    "u`GXCNv}K|>Bn%nO$@258Ox|gV1FWb&k_QFsDQFq!itF5Vc|;4G%&8R0KBKeuHcF(GY|dAq8+6a?6ZJBiZjOocroW>N4glP("
    "<$>|TNHFP7A?f)>u^b8#YTPp;4162HQNRIgOUr-muEq7ea)u*r0zmr%;*U{E12=|PKy`2P#baWby3h#soJw(OHk0aaQ`kJVk"
    "E_dWnw!ouZaDbY$g-)p8ez81Hoi>?;_M|>W}o^hJccb(-whBd-t9kcmguY+S?)v+%;ZU{q=RtR?nyH?>$8GKfYWNCTPM)I$x"
    "6hLE|rAbU0e7dHw@hhFxY#cOtHY?LO1y>`%O{<Z46pZw{S0zSgfJ+*R3vKg?!VNRwz-g&QfNJ9Cg5Gf&-l2A{U1_F=L>xcr?"
    "_ndIf@CbUqBb|AOkiV&|1T|o2fmpV|fh5y%IVK@Ao+ZZ=k+d%T6#>HWg<Qsgs;-F!PV;A-hbQB=SObqM2yFy8n)(!dk>?A^i"
    "Azm>4`(C?aLQ8E2B6&{1B1|kamRqh2Efx*WDIxUx;9mYqCe<!OKid28o(A*KveHLGQeo)xJ)d2YcTK5kPvXxs7SIKj@)WdQl"
    "PV_g6zW=JdT2?<*|U!q5c>Mvngq&NHt*lOkTI$KgN*CG#9O=@+-EscxTr9OsB#jx*rKOGlzp?8=K7p=%=ClU@=zjR<Q{iLL;"
    "Fi?yjpviE1KRXu6!FfgM)}u4=r4d-Q*7CA+3d+pxh&;@%{e8s31P=c2XKkxecU;UeTMK-W@+Vz>9HKyo+y54@M~eH<|nx0)Y"
    "tl7HxG1=Pi@i+4F!fc8W)J3p`<x!k+U14GezOf$9%}xfQwcC<841=BTsjCv~%K9MpHJmP?VwH`bF^rC=df$K*I*Y#S~tVM!Q"
    "gaivCzzmv1H6T3guw9=KU-}jw@ggCA+gb!QqFWmy{2-|1?OAQ&MfkhEiGJhfzRj15BhkC>HkgYta({w6b2HAes?a#Vb2gtDz"
    "7|zI#wIOiWwaxFGLU;$-bWzS>cYDA8@<h-yXNC|I7sDLMw}jac71O5$NAsH%?T{)x<Aq4QyQzKtm3l0z))6;2@ubdzNblSGI"
    "iD+iNMDu-^X)x|&EAsqgr`)jFJ{@1E_HNSeV`#k-3S8<0sp0xid0|NYWldx*2_&`Wl^r_;~s}QPL>8Cf%!dl=PG4bE#qWnc#"
    "fuLK|*ln=uQl3wKCk>Q;HsiA$|3Ga~y)7<^3?(p_}jRwSBzDQ^*jV_f#u}{wtc;8Q(PVUJg-cWrz#_%3lf_Lxw5|u^<+ANcZ"
    "BGHAfD_03J7-hUl%9I;P)Sh%zoj$R3Wm&<s?V7KYFp6%DMueT|8c(7WNylx~Fm){o5;U6*>ev~Rx~ECmUmUDQ$|<R$ab>^pv"
    "C4(GUw=dw0R<4T;<J&bL|PvxJ(8%dR?J0+PJ!+DdRQZyDy#$;0_hm%px{%)?lslFzf@f-NQ)jvF7+B2bn75+*-9+j)f75cXl"
    "`!78y?AbT@hecPwf98K{(+QXNQx5(F%PAfWhGESYX+&*b^T!X1X{(^a*ieY4X|e3=(v(QRAUnVR`9=AAE0Y(VSzrtW=#coY*"
    "50el4SO6-$=&coP&6gW5@>_^D<pLQ-2eVYY=CmJ5369fRVQBY51{u(CwSuvDa!jm7KUPSoAV~aps?1LhmYo%x<~WN*rh{C2d"
    "V^dr5_+0!srSTqaCqi<}zHxAeAiv@haLf554i3E6$Ql%K~yO)=C0PX7Rk39jvL`4U86Mje)#z+n(Bxqe3)HmkVd9U(s=-)jb"
    "ukQ+*jxvu}F>w>x$UFy9L7tWGiM*(>=jf-b&pOX1ly`>BIZcH!=CdM)jS#P}d{zS!uh;fb=_D^71Ha{Xzu$ze$+&n)#2(%nQ"
    "8pK(s<w!oWbggt9{#5!EWYTb@yFo`{n)2_v@m`SM3=@onb{i72B>R_CUl26xAV3JoL`$ngwd9JS{V0@>!7<faq{oD6W3d$dg"
    "?H@r916y$Pf?G1gSSkp`!z!O-b#uLuXFDQD7OER!joPq!qx~7_BYFYqiceZTGj&q65?MgYfVO7q-Jb~vG8188YZMFhDIxS?M"
    "P4dvRz9;iDPh5zg|$~AjzC<x?04lw7t&omtt4+kZoR44A3hKrX&%Q?55J=rT>A!;BC6Ls^+~_!o@WUdBY7>uOQO`qm+OUOBp"
    "4z*ARKbO4{?}zB49fTs=BYXUzm&`1uyn;5=h7cl#3(@mx%$0cNxlTGiOjOkAnmf_BpU_<_1C7DSOm<`|nLchUKh6`4E1^q)f"
    "wLe5<y*pKPa36V}kN^g^EQB{BbIcpd*|KjHJPw{AG519BZ!Py})d*RDXY50=gLqj^;lQp_C4yod?0d#ejZ<4AtD&6;=?7<y{"
    "B*YQbJH$R7B&zzikJcNAvEzv4Vv)r1<=5@)07lj?ATtc(J1}4}#V&~xpH0G8)dh~{m6TU#~GJQwV@7<vZ&^P>%464RHwu{if"
    "P0{z!#0Ym`Z1-9B<|wAUVgFg&U^w$Oxb1}?n9C{t5EPmbPVUrUCSq1976K01D4CSRIh9tvc7&ws=9exUZnSshZ%-k^iy!gBv"
    "KBYO4CE|rCcd4W>J6KGi-@Shn~{|dtuwEfHX5qxXp9w%;9(fBcjnD$J#1i}c^om-;}`-nJaA5{Lf3d3n15*_Ml855QK-J=7r"
    "TScKpF`qI85=D7C7CKj&l9G%WE|6X6FR7s1S>~dKA@frH&|w`>QR3c6q1Cu`238_&ecNdcUvG3XHgWD=TZ*)fbYjqAYNG3sG"
    "okMf;H9ih5@JO?*NjZ)^rTQQ*tF$&-!6qVZc1n#VDf?zk!3ir0R~8(1wu5Uhlao8aPnj0<7kEhWQP2oW8zasfpb%}1bub(hB"
    "rAK_oD(w)Ru&I}Ho8gdLe-lQA9Owh3(FE@VN$V8fmx;x|#uUl@Jo1320id#rZjw7ckU%aV$`Ba2S&I}PkXozws05%<c$!c}|"
    "iJB1i0Yp$F!a(t=!pLdTK_@6Jv|a~*R^$=mw#H4=td#)R$n8FqCI<VL>R^Q?+hopz5_?~BW(M8FzE~BF*l=<dusb~Vq6hvHL"
    "aD{t;_e#9nxhYOug3IYbBKUBqZY@)NLt%A_$mJDN96`7SYORZu+0U5a2=U`p7_ehWeDfjCS`NWcXxmMmjzL@6~Y9Da1mdKvB"
    "#lpnnrK-io}^z3_`+#V>y~EiEei4;5U-peD1j~Oux0-N)>uO_|(RG3m8C3@JhyTHlY9;%E$-8+f}!kjUGF7{jjoU^X-Kxz^+"
    "mG6(y9hjtIiPfxI1exPm+n23ltm)>>usQ<D+P05y2Lg6E@a*30qfQbA&5ITgFTgIS*F$LJ1%koQ*yR7QW|0?LNyQ#eBe&So8"
    "x`|$z;o2)bWF|ZoJUpkk$*}tKKPg(&!yX!HWaD>7aaNmJQ?+gXuzvOiNG%zNO`RtXHzgTB}*y-fEVDum~U8V$}oZseIy*bMY"
    "vZ@bO-p3R0j2qQ$PtzM;JbD(B52T=hzUtV;Jnj0g!u7<!`EZUM#fn&=%&U3{qC(Z7C^%_9{cMkZ9M_r2^oB`&^JrT_2Gw2=L"
    "jr`6`0XiU0!H%T2w?DgC40k_k9Ky+sZR7K(I1)D+2?zP%^1MN^uZV}|7hK?AgNf}z7RaSK4U!WvzC^Q)+^H2{UR~(`c*(+qL"
    "ktbK_^v$AKUS^&_JY%PK^UC!Jb*BkAZjLj>xHicGI+t_L2KD?(R@O_bfpwFVtXvYRA|dE~z*mf96o?1+Z@%T>_+zSb>_2yx<"
    "az)EOQQuPMQK-f(63yw%LPdh<_+&lZn;=<pspMuKwl6O)tz>E;hYO!f~m&kTL0<qYSHSZ)92hXj4LoDJIiO-=6qQgc(-@1W7"
    "az(0V_&9cHO3BCpsdp$Vb1uYUjXW;dy8rTsDQoXuw&0@OPV0s&3exP0_GdNnbXUc$3`RR)?at2+cHdlpq=}}xgs=auCg*79R"
    "VH0Vseo{|=XbK%@PS#)Qw6jFM$;1)Z4TZ3`zP?{&s~}y-O!7P;-crC4VI4wDsd{Ii6C817PnU9W4w4H0#LlPco@|`S;+ps)E"
    "iS<NaK{T6FWrfO5d7VA=jd5=M<mM@B-G;<O{%yDR$o3OXt5_y9gX<J*<;lS2o3S|J^eS4q4m!?sE9fzP5Fusjh;qSp{2f|P)"
    "%H+uY-xGLXFU><A`e6LmoJseOCO%cmOBW6d|@#H<GOZQ(gStNQTytGYz=`gHsdyaJ?e2zFkwyXQbp^(6PH$n6#tFGw%&a6CU"
    "px5r=x;UWrv=S_CUSqDB<PwH;+nPc=pb6iy@kriF3rNOJIv-LpgDAXQ)qi{$x>Q^KTevc9}|H2xvzI0Pn_Rx*rZ`T_+yELo-"
    "~WjYJ+Gd+FCKg&$(mbVPr&?}Tbc+g}T2hpqnpJt(Z2rLs-Ap4l@#(8Fd(t&;Tb{KfY@Z%dQsMh4aK*i8v!jQPXjr-%{T1P$|"
    "Jbwu&imuFG$b+e8(Mw}MeG1q$aSL&TOn24*JF)<4q@wSz`@qo^@I)gIDfngiJ?e%~ylsA8>v2#*hPuw(b|qMH7Dg*i4W*eH5"
    "3NlL1(t_;z<(1CqSsl{cL`DL#$&}OQ}CxHEoV9wnWnheSjhF)qI!EBI8*fZCH9L&mIyMiU*W*(j7r@6rE85(7_S(^k%vh1cU"
    "9R0un6doVg^T<rt1W1gfa3jV()d+=py(O+l~kM2==-SH>&MHApsQL3c85hE@)7f;QMbx@J@dT*ck%+50J1XUZPzY$j#LZEJd"
    "vLQ*J5!v{q0}R!FQ{Eu)YFWQMej-EfVr)DL;Y0KUIBPw<`jsReKI6X(tD(*X~<Zn>Xz=7!_Fvfwyf+E4FxBwLxWJ<b)_6lW("
    "@@p-{h(N~gKW9)mo9>NRub~&NdaWz2Qc7;s5B75*!Vbf8@7B17@E5M0alo}zPX|~w7Si<4G6k94)cZK|-q|iPv;MO01AlGDM"
    "hkpwZ9XQ}9(`%3?hHI1K|6@OuSOkX6)R&vGrvr7n;riNXx=+C)rC^Q^x|$g_7uwJaG78?5#+3vrpE2<-l?W6^5KRl_5Q&1*q"
    "x!nUJ9D74Zh-xHYL`Tx>rG?dHvybf!WIZNxUCX1`LJ>dd?jXJs=n#)^kr|r5aLI|3PvH4Rhqt3B5KyxX4ff%uc3mqL{o20e~"
    "Jy_)riAuOzx?uK>zljOW*0JfG|OTsxz2MN6?1d>_h;xV?KAR&kHRi0dD~J!&68EzpELK`V=Tcr=kC~)+|H4JDUZu8F<+bVeC"
    "Ehy@#ap3oUC;CJixBVlYgK1rN&H#4v1K)UXcyI%>mp*$On1CqB!vv_y9sHeqtouK0+luH09C>L6D$^9#biKK0jImqi+|4OSy"
    "#fk5lYFZ`Gm9l^lnQw{S)fq~0{FuE&&fz%)hSySp;V;zni)s<vD5HDRSzP9ZEqnw$!|8QZW&z#p@?0R2SKHV#0TvPgC)f>el"
    "`U66cR$ur>4oVx;&72%8*kT5l2DkegTn<F|>v8(}!9K0WO-9tKeQO4!M(1`C@%M#d*bOgIZB2t8$*CJC27-Nf6~~m5hNor;&"
    "i6bMDM_wAyW%!pKv+E*!z{v$LW-9O#lkOsXgsT*aH~&}J{UQb20gA^OWVV^qEGXxU!deK`1W!Ps6)aThhH7=u5PkLhc=oQbi"
    "|MbeE&P-4wOPz`d#pg_N|}iv#@np_9=V}0m@{N4&|3gTZ9lQ*ixRa^&t`8Rl_MlO+AIqS&)Wk#XaAp1bhgq796bFBVqE=5I0"
    "~H=kXvu{zkCom!(cZzM%__!(B}OHV6(oCr<^{ZEl%LKp(I7?$&(Kyglq9h?h<c`RUQT_&WX#YD{2Qa|i-#0abuSKwNXUD^@K"
    "WU<(RJY(=G%S}uDXg+Ph%2n5U}C&_+ZNPrjdxW--O_LH5m{AGH4o8NbdyZyH8ZN)1e=$LLzg)#{f3!1uGB)`=@p}cW)1)nMQ"
    "k$LVrzRq0YB|(|F9t!*|Q<nb`<Up3E`c+?zFJ4^0<neUZa@V%Fr-UDPrCT0EwF;x4F=9P!p*xfKFd|AHrOim4fFtI8t`X@2b"
    "tMM$;-eOMysr_HJ(k6e{HEX(@!zTc`nnRxElW$|P(xBrVbXVAuqvoWGQre`msugJYrwF*k!A9<(3vtaxl#~NH#}grBWmiqy-"
    "<Yl5CJDcASuiZ;6s+o1gBQHWBBcssvKXB4!4?=@v~j?Qi3AJeARVzQdQXm9sCVopEMVohXG186)4v9t#&<qN?#ht86ThimE("
    "6#CH@J>gebGIX%<WwZ&tT@qF9fxQXHbf%Nl&Feg=Ok%=KUtMuPpXN+XXsO?_woBs+Pz>6{9F2Fs)H{Xs|tEqos-NQGQ4T<jI"
    "z*pc61)e_`oD`Bpfn6J9b^+HH!>rvbZL;9`uc82k|Y2_CiIMH{{fgw>1$Xo!V2T*Pb!cDw2GH${sli$OsvpEyX$?c2Xl)}yr"
    "b5Ib*FqF!S5Br-q{e{!4)IQ(o87NoSMvE+j=5`(I1q$$>BauaTfHcA~0fh)p&2;wSmb=jNd5imW_eRx&EA&cB*Z93x-Y-ffx"
    "f|t*3a@`$u@9c=*h3N-;S@=+%2nzI00~r!^zVy|2pM^#q$`Faw(z`m*p-$j4u9T2l}iJzNDpQO<)i@^Ro%Krz&|KLs&~tA<$"
    "b89ybhNmpVd%YK{Hdf#wMpQ>|R9sY-sZ4557~rG8i<k`sO9;-9`Rw+0H0y7M~%(l_k}h&7mfCkheIe2XcrZp>g!+3w^STHPL"
    "fe#P#oIt;lBvnpt4WDH^d;S*Q!hLUZ1mHE)zzN{b~xtb63MZny+ZFP^}m=h9X8jE%*Q2bPH(T-T6*;8FX@v&2uZG6w8}4~eh"
    "qc1qbLC$IyDkcuyYmpQW2zVW77=BZDfW%|N1Nf}Wwsb_sskOCx3hx`A`Mqsqu+Yq}=A(_`v#sSc*GVa0YBw4KZPj@D#6|B;_"
    "J0+(0=7pJEFngL7M$u{#R2eSgMwqOW)w+C(w<!?W5!alfc;I|fqiNpba?lWRrjl%pXk)xywS@3dT#s4ZceHx8H|E`m93@1Q-"
    ")(vmXmJ!$Y7UFk9{CRMJF-%&lS3xXneg(!OP|>heTRH!Fyj%0D)dR+c-uMz-jLeEhpN5s`5^(0IQmzdb%3&cV6I*Kc4CaeCa"
    "~%*51ynxq}K!M7#daZ-R5J)wpCK9d60}q4cLEEcG~@=_x}r9yw7wmbnZk<I5>(EwXbv{VLjJZo8Ot1{C)9l-YTlbz|42@_Vf"
    "Vagvk>5Lqt|jh`Z|U;;(p{v4j$9u=UhG=d0ALXsvA59pjZ%lAD26wM8#sQ73gq<3=d>HFPExjeg^G?r*wBT5oLP!!Gb4j9%2"
    "6L^+}!`i81z`BoxcIe{EZ?b^6;sJW7*3`Jyy1#bY_*&Zx1lsF&MK?VGpUk4szG}fJ{&IEmqb50-%J;JGQj?3?h*JrIMx!jL%"
    "cv~TiIqJ@;%g?IhPsDFxJ7D@J0s**6y&zqi<BY{le5ow%;>)=tE^yyWHIVS#f6|78g{n`KfRE$PoFesyrFP!oFh$L&7%E&E6"
    "||x}U}S@dSx1oPc53(iwHulf644~H-DsygOhN+ndzMX{I&DVgQ7yia8lC^S!E1HZT;jV%*@oIq?hLZqyCV8?EpvlejO<ea?@"
    "135bhv2BsOtj3AbF9IYEeLkDh_Vm&Pke8L5Yo?7@a_h@w;83UZWlgoO1KbA2ArCg>zh91MR7mzVHW{zS~(0lv(JgPs(?Uk6M"
    "lpgL_+{X>WqmPS|TkrX+_ZUaVw8%pLrG^Bb8&2l78$Wc5^E@cK@8N+zh4mg?G4tbqCp8^*l43jg+y{ij_6O%;FSu>&yFzu|y"
    ")N1Uv#tEnNVovA?r(ft&Wp^X&4!VZup>Yhg>54?hSs;Kv8PN2Tom~0hNQ!0eM|D@ra>bhuSi-*~Dd9i=|ZaPthV=VcD%O<SW"
    "KOzQxYP-@=hQaCwt&86>*#luK@blL*9SuEXzh&ZVzK@8c95_Xz<;$*o<5z|f?7-?X8Lwc6-(Btob`tWx4(*zO=g6Gmp7Lg<z"
    "7i70>fVoyr%xB_7pWEe5Hqcmvx#N!eaNePEGau)Nvv+{!46njaL|zMImG?go_mDR3GZqe1cp)uM`}dNdLiLNp+*12HZfgA(v"
    "f3rk3qFp*<GzFP4N%JW0aLrwOp1bn|YHtn3~E(A{T{7vyJP?ozB6vYaDkx_erHc<bTTbwSpR=67PQ;Iz^a)eu))Y0c!ojBiK"
    "tLNu$T66O?>hM|WPpZf}7f_XALy<On7YnTe$;Iz3rXgl(E16BFRed(k9YJNCLIl*X2;DGXw^w@B|iHSzM^qd^`r0A=l1?Px$"
    "R*(nqgwU;iEz+~^RR}_!Hz@?DaC3VjyjPLE5O`<lhb<F;=)%8bTy&HZxmwzS$tV-ht_5x{g#d@c$R<<yALn4LH5PmQw+0`sa"
    "_}t|m2nWu>CP%jK6y}#S8eA2UNNXPyOBblAAQV9Wq``b?hjPAMjF#+UN_wgOL3k+rX$st5h{cCtc0zoS(WDDa!?@6)Ic_~rg"
    "HYlYdo=3KPQp=;ss!eqqa>**-Qa<ow^9Enb<AJ`g=~PXcq<OApV#B|9%n`)>0&Ft#o~^x+mu#hPEzc-+R7r4yJW53A?RK`vZ"
    "ykchG`jqH7W4ya`Q3C(Me#=3{3rAnX&kMXl&PAc^ZZ<eXJH!Y=CD7FU&Efo;9^2Bh5Z;UqbBkKF&R|s$mP=tLhMLgpE^1+>)"
    "1&Qh7d0IaP#L8oW1)!-^+Oos)k@H%|XKoF^;3H%>y%f_lQKpRSAr+&{ZJC_D2l$&KB&yM(lZ=Jcs(@oNj8BOLnh%nEjA*@aA"
    "_CpeuQw}pf^p><v@L0(f}sAi@m-r?wwu+$JU8GdHkt^JV{wjhfuOwPntsRmc0L<h?LiYK={fyhuWnK4H*JP{>T9*)nwyU*pH"
    "3qwAo?#2cxYl*+#2-ZSoq3mVy@a<2jlbWi6>(lRM4#5&8hDoz11dbN2YY+9e`?kRHn{76#SU$4eQ6`Pvbf38{#ju+T0{KTQj"
    "(#2|rdUW&vR&$8V}HUV<dxvP^p|%Y`1A4m6S?sIOJ|Y()Nr!E#@BaLgZ2a9sF@!HE>S22$=o$^D7Mg~^=;biV$XKJ6<-wNJ}"
    "+15X#N-;nz$=V=R{JV_1(VvcqT~c<_xS>@V0||dq@>qe7`L`vb)1xQH^~VKTHE2{W`@KI?C~g(}OY;em}m#Zulargs9jL<;X"
    "~Nb@{gT)CVOG-p8i`x0IgJ1ae&0jQmQ6L-rRD#wTpShm0?39I!(9-MkKXX*q9Sy)`hrrqOFh2<dO)yZ)R1>~Tco<I9`KC36P"
    "?DOc#P=>4^5cVx~-SUr_fZS)y0PHP<8&EX_)!x4vmG>rINVyHfUyuZx)7zMzjQG!yQ*jKom6UIVD+21t7xCac%^An=Ag3K3|"
    "bWNhN`B8)8UG0r+ORd+F9a*u)!yPI51w~HMC0V*|4MQiWW`)8kw-Rm*-P9RO(-0u8kp5y4Lb}H~!2!0eNw@pe5%anvqvK#;C"
    "~nK6^UeN3;7K3b!}&Rq=Lk+DR2<F&n^#OtXRd{{XIuX*f(Y}OK&(2$z{TssAIbaARpOLZjjhR3#bON#Fa-)P><ftDNg(@P=g"
    "FWF=fm;Hcw$K&+)WkQ!FD*HqwAXZ&FK=^6Fj&E5&K-&&45F+IkHNcUK<<VW)C2h&F?Izp5LYT!u(esWBgaXBgt#<Bz8{2g3="
    "AiN<21RKI~EQKVWHV)C%cTXBOGBc)Gy(XRPKAPmZh7wcSwO%HLSDTQm<Fem;ltzzz}A7Vv26t!0)$p+Yn(<hu)aXa4Den7bC"
    "B2GuEC*lE*${6xWJPX;EmAwT4VMJdbs3gz#bF>PVAa9!;hL?+&xEFLH?=8%hiYggeR@k#!=gK{5rGrx>p^a=ZAG6_{kT=uo7"
    "iV2^MJ^b`!=$c~26*a2Iv<}~hlX4smkpi}xc7Ev|W&oPyhV(T+ZYA!S&+5IFmHDTmuBA!yGdPcOe(}Kj_Fl_Y?_3rJL86Ukn"
    "<Mp`Hhhl>;PB)XBW^TmuPBx)GE@CV<8l2u8VBKVXlB#H4k1ge*eB*^%qZ404yHdF0LuS3=wGN<a7~?}`2LcogPUWE>fOpX-&"
    "%W_`Ubho%!2<OqffaQOq=mEewfr!We=zE&2hv{V5~eSO#phvy*BD?knXDC<)cxq6Vu~LLg7S(G(%RL{Gtjl(=TMm=*m0?V{g"
    ";y%Xu`pH+K)eYG&-XE&5}>r_rs*jo=wURR3DPKx;(*BvgFi!-iw!+JJ4l>#k`)8Ipg<XR6}HpiB#)w!1%Z_OAH;tct8wl!!$"
    "cds{Xv8E)DP1zvJH^X}TBJ*-^}HK&viv|0izCi!URUJ%5O_IDYeHLo5WQ9=F~oNOt3*KqJwDKy7>D6c?F;V%Ch9{C~k^me3B"
    "#<47bbuRy0DO&7?l2D`HMvv|R)X-3r^r~(x>Yg)V_3mE~r4bqXL^o>n7#`AUnJrys2Ka543`<zA@>`p2?jHFF<x|0-8@$5eh"
    "i{5+XcRjl`83wj)|ocdJU|*;?x7s9%)#ARXtSgk+=h4UFS}O`^Lau?24y}ATon!Q=U#AMg>4GXkbLgu5{L^WJkbv{R*+9!$%"
    "3)Gf{~1Fmr9SUTuJYSC8LMAc!@l7EE`w8fgQERm}g>qNIK$F+ZseS>yB)rs=!$YR>OVj=^t$olB?vScB4pihkY<QPsh7LWTg"
    "#LFaBGE$42v)rVqjBYDgmWwd!B7k*fAx_RWorlJ-s9)m$d902aa7l_tlhCJZ8RSH4GLN-!-UD609JL5t>bqG~2tkWI;rjjp="
    "fe^jh@u~GV}&l$)1@$|tZL;+kQQ*KOxRG!@GX-1`1vd{UQ!1Z?p;Y)riA|r%X6%>4II6Y7`dgW@pkRWPWyxdZ);wH1DLh;iv"
    "Pl$0xYTX-)Hhhb_?ZM+rIITu|!_JK^!yr|Q1}j^5>y%o*!mbXY^vBqo=>j5^06zr)j0k^1Srkh>%yCiN^|Ud0<{Mcle{P^{Q"
    ";Se4N*&u?@gVfU0TAq+-|a@LkU-42|FuB*8||~K*}~4V43|^Q`&txBfk<6z9gLagrD3@*CpOArzp@?Sx=4LCyRkJOrgqiUMH"
    "c2iwOL;j<B0h<VO08Nwqgy(8w8tjAKa-IJE)ClS<pYG91s*_RKX>~G`3$Uf^U{C2V3kPtj_8y2a5mDMoHRhHNh-?L1-`k(1O"
    "krFGxVIB+#Tx`H-m>uX?=BAQ*ZlZ|VGH^Hy@1lSFP<^0Y=9x>bET{IzgP+aM8``(fqa=g!$v*3)0F4;%CR_08;%gUu`l-2c^"
    "Y`!1K@z)uXyV2fAni|<&m;xIpTnK7K#z09#c^x0?B?Iv9XK?Mrf!IyuRTmJ)lZSp7Hm6W(%DKaWFc@k^WodcAnDP?51d)ps?"
    "UxX!TTT~;A?O%11#`|GGEI)UrFaz)9YKCj)K0H95O`1K{ii&Y^3PoJ3iLC*0J@!?XJIP@vAMnw8oS6<Q2n=wii>TD+-G_~TT"
    "(0mWRuN!m2KB_t-$#7aj@nDSy`_o6Dow(^sxVeub>kR)^?8~P6`X|tGx1WC6|FhDijbj*H0k}N5L_jGKW&0?loq3sA7G-78}"
    "szlbJ`2KW3^uBXdIy0C0MKM-!u0p@A&yu_WfwFQ@zvda_JE6mg?T%-2xJzqVirh-&gk+0RD&fcr8%7Z~&|D<pljyYl^~RYRh"
    ";db4(c8ptwH>OW2?84@RHte@x%R@f$b$Sw>bY*OfLU?Dn_hHY-ccw<2n%Su{6Yio@WGYm?@bNWT@YQkO??^vA)HmCyQFNO?L"
    "sL*>v%?;X!D+U!W6&>p1dNY;kH7oc%brOlh0pr<)jv4Wx4;q6EIs<t6-B_T(j|8z1#kt=$UJUc^Kc$ZYD5G|g6(@{RQ{^JX7"
    "zOz&10{{5(_08yrCHH}(ryDHv#Ksv7GD^s;_Be;<!IF+MSm2jO&G$|#CddsQo0m?A%BzApL#oZciH(Va4COx!rl<vKbB;};T"
    "x<N4{T+1?R;t|uA&djS4HW#u6X4u6k-85##6#uL#)NhoJQ8KV4>CXuFfTfjl3;HhI}RsJPX_PNkU*3~?-|vGT#7-z9$Kw`n#"
    "QmusQr;SQHm${NBQk`jCvbPQF#lR-o8XXl7TO2(iV1woK~l47CP4KH@);~%Fnc`NDxzd`pqJbv%2rRM7NBj2J#67NV}>B57j"
    "Myb0B59XZYv=*kyU}C{?N^;(TZ&8T=@(5@>$eEdkkMA&{D<n&L|~;1NY3MllO8<P%Nb`YS_){>jh=;>4KQFRa@}LQZj7rN{)"
    "vGXr9sQ@Ioor>);NNPTglehE50?LEM^P`T<ZacTqwWQJL%r|Tu1TFWEE4@JpUvtDX2W~P&NEPG&h8eXZ$cG=;Fc@#1JX=8>d"
    "xU*M~I(KHVXn@e?)E)G}Zq*g|d`h7z=iW{XM%Wg;pj5ICCU)LvbKbxipO^ZTfz{IXu`~;3SaxQ`jR4UKX5QmJfs>GL=T&kse"
    "DkLmBz4h!>;iwG2H&Xt##|#Mrb_*iV?q!e&Oz{<<7Vd^Kh*{=;Eun?$NtrmG1DP!N|jl4(rD`gkKpGwrsgb1zwe-*$CnbfqF"
    "$J$^A)_+GuyRR@BNFNL(jOE+HQj8_AQoQQnBZaG5v{}0O?t%167g>Uw&k1V?7{WqKC>C<E&0)_{K;ps(zM-#*G0K1y#XnfFs"
    "<Cww=BPQ{7-CrjYexGkrFDg34S=!8Wr!25PAeNp!?aTu=ix6C{w~i6eETwu|5lj*d^+Y39v8X~RsJ+OD)a>J)_?^>gzj>J<A"
    "nacY0*Kb)S`5=c6i$%B0dzU&*OKM=eQuf7FM!gvI^xQN~r;QPgqiXjfi&5?R%%s@iJe*(a=|6(`LEDKPAkNEiN{8s${=N-Eh"
    "?sG-hGrz9~rTxgdlY=D%&I4cKnYF(nd)+zs#hZ#X>a5C#`U`qlv|wP-C1Imur2f^R^&P>7Vta{)UIv{XQ$Ww%BQcae)PKuS@"
    "AieT`Dv1-Ya_iqM2w^+UsTh4t;n-7P<)fU#kliuMeO6hDhSXJGO#npjpx#Vqy1i~jS5C1W}ag-1eVP_4<?SFo*B4P{}EYSE7"
    "Yu8$l%eByB%xz$~F|s7<Xmw`FhMGz?YGt|9;%W?B;?>$4LPz3V9=2|7gg@nh#kmGStA2%Kv>PV8@ds8mh@Z^256fv^Xh75B&"
    "WzQK4pdy7`^ht7@MkfyePo{A4Hac)LO$p3qg_zwL*A*wo1zgQ3~0CnC)2H<x{yH<=@?$XXn(KdCofZ#k4Dy_rhX0lla+iL*="
    "O020#)`LX8IEt*-oWQU)4w>wsubE-K+q531_Qb_FtMR4cZ_n*ZVu`=v(^-mZACXmH)F20z8Bpm*^jxgOLcEb_Je<_rr#_#im"
    "UxGEts~0N8Yc5)3YmtLf)%K$C&hr8C%EbKg(45sF-7NmSb~3sbXx9(Qs4KhK7j+@+Fw`(^R`v+Z=rX13APLnq!OAe?#_BnnK"
    "NEeO_(YJ==mtg<0px603vQLpI>rZ!fs4X##Ha2HC`$RnUYVHqncwg;?Ri=hIIeSeRGu_gJ#OO4_)d?yzl4@x+b6?!-54Yr7R"
    "=(eYa{4AeEst{T=!&r!q?Tw=iko)i!7Ci=*jm!Q6K9^ql7CIh{+9T!wjH5Hz#lv2lktPece=Ks(I|(8vLOC@oxcWV609okqf"
    "`&?0#UQf832735=P@j9L;RGlG8&Dzgp}(xp(Yk@$8fypVkD%BbYNhJ+>7WLqf{B)Q&R1uf6dS{&d&62Pd1cjHv^yQ*NCbIqx"
    "j_Rdk&!cz=8K(*qREw=AZ#eLmJ4ZB5%O>aZ6oGcvCBR5&gT2^BwdkOM!xozhI_ejVpbw0$`Mc3OSaEhG)lC%s>u(`)}L+-=m"
    "@=t{>b3ehRc9eqsEwwvNC7*FoOz4Rq!G9~o52P|BAY*=h^{m_&GGFr`I%AEi$r0%pjC~+`3ix@!`%3;qRZa?dZSq0dQnuX7{"
    "zrUY41G`wVJc-g0L~xoI(qV}1!p%-I0ga<i;(Ea@m*X>O~^>Y4$H&4W=d{3jO_0h5-8)P|C)VHc)d{1D>lK_@Z1^Rx9Y4H>I"
    "pI37}XHh5Ik+TVSFKvi`9epE4Rx>-xO~l#w?pk3=&}T*YlXsxNYvB*Gh9AwE2O!J^q`=59n5~q``42A&!Zvv-Onrsirp(AC7"
    "JcMj&BFTiT{<DN_6E$-eKp32DC8KvRsO51kTiy(`!gbFXUD@lrnNtw?mYp4~@@WaG>Q!y}XXQzDRV-<;AXpq`~CEH|KJm3}>"
    "hLtudi#FhiO-w!L`DP(eh<GM@n+~2FEdo{5aKf!!X8<|hV4f8eHVQYcrDZ65*izE9k-GXxp&>IBA&9nxqEZEa=@LVfxhF1CT"
    "7-mZ1CPL8$t^%h?!=;f1Y(xG@qdQgbwA3zX;f6T`%!0KlDjIww%T+0C0PZ+j!Ug7jKYlQ28XXPYyzw>ZUiaFl@X)HkLmEeQW"
    "kl9gQ(OWOOKP8mgPp4SQKN+iHQO(liQbbm1bw~AZAEuNeYcmO$`vzX;K7d9)6fjY4+6=}nDo4|WFLxz0!l5O9V8u@ULSh8f="
    "z)|=}tS{FVgsaZhFu~LJ535<mqz8GB0j3SKH9tL9S-Depmc45?&}sGUq?0Ro+B{X&?(#Rs)(xSX&m;`r%uZ&Xce&YBBVW2h>"
    "*-)h_d?!78onlb@d!CdL7u1aKT8wDeSzzVuaAe=ZCgL2|~hx54jVB6_GB5D7&8YbVs6LC+0E-Bghv>hb%=UcTkwCe<{8&9jM"
    "e!-<gZUZWc<q@v);Q=IMbH{v>&-n*ZVnkim|)_gk7FHYu0uF5H(@li{6;gF~~yaOL@y+D&+sKHG6NQMkm5uM6^Ia_droWXJl"
    "^!Ivx+2VZ!d6(1~a2zSjCH@@8P7&P69EMNp+=kC3;$|rZ4<->1l}&8@6?E`a^K*dfVD|;r%lYFMVx23cn$(=7okeAHKiOn&{"
    "~pc4R`m|}tp?bK2B6IH6%t>~KQ<_Vu)ixHWmgghakp3*9&(v#j6Pa9q5vsSq=^BMbW?tRI}Sn76(q2gDO&#l+9o7?dT0L_-9"
    "KT^@1W7K%M(zz+oXz^>UuqOE;~;Z#_@snUsnFtOl;4do=;Jl7hVWCZ4;I?9Ld!ez3WK-miioskzJRp@`cKTdknA)>X^j-@@;"
    "<$8WA%LkHL%^Eik?|X4OLr1FHTtc#W}AyHb!Ito6Fc$;&tK=Np95s(6!C5kgRdMfD;;u{)^iVPWfZHJW#%Y<PVT2%Ty7;%3w"
    "8uYiG=$L;eIf>6#HBpPBjv<7<=n`1r#f^+wpjl8kb-nefUikJ5fVhjTFkoDxAIFmI+xf44|(VYC4aO(`a(mHjmT*LJCLlu%?"
    "Q~T{BvE9vac$2ouw7rEm^6bYMyb~#{z8n(<&bixvU%exL1PUJWP_lzKb|PaDm^)D5p6q9Pq*^OO=FYXE>*24&+2r)Vg39i35"
    "o#o|F;$}#x+}dnUix*;x7W}t4%T?;vkziQ3GYIM1rE_D+lDyGBMk(L{w+Pr_oXKyTtSL6pG<Yr3*b<{Lj9%1*~$)@B!rOQsV"
    "E$UEKL&X030Ex=TrW?2je{EOvw&P$TTQ8ooFEq^hQj{k%;%gmvq>^swDUzn<v+t^DY7@t}0k3Pu=wKovp>3zG~}17Zm1|Q}R"
    "DqmBUIdkH%#7PEkDO)+@cAn?Z{`5{XE3O_N=W&hUMg<TiDV^QjEeJ776EIl~5_5q^_PUp_Lls0iYV@&capuOK?g*9S~@i6g&"
    "_Q*q*>c}3T4+hYgdoc@s6pOLQ#9m?j$*#6!f<nav^Y7(*P+Q7dhLKMbDI$J9AJ*~N{mhL2R=_A)WjS?h$&hw=X6+sv&<M%FV"
    "fPRq=d+V{WSjfB``w3BkkCnxO!GNB{F5B&P8aA1VQXvzGnRb5A{fulOGUK331tf~;=*d|_la-3HS^<ZHQfIgF8{#<Fuj}p?r"
    "E#b-m5GS#06Tnwz7cZ9l5eZ@-`w74*0mT4HZiWnmv3fujcdEdrxn2Mr57#e=#%(!YZ;#w^p%x;oFgCd2rBkg=?|*VOC9}G{6"
    "cd2Dz7sFvO4>MA4UU~I`zBiakl4zsNW1t(VE9u5ZLRnY}!iQ<f;BZRuyct%}XQefnKP>nOMBT-CGzfwoOzd0c^D!(<ZL_x`<"
    "PSGt11uKGktszcHm6JjtQ_rT%01#_`mj5i{MQLR`<Wxa2kBg?ohNIo5iCuRP9j<*8IDP=zP3QJeFh1K2u^@O4H<En7pHQ`O^"
    "=8TvO(&lcY)Q?*ltjyWRaVcQ0FQ})B|pX`m<uc4n+8YOEC)I1?K8jct!=ml?7V?qp(lX*c5&hIw6PfO_5jV_9xC>9R?Mw2Uk"
    ";|#1T<+4Wjk+PD+@zP0FKbimGtiXP2^+6G2V~eiv=X>zbf@{QA^@3D8At?!eQ433$ac3jQ8QIDAelDK_qPnqI?50Gxf^n7T7"
    "B1ULjYAv4dG8rs9d$<)GO6Sq3koCY{VNy)@ujoAm!LqnSHGfnyiIc3K2%}YdOF{!+_`T_s6vgOr(e;Uq~|xQ1G8NM%+zfwt!"
    "i1$(G6tAYq!;F%2jD+UUcwT7pR36Fd=(Foo1?FJ;$e!hN^zjdm%UZ?rzfBo7YC>m#nh=ptoM(PqKaoKVJjH{e%zs$-qu=9lO"
    "=TyMOQNiVz!6bT?IwIVxNAit$$6?~X?+w_76P;h@*)`vwsWUP(8^kEzBrGWZjAX0!aNko$<DpZX_V%K*gFQ@O$L+rAedV-{b"
    "fhW=Q;bm;oZtI5YdBH>Ag8{8sZ0Z9y}@ZVL3NF@vm^{71JG<AzRKq!!;rAM1JW(-o2A5R1WGIj=;wI~!n*?fd)oK)VinH5YK"
    "G@Lx{Z(%M1AS#2bS&vyo!S^doSH~ws#;+e48Y$P_<6t^(f2#Qe+f?T#dT&)(8>m?Z)-XTQo^v4>gGBuTSX}cz4&!c0;Cqi9w"
    "BJ8}RJR{w&Lo8^Ry~8y#X_T}*xniFHOo9*wOH&$WZ`tANhTf>HbvK||ACw$;$@2zafh?B6^zk=!Q<p07>cDcd=c@jV`T2tB`"
    "Q!otIYRy*5B)Mg~pa*%KEVDs-B5v_2VWuwuST|V*sYR)?RoEa{P%dzLH=1x`O_NEhZ_mn&s`4*8|$0=s&NcphEC2Fr~RH<5n"
    "D_O!hZlbXaAu20e~z>`7f?Nw|wkPBkzUeB(*z*UFX3HYO)u3q2{BQ=M6XfqOKiDQ0ZiY?#vO-G$w<dzd>W)x-wG#kXDNRW@m"
    "1<BH@%MXzZ4YN(EJ{TPjM`^fuj9Yds49~&Td-MvpcimP_ii;sgHr2nb*kb-()aOPZ(r@r5zZ5)8HL3l7<pV1UN)tDxf1<f~Y"
    "y&YqZ75iv=;hR}aqQmb`cpbCzVvV{~1KU#Ef(emRz)wl!nLENo6OGF4K;i(IpjMdaQ0HL>9YV5q9hwP<%!3ars0)~i;90$$G"
    "HNGPmat+ugZ9^?{qI5-McV3C_0X0fW#Xgy_G%0j(BU@C=yvXL+(Xi9eI&e82J*R-h0O$R-FrxS>j*WjWuYed@!^*_DI6zhIu"
    "<vC^^q?FFf`f7mlTV|CfGB2Z=(|O#u0UC?D;k(q1mcGEw-DMU|3iy2$gAnc1$?3-mJ5#v9U&<usgNUyr^?{$*S-+Z}xM_5%D"
    "oMXmNcJs}CXAv<H?74!<vB1-gU82SLMBQt1yj41Tn6L_z+K_*C!|$qP<VAojbrnl~y>eE+deIgdA;AK|IHt|37-I{n+tx;K%"
    "V;jkxTzo<zAL0gLW9|Wsr5E+#JG34(_Xyc^<W4LS%<fNHu?YCAX_`JC#dAJfniKt})#lBThV_Kt0K7rLXtQd%|6Sv23WeJ0B"
    "Pjf0Ic4Y;FM#W6Ki@3JhWd1p5T4$J5+AiI91CB$bvR#4~^~tydbHSodhXgmD%b_gtew)eRro+8hy7Nb%u3Fu}ZWvWB=Gqy&w"
    "ikI%SyQNd;C`cUY1I<du3e;;<8OxVZyAw@uWix-@;>9?RrQUQNXucscbC!gYJ`{yFC-)y@lA+Jo28quMS-52RWJ{Gxw>8A4l"
    "B*wD~Y4)P5#$w`bnhVBfM{iSpS{@qKOD__=b(Bmsma^0s9stxSD1iou&B=4rzy^Ufvf|6H<`L1G>-$W(|KW&Grl!*yp?B(^="
    "^jrLIuA27cyBk&s8g4-y`j=F1`q&CV10is^qmY(T=j5L!rzfd`YK+}*wPPKjgO1cg1pf}A<Hq}VULDXa%;UN-8?7RN!|bXL@"
    "uVun{afYdDLs)T{;u0vY3o4mSQGcZVUq(P8}O0;zN6l{rXy$@x2U`rHKdv@@O6GLPH=<gG@{jHMXU66Kfo^Cd1R=@nnG!`9`"
    "g>O^|vnrS050QPZ{Zt06W^fAtoHk2~39Fvl2;D9p+Elk|<U1wt+27;tLn7?o#DsXh&1ZME$YV^WVpvQ`<4GW-aB<U@pV*@>H"
    "a{vcymwx5GsYcEapNFyg>!rum?J2ctB063dm*haE-URNaI5B76}mo7#22gO=4Ghn>6h8Onus6`ya<v1<KE270afAlt}I5`oc"
    "SW7>Y{q?B)0<h>6YV33$&z!d+NlU+;8%)GP;BECfy0b(xp-^P6Fpr-C_BwjH$=2S2&e)zG_@h=Tlz=a^6}B`FdsMT2plPY?P"
    "y%|A>YUVx9m}SASqM!v!varCxzr8dV3xQ8o6KJBKxzq6Yqq$c;3Qz`BVWi7bW3$SldA8$>W|kzj@}|AMSd`u?WJbaJz^b(-7"
    "o2B4QT#_)^&;5;H&MO*O6-lB}?hrIUMq+Zvz-s8E_!lR2Wn04586WSIodBJ4KLsiBuO^O6pfXP~{zQo>$YG94~>C*Aoy3CEj"
    "!>QITx^S`mzN_5h0mch$)OdU$T`J=VZ@r_x2L)9RETv}@M(X_6+IQj4Q!1c<wInHy^!DhB<Cu}+0q>jtylxKDjy>rf43$1~j"
    "UIhWH1N~82|P`YR^s1x#D_PIzIi7*EwXW_{8~MzV1z1Aprey{2&(yvghL;?yP0^AtC;bzI0SksJmiWUiHFxzvbK(ScQh$WHv"
    "LvaL1<}H=X{~EYxM4^V`BeQQb!Do{%B6^G0{hLt#ColZ*(BcNsHA@WajY3+S=of!evousbceYILSYEfP==2Mnp@@@3z_!1Nj"
    "4vp^#rm+sVzT(-Gcd|Au*9Jpd%%-|r=iD*Ub`q`!<nS%cU_ONM9nlifw+oT{6cZuAU4_3QT>MVbhZFcR`UfGAW?A@#1>65=8"
    "(xE9f);6o2N|JwDKsb;Ul62<%ud<4E`(5+-;zxDNipA;A_kKRgjo>ev3SYc(YF@{t5k<{f?+jit^6!&I%D{PeQd^gP^fUOvd"
    "_f=t=T@?Mi{j`Y7^^I0}qN^q<Dn{5ut}832Uu}|048N47T5bK1G49aFii<9Ey_zlH8$b-C@uTy$<{$^hNe#B6-5*ClWesu!U"
    "gndLAbI7FQOCGoxZOxruW1rL6c5Tr=KO9Xc@-YJP;S#2ysSlsP#{Smf~0!ID=eES(w2$Ho?y{K-<Sl;2LA7E8)B!{emYotjr"
    "QOeNJ+p|Hju}mg7nTI=uw^ZC3W5h0h&<>C--uFbRYAzvx{Kp3sXiAQ7C<Yzti9RQF8WU!GP5+KWC|AQ~$boe&h_@<6jg;FRb"
    "6w&fB~#?!;6OFP!E(j>U)1E*Iv)prz406t-{nTQsGBvgX(u$B(<6V<k~GFh*9UW5V2C8_p*t1X$AIz1Dq3J>EBs+~Hjs?mz5"
    "g_cRTi#%DL0K(%z#hYJcA-E7>yw-!8<lkE4>*e%@}lFZ8Rn>@My`Z;x;fYqjT*?t-ICx(KHAT_mr>T)HdLLAsw2C$9VK}qf("
    "qzj4PACZk_IlA`rYhsL5+KViZ0gxe4)eBDKkBSNM8%Ii9PnG*GT^+CBVlWK(VWx$+{^6ZT^8)fhuU#wf#yy~yUv3Q@bC!J?N"
    "oR+DR6zcNUop(Ff2Sh~*mA1EX9M)JUlhNJN2>eMqd<*gBPpDQ0u7^oFA<~|{9dfZ#Ez8q>rmcYq#kIBYY(GSE9hRw`Cw0QG8"
    "cy|C?WS%(%_5{U2$L^RVOjiB4%2GvhSCI#?<S;EP0Y%>0(mA{KOeGy?wel|9*aCGV;t9`H=w^*%e%iPJikCojNWISUmi?svt"
    "({c@lYTZ%`6#w)fN)wq3ifuZ7cwW_KI2t9F1>Wy>E;f-7N`PHZ82k&3PI{R2?PG9NxO)U|4#_o1F8Nz%U=cwLZ=8{)uK_xXG"
    "#@z!6A$o~RR+#upA-rj?)<eonwQ0E3NLmx{(Dd`Gs`shqE-k6L5e<90#a^MJjig#f295vg={QuFtK#l|6n*ri^fZ|YRb_F>I"
    "@Kub2%#*x^g4R+|iDtv}f+CmL49PHcsJnV2P-l$Mg1M@bB>>NLR;6q%aejCHF%V_|tlcu;d~+Y7Wo95}h7>RzP^Lkk%s&Cq{"
    "}vg7xWoLW=}x$cdB|x*>dIm3Ah^l2E?hjwG=T^53q+;fc<e^PNT#k-#I}!+Zk>)IGMbv}Tq;CEag_HhdBfNot_rc(YCoiRkP"
    "SI_+N`)Cy&t}w?SsJEHNk?_P2|DT${|Iqv4=B)j*0wUVi6IMJ{(6X#5;9PraEWSzba|k@iK#w$J+Yn>4B8G1I&h9eRBOx3%n"
    "_uv|Z&W`H3uIA~-+K9Ek8-b7A17fN(XpW7WChp~qR&D+NRW2?tJ}XA(j6d^hGuH#F^4(aBFcnzgQVN&Hc|SrO^OZiL&E2nek"
    "#hMw{OeulckwO3(OjZ3q;ryNu9`<6Db2^hHGH->qhNqcg+Yd9sfSB5?RsE5V?vCIWRVM4Dz=uOGsfz;h<?O@!EgNC$>BMH>@"
    "Cqx|DM$<!dBxT+9Cb&I4TQh_T6_ZDzcKKVWb!jOTlM&v8{IO4bvL0=+0#pMS-GTo{)H|@}`F+8{Pi)(2oW{0o+eTySiEZ1q?"
    "KZa2*iIVz?XUmyp7Rmz`&w((%-(BeKg4C*TR}#Sv7S2CuHhL;6JCtA%?{UjWh)izMF*Mh>~`PZ+S9n_-%T1k+O|YR-ZunBC-"
    "0Iu&Fp5~T#Z59+I1{Y-NB%9<7coh#L}m56(jcGg&q{WJK4PLix8E*xVu+vs0~EqfF1E*FI822L|n1u658ZXr0l)>Q<D^fyW>"
    "ntA;mRPd<xv6=6f2L?o8W#P2v&8R#i@fI|0fYw9Jkx99P<yF9xf~(67}5=H_AvC<cE_O)T<^{p-;Aza0uH2=#?f7dZh)R8e9"
    "hkx8<2s!j#AF7(Gx(2tV~+VY{YQ5=5br>-4x7Lr+kJ@1``A7w6Gw|uhlHpdx@AlA!FvRs2)P<~jVjoDk<Xf1qtL<7;>^ZcNt"
    "DVQCJA-Q&Lw+r=WQXaTTuyGT_cZzcOLlvhVV^5_qpflbvsN^cF)KP!!?IQQsv;0b(S`8Fi=~JpNX&aIbLRxfm;0o+t8UEUg!"
    "JW?5#D1~p+?4QV4uOH;ryoEZ^Ih>vd!O0I@e#rwa>tO^nPfb$fiFo_esEVbM{N8(XZ2wOH&_eOcVGK`lB|iyx`|^Pb!Tp$@J"
    "Z+3emC2Q|3>K;)WBwC)|M9{zrY#P4Lo{4ZKQv^nI*?_Fs~LYRVT?~KNN-qN;N}2ojm`Suh}XQkQjRK-wA>XIwka=Jiv(CUvm"
    "CrMO&D!&UFJlgC4}_8)-H$9(sp(Zs7ewikC!(6AY<|SJ{)%_iA6NGh%oHvnAt%g_Akk5O+jj=BMA9`89JjZ3p7xo3en-uj;U"
    "{PVA}B{+JHZ-Y%9NMB43~dRvrhxZHjc)43C9f*T|WoGsT*_(;j^%mxDKWp^e!oVzmS^_0<EZbD&0<yQ}()?2n_;NxPT!VM-G"
    "=;U=;##xESQ+U*ub8&cGYwoX!Ota(}M|e3N&I1cqo<4k&xzdo7L%o9D=9E$&-98mFW@{ILeoJoa#28hlAnP`(SSc55RY<`ws"
    "cZz^_f}_0?G`xTx_foe&aV0({()X8!O7;EgFP3JlpF1KdklrAJFV(BgR8y9G|GR=+H)cQ8QN#jxCKt~FN42_E*=b>GTjWNia"
    "x?m$TDAa<VZ=Vf<<9w{H2xvC6joTKSf(p?XU_(iLQz_TuwBX>T*BjVt!meLz78H7Q>2On>2O5EQms;rN?EV@31u#W`D(y&=`"
    "!eKtaS+;c)bNwg>n1V>G%RW#kwo+mbHb%G^pn;dh7jGdhdl&0(5Ff5>lag3Q`2wALSOn;JjFcJN(kQZtc(W*_rkoh{ysbvO$"
    "0ciuk?iytUH7)M`qzzZyOLt%9#aSjeEK5)V!#3ug0I15JP&yn~sKcn`IOIGNb`|ILT`@&~bv?IvuePbeBOx0Xj_Y*mW-1=6~"
    "5S2d@BA|}#EWM6;>5IF+n?UKUZf6|Ckif_p3&G|Kt1(@x?&`3TSHUa-8C+;p5fUJTjLRl9I|n*ZuE4UJLe{?+kk#i|NDFi#J"
    "{SXG1ZJCEz8v3puKjde6VG34UlRRY?3TXnKf%mYQ{rWv=v`VSMaNYCU@ipiA9ZPCl78Z4u@j#JVGqh-8ud(VK{zUVf!t)8<U"
    "n!Y{ch1<V6J$tHtuN(y(SMRq7Z<tW*Yh#eyB4edT!>0<x9Ow{=}y3t|KkWO!VaG`p%;Z{w#y{^(%;DjEHb-*FBQu8ShKVhlg"
    "mmMjyr-kG|3l3SwYrw27YI;zrX$U{(uT*^H3!hEs;b)8d5kcS8A81kpM-AcDyI!>eN!r$A+g1=Zc%`q}eKx?cdyFjD9$yB06"
    "ntQky@OFKIm5x{=LZ_8k!h=})4bag81R_NCEmxq%4llJU)i{FG`1}pNS%|I$ggEIc$6cpTenmxOhkxyp2U>A@&q%k8w#Zvp2"
    "ze4}O$r=2Wf$zi%MvtAIdx%%ia`mp0^93BE!r&M@IQe18=m#i#lR+u@!YhMu$4>@>^3&OqLo<2iQxZMDf2r9Tw-eU7>bS@7X"
    "z_rp28m|jutl+`ZCU+{E8Kf+x4)qvpIGL=QGp}!$1=76iV}d(GZGn~$$>X1+;=lXHKJR)xZ!&Yf-qeF(qT?|9)9QjQ5jpb=+"
    "v(xICqS#V$#gj`wEmO(N!ki4-OKvui|$mi=W`6x0(j(8wnojFBXP6E~n=l&Q3`xXOgo~3X+lCkbM%ww=jV19RQJ#s{}*8Ys("
    "$wTt=@jjC7FgBG<%bFHnlqA)s&p+`{=mg^<r7|4SGvFe05rgDg7f!xoPprNa`Z)qKy+>_=C_wQ7}=aNkKc?zehp{xOu~2e$x"
    "CESu+Tci?UhM?qW$K9Y=PIEVfTkuZ5UIkiwsj)t-=G+azMVhj|NTC!;4tabe3fyD#keqRUzqk+VEMfI8g0gVWubr3iUt?Y%?"
    "vw*(#J;~s@s8bc(pN#bzrqFfA@<uq}ubMxD+1Ze29_*I83hQZrfLHmfrxdgNy=QrtAE$sVwyV86Z_sXcABHRVafdP-{6oWlC"
    "?*c(&k*gRoKrMzB9{|`mDj9W5@rFdZ!&E=ye>8m3vn8+?%LF!=S-tMag&9zzNxRa0ai!*V#@<qxOeG1z5>MZwm~4qhg44;X8"
    "`0>?cm@Nk4c)I^Vg-M36}@2zr*7D1J=LL3BiAsvC{y$cpB~a>ho(ku<H^7r}oV5V^vI`jwlZc>8{-M=-B$>AzfCUmo7i&dOx"
    "=AL44GiU(FA|91KTn&Y{?$cS?^&i0(Na`>k?RG^HNs4yTuT?R>FX*01UApB!=Uy9(WW?TjVXDG|S(3#_3SX5xrhM&eoQu2sD"
    "wb5(Cg8TA;B<M9vB0Wwem>(PR3fMjHRZHTX3c`%{<U(W=;`RMfA(aB80ZcK8ZZW>9D-VU%Sc(K-SMfADKuvZHGq{jsKW0lT3"
    ">eaV@G-0EJ6^KL$w7#uefWruIM87}r66D#dffnF{JM;E4x!jP|oCDmhV=G<^fRn>DE(xd~*BX{ajUeze&Q)Lm+~C+OAHL9m#"
    "KQl`D+RJ0pO)gVAA+z13F=Z7U%H#<<{tn?7qkvoWrQRMzE)eHTafM7zyYrx1j7)@?YGCqXg5Hxu#WVp3=R~{V41aF$qyNf#O"
    "UWHw$e+TiMpS$*Qd(y@7^KRyES|pMXv?t&=e9vjFU?|?LKsIM7ch=eHvU;8+Q!zSOrKS9~={3b@RXt)AV?p%ixP#yef<mcEu"
    "^Ua|cc=onPXXvM1199D@V`XEsVz*GBF-8^VPph1d9;-+ABZYeSR#VTHUUNm)YAp1(gI9`SiZ*zV5{f;%CE%JwV53lD9hN7_&"
    "ZCQENKoK?pw-nX@l@FO1Cn~xNs6}O_bJPNqcVJGyJ>(XI*BP(_mSN@cB<uO!-S%b+AiDP)VgXW$A`*RWdLGPG5;Gp|Kq=r*5"
    "jil5enr?=r&qc96O=ss%yJ+v4J9GXR{tZ+TS(HH)^zR=PmnK5cV_B7h)I&56G<J!S`{;{2d#C-x03Pphil76rIVrT7Zt1QPT"
    "_<l80gV#%w7Jh=g9Zi98u#l?wQ(`L`|6>Cnf#-E=anj5D%J($BlRvyc}O?wP8cZ-QR;m$JosfEf}f@ikSiS!ro508A|%{09}"
    "JZo*DG%H#(WEZI9!^~wD0-+T39KwE(6qJIj7?tvFV@r2`yK4;jkQrch&6&W|DEAn?0cIsgU-q4-)JdWuI}PA?g3j$7I7)x)K"
    "MWF`m%p^NIUCyX#uz6Va=WH^o9x{}97%#aq;7rfCxI0OOo>fXIc@exBMnlYF*6F1*S;`&?r?Gdn}!K=cUe{BqlbEC4G(<GKq"
    "`v_pjnB<}n-5=k0M2mm=$sSIdIQOz(Cf4EfI%KcPvi_`(oy5LT3BjUELY&B)8M4ffX+x^qVgHyzK<)>xRW^H8kQ9p&SRsrf+"
    "t<5VMiH!Bx(ZFV^OD|n3+G$wHU<Di(+^$GV1D@m&q-lY;ICP3{na8Kz@%_{nBR0~`H|MAjn@IXC!W^(S1-Er7S!%C+)KH9w0"
    "Wp#j+p-#FabT4*P+8#}^Sj}s{guqd;Pm_lydgfR`^sCxgj|t{*Tm<J2V4?Mj>2TxEsG{fZqmi&GfR%kyI)rgtY@I+_;CUoZp"
    "{^$J_K6wk&h2+N53AwFQZ2c!}oy9JyzabGrM#HzDw-1U+nO&2{L-K&NHr6B$Mys`0BQxO*)~4SYuab5tu~$S-<p>+sX}R23S"
    "{O3pTe|`v29Ks{h=d;WvzNfbTMLtFip)T-xrPt1{`4<?y4(7%{70Q1Y$O`6>xK6>1Ceg$w*4U5#?OKN~A8!A!<G!zTc<eP^r"
    "*)7^B-8|E?_&EKgv%q!N=Oy+;d()OQMs=Zq|GMLA{peEik!pom3zYrd?);f;_aOLN_pckgvzvhkZsD5eRIz?^adcIX$n!Goe"
    "HD^Q<ij%(%)kdZ9m`S>}gXW*{P)UZ;?T<Q;=VH6bjEaZ0GlLH~c4!0$WT?$u^4r^)4yJ3I!!D~jq1C9I!Z9yZ3FcT+Hkzuz4"
    "b}(e6Fyry1}sbtVQt(!OWr~E=WXojnc=s~>+{Skb;R>+y3JpA*+v*ORG@YJd&;#(5$3;AQZ5Mydq{O-ejb!EazZxJc91McjZ"
    "T!??*m&3OppE=AWt6-GiMn3&<9(nje}I#B%U9<wo2$#D>kV6wzQ?5s%xwFvDK!Y`g<7NJ}5<9FBS1O`w+q!s9%9Ix?zdyYI)"
    "9Je0B6+g;R@IaKXiyJ?3^Ek(?`RN}E~kQXNW!)9?X$<XhL$oTt`sgi*}7@LJ70?V`v>kr8`A>$ucy$_b=<Y-4HvIk5|zGz{)"
    "=&`MAFg%ea{{aIwA{1lWX-myKeTL0&x%Yf}|0!=-qDi0U}8cgSO{}}UGmXL^&zsx-YI@u`Lk{==8`igQQ89;rs&s7%Ve=)iH"
    "F-<P`CM76)WlPz}9ri;!&%`-1x^Ku7fZfn{LpcsDRZH<&!veUU%J_d9`=TD@FT2G9@!1R;NuphciX74w^T<QnYB^BxC1kv#;"
    "Z_tu`_D9)oKQq8&@PdVwxhU(_q&V9Z@sPkotnB)@r_%qY$&PaJl8L?wc5Ux&7lchB&R@*0Dpeo=)GN;73cj{jvp{YH$+21rg"
    "K(Rg+=9oS~vmHuJgFMgUR>FE^&ToOV;#k9ZS@pV+;wwi-U=+(4-Rj4yHbkM<8lcCUXcjZzW8)8JN#-T`HozU=Nw6^<_{N=R7"
    "z>B6lBGn>t3?_f}y)G`7j<(KKz{y$C5+zLSWi%gqV{;vm*vJP7%7CGg_LDL(COF#C}4g`EE=2~J+x?i-}JIkf-4^kj1q)qn6"
    "?b31x6_ToF!|J3?Yi}(cmpWR<l@qVO1OC_h$B?h>DS;1)T2CZdI5PB!)^4RFW1n3<gONhes^~k<HnlnwACJ!Ky`ZBUO@JX7i"
    "YQh10mBw@;a)+WQ%J)-#BiVHbTcJP*E!|`!{i+t373e#<<NHpf={jRhk%>f?rt3$b&!H;zmob`4y9=ii`tR;07g!D14K>FR8"
    "BW=b;hf$TB%o1;H#Q9VUbP;ZD4PK|sVW#Mrjx@{cPqhx18R`|ahPG&W8*DKYv0$Du20qD-RrjX?Q?NQ2*&pFW)JZqV61yW{a"
    "{Y4&RGb<Z$=Vi;mnS}YIQ#3hDIE>26`G}`~FbeiaVlw`r1HG;h4Q&$2Q_j>-luO7rKR1sQkDpu_{Jzma-5e013>GS<Mne21g"
    "P4k41?-KhxgA*5KRD!`Thq58aFyrop-}QFqC%l(C;z$}cTbQb5Mx2D!t!7lky@po!*i@{Dj}Ud$t<>TgODfH<{4YUSB!tpo>"
    "^s5j4&F3rug%Vrvha;Ik@-Q*OJVH0-Ycjed~*8528Qy*}{TY`vfCh<ppIwRtgZyjzb7pgTRCMJLX6?^Qav~QtawkJ9whSHL;"
    "C~$UiG9k+aDS84wyM{Wf7?%yWJ;Z4_UO0XF7`glvClPrxVr<6w2r6zHFXfUhm;<8=jH6x|p&l996taB&ih9NH_|nB_fqNRX="
    "bZ*-=o!7+fCwJ6IMj|eGFm7V^x-Zi9(gD5UKB9ehdUiqwe~`v{Ws@-f=YtN6Nf`%d{3WCf=n7G8b&CV|6ol*P;oCORi!{s{c"
    "x)plb}7LU>qdyG5B<R4||M{Wkw5{)OyT#o%&Na@2OkM%(3{AV#LklUTCd~wiNZ|$$&8x=hs9Y?fUlADBGKh!C*gUW)i7~x<Q"
    "6kmt|SX+A}dUiIek#ppPSZ`iNYjc1Y=mlh3R-iU5~W#eG@cHhJijusDMs#uhQ5n0cmAc1I_ho=<kmt-XN`j9thHS1H0c8{we"
    "eAs8RqpE>qo{UKVHXe~3+o^!d^1X48q+MdQbwsXz&p<@3spWe@0dY{g=lCm{K8BLPU$>!_Yj!(P&ZLev53di+68ZrPc#Y0@>"
    "t;V6a!WaeNIqNMQ=)2Y%?sE+b&;t-(=C<oj1~*p839qoNFa!^r9Vlw{Tm*5fxdM#$bA$<8Y@q40$h#1!bJMF-J_@9R2!eM1|"
    "Ndd&bSM(*PBcNwgRmr6G+#!uU2z~)ZdU0cLFS@f$|rAekR})R_y(ZQ8M9Br6GQ(>AQ;wNQ5oc0(O!N3sAh#(4{FeN8Xn2WFa"
    "+E=62)x{*G&tP{cTYLwH%gsBmAOCp&p8xd0`x=C*2UN(!7x$-vk_6-Z$5}5}awv%bT6da7wKu>0GZkZq`paR5|vXm0ei(ko5"
    "UWUHYEvQXTUw<NMVMT~T;26LAD1E*FpK&8D<Z1<(;~St2me${PR+%>6I@LymI;3Q#L#H}Zv>*^oa)c)EXWE0?DtnyE6OwJxa"
    "T;1;ozUX5CtGJ$rTeO9F^$paFc#?F|(kvEnb*x9WSqJT5C|8LSc<-*L(BLa$WY@y0z7X?^9yU+xASo;0+#b_D>3-DKbQG;TW"
    "<#f}%Fb%}yR`!=Q(-Bayg_vluyGT_^w($y+51uX7Y!}&5a$`5$H)^mt*%S3NHr47h*j82Ki1vT~no-z<;`bU$rOdO3ut#NSC"
    "(#h>qIL<Dvh^v|1H)r?x$hvx;x+U2sQeTicd{Zf`MOVCEA#g|OKETb>(l~0&48icu5MIufe?IE*TzFn!K53NJ!#sPZW=f!lH"
    "dj(#vukRuzB;PpL2td=OOGpTe(TQl=3O_huLD+5jQzfYCb;(QBpyWYS`GN!-56SlvOQ!Z*7_YxwxxjT=RP5<90zUpA2Bc0{%"
    "s6nEyoZoY-PBZ1<q7Kxanore%=l)_b~D!FRS|3X)n>FXf?V>ATI8qiHvjP$@_C&ro+X`r#yOH+*!l)g)~lWE=M3WfHqC3s-f"
    "!`%>bx6yr@X9LeE7dsKl%OUdm$s)Jj9%sBa67qwgIS}=zYOBo%L-b?@RX0wZMImDm4Z_QUS9?-}LVpe;wMLk9pG2FgbsWG3w"
    "U`V!{eJ@kh9mj~>!68Vw)}!#<C_Hr00%~RGMWS4#CzB?Vg`2|iZnglR+eJlEewluYeIwxAvfT4yy@hI-Kz5M_wDVNUSa^~ng"
    "BiMqzki24HslSHK44Zomfmz$gA7RuUk#alj6ab*AqCmb*Px>O%<d&iG6^9L5BXnc6SwLwL;LH?t@0qLYYAz_iCAeW60!%DLe"
    "q-h@WB#LUfwsPRVyT4R-FAyym3lLq-eo*!-Hr9u+25&c_w&7js}gasIE^k8Bh%r1KLKk-nM*;<C}2mSeGWvL{Qmuv2N?DI-@"
    "%)nQ?nHd{uiq8xpAmY4&Lrj!is>ZPSbcF)ECXi|iM~_Yu#O6T4WtE>)|<-WXM`pmdb({&R9s)<3ndQLbKo|Jt&!pf2{yb%bP"
    "Q+@ih0VyyV}AwPyFABlKXxpFgdsA1Up$oj605Fba?)ZArWLHZ@?LH7;6t#aaM(7T$Z3=XNI;!Oj5>@51kQw1@9+6$R4ccJc|"
    "z<?`2{fi%T+RqA(lz@G3!)4PT@<cI_7UKtP<TB#Wx+?uS>kP;C(RS&L^i}q7tThX~A&;N-d)c|6#sOmWkEXyJ<15@Ujl%DRL"
    "T%P8<ZA^YvMGnXow~zf96n8EZdVul$F?Vc-Wu*;>5TzV-KlJKp5EYP{p}ESsclLB%%_N&{;`&y4>__=2IEu;Z>MXuAseMW3Z"
    "1#Sp#n1VO_@KTzB@=#6&d7@flk%~M&<^<guuSaxPk=i<@RE>FrE!fppzIr$=+YWa1K0|P2SO9bl)W(;mWmr-8ySrMJR!<3Z="
    "{Mcy_t7F!_y;s*uA59t?56|4Z5I`Ckp-Py~9`5LZ*6M4G-9T!Pm(Y(V~@dNlxyq&opjX#g}lzxFmTz-uVi7%=ohDT7im3+5#"
    "k5+)bh8Scs`HGbA67}P)ljT!>a5WdymcUpK?LtK6&!jnygEEr)U>UOuiu+qHMtz&FQ<+)GqYwPzbjtH4GB<2?*^wLXMWDI*4"
    "DAzWK#r(mDG^@5E!Wt`#;NMOLrK^5u%V9K%)mZH)th%3nut>MzihOkruzKc%KvKw$V0gZJhO@`Dhk4u`YQkYH?Sr55N+ij@|"
    "2)hYhJWlA!a>B}#2~9a=D=~MSlTw-EopOt&(lEkN%_3?ZtBw2Odt;T`-hc$&~vkP@5#XUN-e~F6r*k-a>~qD0EN6!8f1C}IS"
    "VO}d+&76aRM+wT_D80z7ej%uoX2TzTS=_cCk=PjAQ<;ec7{|(q6jF+c4R2F0SDCmO?6u#izi7UYfct54Lg$kX?C^U-tER>P3"
    "0iJ~W=p^MmEd{FCyhOI#1#8b5`+jG*+&hvg!b-0AkMbf8S{iTaTATs^Z<9aRgS&kV2$)j%XtQgp5!wTm{6Qyo3d4jx!O+*hI"
    "U!N)sWxvw{nb90mnc7OwLM;Ju37tkauvMi{?2gn@cr%wXB(bcCxF+bF6e9kLt>MU*d5Rt(fa{fI<;RPMYtuHE}K+&lMF#6i9"
    "4Iq-|%SN{VW+<P-m;!37-^G1k3_~POqF32R@1B7^FuCGzaz{2nq0~!tDdOjE;xb8EAQ6XeeEL_fX>YwH^)b)6xK?J>nV0fcK"
    "^Wg#cpw=|b?A<KV~@J~Dc9o)d=AzL-g+G1!Vc__ICfcanDyKId<Fsx9OUQ*A}3{e$jD!`#^A`;`7f)P2w<zJJmR!cM;|5i6|"
    "2}jlQNj1%tuA@tn6*xU)++n*SAbd1J~@9yy$80pqJj$_3b1o*FOOkdPs4%6raOc14M1pyKG5A9wRO&TNfID3h?hKf$$A9pjb"
    "r?Eg;w8D{|Vdk{nA0!>3>4CCheec$HtYl)%n3G;pEff5i2E)@o{Bb#4e9)UJCYm@S;Sa_91q1W~P2r2P=zp->svLzC2BBkV#"
    "2X6Vf{k$JiQ=gNm5%mWiD5dP2bj@~Su51OW(sB47ab)#1NvmxHs2mk6i@Hw3+=S;^2vfZpX{5p#(M&SxCVIU(XjlSplCdMO#"
    "Gqj+zXe5v^n7aB3y2_ONT2GOoZxz<IY}!e()}BDVz>)u3p3a)|pjS@us(HG~Ru%;Ehx#SIT%0Eos2#-)52`cof3}6N4LROmc"
    "K%%hSXTK#6b0gV7M`ojO&5><-o=KncyJfx0z}_!mTu&7@E%a0^}naiG1KUnWODx(F9iL+NKH5kUm{lyAd-dzx(jO`Wvr>hJ6"
    "7pe79B`fMI*=#GV^GAk)`|e{M?p#Gj7?f%@sj=Bwqm2h!}tPbSt~!GUt;)ePl6Himo9-Ufb%?qo`ckORnE_+X@PVnXBz|GWf"
    "|cPGt1ZIdn1)Vy{(u^w%)b&U=Q{#kb!Dv<EZGguhB&n80)DDSbl2YW7kse%0;xl;wbRth?3?vouV*-AE&RLf}vzNhLiP(hol"
    "uHot4^f=P&dWr)f^wgZS3==z<7;QsTnuzt}@F6WBP^1_W$y4rPYKBj1bk%lRo34}Td@c`OW=IacW{oOa-Z-cv}`0BQfCH$-4"
    "fp^mH3d)HLLdd88QX9efr=j}0X`8VPu~E+0K9{}?$tuGa>=NO=Q>gSSt?dCGNx?=4TE9U=T#6t}O|v`~^2FhJf@A<sKQCpeq"
    "w2z@noM_C8~V8+wcq@HH)aE@7)F1}wEl2ss0><1*40gaa+q=;wCDDR?K4=TWb!v35mg;|{0-#!m2_i`N;W^oUe0dF36)G{)z"
    "kdVbev0TnP!D0$_&LmfndrY)`-Z)sCuZx(7&}7nsJ)voFzS&GDJN#PXfqt<AT>$2jTh-(g*giRu)h(bIRTzXg8vp7ZgAfMY}"
    "ta%}^NL(EfWG`!#ZQ&R7&@=zKCFmtz`OZ%fu~K#Pzk^^nHe0rGE5c>k3x;Dr1eo!SbZYTtxP(4=kp73ZMMp0m)!yd#aG{YBV"
    "ujYHFeI69sZXB>5uO>+Hl`!?F4k)Y&cJNR+uNBL{X;O3iaye>oFG}+dwKBCD}Wfq9zKhDd%$tuTu8-DF~62c!cI{Ste#713X"
    "69#5&1m%F@b*T5&xe+0b(cvReF-nxNyC*BntH{))>F2PE&`hBCYA!$(SI=}3UV42%w7iXd$W~llpW-&m+eJ&$T}(w8C?jHlP"
    "(!F1AUzPM*U=97OM7u1HQ(kh^lyjb_{e-x_#CSu5@k9m_T7*ZbAs&9k?s4FDL#!dKavGyvtM-CxyxngIrp*6kXLaC?-Oyu34"
    "Slh=FEFAK#){n{VQ_k;QnKl3B*A7Qb)|(Sm=zgFy;HUGQxr#MXV$O!&GQ8?A=B&PVBfe(pG{`_`8q&KNDgRAM%h|<fd)pYxv"
    "Yk%PD7|wwjOu5#^!OpK!^`T24Ac$B~I5t>8auF>m)TSU&+g01Hj|iyl;t=3L>~L~M6vFaIU%`Pi&13FAbW(lbgart*DPy422"
    "wfJ_Xl(AQKqKsf)(*&i(EfYRifjNk)hgTiseYNi0R!XT(Dgm<1Nc2@IT0L2#wH2th$4|O}B${5s@;H6DsX?B;;82r-~N>Gzx"
    "*0m!H5peSAZ$Q;UKr{ar5(xg?>58OlYmT75w<9$S@Jgq~|Dl34Dnl0|C}GnYV+1h+pN(&_+m-Vv_C=r{vC=&-9eSO|kf7p_s"
    "<w{`_k}a6`-#p3{5j1;Ovx1(i@J^eoO%oUS)7!Tv$ntSOa(~U9eV!t^2T%qZ*}+;jnaZ<^a7m-`Yx492h~7G(M0cssWtY{fo"
    "l=47QwF%-?1p6wMH^_oOrG|g<)j%z5LOal=)LleZ}*1U#KrYLKMtDoJX-L4>Ax6XowlV$m4gnGkP4x7<i`yqjw#l?mp>e`tC"
    "ks{v-i&TR92h+_~g@wsm=q2*5kJCxtfF5ovM^Bu1rb>WQGvIU{NXb@?tt`hAb!15pPl#5L@(`ByVFY!d)Gbk{J?2|zWJ5Qw^"
    "g#xxZ8%H*jazbAi1MpT}AMPbxJ)T-7hNptTceZIzR4wAk^*Fa6Hoo2Q|UrB0j??*hK8{5smq=MD%Y>#6<HMJjC?`z~!R~@S#"
    "wsI$-ROtxs3`Ibapwe>OY00(jS)$m7LX9&qO=TG6^C;a6Q+<UvCev;3`eode{h0modhfDTFL7|-wmxjUiq$&|HrWU`4hh5RM"
    "kEwLBf6~<>Usg)*(AuwC_d?XX@4es0*P)kYG<zg;wXQ!NPi^SvJpWMB!3<uGwMe!nke$44ePJ|ENrRn{T~Ya$CmlP(@mmb-o"
    "u7#%E<(Ep3o7S$%rp#2wERa=IqfL7$N&!nL0s!BtPnakNl#GlC71M@YY!vusFxs@AF>p*s?1sb?Hyptw{nQg>V`s*~>jpx_&"
    "spwPL}D&<!2HdV{N`@=|zlv;Xc}ja83o8y2W#Fk}Db{Q7bKqiL%J0>x4V7ul}tvfL1U5X}J}N^LivjrJA}>M0Oun?}U3{xVF"
    "5JNyk+p>TGG3Q}p1S>vc=cJBB`pO+5jz`VDnOWoz+LTwa3E`rrhJ-XEWe(9I@=cX<^y5u;r&fz7GHL?Lr1N_z>Kwn<W7v1HY"
    "nhICzkCfF@<Q{<+ehQ^DkkX8}rr0ovxu0K_3i}9qus&beQAqNxv$=2FJA5O9uYSy*ZK0^Oqny~OwbQ*5K_q4CN8;3<<M|rfB"
    "r1r+)ye=@d$k%bo=P*aZ`KL!AJLr#-jzkro*OWMlK-55bie|z@X}a(YLl&IELa1Xk;QN8W?*LwX75!*7~kp9B~C5vZFoH{;h"
    "vM;CvH4ugGag`oo!blXO)tpJwjU(7x%7jlWdHHrk-G1HV;tyk|w@ODZ@A<%&?uKldAs2+I{-AV4e=G+s)t)NhN2vk-$aeU*U"
    "lHBg#m(lWJ&=`m6R2h$!_*PuM7TJFOf*(`K;W3qz~^9wvo8LRvMT*am&If-GVZ?5-q|1t2V<xZ;&1QpPW;p()uc1`KuDbs{Q"
    "D55w9->^+&;Z>oWNjy=M74q1aWpY{j2$usZ&26oiyS}`WyzYCE=paED3^;d4&HU&@xZ4cMxGo=M~YRr)I8$_-Mzq0+eL0HJ}"
    "zhkpt+jCrDwhYCD5Mx#l6uycG@f45Sj^=StMZ1W_gCn~=qj&boM2g%E3^PXbgNq9(-Xxn{wGLQmVJb(*@9?W?zLLe{O^kYKd"
    "SJBUuliLK{f%2Qsn>>@aAV96HXk%5!V+#gs4boSHleiG<5$0IKd4&K$k0~y@>1lDYjF%oM@1h#;bT=Zgj*@eoxthR%+%v-x%"
    "sGHULzREXr}2UeHRA%_8)$x`nAalx1BbLl9Npcym!KU=&KnQ@U%Kaa3eY366T`W`P44-TR5V;uW1oKZwPTai3TT88^zK0K|i"
    "?5mgeZ~7~#v5J`mB#0e{GB&4Mr%fdhiXP2W`}!~==v|GCbU%Nqoj9T0Qnzbq0+w&g_N7f>;byo~M1+cWyp%R@3N555h3e<?g"
    "e5|{ANSrDypgzO_T2;CQgLZGBWx{XG$!E@){+h}>5@~1V{p%{E3q0TI?<|KI_QD#UPVA6VWOt-jwTwV}#yMA1I8x(qR{zT)>"
    "q~;T(47)Er%d&LW9Kk=~KlF98=ko43lrS&2CF1Xq#2gKz0T#Onk|O+yD7B=q8*U5!*7CqG=k|@FBaS6DY`;55Vzytv<>)43n"
    "$<6#DL^0x>b;^1C-Bbn9qF6dX(vW>|J-(jqDt9HjP<sNNJ4)tJ1~b~k2(hm{56-r5=2n?ixRp};NNN~cVQ^YO>_S2u4TRAun"
    "wm$hdl5{qx-YA`#fopsv1THGdBoUhZYb6<OP)A!EORS$kfUFk;})^gK!833hNd>P;xPb5+Tzg6*q(t3vKi~%yT9%+-632?po"
    "{~kecOL|NE)N+_zzFBj$|8Ti#bA*-u#C0ev0*%f|yduR3<`y~(110Gr1FLI1n{;$QiYpkyeGP3kpQtEACdeI{X#A7VA|r-X2"
    "0_)f6@^<93kxH$5&<RZ*-oCO!JAXd1Wze4-@g?ru~HuuN=Q?cb9$Kk_`MJ}iZ9P|}Mk^c@gaUPxoPT4LjrrU6I^2gLu5m7<^"
    "k93gyVZ=iZH9La1f*?1G*!eG*Kuz?2ErR6wUht*8sj^xt)10Kb#47f|-V+sroR6a$t=uq9I7_`l5G(sg4BQpU>_MY7PZi1@@"
    "HVd-DAGqmAcw?8aj%HIa5%(*w$s<CwndYAn_OjV0smshOPa5V?xIo>=299a&=|Ad>68WeDs7RI1~~2ip|pwHhn^|iafD~Ni)"
    "qVY+U$z~b5vVLxW!`+*G#uBSrMPVMZZ$bWRLtv4au|b$!7-K8=+gm5UDf<u~Y}4$>Ys**y(M5VQs<t-3(Is`Bnn_AN2(ZEub"
    "Z5?RolH$exvagjT+=q7BUt0MI<=!87G^OK!DKTVWz|f*ek*v}N(oM@3HG1Bt_3{#|tv(bu~jH(ya#FLbJWo0eVNPKHPytF6#"
    "cRSPdw%8pbn&)w<M?Iv=l!0UfJrW3irzY-=G36%GV2}WD2Rmvhf&@DC8Pb_xwi91YJ)s^wFWS;6Q`{tVwx)q3iMV@PbNKwM$"
    "Rfh^T`Bp%@LpzQUZSeSKz%8{Q5}(Tf?gwphKMy<xj_>}yY}`Hc)1ZxULQq@kei!O|ZID==jPB6wkb{Vr>EsLioWcooc$(gg_"
    "_+i@pCHaB2t|qVpQqcvjRC##U4@NfM+*m>Ep^(Rq$cazB0yihj%)4tEirq1<)pcUBaG84kAdqDFIQ2qG5*CPxqUXkEjQvtX="
    "RNUod2*7H@*@a__rPe{)0?W10R3sC|GI~fg~sFNRUvKL{r&`MG7}>w5ayF25Sw~RQ$GfF;gc`k54J?KN|%6F#^?kVLIas#-O"
    "#eU&|F2xN{H8WoF`asiwE*PO`Z|tOYSthN|2JpY#q;0m$Wyu`j9pOGBRTi|=sHDZkT2bt+nsh^INX7Cb;#)Wu2gP`PqOY|nP"
    ">EM%TcD<Z;_F;A})=d<QHSbN2nRTh~#IzuWx&(=9Aeh*&38(N5^8}K30L{OlmTYzN7F1l_ic*y;x%zD;zKnOgN>i=RUE}cgr"
    "X+Uroc&2(ZQr^akiY`Lgw1@%QZ2nS_FEVup7Qd;uUUUG6YFcS<&TI!h|2yR%{x6frH^CT^p?^W#M-MhxGu_%UQAf_exTkt4u"
    "brnKyP*H-n>o=$|5$W?(SGj-%EIJR+=RC&ltw-8Fj+}>?OKv-kvX;ajg!EnJWkx%@qQT^>|4~J@_Mz{M#qKg>PB)npv=yxZ;"
    "8TY&CK%KnSgJEY|!q=qudUe78HvFC6hxvOviD5%yaG@(+zGj3K}=tBxtHbj@do;j?$W99$2#V<oZPQ^7>^OhH=#SS{)wL@L7"
    "$Ggbj%#=Mm?9mwxeL&ASgh(+pTQF*j!fBH<<Lt<K8^(*{56+%3p0@s0vgDNDE}2t+rRv%q70f+pjF%cN4Dny3Jl>z336sN$1"
    "$OZIC`W8LD%1LyjQC6wT*+J7}d^sh$zO$q$z^#gFhdCgzD+#x`^>_EK9(9i5u?kXvmcfAK;rjhYEub_9Ll_#yCh<`agp1zuS"
    "AR|cHEmcG=>A#8IukxKIK-R~u4sU8d0Oq%P%PW?@?o{;{?U|zAaJp5ph5Tl6LAVU{n16vi^Sw}cpq0NON>4__8m-(G&3u5e^"
    "{b@<@2gD|Pp^v3=CLCAxV3kbcxq8gD087_(fM(C`&EZWl*(cl-q_x21cI*14T24-)0lkEoRM3gaJVV4alUxKre!$cu|(!0){"
    "82mJ8D%nlUGRQF#6wv^*jf!<E+0{0)G}0daJ<+(m;?v8$13(3;zRjn-&U3SOS8K*~_hJOrTMWvAcMdEmSz68~~C&Uv1i7^)~"
    "{ih|7UHwA?k$d!tWAtTqh^O_!mLz&y(14`UkzS(~-T->AdJl@1%Iv~dtC7whMTKNRxpq?aov{OTCg7pLRX@R#}r#!eA?y=}q"
    "K-fAHfaq!PqHfjB-+%Xxxr}S$J3OSfwLVIlkeO<oOtsxjExwBQU)ECBakQrTPweJTLA}<ZkT+|^$ivp-2)|K-IAWB(42#w_4"
    "j~~(fntTbr8u=m(G7^xdyn&BNU;d9<VDgC<G<P3AL_7b~%C%hQ<`P!j;!a5h1#1qFuC`5F{Q=Z~7=^?O5pu=569)yy3qq0@x"
    "fyM1uZHN&k_t>(cITa*=03J|P883;J8xhA#-k)-rk&6*>$tlf8>=229Sw(fk9&(n4f?Ua+wQv>6)pAER?+^r8iC;BR?R`Art"
    "YFaVuF8$*?Dw?vQy>JKn;luE|d;O4T21Aq|R#(N~t&^WGWX!3WEs|!L7dxCYkElWT8Y(iX)G{R1JyymH?7%1lV7v8izZ_^Hq"
    "vb;H&*Iss|EWK@awGj7a&|Rv*#l)+zSS^UtSpr4DrBE;N!By4=#KkuL_QitW~<9N$bA^iV1A2DAu%je@*en!{HXGKQlwH<KG"
    "p#I30A8s!L$p%%3KqAQ`f`&LXxJtg5im|==fhTFo(*t0GIRnE;`b=Iyi#G;R(P#8M%0#z_E0x-~iwzGwF<>m_~pkg0C&{P^Z"
    "5f#nks_q%8CFgFW8jBPVS#v!wEHjDx={0f41h7%16-5qa3o!*i2Qt!<RCK?wsTQ(|$bVQgkk)D)t*~<LTHR-g?t1KO@3))JI"
    "?axe=Bz=MH^0B)h1}q8F}tD>Ld&$n6Sago6cfx&kISO0lq7q#iRW18p1>PzA1Y_t>xq-D<>$0(*m%9iOApXmzDv3byteAYn6"
    "}mZzyvPT?b<H&;p2~d?;t$M6lZ|>%HaMQedY)xwrylhgJ9DJOjfZPx3IhB^7JK)%^9C7R5{I+lk}^OkEpWuv&chyO=SH{J2Q"
    "DsYlo~Gi`#jkbejD|3G!8q?SO}C9grnv|MWQOSgNfpcJ`BxjULP}hJa@iaclFWyAU22<uX+xSH0&36Ih>%4D}ajnu=sNHRh-"
    "?+WYK|M`|K1^Nq<cABC=OcS4eSYCv0;kWQGvaAQzX2CI~jgt)j~9ys9lX=Z2ku3ZSRlA&fIiqtPR?xq%|tr~|=^R(*iI1P}7"
    "=!6|7Zc`An+xki<a^Yo0gifrYA+4gHsk@v0Ajh8$RN{Ua;qrYHwRg1PaVZ#8NlUOhBp+>kE4FBh*m`npvOIbBUp@Tuvl^fTG"
    "ZsCMGAs<I6cSg6w-a2s&(i|>DPWJ<r@k2zCs(Z0{!T#53wp92Dayvv1tM&5y5s^SSAf@t>IcR}rShfVuI^N;L$=L5z5n`UPH"
    "Du<6+r-=oZ%i}>gp=yR!$6kCyf7>vro!v{#xnQVS?-{;Izf)F3X~Cl{5T37_Rd5Vr(J<h2B^Y6vT?`#Pa9d{@Y;LQdwlzZE-"
    "DeUEm3)l`B9t&a<s1&VF&UtuWPad&XFDI-Q9z@8y{3+SaXlP2VeaniP$sZQ+#wORpD9P3?JLfdAfZGenI{7NipD?a3hOyF9E"
    "P!if^~qST~(m=YA=haHv~D68^b4b#FXsOHnp9IAD~gkhOVr83p8<Y6t3=eJjMKR+iZKYL-Y!)xl3q)2=V=sV+Qd)RUZ`WV?x"
    "tc}9ZiUV-sg*@g`Y`0uWmf%tgxQgL>TvqxQevAuO7aMRP&AxCjLF8brbVXb&2T(Sa*>W=5MQREwS6E~^gP%B{#p<#xgL>-&Y"
    "Ny#K!l>-nyPmwkkxU-rG+d^3)^54!sipzLMn&5`d;1GV88c4nQ#>P3V}b_o5zP+MsToS>bIlYk)t!C>s}&2+&D;p(OK15B;+"
    "5{`ee7-wkiJ+w>&qV&DZ>3mH^jm0r(fn^xOk!~VbQTH!I)Rznh|pP^j#bJNT;}1btSHDN;-Wiow3)8aL+Y=mIQC`^BKYi`lt"
    ")ejUWq}Al`DKJFsvsqeBTLoBjw)RLl<u-)S9w9UP8xAB^nmHhm(2O0WOr;*0`6L5QITc{zhdlsF#VHWN5e5DwP*E%x)ez~c+"
    "-ZE)=}0Kd4Y2LICTNUw`x5;?D|za5Xz7tY`v=3uWVx`m*aU#?no#DhYRTP5h%Yq#f873rU~a*4jBQ}oBKk3N%R%_u+Nx<?X^"
    "ehx7KeBT!7=BGQkUs68|%B<GG>SKl<;q!{G2zF2IVy_0s$bkKU{BEr(10n?1y~?(P$uZ5r360@6W;He;7c3t}=1TKatL|ukh"
    "<p&2e;4~(jg+}dZ``4AsF}(j7#Gjv?ZwZq4#(fCL-xWi9_kvm)01~7XJmlssM|iPF<MTX?v7)t3-}5!U{6@0k^Q<Ku82W_X|"
    "g+L64SnTAn@Lg0bhmLkj2VYgK&@0`etY!n27q9iXDY<0{%_}sN<!TZajwwYb`SB!qdx7<AOTVbJE;2cmUz-{eYOk$<B&$90>"
    "Lr^h>{Rkd#^l{s>t4esL|{ue(r`DKQcjOu3n)5SMrz$%>cm-ma3E-9)T)d7=UN(nYT%r8>KNA7Y1uD%y9BC&o^<t@4x#>MQ("
    "?OCCoP1rE0pRxduN)7Cd;%;%_(uR;WC7bs2pGM}smwl^`3w?^D)N}hszF!UVcI4_KYs2Kp8^a~a{TL%B{z#s4fY~p<6S7<I7"
    "vTXOR)nqv=fZw8R$X<Cl7x!9Ty#ORX2b4k*66ir6l>dP5u28!(`0j?$$|Nxc(;uD|$9dk}20oSt+>|qh3Gidu1<xH=-vIqV{"
    "T}wmj~7Q(QNfB9nuvgCJsG0enPf`1s;5V{^-0)D)7x1rJ&Be#syrV7OF=`7SVWoDrJ^{YM)65Fo7SVfsSb(9O&^MKQwkwQKg"
    "X?Wu1?nyX;eu|ILnTNs)>Xk=e%{E3l&P&(qYS|R87;N#nNq>Ri7IMNzmB$RFi>+WE$Mnht(BLk$>Zs4Re|B^aAi$X}fP<^}d"
    "~bAzT6&W9AXq)uasC_CutQ0bY$Hu@2DIO+)?#c>4c+Ct3EOlB!(aZm}T>f`RS*HZJo8_zqWMO_ZggNK5o@E<*#FAXPW_MO>*"
    ">&I7ego;Yu%Us8HQ#W;iO;cB_O0yJ7<oq=?1o9!o~4|I7^@OwBVC|n<#uF)d>w;0kPfIb}$z=zJs?^AR{nnP}0gQ6?SLq1P("
    "*E<R^?$C=#%Ut`8V8F4;#++u+As6xb_dz;tCkIgjxyq~k*f{SVRGR&;00$o!1NjWXoT*1-b>L+Ar~6gX$sBu1-UH*aWeF+|f"
    "0J<yJWtNOd-;8=%z63G(Ab8kn;Xg{9Wj6+axer5;(xU(1)~7PKVA4^9MEpzNSlmdNC0Rc1BNoAf7tupdm!qsh`2U5ii)lh2d"
    "CYZy#Mf-p)CZ?iq=xOws?+q31YrBh$Hh?QX0e_a-hFiI72t%W_@opm>8MN?^RQ+A9HBU8{?u6O^I?wbN#)v5v6ewb%Kq4i=<"
    "bi6;EcuVVEW+{8($%)WI<7QXoMaxAMN`$s!kJgkkl}w$})y$N_GNt_B<lgx%UF0)4+F_ft|@3#<1#UC5Zk)Qw6Wi^dTj{|%<"
    "2^Un4JSDyj+%@-8&rD;$3(`s>7jR7a^KWE$jDchl%-MA{KOCT94u`~?^W!O_|>|F2B)0$Ddbut(rw#=dF3{+X95sMwSGe3W3"
    "w`K{?QGH1c6M$gqy}O?32&c1J?LQrd(U@n>CVm{weg3kTDUom}sMF9hD^yu4J8_+c@L1^n^pMjK+!AU)zbm{MH22A32a8sMk"
    "AIuj3nItBRZzh6d=k#o7p(;)7Xk5Igvu@l&sAc-@bQ+Q4qV{tn{1VUQBsmPO$!24PBznpH|boTsXe-PU-Y;osu^JH0ubm5pa"
    "R=L$NAh<J@|(D7jcO80Dn2CA9xb%fG0i+B0wi<)%smRdo^Z-eIBcft#M6aSRe&dQ6hj=h3o#l#@OE3=n#6Es_q^AYECRW0IM"
    "bF8^-ysS>yhxiPS8T$}L>Iy!|TkZ(4c1v!gD|JVvFiM|5DdbsB=&9jk|?$m*=MGRHSj17<Fv$mLi!`3Aol@<R({xDUo;Lo%H"
    "9_haV77vq}*wfVxvCL@2ga`2^6=lCo20*`E?OUI;qMIgvhUp0H81<IAv(5zl4XKxdRXSfxNv*dAZ1^5j$u~(j-3!!k{4j7Mz"
    "Xgu>;E-5a3j(2v^FwUTrlk+tHZ^bHb#?Evxh~toq_kIW4fs0_fTKD-@U_D74%^Fikyog{}CB190hz4A5gmm%>IkW)1UTWKER"
    "tX~t32%~#9A;=mG-P5o;SpgWF>jM?UVdly<#SgsY~b>eqEte_MpX9D@+X@0HvBb1a5(R_a`RF_dy{U!6qv7?gkNV_=(-J`;2"
    "!&9xDZ$~{0_<ndXxyTY)d~JC*0+RY~nr7Cx(K8X-c^I^>j+3#UG<Kbh;uLcP6`?Yo#N*Nrrzv_Rt!1@Jjt5V4`iId?t`KIP1"
    "%j8cUpmey(|JF<spB7PDbRbH{JCpHf9xpq%*006jSPk8$2nW-F%5d!p@Dc1#6%F`ul##LL>rB3^p>If2i<C&LKhL~~TYt3Ju"
    "Eq2VPus!{O=T!%s&5JciO(fm}VJMo+tox$(0^YRaUu)>?OkC4m?(*3U7ur+;t_BhSrfY*;Hv#f^b)dE*nep_hEpr4}i^102O"
    "uB-?_%o)>GY(K(cgyAU`7|Xp3W=ILar|^bDN*4NnU0M?G?NLPM7{E}Zm+=!mZaHpBvygGbk#WOa9FYXojK$clcG$g#l>hu%F"
    "K6+qwq||JtBdgW8}qvt(an`?I7f8!*=Io(9-a^^1PN>+^OlhEsow=9l;GgfNEk8?NTBF4zL31L*P-~e$}s*W#~6sh9lkimnk"
    ">pXQIan;^kCq>p94pFLn+7YE*DaYC+K8}ZvpyqA0^g!6%pi?Gy8~~+|-MI$9%U_Cty-NLfTHWyXXwA9Yz5hBN^YCY)l?V-gq"
    "W4;k1}S89hyLEYz&qSjPoNj3RWsjM&KsC8V{##3K<;&|!4wAH!G&OsZ7oi+=k+rBDM-^g<OEs)ryH@oQ^rK;|=*j2)HP<ygg"
    "}Rp|QPej@;B;;bS?vLLU|q#~#M=`4gmbk>7r^x#3Mfqf#7@BR3d?<bcQHB&~vrw}x9`$tyb>f~%dy&ZZ;*J4G&a<6RAWHqpv"
    ">FBhcgk;k#j5BT0QG#F^+|Xkk9Mq@x6V*e%Od1F-v?}?Jl0p=G@WzI)p(E#;c7m)5NhL0OWL`q|$9WJ&n$Pwr72kIL?Fb%XZ"
    "<8Qqwg<W^F%%1e8PWRGslf%A3dHn^-tH-P*3=COWnMe3D9xu(G{beg?{^g0fB>*MQEh;phr|&xb5IwLG5ecJT=}-r%5HmY!N"
    "oiquw@KQKAPf9s|}tzarg^#;q!Q+n~l``?W!YN)iD%0MFf2wr1u(wiOmta+#vhW$empK#VoW1*Q3`@rZQ0AX=Z21SLf!>J#j"
    "6p6E?hVvNcKW5=dmo-Nfh8;P3ML_|Wx|yyH@)Ky)W<oDmM3+oKQ5-eoWm^5Cy(dEh0sU~DO@aCX5D-Vzn)q3#PvA!N+x|Hzm"
    "owh>OBjxQ7aAO{$V04jK~Eg<&1^KMD8XkC)o)Ca096I{X(V5=GE=rh=bf~0(~nhaX)mEIQef_v*+^CbKefVRE#jc$dmVtcgQ"
    "YSKm^O@;cv2a1w@>1IJEbWXsDoLj8K0Uqg@+(Rp7q1U2`yD-^fTr+(CQyr(yHw@@T7sO)Nfmnr81?us&K1~s8ve2lIAL?##1"
    "#W%0!9p+p-Y93+*Cki<7B7#qS+Fgz7~+pjy|?`ov!lotmYW#lqE(=akl=(N58?W5=D`+E!!XhY2Pf){)80W_Pdk~O*j7z}vU"
    "oJ=$BYF$f48#|<c+BX5pv1vfhUqUNwET>Ir|DEro(sqE7$7<t;-kV_Hb0?@JO$q4WU@8b*nRnr*tvn(P4|ZEc1t4V>HT~Pp&"
    "t>IEQS;XwXw*q||8mLh6ca3pG>)dg&lh=E{HN(OPx^Et_)B_a|J_r)!lh?pY_F#FXwRBm#u%oc_{}9PXf%R75fkFFA{8B7wN"
    "4u$6tKK3i_k=Yt2CYF(8;=Vk@Y56`s^{u(V}f<VN8%GMIaw3ImeG`LX%uSFLbOP(*~=$7AzF&ApwEKaog96LL4kiNWKEs_3t"
    "gafTUusSl-7jTWMsHM?m0r;pAiod*_I107>O6|l0>j%sI5bpOlx?*u3{87IqxR>MI*Da+QZ}Y610S9m8zK=!oAl4sGvL_(%C"
    "w;`wQ6m4zSGss=j8KbP&NK1bOvpYz(!x3JPjjXI_FE;}vV^JlP!liGCn$RT{cX7N=!=9HX%Asv@;-#HAsUKg``8>gDKZh_+W"
    "(KIZ{V)0YunwiZQJ&aZQE*Wqp{Jrabw#y8#Y#B+jesD^!>*93G>FKIoDXX4iq0|K+Lp1pb-Md)_a-g&7`3|B)#L1uQPLsJ1z"
    "vom3?#szc&}6=I78>B7#;lLaWgb7|hwZHAiHYvUCF0nHOn0D}6KJ_<g8539nLFXftqU9X%{v`4u1Sy1<A|7`CTaORiMAf?Me"
    "p;4D!8s>mA)*8eSHJ(^+k+Ro?Q@0AAItVvA}{6tm~WE%Rk&J9#E$GdR!l7IK7Rg0-_$+QZ`rF(C<&4mAi_w4rMNu6GnOXTU+"
    ">4DulK>6Ae_<s@tB~#syhERl1xWIxXgH2;_r2K6d1s<*^7K)46DnSB=8yvB)VZ;?_lyG_E>Clmg7KpZp=T<vDq*Fm_Daq<$6"
    "z1sJpi7SP?BE0{Rs@(wAuhE(b7%8(`(P=2eRMm}yoxOsq>kNbH566ms%ctPx{h1o&x83}ncq_kPGT{FY^DF(^0icUfZ}}DsV"
    "8V`@7hfDW9rVJ%p0=$w+$qF_q67qKT>wT;5htFb1syoh6{FCVXdy2oJ`wHGFKK>(y@e4tadx6f4eh8?yfC36xc5v0ORlr%xz"
    "!a)wDtMN#leo96D{}kzilCi@Uwe({1qSN0y}klQRHc6hZhssqhmnsMhkI*Ug{4zm<Rrn2(_0NSJ%AvLc$8lQL|at8D1S1uEP"
    "LAh=pOigj(*IMyE>^8-pja0>0UhUPEh;&!CfSc-mD7d&HsyJg2r^}2Jk^pGA;&#T(PZy-)!VY3T!KjsjQsMNsDZ4RJ_@#kO-"
    "vAyK1B%cpK9+9NF*PeTboxdz=)6*l`Y<H^5n=^Q}B>*qe&LFulRYDmLd0;8_=~V1O7BYqzC!AN(WnX)5w|V;ga>y$F=ClOyC"
    "bvXvuytqDm_4M#5X#^O%j<@#ORdZYUQYw1y~MIi>}rOf(o3U1ywt^~#Eo!dDVY9#Kwkwftc85M=H9u`fj7Vt>UU0>QM_r0ht"
    "hjoQqS@7+&y9jdY5|)9(kbxx4{JT0Qm?xL->N&n12vUZnmaMgC|T%2e2&oFda#x1n{e&Z<oL!q(hS9N}<5xZYjA2cR)>VmB1"
    "lBK;pb5@W4~G=s%1>QtoH>t#;a6XI2}db}K76Fzg+0YE6_~UB5Pjzv_a&7t=gV3E!}}9KFjMCY$bcxDlYXF<1Fs#JmsP{=6k"
    "IrfB&wgL5dxPU5Wg<*OAZ`WUnNI_3^*e}+htv38aUXsm^X2ca_Z3W!kYYz{rl@~j-0^;WFkc~3MmVe$CB=rwd5(&&_k$$)+q"
    "GssTskU>|Ckl<Nx6tPGkDpB>W`+@B5Z2#s3)I&9%_!Am%CG{^g)4hp)Qgk-><Jp&bnD}!<>EFY<hgiW=FZl>&F*R;9A`S&g4"
    "9BQk>BTgZ$6kh0_;l8T&DXO$a|lolK3!rDtlYNj>Tp@GvS!9#gqEXRd!U**Hg5<r-sQdPMrH1+(F!58=hRP|c8Se=N-w8=p%"
    "d;u?3OBja&}}>$hU`lq&FYDIwI$;S}4x{Zka1Ol>{+;-qA|35URJNuuO-CEr_j}?E#9EA5D|$O0LDRaZ-+FGK7ycx|6VX>m%"
    "KKGJu=Q@!qpef8Jd8TPijiRInBivPcN$sVmP09K_#v7!%&`x<A&gPQ|2Ea>-Fe6;lY=LMe^QE)p51vabGFZel9sd)I;IT;b#"
    "t=<?ePidE8wRfcDSWkxB)PVhadK(zy;wZ%c!&n)+FSK2Q9LrA3KEX~i>4<&yB{~2Gznj^yga|NX4g;}Xobi^b22T~Ju!mxN&"
    "1r^4sZ%{Z6@Z2;*+q*%#+g<BZP@p<Q#tTwNI}GpP@=>}g4r-{PlBiK{6roPfow>(im1QPVI6;{pdjMbzPf)wqCxoyT?mr|;@"
    "GN~joCpXhz+$(on_1Jk=H*t}Uy%@-^8`#5fhI9bm*{umDw3@?xyh&5_Kzu*#cun4RC$t9bJdGOYs8FDLXJ#8?usBrr5|L`p&"
    "8M91C`~r)m?d?xaMFi@=Fw#QFN__z%`I3({#I1_C+lF$RgklZ_F9itmwE7(d=s#g%CzhZqD;tz4>#Y>2i@6Tu?NzZQU!Oc?O"
    "=A-PSwQ&6)6^Rlkm4S25tUzl)-#RFlbG#Ngs*wS;(%$gk)TCqN{)RC4vIjr5uKgzrbm8{MJC^x%yXJ+F#=rGFP*U3RHRSVCD"
    "KLsuv*7n|J_MD(}9f(Bk$3aYh5qkr$Wh4{Vy!sw2KYaUg^>^p(?Q+$F$4dcU8%P($vaBPo1(mXJ>lu1Jro<N)s=%5p8hfHGV"
    ")Bni?sT-N_Lnrt^D|s;#*dHsLl5Zw~LhXM|^Pw?O!3bp>$cF=e3<9ExkOlv)hU+a6F0<kNVo7Ea40I@npphYPz&2)ADRw<I#"
    "j^FY=fGX)FSu|~M{*5$p2zwVxa=Ae&k7JBJ_jCYFnWnV4KpoV{a_gQ+w|$>8e$}p@bcc(9;Rx%4s?BzEOyC&x9n(7*foQ^9*"
    "FHP!YmfcOE@DUFs~aE6onKlTEPo1o~15DR`kN~S?LLjK2Pr%{&HD%Gb8$C-p%WgaTX<4pGAs0G4HyLR9;R^IRg(mxV{`%q6V"
    ";J#;|0xp&(ofu4i~X(n+lLnWlNH<u`#ecrYl19I@aWo$DQhSBzChid28(J*E)xU0n|RB+EbSMX17~zqcE*o`DnFe#hTrI{%>"
    "B7HV%H6h`pZXj?Jeg!x)nh<{ZCpRDMq)Q@zzQi=#;uNv)=zKwxoPY;<^z9AKxb8(yyI<)2r&*|3&{-x9g;9;K&R(#~TBP)ih"
    "C#_K{in%m$*y_gd_dxq~=v;872rjK~Ev&WZ&Ty7JH>4CZ%^CBCH}qo{nX495!t4{{QJ=xHN+50N?_12YoQ_Rqiry!lRD8Jm^"
    "k}f|#1<+Id&k3Tuv+7mnoDk%qmHt(gTt2eAZV^e(05grA*UwA9lBzCB5NQY<UsUm=YOV?*!G-+Um1D;rd;{M{S)!}x}720I{"
    "O0-^T%DL34ljSG_D;qtqNm=Hk9=ak4)T3f2G)m1bZ;5oQ0uAIzT>(vn7>^@42b&w<{t$M0?i1LlzjXG@6n7B07V|%Z5joIWe"
    "q3GA|<p5V|TBS`}uA#!0#%7`!)*Hlcm-3GBZGmiD~A1xC|S#!zxb;w|?fw0JhqtU1Bf%G*UV37KAX%y{2@pJOb`zXDAbZ<ZY"
    "daPc&)Nc-SH@P+?kskX$f#IFFE7EtNNZ=OI^1v$7+(7^ip4RcoIaq|X6vaFPozn)YIUa9Q}0Y5Y6?rJC7z;@FGj7Q>`T_FCu"
    "Kx~M*9Jlc98fV#qw0^+gVijX%j41>xL)};pOtmBhh(--L`}ut~H0@KY;o#Cx_zLvr{mI3)joasu{tH0?@16fjLjO{5i6dM4w"
    "j!tk%8+malD4fRE|}vsr!|mt8^q?AYcX^X*0(y_va-cD-WZq-d$leDl9NTeEm($RXy@GK>*-ew#lOPx*kCXVU@m)WPRS7mtQ"
    "wE2eB1ZuLANAQEn6o_rhXBGY3G6c|1(GK<A6^DV-Vdyu7ECnb8M(LWw{M4IZOX7BP_J9G@K(Dq?E@oaW$s94@}6~@%|j#_&4"
    "-Bp8!V_k_VJ{w2ck>Y#+)W>o+Qn1`Cty@=pXZ?`Amwzell<v(sGciaAKnbG6E<M!<}B@g8Ng`j%bmia4#((F1<8Cr#)1o9NL"
    ">cMscPyubE7lVGra>7f%oM}yzmMy0Up4jvAml2b37fXjwij7~DlgT3$U@z)~d>M@A^khdc>YjXjoce&xCU57l<<-4)ZAj5V~"
    "N9t8W8OqxJy|K4IOm=>-L0q)(k{(%?6jM>5h^K;OJ5`8+W&V4v0&MIAkQubXRY2@?){;>8k_Y$8W)~Ra)Z96M-eDt0*L+O1m"
    "mM$Fj1zL{;~n9e&wcLZai)$!FgyynXBHec@k5Rr-vMc_23P>8$&JqF;KpVDtTY8{HSN6#5N@iGw_ZfjsmuC?bik^IuXEc=vi"
    "kEt&G^T!vl*N>+w)f?M)Bp4nDHdoAhai=1ID?XAJNs$y%_b<9c~M7k7%cLB64i&=2*0UYH5AR!7Z;iX4BDU$pthZ4OUje`Ju"
    "AIW0i>p!aHr8<d&GtRFb(f2_iqmdp30%RT3q!@z#dSaJq!UJoU9%ID7m+6d0jey*X5tj_f-8!E<C4x28I&uF1;$^zdAbb8>#"
    "C=)jWs!LF)7lG)>~kDcV+wIa?|v#Ma-=}XWBT6Z;tVOh?DuIg~4Ghi6XR<Uu^fTGWlbfche?GuF-U@nI#X$i0ncsjKs`MOcj"
    "2G$Mx(JDjE{kquHK}9wp0Hkj1N~7JUzSBYX-w^*7!llSHIfFmuT0_$9ffIir9G??D8RmOKen1_H85_hIb_VG;bdu#T_SwLG*"
    "*V{U6<Tl00T%;#1^z%NrT*{3Y^2W1DXVA%RLui}BAKA0K8cGY?x&j!D*!vexf}i4XD>7zg+KF+Bb+nu#WnT}>S-ULF_m6ppq"
    "5EsmUr!lD(Yq-`vUCu=sd$|<tedS8TX_zWys$NxLxuW5N#d0)ZIWD$JiYirRR^QjDFJo4PZm#(1S>NN6wjiM^<Y_vbRTqY}t"
    "t1JZIYNS<D$kg79sfIOVi^d-1`-K|OIv(zf4?a&y&(56pCzivprbax9HY*$@{cIbC4yD(TvV%N-HRp9*IYl`^iuuxvv<DO3e"
    "aS&vBo%SHH`FyCo2ek3qxZl~C`ESHcw+SHMzxl)psyZyRzstoQmpQN~_rrg@KQoAZC5)BY+qFp72?jQP}BLy=#nWEL))>cy%"
    "v4rRN;ha!+Nd?Krd1DME0v<&=<70X^^U4mL@6XP>fm(c3Y;Rr1QI9Fo)6cq_UsGpjbKmfk>y4ESPdl9iY8O#uy!bPs3FM%>F"
    "6XrCd2x#g4Nm$!$D>}f@|)m<ac=T4bbK{UXKe=-l>PG(uC=ViWPu~9A#}~}_XSkSbpVDlXc{Vnoemb|J4uD`sd679OoPEp@H"
    "nOqS)-*ay>+*Qc(|whJ)UQQKp>M_){tfplvBw`AE97yo)@gBF|2O9NL-?b4liYf|4KiejWL4HFrV!~Pde_zw=C4=#sR(zM4a"
    "XZnFR#-l;7{A{W)IEY=W80yy*llb{mOTvU|OaDE_(+Lo*+q(-WZSu1K!Bv9Rt*np+vK$1G#fu#?04ltIMMvSR-V2X{Y4vlfR"
    "sw1sDq&B(Y2!ra9{yu|-APw_U5XKCcAL<%|;%oc9$X{Oq*7bmH!5d=ob65evaNKT)yhiFq0Mw}{Ij68$v+6hz0hO*Zuy@paq"
    "<=JrJeL0M?SA<Bm*T;f2bD~H3tz$1KxVCu4(B(SyV{QcTT*4wvZDF+FDTNWwNwVCfMFA$G-l*WrrWY=L+C@sjw2g^)!D02me"
    "?A2jTc)j5WB;n)Xqc{kpq1rlsHq*UBc5f20=<oEiD^Zs;K6+Lex^FlFjpd0VOP$GADYT*a5zpoe57QKIwjXEP2$E~yBn_H#l"
    "J>#5Q~mC@TwC#tU}&AiV(jOL~we+B2&y>iuR)!KHwt!{^&y@&a#H{qgmlHgpAhu-2+E}v3DT#4leI~yrTVk5V0-&KeNl4F#J"
    "01u|;0iM#diITi>P3m)oQzZfbMX@Z7&6$!FN&?l>~BjRhqez+0I7gKVgOhzvSg-O$mYpUn?LHNn8WLRq$^a#k#y9i-S-oLAQ"
    "-`*em!S5?h30TF>iRF~gmhDRzK7HgP)ZDS#dtC$IJTt&bWF7u>Pi}kqpqqJBgNn{L^nFBD_4pNDmKr)#HyTa|lnt*M{4?p3<"
    "tBRv{>1yl|-*>?roF!#aA(I!b!~D}FxW7#rN^-AsW`4t2heqnv*CF=0^xiPhh7?{|9c0Wtz~Y^D1J3|yzLX)ecBOF5xO3efR"
    "W#csQ%E0?=2Lg1&yFqCw%lK(KPj%ubVaa>mXvwNf8Mx6kK3ftUBhY)T=;LmKPE8SsV~>e8B#69<p==n4^y5}M(THmt_{|;+4"
    "y~&P$p*6JM^Z$HQeqE;DD`~t8d{1CMGKG5~9ca@X5<djv3nGPNasa{bSBI#qL`i@n(BFC9Zb5Nv=F?{=JIRaE?BzcB1JA!jN"
    "gz_q%uW&@%)*J>17DG+js*W-n+*D4s3w)=JlNbb-Habd$ZJGm)_VmK1Jy;lFA7!?Y?o#gIcDv|KEks(?9ofG=U|+a2sTEFQN"
    "@eAp_b>g5+AIrh;QiZCPUjZj!0<f^I>IRVK$_Bq4$Mf|+3e@I3t2yoR2a`(c3KX5-brV2Qp!I2Hn2OOK6pj<tc7}wIz#g&4O"
    "?}T1|#S*M|?;#(0<8ng)=O&6jbPoX~@3#ff)24I$_-fm-cZOe;lK8iVWF`_-X=+h4LBeFJxX?|M{KEsAS}^HEXT-TtXbZ|3z"
    "A-j)`hPh^_~Y6Bt5!Bw*k+kt+^|xgXB1dKv_I;iwZruv@|30HLKJs!M{v)SOD?x{I|0GXXu!u0cNfVpa|t?Imsud2`f&0wzQ"
    "Ha*aN>!$WNEf)(I}Z`qlQEuiIWnYniQya^Pov`B)mhSk%LCbLhv^ZfQWM;5OFp(r~<uRAIrB4-N$f1QKR55{QFSB%xQe|E9N"
    "1nzo7o9EffGwGF)EJb22GnjIX?!Q(}9)iBy24d%{#7#wLI{IOn(OU&0ko&XaG!VX`co7gcmp9NerXzL`(Uu#nc7A_Ru?hEct"
    "#@AO|xN&1f|6Ikwv%9nPy)#SVANTCAGp^=dy(oBOYlzTYiJc-3-WDCCQL-^78AcMWLA7OBEimR9Mg?1?SY0oR$rl~3uxXOw)"
    "PR`OQ05{_%%+DD0kpku-Gg5JSNOx1jIN*u^9{2a(JWZi^B<xT(;VOUxUJt*767CVp0Fw_4wn@sX{BU@yi{DMyrArfoW<YA2`"
    "Fw{Ok3}PNu=A<R=02W-FhU+&_FDhoHu(+HFG9DMP0zdOB1BOS1au41ids?wj#?S{Xl|r7r4^E>-e5P9eF<}=@YTh(7eTw;c^"
    "$hlLT}I^w@9(p$ARN9bFbRS@fe@nha={Izu^o~4GPy(G4NaBiK74gOEdF-OI4&H7+0dqp$%{gkssn8wznhjz^5tb;U*oa0@J"
    "3ChfkGZ7?kyXVF7kxm6IKh_n$b+yh|I0OS=h#d&$1`6qa=;)$w=L)(18>KeH10u~82&Ez(RYWjg3|V<fEpK&K5w<}z)+PQ0H"
    "JvaV%2Oz_w6wR48czN0NJ(&mSkGtE$cSe=Q;Wx9HI$75fWc&XaQN?_~7w==zhS|PVmk`-__Q27>WHEiJu(l`Uf&X$4btM-`X"
    "NG^sL*G5jai%Mh9jm<A-BiUhcOUoSO7#D7q#K;GFBrW}Jh<109<I1%2{g`pLlQ3kJ`Jyi!AI4<!fPJ~3?<K}n6%v0P$__?9K"
    "ykr7Fe4jTGL9H}JoaChX7J|nROnHF0+tz#`?1^?BfotRh{z44g+FRj*tg<eiMJ(ooJ1y-*K)BX-z1qg3syhO3F3B1zJb4Hue"
    "K+xNLnn8T@~48n-7GdAPj2ht}!p8m9mDQpZ3e9d|LY1LsayAss^0+IvXX`hU25njbQ4;NXnviLQym|Acu$mbe7C<dXvOrMf)"
    "wR8)XWT1APs!5RV@`$_N=F&$0}{sn1h}hWvh!kV`l*;5H|X3-gx1P_v?DdiBblHAbegCQowBp`ey7JT<y*eDc)9D&a3PN5*="
    "V&r~nsA9)$o9U&m8yv;ZUU&}3jU_9H0cZ%VweFH3ThOwMiix`iMqZ)t}(BcMIO2Zhk?Ll7Et8pQQXx~!tHXl97Nxo)WdY>H?"
    "#{%Xz;s`lKV_m`UZ&#w`Kg;lBs@$>to-2V~UnO+^AEU9AS>Gp8`X)f$(C<lr5myHn3ddJHI4nX~#+=RAls^|^>KbDJlg9FDK"
    "4E)te$odZOqr=y^M?;B3$N$h9ZQMXFRpy-^Uz}&Z+T=M+&3(9Od!Hm@HjY6#3(Og@klM9zldU8ViTv=Ax2t<?Ut(nfB4UfM{"
    "{?h02?Yc&m8l%xXhr)#YI;c?Gq@KE69v=vc-Axeq!zza$8%Z(a$-&cZXEaE?-p5SQ7s#OTbD#BShv;b&HU_Qj&u3?79^ZiUZ"
    "-X&!MSgOz#G3<zEVR<{xBM8QQ85OLve{InKGTYUZeRb57`U$P#(@kec~KE8R9O_a4}zwNEF8#>4sN2+y9HXngwpBg?)Q9occ"
    "?BG;j^c1=<a#<%LL*feno&iSA-ESJrBR(#SUyN?^Jf+v-mctR3R+DtVL%D9hZ6ZYlwcpBKYF!aanKvx;;S!e<fAE=7|*4Si9"
    "aVGN}0;jtrJl6Yq);WXZE}?nC1j8OrbRD%cm1RREw3wc~u>*w~Ru;9aPr)P9ZfI5miEi`OmFq0wywc?zifm0=jo&h|a5{v`$"
    "b?u3cDi+7o@K*P)MzO5w9r~R?i_fj@F-sJ_e-R@b4F|n!tL~}w|@e8hK|dJAVB#(8%lSOimL%W?q2^HV5Wbe0Yqu88qfril>"
    ")ptjF)q&as&nMQ(Blj_Q&6-L=NyEDX0Jy%LcPhqO%LpW(%U}x;r!D`;px*slEH!Zptcc%PC!PyfN9CF@X~ge?9q#tTWmEY4-"
    "N3xYOMaCA_eLM=YxWK)TC=2Nc5jTQvK$kgZVsGmfUl3*6&Xd@l<ij)BKDbd6PIXo8o2<6#54YG>5&w{b3N@EWr}vmEJG?u{9"
    "-P~4{_+Zd1{1sTx+t+Xmk(C@;57_Qzq*@M_i;bMoe2vF!DT>J1@TUdyao*Isq-fLm_Jn|c&pw&Cf`D1SaWy%LwqO=K!{*-?5"
    "4B~^`K0dmj`s(!CKTyTUMXX}lwwHMhb;y4_1J4y!Dxh+|tDQ*HO6UC^m>=<jfD?(->|h<w^!nlq2Ebo`$jP@`uEQJIvUJglv"
    "(LdQ<!QvP`X-n;hr>)%74TilGZUtEIy#_@9U4nNaQY0Bh4xmWH5TF+y%|WeXN~yd8CkH)4Y@$GyVNDNaZL4O_k}ncw!E}Z#1"
    "gIFfn)EvC7P=KdOjkbQG{$JMYJ(pU=yNJX|_wow!R9fMUttDl4=xZ{<_B+0{mIBEUDjhR4bhW1v4mdBUbS>4io}=-@jea>0N"
    "O1^vJX6_+z4keSOK(fG|Wg9DdB1Ck(gy$Pi}BbY4y6tNG9WUii=f5LDov_6AAtS+oI*AicZpKi;S$uPYIH&woPG!fmM;;fg6"
    "^3iY^eFR}a8wji|y(wR=#fw}_2MD}s`N@a^Fj0pOoZ~Ub@YTu{7vqWyOSs~H~uXh%TmuhE0X$&g-eqhJzjg101&)0x;O3oNy"
    "N{IvM;^jR6hpw=2^jGRP<q=9(S<ianbFkGIFRmjis8hsJ4iYYVkmjlDYjES;d-QaXPXg+Q>%tL!>qoeXYa;EACjz;{fnc!vT"
    "m&5>SOoLc+<8$;wSrp)TbjRip}||P(Scg(jH@CHaRZ$eY{v>yKIr8>xe0)^4keo@8C)iV?jQSS$2Fj3)cM0M2bw>3j;b*D`q"
    "`m`c!L?1ud^WKgU5=sW1na`M|}~?Z8DNTY(0O#zR+)+Zdzwbqf@XcpKJf|5U@`{mvflD&^6cE`PK-MQXe#TGmQopH8wgr%|7"
    "Ik&p^OE=LL$D95f{B{aR<@0F`Cshtm^Y;gqA<A94z&VA&k38^S4d1mehaKXh-@4TH<jW5c@Ow>Z`0X9U5#ngG;j-HY^xl7aE"
    "(E8VJUg}9okS^EJES6t!E<j3y=eq7$qnI%$O9sNVlqBenz?z^B3<8_3aBQ;zA1ZWvsFUtHC%^K`c{u##CQPKYa9I4V8p*5@_"
    "?Il-2OxcKI2Iq7fqy(q+Hz?6-2wF__`gE{Z>6S`0(Kmn<h-vfa#wz>~i~5LQtfW%0jB^F)Cg;OuCR9A%?6(339A61G|NDOJJ"
    "L{%RnIIXP`Y{3g6DvuiIijh)Nj2Q2ZxOl;>rZWE1xMHh5JlHiS4j7)jBNrx5c+t>G;$^P+S0nYUEHB8p_sn?swn);TkDlQ_@"
    "q_T9Mq^|`W8n=^!QAnCNq^5i(S#|CBkN1aWP8JTcr@k@&Faz??`EOVK=&~D*4F717+9f|H3jtOMbUZ3d$EwdqSApBE9z|u9L"
    "<86W5i{xT-%^)E6pBuF+}J#E=)R>faJ#!X2{;379!b9OqoE!K988DiMS(ANzlo<_y)8Fp;eG7}f(g!K`6>)VmPkj(?y?6`&u"
    "d;OK<?jaqzmc-)sizsEgFCyW{aPotSJY90eq)#K|T0<B@<{!{AUn}}h1dp<!_K#NcU|2DoYeAamaK>&=?YITu&ck0G^RF|bL"
    "4x*;T<)&(s$fcpn{qFYdaO;oL+ajkwp9k;2c#>q}lU?!q8ryfI`L{RzDi~b(9IM1mVRKS~)xwOMLc`w<-kL(8CJjEp(^hKca"
    "02K8Aq2*_{NxH5e@9J6s2*7?Dr?aKa$nPk2z1Q-=dw@(kJD}=uQ=z&$UpwWzWV=RUvYGtx5qa7iFy1S?Y23T*u=?aotBDA7$"
    "6-s34s|Ji{A~3Y3zY?$yexM%UsA%CHX};5#lPdIz4Im0rT`M9WdUhas&^z92By^Gl4Ushd!g29Y9-4_GgP>gS(Qiu3C^e*1M"
    "lJyIfPLh(3VXva){a#$t%}aNctxWsj4x*^8hR<R1PVPjp3VSQy*7AXP;U>Pb>RL{l()x`TY?vnhx-*W;`ch0CH{{#>Bwy+Hy"
    "2=U(h)BiR+)aa|C1-TvFPpvs3oGR1t?tq?QGtM1pCB>%OXneazZNlYtB5%<sd3@q`FjHIsBM#=iDO*<<9zv>BB7v(_cNm`94"
    "mfxHp=$^z<-<6>jZJs}5PT5Alm&6_hB~YAO2gr^N<V3l*eKeq7Gm)d^>QnYLUfRn$ryYA+Sg}k?)wL7><}qt4@~>QUn{zFO)"
    "#-c)<;x|!8U(AmRhC1CJAYWgNrf>rb&(A#<Svs~E+t1-0=s_2lzz9p08M{PXb8EKz0jFlXWoa_;Zpe|x*mTrbwX0g(0apy8I"
    "S9LBdS>sH{RUvr{;}eTR6%dS|atvr*Zkrr}24Pp-1CQ#qtf)$;b{1_kN>2!LYui{%Y*a|1~x@=n7O|y9<D|jUz0?x>2rtA}B"
    "gguxAvR+jEMrZ_1mSAC-c_5*(~1zFoBLi@oArb@p4nua#Ca7RO@NN_{v)I?K+kz6tr%miv6YXdHoYzhb#K&L5KQX{pi6HC8-"
    "7!1maEAXHWTFKXd6Z&%Y~wZ}dvp)dheKhIbhvKc}D(u0qp$U3O}aPJ^52rsP07FEsxblL(-1Mp`QECDgmQ!xkWJ7$e$3*bKS"
    "z|%0>0WBqZrND5LH&&N*y%Y*}KuR3;!wDv1;l5>%+s-K!&K-UlV?0Xblc|qOTi##oFG2|E*C>lv{CmbmuoXnB8MkYkG!YP<v"
    "?jk=VHq(fGlEZIe8hqGzGfZ?HMs|#I~C()_15eU-^+Mz8b*O;6kKo*@n(GQ#g{8P^hD(gJw|IK7JaTabL%q(xPvtVKjLNsIk"
    "3}ocJiKs`k9j^99laep*mXcR7>Gk{xSV~FeKb?qZy;a;Ym4WBM>o5Qrw542kdb%s`cziVkz*X=y+RVW&t=$^x1uOlMYuv0~|"
    "NGfS~spFxNNT&8s8}p6!jYk5Da-^&TL-!6M{b`m_J(ZtN6&bP*`}G@30;HoYlHVL9_2t~k7S#_?-N+g`7~|62gK_~$5yP?6K"
    "6Dii1(jgYz-6im=G%6|%8L=rkn*3-g~YBJYerG<M(F*x6JUeFQ+v`{!nnJo?;jMoT}j712_Kz=uL*}!(y7pvb(;^82Ss-}2M"
    "al56HH$k(x0h}B3D9ySiZK+x;_x@gHwZkPmc0na|wR$l}_p`~T5JjG<uB)^oOmk*L4MRYgKgf2<-8D>FoZ&(s%^O7_gu^pdL"
    "V~8?b|&J6D_v80_Du%kZEAMHcoH_|JH35-O0Gz*bQp;kKgLdi7Y<RW3g_Isvwd={>C2VEA<o$%PSOA}*@1#-WWk#&QdHe9j<"
    ";Gz$_zZS<{6Gt^pmvAd<7(|Xv^v|dSPUq!2kT;5p*6`=(lYrzKD99H>E!*P`}Gk{5J8W^ZL+`epQyYxuH)Vj$V-sgbK{5I$s"
    "rSk=!9(By_dW01FtgvU}Ouajj&OGy!;a8S8wyM^9eq2opHyCkrCo0xS%+S|pJaVi^weC@a(xT-^!pV6hyf9m!E>CT?#^ibM|"
    "==cdx~Fsf*Z+j(Bg*z%MT<yJ*!<`m;0XOx5fEf0ZOs9DTiIs>1XVOyXUqDY&f5C+f8ne+Ab>9t~E&1VBKZT4zoB#<Z7W$%j3"
    "4KW3u8s|9(eweND=50=t0R0BW{$bU^{^O{{U}EU3e@x~Y#$1DJFcePLvd!vK03{@m;Rev60xU^6*90(c;|uLL*jI=R0g^%Ie"
    "PehV_@C6nXQ^Kc;f++8!yNX;J;S^#Bq;!QeCr_7^n^=)8cCnI547R!1U75`6!<ycHVNp`;@gt@AAH{}q8vxrxn!dNCin@_0$"
    "kNiWYdOhh6zO;AAAXT;%>$&GW)|bbsZJF(`KC#*&B)v@{xzv@ytY5aMisqVm{q*Kr~F0m({ar-lkp+!7woLlMw&A<R{Yf0Hc"
    "kY#-e!Q2=0*Y5f+R(=dmMwEJ$x`o4k6bExVXvu)|@L+c8Oz1&lmVUH4ch^;y6zftGh#XHY@+AN-4~U6GO6-9a`bKrFV?aitV"
    "KJqn=x%k$zZ<yZWD66(t~k}a<m2+Ej|27Uwd)L?Nv-0r^(2ND68sTIBqE5v<rE|#I>1~BPtYX#PJSyz{r3c#j`>S1Gc>0@Pa"
    "-6Us&?O%riq+{F9<dRn`eU&sE@V!`NN*wr9gD{!{IIsMUP}u%sN+8I?9B}S!FM5crSyVQB#r1)%!0k4lIh{mhS_+XH`#?hhL"
    "ESrt+c;L8Pi=ckT&(ZttFdyvF?jhaN#8QGIHAs>9a9Wx0Trp(_1ddIRkW}}2v3v_>n9u8U?JL;mD&}gUTE$cer}m+P_4!hK{"
    "w)OVF!^f2b6DMlt3YFg0JqcgS4L*D@~QsA_^ewIWw;@l_}6KwlpVUw;NZC)L&zdWtIaMG_Cv(8KBC@pogy^J{j?aC*V`4QAL"
    "6+gCJ#0N1V_@4Q{u_s8c1es?_e}E@wP{iKWx>4EiPi&WMT=b-Rr3YR8$DoF_Uxb;4F>dnz^|zaXkhW4ZUi2OFQT#euywd-2l"
    "lU?X{0f^?}?M)5K=eze3YM>MsDCCc&wmpVVoBxA@Nq;f(dydEoNFj8M_rNL1(y;~ApB_XcBFB}a}I0Dem%Qu`=OfvoQV?fZ<"
    "PWJRZub;#@eXQHZArI4041Zd6CR{jiQhqmdIh!U@;15qAHe;Re(q9_98?7xlML5Lcuvr|OJ0cWUuzQKN!;mVH(RhpFNmnbM$"
    "~O?C8S43>hkv5LH9nuTt=Z?8Tp`!o%YTkI4N|o^`6tKLPcS;Ki6H`nPD>$i@JM=)U#Z0&>iC_d6<E9;1~lGoiOlIeM(wikzc"
    "`Byh7bXb2l_3PHcZTi-4vgG;#!QV?$yrWo{Uu5Dng7vq|#J&gZa6r3VUA|9tq@p)_eL3$>kI%ZqD_bb`VqbBzyU?`<Y^8xZY"
    ";hk<4#)sFNbOZn8gQtczj_Nab<h6XJ^UtdLi1i)ns*ELA-H*)upA+n=m#Wp;2U>_qUmdk~S_d2{_FDdFJF<yK{=zKzS81-F{"
    "N6PpdtgB9xcA66dd`h^d`GIjV81GN9d0HUf0H!xUn>4F`0WS_cfv)p%8IGN)uk#?*(<!7`nu9|YvZ-L4{p-aSBI)pRmSx?>c"
    "{8ZjA)IiG(miDRkBFh%~jW63cXD2aww?2jQcO1>l5Hh9QJm-&#;b46~vLgW%>faW|7J>8rs+IaZ!Ri(IfTX#|<^U38z5c^{b"
    "<Ytx6IzTkbT2TRSz21C{N+Y<4a0|Ioh?x9-gzJ;>Rj0<jTu93o@y=%HQs&6DIP%%1qLqF(dQi;u^oCyDg|n1%E-l{e}Ki7#+"
    "g8a-6wtHr)5uA!u3?uhwbZ_R;h|OBFM||WDpFv1oWdU1!^Tj<q0KhQ0@1B_LhLMCSZ=%@cWRM{jl+?|6D*eq{=*62A<zc0F6"
    "|m)=mT-Lg$e%E`V}@v%G#SkUg`$AIa4FI_mw~rvu_x>0;atp_&t7HVuvOOcge-l!JOwP6_7c7-c%u$u-u;@^|`-LmRf5Wzz7"
    "u<1$8qBTYugVDzzP<d%J}tCu`vr7X)DZM83vXuuc5<-QqdQi>DE_ag-gMiQW9=If={75nO<byjn4Q^p%C4ZW44E)MFH$AM5`"
    "A0ZnX?%jpj4eW-HI^^xx>Cb$Vsfoif_d-cBp8Y&F7{IZryqVIs`McHfNQL>gahfCiLgjvBMqc3(337?#4r!G$Er=MpBH&+0O"
    "3?4}<ake60HI`?1km~k#()c4)sZQ&GWu->IywnpNAhj%IoUZ3he}wz;kyR4^&C=1)*H-8aZhj8aR$};X<~B<{0239qZ@Ura*"
    "|<!GVWMPnL48Z!K6IY8+Q8D(7!*>+xekVDf!-JV^Qwn&cueVCd<c7khc74LS)7yCSw#xwC5Ar4atm+ISM{wo^|~!%xW~tLXb"
    "(GwJh;0vuL)1*b%c4te>i`B!pr>Hqx+zY$CFt49g8!_yVq-Hce9!Mr>Uya2Y|iF`L}I3h>EUCYn2&CePrmuF%bB<@sSkRO_c"
    "8gta*SWtp@r)h7#7SNcgYKX^-|oMQx2L68d@|6tL@wp_hdJ}RK#zW6Xr=&H6-p7rB7;<PbnMxYrL6u^}m@W!-kBdWso1|?Ln"
    "xBSjvz%wF|cw;3rh^dirg-b)@7(Z#Wjnj4~x7$p^d{0oT2oJ83DqzOh`K5;SQFY>2<$RBGANZ#U82PI#kt^Sy-m;WkrD`&!$"
    "w($$A5%Oi`P};FyisHMl~8T~T6^qe2*mu2BG^m6j+QqGDQ~M{Po5{Z_dC3dL4=)Dx;I?QlgT-hJ8<rO>?2CtmK!c0|KqN9$A"
    "2Xv*^k^4#H?fFk^#EE{NHtnM%-1%%gz&GA|^M;=Dec?svU@(ycwUs0W`em{bwbLQjCCXaFYPAmG5|$$_r{n&~c#L_Sdu(W9j"
    "%V(ytV2HH%ex3adzc*{VjiD~pElgH@VbJG3Wld{}}9btgDsF3#%jYC>LkqIpryB)zhbUbU}3@OayuLtWz1V*#f0x=ch>1q?8"
    "`hKU5BbfE@=nRSRpom0|q0U-c++}2sj7k@3y>&O*9Aw!)=b*z-$krbP2uw?=CVv#cuTv4fX9=~>^I<NqEua(o|lq7$5sgeS3"
    "tkZ<}>2q?QT>v#Y#r>C|U-+N9W3{-B(ZR7$;(AYLyVt}jdyz!JB+JJ@Xk2!!2V+__NiSgA0~eadjAsRTm}h%(J!aW!UMJNCW"
    "CS%lDLq>kFbL}aoT{PG4io;IL#H+L`azcT$qjwz-L{Mhq<K&ZMHLvYXi|_KjY5@7#T&~X#zq=RDggG4DiS5~kauFM4c<JDNq"
    "K(IZr|U(19unYBazK$({cvtq~U(ZfXGSrqV|OQM{#!lD&6T7(Aj7n@>7#E-b2ejRo#7DD7G^Ws|RT`@!QEavFSC$SOd(*f$7"
    "ZlE}^z<pWa)%lO1%=AT0qCr4z#l#`nOtl0LKm%znu1NZeEH+t`u-?xxWve?$%+%M)Z*NBbr&Rb+7Ce??)8Rqb1{?r=hqNfR>"
    "~1JPjvwDJY;f)6&W)fogVz}E&d<5nu~QI>)V#vczby&eW+>+gX7y+ThW%4F02^0D!d8xJFv?47b{PA)hvQFZjG&Jh#)^jf6n"
    "KMu$aK^ICAjYaPtMlap*vH0^ueSz1B1Mh#kZ(k;}M2!tdfT0cxaKM^TZp+^y6C45bHwxJkY(A-Fr;2ZOZ<GuISu#dhSm^ImR"
    "EJA8s#kPVARFJM-wkC;QQmcrrO)o>sOP~FUlbpSg0jD+Tz0DU-LT>^q9OWE9kLnRwD0*VHAr!iL_7Z%tG!4;e!+T$4EBNg7S"
    "WL8+o=<{x*SOa{CB+FLtwT1Nvtm8ZxLCZ83JO3sX}P@NUr@Kh<@cB$j5)wg{;Lg0eJXRJ<)MqQ^N(NxdF%v#bHj@7cD3qZPB"
    "04?oerEi9#KZs}sC)uIrgFwZwJ-g-pUzF9JBMceyU%=%;w;0AtI^0y*(*h;)NDUDsAk-{-U!Q%8zy_;PF)z9iSbmRhxE^h!H"
    "@dWmXlVA-mD&-zSbh|u}>6#Ji&L9Bia%~+)}=$=(9>|S6W`k$D0$@;B<^5=>Y4_23yvLJs+CU8LXJ~u~@rIRWWfX7s~n*B&T"
    "J|ECQ#DD$=<zRd2Z7+?HKjXo+enze-5Pf$!p^$t%Cre0K_53><AY3SST10Tq-W|`62>wp6$(lEC6lGn0#ePv@A`L;E{-C?oD"
    "m$@zur%6x=0o~1o}kYBdA>)Fy9*A@(Vi4cI2C9(`!t$BlIvk8nPu7TiingO5=FB)uc9j7bq(4|$LwSE-e&%HwlIS-U2}G%)J"
    "WY^wcJScljg<WLkmPEJWwgW*Cx_+isZfRPMR1g@kQ{c9bp)eH~F}G;N<fx{s0v~>1Rg(CJrtUw`X_1y8TK8!mv*GbuhetYK2"
    "2sOE6DBpEqP!iIXO=Fk9|ERRb-6lxZ#ta7LLcj8kHx(*=0_K}Zg*Rb}%wrzdE@rUp_g3fA=#rZ#Y<HG)a4=66B6ZKkw)F5#q"
    "VsYCZV$cq2%tjg0N4dUMsNUhi(AfZXk`<x0<N5#j6C4q$J{Y*A%@fZExFQpSZi<4P`ejqu}HGL++I8AC1?XXp7Mr9lTuRizB"
    "Gq6&L1F^Sknkq+;OqY|^Rk|IzK6hylLz`CbJG=&nwS&7{CAjI!)fIndd{+Ext_I03QJVAzZHKaXPpClgXEp+NC7}e&^Nz_hk"
    "c5KhYh`i%k=3t0xY*tMNw^rqUZ4+KT0IYd^LGlAAx{E`QNjCz?**|?Fq`TezHhb{x8ecV+szepn8yaJ>5Im9+0bM&Jq$Xk>#"
    "W>pw9<4CKJKJn=&KW-7PyI1OW>K~poV!~AI1Aj1ogKxUCZUaTIg3SL3xf~3FH(YJ<liYuvh#jcqB3Q-x^w(O7oAxt_ToP+cD"
    "$ay0pyW{Vnx(^loA*)%*2f5)=G2K5D3A28=Nr<kvxaoUN}<=_>*6UarHpS4^*A%n3--M6Dw<tIjDQZ<UGMlkB@2q-Tx?E@3s"
    "KnG8yzmaNMPxv?$krRO<?A8<jn&Hq9hoA47Fb!>lZq&!=(HOsC2MrhDk@hFJ2c<i*2{Av(wASGJ>KHyGnfUVr5SS5hr9$lay"
    "TSW14q};x^_QsMwlu7P<AhGmUG%9W>SC`-;s>ZaVp@O;Y@G>jbuLj~jJsLKt(PvVif&~~S;wMqrzjdkg+fDW``eEMcJOGLdw"
    "A9=rnPDp%q?Ym@Tch+Xwee<7Q2_hrB}evUcmz!vm-XjrL$S6eY$c*p>MPuDmaa$}gaUyKP3SMj8wn~>9h_)kJfp~!amHB@ob"
    "8H_xb0KZWXrHhlEVNqr0BlkM<ubm8)ks?I~KUH-M=qz7csZLcdoV#00EX)Yp|znTon$w!vKUotqO^`eXV%!T^Lr;7`|)2PKF"
    "dkUmP5K7-_aZ31LowLBCMI<sN)&{BJYLIE-%IpI02KZW$KRnO6_7Ou8t^w$}uh>wFKyqQ>C+r%jil%i$*ts<(&3pq#FLrMgb"
    "@s;J%fJFQjG0g;ft6AX%kj@~=iVntC*Iv7rrCIAmHC*Op}M1D;ROy<RIA|itB7kqoGq4Bz>3m$*!s}?xoVGcrvOp1~|#|vkP"
    "n#z}+pSsYTl!&UK#C(y%z%{x0^M0DhF_!dQ<DuiLtBC)u8HTVmlgq-d0Atva)5wmyrGos2`6F<247@V~64s>%xz;k<^E2$U5"
    "F;rBZ?1-dFU?(^{2?Bp6kEXEr<J{U6!1cUwImp1wz*cm*aMD^oE4h;sp6B(3*Mh?hvRuD(+3@H9m9J1&_4~0c|qb?c1gs9dO"
    "*b+L}y_EW61z-H^|G<EU~F83<AFJ$ucInm@VO&XlW{DtHpVpDNG~D_b1$S0yJEh$e$!1G`NCr{?TC142=r1ABC>A^BH5vXB^"
    "=v(p{TW_(UdFM4!t!A&i18`90ChhG9*<0Q~}}tL!Y^Y5m&kSHf2F9`oc0%z{@)oaenKnGDjjC$C;a%Sn*}lc<Jy%B@`y^!J+"
    "ht%9#b$NiUIRC4=V^7+;H!DWjtM6@Ol0)z*uqNT5w+-tL*qH*G>)Y99K*iw;|)WXrTvjBfDEw00t*_1Bqoj`4`FcZ<^UgbQY"
    "VpSO0j>!c1D@-YIANJS}cx(@5A+#XOXF2z{bT=NC^A@39cn;Q1XAx&PLOZ;?zt~2c-6LF#Bg=`e)CPz%ujC%|w?;S}R)%97G"
    "|kS&KI6z{CA-z*^_x_?BDH=e;m_bf#)Ry4d?<B{Z)?}rSvnv&H3o2=78J0Zl+b}{hy&gZ^ZpGB1N%-y`rTbj<YX_E`_n5M3B"
    "N7QU3r<f;o7%<9b;|dQ1$Lo@4D>UfMlk=Gkzi6{}n(4U9H;_ds7%hG5;Gp7rAVrE~K$^9p!5Ms7N{}JMk{zWYU2&4+uX7lt*"
    "iq=M?5I7p;o<2p}jYy}I5nzUUGqj-8(x>%3N=&71dZ!=n~+QHD~Hy*}v`^v0YzDj=<)2B&<KKM8s1)yTgcT8GLN4C&)Ib!56"
    "TD?il97hM;Ru?aON9x7lM(p>Z>`eE$STEke%T%5Phy=Z3$f*&RPB`mU&KsG+umCp`sbEf<&JZMdRz{`%@+8bFL%T?qMt|>6f"
    "4Hd}@l}Njg_<Oa}X${-exEvjOpa;u7F^#C@F^T~6nxCR=^Y}wFhs=U~-9zf>lKiA~v!XzQpVC|Oi{_&Kk$HjM(6Frc74g`RW"
    "kHGzJ90rEPLY}OiJ%9h(6{(W1(4Mh`sIq%K4z7JTLXh#i?A@K-v~_Mi|Ohs62|*9<$%NM<*jE*xB$rGBpTNBc!!vk7Pj}F2O"
    "Dy(V~aK!r-D6`U<gz~jSTXBAaszH>>TVgYrO8aqxB0yIlC(52scFlK~DC7gsdfcgLsELPc+zj7QSd&1#pgewFnvP{OYRPI8{"
    "(;TAO>(pRcTK$5F2H<cLr!rm!CtS*377<Y`*aplI(sOw@VI*T4W(R0so6J+~u>CoKM8&kLW4H8|>*O^kI#Ez=a;QObhPx>^4"
    "QPCyHMVYB~U=?72oRa3u$GpDQ1D!4H6!T%K`nr=S3U(%6)P;^<$A$Vj<kpj||{%x26U^ShBUpT{l0l!7Ue2YLDY5;VEgZ0<("
    "hVB~h*7&ab#e{PDlY+6YO8q$VcsLX(?ho2FF@h*auWqZ@SKm%wG$X|*0jU#%f9Ib~Ljw@fc}J+1#6I8ahnksV;@T|YFD@>(e"
    "jHwhC;NJiFcqAHLF?nyaoE^s{N;g>9?mt3iZ&rTX3peddxHCUkoO+R-rqQ6Vt{jrPy=?NDBghn8>SW#d+mFN-_-Bd8AE4zPH"
    "b+#NWh^p)?%bmWJ;R7E0Xb%I$w?(``mp<CLk^^2r2FoN=ToT^1qa>*8E>oVUw0ms~`~AgCq+y7h9{u6v8kTO&Ud<t=v`&=FG"
    "TpfZEeT6^c&`SOq4C8bQ;b(~%&a&<o7Cfq;oFRg#^`Yf<aOZO=8GUNz1n6H^3OLG0ctbQwm9eWq(a56mv|DPm!<OK?=|J0%H"
    "DA4$Oa21bpe3HW)9Gd~b?qGXw<9FIA5GPyx1*dPVU4*4f7D)Io-4hYV(h_x4mmH-%bbF9XGsMXcPOCb-+3ZYNtT0xp#*2~?J"
    "T09Dm0`Dw`q}7Yua`T|JqU{ONi(Z8BGm1suMi(0@X$G!10xqN>z=3c`JqBGcy^*D0kzaVY^1tg@yMDHls6^2xPFVAJv(UB5l"
    "Y0BI=N3djM*pZ=#u|5kE`)~mGJdZ@p>iw!mShLi)yX_MYa7Ftd8z%<!guK1;XlgeiiEu@A*QWor_@NN8DBQX@M&M8z7;h>oU"
    "tD3{hDFs%>NF90K(%2sxm31e1yiY4&}fk7+U3BeY(}=B8)+m%}MHgcyz{@@r?~&so#+VmTG;Sr~t6zfIrI}R<JoI1d_2)dWi"
    "KHLqEyv{yg2yNCp+qT!-=e`O;%PVn0(exo|b*B8pAlb`%v0$|G?0PA1U8{gU$|+m1584g88s8&@d7|AhI5A6<z~5L5`92tru"
    "v^?!mlF4*O1eKxt6t{2BMrc?l7tACI<7RnL4t2s7k&)Ie`ym+p6@&p7pt=dZ`DZ$)+xv0J(lE;>*Za5yd1Afv9m;wfWTj2)z"
    "1#|cZJ8d*yZxy5uXNmCzhSX)b+u2S-2$J!k96r{da(fsOin)GQ$5l;kt|OpjAt&6#xT>tMVEYfT)5npX!@6W8O1+Uzvx4e+k"
    "LXe!G6lxgx3K{x@D|Yfxu^|#<L}D)t9RL59y`fo1JsJxMbN5`iqnQ}A*JF9-x4WM-F|J8)|+bL=-Nvt0KDJO$*N#b%iopui3"
    "4_RUd6D$g(Lo_`m&J|#~u}T1k|F@dSTl_V;1EzPZS{umcXczGhHGr6*!eig@W5athd#`USt?Q^s>aP$M1ha)CR)5&3T%<LjZ"
    "$x$k8PmIm346w_2M8)9IK~g^ZlJ8#vH1)7w~4bq;m^1Y_Cho6D!js@?>1&e-wv$gyWRpTz`L#f!okV@!*0iK4|B8J)Vj#=<I"
    "jBl@52vur;dc=et?Sz3z50(6)7-&5g|!yK$3aWnpshgklEL09L!3VDKJO+>w&vH1a-qe=MD&I!Zx3D`137j=wbuHTn=)Aj@("
    "FvAij;LPlH?QDd7`EB8B`=&`Y3^2YV(0Gcw;GWNZU_bF}=|&LVKaO?C_?rK3|F-@#h`2SHDdll%MhZDTpGgBHU=`r(UQf`OP"
    "`63DF=&_Z)Gv8EySW-KQdL;DIkgk#HSP#mjZD=Ww*RwyK5oZ2i8&TP;j&konc8$mosV~zpmo<t_Hix?r4dHK*fRs4TLd633r"
    "s^6Xjn%>CAtf=QQ_XB0@F(!+ct#UJ;Eoi^uX!S<PEV1qP<Zts&WYzxgnWVaDj>^Zya83Jv;%qZU3FROWuJe=Jrt~2Tpi`6Ep"
    "k<E1<FtcVzOV6H)5HG*99>4jqdow|#yOV75<^u`j)uLP|B@^_s^_*BL}c`@g_vkq8$O4d`3l(DtrV=c{=wLdUrKfI$c&V@Ce"
    "NeJb>1P5vK>CmD`kX1<pzxPcHDv*I6Q63}cg*UdRIK1e(T3$b!ce<zj>D7r=#Tx!8^P)H5@!}+C(lsaEv-eNs6Mkz^9YKW~_"
    "(%FwplsmOdz8!$&bF_EQi<UHDZ2KG<hSk`v!m?yrX96ho2)i!nTo(wUU##Aql#rZtA3SQ|w|<HobFUGgJLxPatLIq_m&90-z"
    "<{Z&_t@E_ttn}6NX>pbT`eHlMz+k#>CUfazo8vOYY+O2LRF%?_b`@^-zeHlr`hGa+iDx7eIQ=7JeOp6l>$#ueX;r_0}MY==G"
    "4XsY?D-?gz0;PAHyg8(njq;NEi>IOH)-R#s59Y``-hdSZvMTWfoV+W5CdM8VKUu=xBesc~d59cD;fn`mMn*IBt+uUf>eQT%$"
    "d(naK6X=p;W*6CU2=@*}lZ8X*$RNR+i$CYh`iN?cE+8zogv;w>?qjQz~PzaaB;I?celo0+9Yfxzqk@pM&DZE(#t!5!M-E-hN"
    "z-L<$DhXTdjJ-AzOcWH~aNYUW#?!g^Gam}UQzt(-qTh^L0d-mQlIcE}eZNr{Il&n;&rIF>wfgO+-Q1_!7y~W2F@<VV+w+t#c"
    "C+Rg@Q*aVmaR^wB`UWg=&!^oW<VRfoBk)zjS+2#CQJ~lSpg02y%3K3t#g_%<B-2B)OjOT>q10_{zBr~vG~4`Tr?xrwh%|7+)"
    "9FHM>+dSN94~`Y*l%XkhDC)dLQvK`l?%doTPI`>$Pk@$|8)<?X#br-2MXQAVRw*>il;)Kd0~w?wX6E~OhMpmvE?{QtpJecho"
    "pO<Z|+AHUy&P4j=SO`v&ELjJ*_1v)7^`Zm^-gcAEEC|U&S1+0etflW#T#L8_P&`0WuGY4No!7C~p0xVl5tVD4pJ)2gIVUU}g"
    "U4xsE7AUKVj~x|<UU2~?b3_Q+(G(s-Kjo9nf)+dH_LB1gk}j<qy&_|LzNZ9l;e7K$&y&7|{f8_6q{pj=1~3}}cWQm9S9A6aV"
    "Kz=t8SSGFSMM~GI61P6VyJ-YTR=iGZLn-6fqhS=53KT5eWjW!#^+Q1I)GNnMM2(+#TB=ja<PK;)fBs>yd&j9nkGZ-h-$@3(n"
    "s4%ib`eLT01BhRBIu^x;x6}DBh6N1BCA~QpM+&ovlpNeF-gKsHSCPE_L<^RYG*)kb(09ae3^T?q!xg>RZr~j_4EG^b%A24{%"
    "5h|02B2467>}ARSGt<$TQz?CB+EQWUn=rFpnNb1KVuxQw%oN-lA!M@?B(f5PS(e~$=UGiHOo|-gQkXVzoODOD%Vz<bXD_3e6"
    "sQPkpQiH3Y_YLXcTq;9ets8$@;lEe8<DpQAeTVoy|G_$u%cbGOlCLUV1|Nj@#jS;pm`{q0z9CnW6aB=bZy<i%jD7KD#EguA2"
    "ow*LU~YCL8`Y%ATi6*ZT8>(-Bc`-6f?9kXdBnIFbJyh3R*8NV?!#zmtvURTQa8T+MA>bT6+{po-yCz7n!=a$DfjSo!w`jY%9"
    "wq`X7u4+&j^{Rhj0Onk()#=W~Q)G+kSK!)C2bo|axo?Y}T{ellEz=rUja&D|*3CCa9<TkH9W7aJH!V772ILMh9rO=_z?-Q;d"
    "<PK2KgP6ygm#O^aZCn6yw<1WuB}*sL2SG{W=$_F;^#8zBC{;oFQ7=maosf;nmAAqUjZ%IT{)xZs>QXg-a%B?bIF#?oC+jo7m"
    "pN}$>&@ptKFA#Iv9p!;l~X%hifDB}4DP8ndu73<{~Uq)aK?jQ2lj1&Ig-T=LP1vmhu3~n(&Ltt<2+&k@C%-Zfh+%S|6J=y*@"
    "TCbe*LC|t++oNiFj(@I5}aVAY?V3!*(}}zBNGEi~&+D&ZCD<rSm<;%dR^<SL~McPs`&yrQ0@Znfk-bh&Q>xI@5$`>RweXvr("
    "9Gl@dVXij%(0g6J%gA}KupYVm}F3iV2a6r6r9tc>U>YRx<pp+PG&U$w)TtF6yl<hT5DjhhWqnC=}zIf&w%3_SE*;6ZYs<Vio"
    "5;27mg*Wv{w7^R_BvH7z5AOI{a=I|QM?I61x7W|ROr6Ddm_YE7)-a<F($5*)1|2GSJ=nK^LpWld)Rb!7H!|l^j`$@|?)e?J("
    "r?63i%#TDrmTW6{=q{}8QPx#tkD0+^U#vhN`J{NxW;C-6uzrKM>J|H4Mfs%fnLcy=n^BK2SG$L3o`5lYKw&t{#TNeKM-mX?l"
    "wyi8ol^0<#phIin?L)9I8Ifz@8QFe*us99xj+3Zq>43iwcM`<bfbn1t3ByCy^H@TfQDs(Xsywhh=n&DZ#(`RJ%tf9+BV2)LJ"
    "_rL2+XUuImgse+Xbt!Ekv3*U<Ph06>;6*;N+-+O9(@Lj&|9;lm<xO0(_!bJSgLYmCH=QGyb3)F>Mt51J9vD+rDQ$lGtik&Q?"
    "Ay@IwSPDl7>evO*8hc&85%ICT}r3BCSbbF`2W9dVJijDCT_Sdn!Vs1FCe&XJ?{q@xKoAO^$tnzzz<VA)9%m$HFP`uaM_NV{*"
    "^OPto3d;lbvmKe83jLJo6IH`6#Ugab(k|CswA^Ai%%HM4i4G3~f3n>5`1^$CMmZxw38Y1J5`JkB%`RCY?;h%ZEJ=fp9Pq2mu"
    "Ijb*vgi+PUw^NspS<Kw)H*qg3E^~398FJjgdpN0n3z6x=bmpquG;78OOYQS0Wh8B$vd(vE_>exf#UAcST)$MJ_AI!^->fLJ-"
    "z?X>t*M&%EPV>=meE&jAy@U7Y^UFRP7MKlOACDM3IhL!2ihFfzG=~|z~dt8F{$XY9TbyhOiIj~&&c54+@A~p-k^-AGS_yxu}"
    "`IdVR(<(nL7=kh*iinuH;)fFcS5o_tQ|XQ8Ar(QpcW;bGG!CTuDxbUgpNLj^v0bG(VjkwO>hEB+PUc&nYz!ZM=Yj8tmtu$4U"
    "9NVZt-nv66$wY8kQdr~@gwWL8-$;9um7oR_qAnVHd^ui_cXaQ(i7aEx3F_%_^k1;#S&Im?|&cJEmyTY3*g3Sednh^zQF;LG1"
    "b%SE={R2(}DF(EmC8`TD4d~Njpqprzzu+c5U?nc@3r7|-$8xh4sLG*^xnN))dAxi0P{;Ld7{3ioIzUqz~3J(9ZAyku@dwaCn"
    "Dul*K%7h3{?GLLRd+#mt^0=;LlKKG#DZ^A)54ultY4VgxXp`MCR4A<9#SD9e#m9bsGXu)=U|XiaD`q8-Ff*Bu(^Fzdm>Uedd"
    "^NSAK3>V?QYZx=C-&JsVc7x?-gX!)#SFBe{a}bge~)d`i*99MjWi$wtEw)<!?1Hs;4%<e{)+CUM^gizGEGHZm44w2(-U)Vo("
    "W=$yP5<(x6%Ns7Yr-3Bu=Et7=Ff(wN};V`IWio06OSY@d1ZOli&;t7&>&T1@`?Bn6qL|*G!2*g7;sn>?nEa6gSvgA}NYBU!&"
    "*M7yy_E_9{*>^1%2aF$CElD;z6CxGDy*^KWXB%J43LM5`1Q0IO#E-Crxj%&y}P=qB)Qj<$~`(B`A0#%VaP4?Y)cms7pBlp}s"
    "p{ApO5Xa`zahG%KgFuljtO(uFHJ$9`5R!o;OK1S29FkitkT&5tr`VjJmqgquk>eg*7=+zSY$rdZ)2W~Z8RVWoC@z*}4=K$i!"
    "p-GGdY5_WI%!nEag+C;6oR9A|%!$+T;IEor>pk+QT>|#CEIu%aq*s#)%%)Drwbyoi>9iKuPk6=CJs~SruVt6mOs7f<@C?rcC"
    "B#4#k6`C>GQji56Gw3zp8su@>QNmR4N5?2g6L{0Aq+&f)KOU?-+$ca(fGh?3;x9*!%&ifFMzR7lAhOLFd#Z~y<NQKeHCl)K^"
    "cS@TBEX^JeTeC)}01l7VABJ)bBF!<Fm6+rP^?8_F`axYUzW|u9VFqT44=)k-F0-aH>Fr3TBF6tI?)6xBI=b-^@gD7N*kGdgy"
    "cUM-Z-Xra)kf^IyWA{61`ZA3mbc*-v@uUG2a7VO4t<sl)WCWbPimp<h?ko~zH$jPgjp_ak}E<I@e9p(gisR3Z6A_rI~LLYn>"
    "vVob>Qi>%QsvWqSFP6G=b2h1uURWITQ4e#oa5yTf&|5HEAUJI>{LP3tjp)?hGc;{ANSqtFx!BPTJu)*Wd6y+JbQiymqf5DhZ"
    ";*6v<B|i#*S-O8)kt2fRCjxdph39c;LMO=r^dFzSu{NZsT;M`y9{MIGP-_=ifSmpV>YvZXUya-Ngt>9D1_<Lvz;4lot6DDF#"
    "d%Y_$#Da$<X2wovbSGR01EcpNJT5EyC@4{G&k%-BpxHs11>QHB!Dux<BZ@nTLa-`LI(IFO=`TwG-96CzdlBO6+m(+oi6q@Js"
    "(I`ENjcx<X_=8bf~~@iA?;C{5>&q&t?%$Cm0Z4c;T7)_@eNppU0|Wq9}Jo*RMR+|KDD4JNjTK^^22Bw)|SjgHrU)VueWQoj!"
    "a)(iurtl9+bbS0%v1$I?WXW3g!ZBzlN)i5e01#S!xgbmWCFajgSQpRp1_Pi4z6nU_#pOdZzvaHIHhjkjG3vK+HG(J1oiw^^~"
    "APrLw7s_)8NOpOO15yp}#QHopCbOvcU9+>=fEw&#(DqJW5!|fnXQT-Iwk6O^vT$QgDw10&7>nv)6dXtqh<gd%{z{Z_-feTzk"
    "eAGp!UP<G@RJ-TqSn<lFj>i-{a%&>{!q@S6>f(Iz-`UBACS{gBx*_@cV)Ji{g3O-+-$^SP1pubE)Nn%MBLB(Sq6u#5JRP(ys"
    ">%!JLyknd+JODBn7vSXQ3}^unO9SmQzdbnjArCsxj3~2rfQ2dk7|X{{M{It;03zyhvs(Q`K(>Kk8lcr8z;iRgrY+fF_|E>W|"
    "ij1kH1@&v}Rk5U!926DaWKTwn@j$zG4f)(C)bBeU&akolD+5cWhSP93Yaww)~obV1Gd9X%xbCW9-Z+5M?Y})}gl)7SYbpPqv"
    "XWfMQijW_E{MD6{Nr#{=-@sK5X}3ElXpp-Or&#MLa6LH`_)&)^w-{@|j2wJyop(=;v1?#wQ>tV0;QGPquJ%xPhr)RR{9vI8l"
    "!Z6e5RtptKCs}50s<<9Np*0}fOf9nFpfca$SKqv7W;a4EY{ilB6G$pu(?pThOj=jb7W*8k&C$+eQL~vI%^ElobN=H+6_@%|`"
    "lR1pT@Uq0_#9iNs*_@XKkUbm+esYleJlwwaf@|9}C<zsvQ0z@>O?K;evNIa;6?oe~*`{c87W0?;wuLPWRp*-Poht{9#-C_^e"
    "uOL-c;V#ILI<FywN?rOHdqapF+0zAiLQnS0kc<ArIm;t@$|UvR(dbOhgug?)hmTe0{~6Ij+bDIjh9xa>~6#xMVswrDkc0Dk("
    "ukPk%s0zCUlSbx(VpTPz#`utYGY_=rV^RAWsZ2@be0GMa<tB^x#_4{{|r>$xez|G1w5ymodI*8yW>ENipIlHS=`!#~~syci0"
    "ugN}cf8enx%>6{q-Jk($2~M29=r8N%D>*fUXTBe(BS<-eku5mr=3{<n0ynZiOSCd-+esNoSw-pn(e{=UfS_FkD(`<DgF=new"
    "qmpUnq>aBapOR1z~&TaRnnT~)qmt!m03G7p)&6x&aFE0AxgK3{{U4!ue5~BECbQ~K!<6}U9f539pwgWDk_aTFr@s>!i1o9B("
    "*;I&Nz~{iSJA~@$-9ca5<!3d1eCfNPs1bWXYu4$8We?Z7$21z4I2T3k02ebsyKH{RBiQS;7{oS$Yz{-G;FHLhQMzUR8;9B%b"
    "i4k@3q-gr2z^(P9YkJwF~f<C#J}aJ@sd5@*Z8cj$x4dJsQYpFCb7%~#MM6{lEV<z6z|Y8nWnF8?;5sCgHi@f9TwM+`9_C#$H"
    "V=SdwW&M9S1zFVCzq9e6y%MfY<;zRw-5e5w=KPa#0iU06NPhTa9Eugpr=1|Ky7i=ub_^(t3&!falY0X2W<xPsWerA6nfHZ-k"
    "n!Y=}MEpOqsiu@8N=zgs!u<U80^t&ZRWRlfORQA`na?2$NlM19~DyW;7BpYFcy!V8Fg&{$d2sMypmd1SwcO!0Y@`OW{Oo1`g"
    "nBX2pZv;RE{m=pdfMolOkDPCCu8&o7KWMY27OIP@Qj0ldW(Hi;N)%`I&xfbFBI?IdWt@D+Ar!BLtb$8L=PxW0kk<E?BnTq02"
    "aD{wr(1_mKwA6a^^iO{}-T7k-zqa-)Ggd?lr%iKN6IKj5@7dZ(qG@OV&jzm`seiC!r)|sUbb8jjCYj7euT^z;;#Oy$BIdnKp"
    "8)Yn$mQP(IT^4Wht{H}d(FP!RKFG0H?Dx$d;+$P5b=@6LX4RO)-|cOd!t{}#yWX2No0<xT-IHX0m1PC0wIUQ$|HqYfz$T|@$"
    "9qwd$!wanzs~WJ=06lue|r4onKr;NKe7a>lrA&*``qI)%EglksxGai0a>qnUVVt7f0?hcIl+g;DR*?a1)%SPnFnFK-*a2h^j"
    "(1u1;EFj0d?ZMzXu}2O=aC+6gE)=?~rQ{o$y(-W#y-KgXaBw)cl$CbV*!PsA7d4CLSrTR0_``FfWXpGR^%?fpdaqZx8XJ6)r"
    "h^N>#~8>U@>L^aJ2_C)~PWaF)<B!uPl9)T_i_Nr1>)gi14#-oN{W!AV6?hOND2G^MCKW^=%fhV;Mrv}?Ju0HAMpHH}L;7seA"
    "2fxcUz_1HqCzS0Gp*hq86j7~mKO+ABZ7nLHPGJC+Ba5N6jSs_Cethqfm6)~0lRYD+bYvwhhz#x_<t_$H7|0bSnl3+^wtP>IN"
    "Q}Y=c47~M1#d3~&c*0>w}zD#seyfmS-C#Eufqb{5WkG53DlC7A~?$<keFV$p_f~?4g*scZW)mKTp~$a*1T*Na9!HTX5pbf?`"
    "-@9$*a@f@Znz2^#$6X%f$oU0)8tCZ_If~=s>@o+ko_7sAOfv=Yn@%{3@<69MFB))KC>$MSuQvteI-O4IkqxERJ{6lY0lM9&="
    "{W8J@2nprnZ4q7b&qWBko<>it&Buigh|lJ4!Xs-|9!$ZIW|{72(uVi5!>I=;l`)f>@|s@?ov{k4`>V5{N>XC($tM3bJ0G>qQ"
    "%(m(yb3Hgy_5;>B7%!CPG-Rb((Js@}(T)PaxeIB4sVN>&m8&Kms+|1+uYM!oVCxej-f5NtXi17V)b`EOQR4M5dBS8z2qVk>B"
    "^#RY-)%n?K{QEbZfBD;L_QRSB{8BVcIDnM|tVfm^NbwQeehaL?(sJPWlh5D3b|?>xhA|t}B0&TtKB`rrixIKT&EMV_M@~N;W"
    "+@_xe&u^tbukfKT~`dEfw{GJpiJ;xukUVPbv}K>QQt9sHLI@wJ*MP&W1$(1y-9YY=ZB1_fh86qrR{wlPc6Ty7cGdm7}?4FY%"
    "L}qBFAAzzh%CHuxtVS{WGcO)gkBEAO)W0_1;KsA$+c}N`C7HbYxmL(d@PsO{OXMKHqLH)jmg=$8@yrkQesj??ggrA1u3-bW!"
    "J&lUmMxL#;86w*Ay5tYflkb{F8QZs--`OHTFyBauQdzOz~xQmYXriv>_30<bZ|D)a|=+u=ksmeE4X`zTM?zBBV4!34OhV_`n"
    "JW+)6acMIqP2HE^``4x1rPkP<#AgS5>_2NiTi?2&(*aB~#ev*)71ZpgXe7SJ=@tE%aO4?=rGj7zhcx>_Nhj0AAe}*Dk)dHP3"
    "{xU?%PncJ_b;b3*R4(G0!iVy}gTgZ#q|g~x0*151xx_xub!(SEQn`K5SYA9IaE<tdek85a7H+!_W&H3dkAnxr6STfd-UU=mk"
    "UA=kH+g72r)z`RVAt-+k{I<34gDYm(-eu*ZK?n}FF<Rxuk(HYU{_Ly1)}j?|DxHrD+Nt;N@N(tNzIq9%=XUYEDS&^(5Mh>u>"
    "&@IU_~BY)KV$VTQ~@b0XFwvC@g%f-Y7qI<!G6hdePRE7wGt-MH$olttVX*Hc=Q4!{6CNo}k8<h`wNb4f(&7OLiR5KMcmU|K9"
    "z&LqhXH!+Uo~_bVR5#|2LF4Pi*0dd6WUat2r8Npudt{7$8dS3;djtn_w^OC#Gu;dvsLqxNS;mtdn^-_Hk9N*ZO*b!5!|bm{>"
    ";j*^lnwo1ZmhUT`;%G`C<uY(AFXksi~+4|i_@K?I9=K~teWTo93^H{RX3KP2NySZ*xG0%u`RN+z(8jG<XRsy2M_UIpo4<G(K"
    "TP7N`!dU!entg`5faaKn5X%Vm?qTEsuKKdY$$OZW8>Xq;cdBDgl%@r>!~|$xm0Ql6Z>r<^jLYc4w>ynpXAC0`T7NoydBKwQ^"
    "Ja`utrvP_?UMhx6r~6m@vu!o5n=Y=N40L$SvI5zLKxTQO68xA39M<AK(WaJF8uIq>l;VnL@b&xd%11Jx_CRIP3D!xEzD=E$("
    "13IgYLhoQiV^r<Pu9#Z>s{NR(ZcXU^OrdTwL8Xo5Fwf;cP2i&K<L@t4Ch)OIy$S07M9ygQt9MR~P9`z{W6{$UC0oXG}p2Rav"
    "MRC^jM@P#0k-_ZL#DfjrNV1PL?*y%Xr0Z)cs)XAq6jpA4}{vU&N{4>Zw#<j$w@<EguhYX$snX}2Qg&%8Uy0XepKO>VEyZ(;Y"
    "l0+b_@WnUxwpGcJ$Xix4#hq{&hu%(3}vgEN#yFL(|o40wRjBzeJXdp!8ARs6eqr4N=*aKL+S#$vi-jyI@N?Eh{qVR{hAIVi*"
    "tdj{s`_Hg$#R<}a7<R+xpkd40w6>w~c-jPx4#M~({cfYZyh~n2`UY>M`?H4;(?aeAfoU}WQ=Yhx#c}H5_?)l3+9hvNxT-bz+"
    "y2~;3dkCDRe_nvd-PpBA%z8@$qr;SKQ=(Mexd8<kQTcyvjxhx>)$&?`NFch9b)(WHO@D%7fQ}t$pSMDIJ({hWapNS`d!uP!p"
    "+|+z?#iLMy`*_Z=WAUGrG(FN&@0z{)4y-OYkeiU1Z!CeYw}yTuE7_JJoW}K4C~$Qw}kYA2@P2TMf#0t4AW`?GQq&-eIe1#NA"
    "u59Ti|~c#u26*)3&u6R;+1-r5qy8rO%Yg^8RtV+DhzQ^Fdei?I%xu(Y5P?2*S)VN@k!YT~kD8e_iMD0~yLy+7_xNdZ+6;Njl"
    "C<pcZaAs(M%I6n;b$*d^HH_Sj2&onZKuP(mTk+S5rcZLiEbcX*zT=6sx={OT1^?nFQCNd!n>5kqiX*v}4H4cR(i$wpGigcJ@"
    "zkV@)nn{vS*7nV9SWxA-Ns@!n9keLyen#LodDU}~K6{{Uxdo{R3wS`ZD6)y5iK<eR@=@m%1lS3th_A%{!F=zr!SVuV5SEvh+"
    "%LBhhtZ<=$PoYj1C3&teg=`v^y9prEAbQ^5A*=Grb_!TYi6|4GOtItHSJB|NK7XE@E7rE3eWRkdqP+#8jdlt^(~rhit7GF*x"
    "!c5CI7dAiR|3{b>b7W+=6f?T-ucTo@Ih)d-d|#{Zs{MLgjgLi;fYeS*DnRZ-+^l9v7$byB;~ryvPLPji^SqyEEH5aI6w9nK6"
    "3rjIDF3*B%yH{GPHQMCLKp&3R@Dr3aBzlKBF5iQ*F$IwyX+c0>Xzi~OKaddj3(i~<YQBbc|>9X{Hf$u6M#fs?7jKbR8b82I0"
    "x)M>oS;&C)nSiss|o0Igy#oKuU31$G)hDR%7aQr#V%>Am-S*1pB48NG-bj(HBlP@A3GEIu>K^>BFZgLVF5h%(Qya63I+fVg`"
    "8?QZpt3(%4)XMLYtl0i|lo74?c=vUA8IMw%*>OHGBjLVX8!M``T9)*=eBmaxc3*}?H6sfR3X8`uJ;rPD3<wGN6kYUU%0`>Ci"
    "PwL)Qf|C)x}AS}Wmdb@eanTE7_IP~wD_m^RG<q2^#04*kE#9Q?eM%1`lAU8z9AOo>%qHn?ZA?Yzw9u9S*8dj-h|Y3nSYbz|1"
    "K5dV3-XviAH)pA}h7f6M5jaTLv*G%Qm=I;H!tI*ubg&j>i3d=>NDZQ&LHpqonmAqKikp`385GK;kK8l~RO)T-s+xVF}wdFTn"
    "oxAmicJg^`eQ^j|2AS=iXSqNVr-B0$>VH;WjmB`uT2U1m!ika;f5;0SoSk-$l@bxpgS(7Vw{6T^$VpGcg<LPYZIsv^KKJwXT"
    "4zDth5A{Itf5-Wp7bYch9IK(sLwH83XzsD2??a_>Q*rATOXHLI-e}|rH%N3W?d|MECd$&-S61Y6dj1o-w`Jep?o-|QU{hP44"
    "_JR&Y8K(75v5{k7PNh~h*ieBV-!b9R{dD?XUCo=ExNUm>k0FFoo%UUUacf2kDMY&oIZ&7{DsRoRIyJF|4c>0pmOIGznK(~;j"
    "xYLTJ?~F-K1~V}P5Z9^Y?A4ff`Oj$n7c#f9>TTjwmG8@rhnwmr;S%Ldu*HRB;5_NpOtK2<|q1fTE_s@D4u{Fx!n^cj-z|M=m"
    "W>Be9|8VP7*VNNn-odb59iFnCCx@6TWP+&me<S{9Xe=LHcK)DY=~G@zAh0F&{jHLcbm2IUufEvDxH%zaOfxkM<ObLtLkSi|2"
    "`4s|(x#)JkX#M;fVRgCX_(%mKU|E5=|v-e;2Bqja7i+jkt)(O>t&AL<`|J!#LpF=0$XefzF8a@DGncf)1h>^B`J+OqU|a&`H"
    "<9l%4Pvdpz$?SZETn+WtCK;Q!wTk9jC%a@)=3prjWrs86+-Isn4JsI4JSPR&hK$f{R#kJPJlD3pnKh1y9rJ7r;Na)krCMEG`"
    "n&P)0`*l-Mq+OkI1EU|ln}Z18#;5=u?6!08UP1Wr-`rE&O8mH(QS<`P5rjrA*(a3}O}qA6cXaF~yAjD>{V74C!`sQ06Oa}5^"
    "I$50tC7+Iss8>uKr#&XMdSWW8xI*ZXRUE;0XG(d^i#*<ml=s~q{4Mmj+=uY7HG|umR~+#9$q_T{C1U6?Va~PC~!N^mD^smz="
    "oAHQApD0R8IS#jmUVku6sVK9I`^-93*%Zl6kc9N%MA~by#(WvWUil$<eT@KP6^!%D*h%TD-%>$--hvxlzf~cdRgu_|9;2<fM"
    "QR_*z&z|7-$6Au|DV?!uu>q?u?#f?QTr8W?2FEd9M~zJi7h<c=^IQV(bg<<qh~N!BpjjtBDC=h&EfQia$s^xk|Sc3f#8qc}t"
    "bRr?=zwXF0SXqu&y58SG8?NX<pCcd}gi~W{#A4Yg~x%M2xub9@ulhs~gy7vSxn9A{`GBVq2JV;Z^)HtK-@mLlzT-O;e<gm~#"
    "*#u!7QGwhCVB1J%->59pxt*E;MOiYxAQR;ZUk|dU;2J6szsL*Y`zXcpzQume9N((eOX9@*SDNExBI;EcgW2H!mnHPlIFa&Uj"
    "g0~Qb`q#b391;pk_+7D-9W*9#dt3MqZsS2`Ehp6WdQLIgST%-W!}{NObV$6zPyKCO6o&5ZcBnr@Lt`1&+L`7Uy&OLR<R965+"
    "8Q&JnMuxKC55(cqs*&aJPt{Eu>bxQ4lF9?)99$^^1~_f;-@Ofd_{0Obj0*SB;)Y;L!*?<4jAozO?O`v2qZG$9!7Ox=xj=z-I"
    "3L@v(Zi)-1K=`-$f6#H8)CRpH>j6-aUG0S4qSa(>5uKRAnL{I>^~a&(wTi^-qjT*WZLSFLwRW^`JnU@I-KF+R0yMK4hQb}SR"
    "_RY9TYcs2YapwQaCWxECb3DbqP*Es2{4_@DA63$OXAYe?<(n6#@LcI|BVT|u&4sP+aw92dLIs1A!7aM1nr|XWlf5unD+IGjn"
    "a5yLQr-3dGKiEAxvt?8fkMQC)u<{~voVtAqeOKZh-t`dIoGb<R4E(H^{k|>VQW*A4Bi`97jk*cjw%Cb36%Q7J_k750C~EEC("
    "xP32d<>lA+7d~D+W2!T$Uq&{<B47&$p7Dct8Rl(Gn>DEL%cd&k>d-)(V>diUdm>1kDB^s8`1E}6cMz!h*!D~*&JwAwV$Hr5l"
    "V-@v4}CM^7+(-`(J;2F*`+Vv(+c?k*R(|2PT#@Q@H1gnNTte)2PUfEOCF+Hz2`rDw;`F&oy72E4i|!cQ=WqL}#gkgK)7b9%)"
    "yQSWW*Vw*io;2}mM6KMu`}Fe($x9omkVes;P<t8Sz&myG&JMRcY~E3I+xFyQ1b3i~wwa(R)Ai&0{cNISv@XZ8dO_Z5uRFn=;"
    "OYNZSNcZ*trCGC|FFZUGI)^3H`==?>`#8|PYY?trVj(Ej|$E=+c-mnr+y7+MFApn;6ij)CdgQXSh*gp1dBW3O1_Q3DquG|DC"
    "+rh?)aocMRz}W$cblcl3v!;NRf`okMaA)S0(K;NnT!8%8%kCTa*!20)lM#EPggMI0DY5Yy@YmsHmgpeljk$xBEyzU3$X#j_+"
    "L77*u9xx8E5|wgru8rwsYqOiIDWD;qqTb3oON5oDS5fSB23TK<TGWm4NO-dSwu2^>a*rt<8v``u71fK%yV$NhcEQgb_7sS{-"
    "@|`?!2jq0RMvginiOmeOCb!(!g>;6&WvZC{j0vrsHJ&*7Q-5f9A59i@MSdz!{=qvqW@KvC9hCBN0dIkuz;0H92wt8IvzXv)-"
    "gmcFIy0+hT@sbQrW_CKP<B2ONBcJd;WdWAjjVtRCL~Tsv}PpnsVtb48}|*(?xsayFeFfN}Cgwm&-PpQhq|EecFu|8t9caeAd"
    "@_p{9T`$2X}pby_K++V$9?0WlkGlzCm<@BYGG%fh`Vw7Zb<!ZcZx*~++y|c6MNz0-Q2e|+4_lEpuH1?F@7}MEPMdPs}JR#(`"
    "ad)$!-)$R)=XlyTWa{l68A<MkrLghail!Kw(9D$pXKZ3b2&+gj7}Q6(WJus*%aOaN6P%9B-0m8T1RHaY8l4fxo=rZizjOOgF"
    ";#ZvAv=BW=f1WjX#R+macr{5OFY2nA&bxJ_i2Urez-Wl6E2(D<t84Nh@nVq9vOA$pZNo_7PY`1BVD|V69q!}MF!|~$VBgQRi"
    "xdY4E86mc_4=m{d)96-w3N=<;a2xhk6PFvI0qX(&G!p?$v#FJ2OzY@At1f@|pfWTFl_ZwO}MVJ?!2o_Dc2)`7T~60!{g*r&O"
    "V(U(D(O_t_uhF$`eOIkVw}J8_}MOydAnq<J7u^Z9>|4+@Uq#kT8PdGN!qYt@CPvF%P<nYF?OvTXj`{i)>UQj~-U-t(}VtvMO"
    "jTb$O}2U|NNTIar3EAqO+zm67V*B-F{PEOi#Gp?oksSwe#RXdaE`rw6PD*u=XV!RWsnu(%T6~+g`;BXo>Dk;tjeQDlCwd{D0"
    "NPW*;etYRBAHiU$k~F0Pm%XFui(=9Cy%Ad@`4&Jw$ny3zI)rZ=A5em8ts0N)&M4RC{Lws%kdYI)86LSn(%pAW)H?XnC=l|6A"
    "$kImCl3M4;B73p%1|XNBn8&;uDbkbdbfz?0oE;H;f1YP&On-lOK#9>8<c<g6N2|WU^Sk6yUjYTb*6L4b6)WWj3jQyqaW+-aD"
    "L&H<J*-{EJi<GtzOm?Qq6H8rhz+~)9)vd^P4yU?KP2syj&Ps2uMN%@z}9t9JKW+Mezb}56q|rcZ?j$L%NmK&kz!yNDcStTcf"
    "$O<vw1M&_mkiLg>>e@EiU~^aslSYAoif;@l6FEwfVLX5<eBp^g{?96R<kHp<schc)KlUl$YIpAF6@l2{*!<_H1Fmmq3mT&mK"
    "04=OV~WE+Z#J;}C@D+x8>vKN;<#d^CQ4sJ2dWABbe?q;6Y$i;>TC1&)umRvw3Vmo{NGCuO0A+SByV4I<lFq|ff)(i9?DPJ9Q"
    "I^G|TNY(w8P4gG%AvE;L2!mc|?M`)qsqB}k%OZy5awQ2lMsB&=ks`MFPWZUSk7bs^YCK|ohF8VbB{wSeJR53@AO7t*=;okYc"
    "l#F^XJx7{;GBXlL2xR@Hi`4_!F+g9EW^g=&w46Sr#aY_ACMiC!!m+Y{0=j~8nTMGa5Yi3fNNb`54wboa>$367}Lh&1t1%@2!"
    "&%Seg#3A4OVng1J*V!;hqvstXCshFlg3XT0ck*L`yf;^cz=WfEse-abV<E`jomzI3J>BX3N#OAgXBlEyrFjuJ6PSb4XXn-p{"
    "pb?7J*LCVZ7Q`!bD4b1BJiO`7EIb)XG06()KwYANe{bj3mhE@-_~Y}+ZYlBo$<xO4Zc^lHZ)sdgznV#Z$MWBE2S7m@;H_%7)"
    "s*neBBIsVZ~+Gz81mvft?pKY-qfaoBlMIkAWW2XupO#DSi%pup|7t)ps@W=NLWsvMH4kFkNPr<TFbbS(Je(WIp2fRi)Tw8r0"
    "`paWAt_Q`F4zbOn-tPw<RPR()Vf!npc;ZbtWv}?Khc9NHoMwT^wWjY~ESi-t$}fXRt+(HaI4HYsr~B?Cp1t>{Svc0&mv~Zw>"
    "5~5a#mA$@t4oBO#2wyYeOg{AMqzkqN1~~}HT{lkv#P(-e{5f@GPyf(Ghfyu<;6M^rk1cx7DfhgRge7#PKz(U5=8z*mQ+P-!@"
    "JJsh9w#+aw3VpLL&`o?&m&(o9GX$N8*uRe9K^ay*&Mm;dK5hlGSAk>psN1EWVRbdCPMaMZqj#*gZgta8~$GAKK8N;l=R42B("
    "nfKyYa%+j=-ggfLUiyyKc1v_^h81Tdik&8RagBW)6X2)PB!P2unwP15K3DaIe-eH{r(KUDD^aN>4Z)c(|k&84nqDpxvs9bTV"
    "xLS8?v$g#TwDYtAXt1F~9-@nsKQ{WSP4qX-{f>}a{o+DsEa4#io@J83a8JhGC?eP)B7eD^@hPS((y{tfG>sKlB-R+S_a)%!r"
    "ckve`c;gkM+NC>L4I(k$?aqcS5=%6v$`qvWlwd&=f&eYEl5gFj=j6Q+Gs%k{yV&xJZdw_d+~>{Kc=FwG+z9>hl0;N7W~Zn9r"
    "8P+nhl5r-Y0latK@{33$pR*dDSmd>8h6axK|xi>3+oAWZ{#qKPN3Wm>EW{1={@h7MNTAimVyWtTV8}2XXGYSh%Y~S3?sGA)E"
    "gh_S#kpx`EhIuCfj%{0Z9<!$X^xP=}^BX>p}vfYpVa%-(PBSt=HtGirLTTH?GEeA|z~mIOtI>QHuU}+w5=}wD#j$F4v1Ud3>"
    "dFnOMCW<;+1cSyq~^X29gkalvxc#iN<ooxvQUg5^%uhMJGN%AWR<^f~`(sKZs4G(}FD-tAI`Jc$X59w&mff|-f8iP^WjA*<i"
    "~oX$D`f$0P_25HvBwJnH+4Mko6Byg~<EvG`HeLI?9v-rBFdFW8)GeZ3`+VgHvi(gBJR}xiz7{_>}`Bx2>2<UZ;?Msy_SOBo-"
    "Y@M6ok@>zrVWHAewXeo|!Sn}|9xf-*|KBA&xc}u%p@8+rC$o(%<m)+^t_QXsUlTtq0cIIMa@^$d#Q{D%V8uyrCPrXO;tV8n1"
    "W5l5M85kaa(Nf$eB}>3%uI*ZgW|z7?rLzk_JIdcTI*+i&l-J}B94M1)_xMHDCf^#$6sIOZ&tvmPp)rdpZKXqKLCc_qCV;;9j"
    "x{hCFBlnxu;Xec<g{k2S%h8AmY!qJ;HbI{7IYCs-%MqbmE5?i%!s848FZYp2~b7;~G-L=Q&xks!3AIA9bQ;ez&sOD*$ZfL}N"
    "}KN1gsuXra+K%Boc(QTLQV_>WPTBE57F#c{M#-kh4>Y+tuqLM0ElTLAu1LEM<}f4C{jN8S!uXV9P*q!BvJxRKk<Q05{naP5O"
    "ZG5>D<>5Oi3W(pIEdM6mb1VJHcxz5;|+wgR+-!VXLuBbV8RLsf+Z^EzyI294qDFbgsj@|rOaPiQI3;_TQnq@vfaE}&6GP>*X"
    "h>h|DB9pP@@xk4PbF;s(8N=KhDLl?v$j_NXqO;Z4<kE42#msORlD|tVDHxeoxT1;jf3y!rBD(O{Q1bwkzs&eu5p@J4g?y`aU"
    "R_TKQ#s6%R{qo?lJpK@lmZPp0&0##01XmtlV8(`MopmmidyBwR_)G0UpQ7N>>HYxD!I%SJ@uJAdMkB?Y*-$H{YWFSo1!dWm>"
    "yE%vSP6=fJ2WCI<oPeJaxDAG9<p8`{X6NVc+a^L^WF$Kj?3Q=*(8Z{QyPpArC;6T#Uf*AQA_c3INztE`2OA<>Q^IZ<l9|B2D"
    "PRf-R-CNOL@F4wg3|qUrq?N58ZR82h&*;sSXEL-W?jyneajdb-~d*@x+c#j7LhC-EFU+dU=oQSiTA;+OXgCH=gE08ylE!K%{"
    "$#rd}EO}<fnj7=M;f(=@Wjg%@@#6T6bXE&%5L_eO3<K&1P$Y=jE*r_r|0k7H4rFM@yJMToK=vylj6)NS%2Ita3(_^nztcRun"
    "`uZd1m%c)(mIDCHL2Jr&5`I+rz8j3AuSAa#^?a#6wm-c~hY~D_$L9Lzogp#}gU%F;V<xT*!Po@^5s5Kx%l4D$MRjlk+4J>Dt"
    "EPOack`^7_ZZ!*#vQB;zscYMU50^NDmr{&j7QJJ$^Ie%MLe;b5uHo}XKh4NPLEEzT_n))zuR{gqX1eu_+lantRZGvWyf1|qE"
    "qt<UsUF|EoGA-0ZzkckY|+zl3_S8u6BI?_-o*6UMRQoTaXhcH~43jbZ3tln~K!~kpjHnCX?$~U$HF!GO+viF>JIp=l@P5*%w"
    "2H+V;W5vM5rYMIn9HZF$~9ugV_i4ayxQg;<ec4tm!rUnatX)-$C*zo4UHekR#5=Q^M6<j(MOydK0ewv1y({7t17ivvpsdL}H"
    "8FNEB(xsGp=&ND~%{^&iq_X883v^}I69vj0*r9Qq8*!B$M0uGu_c`QRu(NsedG#oH#Ry6Le?hyU{s$*Wakp6O&eR-_4xRQBF"
    "yTrw^a3QQNhiFL}M6kH#q7)rV)raR7zwm_R$9V~^2@o<|Mk2uJHcvHP{ZfX{Mg%|5x*1Z-?!5P#**d4Uxl6rZg8cY}a^*e4Z"
    "3c{p{kKjXVJDagC3sTJr@_UiVAi3{AM!CTg2f=pK=K_3Ly}n4m20EyoGy;V_Un}D8djfKa2f`X<A)t)^)naquQZ&Eq5)M;v^"
    "mAdbFJvRvDG+23SW$Xi;PtgZ4j=*90d`1PiH?)Bb9~v_dljteZ=jJH9oCxgYE@@+C0~t+~S>Nmx7>^x1UwxF~;^v^(;}EqJF"
    "iYQn9G%_vPW3J&T-q@rbpvAnhoYaOk^NdtwK?vAi%_du~>@*i1RO4vQCe5pwYnX*FB~?YAciDQp{H_!@3b{M|SV#R5#|Cy*w"
    "jZ*FrP$>3flm%>AB2LL(AwsDjw5)n!0HLta91HrH^!GbLKPHf@3nL28cIFJEZT1Lf|Wmfr!WhXgrR~^cU!0;~Q&8`UXV~l4*"
    "RmJr{7q~<X@F8%#TxivhdF%2Ilhe(j=gv#*N$ioKBx@f<1+t>Pm_qAW^k3mEVJkzx1$oc!*}KCE_ai`Lg1pD)h86tzK@-W8d"
    "L0&eiews*4i0CcPToCW^Tz>O^!E0JgQ;BJt+mp}*g@mQN(ka|$-}u=*;H6iz}gNc|J&qo>2VpGv8P%rlDvU4*#}&HIC}UfBa"
    "JFiL$g636oK)MMd2=F3k!j~^y$-H_`e_%N5%g&odVK)g*Yt_xBb3ToL54A2EsN)&W&H^+2<Y%0%Lfb)dI!@fH&OP-!8c3k>$"
    "#4T?JUJr)E6W^v=8(z&D!2qHDadOi!G5;M1B(*}P|#r=giIpP5Ot46^v*=^~i=HzmjO%v%J{d82=-_lWU$WoM3^D3AYgi3jc"
    "IG4Dbk%(R7kJpA^G{6>uY<@7%k&(+^&j#w}X^nO<$YbQda%axH60dyrEuhbwvU_%VM)K>MparK{#yzuN}|K`eN7CWE?Y~O7e"
    "3ob<`;k_(H4c^nckriT4AHR=u)j4p~eknH;A7B;ql#9GFO}W6P-~O2_37C8Q^gZeI41Q3-3%>H4mSu!TeFStxcmN7_l`+Ux8"
    "j;+LkJ+&u>9mTL80SUHfI+CTeFLhi>&v%yCsqAaJ)`!ix{I8kSbzG?<2z`f8QJ+I^AV(4<UZ09@O-(Z^>l2IfA~i^m$Fi?g}"
    "dn^4^v1Px1gI|9PE$VjZOzTcv@cOxoT=~2^%+#mhSUMHUb#!d&=7lwxERXxfyMWRof-uq=&*St&Y6w74h4$kI1zumd>=svb3"
    "s;=U-`LqlM@1mc<q^s5-hAKZ4%xAjpxMK6Mx>=LnnBaNhVx>JtAxuQ1paPr2AzKBZ4RgLjIm=Ha+`&Gu*M9qNA`h4x@UE)GK"
    "Q$aGhJ&;>MCN@>P+Fz;Ov=OsGBMQrGAYY(Lh0}_$PUfMn`9c~3THfBk;|8@o>au$GabTBNO=c~3IV>G;KmP59B-xPebZ%OMf"
    "ICH_;<VBi*!1~xcsO)b$4n0)ly??Vxnu#TC3a$acTnj@rD#+kbNgM%=LtYay^sFXwqSPH){wRT$@~qw!G@=r9#97{JXa36EG"
    "hr{wGwOg!N1WDRuHgE(4h;ev4k-UOmHw8omfG$>1Y_)P_w=jv2{p_gX@_$GD0<r5F7Kgk!_z3m$AifgTdnkvcctx6n+YJ{O7"
    "Ei_4ua_^C4t#%t{Xy^t6O~>2g;`tG6kHc5evkHFd^3%Q?N|ABjEc_uij2<#8e4D+@{eF9C#R3TXV>mtGKozozwFB^%+bsqhq"
    "o)O%!_VOgTCtZ2pFC@w+bv@8*PW0>sBHQ#(<T_8r)s4`7w=baXu`e>?Ogar_AI5xc4s%`a4MNz_HknHPOLpa9=xhmaEQK3{G"
    "v7M%bF1mBN&lM1xDRa^4D7(O5vWsGm`x$z<$GnDxIvLsi~mmj(^c98IASJIR=AW&9cTM7ew{c9KAEMseOq{Qw0lzNPlhFLA`"
    "a5W=fs}x4p6i2eAdxC$8Fsc3PlDI>y{*7-dKe!?0!3d4?Df+X0#);^_rw8mwU*g-A==F0Pj(?-P)P;btM$MdAR<c*H&JSHRA"
    "5}_`%;`T@0pjd_6R&o*8o|3U_nv7Y!DxAd2@YfK96T|NiQC?6?{}`$|7|Zb6YTqa{B2K=hHCtWLc2;J38GmnrgSwyI48$)Hn"
    "i#u>|XAId7h}YUJtI#AfBzMh38u*YUig;%+l24g4NQIfyAMfJ;F6R42O25)+0tgnT?p^X&SjX-03`yaS4I^d*1hEx#PY9O^>"
    "mSkxC=wmm*}({grPdWJ&XHuTVxCdcS`0ih2n2nDs)53xIcLHbw5yoxMn)-;(SaqgND0gH-%yU2S8>4!Qpgqp;1Zr$sli2NDW"
    "aq@v~9vlXSOb>YCD>BK6>l|o#ix26j6k3IP3(%pepViQw=W>DVVMU$c$+_2JJMJh0%UkO>5TT?f?R!<-UE|kuQpj(1mjsZ+}"
    "C^3YVK|!<JmwML?MSP-1swK&^e&fWQAm{zGS}kN^F9>kcza)=q!*ht1`;zJrKS>&bT@>0WL7q=>4s<fTB+U4JN<5C@<LkMtk"
    "=fIX#P2p|pOQ~1KRaJT7kx(eEASilGwv8G4Oe{7`a!ydnyB(+)0=>7^pv)M+Cvo?QA=diAEINQYUI;5vj?}gHChYdZ7%3?iC"
    "(FGo;rKGjN!HXjr0-2g`Mh=FM{%Dn$i8gCaQ$<M-3#205Cfk-pZaf+Vv*b1n_5_bJ=+7R>T|!F1<IQ6IYi6&tt6I51LSR52A"
    "`;^UQeI$#1K526tv=_3p2((HpiIpE00+i6B2~M>n1j3j3K9L)|o%3;d$i7RF}m44z{mskNuCN)EAoT8RPnYrcVC2tCooZVTV"
    "%LjBc~J8Svl|BSM%iQWnM>5=tgyI*&)+9-wx{Xt6XQeHrC*{U-!p8jCo8r8dme-%v@R(Y3i_c%}rT*U)bzu9?TaCjqF`7TI5"
    "GB3h1hvU3bl%j7dS@RoJQS85@XN);-|D(T&W_|8eLofex@6{*=QVFb;M4mM`D~Jlb9}^g_=xym`{e`2*y32PJ4|GUZ`zfjeR"
    "Y+_OAZ0n*PExMMT0{y7Y&|=b@A1aNRwMa&%mo;@{0rS|LYVS4&HJ0uT9N3AXi#7@aC`R9UUN?u85Gx|%sZQ`1iw%W4@%v##%"
    "zg|ANp#0602}TQCqtzOuuD$9oNhyzDw5^NAm0${z?FZ4L)f4jmANq-YO8A)E=?1zFK9fEAGY;IbLcJw7WM=_rK#sJpQsb{*w"
    "DePY-)Ip)~RG{(i7Z7m|O2$n>N!3lm9!4h>&dXypN&Y|PHEUkLy+)S%+k%FYu}5Up3qlYrDgp49f#-t(XY=|A)>!vx;ZACuX"
    "^)P}1sF^+&CTw~(ZWHm6H8>yON8tG)4Cb5_@K#zQEWoDQ1VA@Mt=OS>#yX|~c_fO|&vd&Gykxt2jGgC`lRbh9c8vwfg<ryhE"
    "fJ}BgouobV)zMX9+r#q%tX5o@u>d4>jq&t6j-ODVq^Y?F&TWByuB7@kB;<3v&HM((d$rthJ=iDbtM787Qo8d$qHVf1XuVIFx"
    "GkBQ7)W#ntI~>{SeZ_VK0FWAS)n7IaEFn`zJtbHo;%=P++56Le=&Y#IlK2e-OR5D$GX4XRC_Ky;8oieZ<e6|rR<<ar?`}e;9"
    "0;g1__}DFMR}_)r>Q)U$HI`$5QUY-C|n82b=Vy#3FL+9GH@#TF2Qm$%v3a&i`uMz0$L3C3EU6_W87Ei0O&!{7KDCI5&y)j#r"
    "&7h3y0|F-K&D_cJoc#sz>=7{xJjv-EP+h`UQ@b0_fEYwqp>Gf=4A^%%=vvJu@kN!oEue7I?!h3Mt|U(1nzFL5Z!bNg~4$sdp"
    "9JpiWu03#$aM~5xW6Smqfphm?4eEw&-kWG0_C_v$E@a_+0C+lk+^H957;J>1I;As!4{LIlrAsF)e4P0@W3zrjJPmcPdeY>L_"
    "Db(#D8=+^gnOYL`3yF_IZW5BO)y1EhA&6E|{1%9hUOY%COwUw6PUKk(Z*A^N`m}q;7jSsO{%2#f3r5_bumNJxSQmF+n{k|~O"
    "Ipn#s#PD|MalRM-{m*__T)k)-16gJ%ktzhM8R4+&uE;4qF@T*Kp#m8Nec4yQkd=r<qcJg3%?Y9L8HI3fG9d>`d&^~SiVbHJG"
    "S=l1%G_6(3M;Frsv!_O?7&$H&f(_NB~J!v?LT~qA2>jC~|`^o$H@=U5|!$WTL&M6~BYWPi!Nad>cS18Pwaw*OzXE_gpM4!kh"
    "o;=ILvl7&RFYz`P`h1{B9Gnk7So@KHxLfBVLiRQkPhZ48usaknTD)ycRaRMv*u&(tsZ#y&p;8}l`vNE`r8LUyHPy||M_AWm_"
    "b6?mfm3l|W-NN_TMnCz3Cm-<fT^jK#IoDpZh7fEtnilut}jkz^jj6lO_RlUqKe}jCL{kQxJgH*ENfvb-}<L95RCekhzH{$d7"
    "nLs(nLq4#bH@yoeBIn*B9te~7B3Kl%sy&`+;D`@LtgkpdTT0~Bcnx%HP(NJudQ5EuEIgRuW~y+$iz3>D{0nu#d{w0ela`Mxq"
    "xi*CB3opM9YhLf!_ebl4#`0?2Tj^$C14OllV`EOF^YX4D}o?2x9Y8OHLRj<PDIp9vWio9&=4p^ZMVkA)~F$iU2eFU*KH2#3n"
    "O7~NB{$We!4sA?RO@9eu7rK0C^*RYVg}lS%<po{}s~}%5j$L7qOUjA{HsStRv2~bqn|&8WJDa^ff|k6)TYpu!=ToBj=P3_>?"
    "huN62ePaO8zx(I#p0{O>9h#z)?d|15{A2$A$W%*iYNW-3H&u^v={YW?V?4<AxoDbIahLIVl|qttw8|12v5$2^cmsw&_~`b-x"
    "R+EKo8MT@QUC{`6zP#x#B1WP9A9eZrO)@WdiU-0u&tB1o-DF`N+iaSM7?7WT>pH51&Q(eHwe!iNBsaK+p2@Ob&`|{N3=vBU+"
    "J8mLXUOT2zEa)_PFEK7K4Xtg#n#U=3A@(_o9@pxQ_SOp#UP6aMwFG>kbEy*T{Q6BcRq3`#qQEUaz1a1dTBsNb^Vi&6#r^jN$"
    "1alO$G^KWquCL%*PkY1LI%0rfb;??YQ8H-qw|0jT$4xMPFlU=@E&@y>`wrzfN2~#8PcULla=r#4ETTqkxx^K9Bc>PZ-cza<^"
    "C+r<#zF(ZocTD)(CW7NU!g0v4&$G5ft)HyHQ?#v_5cN^(=dMoQr;%Xk5*7hpSi@T^r=Do3Vkiqi&cds9wSL2Ns$FdRHPm4+u"
    "Q3w-o3iYKzp+s&tk2sSmAGOFEf+CW-nE?|8WL^_}|FeAX{>I#lvEFY!<Z$OTWDIRO(rBYQW6DIcWvE%@Kw`x06Rg}U?<(*Gm"
    "Tk2_l|uiy;2UxYgNGq=>jTiZzwTfsZ|vhpl1)k3%e=iwl;W_bhi1S>qI+U;vUA})P}C>F?m4SUsp&FqX>|0%Nz<ih5s@$n^1"
    "nWj3cNr8^+^VHCQF!}?-firJRd}sHZ9d@4^AONeTlgwDye1=<_p~YP@j&uPG`|sVFyG>+(-H3y~z6$ou4~)O}0PZSw+-5@gQ"
    "sSz+MNm0%ldvMbpA(~K%+nO<35)6W|Fw7J-%x(>e}*AM$i8o5E&EQk?6PD@SxO{i$zFD2$&%eDWoZ;+iLzu%F}94IvPKM1wr"
    "ph>%<?s(&i7CF{_y?W^PKaX^PIc9*VldD=f3aryzs(isjwYBM_p-2>s=^wS0m6^ex+z_1E9)}5zg4<7HsQ@UB({@u!Wx7%-X"
    "{fAFgwarr~<opM*Y^ddCErC97lX%<44JMQf!SS=p;iq<_9dJVzT2;1I4&EiyASf1UHLojuYC7?T`k6)vx2&?~!83W??VzGV+"
    "2ByqMin$xwzcb+Vg8=Qp{DB<XIw1;bJs25U{m!anI@FXfJxGp4E<m)*=?YT&vm}D$WkB309v|%Os9oiMXmv&$IT(jNy#yF2|"
    "z7c`nYW4B3s^*#Ofb?IGE?R`6)#%7DU+&o=_@tAtNubzqLNV^S(Hu+=zsCzdhQ+wAW1T+e=(7@8bkif|)HpL~CyZCqWvp*xc"
    "Chp=(zvGSXg44W1PAA)eOLjApJ8{r_QuTO<jKV%^KWa!JTN$`PEY0F+5V;n!dSw|NhakO)TP+twBV)E)|q0~7TY;ha~Q(S;`"
    "qpM{BuklSjFUiw58O<4K?}XKax`c?jrM)Z>^hz1xqCTnJ0qpVWWdWn%XGlngx4xD1y8{tfqi)t2*wq?md3+s5;#<U5w$eEQd"
    ">Zc#OwwjH9U<V0v}sE)@F4&E#Sg`E9b8zPe_5;Rw@l5|+@BHjSsjSRH0#QHtOBnX+?a4}^U54y!IVo9VlCXenKq{$)DJ1~tm"
    "h^-xXFTbDyta40>PfnOLiOA^ev$ZZrxfyFWNX~uKUD_nX#<;96{IUL7?27mIig+foT;zhzN`2MDf@>xl?8(Xjtr9v{bbJ>Qe"
    "X|`i=uL!8ij2p58KPgr_q+Cbok*))N)Mj)!)C>mcO0%~ztahP1${r&<=75dm#lV!Y!}nnR_tn{js#OeSktnxs)AyLsWfiU%*"
    "yXu;+mdp^@#IUW{s}iXI8T{!jZl;;MQMG!;*`k!AiwR8__$z}wiIw7EXpgko6*Q?4|xx_Kexs+Z>ODEhD@H{SL70A0f{U@xP"
    "h*NqX$qyHMr<l%ba)6s4^ctNYQaSY&tzBnRnLd!o3^S?z3q;CX+S7y_mvOy;aTDb3B?hb+yWtF3^m0FV-<|F|5ELC_QT|t$>"
    "Wyw~A#owd^y>cu6z)zJHZ$#Qf(_J(MBp%8D&@j4Yl{kHeQst6?k3N$142LNmFD8yq4l<Xs>3p7eg#2CEq|y36sZko8d-d0DF"
    "|*{UcFiAdzq`6*<Fr-*tzffkY(QDwGeSmhiB#`z5$Gb?H&aJHp&mNJVTV|I9P)iSR8X^Ov^x75Aa!>(8ySQxBL$UUYWZq@wd"
    "`YO`m_{h>`=gV%{MA)UosPnq)2K_3H<)#UZiH&Kupn-82;d1?J8WP*Lv(G8yr^(O7Ot!F1XFVN!XQZ~-%+!7tqY~5NUzN0YG"
    "Tri@Zq10SXe_xiKcp?<-8;^d?J-soz#!2xo2hil0%~q$vo>yWLDLM2Qovs_qsf!5uC$-yewOu$rM&b9<<tSh8jjdb;Q#uhvu"
    "lWWX2*jizg%&OqVhUL8XwPt{+e&kDc(tEG{qHYkH>D=+0@R5+$EH^am@Y1l;OIOnhyv0;b&Qgsti}i?grH}4b~$JFFyU6XUE"
    "hii$8RJ7f_xO8!VG){e%0`pM1^q^_Icc48#pi(lK{_s)UEBFeS>)a8o2i>Q|Z^nRmVB2_R1wxjR&%yh}jTJ`mTGcJR0RGOTQ"
    "=e7~;xy*enjz_OP33CZOLSVT&TeK%2dzeR8024f*}6qAp1DNO|^B9BvWc+8(hP`e_sQ@(uRde4;8F;d;y?kXjn>QL`$DRZ<M"
    "zAq*rKE^yYf0>=%{ftkw*=&Y2p87ugIWuTE6#%v;>**|18c5JrUmFw`Y7Z=56u0ry@|^ZImnYf_>DP&|{0h4<M(n@Nb{(SyT"
    "x-v86pxOeXCkv~0Tm7J{9OvkCRG-Vz)cjc1@ViQ!G+}Yj`nUMFBP?WvRP<sM2^e~&)!nM^jfQ_k2a6qwD6kpxrh0UkiC>{F4"
    "$n%?a3L7vDdU&*jcqOPb$+Zz2R3o!<KSSwDhFc86ZA3obBNCW#REKom8}O<JKKngvy=L_j(B<0{yH;>;8Tmz(UcRenW?bXxy"
    "G%UhX;;xxjIkfV|3h_ap=by_6*RD#Oh0N=t>O>!YwlDQnJAuH^jBaj60KH<3M>O}H!Ox}E&r#k9_^jehfoEGCt*aVWZivVeM"
    "UfO3aHr!v>W;v}yud4!OD-kP%i^+62GOZDvG3)^CZ>bzOchJHv0%?WJQ%s;MT#1H8IxVV?mjmt(K2VEMg9j2gfL_C_HT##bl"
    "JLf*+2Zj|=>s(fl_x7L)v77>hzi^CA6gBNe#E#sTJM*0Q=3eGh+=F(B_&n#=fy0aZbq3(f6U2xJ(%&S1{{lA1mOdZYs`mM<u"
    "ZD8NmBz~{C&J$m@UV0Jbzi@qy~CH6cVb+`SAJ7zW}c1qz~eEeug(m6#?uC@{GbT0$HsVtBoDlj5cvjzrhL-xm?9OZS!11&er"
    "-nND1V=&X=>RP!acWghu3U~$7e$;*82Fpk4WL!iC#OmVq9bD!o^DkI&*qBl(ZxcL`>o$or(fEn`^>knzd9u4zO!p&red|(2{"
    "lC%iPsPkL0`<jD>Jd)ZZiY9Yx8ddebOOSj^54RKiRKth0dQkC^w#o8v&hV*~Vcn*0Ikoz|lG!uvBSPE|%rVe=6m5EXnltyf7"
    "SPbX1r5#mQRsAiX{tdSm7j`hjqGAj;;na&2nUX&vxlS0GcyOwkQ3ACK|2+Qp6V0U9WuI%grOhRabBmAMNT|{Ex0;k04U~R`0"
    "7XrJE6`oLB-H?AAn_U+wAs5oC0*_{1Tju<E<IT6yM^Jx@G5IVe2oJ^HbDLKzd1>)8KlVB(RQW{4fNgbs`?Kz4!<7yR9~6@1f"
    "BUKgdLe$?u62nH)HU!13cS!^*-q^iono?Ky;Cn61l}wAuA!YS$-1FiY)zSR_{lQz?VpvU0$wbyJ544uo||UR^sX}7Vtx`q-k"
    "Akfz})3ToMlu_EtmC^7t(?~e<iJ}IM3=&#dVyFV=<jJ2cRU(eAm)zy8An%ic8xd+b7aZ9ysk$xBgS<4unpCRZYksO9>9h&kB"
    "#F+42it$a6~dm;l}|cU#v+<lLP`3&-t)J)5I7Xb9*GPJdGg>(3IrMql%y(oBm%J)KB}WRTTQgUWIzE4Db;n#Oqpa3sVSq>|3"
    "btIM$sC9dv3&dH<%V4WN1zd2#iUByS7u4y;;Cn})ikW^mVgO&ZLZ=F)!>_=~Ac39s=nj2X4t-h*XFYH~o*`>Z`IQi1=n-%8!"
    "cqsb!;w>`{wwzEM${#ahz-RA$ZZimfbV|rTT6Q3(oR5y4ROB$0fK@ggHH|jnQ`8mxE|}U9EZn+xcFm^K**Nu!({7^~dlr{Ko"
    "*}G?AC>!C7)i<&RAwd;`89N9=Ug#U4V^esZCMpS&Q^8i9?Mw%(o_MkofF`HK3Lw>D6IoIR=(hyg>;{M$@ty|?}906JKIX9TO"
    "U~xDe_d>3$oA1Q4OkGP>xn+i=I|{Fmq6H6iuu6(F0o%+=PmX3b7%8k5bu1RNvR7-KX8P4Gh1cnLhXQ7S+WaLk{vBYMoax7n6"
    "DsL;mBRR@qL7vjz2$RQt3r!yxNWnKo^`@*3-LmZAjSrfb_E%c}oeO#^<?dpRsx3Hue|(yYX3$qHz2`oMBCKVW+<?fhFqHcCc"
    "LOYP$U6>44e!(-v0ksp#A9=Y!snWCjPuLm%gb}GAs9K7iokNz&a+R4)ELRFEV4WGDElc3e1%JJ=sw9#JsD0P`Jb(Ai*A1!bC"
    "D>wVY-S<MoN$Nt(H&>$k(zWNv%L4&-L7Bjb+4AJZPWQ%r*e8N_3&LHEy8EZ(h_2!nW(~M01o4SE>JE0i^aBhxu_F-4)RJ}wU"
    "TJBngJ8kAft7NrE{i@r7Ofiw%^2#nI3G2tv6uT4zDY&^MoRF6Y0P496JlQZqcwsSSBj0dBCM&T&RuitKhK9)UOsV}3VdTLyb"
    "!j2R6+ZldA+oaAag0gnaQn=NNJ%VDKRQO{Q-T^OyuKN*?Afhb=I7UYoO7%!5fd6p)W0lf%&(5%&OdWwV(AW4;@4VEz#kMkK_"
    "-B?rP7a2sRqJ9c<~jhsx>98C;q%zvmXpLspM)fkwCNj+g^q-xEz7QqDw%EmN$1qOzis)jAKaZ@?CGxQrctU6oFJ`P?W$OaDm"
    "x6HJXSM@W%ic(vz@-nhkyURPyKJy*@ds(D+ot2pe;m+9pCK3aB#yJX`!5Yy=z#;L}HYwtQtEN{p)mLIp9RSaFH*;(8T^gQr0"
    "@a@pH3FOTM*84Jg6psvS2;X}f?TgpUZ|(33l3l+^P~VXGf?Hc`JqlfwvuE8aGK!KCm`BdA6fiE_OKY!P!!2Wqe6${Mnioll<"
    "74^%{X7HYJb^h0hS~x=Y_=`WJ<v~wNM_vv=-Z2TnxZFjtjtFCn#>T5!BaW<+CE>Egi!RJm>8R+ff;2upmq_p4yZ|}kfifqS$"
    "B}Y-W=L`bOWC;zDW+<!e3ZIPQiCjZz}G)M%?YU^^T1GHC;4iOJ%8SVof8VFyd~Blnq-|i}H2BsS>lj;?ojIX|nOxR=gy8K1-"
    "j=Sf9;Q6yF**hS<-eIf@57DKigYhSTL0r3VO=k4^|r9?oZ17Bf!JmW}@58k@n|+N78n4gL+UxhwmaJRFZo6r8NwL3ungQ1tw"
    "4h~#}(Rpc)HMTI{unhZGnGCgo-2jq$QrZ)J1s1hZmfIH`j@6r{v`R3u`orp6WLcG29Kvyi3Qk#Lp1^jyd;j_+TCFh&yri5x)"
    "@%3e@WUdj}eZ_%^PkDP+;0<VgcR=^ppPiv7!3jccweF(Ucdo7}kA9;*eLJzBDodQ!lcHxH2w7}oL9#ujRryN`aoG5VBv(=h="
    "*6j29_8$3!x!YZL^YjIZyf3l4>s`<orA=c%7y>g)nFdlmP-v1JiOH)i?1Er1o+TJ1pd_dMa6$+=uY{<b{AS4d$7Bx(Ss?wll"
    "BU`H()E|&J?VmlB{N4JTG>agnSL@rveV{;Irs4n5+ylM0c3>*Si+Ccn5%{SBCB-wt8Xf!xsIjdE>pf1savLO~bR=e#8iVcV!"
    ";)g?Vcjr2`+QS~ta7i0sdW#lFIWmklRyxeFX!uzrr=&aOly=h9?isDdYb<RG?Y3*+M7qH~zO$dji>rhMU`*fj{SukAd_{(bB"
    "NpbC@|sUx}NEkYR$Rm9U5KW<8e**B^GAd86LqR2^2a!#r?Dk05xD^;`kb;Q_*Y6v^EcmXZBs#M5aK8cbb>vnq|nOQMxzduln"
    "x3CO2V*TP?1kcu85POYrde;2`E^><~<Vo5g)!0~K2UQM6-WfToef-q|3S`M+INUF)8&WyOPs+AvOOl*)lKe3uLOR48#FJ4SP"
    "A4%2B`Q81tupgh2_Gv4-QPJiU0Ze1tQRM*;o+zvhfFT=-n`kfO{@oUK0S00%kRy<Wyq1cz-0~V2A~zr0MKvgb33Rru^*Xm*3"
    "aTI&Rp%u6`d^GfsyLEo`!W)TvS$NWl?+9R1EwIt?S0f`BzVOf1>iP0fe4D1Sx*>$Ci-xxngT5v$*O>Ew#6J+RV50IB^D)S6?"
    "D~_ZmEbgK+xx?I9br+xirJpB8kNs9rZmVf{HAhy!$T>XTp*<V+qw|G1R72+}^jG9vvWT4}a*Ze=sT*l&mIk`PvuRQL4r#Kcc"
    "<g?3?#gQZ^YkC>+{Y}nBrKd>W{SEWB;y`T2QWeQZ~^{4kXDM$jN{>Mp<;Z>y`)dNsXEM)TwE;zphUouvNW|WS@bH@4FGep&j"
    "bw-mqf10JHL2NqR9&rc58Ohc1Id>Gm|L&%;KAGEVbVfK;_n)3WS-rO@I8l1Mgb1u1hxI8ZhW|MEBh%kZ%hzBK<fME{^^X{N("
    "K)g`=?Bc+=CL0wan;{}6*xAM#gqP*NNP~J3w>+?EZ2AX{j-|$D?r{E_42Twv<`5r8X%S`)ZTQp{kUhuWY39YIKWf9j;9;e5P"
    "N<Ravu9MDEa}pOp6&*>qVvNkrt3|<tma3X+b<2PCPmZI$h6oQm))tS{c_BD~@H*hf<Gvj*8Y^BRIQa#sW7!>f5K&?3gjDHM5"
    "XR@*>OMHX;khVv91b%ekOYrQOjQK9JjE1dbzbk5>fLlrVM@!;y?XORT3R*f4W}B<RlmKYhD@Jg5BZ>4hF~a|bo00l}N0vq~~"
    "{;H&zO^Op<scu=$hb+aVS3k5h%HEJC42P2NAl@N*bg<>UlD<6CXGzJ2O^m_=h<2wu{m@mtr|3=dNYXr&7^umr1Uwe%Io9I!S"
    "^9-}-zE!PzXP6llWNmiB81YOb87KdhG1KnJgtbofI*YwX={=zKu)0(cSYO@1$WUTVmhq~N#!He!e8A}nL1#KX7D5rfV@j$01"
    "vtui+_aqug>;i=yh^ahxU!BQdF}PTmX&{%VTXC0Juah#@yJVG)RWL)j4P{)Nfh{NPcIn%I^bpe46M_5Je8c^Cl$A*8!LF(T0"
    "%PvNZ^8ERxzso2u}S+@b9nKP&7k-PkU1`-jV8dG2Vt#ds1@(58Xk1K#nB+RWA2GMg5Q+Pp#p*2fU%O>C_P;XAUVY|E?}p^*f"
    "J-L<RRh;1G|NiMplnNMg8)+*DWlEl#xlGgUL2aD-z#fi$jeru`<%DRiJQ=}tX<5|5mlSLJ)O^zphv*oW-bh+bcEstZb;zb4Q"
    "0=hF$XGA1Ht+vV*5FBx&_X=+A7qygj8;zH0QUu<`x<NMN7d`5~{WN~Rb3wg3o=vC1n5yfCdMv^7jNxa@=#IcCrtp5uvz^wBm"
    "g)o@rBeq{cpyf-^E+$coq(}c<|M%A-!FT)CWzE9xDi9d*?w}Ee{>5oV)+9Q4_9=l2O%%3UN)NIJ(jU=r<vkL7WThbXsnaJx_"
    "D)Ifo0^(HudB8SkE@4+=GXT2qUQ;f4>1lAn&|Dw7bw+{vBSc-!28mG|H}V)A+&<&Mc)TAhYR&_7)NcoAcR9j`#u<Jng?`<we"
    "5YV{B)qD9(G`Z{R!q1{yK-BS1BI0d*d?;{rG%2o)yvBP|>*A01r9%=3~4sqS}~(yM>aUXk^K;_@VI*cGCUrm)YJXzg-?i>t$"
    "EFMeOWPl?fkubMv)6{Im<s75)0$HS&WKYD=1D;uzewyLmJNmIi+<aCOKImW<NRZZaHc&0fw@>m6+p>I*lPD(LmUfA|r56h#I"
    "AKpvR{_+|TMbAQ>YHu=3;0E7tiNiSg}C;{^(b<WJQH{1^mYqy~V({Jg`0-~~~pat@;5A-B`rxKeEU<J$YHXdWCxAJHv)nQ3k"
    "t`o}Qgw`5A;}=%~ZheT7>(dXU1gxjxCjBE=$N?x}JN3tJ-t1cbDg|qSLtlF>H5s3C5NWD}ew%x{F&V2EsXk+c>x)=<BK^NTy"
    "|ws#^#lH+1D%Z5$njgX%EIMl%ZRn6MF1V3s*>+Oew}w>_$)@DkK9N5_In_tY<4n+-hOT<QhohA0j%z}tX>@<vHcteI_d4~)c"
    "&_A`ek|OrP)tqwt#QY<u?C_z2Rs%z*YLaS(V3y4!H*p50HDoGq?<&1pKehb;s^4n{?Y5Zp(c6StI+6-=ZZ@cL&OTZyZyfbcb"
    "h~(Ft?Nb{zXus+qK*-7!Ftnv_=}o<~&;w3GdI__NP@!k0cm8Te49FW3j*jFNzWmBFEH>I*x&TRiAX5NY@2cNIJs<tN*9KdcY"
    "YCsbAqxBW;4v;%iN#eZ~I^_#d=A*A31FP4j}`tw?rTQAIN(01V@+uo&Yb0#d#SA?j~A%^R>-vpb8J0v(yN9Pe_XthM&7w6P9"
    ";8WVH`eE>#ljj)0K4W-J3xZH))&Ih(zi_km!WHq^mWSg%4#TqxW<=#_yVAkYIaY4>g`bJR`orC{=(={MXpUI^bL;=g|D#fb-"
    "M~{K=e1bU1XQ_+4~+HA_1<2-9s57N+lkE"
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
