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
    "c-ri`<x?C^)3&|K;!bdv1ox2OvPgov1$PVX8{8!XN$}wA?z)Qych`jk4YI)&e}DJ$U%XY<Q9U)Ex~8V5tNZM#iPcb($HS(=1"
    "^@tfiVAXC001iB{}v|te_JpuXE*==#B`9A)lig`Wzg_&wRLc^0RSM`R_5m7eE?K0bX?qyFU%jL&(yGqzH4ItC7_@PCB%J|9E"
    "U^U2FkB=U1s>qd$Ow;jpJ5YOvVa2A^=xwp*GXl7h@)I|G>9!3|UbmY{iQ)G1byQvBn5l`M@YW1@^&Cs`;KUs3v2{N=_2Ga0^"
    "%!><}p##q<@pDBh1m2RYy~q*<`pVp_V{xuM+A7rqH50)-FhqoeO*VKx+J;^M9wQBu5dVI0&U<Kw$%<KuG@OC*$yP?WaRWcn0"
    "?7Lz$QM?oRUZD+m{Z*5N43xmN(@o+F{T(kjQlR1p^nDdk#6k4H7xwv0&M{)hYX++_`aK>;-K<Sc{l)Tf91^@^ED9TCeK(haC"
    "Vr1JWn($tj<+yns3eO8PHT`E|S+DDrKLMrxWDc=1aj+>eW1^h1f5l|NL<ghFB^9fq_OaUTu(K)HrcYY<*!kEF3{C}JN*w6)s"
    "4t2f+;p^^pPngp(FU1ioStQMKHP|uRX$(W1q0>&$N%^r|KorB|BhzHn2~!71}3J$CIymI8?mHb6m#iMQ@bWIutu&=X?Q?trK"
    "1r5Hn2EFL+J%)VmXN}gyRA0KSydzYM=kSuGyMYf$U&{3tIBl<PRLF(t^pdEXm<N1RGbmf)0NLGo52va{-kjCVT0SVlv>w7jH"
    "}$?j0$^Kmqg)>1*T?ks>J$jn}IR_3KIa*n|BpD`XkP2`5R?ToF?lJeu}}<x%8@J0>P(iA`|szf%*L?LJ8x0Gwb-vMZD;`$ae"
    "w9SS8L3U-%l>En=_SY8XRQ}YS;dZC<;eU0DSxUIQxcu-L)7)mnd&fi_!7cGSQmrR&%Z<MOIfDhznK+nj&djV#^GMPymBR0w5"
    "v_uKt-d(w}!}H`lP_0#5#ZS_f^uqPE`rzLQl42)WG-p&%VTN@$6dZgOohL955)*T%IRpUIa2}lY>Zndm6d6<iKj)6{64i*6a"
    "Qmkykj`k?teo-XHeJx-0x8^`oZM+t+Igb5F+?mFIk|qDGjekY`w{Ynw(9uJ(aQGo6Q9+9e*%MqJ%lV!1=?@D_`uv#e^0tTc;"
    "!*9^CsL)ma&L2JVLPm_Db^Dg>~1eDE-|(>cY`wyiw2+xK(gvSKv^VH&jZ6XpuitGHwD@?&;M0B=?^HO-j20vdew{s_fr8+WU"
    "KhTV`)6FFvzEoLQNeMCDh0&2{n%Ht3&r{Z``AIfm@)$lAZ>#QZ4_!6lxh($Y&y4o@8e`QRUU5k>yP4Dz}Wqi7BN;cWG*f!|V"
    "W#iAsM9KK^paCmKQiW>47P0KHd2hEt70R)=^JwSBuGggBzP%O5<NXQd(sKbvt6GVtpgnGZuEC9Gy?oGQx6dDcKpxm#TUKxrC"
    "<ky^IY2(bi!q&3Gmorm-Qs1^cN(G@fD_d&amotF5lQIZUbgV-tw?{_7a2#TxLe0!5+|Ty!$u;VxrCYsr+WH+OiHK$?&1IEN!"
    "gaM=I1=M{dQqgh+=S@L(UGjT;wrQ~u_Js$5;t0V*m^{F|M0tKy6DMEv@`1aGaqTw9MK;|Y^2db&N*Z3VRa)bN>S|B_sU{aGb"
    "epLbUGuTM@W6$kZfR}5z>1jgB9a()Es;Z4w}s$Kgb`s4XzGqp5mKnda_uRrX|EYj|~UipZJi-%=F>Vj$b(2e8y-`1CJ5?S|c"
    "ki*};lTD{&iiw9>kR<Zt$yOtL&Tx-lQeCts}Lz#bV*A7T$ReTPVwImc04pik@F=(C+e;pt0wobL<YctAGG6Km4q8Xfm~_Lle"
    "H80WCZQGW;*@vMlRM!lBpA>McNw*wTJE8+UfuKn+aXn0i0G|2?zj9@pRKFWQLoDfstB;NjyR45Lg_D@tS6}F!=<A`t4sWWb~"
    "P80LmHg+UU@%awjtMC9^x5kUC6pWp{&?$<TBZkmkeGDSQBn#V6JT~(B`H(C!Of4`T@XWQ<&9^7?mOM8id4wJucm|>Hs0T5WH"
    "`M}&a!f2gmHZoM|6A#Z=qBFo$C@7Lq7$78Vy!U}hd2Z(I&1E&yTbg9e68#_(8OL}n9uZ&hnd*xC*+HIlK`~kVh_2-ob@X<gd"
    "11g#mjtHdDObvd9ns{UGR^<uuIalUYQ+sR6qBCceRTScYd(EFdN&O>ya}?Unq;PND{qu3DD0K9hML7Ke7f~p|k5%nSqO5_N-"
    "I52{Ev|z~EpKy-%(Te?DDsMd}#lTcQcie1?O&V$WNDBJ;h0G*#$z@A2NhU_J=Tc^T4FRR^#qO{tqdpr!BW+d?CIGI4eC-8@?"
    "od<Bgmi_wty0`FK1o*J>EhO)}rUl@qN0HDE$42u=K)(6z~?lVN_#{Bp&2hfg3N|YnYDp8=d`s%L^QRX8>kma+W@edz&P0?^o"
    "6R&B4<s$-44B6iJZqo%9jx!vAU&{`6qBc@AVIu;M!jsaM9oT^C8~>}RjoaR(%x9j_W%?_D2zqiynqw89MHmVWrg;Yno-&ggs"
    "qKf5fgl`#v5^5&>R|pyFXW^F8x$QXk@)!!>LZ!mX^j2*)=FA``e^+nmyy&Cu3=|#)+{=zBxG<4m84c%{!e+4gu?%KDXBBl>+"
    "vC~pm(~1e_Y7WEMDil%4k4&ly|0sGTvC;f9L(T!cwT)Fh)Gq5S=u62AdW->nC-g^51yp)8Sx^0vspMzIT3_tsWs*{&S*qi-4"
    "KcIWDt5-S3UDBM~D_?wQAv6v9U7y^D_lcCRytjL!VId+pp+f%IdKcvlja7n8N9hDHkQ3E&S(D?B@5*z*_ec1@v1Ph^srT{PG"
    "CSjg1ZAwuImVKHfAYUSMIn=w$Qtpw#H>9M8>!7^|8U8o@rWT1E}^pCWul>O#zpYll}g|33xH>oL!Z+X86tYkXuo0)&MMrf0?"
    "tG`DqenfMvB!f?Hj$38N_~Ei+lGo4Gx1J3<_JAN-6(O8+1}P=+J|+dLNu~EeK)7Il!Kc}uflumYdRL;}4(LUGGj$k6vuK}F!"
    "(WgMb^+4je@GrmrcZs%pd(!Rp82<X`O8LA6+DVD%J@+oz<bx(Z=bOit_35K;63;=J|tnyVM;&(H0KSisy*({ylXAQ_WEU$mL"
    "N9U1R`gjRe0d>^&M3&^izK;>_eqRfzxURuK316Eu8%4I(+dw>|nY+Sn-66z|^p;wPGTH8u7&&gQu;LBDuEXI%Yd8i->}=3pu"
    "fYYie=ce+B172(zyJ-QY)aL|uK<>&Cp@`{{+gT<V!oZ(^Mq>0?wdn^MXIHSIDBah|)oKJW{HdTj=|eiy6eBRp3vF^d=Ap7HG"
    "zxH={Y#|=jTgq!+mgqYv;M{eH6<pRJSMKTS=xgk6}<>|PG{$uRarztYr-0p1laBx$s*iY2}K2OS@o&>-e5rz!QF6rjj_RN~k"
    "w?jg^CN1j?M#cPO!W3G9Z^woMcB~{xck1lQE}{&`HKM-+=6lCu@YR@ga4xRD6@a){kQlA=V0T(Kzn+=VZ8tWTq}@4@Ce5qTM"
    "JSd<tTjA9x`~~c3Y$OJco=DNWk=`bb)co&HMY;F4y2-}8JTB!O;SBGY*cPdT%4>vm+0PMIF~KE#=mr^rAlR?qhX=jpj=T$<T"
    "-!~woj`9bN-m(Nc4pw`Qgi#n0%Z86GqZ@ZK0jSI|@7Sn~${gl)ZG5!^Nu>FvkgC_UY@jBsqsFD!MK}owG!QUFui{rZI^GHRZ"
    "I-+7eE;S0E9AP=)BToihQ4_BJ|fHP~=ln4$2x28nvz@JJHG^*(|~-F1?b?Dr2X%RcO#0}}j#$gK7E-B!O1#UZ!p9cRh*;hZj"
    "AIvtrc$dcnA<J75LCb94^*R1PDG#lBY&0XvEsBXfNTi@y51XLGRqz=z^ju*kDA0DSln{?~)w@-L(*EqSEKLsTA?}i|pdyEK%"
    "6KCF2o3~Qnrej20(|83%yB;}Xq#AJW9iV2ANuFI(w|6ZLZae#<*p|`5CccZ&pGct+<uJFhRZPs_cf&G=n&ih;Sl_y3^-tU%q"
    "~Lu@>j=;R5j@Po9x4Tp$S{;g;%@wz&XMqprM3k!-Hm&a0E3O_I30A6=`fqs{a<=-VcGvQJ>O)9!LZf`<ki&no@!8j_bUQ$#G"
    "hlAdK$x0!`yHvs8(aiTh0frBgJ`??KH8SkltvEb4?ExhEU0)`T7ayS?05}06ZKW{)B@5l)L?q{pZZ=tRdX=MTN(ztWjmh2?M"
    "C7jqBcV5AqYPE2Q}r)c0d6hfqhKNV=!{webp(o%^A_cDZyR`<s0(dZyPJ-XJ7<<UkO$S#I4fueQHtjf(7&ZOG1>b;3gLF%Mp"
    "y^KARQ=;-lZtz5se$fCRzG>$@{eCdg$=LNank;Z{^ytTHohV5|&;?9`jNe)lM{tNU8NMyw>->}5;#6=%jhz=$SR*!PJ+N~T}"
    "{Ut2@g!J*pTJ)&wHsDPan7GC$lN-Cjy?ZWm`0`^kV$chy2l`Zwnk1=`8k93fuYZszbU<Cb9TKELXkK!CH(rx|evAAQR4Ofv+"
    "40o`pr>sT{65jF7P50>=wciEe%ge`O165}vEhwyzArhLNg0fRBW{$r_O>G|GU_#AF_PoCLu+Wn=tI7b)PttniK2_lY3B|CX?"
    "f51?H=EjJm9wkj+L8*h>w>@Qb@@~z0;mWS3EuOviW`Jw0oSx8sCcBY$q#U=|+Pi;&yeQePVi7ym;q$fm@q?4CN8FfL_i7`*y"
    ")E_<IM~e6dxeja<JXo1pK>IRMW3vHw1>PNL6*t)%rp1}56-M-;7OI)62zzEvHc_?JGZ671pQ+X6b14!_h^-BZUOP6jP5l3g2"
    "}8bT!OHqU3P@KCaq7GM5*?F!_!$J9r%!Ox~u+b7qyn1gNC=orOVOeev;Rag5&<z25Z!pM5(%i&gkSS?&`Fh8djf&KB5CU{;O"
    "dS>&#Z#?nn{y;l?-60-j*lKW+hmRV?ZL-4q{rwvf+tg_G<q@-K^*!zy#(WQ<hp){R7v`mS`T6GLh$@@Nbemzff-%_Q{BtYm2"
    "Y2tcAz`nuTb&DR6c@CBKOG`@r+9bT1eW0i@-8UH)yGQBWU;$~sbi|<_P<{}4o~R2JFvv{=usV&M*e7q-(hnzs}4Og3M=%{CA"
    "mo1mkQq@bZnu?bsck#S3z~s-sovKudb#nd4qa|A0^2r@0Gf!xJ+EPUk*$r&j4k_gp^lJ%w}DAiwkt00)hasO3gZ8Y=(N$M-r"
    "8uO#esp-r4Hi@RBMG0|?;rKHx!L&M`tP==)mlB^EMnZL)n~66TE6?hG6!{$)gFyd3qzBAzf=kb@-QtDwvG_m2=y+`ivJ5Xt$"
    "de$Y?BgulASO+%u&XK6{FaemX#&ZhEN0ZYaMPTrf4iTC8hkusz=P3Y}l{MWSk#o~Pry{5jLk${_7gkO)1rD@V_MUpR`5A8LI"
    "7~9)v+&Bw&&hHzsv9IIazwZ)Qhi=>i#L;&hR6U>p^#lkdQUS0dbPB(8K=r$J6K4cWAm@v^OIO?4K}`zKz4gC7)H_na^Ky858"
    "DVz97h-Bzn2y^VAv2I#UW%e(DCy$7h-m#s%ope(W$lSwPH$%xcgUZ_nOhf7_D#sv?xGu^NwP-v7$qZE&sS*o<o#wkC0x^<6H"
    "6a622jobBN`vb(`7+yeKjQ>^vn<>6I5z;kKsO!93V5zrW|JG2-oZ(&u8B+6bRL&z@5pyX#IN7*NFNLjrwifMMa0h<AxJ@Mu*"
    "YLpKk1ZM{%hbI-FG#><U^W_zbglnxtO7c&3)Kd2Out_GIj-GwflG@;oTKZC<g9-YeKOKVJw?|6|cq>mCjD9u1@?06V{>%N|{"
    "O_`Ubr!4_P-^f`|0=E3OJAF8Gcz2&*<!a>EHiJH^3RRP0DC?>GqHN9$53sIj`*}Gl0(pZcJ1}8XU&lY{at#T%pAj%sTkEqfX"
    "p~<;1Zws}6!}L0JQZNNROjgjHp;a~cQ-!`WiU=w(>6@mbN3W*`rylS)vx(<BSP_v|Y*W_4m!n#lw3pZYk7|I|6HwE6QdgXs!"
    "u5WcP|~B!KY*hjupDU+y%>KS!7^8VP|5+uY|#*<-YWd^qTBq{w$TJU%8Aa!1iT1T#{LHTIP0`#t9CUw;zn4BVQLW{Jgc~j4?"
    "Q!cnd;y1?5GY~tX@AC0!yUk6>NKA*nlF=6$vNxMwkgz9a0X9dd=qhQhswr;;_jbxR>?z2frWZxPO}9MB_-qnY$WKp}5+R&P1"
    "2!!`=LNcw;$~CuQI$Qy2<p!sK)CXG?dUXa_zA2GO~;@%BA#yasonH(xa~fl%b^Og_uuov%dex6t?3Ijx5|&G*Mr60Cn1TZrK"
    "=bGD1M_cEC|=-{47kvvWtl(pZJ#hFLKRLEeAH)sw6aA{R)^&`b&YFW<};^GF~Vt~}~ugoo{PsFeQS~>Dy;DU8XC8oIznym?a"
    "UfskV?GX<Dmn#>f%Jv&kyT(Wp4*iu#^0xDVc@Jjeed{Dgql=$oI%m@Zg7gDAFI&>>bX$e$v#rRJ-?-PG(Mz7t=k4BxcV}xGQ"
    "0E0~ST0E?tt{~<ZZFLN2@CAXQxiO+&Ld*Jq7Mgd{celhEf%GiS*76pnibVBKLiL1BBeE+?czK<y}DYye=ZrYa7=|B<Zt`7=s"
    "i5=99!+VDgJ9u+VA-m&Z3-0-)r^Okgh%i;4LpxN?Phf@7qF!RI3V26!y1h!!HsHj(FlLY_hTM@^e?(9f^)ZZpmP2d*&LPNLA"
    "BVm!J`m$0R&NlxBVsza>wJ-m8t~eNT4Lc&E9t^%^t4<yMiJfSPU%@^*bO%M<2_{aTn;p}@MNf6H|vYf=A&ZLLd~=*<j1N|Sc"
    "T7~rx3a9hP<%D~(IIPqjZSuY5fUELLyRa#;Gre++g|K3HQ>B;XFU*cl<fxpZm6Bt}MFKZ;)MT_5GFC!WNeSbd+hIxc*d!rx0"
    "M;|bBE6z>F>G8QqAML?)7>V~*kKY)^^y2N#uJ?{bpNt8PubH_!vyWa5x&KbAd6C)x+0do~wiE-7QGq|CzUJP^ziVI2!%%X~X"
    "Ho%t98tPH*oR~9w=(rZbq`Dy6PH87*pl*J6x?@HdrdI#cAqG(PFMv5(V>asPuxHHa;0x?=g%n)+p-6!kZm{uYCnJpe1xx}a6"
    "3U-s;Df48clD0*2+z$3G;{t6zKKYd64f6#>$4237}-ys(5u`chzb_YgrJl|1cU`+tk++GMr*r7u#SzMe06ZS5!!;%L$2<wG0"
    "+txTnv<2wHi-mxHQcSf7-$3NBz~Sf^Y1$=l+Ux@X)9k2Xu>3Lkku&eG~Ud>$_h>y^Sp6@UW|Nf~LVw>vK&04bu9J^5|~=_Sk"
    "oj?n1`nOoS~vzngJ4S3?brugU7ypBB<ovAq`<NBuzL$3$x@Tt0)u6H}XcH1ibfv#t}Y<qchnc~Wm>sfqsAs{f0uKFa{kGtb;"
    "16^FX&?eG<_N3*HYRN=(kcpxWDE15G4#ipq=t4cx4tBeaS&YFBLJhT(yzSO2JhU)J-&az=G@<?w>^qN@R-dwnRjy!SCT)j%="
    "va8?%(c?${4An|ov@b?+^@99TKN*sh?!!}$m>MnOpP`!Guo(0NcMIttSaKJ93*=0`4nGVJ6RcGe096j7cpcG%Ll05K9oz%pU"
    "YE(DD>WrLT5d2$o=TE0@VJwc5Q5Xifj^*5zL`xTyKARnc&thOx14J7rdDKi09hoQ}E@VnhT?XSLK}5=iS1xouX6!i>m-4Jz4"
    "YG<JY{-zawhNlNJ2GPESG%>;vMH#!|kC9zh`I8(7@~oJ{3zyU~I?`1bZzjjfgG_*mU<gu()u!V8<taj4%W!GG}5;w{aaBi^N"
    "-W&9NDf1ekM&G#CGs~DyDD~eEyBjm%qB~91)I@t5a0p2V-;ZlZHWk~Gl^3Lh5pz-%frtQ|Gsx=C&)}yea(0n=y@3M~D(j;F~"
    "_eh{AG}PqZjr7UE1K!nMs3mj+*OYFDk*{gX@1oZ3ck;`G6I7$#DYTWHrc9rMeSwkxbs!C%xJv(k>;-~I929B>3KK1Ml0oBEf"
    "TAgw&=lbRvTY_|s{O@FpOa}_Rn6cXpNeaKl*p5xZoF!M*#=mj8fc7zG~B=aXkkHv-)hJcrIN&eOZYoAvUyIdiS3f}kRjwbE_"
    "#*T0$qUu8{0Lp3FE$|+icT4sk=r9O{V5w!|1_Pm16x*8+>eCh3p6nPS7tdw>qcYZB86W9!<2ACn^kgow6{Mq^)wB%@DFWNcL"
    "BUU1iFTu%><{kJ^keEqmAk05<b)NvT)iYqrD?W-x>(dE@*{ei^+?6nsaw)9g-4S0<U3(>MS2LpH0n+oZkJ*_#o(aJt74bp@_"
    "(y6|cvlZd0Anc0!Vt<k~RnM3Qp@!##^1D(-PV)QIad@5?zYX{EXLE{`ZXjqEls>$*1uW;+>eh-0q&lpXh(!N^IzU9n!p5u6r"
    "_h{&y&@#HElU0)^YSdXk9XjRI8cu9fiCxHm!A|AEEgIxg3qM*UR7WU(v0A!ZkZV2q2RFDSe<B2mhw7J9m;9{yQ|pR0IgX)!J"
    "%Ui9vJrjly78?v(BT9GAasDK$*!<tKD9LF%b}Od>4`(HZE*Yg`J9{@j8h`x8FN$_oK`~lq)|Mx%lQ}xm%}k-fmJo^Gv^IGBT"
    "F9R(t2HQ3bq@61erw}VIJ43a+?l+2O3hwVp!vtRq9<F9Q9=6iQ($d8-Rk<3tQ|SN?v4pSlj8Rxzc88*>$SsjOC*uK%{Idnq="
    "Dg)l&iAP{w5nYe=-x!qfioXCV;5`=y8z?fbLnFI%%w!=P+I9=k3-2gO~xIh&0gk|YG0lTan#<b-B{4TmB3ZaHs+H1FCuE#%+"
    "8l))x8VR49(D2&z=^dfH5C$AZi-J5qns7XHrAJ?hy0-7#&<1Kf7!F>=M%Z)FbTSu<WI=$o@%tK%-`W;)6K`M1yBu}Ouk*kl8"
    "q)pmy8k&{8xedz#_xGkbm1gn1X{|D{3LEEbd^q&U`+0+A59(p(x(pzR$127PTfl6D!3)Eid=xOZ(^to@U`4EA_=*8rj)eI^k"
    "`kV@FdB?~FS0Kf9?;I>X`c1Ra>8SBE~&ZMe6$`tR5D>Vkg+;6k_kg|oQvq__6zi&?$PKb*vXec5#t-jeM~)QLHpHwYob;EfK"
    "Zk0<ChyPoih5cfBX55N2=~lgxq%a<D|#rLnOIEf?>{Mc)SJN<_hHBbURIB!D9_Yf2X$W<d@O4%jFo8IzLrLe*Lq@QWa%4;SA"
    "hA1CaP0=Euj!V>vsWEgm}$v3ECjqkWi``FIEbcZ0ybC=R~1t_yA%{rqsl2C9H$COx(_VU{)I$eqYz0!Ja@*XHaO9SyEsxvX5"
    "V(vNLYK<H*W&h$hY-``cYEcgx=O?~9zE_qe?t@0sV^9^;C!k@FA;F;xc6u_Z>mTBENb1StIb}VsPG&?-&>gfwAWX2KBw}u4Y"
    "e}vR1qMqLIc|%Pwu2h1q{5m1oHm1tagrAVk2wGl_o?DO;xtoVAe+WJ<jJ<E_+s>b7p?X?;78-Km*0^d{3z7r_$sgGLCRkn;G"
    "EeRZi0EbxTAG;4RI!HjKZrVy4OSD17Xz4=K$C~ingqW}@Y&>C>9ucx?)(r+V$=4=tfi&6V2z%hFT6qR#!>dz&Bw34Z1>mGI^"
    "Q{=-@d8=GdjNoyfXUY^YfeBI`N``h^;?l`BAYum<RBtNz7r-N>+w?BV#PVB=Kd8e%MBj?5LGT&L&a}aCqoe#$YbP3LvbJR{J"
    "J^!U=m95c3V($>!#%F(8o84x3Q<v^XX<?D<u&g7JOxrP5<4ghE}3oNunRK?94gdO0ZC`*#<*TxUXX#&8XusPp~g%#Gx;j(SH"
    ">QzQHqO9&6w_4d_=yDPp;otd_fR-UOc65Ghcx(D6A(TRzIwZQH#usnXn&HC$~PX?wqQ!I`fDR}RIz^7@B-4B`m?u<0Xze^i7"
    ")hy&h*bX~ULTx@{ALeVfKZHD2Ma!ETE9XCaI+PI9JMjv~L0s+zlK&Xu8Nel$V9N}1O-m#hCrdD*lN1pM_Z4abx2mH^f`HAj*"
    "29Z&mx4iikM9485qJB>SREtt4Ug}y)a;IIAwT4ag-cf)0y-<?;7|w#n+<l&acmCnyM4r^fJ1&DLEU;Y`vtfxo;R@IJ|}>7nm"
    "vA}pCSGmkFm`M0{{ykDWilxZy4{x0;52@JOvwHIH<=1rd8^>PZDWBb^*6ah8Qtp=n(wNE}UfU(T!I(4qg6FLTfjDaKbSzH~e"
    "&DLhyL~tt0n4p53E=-0^i*kGdp_h-`4@$vsAi#ci(|vS)2}M|t}2gh^9X*<uUZO{LXcqt#6+;8E9&G9Z{LK{tFk1IO-m^1V&"
    "&!HWnBpS2+4!WRlr70?JU8zn+lhD9pW49lhOj}N+k4({+yJ_ENk3QhuUlg8CtvRB!b+&RB+`HC4dF`RDuX`V;YZpI@$C=(l="
    "K;Zsga&nJ;BC|GySDkX0X7}P>kM)4B*}9iV5=GW#TF-+T{fb1x$iKxiZoYy*N}aL49-lr%lxRO)7hTy%-_F0Gk`AdJ-BNLRD"
    "r1P0V@Scm{%OZ%zVy#M+I~l*{gpOB5EdYPb!HzH6)qUPuz1WnLU!@`i18azv`uT9g5aV^EuYde0xyQH`H=GUCa`Ib7IX#jVl"
    "_JoY)i#LQNf{SVs#sI+3Tti-7@SXiFUaY%GGa180>Mh{dv`07%1g3LEfNW{N2^iEg<x*6N%V=^W*%<fXI!Tqz|HXXk^%|&UW"
    ")fsT0E)k>+nv(0kz-SbI_ceLgh8e$U8Hj1&ga%g+w;Lxf`hdF3XUB`id!^I(|t^3T-OijBWM){X0kfBQlW#O!~`D%7IDhS<d"
    "0iw1y5n>L2Qw??S7`;fnQ9@psYKW?vcapFRG16vQ}GijN2UjG8HYSFnkFC)_adS_%whOBM4Ut;n|7sc;?Jqgn4DGMUc&0uFJ"
    "=V+$J7O`Qhiu?9+O?B3xc;x==hOM^m{M8pcO5P?c5Mb=beh{k?z?m)fix5nnj0J(QMQDhF@K7s^Ps9*&#$PJuaDo!Oe0^%)7"
    "_(ehX15aU32xAC^D-?fOG-IB8pO)y8NlB5tN5Ix+rH_#lXtL>;CIAa+`IkvSQtN&qj9wB(@i6fkj-pl?@##`sn|7j^0YHa<<"
    "vDjVGGTi4{G{1PKs`PYSjh8N4O~wAg`sK?0dEh?GO{O0B2?WQ-TYHnPFh_1>K4N%uOlLLYes-Wf({P6~NJx<ZzvDju?B2@b6"
    "#LAkD3~K)3pJC98f9ejXYU5Vb)?6@P?$(v~yBdTQFXHmmJom+BRc>Gf7RuE#YQ_qX)oi0x_AGL-@tj7zn_Ikc2hQ&lmbqBmr"
    "F(&Ss_z{`|Xvf#JJrMShDO^#lu#_--IO&HaTlR}eN%nVv~myav<G&#Xr><jEB$C#P-c@v#HXtaqg<A4Nal^)$q*Q!szGYvd("
    "`Rv5IXvp)-em{D+VB&`4b($02G<UqYzd&Rd&pT%FW#i!-ZUJhNI@&k^&_tPLbd7*dY&sU8g@Nzn*IP84n(D#r>8aiKEsV`9u"
    "6rUMslx?|cL)laPd|5SZ$_PLi2rM;$IMczSa4W`?^JB(J9K2uYgd%!K6d)z1wXnY8l;(Oq^i4kC%HRcKD9BQ;ZwD%ANL2+Jy"
    "%}~!?I8x4PcdS@z)<;w{jd7y%!42Q{IlhWVo;{i{T&V&jk35OB2Dkh-MZCy~&iX25o#|4=ZW19&N`T8J-f>2UTpA1LIoQuV5"
    "_3B!o+X_SiP9-@W2c2t>Fa9c}2&@!JLPYJyi|S<9j9(?1P@p_M9sy>&!>9sQ9+G)_*<O}4|#GA2s|y1e|Y)3Qg|9Emjp0ZkD"
    "C+0U+G*w@*E>*{nv^v53DU$3+5J>feMf~gyW+6&RyR!CFbexFoR<I8PD<)t6M5NmqA4rd*tg1S<>-#ZHqRHdft^gOL{n>Q@l"
    "lDS8&1HTbj-rvEwj?D?FIxfFG0xI7{I%d<XU1FbtEotCOP8N&TeFB-v%-Z?s<AjH8l3m*Xj_1z^aeVrkV4heJ)K4=n*#P+u)"
    "NTHFkG1}<buQVcS`-z68I9HPO)Bz+9t3NDe2vCXA}3Lam-*egv$*8kJ~p;1!%E9TeBsptz+rAm84BCPLeHQ68+fkr%)n{Wg*"
    ")bU6kMBuk}3lyTKqUhM8P4}ZnB6-7w|;do1jc4J9*k~-bK!0UH8RJ3$*Ci*##z-6g7?Y(`I@(Q&J`zT?+>Li5(;i{#Gd~)qb"
    "Z)yc{q`UnC6XWJY}G2%*oVLO;F*nbXG$k_!?xcUZTUoBc9?c)O7Jhc#y&@t5@Yi@CeQGpvuHSb#T!sWy{VS0{tK#QD4E8Oj("
    "L6G-ImiFaGPO7`Lb^wUCyzH^bvi;e=GkdL(ymro?wr7*JgUp`A}w^OG0bosn>+qjO<5E-oiGjm&{Q7j-N7jI7BS=7d`E++`U"
    "y%8n4RgoK_cfts+`{Oz(P!l{q{{d}$#vA0(Apxnmf6Ma$y=(Jbltod#Q!-^fLA4VJ$)V|1;~Ya!i6>)b%UqqX?Ri5&ZOQ@U0"
    "NaFZW}0K7I540<B(bgJ#=_+vVb~f;qPyYc@U2PRGawmR;6Zux)5iAMGdD83_F}tYnNoG>5ZImaYsDu|+tGb8I9tMMs7oT2jn"
    "Eu~G22gC6E`b<rz=cJ5R~j~@?VyPL<r_>kRDGrl8STc50jZqo3m(36n(T*)Dg+N&%-1fln#aDtxoZvfIpzx7r)W^fV2It5@K"
    "`5L9_Pq9#uf)eNhXqfKMnDWiNWLP8X?qBR0k7H3elHk(E->-cmb73<AqeM@O!u#ZQXoj?89F+g7_qS9HgrnWxL3XAw>qcViU"
    "B4t$_b*S<9YxMkd&whel-e5uXG{Z*;*ow&&anus;F(RX@L0^W+?A(FQ48C9z|56uhb6y0`l2Fd#?m2S1s#6(Sjox?R7hA$Jj"
    "wLzJDilWF8oa{))`~z)ZLOb1ag<xDFu35xU_{(H3U5(;UL);?o+9k50fzjCBF3AB)hwRO8M0kMlp}K&>iv@U@$S*K>f&4_Yr"
    "|?F>6-2?EIh#oA#~#8GQi)r?gN`)z#^=pc0}1!<W;U}oXy#9{dgqRj)eb_*39Nj@B56zK(=&Qv+g=3n<ON>buY_IPMCtcPn("
    "dtpXdDtynPA^Y!6YH<%Oho_Wr&+4!Zqy?z>toWp_QCsAGd||!w|&gl#cifwX4{#RxW{)ysthw1dfNS7{cL8QgzKdejSz};aY"
    "{{RX1JrGjbu=#T7qHn?T}k*4uR#5qfuW@2D^sd#pl!=N@@gMy2Geqx|{Ckh~r#)CNr$5fk~_IQI)lmZC!uN^D1x#Q>(jJoJ6"
    "ML9h2arzfE~^bNWif2V*xNEU966A8eOBQ`5vxPaRNFF3&us1JcxD^1ahhj;1lnq8vDm0x^ws-eeWa!bT3mhyp(Q??Yds45;F"
    "AE$rcj+32K%V}fk0F3OgQ14s3x)|Lz{;8NF%fgj4rS4S0?iIMsYEGE;$?R+^A`A+9szt!uEV@3^RD<lkSn3RG6M(07_dAB5o"
    "WX9}=J)vvcs~+AE3+qufwou1MM=Uu5+vAUQPH%Imm4%et(|C#d%gmgV8>`S&h`U%OQgf2y$@!346f~QFXeCC0sf&`baDRs_B"
    "k>KPP~5@5>g@%Z0+1@t}?m{f2NJEm*q}-YVR)mu1Vf;+yeXFM3{vC>nIb*!CNQcLxsBxjDPjr!!CB0?F^Ys3+ETkfw!455l%"
    "fv*F<kA`PBag_xhhe`_O=U5B}*j1t-q{U_!ru0g!!Jrqvn_%_0?d^+7p3me@GSrt|dYd6B$UJYaKSOLv=ot(y=0D<?YfYvJT"
    "+@@F6|+sqSt57O*qKDw<IjgS=O@7UB|EWqGFN>KL{AgPmgf6wLJ1$n$fH<TrWtcl;@(h?9NND9a2{ByKAjt0EtxE?}~@n{<)"
    "&sB)ITJ(OR0K_co`P{^)m1Z%ES<R}U#4XwusTpMB5x&>C6y;vU=QD0~mup639vO7^n1VfBq^4#4oDB9pTd%i3qJ!yc)&KA>d"
    "F`OX4PPMj1)Rt0^`i9pxr@eXP-YO~baWXDx>S*kr_eMdWqJZ-K>4e$x)IH?H5c^uam@mJxcV#)k(@QKi~E7CGmLv_Vn?BN&l"
    "JEGC{Qa$_PW*T81)duOR(<5T7Jt&&S?uBY#aH4I=Y^G05;yz+U{)M$bZ;S<mthpFEZlK!OA}Ym3Q}Bl*Ox0PQ$}fNp>U#FC*"
    "woZpx{0SHjI&5_dcHUauT?WaQrRzj1DgcQTlMe3&)gUIYd9Y?)yMk~$?@P&&UXD;}w%4)5YlZZT(-2A4kgyt+(FtV5EDcYXi"
    "B=P#BRytV*AnPF*F?QxNVi)0cR$26}_O~~a=ra&XK;6d;>2f!#Z01>R$RVz@vR&B=(GAhVufZLHs>Sp$xr|}NRM!R5;(e2+U"
    "B-UQFb2xWUK$jo@p<?V6>SE0+Cv6(-x@&cOjorIZJ_6YBnxrQ`!%UTLNSF=Ay|QZ}`U55(8o~U9JBs8@QK;0Q_G~%53_}?a("
    "i?o-@?@+hn-~=~CmSf#LcIF-3#8<U+c=EthQY>XIHry08z<UfAVy~sFb)5r%lFkG?M_{D3d_=qyDBn6KIF5ZrRbl%^;3>5on"
    "9(|+h>7w8b6)(lAPo2xV(s4U6-L`k1s2Dp&xY%%bnVlGC~YKC5e0yttK=->x8NUV5m6#lIf;jzbv@y1$xdS6&Axj)BkBu&!S"
    "QXtPLuSO`0b7+9mGF|C6OaIFmTrxi4+aR#?s6zibs+gFt{l+Ye$-;*n{l9DvAbtAaCyiQfS<I^2%~S2WKH2Xs?c_Uvq&5}{_"
    "l^bys@boyN)F&yR?eDC=iZTF?fO0}YfCN1H1@X9e^K$7@ML;shCjkTBh&M%9<sbC~G^Wo3o_CK#CZ!y$A_S_Jz_3~^Ds?kU+"
    "MWr~ZGo*^q^Ln_BNEW-Hd9=e+2X4F+rN>bLUVPx-T=BSj3}ExtAHh+80hAe~Cvo7%h$5;m76Fb=h@qh+Bk4{arzbK*DD1vp6"
    "Fk)*rEoBK(aO0{C(?w>Y#{oE#HS*S^)S!sgC1Jz4Ts-KUvdPZjB=u37W%z!N^`}w3hEV2Oy~agnpix>*73)PnDb|GpndXs!P"
    "vUXpwy0_v5O6VZCmziPTkhuu>`r6m)?5`b~Q~LVu`G`*~*J2>5i>~kkwG5SICo5hi)gv#N${oi0NEMGM&Il=C;UOf1-7?`7+"
    "v1X9sjvVq1Tx+@C*F2<oYuxZbAp@uRknlz~fpyg@a~+$UZy21r}lO9}fO!FPy*#W;9dVxJRXyw8<u?g4fU5gOX}C8J3uF)v2"
    "b^-e7HMjT;!hi|B@6$P3R&lwZdv%5pKa4qtu)J(inY!oir^+PJqlOxU*HLf?tE9(@+qNdN{@{GD9$Xfl8Y5#))k6qidZ_;*~"
    "7m>>qQbbM2hB-d2o&_k!cddS|j)}w5<Ydsx)<ApJ(V=Gm?|-#TUCFw3b<8?pvLw)0Zxtu_UswI3h(Zr;iaqfj7C0+QqB_JG;"
    "{OFGrAsp`C>7aFIvI4#^iD$eX|KknT3aMi)Cd&S2b|xGYsG7h<a5mQ_VTm;HGFCc;`QL^3-k>FU3}`up7MCY!L>M<szLz2u<"
    "}TwPlfS?zmgC$IL1}`G2#v7co}_o*j#pO_zZoP)SJG%7Khf36}0)zCC=uwM9&O^?BV$DF3MUs37hc`J81#7E4H(1cBv%USg_"
    "6TZRPD)));Y?E5WdO&4@^kvT|GBufexp=IZdl0pp)>oNjo;FzKrb0a>PGN!*`=bFVKDM-JU(X8`Y|nfxYmNOUK1jT+Igy6#?"
    "+GZ4#8pIHivaVuO4TACYs9+mx~NGxzjVU}%vWP+V<ltMW!KbeYDDhfNua|80@A+??4?dSIt!4aCe8STJ4ud|W(!WhO?F;M5b"
    "KTt7RKhlcn*lVXz5zQx=d&g}}7FE^#{!^3}A6s<#iL=4q@TZXJ1r<@x%zq`v?{8>=-UvnHNMkpmSu?0azSNs%3J--oDNV`;6"
    "tkuic=48eN8AKrPQYG>n%&bg5w{oVEji!^w*37Lb%7dfS?oeo>!}gWCX5S+wR=M<zq1M**)W^|RHbe9dPxFlHusrJTh@wM*~"
    "}N+c|sKU^Gob>%RVB_oaQ>x3X^IiA~Nhpd1Iaer$=?;Kbws2@7+g<7f;sZ5n<moi>b-1@oYuDNiM015$hv_BA@(B?T2JVzDK"
    "TN(Y^Wl%sds_nk393PSa|HEVwsaD04-7d@Y_En*juqxKHcX@w6h==JcGdO^Q`fMXF`Ggt0o?c^FJvTUUNmFO=eP?30j_r`Uf"
    "5%%>$X;4}-o+IC(-l)_Kke}|qIz8%UzIlTI<+_muQ@B_qTPck65GU9t_c(!XM<*y;im!Zs{9J*={3c|;BbA%I}X5a~(E!@u|"
    "?qJp(k`b0@b>Rk34G^-24=iqiFZcjH3-%!A28YCfslR>W+P*t)i`_eNhSV~#m!&}peQ(Fz(xx7>$SK@{YFK<b+iJn*p2h4MR"
    "TxUF0(1#0&W}bdU!g9Eg_?`XE*ajkRhk+l++qk%OR{aFu|0=7rtC^^t4$xm`@58*J8awN@@)m{UgKp*?P4mTSZTUp<GSUYG8"
    "cX88dA=N$~DIwC{k24#s>fo0sym2Wo|Y1azQ|KMe=%+60*4YL21CH_Xb5x<J%^zH@IAEggvDR5htXRuUgT#$^m%F7R`Tm+V|"
    "kv^YajSzHc3`tMR~PEIHd{K|DPn=_Jt&^Xdg_Nh|2&HpRQ3`ljj+bv?`B1QN*Gf(ajgKLhYfpM14{&cC_o<R0-w#oJ|vDfyY"
    "<9Qz%gcNZi7M$2^wfX}0Bi+KjT&9f;fTQY=t=z8uXcaJ>X<6USEI_MA9!`7g~Az}9=m0Lith9=Cq>qo$&C4d2Jj*h%1lK`!o"
    "P%}JAo*q6f_eqTq*($=I?+-38GEIc<cJxKe3;VD&%4JA=O=^RbC-=&tKh}#WSov(pa}cs&QujO6(a?UBP9Z846ASOu$oV#&`"
    "qkuSV_W3$y0rnwp%zltQUwWZLt9KXJ8)M?ff0w5dkTK5D5#l+Nv*Z*A$;gMU{S9=yH{_M0$?Et%N}L=>VSMlk20|u)w;O=m@"
    "A|1D+)TFi=lh*Tr>8fe>;=nb`CaY8I2pX$ngGet8kP{3yX#x1^JwpEy{kkKz9MEe6gH9nFGLSFs`o+;Hrwe9x2|l)sF74be|"
    "VuhyKFrXbO^o02(FG%D>V*ULs2;rE%HIX_4En=aClvnB<J%#`yvO^Ur|8KO&m_Ueh9ReUY{gxpi<{=yTZsjs;cgBG#|SJB+w"
    "Gsp!_xiBS@?UdAd&Y#Z@4@h!^nVB<k49}xekQaoBHD<{#v^FBsA>U=!K&0{Rw5YT!k5<DWf8t)#gxGdG`L}ZJCy!WZ<B4{Z-"
    "+|I9V+7d}Uj5~Zd49eO<Sk7G|3Od*WX2$bPL?&7z*+N-SHGlYr`pGtg>XWuv{_;#}<bKz~P_5@^U||7P4c=<;p3nDk;Og4U4"
    "9bX&Vx?{rCSxEeO>s>Fr9{(iB(gm39=?-YP#CDx-MLelEZ*uFtwK4&e=qJXA^CedVT3WUTdgl5=7zcL;kQ|>&S6~}@lxH-U`"
    "SW)>TMCneq6-_T=az!DI7xP@`2WsL|vxFM@mP#>|Utwz_W(mS<p{D!NMBnVDEiJ7eem;zV~SAbu!p}%Gc&yG^ozwXGrGaXm-"
    "HEBs=u?)=OM6G1s`^<|+q)k}qcKnaTbE|4$auSMehS#%&5nbtpc~)Qx(65l}c^DKmA|M{FR7oRZlmrqSwu!tlR`*{s3^$7b="
    "#L@!Qa$}y`AOjossf?I63I^W>SYil$7e9{N9(9)aPPwu5tS-~EIXwCN_(f==kiT|ePwSu=LV@@{1R>>tCMKnvTb(%k(T>ZR9"
    "1Kj86flvT?B!DCY%*+eg3Q+qcNW~uOF)E0L0)5vOvfaizB#YsSPIBAGTvM#oQKR94Ro9rf6YXi!v=khzVzGkzkQ^T7_OU(~4"
    "o$@sP9VPh#fF)WL37_V#RMC$|G$}pb`ci+*`E*@4Hz}yiIHLcW9!3U)K2lD9E7pV5FMz8?!c~M0+4X5^CkRbm<}@OYa8N5@l"
    "VGcRK~XK0fue)3Btj>u>e-M)!PHOlpzk}{MVk_?-`+x8%6$d!t4~$02l!FQOFNYy!ddcC@!K8UTxwRqt7S&MA33>=ui7$?kP"
    "){f#g}A7maVE9t)6tQy%>NSuz2W)mDX=bw&?(+&V~97GG9c*FO>ZLILT1<!md?9^?0iSI<>hAMv<LF`R|}*47A&RiTs7Te{q"
    "c)-w*!6Kz2kuNCN^!h1~q;G!bM_4o;=Sg~O0fScqiS?^*coLIXF309R}OjDmMj-OUbtW<$pcCU+mEh~+4JL%V<RF}>O4PR%!"
    "Df{3UIO$}5?qpH-C*geS{mW)Jc3}7M>7$D@-nJYln3)$`<WAA(oif6yX;y^2MDbPDAMrMT{AGaMYQk4FFoa0BRKxsMBt!hgu"
    "L<xY(csxQ{+wU{wbBvZm+kNuP=y&FQoi%&&hg?GoEOB6Un%&yE8x4|m&&koXZnFJZzJ>Zf2GN6S=Y#c{5jPw2@-QO-mYX<mw"
    "2IjK^29Z-(nIhfzy#Ve5wBsL;EPEo#vpHa3|N8`<+<ng>fqF)duPd$`eWPc^<~Sb<Bu}8jP2m8;%a2Qxy;Zu_F}}C~;_JobH"
    "T$co-(qDX`ztu!F9Uj=E+LIXyMG8_a7xBl(4X`p@LpTH!z0hl|{+*N{?e8IAB&$ADiXq$fhZmQO+lO1R)5mMxT=oV3eufZQ_"
    "C%n2_+L1bNim~V64ho&HEh7PFk>@hB93^xREA)d?b0m;siFQw)ALwSOY%B4?k-mx1xo;T3RkZ;P7^fe9lDD1NzR^nEHEz7~4"
    "#QZ!GvWfn4qrysH^sHU4XFR75XJi<@Oj4N&U^g>Y5GM5N2~IMmB#TbI(){_$O@*#W`78UaVS!Q6!$+mMyYwWPf+Nmm?N@E(q"
    "CxpB<b4avp&@8CvG?%&&~kdmbiY3uICZ1WeQB`weNIN0?QhjAsC7tAb%vC&JL4LUu3z>|1G_3D2+`1tL(^(qI8lC8_or!+n^"
    "ovs9PN2Rf+YxaC{MQzow};S!1TO4)qe?<WYhOt-Gz8Ql9?)h6nKW;TS%CH>MRo$J$XyM{9Ic~+-jW9upy~I@OWDkTUYc|N=v"
    "`Mumc0LwBz~5VaidVAG2^KEyU(bIv`OO_J=7hfRG1+;<!sz{`^aa7U^}6e?#OldXI_%@80YXrZ=G`23kUa^OUDQCUWADYwNG"
    "GY*(%Cd4{E#$7{~i#fvY?yV}BE%WS{ePqCxoMOJTh&Mhjx@z%3$meZogVj(1~8C74(jKN{gx_+@^2QV-fm#E}qf|per10S88"
    "sa!J_4n}0fd1BFbMx__@75jQH>3Ju2Dmn@kp%EA<-V%WC_J6%hLIgzOL^TnEcudCA4!%@lau}03I4Smr?_7)ueqwtW*frBc@"
    "=kH@v}}<r(A^16pWr#m9qIN({-f(2lZ>$YqqH)sk}3L1^wi9CvrPM?YNjs)5(T|YN>WCDeu~B&$K&g-LGgBH4HTC|A!sW|$e"
    "Mv+oDgIF#Q3z5c<AJIQ?B!@)jiM)QYS%EVOuUXI#Hpg#f{Ov(Qh+~CbI=x^U}0`YFFJZ^gWwdCZ^R{xSi-9K|#^^Pb{Xr@1E"
    "_Ul26=5fe<uqu7-?t)oJoN(~nFiB<`XVyIT$qWSmE^zm$#zH>-MVsK*|^i5`7D3os+N^7qyH%58w|h8_Lgz$IT9fLe|nTgr)"
    "Ou_c{$J(mf*5d`z|eRzk-yCMfV)##{M-Ywdt+c+fQ+ZFqDJl5(Cfc<rj)3rsxZHGEiXAKSW9g<AMQmJaI$ltD5f4Uk*;mEb4"
    "GT7GpMe5u<_sXo2d#7z&f3Mc{(JXhJdM>FkX&}Lwe7B?~9JxACUeQ^NH^A@k;ts4k!w>%F7UOR}y8b|lX(TGpj?^p&1I%Bzl"
    "hB>X&O4pl=I%=(<HJKNKl9BR*u=A2<Ry}mB<>m(s}#U;6f#ejt`dOoo6x7U(rd9q-DSTQX#*Jqrm~cwl+s6_lth^r8vR?0fD"
    "+w4{cusqxnE57G?raW($-Nvl{I2@gY<1Tdq*9wG%yU`$6CM{$Vn0N2G6-#wry`FFPV*-p0^XQFF%Y}*%iLQM!j-*Saz>Ob10"
    "Gt@0FRycPq2sA#S039R0?VBLc!IeIdr{k9$80W=8uy!Wl(snoT=o!xX2JRGz)%eN!z6nDHDN!n1lClN<1fM)&+`Xtx@)*&fw"
    ")@&_e(OjfLhPshj2xET?wrnYyALkaODxS-kQ!?rcKxH;9|^PbGQAZd$fXbr#o{`U5mvh!@$Y_lnFwC{PY2I>a_KFvK3{3VvS"
    "FpH@Sr|19hd<=2iGi=Vn0Mei>h$o5^dKNmh;;EGRz?tu!keXEyv<d~qPRUP2=}%ls7!+PSw>W^o+uPhurthqTT(t*L;1HP8N"
    "#>|wxiw0FwGVc1;fT>cis={cDV|e3Xwv6hZ?R#wg4Djh)dXGae3l~hS0P5~a$fgL{Ui!{N_`3UZ{VS?Y*M{Q1<zFP)X)4#0y"
    "n=nL2*Y9dy)Hx4=1wC`{>Ar8?K<$?bzXk%?-v_d$ev1;u^0XziV~rCnw?lS|0@VerTofU=p6XQwy2*07C|sm8lvbo53D<#*g"
    "{A*DK0QC=zw_+fD}MespRa1msSm84bHHIaxzE`%UHa1}^8ehC*8F3%q0`rdl+^A5Pzq8HOG`+7-!|#HE?tQoD{8cU`;a!^}0"
    "(zyZ*Ak+7?|FpSxLA<coTpAR!G^dEPoGv_RJZp`Eo!x+&>c7EUP#vg$ojoPpT*ig9#pNmXrDYlV5VSd+sG?^)=QyJ~6jSs$p"
    "B+Ks)Xj0TNmR<{e4|Zz1zD5HVoW6~d24&gK=@kT|RLDDoCgc)3^$zf5`(vN?z=V7t+n{QKB0~L>`$y;j!d4M%NoliyHg}qwy"
    "Mmc6ee4tt!7Bb6m_Hg*twb;2K<}C<5t_IF${#)b9;??M_ik1x`*J~9S<>_eb>CeOHnETJUS~7J?6JW&WZS=zxp23v5l@YkB8"
    "kw>Up_S4cE`%_ju0(WX0`t`i1y`RkVbM&jWNSUI{TW#tXHmQFn2(mG)kjZghI2G^0BUaT@Fg}9ONf}L6&IOGiBx|0|z$O)8l"
    "O<pg$LTvv)7$U<SBge7wpalvNTYMn>+^<i^s_*&Xnawa;M9+?xp-K`D^L%2T)2J{pY-JD=A}>Vcx)O7FZ_h%=ahu0Oi!`2xv"
    "9C~x?eWB;a^e70O(M4Ed_)v6y%!k{ya-><ogBWb6Qtm*$B09`<$zdq^||9%N0ef4RlI+G&F8U661-gU_Ys7?Q>Hvo`4k_8&l"
    "$9yWlKiB5)tHBUjGq>`XBU%NXC`2n7QpjJ5_h*jc$MQoMHMIbuMyV43=vh~-&e0jz8wAjeup6f2wUvS^1R6oOPE(`+Cns>s@"
    "$m1BdA!-(ffM(Bo#*^|;tZ*D<~+P1HH)XEi`eU>VM}3(QpQEOw8a$O<i})2i5jpqSX`lb&>CQvEd%G^;~-l28mf4s_joj`hX"
    "8dPz;PZ=M31Q<1!ovedN+PMy&vC;5-t^46iunnLEC)x8|bfg>(Aul!`G-q+XU*J0%Quf&uQZM&0UzA`Zj<CUL)4Hu|3zRm$r"
    "`Kc_X8^#LnQvtY>zcu$4gGvS8}~fS&Ew)%~MN|4Qn*5WNNc`n~#qKYucNplb<0xKtpVKZ%z>>hBpB6ihr;DNG9ww_A05zuxw"
    "5@|%EU(1~a@cwr`5jnr=Cl&;1%v-e|%OkrH_u^tt|SuAQ3>6h-`eP<%-eWs^i*f0iq3mk>TZQqoD7X+9UKCHYzH6P$R?Hb-R"
    "b`1{P^9^`2M|tkAc|$5)-iNoQj^Sxe5nEcWsp>y!X8yw}-MYiA>5AY>2l2g~``+SyYMB6lGU>hX)_!-Pfp4OUKWtnQ7Wsot`"
    "De$TXzdtPaChSs#Upq+^0-#yF{T`o3834B#dCbQte}2DfYm)m2Lbf;NCyIZ2iR{n@QUmeIP%a}xlQ02R=V&>>QBXSJS|&9sc"
    "EBHktj<WW!nZ!aX&p<pIGh~EgjKu0JHsH(kT`7OD=y*)&fW_2}ov3_GVNnG-QC2DIXtLIEg=~rGOT9q99r=4g!c)D}9Ojy?h"
    "1F$&X-%N}27KmJa~*WCFyEn{GhkjJ7j64Ry6$v6zad69EDRO9vH9p`NH?rhGh%Hb#dWq>2I`IzEYC*IC<5E(uu6vcpeMA5YK"
    "VYUD7|c2I_GmR^Sc4ga=H6Z+9RL0Wx|rQX^S{f@I_3h-j)fQknG_oIn#p@!dXUx8-z9sm^p(`+}0)~s#HE?$Z^x%=^bC}9`U"
    "7=>ekguU56gY_&~TQNHzKpV<z7kC05d?@$=IG*?Lk?IUST(_W_3_7nV#UZupitocGYIouBZXQRc+NRK-K34K6x6^+xbO0c(="
    "_eI@8D<+UX;V%y0I*n>B7X72ZUJ3OC8OKAG6f_~2oK-zt9W+31k8Vz?Gn)`;0Z&tTB$7x>Jt3J*ik&mEnrAGW{sMeS?N0|GB"
    "^O>MUm{Va{HN_hS7SwWH4O^1$5&bSIE_|07x8{9{j9Aschq$^(tP13o-M^ZD>@vW!u^^qQ<seiQo1Q;iuBWu<HUtu#qtX|FH"
    "0u8wCOMjGOL6rIrK$l9m4B+mkc@gF5ueRQNvz4~Njgm#~08sqcl?yq5!iqV>WZQ3%e%{~9`p8<59!$YTO-6e#Q$6znb-*qtq"
    "u%v$T0Nwj#Mz8>i<2{m0WL?_8jW_|okZ3gd|)ooIZg+kYW(S28{pRZ5i<y*#4YT1~Y@iDF(Y;{s$^?sdBD5L&^E_mF@0_a`8"
    "kJDcQ5C;Iv%l8HV;)lek|MBeq;_<d1d^{jp`19&CKB(i;9+#sLoeBm3h)(H@*{xnR+{E*;!`Le_D644OrA{q??ydb6Z%?ja3"
    "kPS5C*T>JhNcguvjF0k(Vqt<z~H9By?EPF@6#*LP!cD7AK8pRF=yjJwDIZr8GNv?2S@MwDz61=fRh<hLqpf%ZSDI_+P~$)>^"
    "z}6?qT;w5BvjDm`?|f;x(9ql61QR0R1d>sB|b{8onv=r`P)bQThf<Pu~i(C(Ue&Ydi1)?yF3+E?A=qGLLNeO8l;UJFY_3Y#B"
    "NR7e(m$0QQpeUvKo+y`5+*EXt-^u5htY@8ExN>%q3kN(#3ZoP=lU<vfsT;j_(I{82LvzkZl)&11wV?@_xhy&k_a{cYS>D8g9"
    "~D0wz~Pla3j$$0y|<g9!2=Q5KDQGcT|nX%d$wEdSt>Pr9NOU1P+;_tEC>nOBDfQLm3|JInts~1K9|6w3tW*X6{;DwmzRJfxG"
    ">Am=~^a(s8SHgsHQC7}kLBP%$H5s*WQDfSfa8UzhXHQddtz7(l%(ql%${<S911z1X5bc_?5Cm{-0V@wQ3KIWbTfiGfuf_d${"
    "5McN!E3@}W<-r_zaH;s-HRuyf>~msXYJw{HT{Rx-SBwhhu#_gSik<$asdI|S+626gMVG<?>l;XKW{g@%AI<xKaU5Zb!|k!-D"
    "7G4JOw#igbcR8#V~9X;daug^{_p@u9)rDda{YaY9Yz{lG#M@wu9kod7VH4%yp%qGte>~{;oNT_oIyJ%)Pv>Jc?XVR{8Ngc!h"
    "le&mJAdPLV>bA~DpqQBpQ+C!8#RWiJl&qkcqZ=HCPc675azY<+ZdmlgiX{R04rphMT|#B~BBPFij37ft-AzZbQc+u=86nOQ<"
    "~ig*zwI#tegRUEq>pRn%24Ne}#wvDVE?U8Gu<6(Enbf)4ewjE&xz*#*7<JarmlCV2tF7fTcU_}k#-nm;wT|6S%`0(*byt9#p"
    "H_aKE$HM6DA5x!gAH?2v23aXEY%2XP&a8#vj&`r!V=CD}*Es{aKv%f0au`ssJF|6q@P7mzZbA*eiW^X?-3oZe06EY0foQ`xP"
    "uaz*@W<|*csz30jWo_P1w|LHDLM$?>n6_Jn#?ci4I%bhI*`0Q7B)gU6JQ=b7P1mw@hbSOpoGTsoxHw0DhjGRekuO6FokF3%V"
    "<{>Qf*;s%4Cv*dfj(PP9zv%-bb(`^COW3kgVpP)bFr~b#GtOok7|Az<B#XUDqg3Xj(oFyKQ`?GK1e)(5e4Ngg{w^VJa4;C0e"
    "cCJTD?ziGNg7X70k5n-$C<fM@CLae`>A+~N`d-Dq~w{=++Zs@R^T{!dgXSL)X`|B^2sH|n~<?ryyE!bZMr;f_b@$kYVhv~xQ"
    "?GG<|9&l6X>i6Na0Vnpe||A)Q%u&wE$BrTJs>zZzO@)+sud@py~(lxw#@UJiU=D0Mobb%@KcMqEQG8XX5^{Y^u`7+SDS8(u8"
    "w9z~wg329uZEY{UfCaO&hpzL{gm3DK=)u2;0)*i#e^R_GpkKQcZbuqkS9)s+gn`C!xY&ji3JnY2;}-CTsRiV>T(3-a0-ZbVu"
    ")6T^KZs8b&*KMjWz5e6NYw<kIvHf7&Rk3k0peoDU4N1A?=6IY-|1f@CKy)w>vbJ2i7%4<lO>DS68$Ah!Se&au>k#1D70*a2U"
    "QDiviF(6fBaZRlZZ|Y&l#fAQczau3Vb>@g&R`^<k}XBmfHyc=+rhnAlLioc15>40f63_-P6#iF%UMCdS`(^BnEr&{axQbdSa"
    ")rjzC*UOiB-_oQ1-Wh3~X#_@&ZyIC$^Z;LmVdopZ|Bp<Z4J@YC)PcKIpfloieVJF7T0mYaF&H{}xkt3}DYdR9(v?e}fe@n^M"
    "*&~6=yw)d;DT_D<EEUToX%<BC`V5Q6Wh5QNp5b|b8z!)4;{XJu@JH0!I44U~*evH3LR&|dbAHG%_K90jPH~Be*yHo=|U70|$"
    "dN<c^p97g4m#N=RRq&I;Bgoe+lk$I_E*~32HH%!mCNSDTs8`R7ycDw2w=hdPWLS{4)0bE=^?&6>X<aX}xatipPa+*HQP6|`q"
    "jnn~TA0K;DlXu0CnKWM#f~0PM?sy^;3svS`sIR;m*hvVN2N_#UD0t(%33?{;aVa}07$H*j5FuXY5*V#Ea;$v&XSAQUz+<9H3"
    ";IzMcWXDOZ=ky?XZKk-~`B&EF4A)|1vj+KT_M#m_LTb{KLFfoOL_Y>qY`R(<$LfKWqMGTaiA+bbs?lUFLfv?~`V)Zk_V4JL3"
    "1DiO+d8e5^VSs3QPo_%|ln(8`GlwPmD-uf@B>t!AsyEpTu?(nxoL0R6TJ?KkjWT8Ct5M$%%2K?Q-?CNRh=d=oXiMD4}oBRA`"
    "iB(Fbb$&Ra^rQYWq#N$(Wq?;CGO`#Cj$g8OEqe=HqP6Wiy>|IV6{mq3+OfKkcg%bUjWJW;mpZ=7F7=3CA#IG%3GA*YqA75`("
    "@jvHBfZ&iWP|IV6=rr-<AvzPz<?4^i3;2oLFv@Kkqm~1q*Q%*R$Eh=!at;Cj$<9|Nn@;s@z?Xh2vp-<Cbis@@71}C5#SRc;6"
    "|B54*#NJ~U5Nv?egi-YmJTwsIZ!-fsf*RC3iJ4RcLZaeV=^{$h3+tAHe7WXufXjc#K(VnF>obUzj^?Ai>@%`Uk7)-g&N*aza"
    "H(@T_zU*iWQWJHeWCxgUrw+_;u@kJl<><m@~_dQs(LtrtdG69O?Cz934~}AbFoe8_HaZnpugv(ZtWT_MtX+7vQu0%$dke>`="
    "dC2YBJwC@xTG)E6W&zJ;u^kkb7UsSrp7JNn$T9Z{b_XDlwZINi$`yD~t!2KuX618^FH|IVSJvm3+A#$(FEgQAVUsm|ihW^|D"
    "15sqJo&H!rw5S<Bm48JM&;Q_w|<-%;W7Z$9E8_GD^9z8s&sBE0+>c`|-|F~*yCo7;Q^*>tozxXYq`%FoBUBe*k$faxtqsoO<"
    "6F7F#!*zBJU%~;rbGr?QQOLFn*j%@{@}H)l^uHx{*t*kwnR-QG9?y1$%oa>Tu(8!t<6gWR>(%;t#w?k-pX_We{<pWo9X}@)7"
    "o?O}K!E*d;y+QrZ&vrA-TXG79^v4hXj9TfK2M0|+%0&^%s9S|Dh`R38JN%O+BT*fVDGi$)XKbvtz9xm5C$+)uuWZnRzu-3nZ"
    "YMg`%xIa0>C(H0-UDd3m&ijVknKb?A(s+?Gz@bd~B62%F;n9D)y(}Tw4eH^;X0^%kMiC9+DOKm(1oTG7kIhH`Dw0Ga>X33ol"
    "TpND1Fj_;$034|(SUsGs3$6A>e5L}zS=`u!1spU#e8yL6FJ7KE*{0HOvmQBilXn(kuceTh@qBp{iY*;T=JagG1LZx9C#bO0c"
    "Z83YO<$_S{-01H+CCo7OH2z<9y$1kO?#C>;s8EBv6wc~U+SE;v_rty8EjJ&c?f^D|r(p&z8Z>XMiTg)EOh5Ga{qwnp%KX>=B"
    "rFD+4=x^PI#4&id19da_e|P0PDDS|ETl`rlDv1jJ&O{qtNdepNijjHzkX^zhDg#&QB}qCPAbHIhR1={0{#e*J=^}&L;;tr(f"
    "y?{RfSVP#$7<qvt@AKHbt@p5Wwu)B(r)!D=_X#XbqxEg45sFNIBlRLZ1cA>wSdf9uG{svkD#~wi~1;W-=Qm^Be^sn+CRASC+"
    "#itC<gr9S2`~G+-G)Cif@a4-XOqHcsS~`@eFklDo4Ks;Z^nKwQQS+&Hzs!qBCU=t5oqud^WuwPfit3^20Q4OGn+iw&n|q19s"
    "2eo@oFe(GYh606nkS2?F%2;WSG#qiluVNWYml4m)lOB3crV6WFhs_?Ou^d{}M8)X`gc{Wulw#p>6K^LQ4@*n>232m=6F*yeq"
    "9I*FHygLi$qUN7q`8vuyvIz%&Wi`z9R)FJT*+W0nV_^PbqL)C3i{sYnM-%5jj{krUA5p4>hsG!DR7p}m&Qn%p=$YTdmQE|ZD"
    "odK3B3fS+yep|`uE0*4lHZTQAj|mUeg2Z#`yD>j`3jhY0mse0DJFdW+?4$UhQW@p81FH^X1Ix56W`J-04ACIp1o{&hiD40-@"
    "G-JycHjINqsMn8e#EKzXE^}S`7)Vd5KT@vz!9s3&s1me8eRCWd64}MqO*V}644n-Im4>$j^P)x75sXB3_E1X%${UT03Zqi#M"
    "|@fPS28>NnN@5r*>xctG~4D0|(6HbQJ@Nf(eN%zlQQKYX?Xb1pKVRe^wXp+T0a5e%n9s8nPPp1?o4-4Lrvl#(3bG4)qWmv(`"
    "3Rhq1yRG#>c(dt6*BFuYA?4d^wtO-LL>%cS<cp>-ANjs1W;x#HlTh&Hncl`8DRt5f&kdr`s#NMi!7305W-AT6E6jjuty0cVL"
    ";v^zj*$^8;-z5L7urr^VO74C5wc%IyYxtW`wTC7bn$et^HMEzCk0IqOzNc#c{wE(s+Fy^{|?tA!pmcP&7ylb|<x9DH;@0t7)"
    "_i2}wtN=KTW+f^{sF$c&R-)fw>kSH|`89NK=#bOK(-+Q1bLy)MN)w$W><AK_Eklo2@3v0jdF2tfO@R?pO*t`RE4pWE(Yf~w0"
    "sv<uxz;c0z?qIgG$@VxbkX9#w)AmSw9!r}<O&x2jKU8)m*AoO-$r$Y#hV6kvb$6{|3uteycf-Ry%m#Q0jtYz#ak(L)^POs`}"
    "FIWC3{}Ioo<DOnNjm`08M;Fr~J#Su~4}O2>3T5qSZ7FW6E`R<CpV~;QK`p`;b8qmI(ydo#KGK^+%G|tmME`5AQ-c1EBl*7G?"
    "p2jZA<C(T3+r+?8(NMg9)V9Q`u;s6A4{d(}%*HN0YC47<EEnpKHvQ)0w+P_XsLIeKsPQa)4YuTKDANt-h0I5?HF<@5sp5YZ7"
    "57bdV^3KG{XiAmeT2j?g8&T1KG@8|JAbe6CPAko=UJ&D(-eYiEKFYc0)EXtNB&}S+APv7`hwr5Kle$!uwi^=JrfE^bJlt@_u"
    "Bf>G;9a>d^RL#OS!~y)?utaI+H7wrLhsaE*v5{->@7X)CFdv`@8+lkrcWv>v_}1xJdp&#KQ{gf3xZY&|R@agNT{y4-X$JrQf"
    "_eO2V;dGKHvz%SSvzWoXk!WsmlhP%l<?XI@PWn<o+mHGw@@|9iK?CUtalfi<e<N|5UH+6qW{;gt&3i#9hlFDr48E?xH8D$y?"
    "7WS+pcH3l2G3Ec=fRng+Jc017md;M`zm*KCmU_pkUVY$A1eQPf;r@8(f8R{_e;1hoV^q)4YXC5cH>d`QaU{2HrU{0ko&i^$$"
    "a|sW1RQbhh{lK>a@aeRTmRg@?A@GS4(_{UY$Xv0DSDU(Y1-;!hOK9Oz;}IyxV%$twxR6o$$+1)6gbQ<FY^vN()S7VEg=iO*A"
    "RevcCN5Ib#}JFZ@o13vBC3$LcI1Fl(58@}y2veI2#OZNTaB>oly|8U{`RRlO3t@r<bSirky$06GXfk5w-yug_gB3hO%thP8%"
    "pA$jzUQwU_7G5E*#($$~()26v5ttnU`aM6nQEBhBs$Uv;6x2-VnP7>MWupumena6Jk;6OelPHZ|tHL6Mn^i#-%DdGow@#=pj"
    "MnkP`5`oBB!Y^<uyRZ=Sr;Dessq%i>YFSI+*=!HK%Du}5@$rl$3QX@PH#yp6dsXne6Cpqpaa-k4nlM`u~SHN*6mgw9}{?1wv"
    "2J<z&4F@-2TRE?&HTMvI8EAGt(3ZjEepwe~_r}pbOBs@s@_25vndQ6h3c8wV_hLNWsB_s)fIqoyPmq=i}%D-`LdGmi+Ke^#a"
    "?&kEcu6*-D`-ZR|igy0^D899HnxU1}X32v^$1n=<uw+<JRz;cS~;V|x^B{5L9ig?c=y)tdqDfld84AfmHGjHy)NO8mZi0N;Z"
    "mE=1a7GwB5ZgM*auHEhuR=7kqC3IZ8soB`%qHU}TAtiqjW;MZ{hjvu*c#hptw8pj@1+xA?I-)JAgGYUm)^HT`w3Yow{UZ?x("
    "_FKPiW+jE*SxEF0@QWJlu1SdHM*F>!6^W;;NSs~(z!WEpcSTy<&E}Zp;qPm+c=b#XP<L&rzdO;RVGT?{5^XSI4!@dxBKFHBY"
    "Vq2(P6sH8cn|6iJ=)@*rPC>hQp#0aksk2$ZUFJl0&%LI&e#m}l7JL)Eel5`+bA_{yn12+?{g<{-eupn7Jj?Ogzb)~eHVNWo|"
    "P+Ltl=OpZEQ!%yl*;1f6?Mwq~Gnu!GCh#-)~EZ#iaxK_4KlV!)TfH{;w8KK(+c!4*rSg>`_yq-M9n)Yknubhy^^1wpkLe7!~"
    "ea3ebIhTe-mt!Zqtr&|nM>w&*Pg8v>WA4E~q5AEl9tHq~D=liHznU;1?Xk$M<EQ5wRQwri^Vk17Xw;ppf*;6=d`Ckh563;D{"
    "$!M|zd2gP3=D{;Rgt^*MNKmw@P5(k48-jccjmd)jBMCSqn07Pe-niG|&Z{t533z(EX+ImAZ9q2aQB^~YVH@I5^Oa<OVKA^JT"
    "Mzsp`Hgt;>g`)*}rg*(V*0Ql9l|rQ=apZU#&(00w8@Wlm`TXt58rreOe#vvUc2@thQBpbQJpA0D|3<!Qn}UB^;J|}I8-W?%>"
    "ni>6v*Kewr`_5;>-iVg(k46A$xb)0fB^TPiO*sdFAH{KZsx0i_b_Kmi0JI{rv$7+_?_DM_%vp4pJ<vbMq6Fivt%GSdA;h_4C"
    "tLo{GMxD*uLm8sbg@>ax=fFuro;Ef8t>PJ2yppQW)Q-eq|`Yf4hh918xaoUO?1=0_<>HuV>9&J@Aj#{p*VVT_t6r?R|Uoc00"
    "P>&19{jN3nYn_bZ~nMIe9^!oyb^70gcF1?eASdq#8)FaSVwE;J5`w^|qBVb#WrPG!{F+?X-8ipJP$r61Gh=jbX<81DZZX6r?"
    "dHIp>al!7Ioq=NE+^IR9(q>G~`Jva*jzcRiBAD>9${Hvb2R({!Yx^_1FC*Zfz*ap{B%+?*YENl}1(90=mT^RtufSI#ompQqn"
    "Go;h~^%~rhXyE`__&3bqjrDD4%>So=I?B!x5uF>}G2yrN<6ZT=__UhAeQ4rgv`iqfU%t4C{<ma}cl21jem&?UeTUCT1`+gr_"
    "WC*+D20-Ke6FzJ|FRR8K1sd3(8ODJ??8P{qFqrK4IGSEE-byXpU#xfgMU5f*M<J{47#nC<>_a~6AXPe`Wg5g<IKdzU{0d9P@"
    "$5jAiyEn!rProA^qcz@()C`d4v_Ii0G^f<__XtN<Oyc$58NX)419~m^L<$3U)F=f4alAQ(B|fPxQo2p`hrtxF43hKh9j}EC<"
    "jTh~ejMlrc~g0%>Kzt1Ha5eEjt22=;oD_}d*5>SHLNa^%2@KWPd@)kbAq4rKM;w@@fz4kyi?*SaEq-c<g#O-EQ~fSA=2@H@L"
    "|cmMIi_qaP8(7kn*-sbNlJTv?Dub9W5w=aU<Jn*RfjzqMXO^cRyxBBCSt?)~;xE?uNkAm6VL|^6lU%7g(aq(@cXW3J?xDJi}"
    "STTXo8a66>Y=?TG6W}M*6fVsS;p7PqW#2Y=Wu|?NxA!wmgpLFx+U+H8U36O%42V|;bczJ_TUplkPt<QY#~|H*`@Y10DM;NfQ"
    "WAP)gPt(?Y-Itpg?n}JzjfIUAX*QY0YG%Fs4CuPU5YQ)D`-11YI}7<rvvu-<5>u|pRMY>aX}vQdCx3DXGuV^%5X?`Oibq_3I"
    "OO!N=jK~-TT(SMRhj7PA`RD**b=|XFZHx_@rfj={$zk?ciVY)SPJf)3_Hc+=Ln?;b97%8MNzPD$b^m1OIsOynmt|Ln60x0lq"
    "1Ybr3Cl0rPlIZ5;K+?NRrbi0Ir?!Hj@^kNA_?D87k0?m!*)n@j+m(x1$7>b=Hwmz)<%u5q330MG0=5a0o{a620Kq`UyWxACr"
    "X7RJ@k`A<}D&H}F(8^zTk2d64fYTHqjfBi1?X%ah`g#G^Y$ujKPA)s^PS^P~-v)R^b8g!t+0*=TwZfVx>7xnFc|H!)S2N10X"
    "Ji&<0C1*lq#-D_5SodL{${?r0OaNW*NJ$CNiLgH!v;C|62CIlJm?Z%5z+d(3C=hl+JfYWkO3WjGlM|R2PvJXW6)(!~!<}FLh"
    "Yfx0Nu~EHH+3=I?cR;6k;6V@P>M=icXz}3&9Edp$%}*k8Ujqi$31A^3s}H=n%f}jw`}P5k%-o~^yO-3_$vHC`x|%?3OFArbF"
    "C9g(*FBh*Lrse2*aa#snij)@h#Nw4b<_0<`$rN7?2xpJJa(o|1tGf{(ZPHSHR3%fO=hG%yE#>%kPqPdHRjtle7PWmKF8{?fV"
    "7*`n{{_R5JiharWQbrr-q<u5Du;9_~~Pe7HV~kDG~quKg!Emp0tRlxWRKU83GsXy93y63$m?Q{bpGOR{DH0E_$3>lK;0`(~{"
    "w#UM&a>=f}qPoY4|r1nioACtC+?ORfC@&X?{I*H$|7g0I7k+=65RZjLwyeWG>o`xcJB84G1CRH}fn!te6*W`O1-lsDNPQb%{"
    "H1TCr@b>v_fIJAO`3?O35z)F}?@+@dH{jjDEhgZ(3n`T0BxbJT!F{sG>Cymz-ql10IdwL{U1;D}8kax?_X6$18|yk(Oerffi"
    "dVS`FWEAN^Su;KOncaY6tcDh=}TC4zxE)}UYH>KN(2AiwEO|H{{!FM<+24%;ZM@{p<y4vQ_?IYJSy7wd}|)RI#ULMhX8c9ZM"
    "w*=uCufHZ%RbV;mJgF&W)<{*c0(r*1h=NR0(5&6SjT*s`L(W25s+Zzk!VU3rhn4%YDPRgOT_Fbq0VAY{bh791HCrKt%><*b="
    "#%WikT3*{tH_rOR;eTN^tYz|LHvela(P8<E8mkT*rGvapbWWr_ppU_jVW7G2>O8T}n}fvs5txEBrlBNp(1`7t0k0bp`Nzi&j"
    "ej#yh%vHTRgTik*hQ8X3&_3knH`ljolEM^3tZz+0xEj$j-4E(=@1-!4l2aVcYfZAZQ{^>Eb{gSKj=EehfX1;_>!$M<0qU_li"
    "bJF2sbd`V8O^6nYndNoSpgwL_;{d>_^{=zgxogQ6y}^Tig#%9ETlcw5Dv73$m{mUR37Yty@?tEU{1%{2Y^=XI(Hg{)jOfu|?"
    "NYxy)WVChBiO6bW^JD(`mKF@tO5Z2zDe>M^>*B%&cwh8f^bcr76buoy-%@{s0R{ly)?j;kU8K%tA+nNJ&X5?U1-ie3^X@p6?"
    "<XrR)ySkcz5c%xC%Lp!a)(XS>LHEVe60GC0V2?AgBvqorG@&|6f4`e^eQT@-}kT1QD%U)^3$AUXMSwZ^E_6p$yw(Jr(-YGtr"
    ";v-EnkLR6iR0-;O%Ii5fmo-;PG}yBq5|=M1at=w7_eI*O+a7jeFof>i@X0taPf!<M#wBciJQ@yvddmuI5$(Q*LuuE@kPyg`x"
    "~0ITR{L^X=eNgCpS0D%5Irj?I*H^3+7r}3uR2!hrf8|&{*v_|nnBYKoLg=^H?Qd9WR{1Eo|X=H@kQ!r_OL2Y+$yM9JzbDt;2"
    "Gx>uz4vy~c_k+Ys1ERe~{AgK#4YXxAu&oIRFQbqzSolV*iWlMvOdk0Tg8D|?$9_U(3fJPdQn%wuWU&_+vt6KGFY9*AkcGd#-"
    "YMWP+PD*Sd=6E7aBd912|#k@pNQ6?vI0hsDqoFv*|*@SD4OK}CDRCm?L@pAiXR04bavB0G;uTPc&m3E8uk4Mg5!{w+fePm*s"
    "iCkKg2_LTE2)e>0qYfn~4A&2sRmDRw4kbq}g8A%n_Kc^?y$F?dW}cGUZ<_ecgTmfK|p028#j^0|NjGbC!><coqCibq|8teP{"
    "<8Y`F)~8pRWh=uwp4`h)88*+aOfmBCgky;wjG{RZ<<<Jr{!N3-r`CLmFOuj_fILo5^MUnT&Me4ZJ*Cel3P*oIDLG|L^L8I7o"
    ";(UM{GzhVX0Htgc0<>CFuCh@2BG-Un34SH=FSHJ{bRGP%ooty~-Y=?^+?8GctSO`n+AaIXp;P2HO-ZMW01V;gEuyj}=+7K)h"
    "lr(F!3ks=Gz_|pU%^bv~$l^StOzjgDrTXh-W_oFp-tz4pH1SPT@y^=CknQ^cwb8P`3Tk-A<M2=A6SzKAz@e!YhI|`a9XH%LC"
    "$0k&70>Oo>AKC7tI5tgM*)CSssGn6Gr%<Y$pXQ>4^gNnAMLEd8>WxpgA2oee}ruu(W7L8U1*8cxXf<#>Rc1ADQ!imWnsv2Aa"
    "s~t_D1=GC}T429E2Y{NH{`7YXWr;AhGRFU;R?|qpw%7ZSPX6O*!ay-(vb_^8UICa6)=07HzmCfxnxb!7CeOG;4=|O8)`x`Ys"
    "4mR+c>kY45<B3WxDz6mSJ{7=mr;0%#ASg<Da_&$X^YvwbI&r;8%3*WZ_jHafjyeb9A{no!x&^?0{)8=j7m33Te3Ci<Ta0^E-"
    "#K8HEH3)f(7?m+}{5<qQ3UFXupz3PqSCZ01qg5j0}uclB4ER>u$BciuiJ=Jynt96=F`F(c*NCXTzMF``c+gj|i=-Vw_RLB%O"
    "3UBMgw<Vgk#7WCHwSb;GGY)tMncYV8DB3U=TB7wLHTrb*Dd!P<Po{{xZy_t3FaV%u%1tU@I0M`@P>w3?x1f+R0f4wfa8wNFl"
    "p20<1_6Mx%mhCq+K@P|Jk(PX!zCN{s3!i;<QzVsQfN&+wB)CBP*VPSpAEOm3aPz#dG;utf*dYF#uU!do#StzivL0#AFd2RdH"
    "1gG-;;<oC$U|XhaQhV5Vx7yCtKi}<zGk9#x1Dh_xuacZrzVYtD@(FH_Ua;%57EW?Ya(cY2J$~oUGaX$7%wOCs4MWu#N95v5W"
    "L(^Q{F-mH?U?d%o-m0CZCR<K2Lw+65*PFuYv~g*n^DcY``UU7N>W%%lJ;ZRd&T+~EmF^r*W){n|(!FDZ;+mrSFebO1mu7Wj!"
    "%`xDW3{XgAt(*F;)kc&g<D`WulZNNJ(``BLrgg`U!;ab8J2b}c-q|*ZFf`vz{HvV>Y8t+L@VD^CxRuC#FyF+DCm*K_s9XJn;"
    "`8&Vcy&f|sZU=C1<Nn@6wDCC;s*t@LFLdw1Ff3Et^v~@Z(QF)rS3Rs#zBkmYfA+lHYTM2y;k}bLn<ZYOz5}#@Kq^>5AY%#GI"
    "`G}e?puQc|5)d*vYJ0nqC*isT=#42M24dY07!VY!U@a6rx#}My6JLQ+lIT^5Iw3k%te=I-4Npn&IR~j`2>DEJ7l&6w4{KDw$"
    "4*Zg(s%o2v{xdkF1L(nJweuNPA~&zgz%dnc}^Vc>o~%p-kUEDcC0SL14l6(X=Goyg;gK;XCabezHD_*@Iu(xYsLdNWmI`;}l"
    "@&V2F1T@Q!WV-<OCskul}CMF=~EK(--+1t6FX>ji9}!N0xr0`==|11}gEL#|;VSF<o;cKnIjb||!!LP~`tU%N5@)_njVQCpy"
    "w8T^M68#>#s?nvAfH1LDLC8!+zCajDH*_>MAZwArE!V`|@F*)<Ls@(XK@CEx`Tq?3=TevU-ATd%mnE>Goff8W`fNN$Ade-1A"
    "`+b&Kw*Qz10D8nV5KKowVnO;)8K7KtFq!u7_D7E4&t)2o;~TX=pzaJ?QAlLtbc%_HHoEOse4qM={}7&>E}%Ilk@hT<O%NZ6V"
    "!m<V-af_g)@1-7S==xFz2c5Vv=wk%$WVVCNYrhKBchGZR%Y=V3mL#au*Tm6qK%0s9?@gPy-2;I*ueLtO1Q$#AsvV?2B1^skS"
    "LyGmIK69dlLnAl3%aZS_}Y~-!H0$Y&u6#$H9=OSU&1miCRYD^Obr0jvT}E;hWdOPfkQco7nh8*QsBuAH|Oi4dFsR1Fx!Zo=S"
    "y<dOM|hRHE&UYW%F>%>Ppk0Cd*;$D{ptq9R(#7#IGFX8*t5uHw1DrKq3y3b4Vpdn8&f5*v>a(WA;gj^9(4;?{QEY=<XJJGs~"
    "vs;;d7bs!*FVCOXV=S>#kUkh}{Nbi5Ff1W^wv;TJ7VG4sFMP<WU5E!o5_=)r|K9jEEg`*QHHMVE1{1!w+w8`wa=9%h`F^gXv"
    "*@``lG~_%mA>D8}pB-=Gr`v2RD%+#mwE#*gNK^E8txI+``qUdr?q1Nf&M^9CIx%5e-qywcY~X0%;cLw*>T~yT@K5v@VgP{Xv"
    "7#!XHg^}kizW`qmPw5>?Pd_}2w*x9;RE|VT?Y)-y-vYHy?`>R6s!XQ@$LpX8^Q-hm4kfChBvQpnabi%_HM`T<~-yk7z7|9qD"
    "R-2-}7Acf7LPkSbo^lF%&g{?RE;T-qk0rdav8Jc!wV|;15@M30uI@?cKT{R=7E?_8;GvSf*%xM`3FGc$PxjQP}S_@rTU|fR-"
    "-&M?{a6^>PIw+OULsiTd;5CcZyY!mc0<D~Q(ro7sZIdb&<ZU2@x<HFgT0@{hB)lYtIsEJh^b*@H;53}QhAn3O&WISXSW4*sD"
    "&hu7FU@bKMt0CHxHy%|JAw2@@DKVJQwa{@m%HVUUA;MWxbUtx>m!qqKU9GUO5;qlCWB2~WA?5*J@OPoSA;ZFA?xovUc_q7zJ"
    "g^!c2hpQGYgFkZ<;6Jd2e|e&fj~M_&k1-XTz$=3baeGk5oaOfn{LLeJp0Ebn%|y`u)O7!DCSx)xeArtkN#B%*g>g7=>H>$3w"
    "eUDAhrd=Q@cJ!jI3rgph>`V>S4l)f>q%jY8olg?)F%pac;3(`D$@aSb<3pu>zRMEJCB+5k7vW9c05@bzpEhN8n&voJf8WF>k"
    "$ojh!CjA01H-t&o9iwuigvD*|You6Va(!gChx|O~@WqFDkoud2R%kA&YF_hMfs3S{9J3{;w_9=&q+L$dY1)i(3OmTLwo30vE"
    "FY;<QS=OTerMkjV?E9Ps}t^Z4KHMVLHt2UML~=n)aonagg!Lj9VW#?Oz9V$^p~uS)C?DWqC@t-oz%xRu`X-i&wS_3u#-zY_p"
    "RwsmJx$mg+W*ZX7u2n7ih%_8<>DaOSBb=@K%F>U#{UDff7<~CsRzc}t7S_7B?K(rPF)8eD;5^ieNFeP*rKs4}=>j0R~d-n5N"
    "qkV@{qB}!<G8)W<$@HHRm#9wPBHT5g<fO1mr7+ZV;LRyKBU{3!?T7H<yh3*TqK)wG5E0R1Xl(D()q7G^yl`X;Lk$N(6&P18Q"
    "qlq(JF0LWHPO0=t!by?8=@EK!~lBRx-~c!7H80oo8MCh1^~}w2T07T02M31*K1W^_TIDq^Agc%S%X&}qRngQyq{K|k+<P-$Y"
    "EHdqFDqjQ41ismQbztD@eHIp%fB6l!<XTdM^aC<AJ_gghc`M9s2XGLd4PgVYU|v@Q7-oFl56i3VdvO3a_uFASVy<8b?G#rzW"
    ">mZQFAr{u%e+ap@A~rrW4DBqm(fY+Ta}Br>MpU%17cX`iCVbs!b&cz2s6gZ{_5(LR-}|9aQ_C%=vx<E1r<JV+A&(D&+Pjo<c"
    "acur$Cg1P@-drY)OFav;S4XMrFkDFUHR9uOs&IIUcVB@v%u{F?^4%i)N*~c!qaZ$9<;UY8JAMX|reKfNy(M*fkJ-|Z7adBZf"
    "i~798^pub1kBs8$JJZ;C{g0^B_PuMo$3;X$Yei|#b?Vp40tbqRvC~iCp`#7hO<=p5hNXkk0g!R^;9oB8R->5>Yy|9hcboO5Y"
    "w*9C2S+V-9OQ_y6m19uP-t2b6-(mFttx`b;dAz56Va(#10x6`>To7hdFu`Ml)49(i7d`nsj!iaQtQ^8o?^k>x5dShlItRS3m"
    ")p3|LFJc?3)~>80wq5zfqVaP)C5O9Uxz_anx?(Gcz;z1A80`hi>Kdj);f`+I7v3s5j5wg{K#a@G1)FwuPdyFl<HJ`$fz0q|Q"
    "vU!=}g5OV!MFf4$q|_3Qw!77O?;8vs}?10ebs_f0y>6vM|<5SWRKFVz?D{Q3k?yC0B~Yy1r$+B}#6K(v<l$Hl_rUHE)+!4%H"
    "Xjc7=nt+M-P*=nc%mwCD&`UC=!0fMLprDs}1xUaCu{_idrV76e&1vZ8}$5d$^sXKU1aRl#m=CS8-KfDejC`3ebu8HDa_0rJ^"
    "_0h)t_<?L0Y5~Z!ER>~<Y*dTJB(>{we;sRfY*>~+Q%VGZZl{xld6QXt;m&|zLO`NTTNCX!R@bjE#drHOpS|1tCHewwD9pgee"
    "|mMGeS(93qBUkMUV(@<J-7Tg^}g&hp5>HrK6EVrzz-B$(-Dc*#p@~XPQ$wn))DsGLO2$u_b2NcB=75eE%RkO!_xZ}MB4^JVI"
    "Bc$c7WlsgDJ<yM^8-Rt*s)0nf<)>5fKrx6E~>0JIC--L&M0mEwri%Wnm)?%WUtb2k@HN>d&+{Jv-BMX7>A~ysc4v67D(yfX="
    "TI4(gQ%*YlgehxwRT_iwTubnzYm<p<^g`koV(hresg;x(-acnfy{sItu^T0?k360J$2s<h*2_>z4ucF8odfrXs1AoQSLH@LP"
    "A0wneuUbk14GgvFxlWMsbJLsOpXo~=c{1%2vHnxnp`1H&SUNDzK`{W(G{t*#vR+%w1e*QK1FdoFyb4AR|_^=uR=cm#=Thr>o"
    "cFL@6x0WQ&uEF+qkmXvu-pqx#ZxICnI$QIao0E@=KAJ*^KwSn19EFFiHg2e2gzCw!0XWIFmS~OP5&)t#DZs*!d+{ID1w4#4T"
    "1rNP|0vBa{%9nt@UBCqpx@%!%F}p(?*De)j_@^8%EI|h3XQtN{^L#Dm@eQeV*!3+Vw=hoSs;*zXtT*~xmf*H*~NdQkK=kbkN"
    "ZwEVYLL#PwT<IwWM8L9Q?0SD>bj3!n(S!VO-E4-r~=KC2c_e>%2EQ^FczX08jw}T@X<Lo=~`3Hu2eoSyWHn#=$?)8nsSG3`8"
    "58C@QEjtkORGb@nixX_v4?xt(qEdLF#?W+MjG3_|bii91d;6F>~iW9&|4G_R|$pnOazAHJ(Fl5=2Xfxn!d!k?8c!+`@g1Fb1"
    "u4~d92DrZO`JB0D`F2Gxw2l4FUFq&0`W>aEV*%*R@l&}|<qZy_GZQ@0e!S*%M-kz%76$@S24(PM>a8J`17yGjm0;Mw}!q7-F"
    "2vAQ+{B3gvFK>(k)dPT>W4lVU2CeIWCeenaDneiZviX21qH|cbF%$UF_`kCdug?>cvli<hGeG|?@xRl~2uKDIdhXJh5~d$xp"
    "=7(*AySy|U1S>;Fb}+Jcnki*e-Ia6{mirS>ktvq+T@hC;6<q>{ze_akLHHp%_)?dw%KiGi<Lr3SNf0JozBiXoyBEqyDdExod"
    "m+gopnOJyYZ~B&u=1-FO@<?NF0zYym|NrVBsdg!9UU3#Q*@&8l|ux&^|2wVs;eYY1iPT73w+&00AYVqC6YT87>3p?w>_95-e"
    "S)NST@mY0E|lHr%#AzHQ^-$u^#t%HxajUi{Aa+c)G}N<_4or3&XMyL5$mbGnAN?ViAeGL6Y8A0^Mmkg}0Qw8fuVu6LXa3~Uf"
    "fwk3?#{PzpMCyVZyk72ODHt(Cly!26X1AMbl#mU1rJt{vw5uLsb63!&r$hNBD`1j!RnY(b2pTW3rO|)H)YkLdct!y3jUQ8OM"
    "TE!9oEt=_H(piZ*GEzZGWwvb!0|L==Y=uK!3!^0m*^-67o1ek!u@ev7|7BhqiHO!YQQWDrrOWWI`LNL6{;4K}2kc3w;rhBgu"
    ")_yNTg!$SX;A>c)Y>tx5<MpVa-A#zShf}GS;}D6{r5bvQy4J0ePR5N#Pg-ZQPIYCQNv5@OL5}CuL7818%nf>F#~{T&8wj@bu"
    "0e9HjAb!QBl4b!?rt}lXYylbpKV=1W2SO_Kk%oczTa!p<ubu<xcOO5I-RRb~$PN7Na>U@!Y~F{v|VwU)wsN3ZoZofH#<kXmd"
    "(!*{6OZ@8dh=Be)t_%uNT_qtZCvO2P8<Bck1O;=zAB18#)@<0ZP<nDx{=oWioePS$^-j!yD-?ur|P51v&XriG7xsaJ5~!EZt"
    "62n!LdX^hYjtqVnEWiP=ei!=D%bO~ACLO~ZR>RQ4VtyN5}VI0(1St}D5y#xPKDFoQ>>ebn&d2z-fh<-^6BK&rVv_}aA%dyPk"
    "8-9R{YeD1%?h_4swN=F%f-xLF{2g8=iHO#b@r%Dly`%MrsqlY+N+YN%2w$M!IAIo8psU??XN<|Hy@;C+*A&1r4~QOz^{a1N8"
    "x8Q6J~;8Arw%}3=D!sLXxb7Ft2RDgpT`^hQ8X8BUC-|l(Wb!@m1w;X6Y3?yzzZ@%xD;8Gr43ha4Y>G##q>q<<r>@_pw}7i0x"
    ")2kfjA)2v#fLRQBhi>r7IUpWMBif-ewVKDIe8LfS{mor)=P7n%gjQ{9XjL<GfxH5v^sJt!mpvH{h@Q{Ww2JnS!r{wuNC`;IE"
    "VJ-@m|JoCL2c?3lIfh8WQ1^xU^z^z9eKlLkG3j<|baw)jgf0}yDa05wPALDj<7>Q%g^xeKy-2LM+6Ct44<1b}G0P{+lG=ZEp"
    "FRt+=4M@#4}cqF_)q7_I;J)@zS0R55$duuZW&~F!jQ`Ork>wFq+UnCO$!a`4rvpPD<GouIob`(4jVWGfc+eT|z;R-*C`$re>"
    "J0muVyRTl0?;sHoX+xK)w~jbCoIZ-n+F6upHp;$@k{<Y*V0oPGuj{`gx3~-cS<yecv)6t6v3r@?V%T6EHVK`!wx@1R@8Dm54"
    "B{noRv0`H0!=AV7XfN1iM!Ci$E!1V^?U}h#=$?)da@3~mqeSGvqhD+-hjXH_v0EjheBYX6fFhNgIQA;P(*P(eM9dI`$jtBmz"
    "#}Arfv3pUb5nG)cNVz0=cRJELZ_%93OTOxV2r!>$6wk=>0drZ#=S*-bo^&b;}vvuD0)a96r*#57#<5%*_VKw=HC)g|edu|B3"
    "6n{@e_1qZIhArE-x$JM2b7|L%Enac+v-K3bMk`|tVM6hj1L5TJqpHCti^KJE*ec)qw6^|@Ps`T@3wMC%MsTB7wPy-)pSzJed"
    "k3}J^%VM4e_#q07q9g05bi^<N$Mmh7vYPUE_Ry$7IY{lt~i+7tqioV?zXaoVK10SWVjdn`mu+_r9%+KM&_EsEu<d%){E)o%~"
    "FQTYKCX1mhd+}@Shwwi~hcV>YXjc_Rq=T%okkYf(=Grbh$zPfYk;h;3&V2Wd$$Ph!UH$>9{MqC0{U`<imVD1dH9r#wSEeRTS"
    "KU9I31KD@0MC**E<D`cuH&oiD&8qBg*Uw)z!A2CMC%YwT%z^H8dt^g<@kN;0sKsU6a~+MFJXcJ`kxuVn#bwlcIe;H*f3{)@4"
    "$Y*n#Op|f9I~`Hi6Om6K71AZ2~3gfke&@*Nl4lYfGY)lcq@Ezg6e(y4D0L(}&P*ur>e@(WA-E?NsBtABPWmcj2m37H&(xX$X"
    "{*jg%CyZD(;CzbMm7Z=dT!A%*02u$@L>h2{OdgY|x?18Yb!!(dPWz^(v*L?HD06TUUN58+7#q5BlJ!g1x{YmF*i<=%kV6Sn~"
    "VNpAH=w2rOes}~XVCC1DUe|+0haaZ~v#se2^Uz%-;(n7CbJe4%~^{h8_aWOr!yVzfEnrD>yZ$6Eth0J|%hbgKKt!o2#63{86"
    "`lF>x>f>S6#&tUjI3Zg2AND>RJ@{>$Jb8FSyrV=!YhAItLv7u4J-&zsP-@#avd~6Z+1M&vxcYjoXZ}r!e{$QpD8L&HjDtYJH"
    "nm^$eSNaU;=pjPPEdJ`FR6<I0R6Vu)jIbj1LKPy+d`tDgWitBo$Utxu{w`GogD_09{5kM<=>o$R)Hrm(YjMqKt(v|%hU(*bv"
    "!*?#7@1Jy|1&`6*5t=9@7C58~Lp7o!t)y_Dcf*$;ZTBMg@?}gLQ$Us3REdYrI$>X|X_5xLhDW;3ynZ9-O>DX2`<FPE6tt)NY"
    "(OdOy%+HUJUPIpJ(oh0*izD*F-q?C2<lYYy5qiEVC5PhcZuiq%<R+h+>m#Mkk-*lcuLTqw5_2u`*YiO;+4@3*vU4Fmz=;B~U"
    "7U)*eU{j9M8O94A25fmCiVnGBrVR`s+wSw1)E8)-F1q4$7s*m+=Ohjh^Ph_HXtEAvwginmk;;D8KqrQWz-s4!W2hg3MIQ_9-"
    "hi0_~?6S9ZtfDiv;*!l3DnKQ-Rg6+e14zsxfRhm@lx*DPH}KJuQ+QuH4S(jrHT!N65v@y^o$94|4?jOXgxyFZ-4sZ-Efkdny"
    "R$d_GS~8f>HVjX%750{#Q{HWPrQ2IueIFw*Y}xaZShV9@oqcHr1}fJ<3U(8cyY2oD9lF#|9iX!KHIF~Z~R^GDh~mw!ofe$2E"
    "vXi(R$`=RTDeE7ys109eaZ`MuZckv=1mUbgF0knhyY+rcPR<I-@<5>$)nkBatc!%%uYS!`v)>Uu?n2gEwuocZ`VWQ77!ODvs"
    ">Nui2A$_V6%vsgzmk?|K56c)PyNEO=6%+566mVvSfK05It19CTlAv!)0CdT<}7`^Ou9>vRbr(Do!!wq*j^jcAG6p`eBDv}$-"
    "mun%7IL8#^=fcZ7^juFw>!IPS3JrhF;_AY#Mc)=_M*y_8;!HLq<d-nY8+eumh0|3hg0F<SJ01_uX581qhkr4-9tS{iD_7)tu"
    "{j0pb5)qw&@}3*ihwLdlEmH(4K&mZ}6SgkN0yp0BcJTt;-FOX(@2=MXfVr*D58qX<AW_#KIq;AB1Ia`QA<zsw%vk~IX^F2kD"
    "|nf>67>_e10L(z5N%{@<}ye`r^&iN<+oms&)K))vLK65>4XLBWEkZSC5qk+N|RqMeSV`|DNZ*7AbxJt*=k4IOQkIflb(lJ$H"
    "$(DG!9xV{K+Ge_+TRdW+yk=yGKNH78IfjaQ}7X+phU>^{?sxc6ctD^9mEnH5LBD_5HDBuH|Q8$G$Zi0O(yNkbFXCi^F(jM8A"
    "mug?Z^irGW?0!oOAK@msB}K>Z*P%&ob1iiplGp5#R9U1~zXFXH!y8~Ew$h{*yd2rCNyCwd9VLPx7vQ@HGwNSinSkkC@nY%P^"
    "_!@`R#FF?zdaEiig8Te1NIsCdchLd-HXQRD?L`3Jrmc5TtFRCBK3x-B9-gc2`SjYwfw(FStr5C_*^ftH2QF2cayy&K`uh*Ov"
    "+M(oZ|B{OS@l1cu0Ka$Vn`mbny;?$l)>aZ3%R<XmxJx$h@6~y{30I+2Jpi=tTeI&J5uIH;*@-p+YgDC&ufadM593NJhhb$SE"
    "9}Lzz}{-Wg9iHXeR1XF<O4U-)#5A#06OWEX3Hu4cd$+7g{cjYmS`6x_RA*z@AN$Wtm**OITlhPB3g1S9a4p%F>Kv=8UFX&ZF"
    "owyh~c`8Z88PR)7!Gz(I8)M&1ymU5+W{Qw{BAY&maKM@420)#WVXoOZ}v7lfqA0P-qDWPp|ctJ`VUT{A+6gA8KxgS3d&a#F~"
    "AVi0JI&2~V_9Si98ghuZk5>@fC7T@cVUTl$#EfjIo%)k#=s4BRt)ve^RwOFCompkIU?EmLuMvG}6?Uj+f&yg)NA@vqf+ysTY"
    "D_2FAK(mP2+bjAwXE>o|SbNKP{FfKy|&8k99T5yzDob8X=Fr9T}nPqOBY3}7O<((_;lDzpfZke{XU*KLWR{7U#T_Zt;+XL5x"
    "#Ek9Z0olTT))(;m;zIcI4*>onY>$XGA)fd|8-*BAa4y8(jnCj(<S?!rq=ki)p8YogfT;5mZDrTdZ??Z*{{LnU04zHblY9^3&"
    "6IU7HGIxO&_**Skr}q|t)PZqPG5jSH-By;y_-Ztr>(H-8ui}PJpM<f3~ydxsA;2Uxlz3pX{ywFP$qR<-xf$24sMfH3;>*^tg"
    "lDa3QP9-4E}Yqql3>u^f<jt&9Vh*c7U%os(2x;!@}{e1K_})XftCclxRcQrph~>iq8hO;$ka{g0xVw96*LM0gD}ls6gP7B0{"
    "UUG_2d%l(TpR?Cd)olX{gU0;SB1l`z4UXokubXh;u7L>sBH1(gRrJ2#8}HSZvpeqhN@V4<MofTCDLL>oq7oBHLf!m~;R>_!@"
    ";mW{E%K^Xv;Kxe;h*MMDLUE6x=Ish(2IQUnmGV{Mi^#+!cmHbyrXPa5d?D%KG&xt~Tx=8JU9pK)ef&Zv2;O)U~v={CN6bsW5"
    "ZFXz@@<>FdDs{PfTVW2*&JSbQcQC3PxIza3qVc+!I0?cH0eWi#Y__Y$nFatl{k6pafZm?U)^D=Oyoh%VkeF9Knkfk@Coq@ta"
    "R@EEI<pV=-t;dU=^Z5^T2Xn&<J9YM0#`U$Tp-dI3LNBp3ngVknA!a}z#RV5836hw8v<76`n!<>04r_HV{-hXn<UygP$CsvTL"
    "(x4=2d_h;p3)e4gb%t;ltGtp#6x>Nn7jh3K2aDcp)I#a7I;X`0@Bu_8=Z_<x%!*lypJBcu;E2`XK6Fh*fWS*Y~zTPha!Zm(N"
    "B3AlVm7zDGI%GrY;y83FoTj&@_HDv6p1;AR9=1~{l%`24~=-i-;&9ld$2zgt8^XU5&7cJH|XACb3VmrSGN+i-mWTLSqoblQ_"
    ";)^$Uo;(cTz1OR&5*g=mAAKd+U{G};~sIVXcOv1;*s*TUp=kQ)}1sXH^0X5ITKM}2)%Oeq;4rh;gb*X_D<VLY0aFLc4hG0ik"
    ">h%MHFcUzXVE|ys<2OkFVBpqFVF%TV-XEQ=DrJ;(5j{?43bY_GF9M|V0`;`Sm+BR~M(n`!!T(<C?-&u$=_&71Z_ZZn^CM$OH"
    "w1Dm3wdel1S+KTtiQfSMr+v@^)9zc1OZlBfwrEnrd@&de#`Cj(ul?8M_2f-TN20N;VZQYe$BrEt%d!7oB}Ynp5F-~ItO@BAl"
    "i@$%F6G<2eLDGMz)B8Z(~F`NSUPoQ6a#1_F$y~cfFPi0CXOM_2G;I0Lj-;VeP-@eYNz=e;i;*&eFvFSt&8;`>=Ds@Th}Z{5p"
    "Orb0H3W>mS$4yGKN{D*4?{P#?0V@q_uW(4W&17}ohw@#6K~fT{^l_hgza30QBCc4)cGfF-{};yn=pv%ZJ6t<ZE8Zu9E+w|WI"
    "1H0l0FIq)Z<4R?7YqLo+^DmVHR{A21)TxDfZ@@!;u7C^KNK*@L?<ufs0s=r^s<+XUVIpbeH-dVwX5pGcxO;DMe;whSBkfo>4"
    "Q(y%+W_xf80$xtxa|`qMO>D*V(ffev>{@)+h=^7tGjWM}elUmUZyCa+Ru=UIiQ%@5qHc@gS%0&ZzfV9qzOKg1rz`AXyPmF?e"
    "cOfP{mC!7gCTm&|AGwAbR>=|4_~WS@tfA=Xy{r0*3#m#L_|rvNDysQqNsogymh#a=jBJSQ>M&XOX#hX%tioantFM09ioA={-"
    ">Dhzt*leXZ-W5uoFVR_pS4m#q}5@no6Q!ONgw1pHcXFvx+y2KLLmD|0b#@*_k7v^+ja2sFCq~c&m6AKUN+_x+xIU6>`cpThp"
    "c-TNg>`zCQNO^e1br=&0&OOZo4Yeb?{(2=C}BiLihG4~jN!YSi%Epn><dE`+Kb0&rx#y$eM27~qA1Xd@G&Dm8i?{>6O=*V;K"
    "0d<z-9EnpC(S}vKX?=x8Ktjml#C-E$dID^c9wc<>Ep1wtzdpfLxo)>?jgE1!6Rj&w;s31Vol?bvxkX885iAlUiZAInSEo<$a"
    "BO>a{8QQ0|@4N;dYu$!RoGh#wfF>|uyJi`b3KT?K!CtDa%>Pc-d+%1Ooq_S7>iCa!`?AXA2?GoK52*MbWkKi}e^1w!(KTd*#"
    "H8@?kCj=xEw}`Y`NIJ8n|z$@1QD$YFBU`_-d6Rp5rLo04B>K_#jr?4v;WC`l;c!@c(1^Ci@U{HYJE>9VW2ZZv(oootDUv8Rk"
    "U!K6wVcPa5D7Yz|>?|d~-c1(Gm(ZJHXbR8GLSP2G8}!Q91avweXG+(FP|_Pzu%4y55K_m#g2i=kSK}w&S6bZRFY((o&$P3($"
    "6Eya%N5$J?hYc}&+2*Y~M?AG1vJGx$YT`UZ&??<9a(0~(aLpkboDG|vfx>PqQCe#&fZxU|?|^jup&Dut7QhngeNa3pT3*YFD"
    "OO4O%s)s_7L_`qrYy@+UY;st|f6UY>wpnlgqhM&ugV$5@q)-%s>@1?5)lc>PlS&tdsc6tGTHGTz3X7Hb0cQ^d7Qc=W}mI#=l"
    "0s8Z}h=6{xC60(ThDRLSfd>9&Y6c%@Iq;?*d92?xBBE}EaW%Z{QhZ1p!85ZZwB{AY0|&MrUDvGTM&+xl>c3o#nSS@LXt@FYY"
    "VYqIxF;KxM0*;hH7q_R3i^6}V0Mc!*MHN<M(<T10oOv+_t3N?nkk8Uye7U>UBElN3*c1_064+6fQU{DFCIjj!g;E^?J4*->v"
    "mkA(il|^T%`*z^$g~_mI5p@Gt#v^(FV8zo%YYMiX9P_{hocQBz6K43e(a@kWxtHEHu*+|5;za>zq9}cFz~r$~#9yn_b}o^{Q"
    "+gzc@aM^JNNNO(El3C<(h0+YGavFktX}iUEL?%C9VUbzD_ez-oVh<clu%;tEoa>pRbjf+9)+PP7IrZb#xIJQFaHm=!)A5G~x"
    "?uH!fJkHgG~yMX#EpmfSVXZ?xj^f;&aJR(|G>Zn!@<148O$^{#CTVTv=Qy0zY$LrP2EVTKgXVyQtw*5>xY0JF8ax?L3bvJ?2"
    "9sEZ+D>0J4R3b1iY&od6C93TJA_M$Lc?jqENAP#sC)E2q2Xd0x07UfI8M)~D)o<1B#Saw6u-$V}SqRMber3mj>RH~DSm2*%3"
    "QqGHdS;j2v!JIf>l7*M-^N+}eqKHJ_htBST@yj-fIyfHu;6<L9EEQ-Yxt74fOiEKLQZ}SkX+|aL}zX-b)|{uT(T#WDDT6^(+"
    "}h6b_o-Ki<HvqGWDJD)J$SeW+()ZI!pk|WC=v0`L0ge3YU;2Sp_}M={Jk>Xa@k!v=HDKd|$l=G+bp72V%k(mC^c8+p^K}0;F"
    "vVH5uTz@K7GIAqxthnwi0Cs}6z_dY6Dw^ph;`nodNIitX3^jQULDHtYyes4fK9qFjvI&eGjaqOTW+#_`f8ac&0ok4gqW?+Ya"
    "wvrf_6`1aladY|7ts>xFcJWN|Yf(-EYv$J@MdnKyJ?=(gJged{YYdjI1Id&F_HWPP3y|4(prZ|S(K?=pdjn*RurpmAh2z0U;"
    "qqXVg^QaSJzCNQx^ULTdmh@;i)9-VJ0f5Elch4lXO=&0~rNb|Juk0ZFW^GI2!Jq}VATT`a;7g4KyvW;*xdRU%m37gs9pW{eh"
    "|UdXtBwjIyL|$`WliC^!y^cE4Z1pTzMVo&IA%sW5DK;%1(Qu6AXzIVTK_&M0B|<0u`2}tR(i~;sKiV4E8y4j14V`Zy6<1y3C"
    "0To)GY~>2ENs*;@R?XXq>ni@J|Am<8_^g&MID1h&G$T73$A375qS^j6FeGrv{h+K%i%w%}jK>3_$CxY~Ry+I*XmD#5dU(0f6"
    "3Fu;qS$o`Q>>2zOm*2NK1U3wY7%SOP5>pe6#yG>{$=m~jJqYH}LCRmnq6@8>n0h|Z1NF7?7}3qLth#5JiLL=8x_EDR|dE}}r"
    "CPHVT78PMv&|2nJP+^7G^_&TQl6IVOM*$)CdN&$eS-*mMv8fVi<w4mTy3Kc8B0olY?>J_}nxe)%$e!ye8KM|c9>?{&(HujiG"
    "<)4WES3H1gRSqS%VKE{kQqh;J+mAkqegy%~^h(mFBlTDW08Xo8IA9lm<fhikJ~t60=q#;JSi0gu&k~7ny{M@Y4OFF%S=Wci0"
    "YMJ<TCIZLOkIG7?)VR0*NNz?ajYSg8Qz80rY7+N<uZ0i7gj@H$hT3_S!40ivFO?aKQL?AJ)Oy<bS6_20EjaJbRapZeYa|-S|"
    "D(x*Ewfb$wa09t{=L09h*Yc3e3L+5#aV#9iMO4@R9a7P`!iKa3VUVSOk!0vk9hz-+EB}t22ikITwMiFl@Q-JPFr|QWEvFjqc"
    "2;L3=L^$OPzp=s?Nm_dZw`Q+kw_0-Wym8Z^LPZF+0h_g#En!$E(PHX7d&ZxI#sD+|Jc9XO~|1N?vX{sT^u<gD|De-WAGP5bd"
    "P>%G?+Y2`sW+?_bgozNdEB!tm%APEG51B7%4ArKNyfRKbv!kyy`2Y2_vfxK3`tM%T_?9A-=_T@7(;{8NqMpjgIR(n(3{d{+O"
    "x~nQHD_up#<9<)0CGc%S!?+5k@UcDn<fqS3<cJ`MwZpTca%kcPe2~9@Z>vn8Q<vK4&juVhdyF#zvU;3Sp?`^t{knEC$5Qycr"
    "2*^7Qmb6gkL<Zmnep2$b1=5PmH8kg0x8hq5{*oN$NeV0RGY{9#bppPs<q$Ib=*LLAc%Cx%SaHrk}+8ty%itl&*B^MRg^m%Ri"
    "5ce(=UkhTLyci0}yryNID4;Z|lnnL<Dzg2|(O&AzBfOj;SdJu#NxtJ&E>=oIwaRnG`q&50xPYr6G<#yD*8L>kMP&*n>3269l"
    "n3iU;M`!JF|w<s?`G=*&yqLUxFUu_LAOA6A7KN3J!d*+y|(I+hsEu+A9(n>yOrV|3KJPj@`9j)SGA6EFdfOSIHD&n21}fiKk"
    "O@%QZpJ~LHOb^ZX((|An~#HL_;u>?WvDkfQd_Gx@UG;kbkG~zA*(fmV4nxlyuOHS~ZUfNF@qc)4Y)cu^@KG%tkt#v5kR#82_"
    "?e<d9)8^c$4h`TaN*5QiJerdN^|JzR8=Ao9M?75liZ{vXp{usMVHQCU+lzhIyiR^*UlzxzXV97yU~|BwJcl7A^cMiam+-Y-N"
    "g~ZXRRN#rhe~MHmd+b2?7?_B_owJ4r)JTP(mjaEv~(7PfHYZjEYd~bz$xM3EcftrS;t4G&f@$1J^0L=T7gnh6v&}MV>Lk#o5"
    "G-tzyv{T8fA&n75J_E1$<|21QWiCDpOeirase}sF|X4ZF8zNbpin-GCfg{4H#jP2?*=4&ZRzUGerOw6OK+>z*Jl?8U7iBJ)>"
    "g*K_wC>eO%xkN>v9_IUoObb{6k-4&%bpU#9V%Ac#fDRxgo<uDlZ;p1udSW=be^IEDiUPGD;Iqki>K+q&M?eu;4_R=!udCMv^"
    "8>a4L|)%<1Jyvx*6T_0AkZSgp7v|J*ipE1Zl9VgW!L12~#I4;|`uhqc2^0%Qg`8d#cLVu9Mhb0#QJj}BS@^T(68mkF{*idMY"
    "A&A`!8<mCe+wmXS^SGWBa2VN0u{kt0yKRe2vQRhWF*HK^lmNu*U+eZ+e{V+Mh;5|<AkElcN?gIzpsGo^j3=TEDd4#hZi(rVf"
    "Uk9Gcyr}OJoV7$fcbMY?h^#Dfa;+;<gef~zNIvTv5t#!;Ha=Y%DPn@*9I+fET?ZgJcSNng%c~7+9G(#OfqYnTP|r%;0=-yST"
    "=f$7rKKE=c;9EH!(mR29@$Z10Uz$<8iNvFLdhoL;o<)J`4CYAef@Dm>`HPfd(If*zII4mOoi(;fM00xKid(Rg=CbsvI_>GpX"
    "sxilOC1N4C-EwAC2^dVMU_0nqFFu->GM{)_|J3BXiDPNku$P5}T~GC-S4opL%n>Y!DS_{`Z0c;9>x!PF$cd_d08J%Au~JI;t"
    "aeBCSXhpne@1<NDf;Mfzm$ORl+8UKn5gV*+v$vQwF!XyAC_7^(<!g0q*W`)_UV;6|Kt}x?$s}24%;=2DZYpx>%0w&Q>#y<-%"
    "&3*j8`8mA1bt%w34v1+$%naII5CpNyph1Wr2q1sE{FCx|d{br!heZ~gIniWGr6o%30B{mI0O1I-WU>DeBh4Z+I$K3~CyD@?W"
    "i%q;1h6O2iPw8X1AwOIqmWT`xdP2VppbR7V?a$r+bTNc0OzHLY>8uN$iWwCbNF$25zZWY5a>+OJ%Au~E4(VRrTutkehzOO8^"
    "vDVMbH37l*+$QD*xPSX)1Iry9flhs%ckao9GkGkJazfJ~TPDZS%5seSAy?mVoC-)SLk4xsSVBb^K$efzQkh0l|4dQpBGih{1"
    "p+e*{4Qe6K9;e--|__Xu9Xix@>Vv^nGGO|sUL?;Z!hVx<S0;Q-LfS?#5IHb!*Q|D!0B7YI0vMPk%Ux117OX-o&Gy8(u(4vxt"
    "V{(5o>A8nV=n0%J*0|c?#U_)|v|4q8R-_6+~Mm-lJfs3keLc?Ds#xXNWIALwO&Ny12|FVcEtX`Kb4!GV9fHaT8a!RQB-DH;8"
    "c0jK}!c+Nj4lv7o+}~;7?sg6D&s-02{xLwjNMkHP5Ca7bN(4b@oS|#vdz=}3e`y@!Z5QJ_+nbVZ6rQyRl<Mcq5|Qauj4=J?U"
    "V}0+C5?EyueD;ODgH?o6*pX>RyOt6CB&;DF-I*-%_Qndypc<k^A5a%#3yFY<0HeD;P?Yy7?dMU5X2^M@y*{U|8wIhjC(E|k0"
    "Bp03`sXM{(A*r!Z$=+N4oS4@u#ztExuy<t)P!nx<{ZeS&CpgChRu2w&T^(Jut^Y-yZ_hn838-;|0;iy{$UlTeuDLlTQGRGpf"
    "BGjjaSh3>-8t5d;xa-1p7$kHs^1U8af&&qYSHd@>`2R2t4Q5;`(^0BbaW2YqBpi{i&AvFo6Lu-5Jd3$hdXMC8=zinJX~w}5%"
    "q$6O`Aqd^n@^~@YTIjaP}C{jfbI~F!BbK^(wGuhL4!|*WnHZs@~WFUPYBUsn?*A4(nhoq;~pPhxYMiIX?(=T%0FB2h=LDesT"
    "p=TGPEGvb|v{E`ND$~jjbX&ugD=@`;Jmxj=#ZC<$Z5{-g#{rxll)D%~5X1ta**!rJ1kjj%8ec3maa*>CA~=TC<R=#YvnG5io"
    "cpbq<*s`xrdZ1{{NrWUx{X#ue>GhYVp;0$FExh^e4zqYXto6IsFv{Bi>r9m<RpIV!p*WZ_q^&$O_NuG*hyse$>QiW_%GELaY"
    "ue1rssSV1c#6kE*M-B<Tg&i)s$^5#)g!1CACqO@nPDjn>6xGtHS6h{kkfHh|1lxGeqhXf37}LGBmls1;@uJbns}iiJ$Oq0cM"
    "^7*l9BU34$1SXp%<|L@&7;<X=?lc)45F(V-%g(z8nWS1(4b=G5d!S(0pvN0<#?|1#?Mm%XmlM8#4Z0P)k-w)M*Z=t*U@8#ze"
    "*R$ofYsBQrnfr*g}9_ZBZX7?r>eflftv`*0dfgrX$Wtl4<#yg5L_=){{;I;s-E-@@!xQyx1JuB7k$lz7PV~w5uZy20mL6tSB"
    "_Jc~GHtbZ>r^dg>d72XTXJMI?61-LaXG3ZK(7&Kc-PG$+poRb)<p@xT{oKcw+ckX6Z{knt7X$6{0GkISwOJ(yV(_610D>TTX"
    "}^fS53(5LE{cq!Xd)omdQ46bmtZwf>y@zXb)_4~R<y8+%U7+5unCR{)!B<<R8<57E@meKTv5#9f4h(4FUJLbH}evC;pqK?d_"
    ")O?Sb}SA`zE~e?EQFUZVZ)Kj-uf3e2Gdfqs9Cb%tXc01p9i7fAd^IYh>U^WCQew4JJ#v!e6SuP3@`@Pz@a+s>Lc-s;YW_mCw"
    "5^CF+jAQPIZ#tIy&?!DaC0j{)KtfO~+T%qfB(wg)u1BM4$4?$z?W)j523b`+N(r@8^6;6#}KI`Y553E*apG=n~(v31A*U@Or"
    "8u=T6VI_#2wXyPv<+FWAZ2_TC=t0=UX)jKm+<M`9}0qxU+eq;%Pu*eTxBrm?^6?p&IyYbR&8QCVoKGogDv$BS?kZUCDs<Yq|"
    "weeBvdvBsqG@z`jg8wRrQ}>fkCY;pCEU2F65+b*;lh!&8jG-L_sPh0dSKy0{dAu#S39ZJnK=Z^viu_%4`Bn0TXP+9l?IH+ba"
    "G(K#Acz!(Wq$Y;e9CzNugFy}5;&-;WKqt6U=<F4ek0C;Xwxnp*)~E1ut%#QD%sGJdNYA%Kp=Evs|A6K5(iY`09jz~coxTH8-"
    "H}>9DcKwftWkK9giwO3^Xpv(noDwzgwlfx5y9Wr|><)qnMiwAe+E`C!@1|if-h{RhTlaI5=)Q0J>s&gXsXUvKE$w>0}eHpz8"
    "pQ4}!I$(O5Yd_y}?m$I!ulnxDc)=Jx@?`N3-KmpLf&xiSj53`R$*0B_;Brzm@iAc+19&HzRb#9+ZMl0P%t#&_mMaIwr{LS~T"
    "V4iF>_cDa5IfV5>6TbJB|k!>Yi09Lf#6)vBeJ&<yMP0FsR|5ua#=;Q@LfODqPUmYH`cT_#Cxx_T{Q5<rRtup-e>=fSK9Ky`e"
    "2k4$b5ChC*FZ&+(v6%;O4KHA7%Etj@Fv479BBR}wb?u3m$Jp6M1L^>X$Kc3mkt|bKc6S<8-e$eWWIS+ahiHolOz{ABH*0t^y"
    "B*%yuPcGSff7mOdv1|$^-tqa#=&1ryc!~y#)%V;pjjIr2L(Y80|yNd1VQv+RI=)o_;BV${PWx}E=3NRAQDGX#-h#ySTH;6TI"
    "T%(^y2J+MU3c`I03e+CP0!EwHNG{fsw2aSWI~^;X$xPw3N^llbGYGBtQZc;6cBE&zzmbXHK8lPDhm>b_L~&uaiIJP2szSN3g"
    "G*0c$V}1r7>oypHU3J#6%d;CEdC3&#Yxj5c~pj8z+|9mx7-ETnsr6Xgx@I!snn_`VJV<`H0$`*_T6;;v2&za=gM>MsD^46x4"
    "G8mpza=SrEIxEdd-J&act$~ao@;7PxUj~1@Msgqxa=u8d7b`k_Jn9u-05JVr!64?rd_P-qevHb{cW<?AO2YK#V-IuI-a<-1q"
    "^4(ktu$mTs-6yTT(@siK04rL?)BxLP%}0S*9$?b-Q5ka3$qW4Fb5nTV+$dVJr_t_^;x$2R6?rxyS+<PPORvHQ{O53MwuDOC!"
    "Enn#-s8x{!mW{kYYgSM&b{CG&}Y0}sRLj`u^j;Rc87}ou}{EwJ@jFSoYH3hjV6i~{1=!NKIXZ=3DLpV+jaabyB>c1d7yI!5Q"
    "9<c?+jfb_Z_$nKRNStytG`xK9&J*Gu@%!i=BD=VtoXyxrYa0TM2>~T&N2GK@feYF?4E}J^hHhyIjL?&cSuOfP7p_X{Aptm~J"
    "d1%D)&(y@d@(7lMJK-wvlKd7I@D%f_7o)Wnz}CmDv@4lbPakuPxk_|P8QoUP&eNAAF>WA{jq6M!JLgrGEmpDE7c`}i4*I91H"
    "g2o#i&D*(60$mPA|KsL+PUNLF^=1l`Y!tmD>OpxHQgTitWB%PdATib>RP-6iuxIXUhH1Lkht(csB2nfD9P$GZDi@#ZZxbr0L"
    "Xg!UI{Ftg!(CrUvfq={cPqjU?n&-B9GYNv&1`N!=Mi9iHGA4QTI(#B`0^gLYV#srl2iGm+Ry_|~uR40R%SS!7LV<(@DY+&xm"
    "UvxFtaZbO@CojO2E=*aL(K_LtvV=GIX-y&G=9BSfj@V4peD)$vD3-!xk3IxaUS1V9nuQ_q6tjEg=3=rDoZQQ)M5*b<^|u@#n"
    "S%={i`jteXm>jF}t`yhxQYThIRgGm+BB`LV#z0XZ$w)Yhwx@p5710ld9H#0Cu_}l_G2P$PM^Sb`;-Gt|H&!@Ea0U;lLFPK9`"
    "uw1o%p)h98{H0p1e>u-ybf3_3JW5CpNrC{dBBH{8U<-+(`F-H$7g$GFU(q~k2HT=FVLpFSD^D_X~5FZKy-?W9p}U4#Rp2WnE"
    ">)A!q?&N9FkajL9V#by$@5=Ul;;qPW=@UGl#IQhZ@K>g{RbaV+~u&5l6U<JG-SI1lTjo>no!~9%;36?=Ya0DG0wrgE5wk9)u"
    "l1_kr#{YKsI!8i<mIEL({v#)daW+R;O&$b1Cbi+;;sPfF4_|4{<7eefkoBhk|12Q3UgR$~e2E;LxE{Y$dl;`PR<U1Zz&d~zw"
    "Q($PuFrWpBXL(y!=JTh@TW5YAO^v4K@h~CLjwgt5X*yKF5f%cz_;f|a9Ct@v}u8gvh{0mvAT^M!TL>LEyH%FjC^Zx0L1U_)("
    "D5yvzFR-lujJB4U~WoQSWeu*}%hj$HU05i{r9`|2Z{{-@qQU&px<QjxIqA4*7l39lip;pFNJ(ja1>Z7;+7U13ZhSC$!ifQ^v"
    "m^39#xGf0m&i*Y6wbmUz+Q1uP~a+VAzmq8mOMq-8Wjj!QjuMMIekRsB0mqRj<n5#Zit9bfYs_yhkk$l9@iXziCByIdYPbS>U"
    ";?moP_Sizwni?NQ2tjADPS$CYnL!eu?210@rfj^!<ho5f@1Fc85eESK4*dEYeK@h|;8I!q@TkvuBIeep2#bMPfenA_h<Os9M"
    "?0|JK{_TYllh&Ow^4SLb0^(x+^!Lg{JFl*4R__Oxry`?51|nR7GhI772_J<jhbT$>U40fm<Beka*nK<Y2ouEC!^h=Yhh6;Wo"
    ">5%o<}ouDpyYE@;2@{Ijjn3XD#Gum>dvCRvn~(+*0u2xLFC?Z^pDjJz_38jZ@D6Y1M*dmHzO%js5Uo1g9+4msPO-y-@&7uCf"
    "+HJz^gqE(XIn50Ob7E?M(ilJaXkr@yoOK<EBgz6T(HQ<Dlqso$9a8vu@QY(S}5u3C!~V&#*S$z^_2<)K>tpnDT#FsRazk$s!"
    "11t056Uf*_WK!vnNy&*SrzCN6UHbOd{mL54Yf+WldPwoHq$jLd;#=0VTu*J+-!DG{uVW|>(SMj%Y4I7(FHUq7XyjLPW~8W}}"
    "6a3sUoIS;jVfbX0b!5zGf-)iiWpE*bE0tsSmU)_pyhYsU6%JX>Jz6s3F2AH1nF&wxUb~3R+7#jN47uh%jtij7T0Mv8Ng3sBi"
    "n*SxlN>@Tp8&i|jq<#y`vp{z<sXGG4{5HPSn#TvG_5%1)cLTOW*H9VdMI5;1Hhjo?61U?SsLnf14JZi*Wx-M4R!N5l9XaZBD"
    "Tl^XCcuBG&7d~-=n}?%TFXa*Aa*m`erih)#AY%gnLCQZM{dHeHy*@mP{AQ3KWtJi6_Ih+wL2vOX=*bQqH~Li*e#-9pSIXit6"
    "6lp4K7vK79;pFydB2T6Q4h>^#MFC^@Q{S_c1Z*qEnRk>!~TcTaIG>xd-SzLl7&#;lncERUEkN4t&CY7`JANXxAmO9j2rHSuk"
    "X{ZP4}kirJ1?+sI!~4zSX(WIfue7-yrEg`|!4WUJC>x!Az(b$006jSh}mSq<t>ty?N|hSCfV@FF_+YNLi<lUJZV`6PhTTRJY"
    "er6Y1^{2Kf=dm67Fsv_Irn6C#Y1svnTg$RHQH~SvlUn2p-`5-_&FYvd)41T&+MPvRriLep`u_9<<Mi9gbDa%rE7$bXb#m8Gu"
    ";8Ns}mrU277NZ{)wOleSnZmhQBDGwTa270QzPS+&fMu5}3|L>mt=J6HJKIhXj>H4&P*Ju3yv)!kNIc><@ROx$ar~LDqceGOK"
    "n@x~3^JoKS2>6u&z#3UuMXi7mPN7S!0iA-+(ph9{!SGAUo4Wo5`X5Ve>?l=3-n};S<A^@F~4~Eq(@mB{t|OCK*y0d$2>glHS"
    "zg&9UrTW0i74O&RBN$%Y0=5hYnwkA3S$AUR$Z)0Lx-HaNv3juFtf%E~Lt;Q*Veeuj1W}(*GTShhziao4pbzkN*vgs{}!;7#c"
    "VTf>;G*33mi6e+X~S9>q;=9v3-T?3EdeOBdtFAg3oXCUT+P6Nhoqho7FF&dHQ?%VEHjl5@CBW~FJ3$sX9togv3_%#`TVZXUt"
    "a;ouBG5WrET0S-ea2+(8#EDvN#4Ch@RpE`dYACVQ*PCT{MTTBpxOJ!K@KXNO6t^Pb-mMvk-bCGE?2oET8j=bw?BTxt#X>s;("
    "sxEhU+wyOt(kHNz(|a-#EQ3E>)GF^cj^jw@z(o9oKuwALae*Ks@rc*NJ<S^4%dds6qW*Gz%Z&fb$W?OB;g{eSFMJg@7m7ISW"
    "C0Jz`V6^%V^|etsQppctqUXPY9NH()fx*hnf38E^%?x^R1UziTYeS^g4ll0z(Eki+HfW$GJ7#JdL`c5x)(3WmT;J5b)Vvr<T"
    "^6|lBaZ{ifS~IwfrosRqbYiE_4*E+5w>7zest(l8^(S_gIGKu{$?6>AVab8KC9{sO1ET!yNav>-aH#5GNk|9Nl*aB84~a*(c"
    "w!cNiB1ImkLN<T)q`u2cSd#!9<nX)&Sx0sp2+CgDSBQ9?D|$74wHW?`cK`swJm+Q&c%Acm>&Z9hPV3wW-?3$lZU+YNlqZ{jn"
    "Jy+Hd6AkS{i(O~0p;>b;SpL`atDOXVS9e6FNTlx)iS7*#+m5xrF>5x{cA<z_oK320%fUk=>en8xW+PS*`oEq@6Oc2B%LIVdu"
    "5bH!$!Wl(&<O=+<cpSGWM*y-~C~!zR$f!^ctd?@NTJwVFy2%1aM1j~k&T!YGL%~*$pj-X<oP}Khlpltvzm?X5YE{*p%+A8Y^"
    "RkU=_T|yc3;fQBv-prVjP{www|eUdV$0#qgv?eC;v+-T_*bK&Xw?L~n#3Mtv~d{frbOxf+6d-Wi@T_1zTYr5=-)7FJXbm~x?"
    "Ie50Q6KEsV)a8@-VvdfxwImFz*C-0d4&M8guwSYcFK;1wc+QC8oI93je%xNEVBi;&<~W@a@CH$agp{%zI!y!?5G%mVOx}@Mr"
    "cjzNJ~`RNpg02S-c#XmWv5j)y;MOyWbcqd;&Pz*6FW1VIoBp@D-Sh;?REqHqwU>gD)V@9VhI$>S0yhfz2vNEOZEy8TGjOm6K"
    "O&J-U&>S(oIBiFJ;0$0!`d$ZZBZAh!$F!j17I%$Nsg6K76v}74n?CNOHMs>(RuFUaw(=+&$$}M>Dse93?A0LFHND!M&Y4~z^"
    ";F8<%@#g)w+|47XNel%JMx+}?x1(&D1=;;tV<oL#-eTatRrUso-Yg<hIu<V)8UJy{gD&*fhH_J-{6pZZ^l@Lij(-Xo_|y3jz"
    "&nAhXnV(o4#~q8--LHfKZ1W&t|H&&x{Rafab4e^SJD31L28wjspoV;n?wf!E*N;wb@m7r;5cjJ{-A;HYh8lY>>~iE(+WWlt7"
    "G7A5d=YOM^t;GEWk=Aj9-i&4W7ZZPF_0$4zdhJrHhh?CPQgNB7)Wv;jf;|f%OrhUiLDB>HyfRZAoze1Q2kXD2n9^Bgd`Pw_("
    "}^YN0aKw_4)7^dNFTwd~*=_wbnu7x1a#5uAPY?m;?|1hL^9y8KT0_T~wE=g0`geHZn*z-SPr{5wkMPk)c1NU+I->M<6>$agC"
    "1^=(>-;OeSahWcxi_8*V@vD&}H9P@FW`FO%_;w!Bhev2JJF!?Ni_NE*Eg^A1LflF_~JI;I^H|L7DnB{;bQ1m(6AQbm=)csC7"
    "Mk9}MRK5`Cku(bWE9qPg6tup9*;fX^1AIly<G;0M@H<l#Fq~5b0W@wB1hFb;@E{0c<8k&%WDns-3oqh!<Z*qrfP*|#KUQLa%"
    "7oPEpSB2;jsodFdc~gY-|I1oE%yGUGy}JM1Wh<ZR=PcQ>&E4Ll>Hge+_d8hWKAloCB_w>CnMshM64ijHt;dW0_+>fKvpFFW@"
    "ZNO$zP5$kN(4!A5DVTP~0&InZusTZoqE`&)`-03WA12w#`tL4yxKA>huvzwLOuxI(*94#$*nxwZv(o9RT+B_pINv1T>#*XFP"
    "=V^E?7fIX*sDpU2yso6w$o81SCo+%bfYNR}PJfs3!kFSZ`T9i<Y6d<U!rRFyL)P+4zGYaGM^f3mk*0l3n%5%6>gMAZ5(I>TD"
    "yCOXyAj)(v5&ET!|5n%oW0FyLc5(KeoXaFGyVsqdV5~8BA15i464L;od8g6w<IEbtk3(ShJm7uB3SCc#?dZftei~wsA6^~%n"
    "M0qunRkkrft1TN@x8ie?`)j8qYln`V?i$uHx1_)<3(&|49Gb{tCL7>(?=rk_-+!fh60tMkRS8+a&rSsR$^CngYcYsAFd`l8{"
    "LDyZGQfMiYzw{-DjFVszjVF)VmAJgT}syIAXu+)qetr{s)5&!Bdr5H_J_uDoe4}cAE%jzPtH%_6P-&SYsUe+xVd8on~?c^H{"
    "p}H=kYBgLvUIQv$X(a!BJL@oB+tM=$x9J>uF`!-Cre!C}b#x*yFcRnIKGJPWZTx^Kr%05X8)vXpAHXV$IM%LJ-8}PJ)FCWb$"
    "zHNAOdbW4IYbT<+#D23Ly(s*HdvV>%LICQptrBu#06PBl+V7S}6UwNhPxv@8L(8%A<lmE4Nh#S>WTd>O1xj}ij&JkWi*E5i<"
    "2d5O=SyMW)#9>V1FPXL&s`xCJPC`<4PM)qHc54*?l4dse9{8hUDh#CuZmz1O<(-?{iivN2bF7?G9GzUO3<0#e*=@a=^USRdQ"
    "qsEZ{Q_RPl8{qC{9X}M@g3jC{knI;YFWui6m2gII@RA$xGxJ}^w~vk>>oLd{;B<fqmO<80tr{c!lW2by+!EsKHgld$sYl}TI"
    "8aA`N!Q0;*QW5UItN-W(6~qt#G0Xjgdm75<cKVlkDxqs2>-VECEVhcaHW&OUXejwL@LR;&74w~H>sdjBqep$wA2K6nUmhtW)"
    "W<r17J%>a21`4B6G$8U_3Ueh}EuLPCZXb>`Fp#iCGaK$OFYH#{-=@exh<Sjy?4iv}aG!J&M@YWQH%7Z*yw+mU0D`%Nz<G*Xj"
    "OB;Xkj8MTKzy*p4%nh!CqWP-O||MWZiTw^wQ}@wa9`9RTr1N2&d`^H9GQISz$Hz=SRtnsj_T6}0gA_B=k^Is&v#0OIuKjSoW"
    "?$-RePh7V5PgFA919OhXt9|-(Vqi{%Tp*Ug2f{|v3#zh&8b?U6C^QR;I<|oDf5xzHkV#@JwA8X*-W)Hxh`#ONl?Pfp_#Lk2U"
    "5`rKGfN|+$_Mtj*Eq=kj3%BtiuFT|7kq+{aMt}~en7YWG)Yl~@vFqUkus>_DsM@ZG{4bUPU@|olug94hCbidOaWDv9fM+=70"
    "#B7kV>TP0RS@{wnHhYT9mMHlk72W0coD?f8J6WkSK>Y5MSN>{7~>rm#TG{u4zk+tGfMY%T1<+ti8B792yt8@uxtmwfRP+Ktv"
    ">fXmal$Z35f#7{5D=d2M>7-{H(kN-qaI7W*+dSH)St#Lzm0LSG)v2bM9{3nk`|U$e`jm$Oa6KU}2iSuG_cT`KkR>r$~202{j"
    "v({)w*Z?>Wczc{TzE`oQR)77K97_3)|sdHniJ77!HuCkSGF7}VPYK@hu+sswU?GmO&cCHTqU5xg{8!V#9meq>P*Tu03u#v!F"
    "dJrF2s@wsJSr(3Qy0>%btgx&HH+zwYI>iy$Cl7e3L+atAeHS6UJE#c!_;G<e{fCBKP_B`I1y&BIw`oFe(PYGfrT=mj7$&XJz"
    "h?iuFXw66z{IE7$3JK<Nw1WUSmD;W_5&xvnW|E$$`7*x$Y#TTMVjqA>gAWbmd1d^v4jv2|_{q|3m^yhE&^fVbd&G+S<;4CQ@"
    "avtYwF9T(akT1ENBs+&!(|LPHFhPPo>~Mo>VBffwnfS|^vjmsfjPHICj|j&uE1Bl8vb>CFFN%{k(E9=ThQ8&Ac&m@4I~6X3?"
    "_WP%$6_1yWHpS%1jvtSQbOVL78zq0n36T6R4EfG@-0zIsohm*m5BUfORYqVt;Y{a<WIcW!c#8QKF8jk{}3RI%KIun-Dk|bWj"
    ">~@PJ>(+t?wTe(G~{zaj>>?P*T`Ro!<ne%3vMe=$6a@urK~On_@L1wc6~Bco8N>z%KlR^RT95<X$QcM(74pnhX?_JcM4nzAV"
    "dw57o5po15J4({@6_=VObKvQJ_O>OAjaCbxsU*+d#apc<D@SfUZczvY`F%RUL3}eDY1yRX{%H!wC5iO!5j)Zs9?uHUOMbqv-"
    "R_RBqkDv~T#1wp-a69<(#w0#6lZO<?2K8(b1hEaF0fiul0T<93LZ*BOZ+2h6?JSS0GkNSsMz>fRhpQa{%NohnQVP(sp5-pMM"
    "7h9vuxO-kGcpjY8VS>*e1Qx?BGuJi!Yt?lo(Ob0ZTOsnhVNn8@sS(i_?yNI-g>qJG&Wi3n;@1;{(zjg_zrxu`7rLtmQd_)<l"
    "7vh%!QUS4WhzuM`gW)QQq$Nw9j`WZFpM57tnW^K{WmqrWKwDyS}Je|7ZOc?rqm`Kic@@R1siPfSlRzJ>rFfa{nba<2|)UaA%"
    ">6Bgi3WN|bz#Y`~GT9L*-LNvHmsF)YsJkUGmlzivC8`(=5^@VYRoQSAWLqUX7X|IwPkJ6Z=I8;>K9vx9tA34+*W(11b^#P+~"
    "BAdxwQw-%4%4&-rju85Jq!4N{7fDEEGg2`cxEm_##eaIGDG+Ll1n_w{qg1!6(v6L~esSW_C>s(dYt0~Or5xYtaRhmekKp+Gh"
    "mqYrY*qNG8H&sc1>jT5U4b4NCf9CJ#o<$5CEW2O6xh(Ofkt(j{1r%Bwm4G9!N?epUoG+rNuu6Ba9D_aS-$`tzniW}2EV6K8>"
    ";*SN<Zl_Or}4{XKcY+^DRdQ($0g1Q50A8)_?lP4hk`57o_!j?sg3=<JL58wAHl?di}9oN$MCXJ8JDmeMm<*>{;F(4dnS60r*"
    "+P(@y`hTsb^Fdn^3UU?DJwRY9eP)bZOLOfR;KQ84oY1UxCilJ%Av`CqWSF3r(g7g4jk>C0H4`(kODpgZNePI4*bcIKVTQkQo"
    "dM2Ni90@}3k^l~UQ$MIbiL?I@cS&57ww__{AeD~^{-PVVHw-;0g3JyF1=1P%MVx8Lg<PRhi%?=opGEfMu(zy;}n4FeC02EOs"
    "M56nJC_bp<e*nj!=%Ks8Pfc<_3Bho=uaFp~IWC>yRd_8)EFcv;#zqE{Dq3`?C*0ruA$G+r#g(VL{srd_ujLLq9vwW1nD=_Z_"
    "I40ZpQez(PX4j%M^*A7=HoUc;TRI{O`)<Q;x9-QS<&wU4WZDcB-@&j}^N+Sw?@DrfOVsfzkw4aTemXME5uJE{q;~+fn;p`T0"
    "@KXL^Q?`(Y0cm_W`>m$1P~PcCkSGFp@|eh5ZjnbWp2+6`1k((xISCZf`Mbw)!hU11YC<US(CUpA`?Ak{Z#GEb160K_V1oLck"
    "_fbYfqhY+x5G)QvM1?<Ya(vyN={N(MmhhqPxJX@GzP2ap~a#-uCnh_~eB%+jVb=9Z2!Ot@5wjIo!;OI&xgrQU64)xVf(5dhx"
    "hl=K4kHx8z%qHZJylf2D}(<dyM{t~0j51Ujz7mmBl=M{gd#Q@aT0JPTlQ<MzZEmk2VLIC3R^J9`4JE>ytVK%*&;^BDH1(lX}"
    "u)Z_P@Bkc%CI66!QQ<VLrGSPGfQ_pgC7ZmGx^*PG;kDR{^1USb%eA%zz2j&k0&1V3)!C4RlLF`H*MH7M`h;0a;M*G~?@N=wy"
    ";>bb#6rRK_ZV^|pP$xh+0t&)eIAJq_OtzYKj~HOW(C;zqZR|;1YN#*W(a^gwy{k(ulE!M5TaBY(!%6dGgoc9o8Opdg-SRL!-"
    "NCnxl<}ARM%g&`@WAW=vAcPz_ad$?PJlO*44`T62gpFBgLCV97naCq;rQ5)+$p4F0;ylhwpAq%3QwTP18w-%q`;Kx<8NnY@Z"
    "sF`n43Nd$m43E4ckI@>`FN@b{&4R{UBaennI>i24(>6L1%3Ya~D}9)Mz5}+9+2$5OyWd=PnwZn0D@3hP+;!=?Qi3SvB_;+tD"
    "Kz-W#H8W;*b3PWpJzYXFTi09qS%JP3l=-Rz`05J3>T85P|TLvV{1;XS!0ahp@bm2MtG(nT2@Ii(XIP1k_vNA!un#gXa6MBR?"
    "~$1f!e_`aiR((q4nJR~gp)a-%e_AEj_Lt{`z{<!QRnsCSUwkBE{zNTt~p9xy1OgQ+^>9hFQdCCGHwjMTogZz)f4crhEFyUn|"
    "?q<U_b}}>;bwaomMeeXL)jO-7x32xZA7HioOMM+%Ofn)K?vHMEpdPZW{z1S6PD&5+Zh#X(2mjEX!$%t<K<mVYru&cVyH-}lF"
    "2g%#AHwUaRTMprdR<^xI=ZWj(rHjF{le|FBlh8LdDi(+r$V_ixQg=YXG|tXB=8txw|EGn|Ggu7_^-}}P?-^eA%Ksgtc@?VYI"
    "tksV#xU?RWrm5FNGioVs}Cr00cqo2%Mk|$!6d;>-aUl1eP7a4`)u`rA{6<Wr`RVu8#DKa#zpfnjL|HV`4Vl311gGVw1=iNKD"
    "%8Il5MVUa)n^jDpnFEdF{jU4GdNaJ13Rj_7e#Sk4zIk&%ur?I?I0-!xRgr*p%yaq`Il-6>*MkQ<Z#E;orQ`3Q<F2jhBNiEKf"
    "W@~(2iExK2@oq4p#XRNeE>0)e129O!)tdx0Gb!9#*2(-oAW)jof#|hcSU5z^4>)woJ?P<U}y<rBfQ#vB|9l8bYtv`g<ix*HW"
    "jA3pj0P}$ZP6k!xz?BRvYDF6EM(nu=9XXMZsW#LjqrbbcrhLm}3#6oFMUnsTvQSQ;-d$y?{y#d$Ga|sG8{liQ38|eTWc(8Zv"
    "2oA@iXe!cOLmWhoWNTullVrbi0j+}3IRt!a_r$Q@=EAQr|tHu{b$S0t=Ds36~s<8_wAa}J{biI*3VWpTC;7K0kGg0n3QSLGA"
    "k4jgBPHVFl~6Y6yRTuUybL#`d<fWFNj^n#Ko_b|4=xOLXBg8kU@oIx?g@H_@<)#R;1r!Lfe<!?ig#707(7Lr@X!%euUI-TeN"
    ">Y<EGI*k!T4Kru=6F9`l;`pY1t(ytWSr&H};djrsoaQCU849o~my_?N>YsCXPslYw`jqx}VC@au{MB}y1MZKCs~L<yA;pTk%"
    "vSZKFuG-YFp9oQZxZ8!a2l@A~-bHEAPpQ?{hEl>ZfK8g3V4kBni1;}X{-w1-(Flc}w2x8~s?vdaV7#X_(A8g-+YqACGlNpQ("
    "7Zv8{{_|GyxsKL^HmIuh3@3r=Z`Hng$rSy*6XnF?)XC!}kJN0y5(o4|+!#$dlo+NEYxQu6ldTp+6}T%?!<)`DfmssBA~v7W$"
    "Tji<#X5eVGKTuBz#*OmQ{sQ>@>K$Wy0?8K?$%>C8Zo$j<H80x0Fuv}*H-h{J@##~&8fXofl2P;sA%JJt$F;MxDIGM19Ud1i$"
    "`I<EbqAzzwaK$w^oP1n+&2MF(e%@pCPNF{amHnM_C&BJP8CcEKzXOYo<-3G5o{UF^e3hJ};PzfaqL@`T@rHw{%XpL{kQ6a)G"
    "Bs3$L8H1VQ6brH4RsbAli?6e<BA2x8~spJTu|OrM#RKQ1RQGIBM3nSB|zx+U!88I&1EUg-n~u4_D9C_yJJ^<-6eniS4N^e#D"
    "}?`K8#Ot_PE|GRy@7b%2C5kxap4kzkSBrXux<7ChX1g<XR@#ah&|6!{)o7jD1N9FM7b@-OdQ<$9dafB)9Kg$qS2Bfy}OnP^+"
    "v?X#drj`nAAZ#NucNUiKv~<mXCp7-s7X!_Q0I|+de?BJjm3<i5b1~l8co;9wpTlTS!u(`_eaIpgFl3Zt#%R8nlzr0~hDmT9j"
    "y5{Y-;eeq$`V+fGiBlV?Y<PYnsw~gjYBAM5-35$x)b1^>T`g+0LYnjJwyaS5NYi8StmgdyNa?@THX4Gm5~|03_l$_fE%46E_"
    "ZV{B(tc>P#8)pdh1ENKwH(JE1@V8^@@cA&3a{TJ!nr|`wH32On^oF70Y5>d>7_;N{FbPmY%ftI8LPQC9Wpvbywhg!N=L0hi^"
    "Osv?rgS`xvolln>l4|CCSR<(V={?WkwGaSA3&h)fBNOs@-%^Nv<q>%UY6z=k6AZq<cA)@5*%K%R7TWWCk#;1_^Do4bI2Bd&&"
    "=eGrgm*Y$gvAG=0Y_gshf&fbe#3nffQ7g>*?6mS&bbUQM{o0}}TP~%PHh|#CSuJE_g92S&mnGOK9uwUYR)_b%dq;CCS>ch--"
    "NC+-)&hhY1?Kynk>|vnwG=L2%jUWhuu%HY8f*^JgN^q(c{wV=(@{IhjGmcF4Qv6)|F}y5O##L?}Bhp1DV32-*lEabHsiDy-;"
    "%Jge^EGq-C|x}k^)`-x6;AG#n);=s@vbLZIrUT>8dSP$vW8m!R+DJ;2S?NMk>w1xREqc^yof*9!c8W2A3xYWf!jy-=wYOy1>"
    "_Qn@8)-!UT9MOL%+Uh7W=xRj9b?XaaLE9Y>wlkY~en%A#2aCpYfmBE0G<+z5`d`XY2RlHNoQ;DGnjmVQ@PPCBac)Zs@o*8X}"
    "22uJHNL;n<7q0I=!p)DTt%m|UekRbR2BN#r!vS`gM7)Ho*t)TO}loi^@LZU2H(k?<cu5X8nqo<@Qo2v(Jl6(DyIKUzADJ6Qo"
    "Y=ZhE(TvUaFqTtAC3pASTs>x$dE5T?uRgQuM6Z&;@03_FIN4QqYT2`^<41nIW;rJ&Gz(vQ@v}@!HGoBB@C9)NcN3sokM|%wC"
    "p7}D}%ZLrf+4~atA96GJ4tE5s4wPKSs`HN``%>!GaVjss(V~_MqyIhE{aPFVTbco2MYj!lj0`ZF3GnyLS-f#>0%)jqb~Eep{"
    "T#mPo8@Q3^LTZk0^R~9=Y3tarK0^6?jWn$4kDq%s>hQsvq+(}T#_q}#Tt`(4Pmi{A2|!09vv8E#GBgwWClPVod;{1W~GmF+{"
    "6EC&Ef6y!+?AN@Ym-!5d=Xj1!Vvb1VP9-2FwBNS@|cOQGBX+5I-QF#jVKVW~Yct+#Iq2*J-Y0$I<#xzL3c22%r&+>US8^6r-"
    "2wGO!$W(p*vYsgX8W7U3kiBLu1$2V4Np&$e;xfdbxo;W>P;dPHK5gtLeZgzuH_3QpnL%oy5DfiX9mS^{LQ-JZ)jzO)n8`8JO"
    "JE4XdoYDa*?JPYuY-@@lRbwJnDca7Q{%Cf!ewtr=bOa__ZaZDV%6z`mQ9Iwlq#Hd%q+*E){z;Os!{ju5zkE86Sj^FaNXkTec"
    "Iluy}^AQ>G_8E#xz#^2pp$Bs>NF%EGmr|g`1ZG%(r~MZ0M;q|Yt(%jCAP8bP(11e_1hHUbtVpmTvem<IvitEa|LeHLDd93Vh"
    "cV&my5BN$bp5MJfz9zq<2g?Av?ic2D{ug?O&Y=1`u=sx07$M#z+(~_WnyRtKv-Yl$pDT@t7ROuz{gbH$5T!V-|JqA3n%XZYL"
    "j$NBi5hX0g3Dp{NwmEE|od#>tvAUnaJ=rb^hJje&qxRh2KnDOFQ~+*PE}=0kEYR0IYYc(+N@mj<GiWrZIz`u1x@)rvW*?s_&"
    "#TdX;=Do5fAJ9PTWaafD|Pv?N@gVF(WVApA&2mkt?CmV`K~m2$se+f$!6=O=M&P1%6`WOCgswFaOoKB(6bU`_;RIRY=p4*q9"
    "*8XugWfbgD=%F_sfAT|dYa0r4R79%q*;qHT*J&1QZ592ncgiGC=b^;7D7a6cH5+tBI3B<#yE%;>6<pcVU#fRUmasaF}F=5>s"
    "7?_m_efV^QQ5pXt`Ye@#5x%U$Z^wcb+#!a)s!ieNW>pF83A(2d>kq#~erUqO8_T08wm9~%EFg^NpB?p0hWz_V$FGl}zL5@qC"
    "G|@zC#N!w9bgJ=JSv;`&fH5db?l!2d1l4m$IQf~^2jB(;oqFP3okEJa52xK<U4RYprBhVGOLYW^!a*xum&$v|8I0zmL;yDvN"
    "uw)8+v{x-xhslJkDDsOhzcyDoN<TN1X+zI|5(t)bV}oLukxANYQ_SAT}K;0U!v1SPbt1gV&ON`vN{F%0O-eKU_M2muK?05k("
    "wfS!9`V0;tKJK%P5&CZx#~8#U=Q7}2T0t(92s$@gLt>8EID(*L7B;~HcAAc~|41cAgDT(mn9*B1(?WX3Q*e_}ItfY=RW#^li"
    "G<@m;-7vVM-3IPutQQEk)TFb@Qt=>|uaa))!ZcVoxvGqDMePdu=UDNfI<Vs`Pwrv}YZ8T_X+qN6qw(Z8Y&BlJ)`}w{<=l?!~"
    "wbtyJ*__<Oz3x~0eQIFJcd<1a&&LH07YW+8LSI;&R*&{kXv2is$Qx$d1;Qqp50KR!;tLE#B#}Pd>bE^DGJ)<MyS<f-pnJ{UQ"
    "pbG()3q${7s13?n0M*%wPka%h%pJTFgJe7g2tbk|9Xm7kVioT|HcF<+czX<1oPCxk`G+|%d5WW<f&bFwc&U#bd%wD1kR8kL8"
    "+#^xd1;X5dn`Cp7=&3(aVym_SxV{k=L65Yb+r0+kstBTeqPn6L7Y0d)F>VP>dV06QF+d=Q;UNs?$@ZIelg902<}l`IGf=-0+"
    "82NaiVxZAmZ1`6q_g$ZrR#30vbNcC(Y5#I#h9DQN_RyaHzXl$L;gd?-{VmuKmBhrcjRdq+I10lxZ8qR))74{k_3+P{XUMidL"
    "<$o)YhEITNYbCw$Y5T>Or_5Lm|>g&pLzMeD6o`4P|$8zE}?%isWP0#=u!~)XtYg@n(i?Ewjp@88pe}KUD`WpgjVwwTb0f!Qb"
    "c&m{FmVAZlkb0*FO>%;Ib_Zl4Tfaq(G{`IIQWU~sh{J9RnJ?6<K9z;l@(@+E&g<BsE+XlAu)F$Add%8j9_5Q{Y61B`*(2`_M"
    "vkBtWBtN6>^hr^o<BSXU+~#NMY{$B%#=gYcXbaPZtOB^WHvm{%~gm7jhC4}DK>(mVtcH<@9Ex|^m-bNT^qQ6HT{Xcq}ouN+<"
    "o;z+Mg3E{;hD|T7An<x^D&hRS2?8vey!Jqh}Sgj*q1s+E;zpa{f|98v`yEWYZ?-_KKoONG?LOWd}tBEZ#l8f~0=<qWk<_n)A"
    "gCK&B^yG_uSMNB)bH+`SX(V@faB?_S4x8z<=YZD+VU6&{8dXvt4y`74UL<r#<$BjwhyBr>MVW1c|+NnpLp@BqRBiehm~LMHp"
    "gYfY1&_^JZ1-cH+sYsSnxv}f}U<WkVD0={UD9CMJ%c_&+vr6}z#=}()Y;Op@iK~_KeD`HDls*6Wg8Sm}6ZWsp&PC$R2Ir+^E"
    "tJbrc3tcgT7u1}<ug?z}+_=TM$Q$p=g4QaP-bEYyg8s#a54li7Nlr{-n*})qtgjSP>DZ5KhYL@5<GuaMFz@L<Qu~|yiY`vu_"
    "{tqU`?6q(NXYB&OU$r0xZw>qH?`ZnUpBw@5zPMhaf%zG3L$ELOa2Fql^`(@sA*>TkEp+FGgEt#aKvp67`Ns;aJN%x4Ag$ucW"
    "L`sy^V5JXA3x(&aILpQ?m#)k;io9AT?#4xpNOaZ%ZCPX902ex}r15%F&EzAQfzZZod`4-{`wR%(7qWfyL$l-z&p!`8amaZ!v"
    "d3$cCGiMubyt@nnmGN5oHD*gnyaL4c;Bm>)eAiXt>_NH^!Fk?Qmb0tr9&I~)^R>pBt0atfB9<Df9za;0f7skzSxpgxB7^ItP"
    "5_vi;uKTh`5nTA&sKO2(^!(JYEZIgX!OI3Q4JkptgmzYY^P`b@37$9emH^MW+%i7Lf{XBrMx1UzTkVZ0j|K^2^NbDY^T@S?H"
    "6Wn0G${8a>gwREllEFlmyyT<pTD&zj=CxvH9z|D%lK`U+IIHSf-{KNfJIY*9b-!@r+QI1Ug`Ik7U~_Dzb}5c%%w+{+pE!&j4"
    "j#t@@Mw0D)0xYyAv|@9-fea7`N#m?40B@Lyz9Eqg89Em<;LOhg~7IIYC<{g7)8%t28FOvJ!@Lw2$JRZoe!y@@v0A19PsB?Wy"
    "_=WG5K1e&u5<1Onb0VJ}6tSgqz-3PTv$m1YI3d;z8otabO5a!a0ho)KdeToTZ%D0w8A;uU-9r?iM7*bB4oz+W36y;b(*2K?P"
    "W-OCt_038Rn(5F)EMWe(Xl7;J=Y=SiMrQ0maj47l!m)xX(8jE_QdM18IggTbtC{p1kDJ=CI&b`HPa|NWOI0%tgW2|{wx&lCS"
    "hoC{Spd0uohyIs`^t=2VKjMBZIKHytzz_e@|b%Pa4?kb4#xqF!Rz1D;9W1ckI*$3b1E6GTFPQ(0WnjPg*Pn*>b97fQI)Hml3"
    "SWc}-^Mk3Oi+^gn+5)L6$~Ae~XLrZWQYXMSd%)^iqX@5Kn97XE(eNrr4Cxx%jYX+Zf_;BZ)g?EetNCb&hxfO57$H4!^SisTO"
    "YnRS9j5h}ZbR35Llr&eogv!KAq=Yul?FftNMfN&Qzj!6#NiC<Tvl4K=YS95a>1&L+-a&|_`ioL;edzkW2*_yLWXOi3%*lQ!|"
    "2)78XF3J7~D?lMA~gTY^CbBG{C0+_}yqBfDh%OnieT1k&kNES(!PK<1UuV(j<i=enI;<zMU|ge*tGGS)SpPY-$ASLv}{qR45"
    "UfO_35oN-_7lrS7)ohH%z@@aOix$e>B@q&jBA8`(s3t_Ek=-%K2^{4Bq3*BlTYQvvst|D#<yLe5_)<O?*Xcq{~(C11D+rDHt"
    "+FFdxrf);&KK7qQ`qN`g&JQ1Dr;=$va($6+VZ(P%$SaRSI(O<2-UzZ#HG?tpX=>@M~LYl?j4*6F|Y6H0b{f)Rlr50Znfe6bk"
    "++qh1pUp0?rdJZ=kHIW-g_L&ZE&3rL&2NvNEwS}aW>;~`M-=vyiDHTlKx=}S3Sz@u(G;dK9ED)zZGN$8nlew_iP>w8k}Zn@G"
    "EJ5$d<!PAyx3jL>D*29Rwnhqya}7$y3pf7R1B9(XUWQ#c#@jl3Yh8sU(s{#`}}viw(`(F3T!RUFzDE-crSx5zwb!m+P3(sfl"
    "YPe9Bg?n?}f(tB5}N0>!{+2u-PfhY$|a6X}8W{&LGPy^%T_ELKT~JPVF(rU0{GYZ+*f%TEcAGiK91;yNK7S!>gE0tjp;W{rK"
    "(B1rK>R!AZfZW57Sf!=HVt-P$tWUlKU6+fod2OS$vg?_Lrz0F(6}K@bI9bo7Q@Hb7r42*brJpJH)yy_I7<#!nHfA7+W(w0x)"
    "Wi1HP=1a>DRubi7WsaOgxqW*%iV(mMa4GcCFW@c>?4f8D_@Mb|;E^ARbw>~Xl#+`$)QzVK+SiTx?<v|nFSvjjBYes6jtvDDt"
    "6d7%qz*LL4Cm&k>0U}A*pmFA#aoe-N95_z=R)(8Qp@k>g2f=_pOmIjr?EDaFKl_Z&dK_H+P-C|^6-xqE?Cr##m<K2qP8KQ?1"
    "rY7gm)T^_qF9^+^Cup#W8TgW0kKl|sdNuMngtEYSp@UJ{fkK$M?iVkZ1%ob&z>i(pyKERz1&M;|IP3^{_p$*FMB>Z5g7JJ^_"
    "antNUfZE{2{)W);mvT)yasl^FXsAMueX2ZfNymxxIEPqB)STGlTukFUtCbd1O1Ll(ds!q`MzUmRTC*R)p4X%f>v&Y{=!}8U@"
    "zSAy$#Qj}A~6+jeL%o4!tX{BbLEoyouVh9`kP@J4@8HubY!h6Qbje2gVUx(i{s&$+imGwzQB%;AK<nzh63ECxegP4k5!Q;%|"
    "RrHwEWu~0JOv(rRNrzXuSxAAtsC*QQZc4Kp)eklET4jozgOc;?dzZIe<V{SM0>*`W#+~QqAKpEMJs(NgjeZ#O;S5ZS{s9*pK"
    "M~AsLYf0~A1@+2fkFA+N=bz<<by^d=!QI68OB>PS!2Afq^fbQN9)1N;i!;Jvh_$xD>XdYr>)l`7p!&2pC!$7&n%6fVtNbW+L"
    "`FDRYaO!9J4=aERtv`4jj+`HeT`aR$kkU>Rm-Nfm|_`ij?-6&OhY5mj|5xPI~!o^8wPP}J=BE^SKdRGVk8=a*9PA*fuVTMMe"
    "bI-?jWacxde{C8a`o+gZ()nh;_f50&Olxc+A2HBC=#Q3K^oaGEw*h_iCBpB+7iQfB4*(qu=>1)%0zWmhEJv>GM`P%2>qRK7V"
    "AxV%yBj<g`xATtZ?3DNX6}UB%nCB3xp2m;hW|gk2u6<>*IRrxQTfjBo%Tgd`RM5vwkYnjsl-g49Iqvj=EK9W(5x-$u__@`H}"
    "v9YAWJvwf=xk#Dw1;W#X@^D|?j*GcM+Q&x|QAY%r-$7L&e<U1vhT&gSXsdcP9{#5gB$`~;N51cn_bu5gcv1x~!=DT@PYLtZW"
    "(})7yTI7$=mLA|vsES$vcYbSDGPC$_55Rj}6hU1jNTiPt_5&Y(8s4F9@?on;noUC|AUHgcrOp!XVWSFpC*I5Fn*YZ5TeH1Xz"
    "W0+?b)v6;9;gVXXas8=2C$}xdL+18bF1C#wN=v#FMBcDS)2y!8J1sDKpJTa!~Yw|+jWO6$n&J9aW-bDQ$jm49<>Nmg~Kg)Il"
    "f`JnwTjSAVQK=w%tFR<BoZX>BJBHc(X@g2p}q;XpA|7HGt=6(KddVDA2dgI+q&<tre)$zRJ!14Ha_Q2Jqe6h~<DK5W0l@34-"
    "`RUl36#tK+YZK4rvfr>OMJD)ZA;JKqJp7ryx_H4ypYF3<AaSw?_GZK&!Y0iS!quzqKT&gk;VtC(ys6&3hh+cx%jFJKL}Hx|~"
    "HWBfQy*b;d`#ajRcvL0F9N$c68Bj#yBdp6StI_=%FeHjT@cS!^R5JKd$qlgV0&4<N@#_N;li%>e=-6Nws)tf?lV%lI^=p8Yo"
    "2NTr;Ww`pIdCQEbY-RI`|Kj?B{&>JrS~}LCKv!Q$Z0ucGfN!jr>IY6MS%MeW`M%glsDnm@4JFQ&S*C}Md+CnAA&+|7yo36g>"
    "k)r{q?dc1D47?ge=xmkWCojD9GE|QB>4(BFp4Pwp^99EoQt~T6p7Lv8HuPZ!G76vrT@Cq$hm$GNKD8Ui+k+!89zaUbn_RLkO"
    "b=F4}nh&j4;g(f2HS)<cwPG{N{rIezl$tS^o`9uKz-FOUVDQ$zDGokk-wj!ZI1I76WS|B*6tW3NB~x?YIV{GYY73{m_=hc)7"
    "{=KFst;wLz+Xyky7t3tZX54|(()s#<lv8uiMvxMoai=@1ihR`{27l$F|P1Kp7cRFE0zK&jL2GT9a*dr%J~{QkzqLA8y%R3Q`"
    "b%cxju0du5PC=rFqy}oux<hdPf>g5GcGU5v>pR#AFX*P><@{g1lKg;7i4`8BnHx^vrck{iYSM@!i3~R7puYU}Q!ait2`LKZb"
    "K7UON!ZSy&WfveU)X(qi-$aJyztcfR);np)ReY-VHlYYE_Ya3@;0S&nN<tBAf>N14P|Y6p#OCO?<SWJnIH{xxvYxpSZx5R2;"
    "Ppk(w~d~w%MR+F8RJFh7K!%nnP9virtASv+`Yr49ED$aZi$<5dDaQp)%y2KER)hBS?CbdqtS0{DRO#i&?_LZo9MR8jp9aALT"
    "+te?30ElgG!hsE?%7yr)*O6<ji95j({hj(77}c;p{V)$WY-a(nYB=SpbiWjNyPRQ_VY`GAIM@Fusr>;~8uO(?&e%#hzi%Oce"
    "g?6V_Yj*+B|>wzazvkZXE}A1J^&<Nq8LU6T=A{NXPCkFRSz*-Xg76`&}lDt|E#x`A0YogU>maL?E+)Da@XSsnD)9JGm&uG97"
    "tTZi8Zl`OQN(&A_IErD43!hz<~khnBey}Qk7h{PPUW}Yf?3l%PEyCyOWH`QRk7A$z5vxMI=g6gg3s$r&phXoBs1}3S7nCW=v"
    "&G(`PJ8f7Kw2x)B%O&PWQqal>kegpsIQh#r>R-^_u?C}$QD`43GKrv(P@%>2j?&FHiB$08WZy(T>Sxe|@yK@^5A)&ebQ*6}I"
    ")Xz3$$jK?5PDotA+Nv=-U;EH{t~crcsK{3kOpp&Z5hzb)f6;UwC+oGIpeHOKvhOiv`6(<Av@3%aR;mM22F7Q;+P)nV1EJsC)"
    "0B)?$#IfyX}`fE>!)>0L$zx`$tv5Nrsfa?%im%5<^G4D@b#^tz^a5C3i)CNm8wm-`z$i59s^Vq-N*!AXWP{649#6;ai1uXBl"
    "gR^gtg!2S!m^q*$iuQqxiiyU%i5sbu{%(yO9;$KasbK*FJHv!N~C9e7O8prdr3ex4|fbxwf8K^l=TG^>dp7e#L;%1-0Wjnho"
    "Oyk}~`JTFuY6HG3Yfhj~ZoC&onF=ReN(qAeOBnB^%9>Ojh4XaD}eVJ$WP;o;a>+8%mnJ(9d+OB^RWJ(c>KSckoTGaT{(kbYT"
    "h@P?Lw$saxtr1<24-qp2nNUV?=1P&UMNf-OyAZCH62<~mttI0*E|^C>9=9o_x1s{=$D<Bim!mxVBtDAvP#P_MJ64MmK8P*Tg"
    "=0frSRpZ3BbYy~d=l7w?L_n!e<2z*UFCX<G}Yc*7Wh`s)d0AW&+yM);;wHrEWMf3M1)Bp(5dF!$n%pUF!j+R+H@NzjW=bhP>"
    "f!9%qvpjJ?&ToDam_cqb54C-}$J5T}{m{3I5tNKzBn1anL42m6RDAwKu=;b4Fwo9g9~b+z%NVHVfSFz62UVoiKD=v45RqByL"
    "Pcg5^-Gbh-G(rW2H6cJ|@Zg_SOIL2Ie|V@>I7zl>pB(ZRAWnp?yHT!2PT$RP*09rAWw76x?b7pOXy`#Wq7c*NUD#>U|Rjpyy"
    "J=r_BzUl8hDJIO>p7mHywy-Bn*^c_;tHj(uO`f)2xD5ea~OcR|SxF=JSU48e&ti3^Cbg2!p2sR7JUndm`zxktbuYJL;Jxlna"
    "=TzzUx^gb>jNphoFQ|Njl)L2J&(Ws}jbIpgv&X%@%@!HnY+2M6MI7||?~*%65`Ou2K_$)m0QXm6+ltI{#5g>p@e(a^rEz<tA"
    "PVSmo}bkbA@6nL8GLO6x%PRmx=6(X@0B=QD2pa6jOr6X%JMK5U<~`|Fd^YqptjONJ2BtD1>62Uc3=kxi<Oh7jN&%GLdma(+j"
    "oCwwq({3ei_U|tBUmeWLA8W@D4f7KcX=V4!VfK&&)5TG148U8Ue5Y1}3$kP)M$ny^Vn*$9e_<=2MbozAnYVinv|luX6`T&zS"
    "!*J>IRKdqh3{+jcf$RgbiccP4_F1W5(W-K`Qo>YkC`*}Fr|75YiN4jkWRuW*wgO<j-p|E4L6{|Isr^K-+RpZYg%PLPy|4A*k"
    "k_W0*S2i($aPr^F+G2l3nu9o1vaY8sDg|FgPly=}T(*ftG)S;RpJzDW`s~qn4$f;h7Vn;p`F!F?-RDW$<1;QmmLv3G6+(2&J"
    "e^Ia|pi4Z-*pHi8A)}*Dzq6TT{JhweIy$vl5LiDlXu2z6;<vL{g#H)_D~&H9#0B6*lE?(3Qog7E?UtsL(0~TJmi)`3L*q)EJ"
    "l1T@b!|#T$rugn9blI{ACiX-Of%sx*6^!wJ$uer9?Y4Tn5oS1zn~QR0%U@hSzEUVq)xP`Sw53*L|Q5gQ{rX~J=MH`Js0MBG6"
    "*5U{FkMX#+{~rvVD=BzTS3ChrEF1k^4CiP(lekL<vwLH3$`ZM>KWjcUravd)tVcDJ12qtZ=>(5ZHJYcR`c<sJokGIB8z3WCb"
    "Jq=`}bkq7IP@fbay7od$OkYm17XG|c4lbn0r!#B_4|W;-pv>tF^9MjwGxp7mvW7o)p$nv*=>Jv#^H3R!EChEm^cfWATk9<{}"
    "@2o4cPnI|C;;HVhSU)^#Sd%x~*p6}l&dvOHcXlR>$_R0B2OQ-Z8UsK`^OepljQJ#28Ai<v@Dpb2lIsg!Xb%_7INC*&7$BH_l"
    "*rJOs>qp(`Nn&spjg-06U<!1gmXJ>BfH9Tr2Y9^0BE$x_99N#l28x>qS+Y5Gg;i8jB`Yj4a)X{F)UU>7AHI-#rEC2mv+5t-G"
    "Ctj8KUQoFv*z&V6J43ptXS=9<A!*Ob9y0$=@XmAj=#~RNLvxUgh$@|e$kA2p{Je$X+1+Faw-dR0h((p_^{-SF-dAN2a5KLe$"
    "|hZpz0>z+xK3%>YTGO`*XuEl7Z<M;Nw4OJ$se-3sl8|e)1yncHd1ax#R?OViQpEM)EL4b=fuD)<{41%Q4SfdL=6%C?xl8ObL"
    "(!g=lg9-?8BtEcQ1=?^1~uw3V;{)N2g;u-eJys{u1zDd`1kH11AGseXCkrk6}!CWX;78u--)D>#wHt7UaAKN749gm=X>=E)y"
    "9-c_kv_Brj<1)V7++9KN-Zq_WoeHAuh*A5&lU+j!{cB94!5ajln-}ze|1r=MuqqIhU!ugG^7Hj8_ig6^qKJw6IcE;Qz-RsYK"
    "MxzLRQ8nGQ4TCkN_41-<Eq;B9gCUIl6=$8mY+vXb7ysQ@!|+MW`m4id$xo?`pnCcyWjwcq*zq0Z)EaI?LlS+q-xOW8f9d`I+"
    "!psM!yAn&2?G|E{8aTjt#Ekn&Gpt##^nG%JnQ$0>TyuB-MoEWfEYoFc>XY<<uk&bn!DH=?p7Ru_&Q7jmB&K0swIu3&4y!wl5"
    "$E5h-F>TYk2f&z2Sr*GF~mMv3ZmKM7{gF&avh@tJsJOTquJ#)fQonh^L-`ifO*3uy;-nJ7b3yPCQDkL@9j{sX@UzfM%{2lN3"
    "4L7iCBuueS2gbDY|$3&k0~-*MgvNUlpT9l?I}bLr;1Ej5?x2^M!dlp#mWS!Lx#h3uK=U33>z@033fN3jp6V}0^#sS8gsi>vr"
    "*KA98DFH;pLbpM~UA!erR7s2Oc|1+;Z^=YA%cQis?dnSqkn@$O(AO{%TWMtA7;J%yQ`*`bt;($Of&g?MUEe{tLNBNm$9j`|7"
    "EAzMx&rp>%;6necrg}c<L%nQMbvJhw$?Zb{?WK;X(KJ@(Ig#hI7ZEB#Bz4Sn5r2rR$WWyyuu}yaCvW#O-Ljy>T33{oKh@~NH"
    "c7Wh7a3NmW%iFKwBh0f4v)Up^lE>^BX$4X96ItGRP-0c2l{6nd#L_{jo^$Aep(mI4FhAceKQYciUGzh-hkPybdo*UA5PK+%5"
    "S*+r`#ozREo>>?WvX^dW)MzJUa6K_K^LjU4u*%9P-!z=xRT(!FnQ3*EUpD;Z@I7Awbal6_B6|<w3&_ktXY3#v~5CgSo4z4rW"
    "gwe^?uD7gABkhkbZZ^GtVNwzDQc@439%J^eJ9EW<XEaNx8KuM3Ebg`3`~a+IdGbf9tZUm<-YXao7Ge4(YLgBY+#n#=bUmXHM"
    "_Z?bsZlWY1;UxF1>b1v;2V*k6_UEfw*uJXvX1>^#WL(EIg)WlC*{6x*?sp;(ba^o_sf)9MQjbbjT46Yw(jh8uf*E^ZTjV;6;"
    "Qxg^n!aav*0LyEiASUrcRUO|zQvX<$a78yXf-tP;Ki?*ztw=t0tn1aU@h-csQ=u+)KsZ5OEmh5BezsmPo`<fjS|W6jk22l7n"
    "cD3dTED?|$911l{6qGqTu(E&F*@nN;m9e{6j&)*XbGqbh=^n>jUtH|pGj2obsgJ%1--ii`Ft3J+#-WFe#}fNRo3p!f+T3y_?"
    "(;sTiK5x-rlv-DWNd3SWBfBwYfw5;I2)O^BD{Flm;ki#c9O=`bf_p8L7N=5c#M2M!ciB`3J8Ay|1Wxzo7l@)~%DYc&uU%UMz"
    "1u`y1Tw$~glv>0y+cKCu=_QYtpOY&5flxEhnl1&8rMFi5ZGfI=58|3Els4kjh4W4AEBq)Gp}kXTCVuvn@<RT;hr93TbiM>Cx"
    "B<8rLz07JrC<q!O0sfP*3!D1X9G?Np;tF#7fSUUQpHuXu{p(?l{m*|sWPj)i4ykr$f?getPs^Tp!(0K>tk7DO67KorVh%4@@"
    "ecRW~gq`QP;b?~F>Tl8b<C}KHRq4}IJI?m9D5P!~s}FG6H_t4}UyLI(^dPmVaBQ**u_-ahpw9G+1Kyc&c)X~rH{E&a2Cw}r="
    "F_Zz7jSQkamL<t)nh}Ael9-(tc-q+ebVX?bDis&P%ik*GX|WJ*U(ZqUJF?j_%~|Yck`o)XASMse^)n7{~4S+E1@r5T-Kaw(r"
    "JLUj2SE-yC*n1^F7&(&9A3~q?7vWxoGKoE3YFg+Q{rGR#(}jbdwhttu2?ixDSC<ULAg3b5NK@rUmZN*sze~FcT?WX8N7ou_T"
    "rNvnzDY<afzNSHmQGih+t}w|)MoFi`1nM^jv3MHO!Lul@V46_3SX-%@uYedYC}-|zVAp>vRS(s_7xXH?0})gcWT_p?W!iIXE"
    "FS>*i3i#K&gdOQ8wp!qG<o7K#pSs%z#hVMEroL8b)Ed@b*qvppRCrPR1;uNe`I#^g=(202^xUU1{U55d@d;x?mJpaO3cpxo;"
    "G^pwA14X~%5M<2MpB#rUjGTD>1}O|naLVc~{cfpuXTXv-n&E(lGi@w?92Zs0mAPv&Imqh%z<nYUsCau0S|@PVNwzbrf+cp)9"
    "ud{kX{VsdHi8$f4u^J=Y6BJRc+BBR5e9dVP+>cAnN>nq?2mkGsIs<lS9j)%oCoLYTY*zbM_~*xp<_yRt<5e|Nr?UhQ}8M6hY"
    "}A`q4Z%^4{~L(U{|v}II^zZXG;JPVC=W?oA3N-RQU7TyYLlLCp-yfSY^z?dW<^~#}kaM@|hOetT%@hHqO>aGMK@r{QxR@!X6"
    "Q1e*o@ZW_^MTU{o(bE>G$&T*(P%CZ!l?o@Lkv3C{Buq_Kp^7m{#IrnGjb#rCQ3!Lp&!?ahv=Sm)-768VNKE8&tNRlkm|9bCI"
    "gZkbyJyN+h!460!O5R=b%H4Y`&XPION-O!-j`|gNwQ}V0xaBw(&+q3K4?vnpm56jc}C5rnPRya%y))R|IR8@Pvm8Ew_?>&+b"
    ";{{)|=9j*U_h$g2&!6k0Y0X+2<L8Q{T4az^NZjymK>BC?><8^<{VMEF$77?(WjQc66)1a~k-*OG8=`loD<m(lkXi(+3n4dsc"
    "9E8-YAHG`EIjLdfMhnGvw&KDx56vaUww@JU;2(BtHl-HJqr)cFd!}Q+<g7CL(cz%p{Z3Zq*a++V$0(02IHHxTsS&Csm{=HLw"
    "+xRXVz-fIBN8G3FC$t#;+^j*3w<iEQ3S=Z;{V;=l99{(+xg<!%qdQm%p^tqWknf#$ihVNo+@Y%n6THlJgVH-!o<0MsMZ3-qV"
    "jtx;<SwR9ea*6Zz4h%uVc@@_iTiA^LV<1+C}{=G#;<ilCUxTTwM59xGeK+3D~N`K&8SbgxN0o*@Ut1S|qMOb^Y%@&oiB6!R^"
    "~TcGS}{0pz;M;!~3hog>#amx!Bw^Dxb;K$B>>vrFK7CL^CwO6|%)w>p4uQA~0^bI|JEPB5vjx#D#?N<G1<0b|h{%Lr2%hMJ<"
    "OSRZH)+2Tda|RnDfE554a1#8_Rm?f3&yf8p<!E8&S)=>5e_d>^zfS*vSYcwu`-s(}SPG%}^*nKu+*)l1tNz1r)Qx|<JUE>nY"
    "Sz6j`hAG@y7Be1Nwy2a^IBZ~RGH+Lj2PKvHDGo?(15{}X&&0ny3LQ{cxr$C0dCFI$Z<!+;h?w4t;h}k1ztq&Mz26~RPQuQZ1"
    "K~Yef374b*KBjc~A+0Z`gOb;#R**6TYrzAZhNt_~E>ov`&POSqW=LCOidp#uOP&Vkh(d#=IlELlh;almNI^0#Z!;*}=6afEN"
    "?sGDu@qGd8M>^f@%uTK1uC@1tC3hWl7vfso2o{?|S7L+R*jNg$2lm;oD{0lAViSdArNhQAG;+ykkgASvin+*;MVW<?v^zadB"
    "=F!YOT*6Gqerq?l9xXupp*(@8Buw3W2wOHRj@e;_Tfk8EThbN5O7T;1UbVl*2ucvP?ZmD_#)j8e6*yET&da_XGNYJ?q?mJ%h"
    "uI(4{1dsL0d>1(@8sRRyVZRGm7n~#d-p?lz6^eVI9jdP)ow<^RV0woj8s06J9$UJS+>c1ajBxT0dgWL&t^NQ#Zi_X`ME{g<#"
    "ICW?k7>~v-9b@?H5aIX{nFJt-X<VZ&PVA%7VioFWN@BIa0SmwAE8?Mw+N4w`Y%l%hSpJ+K<sbRyJjU(>A&iqA0H#>pS-WVN@"
    "NBsfw3u0O-xVfN8zmgjKUCST!vRr4KRfg$>TuLNH!;(mK`5kb9wlz*yv`Z@Kc*Niu330hfRzIxJISk8V4&syERacNv>vJ@Hv"
    "6$?Fqn@{8m7MkEkvv_}p}Qq-^re)qEvJ&@g|!qg=yDVNHYNqh*>D<%-gLFcN9}5r5Z<%aM3igZhq@8&if(q8bBQw)oy9xp9q"
    "E6HF0+zBStof>;9b#SdVB{}aZnQ0i%hgY2%Wg~7eh#6sb*iMm52OraooVsp(6-wz9bw{!lm9jitJGUfhP0_AJ6%d%n(zsNFJ"
    "Ni*wjRVW2P>|XC=$TTYr&wV|$RuZkuc7*LF@!jgdQU{;jQ&SUOT=>#rc~yuf;^lx=?w{R`Gni-;XwH3fr&{WyGNfTf`<%9im"
    "zP!nlL%Mec_R<GUA`J>wR^NYZ>Sn9{zDTjVW-&)z4Q&fqx@47Do?B+5v>YegCg})x<Rb^>E;*y@CR9ISEcoP$yH7=nL)|(I!"
    ")Mi&DqHJ!fh@6B#_)sOM8EJj^47~fd)O8*q86`rbq0ora52%Z~i;?x%h|vqLBLAJgVRP#)}n3_^8T^V7(utPXeIMzoPH9Xe;"
    "n5kU<Z>{cCRh5A3zbo_SVN<NG8@DN*H!txR?gk(;NLkYFEd8~~LBCF$FgqYNG2b&@9rV1UdXd(#*}53;o*b@QK|z^`VFUMmH"
    "Kcv<-(PL`y$K-pfq>Z{$9aO6+8n0<~+`&D>)*s~=Rs*9eZravy%xZ-Q@(9}b^V&xyBeyYbEB|bh<MB!D&;op@RDz1C54Zr(7"
    "FN6uqfrA=*E69k{o?k~wlSdi%Rmz7{i#^O3BOj;7D(43p>*2&cfA^a4hU#2v5Imj$sB{a|DFyV-Kgl_MeV6$-Ug}coGQC<pg"
    "1w`B(El)p04OVe)Gzec{{?{m;XQ6E<Q^=*GGZlBFU^X)u$ams!O#o?nkG2@5BxILm;0mP7uz3`cQL%CtpVoIRf`S9Epgj}ZP"
    "~4=l8f!gx*2ATEtleOxZ=9xc}0>R#cNdMk?aHUFr?*k{^pWij?R!dbTRuUvkca|;>a|IsoD~Cp>PGLoRsMcX2xjgj@2xn$hN"
    "o#QGP1zNZZLsF&7?ArpU5IuM+3y$crBm@)aV*3-8)WCsu#_z|3}ct6kupUcbK^9y8}Y68H9ihMihFqe4Ury49WJa6ekma)j_"
    "#de;8zvSftV<hFk80<XF*s5hY8`Wx67*hr88GoT8Zz;@@jbc*$+FPY!bm*J&a&EP`V0GuF!FI;|(J!8p-&?8(FZY>Nbx1nPZ"
    "dc0tLgg~>Rb4hWwmhqDal8h9vUUhK<3AElZEr{h<w433zhUXb{EBrc#%*j$*fj>&`cjHt$pbARcP;_=BdQtSe$x}8kt7J6V&"
    "2vz3roZW=)>1vvucLsB9T~Sv+|Fu#3*tS}66#2&<Up<JUR)Hn{H?*%nck7(N04rd!zam7Rbl5NONo#tIprX;s~&NPUUUAmJe"
    "5>G(m~H?a#8X*fB~;a#`a$sD)>)^HWDSp&V6IqF%)!)*DOWCH<}$3?V8Rdk34Jpxk=)O9bGBl_`LrJ*GlQCv&^9$9GDqym64"
    "&Fd}bvFpD-LPTf=gt&XAcw(z)V^?qzVTEYod^7w%ca@TZ*#y5QbUUh=}3*}M^4k3(n37pqN&|LZxGvYcxtDFl8;<dQ<sE`-Q"
    "=v)y?UdtyPd@)u@n`{(i;tU=kiB^Nw+8>m@tz$A8JzO8r3<;d-yVxZ(@&xs4%r7B#L);m+Jq^JtjYmPB~OawdrPxjm03%oRI"
    "+`xOjUSGR6FNRF}^l23)l_|sRPh5PDAB-(oj{ZM^9w%4gcOu>xCJPljHM2W)mLCI4UBfRpS6XfYW_GO>-_o!aj4%QSn*kYFD"
    "1+4!i{Biwv@jo$uF%5dim}(GfBD5qDX4svhsBQr6a-X2Ye7c2mTbEG^rw43OH3dd#%KGj_XU(VmqV=Qdi7P)?2~DU7&##att"
    "W{gB9cbyOKq0G=p7xOv(wF5JZQpA7~8M4I_njL9QAVZ#p@ONx3KFf^&Zd8>+mI<%j7_Rg1jCWWIW=(jjX)~PeFSIySRwl7vT"
    "BFlZYaW#LtuX{F;S;g8Kr1X8*-*5YsF`2_C}JoAZ0kBdkx{c7*RWLGQwWE~M5I%We*)Bp5ebiC5Oas?1H-&^I4Smgw_pU#f3"
    "tWibLlMOOq(j!}BoM^^Xvp9&o%p1Qwi{TTy$@1KYu10erfj(UF}h{Z>pJX06t<0)(?IrXZN?q^As^$XcA#YdDY4@cN8;k!IP"
    "H32;vQ~X3OEg0(W)w<{qR3fH%1_O|?*_WZDQIvCicd9?aOY4Oi^^3o__2Tcw8^5y-$1%iT+j+g6F!J;MO4a)~X=ZYBL80X!h"
    "Y^9em1%e~U}edNs1Y7+<U`^6IUBg^#T*0K91!*CQwCg`5~TzA?U5v3J2KPqLF8S1z@EtMcrJFj8+5W$p$A9csu$4i5D-3n`c"
    "7|P`sRfI{r1D<fcjnfSTm{)oAXcFt@nElMM+<#B2{1?3U$)lG8ur_WKwRtC2gB}&Nju~1NUy%GIL%fhcHZUluQz_1HTCNLhI"
    "qH_%cqKO}60~o!=OuSk}c4Lx7k)AlDJPXVi8i^5idtQc(YWu~;cktF(5hT)gh0NxB|2G+kpSlHj}$D5pfkCkMq*6WYTZ&}S>"
    "HbBTKMsD!e*mwj0u+5t@k?Ph5Q--0Gx$_5lySr@1ZM{25>xBfHP--SmA5rd|0NFGSWin-`k<*aRVxD>P`^iFi<zKE=tPvo76"
    "ftUFMFVl{@Ri6DOhg<nsoyGGuzKr+mxaV6~36@<7T=%Vhib25~UWXRE?&J4APb2luMyI^pUAzGU%rHojnFwCIACnDn{?v*%f"
    "<YKufOd>Px(hRWS22(Qv+r+P3XHW+UE4#SR1W_ZfCj~B#}T^lS<D>-H3h`q+7d&X3eT!0BQU`S)S@tHBO+c2<{FCaguw~Q)v"
    "b<69H@(1U{1A{GD48)?pM%od(>fr3?>5%TX{CmG=8cGq&wH1d28(+S1&%tvH?^oDs8a*JQNOep44rZz_)x1Ky$LNMULHMEb3"
    "T{812N#CS-S<58b06s?~TA-j-bNj={)x2Z_^vX@Jf@br^6RrIdfkcboYOG<P5u9BixJb13>wh+sfX1`GUKDSjxKDGm|q@!hL"
    "xbJ%R%lkl7+zBWg=cPQ?W^f}PulIM-=nX;S&;>P%sq_u3NkL{1xfhgLLCj4~jN+4_i>`lzncXN&&><DytVrD^+)06x7)Y{O|"
    "#$D#e4~^8^a%h>~uf&i>%l{SooN)UfUskO{tl+qQ`P`|oT&g9;_Mq2*-+*(s<An2uJ}uP@;jP}S9RE<b10T0&F40ef$=}FhL"
    "gli)hgvVqebnLu!RZayI(bC1gdquuR}OVdQkiR@uuC(!jr??UlQ#qkIoi-PXG@aU-AwiW)JaVDvjQ<eFZ$Fj(bBz!IW_aHL7"
    "6D!mD-L%bL-uE5>GM8Tr@Z~emElp>h#YmegPVod&6@BOV;Q%LfQEjxq+-X5C;P={9b~_huE%r<Szq#nmX5$`w5dw7c^1%lw8"
    "o?W9+vVsh_hehP&Cb?=#FfrU8AyAUK&;pj8F?+V)=Sr7cj(pPnO($y|iUS|Dp6Gb9mGh=Vqv|D@5q3Rrqtx0F!hJUm9hdNn0"
    "A9-_sXBo+W?f;I6H<6r<Uge0Aons&kHhGf5IeN1S0P5&{Sy{0NMYq~i;k&rp9-`w6-MeVrB+>?s6QhKuQG#y?~w`xbhoj}j+"
    "HMnZk)ClBo*ZX;R7Tp0~Vk<TyuPnuvJh6a6lY19YTe{Dej<#TnzfG#kR_B`(p1+$eRFPmJZ!cMftdaDq+wAoYR8O$0sg3_NU"
    "#z${GNSZ_!;JE~NC-7Vq4HW_%P33hQu+W~o8m<>)@2>K-pQcas)FiOJ{4${rCrL)^Wx+L;0qs?U6_WBlERO!+Van(K@(8c2<"
    "9&215{WSWfMG+@PFlmx^t-c;pp3HVgy}2zqqUSJe=g(CeQ^|5iVF^vb`HL{lzq7969pyeZD3fdy@zEi!oD$>#*7{$AzV-+^9"
    "8Kc~o91scvjyRr?Q+$2)J})Hf<n6JFwB0~G|P@=9lO&d_rhPX2*DuW#EtPe7lNdVTg|`S~P|39M9s-OLfV^sXJaTtY79Vz3Z"
    "mei50Zw#wkc=UR_J&cnS|9B=2(N`!h>3RTH@3tRK5mI2bKzJYz}#qFA1use0oPjx_<#Tx{kYCv3YBEdj+VCtR(Ho{)95*)+|"
    "<v3l8Qe**QkZ?0S0?C%#!A?B9f-8`JJ5!|L6SzY_@chB{Id*W$mfuOOZJWn0f4@Z;Io<ts=3I7>CWP$^6|kc8ub9}8J+qLix"
    "FEC`de$x^V=$VlCvxAJ@gwae2tB(#Mfn@0G1oX?1=u--_3g*OHWUIzI4->@7iv&KUF@2tCOTxpTgW;?l~$Di9cbH4k(0MylE"
    "*u^;+j~qWf6REqj}8|K%pnN`*CsmY%PXov}|N!2m~tA_SMb0EkGU}A&<+~1DrtC3Mdk4JG>5a9G7D@3WRm{o{PG*)!KaM5KN"
    "E@2xbTd^_21Anmm^=LB1C~PSu$DoOJ67zt%i+ty;(M@kbGqW>x*|E56giesr6@#<;VMF#6)p5waU4rM40q4#u%J@KCcWcMJ>"
    "}_f)h6KXD>u=AS>5=b9Q|eWF}1L*mM{r0wOa!rtQW#DvW5brEbLv^G(t5xg(GJXx;1;N5R*5d&>H^F07Erbcw5z<>->E7^oP"
    "${`Mhi2O}GD-Wfo!kobhvtNw$GmBu5m0<x=VytC{&EkTHaFpbZf)>V!^#Jxzl#A&Ap2G=lGsYBqMI>ru>@L*MMmj^rlqiG;p"
    "(|P}KNVs;p!KtB&P6xABxf~@lb24$#P0S|PJfNnkP9-?>KWOetf~=3mnS1qJEv%FGpp6UudU#vUhyPE+UBWl24}ebD>CbP$A"
    "vWdnO)GFoSYH;ut@)@<!_(AG%4{Dit+-V^{&A?%Qps1_K2c>Oi*&*p?b&E@7Q4lVxKukAI!?th7D(Pq3`_c3HJPf0y%|HeWM"
    "@H8Yu$pB9$!}_L1IFR!4i9wEUUtlTHB?y5Rm+j{+}*`0Mu`N}yhmFI(G*k!a|GE!!z!qOYa-qW+++`5x=tPC6E;vSJ}4v8h&"
    "m@WZT3ArixobOi*m$=K<6W3#2Ql4=3Fy<%67(mTQgXyr}MtKtM?net?0cAzaDe*Y*LL&=Xdx*u-u)Ek=g1zYGhVk@_EI!1Lp"
    "6EpH)c2Y~`v~<aQxpfTBi+V~*zRppPdH5CkYjlUzXr+$+%Ko7_{Z%)=0<*gMLmtNhm%H@38?blggQ?yPOi)`UnBmzPFs<85-"
    "Q+0$KvWlOwl7E_=>lIVBN&-|BHUXU%y*2HB>=2-n={6)2RaDTg|jP6A-*;7+rKd+8@<RN10?@r_(lm-Uy-vtB7&SRaX4hPVu"
    "kwzW;s^6L2um7vgK)%sgQ-IFwt8JUxQfMO>p&w$F1AL8q+ls62J6rn_tX-Qlx3637)V=%E7b`?xh}tKRnwRvE4wuC^t#e>Z^"
    "J|Y&IU#lhX;@s>FsGAf@mC>775U_nw#0teRXDzL3rB|BWVB{Kg*KP|RhC^e15<j_0A3sChQ~!%>0t-sX!ez{(m^5y1QCsR`S"
    "Jr{WEvdP-ap@v0i0IP1=epEJ6f@AFbV4}#*xY`&Ko=?cnOqEonHBRK(O0PC}FaDChpUC5}Mdm<o&sQWKr3?`J$`CS2nVBh?U"
    "K5)0lZ2D1zU>a!srgP_iB%=s6eVu(rZI)WtstL+=2{cu+sj{qNzChELo~YYVt1VZdnSIs9V_BpUT*QFr4Re~UhVh!1K^(63p"
    "z}s*_S@T{u`{cS$}d@Cb)d6a<x95u0J~TR#CyPndeF0x-^6YA@*F()xx&W<7Tr&mV~ojEzoEa^47lUc$nKR$d)n)E`Mrb3fK"
    "|~B^I@oRjt+Ui%x;xm7jhkw4^Vl~whn?nKbPx|ydQW2e$C-2*V3Knl@8xrdpG+AL?%9KbAg#B$Rmnk7yfH?h*CsHSBuUgN>?"
    "+#2ZVtTxAtnW#EwHq@Zk!hL&VJ@u@r^jrI?K}PLRkswy=OI0Y_3M0?f^X0fc1`wHvW($awyx8ESYWNO%pS!=vR|`|OMt9nZC"
    "2pj&Eugdc6n>w~o`Ahk>{G#8xkMnDn&KxWtc&!hO;61ct-d##TzhnkMV%-Q4!h3Xfu`8X)FRGWK!-4^NR>sIsq$Smy6bcv)B"
    "g65cdwLcKkggmTK!tSuPHUhEQ(6}7z_``9u2Cu??^$bjXI)nu(=T-SW&U*X(u25K#j9H(y-8Hi@EdE^hCpHkir1T&eu636_0"
    "_=Zcim&CCzptWwV~tJDtYLnC<MD(FApFnj$SB}Ei;U?mD>xM=$WsF?mz|csSc0D>)b}NCFvZ=)B&Hh~3x04X4rt~|W*d=_t%"
    "seK%&W|<Lc>0pP!}^aZ#7P9_U*xJ+dj^pkZ525;uG4h@~WCOv2cX*A!Amx{M1#(IUUBL-9Gca+Qtzm)W!$NT=yQ*kK=0`bra"
    "%YhUh$0A5&2-_0OFfaMcbvwTuGMHwg|G8h$m0OgE(qW<l}JSnb5xVa7e#T>53!5Nq=V5ZuJ>zFMIy*TS?Gw_<?j6!1|HdgYF"
    "CQpcch*%RACB&rr>+Shy9LWL6V--KlXqVnLv3+e->Be~b^rVTqtl*BEW&!GY|X#Q*HB2Qo2t{L7oph$XB+gXdH1hKzMH@usF"
    "n(&nH-WZK2m4<jJWo9*o-S8Qf+CD~!Z(XcSd3vlgBZ1{0$-v|Sw>tKt2MJ3t^drG!whr-%+25>!xOGHX9)G!uO>D6oNRR8G!"
    "5<OQ3`Su*m>U<0YB24pZfdI4Bj`zMGArsDS+*>^%bWX}c0_o}4PM$<!t93+G3kY&gvIOswF=cq><h1MBBA()3mPxRD6$~mAt"
    "4PcRpOFE1O)5DN7V;~J7M6&x18ID)}P?aUB>`F8;$P$cEg9z&0xffVL-&V5x+fE><_$U3y>5t-~{6L6qM0&fe~yrJ5us&jn;"
    "dcB3$15vK(v)fq3)^zC!<+h!Kt96fgf;J7z5S_sP2x*s{bSx954~65FzZA;V(Ey(JtQEz*D-RLygYYAu(Z`$5OyQkian%Z3y"
    "j{P_@(=Og^vuaz)nIsdJc2$PXMOr3>eV0WF)P!F_<H&fj#Zu_g8my8KyKFC3nP-*ot<(_Snx8ra6pYOk-5Z>CQ_~m>jBB~pj"
    "ED%@1K|Wl@E^6RoE4&dAsl~RyudJ7E!<YDbbJjpT?PTlsh&nAb_O8W`Z?^c}Zs?{ELymEO9AW-@28cQ`(EbM&f^Jgzpg7EXu"
    ")tcnRZNz~4_L%q;s!ZC3=IeYMo*|hU+8tb^>mwakf46QUEi)Mw`eu_(si(NSMtO>d_JJi;0$jTVOVya;CGCGlM#JluEnrI5_"
    "DYXRHdGt?GFlUqh?5~NoJ(Xp=E^usVyO07_+i5XV!Rjs^;^erc_hhszJmS0arzIBzJ9+vb~hGmD<4};$wCEJQTv^qvsF{B&!"
    "2RlS3QA;JWj}H|$tKbHG5qkj-!9RG)(M2eS;*A=8GHC&uxZ*epE5D(E%Y`~mRn2d(EaC{_JC00;meB`TzHVJ&#Ka%5f8p`P!"
    "Q%xm|6a{vK<a2p%y^}dkZ)hdTRlZI|SErlx%pUTNaSAJ@Tw$$>ZNdM7w#l;YRIL(EP$Qi-@sc#0aRIV0k*5Zx0v9zMNpU9<>"
    "XIbd_G?`GWnw$4aB~P!+`psAvaqv};>>u}LVhXH|uybWL%;v}!9#a$1btk^#f5@<yNM58NA=p<V>f(Brdz01~k~8i}6p|{Hb"
    "aCRpkn9Q1Ut>r+alOW_qV-edguIyk&Y$z%TFBccJ>Qn9y>G1)?fge1VhH0DkhbQ4-U1u61e$gYY;95*6hl$pU+EfAZ;l@PGb"
    "%gUG794+W+=QI5i7kcjiw*TxJ`@^%2Wwam;Ccxm+|y=cl#{2@f|=XVTA4<^T~0HzlOT#o4rjDIRJ6vy+yU5XSL6Lt%*w;Q!r"
    "=0<0iNxRPu_!oQI->Rhk?HCJ&vpRC9&38QsVd@8Qz<)V9Kf%*~<NA+mV6^RcJY>j}yOW!Q9bDOD=%1!uLZw+{)~08&cFAcWZ"
    "Uue9&Nm#0`j4r4)F9OdKLAJ0B3$qm-O@O9G?t`&FMGZZFu<Qg;fl%(&keH(O^5u?a=;D`rj6m$DQdRAm@U-i9aNZt^Izd&0%"
    "^9We`6$Ohne1ALnDqAt@YkmacCI6T!dMp-ETgB2g?$g<<B+>j^0U5rvU5(?F(zeN`x1N#hOHmCWDCV;zt=Cu&#kIl(Ex*a0A"
    "SXReCy9yO2XlL$FB*qgxwV=#!2UG<!X6e1BL)FADZj^ZTND@oIDtfZBk3SBqsoB)i2Lj2c?|%d+`xdh5Q@-;rl8&mJVh-+GY"
    "u)Otp}Tn@C9WL5$)JHUfTDcISSN~Kp{k=0{~%|u6){kjRp8+ct{<BXThf~QvQwW31jVki3PIRJ=iE*?T}l^>OtGvAs-1ygdA"
    "EM;YC*UR8xhemHIe#)n{_IcU}9jvtj(Z#hs90w)6cAGe4F>9PW4d9X1iPi;lA*PS<xDrOEEv=;&A>W7+PkoB`D-PEov4>KfI"
    "JBZl}RLrYHDu#Fnlz#jlnpt?iXUF~5Gwv#GMXGZ`wzw$c7D4g^c1AfZtAH&WGfe72ttUi-uK1gol&&-9rD6(o?Ho@HHbvPOG"
    "PQf7JLU;+aiZ>Wm6U1#};eCOk$Nq6~=1sicJ=R1{Z3DD0cIq7=u@Dk~>ueBi`wEhK``{-vme;feUw9}6MeN+Gjj;oax2|sd;"
    "ctw;f(gUu0t1}>#*d=2KQlUvR`~^U6|36!t&3x4sNR60a5^Eq-VUCY9Wf`yf&`&-zX?oUJT}>I7kW+gp5gEV)88Vg1r)U>KG"
    "^<T9qg+~GC{F2(w&oLc3QB$v7sO(tv>5L=TsB@Gf162r4a!mPPWf8Q0ct3V~Lc@$Nf0Kz_G2Sg9j^tBUy<7Z}q*>?O}<mU;b"
    "0458uD0FA_1^HLp6ZqW{E_bK<9^4NPCHhE|AyG?f8tqIZ!~28L)u6AngYVwjI_y!@LP;uQCz3Zwy~h?ETillfz!0(?eM;y2U"
    "f0n67Xt2pTN!~PiQp{{>;X4Abvc%asA<ay#B(aNv3hfg@lz6_<ZBR(r2{=u&(#`wS65qT_G6`}J%y18!(-^HTT{OFJ&C$JFZ"
    "&%!_qVty~<r|SP+s>8sFlJf6V+FGI-Y>w{;r&TTJ*}(o}OLQ_5gD5B=^HWskh!t72XB$%^Hq|6zT!yq8kc7g}?ZhZ~mRjv*l"
    "*jnO9y7UnzP<Q)acn&L!W;GZ3pT1dqz;Yl%Kax*d^kw)$lIE{D2dl;)Qz2fNsQ_Kb9?ws-G-hfb~~!=UF@FfA$GM5UkovhxM"
    ">EFxy)r6mh#U}Kt1z9#O!eQnqA(fT9yRyz*f*rK?Y8!J!k#b%enabKrsT}D?nkBkh6GaAEt_H;TT_y3uFcAL>y94M_|iWdxq"
    "iGcpRh>N%o5!oBvC!6TSDi#V+>$kM0GrAM)G|5-k7}hP$#W$bf+FqQs<LWVPfp77B{gn<kg!xkRRj25G}RHJd@&;|%6Z)m_Y"
    "ixUO@`W%Ef3dkarN(1V~I7J(OA2jH!<gE_M#fSJHDb$lhhN$`R9s8EDmrgsf@f;EgI4nq=Gb{l(vEyfL@;vvRKT%dmt3f1OQ"
    "4<dRBRh0skU8GdoOf;e4^nBNHAu6(?oL|X1`qoHwsQGrs5uLqE=;8BL#s3lY4vuklU$pQ{Y-?gPw#`P3oyNB9WE$H^W7}@fH"
    "j|{Wt;T3<^Y-oU`|kY{p7ZRp_FCucwaz8g?cl{sFD&u483D3>ssOQ0J{5L@Gl~gfLaa@>bxcgwU=o#>;N-~%jai4j6&Z`~Pt"
    "#b1oE`W6ei#{Bz&zxY2d{BP;AP2#;|fo?FQ$Z<=-eE8DB5Ggsgbub+WG93-H&BI1K!deSs)gSc<9tg4mkqE#*`<^*rG>WuPF"
    "1+jD4eLs%yo1b!-r~2~k@rAhNa$ancX?9_fS9RfktM`ia};>j9lGxT1|q#K@DRHOl|^lRux2wtHGvZPcS{Ga?=g$80D9KH~2"
    "?gGo7J7%lHcCnO)!umK&@SW?a1F$tH>;j9Qf8F}xWF@Aslj%=|KmGq&wZQ%}jeMVZ9bhH<-V9;Su?!7~9h(-vj5AZf2$H@jR"
    "dYJ3brEZzXM2_@i=-bply>E_c;dX3@<>uD+n@cAKuY&6_qdWW7nCP3v;MmkHD%Z)a?2EHu_)CY5S-NXP90B4?p4oVoH2xB_A"
    "4K81#V@XQ&pRK<${xMEs#i68qH>}41qtS>t6!texbsNu3P#hmUxMf<N?^P|6Q9r%nrPlcFR==IjLbJD9Nx!>NaL%kMk8GT6^"
    "%L;e=1!Tzj2)OR#V}eYl==!$CJ?XI*yOd2@e0;p)-GXD3lodJ8FIOC?Hu~m7797#oDzd9o#kxiKAf|p%$|j#^R>g`yfJJ*XJ"
    "fKzle1Fa|&gMqin_c-p0=oG#o{4kd<P+3^%KGJI@%my}a61bbp5p{Jib+%E(YSH5f;6?$+)Q9>lKJbCG1{DMsuX<9tPzU>N5"
    "_r`@AB($TBxA)(sQaPH@>c=u!Bi9WpsEVbCJ+EDtfPc8&~&c&HO7_vC<z7|I~k@K10(W-MzCWs>p5mAJt2W>cDG4Sil<POMR"
    "oVd>mS7vjJZPyN^G+pi1OT`kc>G!nFs|j*%9kBbRj(Lo#nasACcLZy5dWZC0Z}(;^$3)~p^$(Ph-QtwJ5NtuA8<ZzZY>(z3W"
    "Tb^N*QYnX4mw>g#d{|lkrQ4c(=da&pg+K3i407R(EINM!5xPdp;rlDA`m1ybFio@AzbgVij&C#H2FZ815QNPB%khiIr$_+p~"
    "nY}-Ylf%!xnJ1^QkjxU=^=5^MI3&BgdF<P<irK;Iid8M-5{K+TF97s9k?eL_{aScsL}kgYst==MOZ-job!%%yZ;C2!;9d0Rq"
    "Vdx(sODqZ1`sb|b5iL~g;0-2rr6&asj<lqWzcVXXG#E#7v?-2%Rw3s%0s!-g6=|C)JJ>U|#>^X^s>S>Kk|KbmEcI_ZL<D9E>"
    "K<ssNjY&KmMmbPb5__HOg%wNA--Gal`T@+$1V4EDL;TmH5%_jbnJAnqASj49sRH2tPH(K3RWbletP4VWIRxk0cK^e)x+OxA0"
    "KbTSg`*LF#Q}FxO>ffv$PTCWg{|#$Thy7=0pTZUpJt#O0We%U)?K@<@=u4NpLm5@zIO)j!B%=WxgO~Z2S^`wf5;?Dm*T>tDl"
    "#7!+R4({k8BVnne<{W}o**Dl$wrqTNuHZEe}9~ng!`J2kd3p+-B^_K9!J4oG{gxHn@|nn{pr&l+6}>N^4QPJHA%InoWGR6l)"
    "ESX9u8r1`$#m6XA%3Vw7LeIa+qyv*xxWWy^Ze>KKo41P6d_oN962i?qayZMNFjg=5|1OSLN0;_N)U%bpAU$epd=#?|{lJ9};"
    "SOvLo(MD4IyFjN{Ct<_CTS@pFOqlT+Oj{~^ha5Q~@9(F`dKOEvvBj5uoBOEF_Cku2CR_1s4p_4M=a0+8<{s?YVCBS2#k6E}Q"
    "RyLbGi44wM3y(%GPizo~j@g)^FfH(#r_ou08sL={#&aE^m$lRCgZl5AXuq*lQFpv$LV{!WU=fY?Cm&>wr!Cd>i<nI#CjFq5K"
    "4))qoU)yBAvhq(%><zb;;xIumr*>u;2fkLDi7Bv7P`u_b5A;@~LkcGt&E_f2G`oH;R*goMDmR)VKIRC^N`PV-QG^=yzF(1hd"
    "XtjJ7QXla^jp;T+`3+Rata(|_dXskg8DEI@<i|bA-uz6q{CZY(VP!N@1Ohy$p&f-5&ei*svO{9d-{f&SwyTZK6{H!=@6({kg"
    "{Fy$y4}P9nk(xsu+(VTM+<6k@>y)c1(c^)i*h@yu555eBR|CqR__C;%7N^M6nhv&|>_$IjLv>o_!H}Rx=eeqTAxLLkZ6!&+f"
    "lGl;WSX=eeHyAdc8unICHbtQrc*yaE*#Uier%c$HI+Ww{d+QaXR-K!=Z~_qTjPa0KP{_Gc2i3PH0FWaRA;6}Fze=;gkHhv{&"
    "6dv^~Ut=R$rMbGk>rSC-Lh+f30(C~qJ+lts`55lUF$2X6)>mv>lI%gd>xZbVaNHxG%PF{OVtGd>uw}hhYr*@|c8tTynUXVI6"
    "SrERd6<Cr4$ihZugslkEtbFsGHKqy2*4>lXyBElM-mk}z@-Xls<X9D7Jm(706Px}+pl;T}|MLkfQ>w2<z7rZE=2R`>MwK|q$"
    "6_-9HZ&32Gn^|5cUj2D-J2ShRm-C0rWK>2x}bU^No-|>-rfbHV^oWUGwUku=bpwcvJQ4oZDG{L=giW6tVhM<2Y5z`K#5}<!~"
    "K^qR%k*wg$-AH&`ltnIK+f6&G`8xCkuk3Nodn1E9149VG6N%;c)Cr2}GVnAXmuubJ+EALZ%@vhZ#)8HlD_LgH0OS8ylZ3p~l"
    "AC5FaR^9W(`teVVuW##iTZ<&7_h=yg*BMASy-JEMCmctt>i)!7Z6LQwO?{xOTQ%$#C$Ufihx6GX-J0Z;tAV_`Ltw7>SMHzx-"
    "U+ndLFOL^rh;LDRz_I;W~!S;g^qT?Z8o%?M2+7Ifxmp|(n%7}A0h<MNVOAI?N$6J_gaqc0u0Ga!N(c)9~B?X75&IkE#n?mk("
    "x3dY_PhPt8Z^!II{t0763IXX)_FruFccd12@CmOo1Or6LmFz=+rh9bv9Y+9+bluR<QtvT_AIDGgDWmSUzJHqq^DX|r&<U}Bm"
    "a)SxOo<G-i8aUPiqPk!My~By-~VXff%PN>IVrak&xeLr?)I3n^L_P2_*NhU`n!oSM}f7DfN4bD_}o3IJ-@Uc+F|;~L_C*jF|"
    "o7;P@8<dT6Hren%Vsm-+%EYplm6B7j9=OwM~oae<-wtXPrzS=NwGrbU4@Wi_X)y9AYzI{gX(%ivy5{7hQ=J`vyqGAl8L_-%^"
    "4W-|2rK`7O+3;DtkF7I9&g3xCl>f&RQpKqG{|O!(1|znoyPC{S)#R3u*YxT8U9!?BqFGotWgjA+~Q;t33*C~xe`y%0&hlO|L"
    "lF^roKgx&pus`eP*c^+T+XapV`sC7@mdOg>+HfaK)Ft}Aie-VHo;Cu~02qu^KM_y?#9E5dL1_DtfWGJxavxPG}CD*P1xLpW("
    "&{a{gKw_P5!JZ-Z?>)Ohfv~K7n3o^!nqoZxp%Qv>hw>nJhTd}9z*0wf+~nAYX6~|6z0vw#@#lwXi7$R(HCwg9tHn=+#|Shs;"
    "%sB{g6;lH31oTxgx%WwbgS2_Gx&w*VXwTS@AWg_Rr8EQ&}ryN9#J)JDUZrH^06}?zFxnywZZ{{FK;i2=#iaj^|^_c-l{}VY0"
    ")_`AG6R4OI>(M5R$l`EG1|7(F60t-oCJRl>N?3FN`Z{xB^54MWSy5C)$oSI8|<g^{6IM<>uSBK@qflC(FTN?2<O@);m#8CW5"
    "5y3VkL#KMa-5lB!<{9)iYdh|7pMVF|2{*9ZcW&{rq%uPiQkJ<j^CWSXGL33SyC$qWm8Lw=f_2_}ai#yKaCyvgIc$PZAm7?P|"
    "SP=8lcT8<3WfOAO^&H&9a*wj5n@wGep=!NkO7yM_7?;{SFfR9F}`I6}@*<<WN1<)kZz?k<C(Q8!rpnbFAT9*(fw4)W?n<X+7"
    "cwD94rEXhDJ=ox`nvZ_5;)<Kr7^Br4CrDiGE%s*a47b<;Yc2#w^N~V8{*|?g_k7Wl#Z-9qir2m6NcToKu$7B8`}B)uJl{m33"
    "jxc62&whr7Bar`z?PO%&txj$LyI?p6CL`F?QW72o5BMq7LMg=CN2lD%7Z)vo9%$5Kv+8P!Asw!fQ&_Jq&Xg*-cgFMjc87ngP"
    "~cv1DbEj88#1D_hEeVNcO?$PtjT4(c3cjk;M@vFPe8q=ey?`Tp@HRHve^)iUSs6FnQ;{mPpZ5N&?8GOJ~JSiD^NUx#Cy<RuQ"
    "N{SgZv=(1&sL9F(?i<E|}VBI~SA-GEG(_KuSiRUDSfS$v~vi1{UszXZ_AZfjZ8PG)P!i3PXNo%-tAFis%JhAM;H3A>`LjRaE"
    "%(I-R`5^!ifWc@kxON7v$4BE-LT^wV<uAv*YO7J3G6kgV=XKOxn)5Ei&eTkDD-B8fBNPw=IgwKxbnAwV?gj8{u!mx<!3WfQn"
    "@2IU0kn%?-pOYWE?DEUZyGT&!w$7QUddihlOwPM3Y`vc~avecg5+{hRdbU(%`IG1<Mc>^n@Auy^FW^KCp!@(%-&I|obGUy8F"
    "w1PVpKOXOi?R7}&9E(3rc&>K0`yz4$6T?)Yzb<zNz9_IR!)5t*YhGd0Jc>GVlCgSgZ^qvjeqXX$P2av0JFT}QoKk8zphv3l6"
    "*#V1<DWxZrl<yyi!|ifqIf)rRJ<s(X2>VSCgXtucj(%XtR;d$Wg#l_Yqgp#CN8JRZIER7H0ZY%gSYJvzdMcM#yoM=8KIBt7Z"
    "HnR`LxSiqfIlBk3QmI=8_u`~?N>I7R7BPx(We8t=N7t}*L`KF^h>W-rYaEt#>T($r6VbunKBEo42~p$d)!>14y1c7~j(^9Vf"
    "Uhor;XIbix+I<&utW@=8Kia0r#_hx7xBQ0pSV%Mr4B6G}Fi{;wVHkoT8_cnwUkUm(ue3>2V!(Y9AkiABL<gacSSP-`>846C$"
    "cO(k0dCr`7*+-c)R$_Pkd&>2P3gUmIq*nSR;x^rr<DvJHi7SSQuCr`mdTg@dPB-*?a7OHV4|T>sge7a=t0DAkT>_l?8u?7`x"
    "lPhf%@U*f5A*9<>H78tuj}8m(ti)&IEAEX8Kk5A=IKLSh6*fn!!a)PSgOeFO{|Iit8nVj3Qzd?a)v#Rqf+xE%o(#P+-t(gK#"
    "i|Z`vLW>E%};_`?w{1vrjb~6YeU)G@0=yj4t!v&H2Dgci%YMe~oT|$BaWeoOLqN`avPZwr|CDYWE>ur8_oeG#aj6yNtM>N3p"
    "eXtMkEOP@zn&H+OMw<w?ny1q%X`P-9JEtp!m^ZBLj7vR~-;clgWWf=<S^UMHx<o<E5xoY~Vh2}C$b=bO1@#di0Z0|*+sFK9;"
    ")KGo4Y)p7!E#xwul#J;3=#p6~<Pht-1YKmmno(iv=)eJ`8hGs5&Vkwo-P^1k_$j$>p79TtrCxUyli~SH`(aqLe>hsSwNatt$"
    "n8c=a4{pr#3c>TosXE;N>z44OE{a1i@0TDEq1f#$`9-&#HeN?WvJ0|4ar0@L>Z0O`U>(pGIgc4a{od4@RQH6yuk*Gn+#U1uP"
    "{XWAp>w^-Z3vVyhR){xaQi?_I<sk1yXR7N!c4pe<Suo|pU}5ihYjWMR>y)MvX9rVXKQ*Ux;Hivj@ld4EZCpzy?jY&7nvy}GZ"
    "d#J012=wkKUvrc``%^BQ$SLc6i+w#NuvOs$yfO_B%#jJ)PSf@qD;lB@J%_mp%9IO?`!r4BvF#HKX1D|KIE{r8ES+*IL!JY@Q"
    "Vvq97J4(5SP(2V`+|tB8*cPD0oObA~BToDc38V!JVve-;EJ)1O9{1mDY1RgXHuEHRjmMsLy-#{|47t)_bP5hxdmV`rERW}MY"
    "waDfAcHUnPhK6^}B(qy4Cebo;nG33>d`pXzC<-8;^NQ1VvQVVVR9Qs-k$c)GBhe3zeg-O`-kxh-g0cUN0%+xFZd~}tpl@qCv"
    ">04DW;2ur5pai@K+u@N`)n(>o)$>EGM6db{L#I5#L6YH}{HZ;nC`8*I;em(;HpiT#kr#tW3dk1w&~<vRihYAF>pef3;=8YCE"
    "~Q;C-vaCq#z7V@=kZOT2?PJGmm<%wN_EGxQkxP~w@+4LB*5T;xTS0{3>ZxD|5%jd!vo_bQZ2Fl46;M-P2a_!@mC~wcKR-b#d"
    "4nGDy8`aS{k?n!VoVcui~&~25iY(KEXi&yptL9bi*|{5}<1<oKC)j&SGdtsaDGr<^1$?yF!+Uq(DYC`bBOr6#;1%aaXSWUW3"
    "2P4*jkGiZxJbEkz{y%?%AyvA(yaR;1aOoSe$sAOFWwb;nApd|Pr*3bQqHPW0&DU{rx0PVxX{Y8h)lB_RiJxd&?fGkbXdI(XW"
    "jAQQbmXllWC2PJKv_{lv(EEiE9oIt-gNI%%OCT{)k9`l6j{jQJOihSSeBs2leG%$Iw1B&goI@gUfv014Wb`vfn@B1YQofNV;"
    "MY`@*xBWyo`mfLbf|7+vB#%VEWzLvRflC=78$c~ldgV$%Rrji()SyAtc=fCumSH@iVe2LFH+pk<iMUIQ=fDmb)49uh8ow%<@"
    "zJm2;GKI+GZA3-DzeqUo{xF<VZ|L!2yCW~^?1H-QuvvN%jz_3VHRzGwMvCupKV>n^<%Ve43z6g(#;z?u}>{i*Qe^}>ObX&Da"
    "!9!c~hRhK^;CWA<Y_yyG~9jWtnA?)6vOo;Gffa>13pb=n!_mUxqruP1+l{2QAEfHO*6E*vIG|t7Ad=<5=-2i4t3+?nhHS_wn"
    "b9zLKDF|DSJpEdHI}O3Rng<UdoqjkTQDb-X$3Z1_%y(73F0Gf)A9Xl@g#F17chm4|6akGU?Hpk8#I2_I@X!QOzxa?dR<D&*l"
    "RJ{08*<vtYfR8Mh>&m7RD_6#rr;f)YIS;aQwRB|WN5@1oUx)aR+ia~w<|NX-f8SoUgo!Da5yAdf!*a2)7Thd^<yzH_$lB_v{"
    "v^SxWkk9-ABddUJH@t3bA6&yT(NH8W6*b_8;_U{=(C12vA6OyG41%)J5vYXI6e=6I9&1)+I~$Tlnz@{bCd9>K;y-9EW+XuH_"
    "xfS@W%+}SA4FYRU)GkplH3?8Dq37EKxMYFOde;v7b^!H8ob+XYVKUy=!PO??%nqe=`Q)!i4d(K4@^P4WRO_Y>D(U{i*emUQ5"
    "-aT&L}+WiblXJ2jmgb=Q7=+48KTqp;WY%1NZBr;P?IwwTg5!3k`Pcwpq<w!eY*{vmsk^cBrnSx9W6NB|wtv@Daxc>ZS@K2Zv"
    "=+Oc?g||8+XoJjCf4G(a)P9==>*PL%7d3tLQ(6B1}B#n2R7NW2(;6%wDSsGs4BXC$S#xU=v%0~L!voSl)Ni&DLGgQzHV_rYq"
    "}evUgWFMiEywHCjVC)q%IO|xE`dr4i9Z0C3Xr1BcPi0^PZZN3w%6BcJXg|=81y?gj4d;c;6Xd)i>n+|e(A&UU-syE3IR~s_3"
    "_nY+P@}R(@v_@y>P93PjOhg)inkIF3Sg|K9T_T(`Jf<OqgXSH%=APYR83C995IIz#-E#oTv?r{RAnDJe#fz_}pZv>%5Z8J1q"
    "|NqKTaNz#Rn<{HHLh+k;UfVU%ByFY+nPs#C)ZVM%f5HQ0`6E9V_(?t!GDn&@jnqfEj8DI^u1R>v@<hr%{s(q{UyVukeR!LhN"
    "2G3SFJBr?s_e4f5Ou&{F95;TeufC%RmZ&CozuHQi`q~h8@qq0)<1Dm4}wYO&R&uG}ARHknF(KHeGP>d}{j-jo$Su3qE0wIo&"
    "p<R=hs6GB%f#m$ECN9G;K-&WXof>oZksyA1MTcs1VKF?TV=te1~AnjFWExU#KB%;g&TBe?OKAd<9m1Db%<qCIyVuui5yH0D`"
    "GDrG8Fq&bq%S}OpdUGigEzxjvwXA+@x>+L|UOZe7N40k0!yI_sHl@B!rw6Ry@3p3ImW1$GST@H;ua%*myaA7HtOJNgti3bV?"
    "l)#+=Z93YwoS#%FW?|%!VgCzl642;3b~-;@uL${cE+fY_8ZSpjL3PVnWM26jB~%99*YAR|dXeJYh7U3?l%Tp#i5==N(2Gri)"
    "KWW=Z$?DsV${Ti<#8{c3ExQ5qie$GXD>WAvWBdMe`?l32A{(e@42$1H?+B!m9SkaT)i#0Dw9s~)#<C1OS2%_w+XhMICVCcIi"
    "3^po2Uoc(Jg#^_v$5bKip~$C?;C3plQVz+g~~am}if_``4|k=t~0gT;Mp^))~+6*(&>Am4?xjqS4N(7B2?(w2j;DxL$No6BF"
    "o~Te>VODc>c%nLZGIs~X+!^{ZhhM@H|ceAb2;K8ii?QAaD7@Wl|$o2~yRFpvwe{^AFd?t`)mEno-6c)>h`I$7#ttLd#SMmc$"
    "SeYN4VZKg~6P`lh}#u85?{<0NOpZ71P?VP-D(=SpDcjn++(=)<y?IPwP@o%=A)XRk*71H*8cIppE@%lGgc%Gez{INd({HzrS"
    "m0RtR)F02$68ssuV7L*c^=U&kDC<6|7BbxW>o!;6-e`nQ`T20UE^M{TU%4|+KU`FPra9{uJhQVbU9nNYFw|HBU~swzS{(Ylo"
    "Iga=NpU-F9rwZ53?YT}jq2qw0<`P1VD^HIsQ)5+hg_i>;MrO0@sSq%q+GV}LgbJ)g;>x8rvW!$<jtD!`@fXUAOEWX5KXX8Eq"
    "M(MX0-WJ;VDc*<0{-0-IEbuFvAsK&H!K#?B8C+g{h@oX2mrOrwvKRE1Z#?O&XhPXT2_`)&5nNWK;_WHfan#Lj6!n+-c=k1AF"
    "?Kj6yXQHfutFrvLrhBNxMS{R-|zOupB|j;<j@Wl-FrF}a`w^(TvrRpx-Vky>4&RNNJAv_*{#8UAoll*mRZ6jROZw_G-pc<rT"
    "*qUxKOTdNE^{^%#SFE$T+u;|JKQLGQw56Di0PKb9~ea#@QvTl@V-(-q{o438(0hBw4I0%h+4VS9s4=>1zW`4tbtMr>IO1?Il"
    "f7;u*UvroK=OpsTz<*dNj4(ar@RABntkOZ-!8G|UPEDH?51>&p`3jd&NzF+K7T7-Qbr}VW(ie&gtgJ?=v#!SsO0Tqoq)uk*$"
    "U&Abx~D%D(%Q>5gc`>>j-{1dp3^8L@r9KIamvzHl%N;)01AtbN(%x0_dhXTboWfh@&l0sv#!#vx}*(oY>CsT%Sp=4{5en3sa"
    "-Fh%X-QU?&<d^kF~Ozw6Jtgge?GT@Qq|2ON)=SVz#hHKsB)=JTSo(1KpMCufjr8RXYYfxflC+(7Paj7iuq>ljvvCV(Y>xVu1"
    "W^LB<%s4@YYP3hz~`*8jMww%*!)8w~@dG56n76ut<-0)~<@$~2ui0F(Evx-Vo(!Z|or;7qk+L~}r`?TfTOqH&n)LF^LG(Deh"
    "@A2ClFS#jSkB%FS}K27@gSz10t2N<>YENpo8^!52?X+zvY9-)mzP1dQ>SqLt3s~{X(nI6-AK>Yr92<=Kjq5tj*$@33q<cM7-"
    "blxp45QpKnK>waEM$U>%J<($df>hLxI>X4+D<Y>g>?BAvblwR%=|gw2hAP$EZz-AVF_uG;`8G~=FOQz78!PMPWx>l1^S&$$L"
    "<sXQ8HNrrRV!}*D+Ba|OPaTV>>jdj6I<LVecpranCmCnfJzwVv|yA*1}OYu=T_jk^rE7!hb-^B(ZJ#RNa=#ZGEvn#BQ3b|D>"
    "jUH$v@(HGi5WrqcPow1Lg32HIzG&qiXZ?jsi`y>|^^Lv2&3c_y<D@q*lV64%*m{eKhNI=jzO#B*GgHJ{aX{VAEiV$RGQ&gQQ"
    "24*m;vq;)5~K`>V*(3iu&|J@-h@4zAszCGtF*KTi3KD5)ni_bbbf^NTp|Fuw4@vf{yDwov+-GlXh$>T?4X*6t-F`|=4_**Yf"
    "@r9u~x5BYk_a=pH}B}<kW>g(CC7_VBVB8mw<=ui$cn}S$wLjTzoB32cJLU}~CjF7mLdNGyB6FCLXvew+a|9cl3*6P+vk{=Lz"
    "y;ioG$1Ai;gAI8}pXOlDGs_bAFJ1`Yf03HVRsm!lykK-~860=6ZrXTrnHT)B_iQF$L}e3j6N6)@z1Z4oVrF{XvW2kx((a6;J"
    "zDq+`=FFa<U|{f$^zfLQA2bIdz!v6YW}yS{X0p;ua9|w=ie4FVJ$rDCsJV!{(z!m`;HM(1<`)mw8y>=pl`lp+MIm&UC6jQxj"
    "@=q`p6EG+d%6d9#OlUZq;AE>0h1;-Lc|PKfu{I;dvp4`UVT4-~W_yYs@n6P}K6Gy#*~J^`0py57!PLn`MHyi6j5#W#M{f7+c"
    "7bni4`DqV;g-Si4L63{4rKW+58xA}$DMPn)SXS_tx5eYp(n`XpSx{zoRL8U=hU_oA$p%qos?_%F2)Mq~mW@}04Tz?cB@i2H5"
    "+L!W{gO5qk6;R}sAM0I%^a7PI}NYeHJHtO^v>i7ibLy=$tkq<BveE4>%Kp#^dG2U#x$<+uEfYW^r{N0oTuwfngCEw=g#ab1z"
    "f}yXUaqm3tOzI>Mgw$=cOv@f*IVh<yc=sDD*q?G?i$ygv%~Qc+%m<%JW%HxugZT)*&H}?CXN(1=QxeIzQM?J6ok>k!sc}$S9"
    "Rk~g;4x=LC~cTle7+2r^TM5|yB^l#1=tOJyIlUIa`KR;QOsdbKR@IPLk#2AU=C|hWMlj934*8SscBP5P~Y)bR37gHxWS(4yA"
    "dO5{-@ioTphrFZNl%bY=I#aS?$zShSK~XUWzSe2T_?uuz1MEk@AZ+i4FS5LueYF5yIPXpFHWJr)HKHMA*IBj(`rYsL&xoI5Q"
    "+tM}<7oQtNvfhWwd(x%xGhI$eI2Jn{9o+>feiIH0kAr;`+AkIgM0yf8lIoPabqdo?5%il{^DXT2vG+AtF_Ivtx#IgeMW>WsR"
    "4{a3?Wo{tQpm;s+>;Y(^JJ4sJ{UtwFHhhG&cPtOkt8)qD1<(N*!V~o_$@PYKO8b;{1BwF>1eL-@*eEThz1+$QiNRYq$8;$=T"
    "4K%VWSC#GyYH~i{CKJ_85S7aP5XT)=NDj|QmxGsLwt-tW_at>Sufz_S0J0c!X%1ihtr4oMI@e#3JB|DwvrHlfqm;Se<;5dp4"
    "o9fnd@Cm{+*H9&Au&!zpd#36lHwys_)6JE@`iH#x^p!u74@nFr$cT2je41wUUebu2+IC5+?S||aQZjo)CC<^y}m!u$sgNb9P"
    "98dcTTw80D=Ik&q^mhuy|YYB&L!Hyf}P=<_Tuvv$JJPljX~fXg{%6?07JxcQ$^>!nFy1O7{driYy*o;Uj!0OTEYp-BmLx8d0"
    "fX|AJi<0-ufgB6!ckWtj({c?Tk}Od0>6ZwFMHLV1upev_G>+9EZDd9#NX`%E+C(Gh_LICu&&qWeL@F!L7@NdDdFe$3GQJc#q"
    "sj^5ZKB$u9eMTcZkjw3}<%B?fZ2DE^gN^Ex6QuHqgKxG-U(cd-idz!(Oq2v8j;}jDafNWC#3x^&2Yl5AemOnTiYXj#Y{SxV|"
    "Bqc3(d1v*34v@Ch_t5|N%zlJov-cj0*@|uQh>#5R@+qAOzLAusnZ*}RXZW^*(CW)_l!zfp$DEALGR5$p<m1odxF$Bt6?XxY9"
    "B-Ohi#~@t;@w|lB%y;M1y!o^;ez48#(0Tyf`QkYLw_RJg0EE(4bG#qyv97uU%VzQ?`04#tHywCo%3!->!-(P0HT8%N(58AkI"
    "gQ@<XCjgKceV!kI34f+?mBGnYT$^(e%*6JR<H|`djFcngImiTgLgW0J^@UV60Va_P*dJb{}P>ZKX3RvWmPj8k1JCHqAC!h8t"
    "J8<7EL$V8%RCBR!+;SBpiKDoQ7(K=K~_`0uRj>iF$$P9Uf8@tuT*02BZEns~#A#cLVWDi;(tcoK>v_0~U~*8D3zr7GQ+^q|o"
    "RI^!7sJGmCbnlrRv`R_(g@1|WjcR7zwH}2~VGP}E;D+8uW_&*1r$C?0t!Xog$qmh2ZCcCT`?|OvVTqDWMEIH_YY=0oV2gWv;"
    "v~$$F^Hw}tW!#ai+kM0oqkb5qGJ#+ej}`|qMnG!bidt)a{tpHIW6Q!Y8D_DFFA)Q^6;xt+_c&-RROBZNByD$Q(@xlpY;fIA?"
    "43Zz)H^+x!G5L~g*pWpKfT!=t7H6~ZogUYb%)|IcSzb+Z3>VQ)^&hlJ8xI@{Puv*h7&hRKfDM38M%heSNYM?i8-JKzX8iWB3"
    "Q?0(&^dl>Gj63dA$`D(^{Pn!=e1N!Wg9&+nE?%bE|-x@e&#SJ{Wz2;iF5#X@s6Y<TH|T(bOg#oN6zJ_I~Nq^dHA=Up>B_8Nb"
    "i&^{0EYbul7@s5ZY0n9_G3a*r<$&0R!HsR>k_1M}X?R6Te`#BGk?03p0b{e|4xN)OxDw53CgAEJ*UG^$^LWtj=h@ewl9zuv8"
    "tcTl&H{NHn8(3L!<@}31Yg$H||0y*Bkg=5tX@e!ogP5c}Up(tP3m!^LkDbU`aP)8%LQ3H55Y1aA*R#{MeuubxMjqNn@t13qD"
    "Sw#$%{pSQ^0vAF@mc<j(o2|FtBN@pL&V5+1fIecic&R4CWoE&VIka}N6Y@Sqen@#4z3`q29qfX0vtNv!QcaEZ4sT1I+djWcu"
    "`>}Lzej3a+r{cm8D;*YhUlC$$$gANsqqVc>;A*6Wd?%&ch(>{Iz{8vB!0S}N@qOB7!&<Yy1r@p_qr>fB>lmUh#`S?Mn%A9yI"
    "zPdu1>=ZVj4@7oW_?DJDjCTs;DvO>(XdWfW$|YMc?d?<sy>WpJiL5z~Qc2u4LsI5%_CpKMy8%nro3C;`ebM!j_RNCxU<%`Ie"
    "9m(EDv3mBUJqE!bQVZNOr9klMEma{yh)#z0*G``6%3?MVuVQS_q36Zd};ghj0XJ2nfoKPHsm&QwVXGvxwe3Rgx+r+Hs?w2VN"
    "hI7H3u?mKLoyzo>d)8wt<TCm~lo}7FVO0nD0>_C!}pmT9yMp@DfkS(EZW;4(<fMy(dGOVV7G_6mjpBsNh9_E0xdu1?_knt46"
    "YVCyBg)<V2ob}tk(zRhzVJ~jyrzx4%fs84KByZnP;x#fQ+Gwd=VVJ&JXeHPS2-814MX^yaOt8oX%=UKg-2O@r{H7rB?XX#rn"
    "rc+^r4#YhP}8(fu+2G20Nt68G!NUszit*{<%0RLtV8~=DlXtE8Ja?GlEBi9aO<T|mTRzSLM&f)OU9%Kc9dVA0<smu079hAU("
    "`pXgUM(9xz5!p8pRfz(ejkut&%7<6hETOV&R(jnmSRpXF@V6!m_G%KlCv_79F8W%lPZfO4ho-byFFI?})>r(lVi6#$wtLc?o"
    "Q<w%&~gF`DYp^xjj@XI0ejQQT6fv8MH~>)g9!SY6&N%!+xQ-z`7)ia)x&VGCr@3yaZ4+>{(;TYG&TBt8(?3-EN}_xrIYV_A4"
    "fCh|iTZzz}nT;eH4iP|4kX3gL*@GbO1>n-cF=LedO1kU(~o$nzsQxH-2{fo>AuD}BJFQU2dFO^-O;A`_2^bZz?ow%`(>5V8A"
    "_436y+l`MOlOT0G;9S;i`doOJr#upCpqSh{Ekcp#ztK{GqHxZOmV&7*>jsqpJ-z^5C9q?Y*MqLt3}vx~CT=E&01&@J2aF4Rg"
    "d(|h7$pudceT9Z_xJH8?E}H%UlIq)&c)H9W_hO*hOyye4;@GNOa@2VO-f9kOWgp{vwa$V-`83OG)}L^9WnSR1!$)RN*Frhtf"
    "0L6dlTf>#BaYeTQ!mp2s)!0G8@kQl@Cd(#&QIdzSDK8+HEyQGET%{Ha%CRq^kqhVvwg7rMZ%l=(p072%iy7LZZTWiSHtnx(|"
    ";6GeJmsjyv}y*4w;$w-;7<P~ON0XEen@oAl)QL^7cAEhIe8f!Ng7@%v)3LWpAquwVdf&s)=hB%v_G(<*-E9WnSb&c7{!?(tI"
    "iuDhnbR43n(qA|}U^~&=jCJv(jq#vu+I6^u_zey6Wa7PZ_63_a9&1jh}p3~!JS>ID^h>c1OM}X;78GquuhmYW3s8?f;{popZ"
    "iLDjporfr8rZ%>VPE~?mb$~>B*lDv<0r+0lswf9=-MON*OV~k}EZTHI;k=Ifmdn1@9S7~Axq^C0#1r{B!>M#pdgc=6Oe2dY`"
    "ZYZ)-|0sI2jIp8#~P7Ly(xsVCInlFXtKk>VB;Ns9VPIhmo6}%3J`Q>C`M|9AUowG2;ro9Q1usIe8-P9w%i3E2p)${R!q-(*4"
    "?j1e4G~Jb!}rTPej-+c4ZDGk97Zc)k((E;Q6QJjJ{^JQ~kq)!rVqGY{qb1rJjanWSMGCv|2^pX1D%#GUrMn$lV{Nj~B#e5+s"
    "AcO8#-7*mHHN*`&MrWyXfdC9eJndl?$~^8VHw<DKOn0y4wbgK^HN^Ni4FN(FuEv7pDE3&}SbM{r|}?yh<~(;K6S`JIs+8B-y"
    "GD7c`2ogIaQ8-)8_JJY0)Z|OT-STl7YQu*@weV2XCAEnI49#N*14-g{18eB*p%aC-7f!=^LrD|9Am%*z&1{GV%tAAXqoI&ea"
    "jGHOVwwJ|#?gBlJy5mc7p2Vs#OBokL*C#<Ek3J#(;u2HhlRIjs9DrwD)T8R+vJi~OUN>Q46%6=qJ&67XnUY5SL2@xj^q8V4t"
    "_0D*aP?$!h0!@0Pe1IK_WDL!ZH;u|Z|zd%u0Gyxp9HQ}NkrmAYYZavMp#Xu>gwJXDo+TfZ#l{>r0dhoFOOXn^2E6c<LHbv1P"
    "b3+oZ-J<RItTArbFiYd|u{WkRQ^1XGrQ*wxN?x@U72!LoI4aQxIYC=MLH*Z8=!U-<wxPMX2E&o~g`a&+u~nlwMGuWAEq;t9("
    "0J;jR4Ldxm0cC6!?$jK&Z}gPmao%!;4$SX1^^{7swv@YxwPc>fdRorAn=2A!f2)w$<^?#@JQgD57p7<0`k4tlNSU0tcz+zVX"
    "ttnP8r0U)bwV*nl5_q_dg%0d2LCQ(3=DI6<gR@&bHDfM%Pt#z`VqLJy3n)&>8K?p%1<m`hb*(hW<7E-+P^A&S;>^@=C&m3O6"
    "L1=)gG_r0vMWNV|Ui!jSbW919aP()V92@C5rdMsHMryU=#A9hSH4;$n;MzS;W4CN!{ozP7AW9)*Yw%8SlS&7kQ-+q^xdE}`4"
    "<zm(Z=3ysumuxafO`xo-8t9dMqpEQStTDj)pl%Uv}R%D^ee7u%<*zP5&XbWt(}Y=g)HAb-%Xcc$z1J=KMVUL^mlRrz9=-(Q?"
    "5(B$5r-K5v1u$;3fH{GI|+j<Yyr4cYZg~yN0CCY_slTs@<BBqWB)`pGKin?sZ#po@$%w=U#95Rt~J;#g;Vxs}Zt)H4<b_62x"
    "Nog%C!_@~O)U7TDzg^rON#a#FvpqT$%`>qVTvAm%$m*o;*hvxO(`cey)!vhc=0m35e}jGi}qmb_UKK2Cybh+i65)4c`EtpBX"
    "2TzJ3MFko|Hk9`JxSI-d-oXi9A8yj%+Lq7;V(s^T7JfX>rMa7#eUKUTjLUBVh)4?}2W-5ng#YZ#v(ZT|{o2r6!Sf#Xi2vayB"
    "ghCLFfkD;sIM!$Gms-(~^9rL-qnfYm0Y`2at?(cLS_06!AoPSh9}51*nW&ZGs@RS?^|jPRifLTPOQ?ZQ?|Fjl`(p5~5>h`+W"
    "HAO<3ItP^e`pc3i(}VH<AOv&k~wv{UV{fVi8J+*&bEh-Bvk~!u@q=d1Zn(6<@@Nq>xH0r4ti<w&y3e)pkU}S))Sq<ymK_QQ&"
    "zBBzWa?eU|Qw8ip7`!yLhs4yyvK#?;y8OH5ypYsx>!}_?37b(ldOB_S4TE2K%`VRs}?Sytu{~MCXOa%A5w#6%%(hKSl7}00+"
    "1;GcBW<rg(8zayAqt@KTwaXSeT!l48scOrF$ZAV>n}VOP`&dSJ^qfutsiFMsZE0-FO!-<yP^jWUxk#{Ix|DepmdZ_rBV)!(l"
    "Ng37CA74COC_>Yg|I!AyMh`<5MA85}Tt&4#UJ06f_aF4NT12Dw_1I`QrW7cqa=DRVzzPR41lM<S!BGK8I>^R|aRx*J*`F@?F"
    "US8c<PCI!M`s^>o8Bkqa&A8|@bB<|0RV&KW1uvMSdiXAYtDP^{_{E9%c-$%tZw+^dE}}F1tV0Usfy1yU8b}asVi_X;S0!a)P"
    "7)2$w=c!iRH=UGDI!-Lw7UT$TdWT>(_tl{Fh<)hKu4_&0T#%??3FlsnXPf(nFeU`liq(D_2T&<m~2*Ge-Po-y26;$q%(FgvK"
    "eI>W$PqVZ=x)6zhu&+ZWpVfx!7NE`EF)RTeSn<NO(Z95<)f{D>eu7lq3<}_Q8JHM-i8F1(eE!scSH%QpF)7F_N6TZ?DXkl4>"
    "T|iwHemE!+a`EN!k*@<l`Q@eo3W&%e8u&{777e7n%wxEXctB-2xIOdSUO6}#A&Hv0spBs;oAoH5BYV_tM!@x&+YN=cucS_Pn"
    "t(`>`oP@1bYQ2>9x{lkYeuMKf#IZm$1cj=m;Ii~D;E<X0z1L3IN%r8OfP4fj7^=VQ9&6pTA>(9qw7f|b5K18JGj09om<rKt~"
    "@GYDi2ERPmOV?{v|JdLQC@y(b;{4J3nk36(O?x(<MJh_Jb|Hr)`g<)V4|Nf0S&=at*7#QLGtsUS46Ta{3;Llfj_iZ-{G-f3H"
    "x>*#jl7$VN--=XM~+I%R{f9n1yLq3bK6@g13n@=kVajErWuH)!~GJp4)b#}ev{S(+EAUiH$UzV`RF9nn-9<C0{0vgZ;Zr!*^"
    "mp3uCCO`FHUY2Xf{GY-%ir+tJ5A*Ai&qdyyMvVO;2`|=5%9tKpz_?6=S<fN<~F`x8olxUEFCgDH*1l7!l48{FIYg+=kXbv9E"
    "+vvM5nFfsD5wLeqABbUPAYe-R1}N|n;bA{Anc*KKv0<dqRDA4Ze+w_0!8(icYIMCfPkSLU%^drQyq=3rt*E~IVbmo*zw-Xdw"
    "G{h~n1X!{ajv+KvZb0@*;ng@YPinrgS8~^c1R@n(V;B3@#daC1msr2d>6SOMgaLWwlhy=1~L_!nEW~%e0LwV@?Vm74uc=a;r"
    "l1r|51Fp9iEJQD>(cDY~aZe8}p|wU@dl<hs9ulv33i54Ab~7M)TyY^?eCHKJOd0+(ATE~aqb;kYz3>3$K;fia0z%lv#zH;(`"
    "@68IE{LN0bbI`&4vSV{2AE?Nj=DRR4`zU0?5#~$QA1Bq&R=gOAHF|$`v~TxapOo~<kHrnfh*b1+iox82p_e6QJy@5P=;+d;r"
    "2P+iT87d<26_1gNmzVrG{=>3`eEEI*HH01{QR~3lp`O^dqQ)hs^HJUJ2UNE=b5()to<#DTS-T17=rPMqsQ<e%YCoCBZiAM+v"
    "I72venf)#xqNcu)Q1<NZMEh1Jc`2pc58^5w`2X4ghMo-<U6=cOL0!kHybp%WaZ+Na?Pm3XKOQit0SQno};9LK|oJ4E|X_aK6"
    "M;^A&b5U$hJ01Y<D&>_Ib`s$1nPiWnaK;#kqNjDcNG>Mf11XZG?(AsM-)9Z1VgC$|Q0NRogipt{fuA<~Ocd+%$%SboR8!#!}"
    "@ZUaG-_IO%T^Sb~#UB<kLWpW{PGRP(r7N;kw6^gGz+YmReF)`4j!Zi$NRqB<0M(QFz`Xv93!d|M*P+13VDrY1sJaPi1;(KkJ"
    "%5xQ07+bXK`{-|u%@lmo=3PR#4M@_c2(4FfDX4;9T9_6evl%>LtkMLy=YUri;j`Egg35^R9F?xOjsX$;bMFz;@1?=u@<R)$^"
    "UL(6Y+u|<UjHb6mxzS4L8|`6Z{Y4p#NN;=xcUwkVIimi>(tp3_S1}Kn+bTa>sQlfK5qow%CddqkZj5DHMIF{{HN6qXGOM0p1"
    "_ziml=4R5hwpuX7{OCbh^#7kONoH2b^9pFNSzYgHfHMDfQHPuQl0?hOl2zgkDg2D@~^dvAZkdj8NL0ppIV(-}}^1QS?g1;}="
    "yY(2+?G+iwG2K~-wFg8m3$a))~;aMjZe+E@$FCMd%R6K=U=&QV1GaAP9d6z50W22SdQIVtAEr1z!mMI&HbZEJ7!irI3JZ(oh"
    "KX9ja5L0JRkb_l>E&-~2Xy9E_UKKL38Ta_7k-G#9@C1?z|6%)Fi4yQ7T5TOsV<46U5o+cS?B^<TF{_z_I-y@Cd>4Hw;7u&R|"
    "63#ce(mpi&SADXRP;rar*Ec(_2$QvoU9;#rPwSqk#J#{b~ze=Ko|WHq7Z_pTAllA$Js@<Q||J+iDY(BqD@TMpCNyNq4DxLf2"
    "HoVnE~f%WQX#E0$O$3A0riC1$@`>mxel^-p55^>uSHr71~A%$~ewy{mwccz{`~GX-;(XV>0{F{rQ1)r9j#X-0C^}O~=SX-@K"
    "W%ddq(XTaH6)8R@b``(vX&f-~J-en-{t%_f?=8K8~hh~6c?VAZ^;u)dh&kOmr}<c?f88JCj#Q$C2bCxlEN&Q6vMg;V?Aj?by"
    "kuG^#(QaH#kFYeFpp#x=?oG%dM9AYH0+r$E${mS$@pfhfz4wSbyw7qtg3*dOETgm<117$VwrY6F;plk2$)Rxz;OHEG4@l2HJ"
    "E>Mbs1@wh9alfE^qMxEpmTm(dhqbF*IXfw%x7q)|)apzjB!tau>zZb?mqi~^)se_{prC7}ATc=ZoZ-iU&v9}#3@F$9>|AQ?I"
    "l;BAi-;~}8gQszuS+oj%OaA~iCU3&{y@lCo#5VvE-2M@=~Vl&k#izZ3K-@P6y5qv8)6iM&L9uY8^q@7sjeG?`wQ<hCjY^^8&"
    "%FP_BqY&trBBQR3rBrBO;CgMB{zgHkKlB)On7q31F8RsHADNctLjTsgO?poRU<Wq`Wi)kvnuAvzpQ;P_il61Egcy<<gUM4El"
    ")=`ZX&@m38B_s)hy}#ji+(diiwda)UP8I!n(qSH&V^)O(w9m1jw9aZMv75I&GOEwrJA2%IQwD{hpQcavz*3)OYs-HZ&((pVd"
    "0B1`bbof|-d-ddsz%;69g$Ug01g3cVj!auP}`YMpNabS|soF;cNmWFF*ad24D{jt=mtR-H~{(!g(1wBZ!I|UX13eUtp0T>fl"
    "#%o;oZ|(@`Yr+}(;(e3Q0j>Zs1fi_yK2E<cXs<V4tO(8b4`5<i=3>NeBln*^#A{0<7Dnr<9@$<edgYDX+r^RlYbgK38Fiw&o"
    "7}~)=H}6}?@q6;6c4DbFizR3=}u|3M?oUOA29fBM7N21#UTJE_3}~A25)z02{m?<lEQDXWx0%XNTX1OIbrc-jh|C0#st>pfq"
    "T0NUWFG%HdP7?EslDAcMp79q716|+hcXQZiW;r37(VGGTB39E3J&}V!HPOfdbeN_er*apqg*k+f4f2w~QmykpEk@zZ*ziECT"
    "9Doh6|pKb3CpUKlR2AKmY}?Xbymj{pIq*zE@Hz)GM9(lM$IRwDkz{!=X<t9}}+81yof{Thd3AaeF)zMEO*NjWHPTBm5jm8Er"
    "G)to<3*PgW{(KXEW@%8Er3Tf5pD3+Ru`o$LZt3JBivvMoFLaJ*<<og_|wXYo(Az?^DJi)bmhR0Ou=P8cR<du#sU97LA2~K{v"
    "5B*k!y07fo{5B<OM2(9h^nD^^QE$|K#Rq>ZG^A7Lpk*!LF{I(a9Ds?$Eixr(CCYG<jE)|(|IkO8jRHge7vdgZsx`89AgCm4&"
    "AXl|z(u#1{dwr2Tn%tU=j^}`;XjFV$77YAu$gmFHMwP?Gr;eyDk!VgXo$cJ_dCbF!=~t{cKTK)&{jA3_V7ARfwmdDOwTIC!u"
    "aSIHW81fO$QXp9Yr+D|DwwlJ%It`h^YMFk%K^->M%p0Y{{VTm59tKR--7K2DxP3En}=k*4}T{E^6ixe;3($V!%2pXO0&~#k3"
    "OsH-m^?IScLYtAxU9syL&jyng9Swe6t&Q1;&TkwN?)Lrb&~9sIS)lR9gTYLi|-QW34<cyf#New4m3WKY1~AL`Z1?mrNSScRZ"
    "^>j46HBw6p&jca374bX%om8s%{b^`4&=wEX95F)oU6K6-6gm=6XzC&9v;|JnUPOvZ#c25a_!<J%CQN}|v*082^uUBub%lv{d"
    "vx~pEWAa0c6MIMf{J_0=7TunqimRuaoGFW&U?cV50*w^ndg~&O4Xz|F?6p`apkCagk1fm?4RFelT|Q0N^oU^YswE_tnE1n(b"
    "SM5sahLfmlNL&~Hsuc;OJ7fgWz!>4lfsDeZzLZU<qzLM^8zVq?~3#&!n|gO2s59i<2|ky&1VjGELUuhZuu>CG>^+E)N<Y?*~"
    "VV}@l7{cV*J(-DcmjBlYMbv(9Hm1qJo10+UfYqE<(X0JvNwwzzG`^c~<NHVS(DLNJAtNz7H!JPbw~s;g>1X0srWbGFgYilYi"
    "E&4bikylx%g1K9fqL;iTQ@-2`U_512W<hM5Vc1ht;&vdA9Tou>Epw!x8sgF#Ks7sFe6K2X>YUqmi013Cs0(89jvHW5)$4IHp"
    "5e1iT&9MLubY>xG`z?%K8+s)$;)ywp!N1+?UA1a%w7}dIrh3;$NKeExmQTc8_RMNWTxZHic_pnB~X^@FgPqxD32k+=)4?~X="
    "O6M}-4gaasuQ8h#fT*3%9~O&EE^9uHxyx1V<$1$zF*fa%LVUqBX)>2Io=WkGDU$wwi-Hv@NTSqDkWym}ko<9n51X7cA%iab3"
    "<D#f&&E(qqO9BRgvs6yI&m4IT6r7krQnbDZOd5YV}B7(@&ICktk#RYPITv0==AcgP-MFNUF$HEtmITzX_(`rgi4zC`~rn}gr"
    "m;e4@^8*XWhA@h|3J4o=^m~BR??)Tg@f5qhgPF2LPdZmVMyL!r_8<)W|Kq(hMeBNHfEg^8!?Dlv<+%F*>n-fir9G)38z<+f<"
    "j#zSle0U-4_)WC_boeTdaXai-z#*|b5pC4@eGtHlVLZL3~v0%={)wfjn9qGOl(@6@r(cmW!0h;dmQ6~yZI*WPOZO{iaNW4^&"
    "8fdAIv5Z{H;T}1*MeFRqkPyI=E$EK4C?9+d(!WHti8p~yvEr75T;Lo){pOPYTfiS}7<iil$YL1tuuiyc3zuj{PEN=YGleA4g"
    "ssrid%>k&3SZDHX!5}bs<IX@G^saIi58XJOM=qZzi%`FP{vDYzBR*f|2cD);=3~z~v0COhkR^P-R(Q^5bX$nbIQ(Yirq&Ol)"
    "Id{}gMY}=9@u>_f&38K8@+RFxf(^0o4$v7EYm;@+R5*$_6@%*J`B{y-<={`s^FuD9|G*n^i#jvSb9qOib>d~@UGgRP=w{+j9"
    "e;8e}59ns=xh(fw(1Fi(McHmsngGj`630NO=#Xw_zyai%Eu0-#<{4`P`pBXB0eoF)#Kj0R~7<1o`E0+F@Iv>hJ-?@iR<NGnh"
    "&cu)y3yAhN#}O-tumBL~zH8e8qvk9$~N@DniwM{U?*rQ4;?IhoIK?ayzFM&Y>r3{%%8emS`y_l>BNDz8XW+H~oLVr6t$xOdl"
    "*NySnIA-nuGV%%vx$C!$zc7|h`x8Zis1oQvwY>u)xY&lVPzNj1f0iOLSywm%Ob#?A;m593Ye)t9=e1#6*c`^CX;>C0l<F12$"
    "ml1D9^NX#p<Om)gcKgHXg)h0LL9~(8e$)*|gWIC9UWO{Qlg=l~it(gZa~5#r^<pXTlB*LQX4=gYM<jkma2_so{{3%<7yZ}a^"
    "Y|({2AvT+=EH~FVWyx7i}jhZ2FA;n$mwxp-KN9_=eP~?Cknq=!5gF2(NrhuaL`DWUJ?HcuZlKQeSJtKkd!RO3;I7ynge^C{S"
    "&SCj&0kvZQHhOCrx&2HMY%0josL6lE!9ZH8_3yzs_~eN0@omv*unizqZ0lf#PYmwg%>9TfSzwyoE)TK5WV990Eu%NK?{UpuQ"
    "zkpE_^cuOoau_xESXH&Y+<{KuMVa*(o7-|z${C6DyzaH%kJ$94rLe5v>xtx85GhMmUqvsP=^URs6b_pr7*<`JDq$K)|1YIbq"
    "&z1A;SAI00F$%vkBW_~dEv9u1ArH%AsW;_bC%HX^d3B?KC$4-(xewB_=V9ireMz9#ye+)-cUxlMTEg2oh^c`C$;%^G<S^ylg"
    "s_(0ba?q6z+eLHW{qsQ)rda>ub?Ou{gxP)EcDb8usJ=k5;(5Lgu40hue#uWI@*Gk``3H$BM2GH?AP5v(A+qzd>(pm8S8}9C&"
    "p3GFJbrD;c!c2gnZ7ii*-RZ1Hh7X(F`DFNwVxo2m@)wK@86QW8N<hXA}9Sd1Vh4|mS?B1RT83}HDVhv5m<}axsw)UlS+&t&Y"
    "AOc1ZhG{VMIbGTM*CkIBANAGC%bxI-Sx5@vjD;;V=U@-JyilPe$LXz-nPl+VcmUEWRmPBxP{HHO}WXnUn?p?$E?w7J_ZZUVA"
    "o%rAV4^7#7qLUH+^Po2T)gtn#Y-w$SIApR!vJoW-2)BzNLb9v#cvwHo|O0AYv)KKMWDU;y3i$sc~9A+xz>;5v%KVqKv7bcGN"
    "%-x>|YuWXSiiz5K@U(mJagno{ywSI&5!Qjk=-;^S}`1)<V8g4y#iXfAUVCw=)R_a4P7obWD@PvRlL)*ASFwztNdHk-Qxq$qg"
    "`Rw4!uJnpD(d1iq84(lIeFdx7Z-x1;NeRQN7$I{`C$%AMh*vK|Jp0VKM5V-(bsJRfQaAN<Icon(A+)MK5`>&T)HiXzUr&-~f"
    "6j}rtoD<Mjjqh#bfRVkUd)r6WRzhuM_9EBD#?{ABwR?A5s+c_p4nky>S998HQ6%b0S{ppeIjhic6|S9{hFIu{mEJK&Nmr+2Z"
    "8|N3RmgV8pmqjU$BQH-Herk1}#O=a?Y1N*)IxZS0wjVR@hnxbGg)>xZ|D7?L_$v8Jk-sGhYBDh>_J+8Oir%N4WNNmsn}P)|Y"
    "hPn7MOcVf#O3&RrF!vn%Qk=vs-AnOjXDTrSv$py<-hNjn1R(LTLw0BeI%4Ae_uC^S;o55CKf2}{4LIt&bmw>w?G6)hUQI3Pk"
    ")#dC=tj2DunyPld$Jo_}XBa7IgPF`i8452+bt#Ll1y-a4YeKeh;1=iOPGq>FSyeMbgDP_5+Xw)ocRfygrO;XeyTTh>WD&n_K"
    "0-KS+Hol7yxnv+I*)L7VX>DhNurexj&$+hxO^Psq;a3*#kp0-FK?YK1wsgGDIWDF}FT_@)mhs5YyAGV`B)%Sfv0*`IHu=ZXU"
    "{!m&dYZ6kwm=cW2Ws(r4&Vu8F^ur0%@_yCyhx1693Zk7zuX^y7}#lIYMnG-95vMFmh)U$Yp(Xl+x=rBaerX|BA~2rOK;3^-G"
    "sAZaI|2S;K~{GKBss`7=HZsRPhtHr{>q>-z%On2ZJq-9ommMSsA&=u=E|8aZ0?@#jwdG#n4>03E_@xq26W8CcLmIQWieC0j1"
    "rD%21ebdO~9KdfOw93w&oMmL^(Vwn5V#49EOm&J5VU9Kq^UNXUh(RWQmYsgc37juo-a5RkHpA*s;!iwD9k-|mL<1DgCxPkL}"
    "02xWHZb09uCp5V6TyHLNkZ~io#HOt8vNN0%`GOgLJI1gXRSrO%(JLyIR%V%^oYJWD;8IZQu7h%Lt5#Be?jsHwwr4bB5f85|r"
    "OEwL^XTXS$>Pw>uU3~a(EkY(VrglqLuLAU(_}Yb0ZNf=@Qa|gk{l6aX#|~WbAZjCC#b+iD#3_AU)N`cEj)da7&u9X4e!>4<+"
    "L?5|J|S&MxDQP}c&D@rtHElUk`SgEzuI{=k*Rtt+2lj<;$2Un|6qzam;JHrl<u|h(~Lqo2uyem35rw%_c?q{D+JWnX^9iM`f"
    "K$YBbFHivOIJJr6mx;6)OByB?BgT0FORLdG*a9deuH1S@Y}-A!(X8FIn!ipl#d%%Mra*Bw(;^r{vbFpO^bM^`b?PMEz8eZM9"
    "F?spn(#5Zcf1ZS)G>NAd}9)pq;yq%^r6<|0}5LPE+`0D+_|x3s)vf@f@MBq_xVL5NA0XlwBujHK|vR4dLycx%aDr?tIoUy72"
    "|g9<mfuau>}gUN;u)&A_nK7zy=zzdiel-zN<FEGvg@h=ErMM1CjRYFlv`H6;N5l+Wr_N9Pps&7QuWaENz)PNIMC&^q!;m65W"
    ">y2~@Tvoo7%hK0IpGpFl8u)8uf15T&1vNGewI84qdwP_|h;G7a1{TZfsK5R`eap^O7MLO_7j&WrPaz;prv3fe)E8K_RY%wnQ"
    "EEJ#alYX?S7SO=96}N!cdpXs<XfIt)A=|)Fu!o*LdhbfeF2e~-C+{<rHbtGn?)DlnO3Cv;HY}#KwX|z8DsN@%_^2H@-K!i?m"
    "j@@FY;?^UF6T+00Q9*!r}K~(54ZTxD(u$-uSIKt%vvVI}J+>*<g<7@p)s~9q899U0Ctd1t5_tU1obgnC7Q;E`yUK_N{2@mGk"
    "LhWL&@(@A>1tl_^#+kn3n}X^M!on5;o?<f3R4NoB+R2rEMK$iHm|d?}5E4=OcE<%$GGQDLQ{`>-$;OlgiHRg4KK>rT<Vlp8^"
    "m3__y;><xH0(Ltxzb+YbiT$I@ZNpCnC6|HBtY1q6>)<Rv1VdM0+R*CAA@R^YQgNSsd{FecSO2rHqT5uAGh4gSIQ*vTG9^W4W"
    "^byeC9G?_VU<TSr9{xy|hO!sc5b#-1FSaT|wHR%V-LS<!n@Y2mVO2{MC0`KdS$&)63q}Z(Yt=?lBvnNt&3~|a4hsUu-B|ogS"
    "f)?LOCK|&zr+9iL%KQTIcTxsCSuF<S1eflll#wu()s<LIM-@8aOyZ{wD)UO<?hBWip8m}hZOMPYH7$CYcf$JjIJCm*Id7;`n"
    "#HHyArbUuHLXNTHVilrK>-@#Hb_VeEp2@;?O~JhptDyRf)o|&<o8EGz0;yUOf}N<~R|$2>&<>)c_;t+#nYIS|uieqi(!M_AV"
    "ZZBP(o9^_EIv(Y<k5<k*itvS7eh=jWI%;2h_a7`4Fjaqp!uA%^fUS_a(_abv}NmN8_zKD{gc(An-X$L?yQ&L(H+4Of0K<D@0"
    ";hi*}vT5FZ+N?2nOB19V$ZW;9T%o*yvLsuL7YLdTRz}j}$Z(dBwD;YS?BbcuPa#D)m^A|J*s$^La5hA-wiKg;|$z@LoFs_o%"
    "JWS`$$Bhw<J`gb0Q6JV&ji;T&!$F&11ZR8+1+$2z+MJ;Vs)e)7^M|@8NDTKA7@e0G4)kTSoS18?qZtG=BQhEzeJ?b6hhGs?T"
    "EO3W^d(fv9y<CTcIl&gBzvd%!lq62S}iHQAh|&#$wx+6x^k8ynl$16b-FB>MH&7`BV~E$e1EOOb=JT90rg*mYo-x+B10-kfG"
    "vww+>`QiG1u!p#kk^u)T!Va;U-~wzC2-n?X}C$K=&ycBis0420AAk<&AeP3fp%{b(I`4F||bmJtp6lH9BHt!Ld{{v~>1kH6^"
    "8Yex^6*h)J}bCS!`4fd-{W8(mxnhvaV|9oAjp`J^5gwlaKy2@#$OdZPR5T2+s-hM?h<ItD6yS$GUPv$P;ggG4#779-ip^>ac"
    "5yXQ9J5$zGEb(l{~i>IBywXT=Im&a-SgP`@VgR3FOF8rOl$^b3g3DIVFT?a9|FO8<$c06ReK*v+=mGEJ>FY1ExI?nH8LoN)M"
    "I|F*K1$flE!u80;wr(AUKB7#C-7QOZwIX-`x-{d}TYS`hual-!otFY7NWKvbyC-bSm=9&pRl;9zi~S$C!ENIYMTTVT2t=bxC"
    "I`GS*IO@T!bmSLuyMtsLX{A$Xh4w|>~MAA3%>h<G(IObV5gc;UnK(q+^~t@CU8>LZAw$fGv}X`?W|^p2{b?Pr5+Ws0B(;8!3"
    "TTgxvkS+f$oN7ZFPW>S&eZ;oSOb~m)3X<lDSJ=oLe=Y$sg47t+w9Q^`t=>7}ChQ1)F3_gR1A&>p7fJOaYYOptO-C)6r=>jQN"
    "S=T|z~b(amHvOMXG78XxXQ$q}z5E9Lu%{CMy2fxJ&J;wJj%-;bDYYIZPB{(?U>6v&O+RIbNxT9ySDV(-=H$il3{tNq1n!s*t"
    "L&q_^B<G?8!<yOU8nBtF6@2e<PzljMDYTd|va)~4W27XTbUa848dRf1aU2YA&GUa<0CbG+6>nJ>Yu_idS@oSg`y738y;=Q>*"
    "^jGd^{cR@$);|Htj7Uri2H#z4bdfW9V64_qIkQn+t|B-q^psS6a#amtaITTEKT{t2qi{*CWj;)n!i1>%1RVt~@5RK`+nLZ=q"
    "<EdjU|&(Mm}h00bxt#AWU^M@C!-V&X2@8p$)r5%VEX75LGwTUic8o{*a6=P%uPa~(yVTRwU*usn*Y#`*Rs1sV2AqdrYl99M0"
    "y3sIC9jLVRGmO>QN{24E@#q9(i+m&(nJ*7)z}5U=}nNZWxF)qy#4(2!}5TCGLf{DRy3X;0SN4Pg4c|%2<{r(z>NK2v3nK@?A"
    "^OO8&=_+NA<x4B*fsssWnP=SPKUG-Mm8MS8*%iP6_9(L{SmN|x7O%9Il(dW-M+@?d5y;5%>u0yV`S0RgxXx_JMPq_}D|Vb64"
    "F*(5v{V9`4dqE0X$E)LSeVBsqEC<hUlt4qX@QQ#*_@uB$Wc0!}zKf~1dGsQ%Yhx!m;8ng&dl4Ush3e5W!^D9h^(k4xD+Y*|6"
    "|LBs$FTC{D3$$kvZV;P{&dSDGqw3tgU#u&GQx9rP)>PI7#Jd5aLmWvpvE_8Gz*A<6+~cDB4rzLK(^X}|X(q<9(CfSk{m<(v;"
    "R`j(2M)eU<b7b!RSn{}*cFE{f~tx4&^w63#vc1;E=4{g{BNjxG~cwJbl*(oLc6-1mPZ;!zbBIx3CUL;as}#0J^er#la+6cB6"
    "rpB?2BuGQWK*&PGCbSTk#qT!&+z|T6zgS8>~aw_X0WdQwGSXaSgJfPK+;~Xm?cO;PoPTTXZe6QU>eCV-1wjld9G&mL`@ELh!"
    "jWRY|iV5zm%H^wnR0zl~$AQAL=p5dRw-usEp3b%v4Tl_eo6xONzaWait-2tFPM;>ckz<S`O=$@9_$izHDWCBZi?nS;MQ)nn_"
    "5mQh|U({b<x<M+?nk8cA11Pb6Uk<dcwq3RDw$&;->W!8-Zw#^>th4x8IQ9lIDj3a%EdB=zh#;7J2Sx0Se=mH6PzomxZTupgm"
    "DDAlK1`233m<%GRkW+)`RFkSbO&5rp&|2~_M<|O{=>4*qAdO)e&(PpUGb+bX8mfW_os%lA!|R)$)vh6~Fnuqs*>POdabVPOq"
    "~Lt%!&_Q3xIR<ExmU#SpVR$Lr-C>+vnBZ{J!~UiYxpcqX6QWmHFU8Oi;#kDWvsmj*x9ofZyC3mujvo^mr#QYAFYbtZwfbHEE"
    "d@3oOtQuO1hzp1(lUmtTbF$nYc~=4qS?VeUo*ux4y=q!wGJP^X=@gf$m>g0hM1RBYer0Uha?@5tbBF;O!q_i6=figRBh{k~>"
    "cVl#PJ65Tu4rewsfM(b4FeQjo0?L?<=_^w@z%69$~XuM?kUkH5KEfJcAyAkMf`b{(3P_ujvvV~I%@uYSAv{&6>k<RERGiSiI"
    "_{#;&5=PF(8zN!S9*Hl<?QPU5fH0LfOWua&+QoX%$`B}+G$&%Fc&G_J&{Nx9HQ)oNq$w=T@xZ@bjC0fj{nm^c%g=+qbm#-&t"
    "b3`s<^HsU9QpkfbMmH}dE2Oul95IwOxYfzsM(NJtRUg88X*VzHS|r_L5xa6Jxasfj-*<i(3QovcM3(L~Oae}PPo!qK{UoJZZ"
    "=5ghm3WGaSAt5eU15oONq&dkOKW@F{cW4^zl=*+93@=46}nh@l%Rt9IQ}Sg1JWwNOl~c5p28*%v^Y9X$9i1jebWnqY=kaFaU"
    "IUo4T2azz2W`CMR0qb8F$~LAFt<Ekw(Q=3d?dxy}qXBZjiXLmR&pu?_m>VyM9I+yCTMi(JpYbdsPp%mDCGS%I$H2SG@y2pd_"
    "%Ds;V4b8I}rJXa^|w0M}t96aVEwXLCF?E@2kngj4;}R?gNwem3|>5_)M0rJp<kl`NL8$MV%Zbg)AfTKb?ed1=c{j#lQ6dBe<"
    "2<%4mGJsE;3Hn7?YL>@@^8`c?&zz%-2mV?$G#rdw_2gsV9S|vkr;uFu!<$Q`V@2nt|h4a{m?XqAi4VC6b_^eUAE>B&LpT5Nw"
    "VW?L8pT(iE(*1h9^Fi_~gHjRu$#SN+6go!;cE6*Q<L&BaK{t=r$QnfW{OwABgiCyagSgIfW_b9{2gkCE%-GJxvV_%VhGGK9!"
    "Hzq-s93;6CcOC8jJo{FEsN2jYg9A6$}tJ%;7)56%BpKm^e!Yx3LhL#Z%!0w)=vB-=LzU#44n%o5#zJI{;217MIxHe(s&l9r`"
    "_OT&_XefYMqdW5Urf$jMdVQy;}paV3g18>z}kb95BN3PD*7j+>r~YJytL}L=m0&lcZsm<}}H9aDmi55<eEMZsNtI^S+jsiWf"
    "71Yh0j=?(7u2k>y5*iuhz94yBD;rED5*xHz|g`h(BzMMkq{2>JXDP`GC~+~6`5xbt2c^1!Jsx4WxhG`TjPLiqv`KG+eOhySN"
    "03yCVs6gyT)78?sW@S>H{W1nYydeWQ>SCqNw=rfx0-r)}qY%U~K<O77i-AXu)-$}IR-UZm<*t-IfZj=Z0E*bMrhj01vILruu"
    "RA2%_ziT?LxV8)Ir9dyyUhdKnR#I>dEekx{r+e!jNDVhi{c@OdsAt#`mU}e$Uez?Z6iC(KaIz-K89ucv$-8xE7t3cYekv_cA"
    "~FdWlVa;=jo~8S9ZRUwLVn9XkK1A76>a-)`VoG0-QF``=~I5<+XRZ37Y|hvcaNt=O$eN|X-MsgE8!C3Z&WtbXKIRM4lwWXI>"
    "31X@jbtZ4wd2HKdoa@WD{h46H<E9hKG{N4UV1Fej>kq;rZK>mjBz6w?D6e1k#4fU1V;6lLWvGXe>#=Me}U+3==tw#;=N_;k="
    "(XOu4Wj1FC20wVXk&_4pdajt3e0FoG9zS@b)H#5qIVUYPs)y28lS-UC2^&-IRN-`nEX*Gj7@w4IN9FsR73LUSJUXC<A{wYkM"
    "7h?rV$8Az9MV^%5L*3Cs6bA5j2R4Q0cH5ER<dV0n0O0F+3yJ4iaw0V!tPCBBMebNb&wQA?zm(0=%b6_+Lzppe#u_2s1m9T|H"
    "fPv!92UExr?{f|$cu!WZXD+5eB(54*;rfUee&2Vf_~Cb9?+2uq{L-@+xKp;AA%O9FedD|fxPaHP$-Nf!H(g3_AKgO~mcM94`"
    "9G(2{T1s&<e3J!L*~GCrFfyW>N=Xt_WC^<CVM4ViXjOhBO86s^2O*L`6}#0=9R6vDHk<JbG=wCkGbE`_A`US^O(Mk`dFK5Zi"
    "UNuaM2mh@;RIj5-;XXadMT+4L?b&4r4D}fje+r5We)4-<|N~_=h%C#7(WXI^*;&7L{bjlBVqhDTpum1>ZLcv$z(V8T+DgfoB"
    "fnp~6XYvY~pnxW|-~T9sY_a@ZntUqm>Y&*r2(w_&Bl4z4p5o7k9=*%+ZqGVCrZksVYa<WR1%8e=BPDge9#Ri8B>A#b*S*qoH"
    "SX^%aHFCtu#Q^u279zB&(gz#IoWw<Q+=iOB@<{+Qj-Jvh;dHDVQ`mozSr&-uD?g!thlS6PJvwN<9=H?6EK=2sjH5pFsmcpz3"
    "m_32gQRO>CQKM<c3Y_)DBikI6zM$)WP}+|l*p!pZzo#(M3!Bf*oTiF#SJ@-=IX^aws17OB>KC{?rVR;VeEFlA{q#!?fL1{3+"
    "M%_--BQoqtcR0?>u|rAgt?>5g$y_))j7FLV!ssFqI3R{+%Gzgq=G!ont5S1_Y)(HuyC;~g%3C%m<aJ;L!{1~SDM^UymnixC>"
    "imRTdwXaG2x*u^A?AxX*IWfu&d(vrbbgDOnHil>ot#TThurFTT)nJyQI<u+Y;&|m+C?7bSM5HCXm55U$p~*f&kTQ>GsA!XXu"
    "Z;KVY18w<f}X*eL&OB%h_`!<InbBe1+=-!b2RWL}XFSlL6|;}Jn{3Z-+_gI)Eh&W$n3i_qtnPbm0TUcCS06`h5W;ICK4ydbg"
    "#(=iViTM}I$k<tFceGb+l^>`w<9PpQz8j&vK59b#B5ls+Xu=+c#H8k?}eV{novC5RC$=uji9+{VIzX8De_Bk2~X6kLdRBV=g"
    ")9mZxCi3UR)=^Io9lLuHEk^h#s&Nyd<xX*W=_hf%1yH(_Yxk|~iVZkVAj!l;v>E;aQ!Lh!?oSnn^%A3G9QNn6v(98#bbjv%t"
    "D#%Fs++eV$*xMqPP-sNd9Ry5(cURag}dfE7y6r9*qjQ+YZ<cg1>5;Eq?Zv{qf*(P?NyI*NUQFZXE`?UwD~*6c2<>0-vdfdK5"
    "2QLg_e6v%^<(WnPxs9{CCdKbqlaYBfc}Pwlkvj(~pOekb=$HvPL(PDK}KJZ~guvf2Z1FQKPUw{eenyaa7`ksZy1=gCby%nr|"
    "1Kc9AN`86xa`)BV#)A4F(L*5VetZ3v~%D9kGPX|ON0P<6mN8FEkAX$b%6w2#6TPU?XW1o1oBd#AB>NH$zfhq*&IRiseQ(UGC"
    "m6HJ2cCH2z8$h~M&_nQg4U$mk#sfR_o>03=GZkK2kxd<=eo@zzNUfK}MSt{C0E!>6UZDQ?WJlYrZ!wQ++f-#4Z3@5{CR!Uco"
    "ghj(?44BN9#KMGGB_r_Xk<)RO|Ld`qg%NV6xp-q5D3y3uKLr-aq(`2W;mEQoqk4I5#Yv((05suT`k2qbS40+fU7&<AW_Eh%|"
    "2RAG_jt?%#rzsYUAaI1ofDO{2-`6Ks=5vB`A5dJb@uK0bPf-NVFsx|3M2~d>RLZobw5|~i1RUjmYfh-_p7SFL56AzSgNGMFP"
    "c%~mcV$&sEO@X+S=~}nLn!Yj3^SgiLErhWSZ|qx{)yMd_Uv>Z<JsY`6UTjN18y%XLRMM-EaMf2h>;k(>KF4`dNOKWAA*_gHZ"
    "_(gVQA&e}5}E&Z1Ri_52vW;MxbpLGP$pA|~Ak1Bs!>OHlIT^8^2;e|hA89~{a+#upM<b%Hqnvxi#=fCs_pXC}?ODKJjsPVKC"
    "Mp*lZw6j-{{%^%9Jl_m&DGAr%0$xd}PW7|F50eu{{I!3|@etx?5xm!B}>ac;F8W?2H0^Ci*WGaTb3}C`cJE4}bHH4kVk>vF^"
    "rismbQ(=mDUPFBU8E_fPcPvvQNG(M7wAWFXphp*`LHed8zI8F_Q_Px=r@91bLviL7#kF|c39^*y#Ew>6dDwluD0@1f;DyHiE"
    "KnCy3CNbC)yRlD)J3-v(m7Rp4*TR#2~qo~I8Lql<euf@GxqEZx}#K_<z#Qb4O5Rqm~i6*LKi$WK)UeR(fy}^`~PVG1XV>Tz|"
    "xB>t%(Kl0%W@KOMax3_>>@;tW%<DV40`|+oDM70(urAe#^Xx6hU|N+CPsOLXNpWl&zBrkkVIE7RH+Bz4VnD{tP_nPLjAj<$z"
    "A_cQRTc8;+X+XEdWW^Iym5PmdR}9jXdzpPAWRt)>PIt|agR2VZ#wuryebkyOewyy<&q@N<@%Y)6vkdCK8w1`0L)P~`pG$?7D"
    "`o}D_Xrg3eF>BJHkZYSL7Qo=2uM*`mFf)3h(YJjH56TSKNuIknDt>IHcTApv^sqy*Rb)oj|ajisQUSM-U_Y4RnQ^D{{hd@rA"
    "vXc4lKi7s>rf&QHTX(0!%4rG){}%oJ$u_Ug=o3bZ1oDE?Z`$Wa%zh15Y9_c<e-`}1Be5#Q1g`Ux3VGn$J=&+vn?fU3UcAnp`"
    "TM9_SA(TTw97clDjI$sN@ogAX<S^Hfq{;iT3j7>HoDE@Kw%P^%Z@TS1Jm!Dr8RV(Z6Ib)%=t~F_CWh3xK?G`Pz#J>(i}KT&l"
    "3JqXa|)|%f+fi^?Tg5{rezWVH>$?edbr{W?~x3x2(bl?tP^GzV-n6!Ks}3tGwsUYueItFnmimTx}Z6pp*frnc9Q9+KyrJm4P"
    "A#06B_G9x!2WVAPeGWHLbGuhg~v4a_DHSN|y4fTB))NiHh#A;$?3VLY7E%4i~lAKaBX8nV_%I&_;&TF5tM3t(do2PNK|B+?R"
    "9&j|TqX>{YQF##JtgWQQkZWUtVdnxa66+aj6tOshA1L<Mu>c-*Tn<^^^do+Rs;PusQc@9y$t-5X|Q%2`lyYcAEp>JlLFtr_s"
    "4<mL6E$QdzZw(YSb9KAGTZS0SVroi%@He{U4?i1}wS~0kS-d5}5+}Z5F40A5NXKF73zp-46FqYGcd1Cz9tk8?!<i~wYG(8eo"
    "H%)rTrEs^R2GDehlBm{Jq|Fc8hNhji!c3w8=-6Tzlup%X)6uW^o3)ORfZr!DkE0Mh);c@s#2D~%a1UevXvYGw1NvZ;B&{2KY"
    "w0S+;pANk3C);F@S1-tkJ@i+u`6%<q!)rlAV?j>7<V#o*x_UKI;BGP;Q;8U~Is0d5+AgTM<lb<;zHul?(!_rSHAta4Rp5XT&"
    "*@cv_gx;{$;XJy+p`?Fn%%$5GFdX28T1dYXz58ag~)>QV_3TKYm?PqX8ld)K!Wt{|%`uZRq~M4Oupg|*E^U*zFmZ-RBOc#7M"
    "$Dcz!0WO*B<Ik&aOqr|?eB4On0Z(xhI5>`0GFa^WuEb#)-i&RK#xVPix4s2R+=%B*mOyWGfGoQs2wBWPMyKmP_Jep{q|LxlU"
    "*BCbSAJRR4T(Ro$4qD{ePl2k<uR#pyOSz;X<zSZJ_d`-!t=Gj4z>X`y0Eh;t158!-#3}~R{(>rP^Cja-7CSKAr)&=Qs2LKr#"
    "xsV!xPzuRLjdS$BA+>s(+#f^Xl58>f`A<9DR8`^Qo#UXv8ioxKA26_bW+=&Zln0l`fb_1ACacwbQ@=3L=S6Fg{~*njj!L^5;"
    "xx;SmYgE@>v7frR=okNAEQ2QM3L<?hiK}r^OQbxV82Is>#{M{D~KO>}T@rCwgW70~6Q)53%##|C#XL7IMmmMmt}7Pb&3DM$E"
    "|w<HcF+(P@!L);n;u40xZR)^{q1%cL<HK;C)%=R=j`yDuWbXVwq2*W>H)SH{1H?a4Iv!m*6lm?`kKW|MI)EROmazy@5mL{oU"
    "VT%m|O4fKw{0*}Y=H-r;$1a{eh^$7^Xy``V0zwl+F#NS&5DFjrtAwqX&+ri63Ft_%Qk1CPGi>oxy<LbKlwXzl;HFn%t%vjHm"
    "1v2~EC|*U-NhdWWzka3~{{TNE1hMyC6Pu+I`Qr<n3B-sR3kT8gPg_*avrqquz4xV9x{EE(ywkSMI_c;>;a^(6XAls$SlwNzo"
    "F@Oz)c(EONzeKUGbsO@`6Ol#Q2_xQ_o<Pt`h>zGqJ)-*c;9fOp*{y<ZnmUG;WCukfia(74fKz^2VgY7jYzb5iSee)z+vyxdA"
    "7BVuLRUKm$i6fGjq3R7I1NW>Beu_F<v~I=fsKz!;}Ax&sE#m?~*h^jGa4E?|q4u9}=rx6l+H(p&4;q*1MIW@?B(^mE}g(gaC"
    "4~ak7F3%*tbmA?~1944ww6*DhY>&z|QVQomr`%v0G5r`3EE;jL#l>#yX~2z(g?GECa%QA!8BRb%wymLG;paps^a9i!COAjsY"
    "cyVuwSFA|Fz;RsVc@c)MRDIi0lH4trES`*PnX56r~CniEh3U*CG2H}1S=e>OTD=tq8I;i*in*4s^8#<s(mY#hq3vf<A%e*^#"
    "&b{lZt2!clDz2g>OKw(s9P=?#h9JVEE(OZvL^ql7Dx-CBeiggLU#vuFTeG3l)k10;u0KO`j7#)?j*rK0d`~A%rn&b#;iKD^|"
    "H0@p%xJ!Jn^q6LEWbFJP+a3$D!kP<a>$M^r|uH5dI7I<9WmWLHX?5$4OJGLafxCb7Arl-7L(E2aFr$hc|J9W^L6vfpX<e!K+"
    "3soaY~!{yHSILx;1-_X^W05G%Ru`8I}720)PhIlhF;CNIp;^4;f{Mh49}c!y|02GsGL>X^+4lt<#b0gM&s+>OB;TR0L0gmh*"
    "0mWe)s^1r5AqhZpV168>lVdtjJTMB-6r1r1fr>@IS*zbZy&GXyW#Nv>T(=4!n};lsPzMptuW!Vj~Ijrx`CmJj<EIr3~JGk;Z"
    "Y#0IM5D)@lfK#a9FDvt<QQO2vS0)JGca3leFGV-v67aNI}oT(Zb+rSRE59^a77W?oK0xWJ#c@>f*iXoIi#c-dAy1g%+6IR&<"
    "6Ln@-ipX20go9pLqMQh<rTG%sJQK>ZjW~6>=0<oa<5tpHjvljo;MnLXOQ*YE(WVbWf3PS}|9j9$NP17D$|M*{t)dx99J7`!>"
    "RMg4{XM#LZf6`JyQR9r3uEqS{F;0yyf>vm=UMEU0`8sv*~SPn7rmq`l!xLxxg5e1a&EpYYr6R*p&{evT&`4+(bVxV`r=>&=2"
    "soDmKQm~qWFb?eeC$4{skz{?~Sf@!#|LZ{2Se^spakHG6{l^lsh#oIjV4~O4Al{(iqSea!@|IT9Jo~Pr^=@@jke1VYpm`?ym"
    "`#b~KTP<QPxWSz|3se6XFSJxjC@=a1K`ABERuxDr0>TZ7E6@q;%k(sRZk3jJ3spM4TEc)qOonc$Q+|0A^-6fDR=)qqAXY^hy"
    "(K>*u&3%CeBP$9nb6cdFi7hL9TqeYX<93%%cFy7m8AnJ2e#j`}t02*M%?VSIhLsI>HQ3(P1Q1S$D#Ex>Zm&pXC`(laZ{N`r3"
    "t1S3sP&b<n2TeF$5V+-2HSQMn{G<V^R7#u#2hh#HL0WvyOQxRhvDJ>OFDbsZv%UtNBN-$SQCa??P^_!!q#bsBl3Ghzl1eiW-"
    "S0D$0<Gv^_@!0Af9C8n2WP{m%0}{>EMI3lT!LuG?sZ`Umra~g8#1IDWy>`W0^O<VuGo)!(=?vA866SJS;ljl%OOB<L1>@+VR"
    "%BC>&Q`OF^)t-EZWrn<<#;}pQIVe0C>vW$O=0W#n(PU$!B%MaEq#ikNuofrH6XS(1t6Sa9<RzSCbO0ukC#`AVz;9gu;S6z<I"
    "v>p1df~SX`Ai^?pYW-r-bQpPw3J+D37;GO^XMFtcZ$wZigYM(!e2KFRBxov-qg7&vm@;oPTy{!u{($b(8s;fk<;JEk&tlQAa"
    "dx@?EfGgr`{Lf-lPE}Q$!fJdux0-bFMOhsxm^(z>}jx4O6rM?PAn=i^DQ@arPC6cpQAC)DxUXiWEMO8iIynM@WD6QcyM-RIw"
    "4{RHAn?o@-tFX*QFo8roqr`I*jYROTe3UFT;e$Kz&qY^8_dHmBVEBSEoMeAGIi}Sp={;=XsbF~_Pkf~cxSRCIPP)=6@n`%8|"
    "Bw!|iWnW4&#)*+|9hA~I4p^hu<QQu&I2cnm`;Nx7HSg$C1){~MFZEv9ZFwjK(yJSHgEhIH?l}Ep^-xB70a-t69`r84^O;Y1N"
    "7B+E9-`hRMif3=9Aw0K!wLupZ&qwxHOeo#G+kZpV7vTZWiRIvWkaUB#q@|w2s1*<O(4q@Pd)FzRoMH#}f?gf}ej|UCn4>c-B"
    "sft8Q`MRdj`tgo(9aAwul|I65!az18G)&VEb}V{DP@?)A1kj(hxba*Kc_?zu?%QKTo)6Zlp0Q=3r#09t*N6{A$6Tz8;NQ=tI"
    "CzjHe?pu}oA+XqjuWUNYYd%g~=N<%jGQ<XYJ?;XbAi39)huPqY%hXjkF6CnrdF=>lDkkSty<)SQz<sS5uj{TI-T7QRxH^+4`"
    "5EGT63BtxGdrPzVy0{*!&8a6n@l112;^ylalc?Q#YBoMUU@qHxGrLxBHuq2Z+aF8QDuuPR3BtXOS_@fV$BsaMolG~4alfZ`F"
    "9snwjB1WR$f(Nlp=i3&Q-u>i7qv`Z-R?_^?GjicBOzNw99Q(XSfQtUjGP>4S_zpVE<$o*S&=QunM1j3%tx1JfSVb$g<}gl{m"
    "fKWo&WDa!Ei7OiW%iuVmCc}=$3Jf*z-5@3Jy^`&KDWHxm2*E>up&cABnHvJ7~m+5vE!Y|Ee~ntAskfhCMba0~y3Gytb}?C(^"
    "JT60Rz)wWl5bSs{ukse3Pv4|8uT+>_FuP7?oJgVwJjd=gL(X2BAyyz2ZzbZMzW0@~0zRYCBL3f$ke_)5OtZ22O^_X=J|3kR&"
    "tQWEUX`r!(><4;e+^tTMpJjkRbzIiMbh!FbcxNan6KTU;lur#p-5^+6=LlKUgrHM27UbQ=eLR1#bgy>-pJ2yF9c$*Up83-}y"
    "_tOulV{6H<3E0=ZH#8Z1$Xy!g5N-6e%iCrih_3R)ET=yeMf=jDoN;kMi)YH;8{)$0Bo9yuKjWHB2!hcD-^Icq?B(e@qY;J-d"
    "j2^kk~&7eu4*lzTJi?#$;UQFVMQ>;!!Q?OpG`jog&spz6h312i6kC?ZkemP=~oCxZFPTaGvu2d^Tww(wC2*Lxetz~0jNSwF7"
    "8Atj;QoI-NdYFY>;ot6#B#S-RBiSy5o^Od&4@}Wa*;1A>SOm!#y;uMl9*o#Nkb6FbYbZO@l7h64o3e@elmY-#=h^<VX^W4@C"
    "!20VPdBtrbS2@4QkM4G-2;{GoC%EM1xsV6H`6i058W^y!h(-Ecy}TnMGHd4{f5T7k_w`@IT4QB1n`f_zRY^6ARAoO;fYoz+="
    "t^2Vwne<Z=OUt{x%O240=xykO4&$%)YhFItU|5hBhgYeHL?_6b&Do&{Yo3G%Ecs%ENay7OlmJ<+P^ME!)uTIXJBMk_T<lF)5"
    "{=gMMb21pF{Ra9C4MRp=AjkN(Rxbiv=!FISSa-Fv97|Mrmujkvc`Zn0)e#efRoWVcMj)++KURI5|MLT*_zB^9Ou}v+b_sdnK"
    "5IjWo}Bbdni8q*QgWv;xv42-$!GkF{$umpQ;mjLR8jy#3u4Pms*5Ndv@{rW5Xu%@6ly=dskjT~H_zXb2lP;XSh$XArr6N39I"
    "q72<wO)>^#prVk-lb@>u=dvKT`VmB(SAX6+jNk3LPN~)#ChHWQOCQJH3+-NoZEJ=U~XH?>kQbVAS-uxarZISqt!cykq9(p5Q"
    "qe$X&#LhOe4qbnM#ygl*hPrrhPTzQOucA_t5!v7n!Jys?^q%1lJ<3#-uHuRz-bvyz-@<YU|@Nhg%u;4YW^l&M}G8iXoU&4zI"
    "muZI6r@@UuU2$bn&ZYHkSt>p8ie6@x^440^0?)ZkMK<hbHEYmn=sQ48xP7jj^2Es+I^Vv%$L_L5gDMM>$ogH=U!|?Xuu;k~d"
    "waSf{gM^%*zCx^U$-4=`%zgL5=MS<rDtJ)w$Nj=ykXm$FAdL^HW!LqG6^@nUKZmE6_K^z+bcmIUC5UXWYiEyc19g_O5fSIW#"
    "08&y#!HC^zA_>HB?(iH!BJ(5*ZB?a$ruN`MO&um`ES%3@|@Mpj_F^QhU?3;)^VTN*DT#HG3MG}-w=?(k^WRGz>D&8)lXM~?z"
    "y1E@R!v<8IOnG-m~@jJKf6Qp*5rdZ0W5Ti7ToZ5OZ4`34@1XOeQlr&@4hnrH~?GAUZ??8O(QKhV$plX8a`Wbo1pbNfwT7V&<"
    "90LJnLr`~@5lx#gQh_c0#8SYbs;zLV?=H`1xc{RNvJ1%(Gc(3lq>XQ}jVjbnBAzfz}s12(JvGVU_*TFb{7ndT?WV6j9?ac~="
    "J-hIFPlMdHBt{WK1-{_SE;Qxgnq{<8WHNwvWzf-*<Af(b`WGkP9C6Y^T7Ii0M<qa{VXCfTGXu@Y6)b_GrK|IBaUif34<*)(`"
    "_5NV8bT-LUaWx^vL|O@8Y8sj*RfVyaUk?`8?S@Mzsd3Hc%{{YLPlsBp0NKjVkk>*|i6N2(!Eoz6)oZg~6HSM7Uvp^gcp>eHA"
    "tyxIDa`rUpy3G5o{C7q*cv;TUJv}N+rjD=gq2YOH&#4=a{gLyn^=7;#q4mXK&6PcuR}!*l08j?1ngsr-X-1D;-|YoB&p}bee"
    "Szl2akVA8VFC@Qiw3c`ImQ_bhHqSUEB6eHCTd0(!g7+0GYRdMN*Rb!-NO07Ap`@*t|(R8Mi2*k83$}->xy>cH^(+uV~?g+Y6"
    "fjm5d~a-49vwHa;0F`&R7t*k-y+M;JNNx{WgHnA6fTkk!i6LlI|}DSeK*T(?D%UwCd7LwkO<Je1EEikqsE@Ps;dQW~Tl5G<J"
    "$oe_y(`BFC=*#^olKTv<vy-_g=<>?jXVPm{gQy;J9%09R5gS?Z~Kef@#WIjaw!1Uia<eUoCK2Kl7=ZsSzP2^@3{`6^WCy%qK"
    "9gC$hip;kDE&{7m!@GLyXPKH9!u=a`YH3V$FoJ_{h;N+-RhL+!N!SiN<F<!gJ=MH_xzS?jeT}{XxcX5^n#gq1YPVgphX<Cju"
    "L7$`y})YS1%fb$AB{j2s^YMuXNrjXdqWN6Ud_0l?w3d`hSb4c1>bYLJ5QT<(M^oj0kXy+xi{`?7AKOcNVF^5Y`{SkL+PySet"
    "34sH-3+H?Jo~uJ|yi}vrwLKIz)7A4jc?RZb!5?g;%m<S3qaAf$0jPR6-PqbNPu+Wk}7p-e&YlcMP9a*2WjCH?iL=e$`wTA{C"
    "F+<bOOoQpx}$q>gN03hzPW;uNa&QhTMy7!BdX9?!3)I1yR@d))^|6Jz)8i%Cfe-H(ack;iw-Rh2=t-e4Tv@@qss1L~f<Opn>"
    "ob@AEYkpku3D_}AciJUoheBsU~ZiW)Iuz1}$YsAnD3As-R%IX;H#yF-nq{F#lyjWEUq*5%eGv<%=7Bj4jj0gxfB=jsEpMVrd"
    "fMco%(3Dr?e3*bYVII0J^Ym71E|cX}WNRo*RyEbw)vO9pdapS76gNezB!Ci20BfLHc=>X>c)BQpO83yW-G-k)xUW%uoS^#2j"
    "by71W)ih+KPrM7yg=?7>(3qV$wAVw0Y1c11OBf*I+#uMJ@gqN0ujwJg|B{W%f@z!fS7ItPcR&AAmW5VXZZ^J-0u^~5Rj+#p7"
    "D|2O?EIIh!Ks(g{q%VYL87wdpohhQj<63UPLgrL}lBc3%up?@JHG8tSUicGGZeJCO8;v)udxB*1Y0!pAwj_?NEc<udi2wUH+"
    "BRdl55+!hx{F@Xr0gg>clEgP28LU<_?gA~PFT1-^jgvD_$O^)gJYDERc)$Zob?42M08>*a_Z@m^B>K|?JfN@|gY2K&!(R~r`"
    "8AWnad_<YfE0n)|cbOM`u#f4_l$mJ(h(Qg3&w2JnFP}5A!f13+kPM-nU?wL;IQ$XB+b|`Hfc%iz(^o~3g8^EK*ILL_)W^PAe"
    "nL~QJ!e|El2cVCYCv2e38!Rgyb4$(27Z?3--8O)~au0)m6GR=UmSWcR`guBX;LZuOZtl;h%I~v%iH*DnkaJ$CK4Og3$_8O|i"
    "ov6!0|Twkr4SrCvGPh1>~3I)5YK2fNCV^t%j+R644G4H4~X?Lcya<t=IK}sVN;TWO5Tjo(ISWVwsJec123lrSF?1X{0@&8x%"
    "a94p;(L%=J0=x!EU;xhrP9=@Xm0s_ejPKtr@T%F_|?%5`@vETw)k>mq|H(@;nrnW-deiD_n4CHfrJL(+x$n+;BXUkyb1T$!1"
    "F&038kdPGgCa1YX_}DhV9)v2Y!CmRW^i@>6j)Wsmm&UYx!&YwDK#kV1&N1Aex+o=wiCaO?i%LS9E|=nHL@Eur;<fz3>a%4e%"
    "ymxYBi+A}WgPI?uyAC_~m$7zBp2F&P9#ukyl@si3nF&)I#9>}@uH&ZJ7j_?<T$rczE#!tKis=Ojo_@XO*<X20LNoas~TuFaT"
    "RPZ$ab=x&bL>`9U=~^<H%myEN1m8G{6tOrzs;9?aB)iWo(r&^mjGF;Y5a9$T{w|DDyZi(A|0^~O!@glUCprWa4!F}x&GzVi("
    "dUP<F|j)1fW?d3nD65ziBE1y<X7K()^+*3e3-=q8Vsrz#g@3Fl9)6d>;H+|_NW7<6wEG1*ylNan+eP6?L#@|#D(R)1V`VfU}"
    "~wHB0<pfnzl+Fcu|EG=K7h~!`<Byx|Q7IB2RsjRJ%(ifMJOOk4d%K_svj>!PRNhPA`5~_q)q0vl`Yy`@JiW>4WAcyhh@;o4#"
    "tAF>R=l=iquG8EhOexG#evVfSf6Kci-gWtWtRwNv7;wiP+<^Y|#FcB+n7!I3N{2zK{pSf;8&|Jy^=vW-YM-pUFj(2byQK>Si"
    "zD)=}m9*b4gYb(x3SW>|knNJ<0EwR;rORCd*UduPScL*5QgZa%C+ut;DofZwGgpv8uPK!=r)#>U>Fm3N8+^T+7AiLbR=}h51"
    "n;}MCIPE;?)v(ryLJ=h94Mt)<A|3^L1e0tQUw{Ktw*vSrp`5*y$c23rp&N?e_uNy&eFkgH2H`ZaIa^m2A%Ch0_eyz>hDnJPT"
    "Z~=Aj5x6xvj@Ln=~YmA)8^qjspE$99?!8=J^g7vG^e=S7yg5uw7fsrX`R`@M)LrFvfd5-d#e+2lajD+c1UZKlis5ZN057LjC"
    "xdC4|8Dn349;KrEBBil*Q2M`rM8o`Dst_JocY;|AUtrr0uRKVb9<Fs7q;4_@_V=j$ad%7(rFg8_~ZjfxcpCYxkyHln@xpq~X"
    "@|0Ixr~Z@!NNVLf?yfb;Gj6hHQbaJNFuHRS7G$CRh(vJxT$dBfL~a@IV6TA<Sw#OX-Jf<GfgD=_YQXY1!*u@(~g-^0P6xQx-"
    "KH%V0$?Gcn^pew+kHR+??@lvZuB$^pO>upDE(Y>XY(f;3=!%F{zE&SL_BB1b#zOR^UQo$x2VIbc2l6zM8BD|A#OmkgL0-?r>"
    "aMi8(@eYMtVlLDf@NOU@bswKDZtpKmE>u%-?mMnKhp4aEhoH<0%ooKhsK0`CNlxVdTRGZ4hd+Z+Mf-7U8h}qJ5Sz{RD~UnT2"
    "{(-LN4Cc#6{02F9BAs^rJO@~0d{Pa;g>n~^_6M1yGqOw3P0Eiqo+X@Pu#JJ_TE>$O@3RjHsSll(Q)gA*aGF~euJz!22(0MHJ"
    "}1~&x)@Gg`k&Cl+5r<I#`xee3#0e7q6{p_nCQ#%>I*IB*=lfA&;+DV=Kb?oo_^92~8#K*STlK!y;D@%pCnUL9w$q60vD(E?+"
    "3C$t)HmvJ$D{Kyk2O#9TPTH=|c4pXHJ~_av5P7E-krhONE$-IYT4lr$0C56GX2W`X5B#uq421+?S)O0&eTM7$-Z9pZyQ6}x+"
    "^v*GH(1JeIFKm0#CD2v-GNh9<D)3j_+m8Zmun%{|AU{gHnJ4FBulWg)pde}ExG&sSB%2fUKmy9mJ#~J4Q{zg+eRXfMUHmR%&"
    "(H^A?$*iIa;E<_MNUn+quwUxUJI&yDDlbuQGuklt?C>PA;Q<yq+TOz3u!@vbk;?9FE#xSt*FpF(<fu8S)IvOe3l>6f>@nR93"
    "Ap=#kL@CT{bk9O&SfVGrIjU&zV&Xl6hcKq>pYSo(b8=Z`=nAf7pY|&<84+?6&obO@(lxm?)B3~Mb!2U7huf;*B#UDv<-jbeE"
    "ZH5IIlVj7W3gPIg3utX0JC+Rr2|5A*h)PWQ!}~_&KKf&Z)3RUsiYEaPr*7iZC>V`A-^hxacnVLy<1zNQKqK-$gC1E6~8X$lt"
    "8>01JhTyfP)W<?NtHk?GY$47f&<42X|)U$pQ6Li+BysarNOso2>aRSg#;C-M@B#Tg;{x*O^}(>@1$a3dSTPq^eU2o_6rRz6Q"
    "5UD87FBP_N-t@)rnx^Jus`{a+jrCt8~?R%1MzK+=W_cfIpq+<Hg4$JG+m@7(R3#>M4WQRXx_z;e#I6gv3eJj0_B{I`_b~JDD"
    "uci9GFlCobDS<RaK3BR9yO@O|wqoj<2F8FQP~EiNtbC|s^Jt3+`J_;O*s~Rc(;mX4)cwGv>w#~ZfJ*rh2x9jLQ!U1SnH5tV>"
    "o7X>xuP)yU2a&>9=L?cC6RScqKN;&VY5j4=_leO2L|JYmdT}bfPy0ecc>TD!xo$9X(+bck7z&UXMPl$O8y+?PM)vbiB<~1Qf"
    "3k`Q}r~Nd?GA38KifXeO$E{GEvE8=Swv~EaO2Qp5H%m(w<mANHkpE^S#(z0Y;ZU`l<YCK=+iiar`-P;Z+tIG|^pBf=)4scS1"
    "x`?5Ib!#KgLcd61nXR9%I#4MTrTH_N#8n<aMiY>QIZ%y8s^Ez*^`U#b*8%c5=-i2JTVm+l~F&tZvhL?kj>iUyV&8M$4z4Yi}"
    "O6dY!XWA!lj-=Rv2dzbg-B^nq2Psus9Am*g!soS>nW)BTg+U4-fDR&3iV(M^D90A(M;umZ{#HUw7HEJni2N7$qjZU;Nc89zH"
    "(43kT@}ZA9@P*5z1@#hzhWCAGx*Ctz!)~_lCzcDX9CfC(5_f2LU>>IsrMbz)bJVw<@Xj?tk%;_G7dx%)vZ<p5+GPINCudqY#"
    "q0nZ!>%yM9J`woB|sG?!hNB%vi&6y591=0x5OV7hyYU8ACEWjdawoc&X591@5Y=Kk%u*INFSa~fOkxM!FgSg<H*3k;nlY2kB"
    "Z_xK6DX&uqk?7Jdxy}GnQMz)E$iiu>O$5zY{X>-~F|EbP)1Q_E2vbbBCZ?N}~YE#ncSN8p;KtXEh<@z|CVgvV5^$=^Ut&l+s"
    "Th8PVvwnn&Lfu3*i>+^hC0PTj>7Hs1~EM~gcc2l`AlD@&eaM<;m5V!dGtJej+0U$du{2o#rB3_^mT*R}ck7o7DbVnWQtd!}8"
    "+t7#roK1E7GL~E$%JLy%wb5=Gy(z|lYbBg76eGg(dRa78Tg}|Gg3-wOE;k6a3eC)|OjrT=2b^`&Pgr@<mWMyYi$j2dB7&>pX"
    "X1dIh?FdFPW!J=s8@n6W$z273tzweOCA6JCFxOxcn{S9k0pg$KJ%nYV^akN27MJG&^u`z+TAbLbJ}l<4{B}yex-+3pk5kD(*"
    "s!chGv*Q$R+#NO58IYTIPWolJQa2de&GMY-lNHtp-HfDM6gy1-CzH(sPA_G3m!k5T2gTFvznB#$#W)UZnn8(vu`rU{z_aL<F"
    "xotR(zUj-hki`OrQpH4q^Z&#tDM^g3ndtz63bt`52%#`*pkg-rurcQiRA0=3)4>B!~?MYrKrW!SziRMwJpBrrL`IeUGq|it?"
    "!B2?Mg1M&K=v9oX>9vtw)}?vlpB5y04sNA$yFSxPqov4S~|xh^E|CXE39^I?ot<it7>>!ZXPskK579{cxKZ_-M^?HkAc?(a1"
    "JetJa|h?3_3Pw4yv2q5iiF(yy}UnC{37TVe3;(H8tR-59{i1gh;A2%6f1=+Wa**#`BO`R{Rjp!zuZjwvC%%6qmaKu3|eC~0%"
    "8EyA8#rVg`HV3)nAD8mb>5-C5ee(!~WdM?@;7k;u#Z7cH<NIKIHC_yAuwR)IyVRkq9!O{__&*Bx{<zRome@e9^L?kGASQF<^"
    "ajX^N&mumD)$rValSd!8NY&3%?qO64~FI@ckOT36@SPB2@H&U(vfa>*S%GK0j^FEFs%q6EPf#>>O7`q7s=iP@Y#pWJm^`xEq"
    "b58!IHh>ET)yyfC+@L(WQ~g*|hBA|3^e3|Na5IB8Ki)Rsj;{p}$EU$ry3wwh^!OGb|c-=BM~>B*}~(D!_<QS%F_fJpoY}7yf"
    "*hkLY9G31`98gl>|z*HLjjx@Gu(Xu8U<IJ#!J%i?aq-Q8Um_r)Q>HMqMk65QS0H6g(@xCNI4*WeZ)IDF*2&;2#OYr4Cty65y"
    "9rkpV8&XCGMi`l{inM<>{s6*Ar#e)Yk)x1TWFt@xQq`*c8<^k_&SC~p?pX)aE={>!F=R9^mKD*&wUY}7nqrrOuWXNLz%m(u^"
    "mCKh3w0iP=P_5gB6(TzR`AQ-hn=dyvzY?7hzfG!&Zy`q&Bf6+9UIeKFt4m)dYmsMHc7?gLS3ilwtImG`{gSm4xBVqY^_i}$p"
    "gbzfZ6vO7v>I`qJA_LC@oJ)Qg3=X6gxc;7Y{OsbXDY*=_C|)?|IMm-2QnE{$@)?%w^0qWk-<ZRgs*y)3LEp*t+MBF&=gLC5h"
    "RoL&>SI?>_s%C+fZ~?Wuw2B(cKa!tIrzmtAL&`wMw$mWuCYgC9%wXZ!T#xGKkA9Ed2SDJoRfHk*3|$KK<{dDoyq;My%nD5|("
    "rFGpTe16QSo7qB{8Arn*4C`VRa&OY9(njfnjxqG}yPIrv1KR8-8mN8J0N5yt7s1<sUcso5^g6iPZt@;!H`lP|4*cPC*l+*{X"
    "={IEAE%HEgYc}vZrXd$B16cESVQz#9NyDrPBFF;z}T=J2SBz!z%*efuamk7%juGrj+`-_6<I}C{Z<6`wz3;%5&FXC;%im5Np"
    "9UMZcGGz~#vqo~YZ29s4s|O9Eh|@wqp=v3QBH=m~Sy6IfTf!%qX8@mlPk;<x(ucsOO)fFLcBHAXY@%s9Q2@>{f4M|1%EmIhy"
    "`$`dd(#t&3!?jwDY)G;4zb7AW*8iO{aXH%p6>)8^wy4Y*WRp21C3mtpBL`bvV<%niD2uvB<F_oMKHU+guCnx6bJbRc-R00c^"
    "LFfj<734nWCa_DZB0Oz1b?aq_#iyinbUKk4(f!{8|X&e(8L{ePC*?UfRf?tUS)qdz|6!wTNjFqtDhi9ojR~dQ{z?f`y5tR?C"
    "tymP6X1PN<B>^@qN(g5Ce+!BFN!XTP`cvn($raa21@=182)v(*4#MO%S50_syh^7kAJU*;PbFtXLZr9jc8Bzf&h*Xt`~gavU"
    "%#VC%hMl5NDS`T>N^t)6Sk;$d(yDHM`>qqkS`rAF>yJqtplN{h>vyLaLqwpwJsa9_wxt79JbAwyHad5shaRy}POt>@ZC&*%l"
    "Cqr{a?-sNW>E|89<1A&jKgE>>VWEUHmuW9?Diq^FXI~ZkFIFVrAX&aWZfJL7nu(&I$BVr_xRYz{3#q955eJ!|rVG2(qlSeUD"
    "NXl|_l6p>1@EvO+1uq3clH6cck(vG&^h}j?*IQ?oL!>2dYxF*d1194hdLe<`)@R=AGQM*eD~oY$&w$@C_n3kG*%Ihy~Bv~RZ"
    "2a$ie%GBIAP=bhT=~@b7$9tD`wd6AU=Kb&bRrx-D|<QV(8K$iLv}{kk}P_c&pp@zKrQ|e~D~7Ya~lBqbUmZ8cJe|!!-h9E~("
    "3fzA#^5&<bmwTlT#<%)*s70dLumssajK7IoHP%Iffg7{$kQuzX=7A~r2%KJ8_#aesyF5@2$d%aMdz*Y~kyvuT^>ObK7DD&k0"
    "N9fSf(x^&XJPf}1tei>4?AL~1C6OO*q{0(?6`@^xOr%|Ax<@@)0y>Rd*2RXr8*0cO42XS0fVwxx4`ztFY2nB)Gp9@ge?;Uo#"
    "m5W<u;0l3eq+<3S!t()nHq&zKUK-m!a`<-8+L#h8)q8IuiSzq#Dyy%Jgd(;b0h%^!pv;5-Vcx}7clg&?ArvCn%hZKAkE?3Gb"
    "zJHXHxvDd%HM0`QDGUM;#+5<(Bx|+kqT-~2et~)htbt3S)pMw6)p5hr&3hGtlL4Fs4oMi8j>Lz%zX(c#)3ra7F__1vX>>Hrn"
    "Cvvr&#U21pEhQ-&q+a>zdS{x~pPR30V$L7DNtdRu-JIP7YtPOezXtSD0z5T>_d2phtlZrloScKRIGd%@)kZx1`7X5BuphIaa"
    "|RuWg(8R5NZF7n%9$QOGwo?!U-oPO~v2pw!<sw!(*9#EimoCh9Hl$~DdEY2%cE^&F8)yQ~yHilN5|SeLzb5Rvd`Th>F~RVhu"
    "o+np*m-pzfxJN72N-ls-jEJb$opYc+g`F7O0Mpf2Z5ki<|&o~PT4%~9*z=6RYQi9&!#Al}lcwhlGHQ{hwgqE#RXZ1z~X8G#I"
    "Pwotf&GsIrOQ|2_Eq==c0-qI6ynx=4HC_B#GN0g-z-!cypXe{^Ibh3O1quOLC=wsMZe|z%Q>nj<7x^DcV*SJ+bmlpZ%|k&jg"
    "n|_o<$8JddSN?|jyU%0m2Oa+5k?W69Q%bDp|?e?Z+JKYm=Q17&oQz5>A!J`4bxt~cZwT%z9gDQ+Dn5HKv|R?du(kqvXBvt12"
    "kaKLBB)t6UxJ63Vq3r3tAF~st7A=b@uuKj?wI36Gns}{R)wae8ioaaj!QPAmx1;c_B<au>?Js(oc1Y07S}vKP>B^`qvCCRac"
    "nYcxs57YkA+y-F54$-`wwUs6mj|>N%trXT8F{(Ygx-9XHG7DCEe>7OB7onUIjA?oz0Kl_EhQ^@n`~#(Fu<W!ey~USr=6r&)a"
    "-AFp&|(>izJF`WollYaE5AP6|ekGfs9VJZF_WLm<?u!g}Pe1N5O5z*8I-AoU90~_$4D_Eu@!QUJ6y6mz1(Dac?#>*9!;LRHm"
    "oe+`&78Y4tKs=xUWuCQpzu8VLWC{_Jn4BTw9Rb&8es$ESJiu`z81GVdM>s7XR^}o5c+dkc$`f6s0<&eh{SlHcJAR>`B&Q;$<"
    "MAyw^+vNBYKZUcqKe^*;8m33-Gn6qFIRT(*eng6j5?5{Phpos2mV2*%za5Ok)4}YvXZETz>N73z))%3;@R@vg&E5P#4h*5HP"
    "Ew9XAc~$Q@=_r(XPJxz2&1}=`hpPiA(q=bx;BV2&lG2L#cx+xiLBTP<Z~B`ln&;<%a|-wHhILgxauvou7IGDZHfP{qP&~i2s"
    "5Pf<&|9A!r$Uy*X<4z&w~*=3ri)5$=BBI_&z592zTbQJW(NS)zc?>Q&)CkF74nBj}+#j9~8LPZXV0FfN1`2=TVGR<Ja2J_21"
    "NCbRwqP9K17V1OwmmASre!Kb3=TBpX@N-dZZ3A~0&;aWHf<~uV7dUS8zc}?sLc`~gi{OPe-)b#ilJ3}c}f}h)DHm%;JlXw@U"
    "((3S)rBWiNI+yA};uJ!whtMoZUz3EVlp+BCD4ReNrhbym*b!I!n$8DRx3cVd!0#;Z2S6z?7-Y`%#Qr_z_=TPv<h;ey(MuTqq"
    "2WKpyOFray({d&Pbe<-<<<NauL!iJsPqf5(?WK}g`-l&jf4-@qfpC%xn?Bf-Q}S`07S`-VmlWwY{ul+ja+XGe0U4FT0X8Zs|"
    "`K2V8Vz<p<D1|L3m;=mCXgQ-f76a1!!WP%(*HLSt)3&dLoj+_Dn+oVEN-cpGG~HJ#7*dRRVQ&`n#Q_a<5>Vm)BaTlmuxv?N;"
    "(&!Osk`CL}E`gonFioWdE9m<F8I*f~sfnTaCeyiBB9bIhwsx#^w&#qdu80}1IZqWece{8zfAgi#HsMCo+HgwN?dr^hRy<@7O"
    "Pk02<y&Mb6*JD3ZoY?bM9*NUoI_VQZwmGC0|&*evgk8A&(M_)u+*p~1YXa&is>0*(v9(_a=6dmDrb)3_7C4Mu$(dx*IWuMUd"
    "bPmg`<P4wG>ha0X*r>$aNri!nSluEq2uCejJO;FQa_BVF*i|Z_i~VazIVSH4%oIW3LdeZcU-bN6I7wqO`BD>IsGTJ``FV|}X"
    "IEd0nd>#7e?NP1KAQHm(WmDU7AWqsy2lIA-mZFh50?1+;g$ua2D^_U-0dv(Ym3o9hHXyON#)m-ejanD^z)PYEjhP<R)HhNeU"
    "`Nx1;j-IR*MTwo`U!y&kH`U2u`=;FRD|BI|PM~qKAO#s~v!?_tzf$V7KUmH_<;v{%`sdPw;MUR>B|U9f^!#jkg>~j0wfLq$i"
    "LElc%YGj>zHxJZGY2g)Yxaz;jr{lXwylm!wYKa6s6nKWlmIR35m`g4)WKNUL5?IvmO%1A#g#_T04z0`Zn<P1-l!qbjX^Fgcq"
    "2Vcgg-$_R$nZumTN{Hszm{B96U>gVUz2%+OqXSQwgGcl1vovmdg4{=RoT)US;a}vUrAtW$5%n=1RWf*hQrYC%(;S{+0M&hnK"
    "-evMmi4Dh~z|IbGLs}&dyU~6fLSy$SIx93%Rcsg<N?q6WY*hA=GjicDb1SG1-?XvbBBy|NPAk^UHV$-3596)M+5cm^b}B^no"
    "hf?0>UovwjZ*pe_#@5e9zFokVK){XwzXDK933DaLqlHW7#z)z#IUJTs!oh@S-ll^hZY1o;;0wQYMBmVq`#Pq(odzJs0y+R@R"
    "O=p<8RX5Jc{`_^-V11n|X=6Z@dstdhpr;tj-6J3}#D`tivwe)Vrg;h5bYP*WGb{#0BfY>Y}L-hW;HBJrs4PIZzR9U5mZaL-i"
    "yktOtrZHj|pra~lIb#Z@CW-3cm_M;rekd_GLf?<B3dAWMeVOj&aFgHAstHqdv*6yh12m3>%-7B~kps}KpFeEEu&%E|d4&^k!"
    "{7I3Wp0zS!r!l=4My+eEf%On75Q6H{5278EP6sPhSR(Q8$JInGC#Z_YdPz{wHBPw*Cv!_raPrG|&)xWH{M?UF`U-)>>i2}uj"
    "ijoY87u5>EB&rwUp5d@jp^-Z7FxiS;qj<o6^CYycK;Y1QbQ3ZR*>&A-e_CV-c`vAXidI%$!3)?PJhBn(8ydvI5ML6HTw7X=h"
    "iosYMzSw8Z#^2lGf!`*H;4T;o6hwVsz&ATL5LVCLZ}5_=$X)MJl}_Dq_}N2Nh4;sQPkeY%`ENs{%rNu)t@^6bteN<8W0Tp8F"
    "#|kF0Pr5Cuq-jq>4_~?&UYrWXA)T(5?}Z?6qAzw;_^wsq#N5Q17c4`U7D5@-@OV(*x<hF^N}LYB4k0ChJR`H<5O1uWk}4HJo"
    "fX;CY`%dR;oj_Zw%-th$qR3X?5-JkN+$h$cFR*wIeF3jbCM7ulb#j-N=Me_vvS$qfcw-){NLa~4gK&dG^1Bj~&aJHEruoqBS"
    "+uN@?$*fu&IJzTS}UxIV>Kxt^Zh80rTOxV;n{gCD^fY)>tv-=E}_|*Y6aQ=FxycTYU1dCx@t?9{cv1X^=&`W9&0;u%ze<u7<"
    "zjnLBUcDj5L7BD_&hz2mMfuiFv))p#lju9d{DgSo-o_p1E)32)lvxtAd?JxX3pzW2AFy1%dCPwN|FZvqh6L;8&yIIjkZ^p_d"
    "L;G?W+HqL?ys`>Kv#IRHSsQG9>&<0x;ceWBur|YVs+8an@hAIoSStyeA^kC=(BAOH5+^u9}8=1Bh2<_$fVxMZ8Gd9X>>Rx@_"
    "1TBC9_9*Zk!L;@M`|<bB6$^@RVqFnDWK7f*3UX947{QP7Vi|`R&gRZYaAH{QG_dSA;T+@zv22#tvZ>Quil$10@xXYe)g^6I0"
    "7<WRgfYy7{2pcXM)yhZJouq>Vx2J&6S@<O4U5_|BH<HS#ob^{|56)^Z1WQkiz$V@I}!pV=cpm_Ou}I90}F3TF5Z1v&5tU(Zu"
    "+3ylQJuEBTUx8BF-zuxCK<08a4Ms>?n%Ne<z=s=xF{FygY0_Spx@%4wf*xCzgHGVvNnk<XrZDP4AlxL_~tX3hI-)TKEcuQEv"
    "-Yu()8j<d@Y}rU#R)gl<9Ut#Y-tBcQUmWnXQf(-09_y#hFkI8-u}Ybmi=;jB>|IqbS)rdD0>7C?Zx2+iUud#_F!N%|da$RG8"
    "(Q`Wr5`gmG0A*d&RR+2O#32gUIofMyGvpw6mjk}Ansn!Z^Rx^O>BnIs2I6G@GQUD5-P2OFR^dF+C69CVzXa&2oF{dvL*I|NA"
    "Ff>C*M(ZsX}-|NcLadcYhhbD;agT6IR~D7UAvfAsKYD*|es;1~B+qz{koy{ZM33$Uy~?uFQiJ9$w;b6RJU7w8XD1k2Jn~Ydz"
    "VuJRc=+Wy(AW$gi9RKeSd-sM%r<_44XrXYVzlWGJ@vcnG2xe(adjW3G&l%$Vh|A&4At`K@FxjhvDKJR9A;95aZZKAik;x#uj"
    "Le^E{FMYL72BB>_(RZW;ZmArTMa8rxRoo#PRrA=6!P`np@3pr`Sx!|dwpVq$Nqlu4NND#!mJ4$*e3h%ijJE)3_KXp-Rx09C?"
    "fGBi)fL!h;z#3uuqOcz-G^Dnl*%0fYxfbM(?q-GmChhG1bvgk!23TAI@d=Q#AushIA8%h*NdgYWsE-r)HA#v@#G=>h6Xwf`N"
    "p4X1!kk3eGHfbcth>J#uzV-a>QNK$p0Ks1lChC9+v+4>ZI4tA2il#8{XgFpbBLL5I_4q~n{UwMEemI~rSt%%Xd?nJ4QpbN6P"
    "swHU3{x!GXD4;295sj4)LiV&#EaUlF0L+n1`ugLDJ0}2v*9@6o3rryUT7*NhGk%;XGk%YM;%tCS#~_r{<B_(s4#K<E-Vnz~$"
    "$WXZ>ZCVAHq~%U>eiV6_hhyYnT>ufytt6?FUn0k)A#xox)GqwgFOzTy9ztN~nXlp5JEG4oP&wo&w51vRHQk=hY%P~Mm_7F8W"
    "mVFXl+_JvAqh+KtpW1PlT>Bc`51`U?i<a2Ic(07HC?lW5E&b0}%B!;cEg-0zUg<8<(<nULGRCE>@MhOFK)7a16?L(zDD}69&"
    "OSgz9d$y7Ku4~?IOEj*Z(2sz39{#`9!p=LiVew?16fO&vVUnq#uz)7bsTNxFF{1SYLkzWJ@$&xbF+)G&5DYE!t$L1xOTEJ7X"
    "PdO3fP}>^e)l1yJde^j$!vhTQ@nngMsvCt!Ve$$tC^VJRZ`Wn`Bv(~pqnnJNZR{|#>A6rQ-Y7A|1IIvBU^YYcu!t=XZX>R$-"
    "v=nGWM^7L9(O^33iGqx&ZUL!{p%BmTy&@ta6jVl%-mwNA{zGWa2SXOBiP39^zvk0Cohy$V0~nF4*yk7`O9+{SjIv+-3(v9O&"
    "HKc@$}$Y21{w?O~rnK2wsKn5_=i@Ht6$d-?67(?s2Avu}3YKRPSiRYrm>VXWDW=BGH&a#2Y|4s@YoS5Pk(Rv({5I8ox;orEK"
    "V%RVi#8@))w5rzn6!pky-u7a~siwpB?W_99M*=b%++{_X2wFdTnO-Ps5gI9k88Bj9%iTf?Er2m=snn)(wJ^D+}FXS7t3TdEe"
    "ikZqzFS#U|IlVD=<Y}xRhle?6GJKN7PqhJs7Nq%cj=6d{^prAy@DbrtUI0<f-!C{ObyV7l7qp#a{xKRz6+6oD&~m-oW~>{XQ"
    "19kSzYd?@HDluZc=)eQXRd`CO;eE+O#w;=eA(AuSmAsnQBq2Po~7*<bdOX*iUfrMuGm4k<in;l=m{i%WG+CV-ivxmqLVkRe`"
    "6yMajH?`r>RDN%h;<BM^S803lk?a75j;~SL60$%8_a-67`0H0DNNP!<-fFWyJ)`+OvdgNKpN3@csQPdg?fa`kFYo-CJmx{u3"
    "_kfiS?3T9wGB+Yc>_F8oIr5Lq!9&O>%WX2Z|aU&LAYWDWpDlYm0g@)T={vK3Vu?nwB`UFn}t+|Fw0Zi}6uimA=C&>Y%XVnO#"
    "#IzlXu^IBKH^nEdgStCi|O+yqv-M+qP^-B!1N#^6j@+c+zuVsy5)zZ&dlBedBf%cy<Rvi5m_C28&ly(^xm-BhvLk*@Hu$2nr"
    "+OVxGqPdCa>jfPcz23t*Q8TEgZN@JS#_v{Ec~*<1G3>9u>%{A}^XEJSw2RZ1Jkl+1Ffl9ax7fV1mNppOQmTH%-`wtjleznj6"
    "}IKW_d*!ncJ$x6jV__3dL2HekSDCM9MV)#In}epVv>X^1S$k$IjxDz{mcteCX)A*fdIIk=(m_D8HoyKtz5FJAi`xY`#SG_>P"
    "&8)_7h*|i{d4k()a2OWKiFI_A9`Kr3w9_ZEbJ6D~1<mAD=zNYff?B)i%rM5aRRmr1Ud+z$e?rs@441FC{y?_A*30hC=A>UI*"
    "EUDKM3$*MD3{5Ua<s+(!R8Q@L{_Azyqmmbx56THr0DKJI7uyMB%HC*}{f<8?cS&|yt>5K{%$sjdfMy3PeZ5kPjP;Dty9PcvF"
    "F=&Sl77}(rSu6Yj-bf{X}5HF5phkV3xO@EUvUB-XZ{kvMKn5NGewt#@V&%AOImn61Vb4VNw?^yHbWhbX>20&r0MugIzW%IDX"
    "LqRHyOq?{-))-^2zNtdYzj@Pzr*>dL?*7q+p+qYHUA4HHDoRhB>WrB426~jb<L&FeP5}C7%iTG+ocF`-ODFv=gY@-mS|DujB"
    "8cL-OObOR;r7OKIG%V$&^8q*OtqDN%cdb(iIKd-h8$sy=;d=D^QH!|K)I&<&wK3q(W9@eAfNeht*ZiUbimqj!#xqFZi-8H78"
    "{_>kv&@$Lg(fY->+*Za&W_%dim=M2~_iB*YpkHe-kHzvRLF16z{@s?=~a|hqo%P)rbs|FCjxY5o*u8O)t0-RP;cJIfg#zAVx"
    "Q6Bci(?l+1rN2ELdlb1i~IGD8SkvD0cCud}G5KVUkG)<na5i_w3wO~Nv6y3K5UFh@UOFq|`w`%;Q8Ul%_^I_a|9HMq>=3<51"
    "<24^blP&9uXsidwT`~tLreHUdXgYM)WU*d)fcS6+p2dPug3nL$uNx-4wj`bEVY@y`Z2VrTCN%nf&eaq;+>qTJ|&(pm2pvL#r"
    "=qHoM#{6YO6dMj*U&Gh0Vc7{rLP}s^<3n*xF7Ua^BLw^TQ9N^CI0giOG+s`<)ic@#>|3Uf5hhoi+<5E0&=`dql?kn-5QNQwX"
    "TJ%Q1f@htNkOpFC3!ArhM`e>SwP!rPI5F^R;{h$Nstb7tB%n>&>c4Dw*`l%42CS6Z>gm|B8;NuM;+$$pVS*7YW+R3;*OH|@Q"
    "FHBaCtx#-g5`4&5vSKIzOED0oI~$>GbL1ykb4L-}Loz870{GmOWi-^FBqmC-hqMBxJ<zI`2K1lZxE>(bk&UF9(8r+x?uc?}x"
    "QMLS0e0#-r2L8N5#Xv0hXk2&#7|+eMWY9#bw=t&jyj+yv-sNR9rKqk1kVd}K;9$J&LKO|U+s+n`vx>kV!0VEg;yTXxoUVii3"
    "KkQ=|zo9_fc`oCldoABQd47uGB+P$hsOKK)1bg%lWNtc`&%TeWMYFnvLV0ZPyR=OZISnhQLt*BVl=f-HMNys#k89(4@{r3;~"
    "1fxD<1GfYbpC=y;Tuh18w8Rf(VU3Yf+PCI*w>I_?vI_*m@Lil$anxW{ZsgtHDOK?yzwDFuTo5B=rWmbw{;m{te6;S5595-n7"
    "Hhu#c(Fc#XcPm{z(tH{b+2b&hr{0WM*;D@WDwWbb@+Q^BottvQ|d$d|FUQ^$ylKhKFphjqWWrjTIM#;>4(?z?T~;aaTDcj;i"
    "tJ6ZeFQG{BdYIdzul7{H%YqB)kbXYcK7;>|Y40{;?97IBD8h(~Y585>5qUpaBP1R!fSKD7Wz|uQ;4{a+n`{00_|<2&0W$R5("
    "o+@*o7)jZp0C6SVDa;Xj67=$unE8~L%Dpf$4fX7~16JY(jE#auaa5@!9q?Elup46fB%uchR~zw&F!#f~vd5O`2Mzj;^G5NAN"
    "aAxOCSN=VcjZg+O}1dpH#EA!lM5=PxW9=q^Wsk?q<xM%XVxaVX4EzLt>v|<%YS&hU@kSlEFu}p_{$+_G<+A~^lWe;P&f~SoO"
    "^-h7_bJEbb+!OKEB6^J@*?3nRYCne^@ShX!XOIok4S+fSb6f4M&UM1z>jYb_EL2@DwU9{UuYm(C)-IJ-DLB3rqAG*ia<66*M"
    "CD8FYob@{!rk83eYniJAefa}`s4Ec=2|g8T5dph7}+}<cW+B>D4J6>@}sbh6~MY&F`YHcLN_=oy(QHUnC$WLwF=?etH`8(<W"
    "f$oICjuV7|S|=0oXRO!=hGcHfPVT-T!H^mm{2s(eep{qKrpl#DpJSJk4k(Af=p`QoN@KVcP%WVLWS5JG<txxQAJhU0it*&aG"
    "+crQ@rtR`gU&8)3L90ouPV+LTB+Qt=Y7zSo1PT2wtNR~4Q*tHHQ!ar9`@n?({!XIE7x%~YKg0pD;PFvs?poG}e)n%O})9=>&"
    "Ma_9VkK5--P+!pDcYtBU3hjHjK@_ZBXXiU8{;qSG_Go56c$gHs4?KjFUG~a+%dqQzxk;oq_jz)*tX6f12eE0Wtf=`ndvh%~G"
    "LhGe}RfoFq^cT<pN!B}Z@meVXGO}H58B`DaKUC4RHJv5rMv}lwR0~h!pF(fj`HKvM3LgNK$rx`yWdHjnnn_n5sd1>#X|x_ku"
    "dd$J*VIdlCVOMdoy>FY5$z@N1F=(`hUpBw@GHy+u<%oL7<N}NU-0+J0n$KzvJ=*=?3F;Ha^E(U&7-i`$VQ>oB9eE;td44=Ks"
    "uZ(3eGPvBk}QmSJYl?vVL48g@(JLhrYHy;5i_XY3}IX^f!LrP=XR+HzhF++#EVhw-NvJ`z_VWh1wK54ae;EY$Ol%eD+iCBw$"
    "#J_#t28%Fr&EZ2Nj$fTs}`_we3;ck&D88DD$(H*=i=?fJ2^*_Q&@cRi%5k*@a?6jS{5AO2zd&n#!+m5R_s?<DLTS8f4pnToY"
    "^4$FU-Iks<n<2y*%4x-yzL3Q+i2Y+>b*X5fu#GzqJp`VM&p{BScu3gY~UMgkr;Q1Bn+Zbh8r1)3kVm<lf5_-M|UOHDB+mtUB"
    "4zJ1K*Lngf%Ysx4W;MbvYVEf=r7ouP{TT0jIXT>aAlK1<wXonHHROMeeIjAo;&U(ID$=|e-BLg&KgG=P)yed;(zq<>&Ty|iv"
    "UyM}whzIUTrmAK`@-mUd~+6;nOj<qZuRrRiXhzPzeC-o%dSYqWXD6tAuE?ExGuOJshE|E8mYF`aYC*z)^dO@29#c<NX@1pF_"
    "mh&RZeh4oF?lDpM_dO*iS9U4l6O=mef7qV7UpewxcF<+-!G@`;Kg^+8~Szm<)>+q0Yr6PTn6-9}z@ZF{<%XmOFz-xge;pLPI"
    "td&*kepZ(=pd2{QMc)GdR(*zFSAFO^0PXM~q#UrhFkE9Wtx(}HiR2kTa_Ps*dIE{QV>JF@Xbr3bdN7pg~Jru|$yle{TxTtvd"
    "Sj1rz1(ns%ldWXdOIVO1iS$%?X)>J-U11<WV2!6ko%_w;sD17!V?DW{HZ)_HcO?D-Fd1io6qa_y{BGGPgq6uGgq+tR{Dd-NT"
    "w*eJ(r{`QA^y}ZMRkX{lrGKp}K6*(#YLWnk^b)(O72ecq;bb{E2XCJkcg^NE>~>-Jq_{>vXY@eN(RqKpXbX^`HYCmBw~S+jz"
    "g<D^o&z;O^)CW9{}XBW(9bS1wqLvPkZy`(-Y-Pf5XG7=tZK$-F8D{Rr^uqnyd)IH^Lux23jHN@UH>QasNA4`b}l?C$*r%-A0"
    "sHU9V?+Q_9`y3EFL__`sz-~tg_Vf(tfsLft+}$+HYLq?a&C6N35yTLqD2gAYFEmiZ%Ls$yI~Dv7YulUq4V*^7<?1H)O0-!fg"
    "^q_xNc#$ZE#wL=(qO&)V%u!1|eAUQ6&qIzPUovbd8B{K&7Wq17%=A_-DwJM5r06PfEgp;zR$Q}@R_6uV&pW9MR2$d=7RM1lX"
    "Cnroj1`jq1CU(RKQ@?6E3*TLwQ>-@6<9)3YXyP5F=;55&+y4D4gk0_Jkg;U7X8~J5^_|K<L*oRS@nO!426?tGldcV_pS0i*P"
    "n8!V8*_j*1fFPt1ba`;sh7bIfxYH&XxOGU1X|#q=Eehw8#!y2?yw~r7kzS4`l7R>Co-nmsG<2U5uI{dPJp@3yGBiyw3}X1nH"
    "m{>6iGyE!Pf3=~7W*P}tc3(SLMS5l(IqWF!R{)X5q=M!?;r3l@4IDxwx93)!O5Zu<XA)LU@%c)brni%B~IRgSZeTmItzl=+;"
    "DnPT71d5qGu$KAE!`B=Y$=*3#tj=A4{=#N~m9t33-#|ci;Jy-p~oU)t#KR5uQWD!~N8H#VoXi#TB3FDk}uhAdK5GAib3JSUe"
    "!uoJ5@-K(wnd{}a{M!(FMOEBSXXEX-~P>j=yRIsNbjTLs41Pj3HnBM<uwr^DMzw?&G-B}#cHoXbdw^C!kcoW0&QKPEa?f8V@"
    "EN+v|xeL{9Gk98;^@xE|~$~Q#`!inAHAGULrWBYU8t#`Oa!EfJ6{wnBC<`>FBH>Nd9qg69^hj>g48P0sM`w`3ulcn|ORLXNG"
    "yh{)#qwTRG?mN>Y6aD%cNhKB;(8}dW&`Z<uVE&em)VaWam#taRsk4fPVm$KKxI&pPT+r*I6_dUjOH|Hk9E#H3%oS?W&FcS%k"
    "w*_!(SaUDsklx1OUavJGRA6y-sI~pt_bbUUlp!PSb(d28MAUb=BDEU*OmzdItk~N8!CS<AvcgABpOtv|I7++`cg617K#b?{s"
    "7J1Ap7F-_4s^v($K5!T9IpRrbESX?H+We^FYA2IM=H2S9?sntCleO!*)DD-POUNdsCuj>g+St8cH0PB9Go`tNM)P9OKr^_0O"
    "gJX@Q<Q*PGFB`|rOL9BxBJW0uNzs@tJkqTU3Sv|_yVM|w@JO_1}YB$l;qMY(RSnQ=s;8S8~_$UNDA@_v9NW+vZz3rzL%6AnP"
    "WnDL;h1;Rz#2~D7z^H=GQk9ti{i=^q6MeoJqheNY%70Op&hM0c;2!FMgeU!|Fb@PJFENh5Pkvobfa(7?|gHr<R#A7tjTt*$4"
    "?zVi!{B2vp;av0No$;w*3B5=NyZ9*VXK-xvWJR%1pys}l(GaxaF=s|nA$=h8A;_0dj&V)t@JXJ&v3TVEVP!EeRz(DZeKR}gE"
    "gkRwJH?tQD5YK=J)6&_A`-W8<*3eEIggO9p>d4VWb1G}2m#b#OhX7MhDtk*VgX$wilJr7fa<cf5S~dRml@s0%b{*GZ>5BU?z"
    "k2u6Kn0CuDZOlQc&hQ*Bjq=c_dC2Kms>mzN3s=lOIlp%x>E}{3G*_WCnGShe+SS0wNa|U8aP9$8*D^CJVjK{0d2JI*#kl{eR"
    "{}X`gad0k%7oN03O-5ekqJsf^IE!oifg2xk_%La_YRdg*P>eKNXcil~gNIFfy`=Ba|#rQal*GDHNma3CV`t>}QxW4Lcz67q}"
    "UYg?DM)h*#_jL2V#8jZg;fS9n$2AO)EQY;f+1Nst!q0OZ^8%z=}Ob*4LyC#L#u0$k{j8Ph1krB^a>v<aq+z~JN=leAPrIVzd"
    "dCh)ijjmQ=pS@0-xQ@9XZt~hgt=A>u(bHH`npAPA!ws6|tW$h%4(*`^9hUh?(k(atvUn{|`7vie&x+;{J1VMVYOvT;_#P-nl"
    "knXydUZKMq-#RTkzIAiicquM(sCT|A3yhkk`t!c_mp4e8%n}%=WmPkp2cdOxl#LBU?%^O{|650zAEvU1TD`^Q!Qu0ZZ3n7#H"
    "FrkmFgZy5G`n(;8m7jeEu<KB;zIC8WlR~15RR(PMq~$NmQ=`m0`@sP#Wc*4rcV5-=%&3p|RUs?-k>+fHS84<l%yuP*RLqRK<"
    "GfE(q43_;VyH=c~Zo|FmL&qoriT`l*$9CC(U4V7Wu%ecO-5igRCo+t3)}Q*uck5%3TWL+{XEE!iJZHjnNFR7qm4zB2)n(${f"
    "+qeerxZo8{KsHUP}Zs0##6IDHH=KN^MX#Vm~(7wWc=FfWz*bJ(o>G^l^zlH-{3?|~POoj!@ghYs%KWeJH%D%G`UX+vcW(Lz4"
    "E)vA*@Z6OJyW!g}i07<pmd1_2u=Qz<)1ZYIX0iO~!t3S`3b|FWfNs)ktmvj1{mKcVe3AS6?@|o-BuAgs<f4*6sukTGc5V1x+"
    "ew<pTZB^-nsGoejZ5}}i0uKn{FY=(3_b}t0u%n->KR4VSshnK2QVl_JT$`sS%42B#L(-R_J@5_DM}68^i;yo<qDDYVcW%x)H"
    "fYsd{rpf$VK{HIoIhPL`{G6Zgv)v@&y9fJjEdfy5J$QU0quJ`*-z!RQc6<C=3;{y=G2Kv<4gjSIlciKc!GMkOG!5xk0;&heC"
    "D~Z1{!QdS=+&L@aOJup_9NwSs{d$#E^-5fMML6MHkQtN-qNMdN4p?S^8cO3lnshay9?*`7}shKn+iTz1(0`$~2`&xViJVo1c"
    "Y#Z{<FQCse!iPR4EtHY;Nj!&}rs)vwSZub;_ZMK1p+x%fM@fe()`mwQ}F|}OR+IHeaa1RIh6)S~D*ctxr;Vne34_$5WW_h?E"
    "!WS7>#lwR1d-7d^b)#jN_Z7eH{sE(^|2u>5R&>~n5|Z}A#PDpJ#)SwSiG$_xSQPaxaUH$HJK`TeIW+cBsZG8PHlwMYHQb<5-"
    ";I>7&O$reLFx1t!)AzSNfq~EJyh4@{txK>W&5Z`;bf@68f7bkA}ceFzHac}=WVX;jjT8v6WS~Q1oY4a4OR&J79wrve(=L@%o"
    "d~M%3QJD{cA4n&i%bVJL^aW2_$?%jCaA(ipZ#usqGtTIw@k3%UKHLot$@v>}zweMdalBcSh-o0>aN>%i@Hu`<sl<5wF46FV*"
    "dEM$ffOEqZ4T9|^+S^!~f|Jd@U38k|2=!PI{z<I<vNECwf6^?t5bw*_d=_cEgeKfQkE<Z$tk3r@K<6@D@`WCepb(9o<hy|3r"
    "&Y#3n<=co56hU-svnM}-hFO8;Xnk`v`VAokS*^$2Y0TC{jcBKwNTtq740(EgFMtX=TLME}g{`MD|cOcIAZZtpLjmh^Ir4N>#"
    "7x4GTp*ef_{hF<eCz84gA@~RFFQim+@>8lrSF$Jb1lKy_E@ggsi?AG%!S6wzelG}uB4J-8b0cDmhfyw;%3wMlQbOYX2|?K>("
    "dsv$8xQ`;5D{@cv=Ulzsc~(>Jj*1rc-`uF8oXAWoX7L>LxisJ4OMa(C`-2BM6GF}_)n<+cgZgO?I~H=i^Fy_t;tK#o)TOOF*"
    "o`b^DP)hDSls*5(FKkx<_T@3N#MlIzpK7GS1ID1m?*v$upI1AGhlP?&SrA8qqL`q|FzuUr?sRU&QYWj1;94R$YI@T$tW+IDT"
    "!%N)N7`mkesFWGgshH?kP9qD<vx&ia)qLh<{>()Ojv4J-_Z-O&){yx~#+r=5L>P#do4BIf+yO9X^ma{fD{2QTo?|9=!r%ot2"
    "da@u+R<6CADK;XeUQf3c0!UdNSHI%B0^Aei~S#K(bi?5B?T-c8R8E~LR3$BP(JOh3$j^AH@F2<cczI>AQwf1-)pbKZY)rx<C"
    "ImUz&Hk;EgNHeTDHAd2Y7}WI4m#O&jE0X$!j>=vUkW7p1Yn*hjy4RRcH?rMSvLWYbjZrYHB(3{ubbs_+<V7)mz);IhooXqqt"
    "TCG5F@z+eRJ^z&$r?e0D`k-2uc!O`NTupWfu!`PGw0$wKsh%uYf3%RtWuGsX7fbDQiD{RFZ90<T84Gi{0re&;y132%l1COCk"
    "kXm{6c!p&*k60*q~X@T1M^iOeDi?(!j6stf4mBBtk;%vcEP=4I!<37f+A5v-pTG1QDOOeML7h{W|gU@nWW1^G@R041tTOy83"
    "2jKL_|Z(;n)%QNXHcVmk2g@x)H>EAxOP6u@U+hV2Z`#&=WUOm)5~r|IYNpfCxODGsNg@<^c}kMH~0V@1W=>E32F{YbW*3KJI"
    "lS-wj7-I&fFDyg;7i<Ev1E9*q8h6GYegv|M%?1XOfGvnRDQomdqC)+U9!+aTtQoDE(&L)=DMfU^Qd`$$<VA~Jpjbpg__}^Oa"
    "Oi1DiyYYr-{A1#<qs12>qqeS+?J^y5w$>QmYd)KUQVYU2Ejhp#1Bb$1`*^1(g&H1UVIf<hWr=mmLqX(7=i+aEhx7eJiZflpA"
    "2$=iFVpO_z85v2WPzlhpPx{h86|oLg#a9KSH3=3ka*|jspYw&NDc@xP&I1cgMgjj!Lr$wxbDzJ^_55A<j}T%T#&FZ)ZY|k-I"
    "}!jc}-MN|9jQU2U}CnEK}D8!7I(AT)gy7ZYi}SI*ThzrZQbS24Mx1^XxER%1VHgTQA?{Sq=iyW3!Yr46kS`egVon`FJ3NY~o"
    "5LtUUd@Cx>6;;>~Lx;#Lt`IGvN;agb>|Z!y-jVf@7n?y)E}R#i%eKUmhgYP+96osTnz!te56vP(l?6u*cf=(3vMg7K_0*t$6"
    "a;a)jc5|X&5uD+UlI7~4-e7<v^qU|JrJCR~j%*<CRezI48`sD9q`c3v&h4t3mj#Ix#%FR>hIGN@MF%buk;)i=McV+)+TIRv!"
    "CC((pBxzvc)S4hSjp^;?a#zbH>4Me8PL`OmGOQwZ7)f$J6Qm&lh49p((hrFhyS-vM##6u&E^|lqmUs*X%(E8NZFLP~K!H;16"
    "tp8GPH(`qR<j&6HFc=FVSL9>1-gbL(DrjEBW&idzCGlAF?O^&_0zi{II}iZH+a%Tx9%0Ye@KC>EJJFVSPKbF=(!P;zs1Ave*"
    "6r%N(4d0vcS-*i+OOTQ%T(U0`r~P8G5eo3sU8_aqOj=>4%?`LEPtC8DF1U3D=l@v<K|^34Qfx#tX`G0nh|32ox_rFZ)BNs9*"
    "5y`iJuX2c4%nx?yL?YT*go&7nmqjQ(aP*krBSy&m_ud7^(dLbrajY-7~!e`ZhVFU$$i#c-i+pAVplJi{3!3dFftVtg8kT$*b"
    "NP2x(Br<g|MKS~c=wkiAyi0wvN%NW5D1R6Kp3Bx1w2zsK~yO0HUR<?hf*hw`d2sgz8ZaBZS$U=$|$jlg&%{vYO`!3w=&aAFz"
    "DgZ828?Zz1y-<L-jk^tZO!$#60~yXY3&ceAGCSv+7Mm=Hq<@SNXpM26o3dMzdFR%x#ms&e@bm{MkdFn#xXLKbBM?&12jHVB)"
    "2LGE=ZWL<^)SBiq=j+wfMIbu3bG3c6#nfAb4W`dA;`s(lTn>VS+0`1sDkM7X_@J_RP6Ob>%Kf-$r9u$q>+WjrTa73xZmgLy%"
    "&4^yASW*1q2njC6Xl2iEgwS#sZz<CI7I*xp7_x4EirU3Fl1%Ij-81c3g19Ci}FDGcmOO_Ig18t-ZHIZ^ez?&u{ehNb4m^lt2"
    "A`jyJi3?rv(OMO;q`<ZGV?>&dMu^TZeSl<#{A{{V1P@PoW?g1JAY9geb=Gy+{=5;c3rK=_(uWYrm$S*yGPLE9@&{_kD+#vMT"
    "H{Z@lJ)vOd{hF&uFWS3a;Y|y(%Q$^b+tpOqrz`%Z~%loDkypkkSRP`~VHX46r)cd>HJBAnc0T9R7z8%V^J~Y>>Mg7bAu@c2y"
    "cKvr3FjX4QEfjMHePBQS`wWsOh5h1DS=%2^)9A$931acrtgf(X@Yr1ydO_{OiJ(miTW`#F{>`0m!E%hRxozLy>>xIc8|J?u2"
    "m~u0C9L^r?hDKx5dTiew#~b^Io_}7)r<T$E!H^ryytNcXrPnwsCV`Zf_%AMj=Rxpam7aQx79C-P?aj4z-BAVrMvx$?ha$h1T"
    "r7Ymw^v_wdt`!^|1v5UqgBKE-0;3xz^T5_@iqy`oZQGeB3F&@^Y>2Nr0nGdK06j&6#1_v7=SyW0xAEf->rs52;k6<p$++Qn^"
    ")a3>L7p?nIRL00NnMtCo}FwNNkkVP~sT8~Y2C3tJ7sJ^dsNt2LUZp?k}}o{jHH)bIEq(kTg&w^(Bovyc!0uTL)ysjr7>)Ax3"
    "{!Zgwk0a}++mD}SuAi%<-TNTzDt4Dta3BSFAcUCdq8Xqs@?s2>+|1fbWA8ygq%Y>c_P?5C2@W^&jGNKZwa-Rat&By&)7F@ur"
    "ZIiOBZ4Xy`d>9p%b&5z0Uv9Uzi{ye6OFWeN9q*afJf5`b<!%frAeefrhB^8~d1(@J*`z{sL$CHikK-F~CYLlNFU!_Ezc6s)="
    ";+_GaNwWgU?)C05e&->=qSf(91GM_%K1i|oc)UDk4(8sS{FM>{*cSuJ^~BVacaLSKeM0R#*Zl^HL_~zjt9neg`t_^xN0+k<c"
    "b!ab3X)1eIRl_sWjL@(z=x0chq7^fN7QVA|~_WLhY}m@W=UQQr=xFmWE&0b@4ta?S4V{@Q(H@n3V9+cUmP}SVp3Wv%zUg!4w"
    "=y7@KqZ(4jd9=i$(Vb(1^>1W!V-B@MU}2Yprs#Z&1o$-aR0E=#~^EAFiEfxj$I`}H5EwqCzeG*i|kbRT)DD)_jwNLhlDwuBd"
    "eCf4;S#yRNF!w3rZkF#PNLU=q4#Dr<Pbb@I3uS&|BtYxSgRoJUF51k~bI=ASZ)Lw+*i*pGM5=0W(avN1Bh=g}^$*M!`lkL-e"
    "L1As=G*{}%<6>@3oMy%4H~@+9YPon=?z~2xz5}s8EJxm$wEne?IQecQy(8NGv2T>7gW=Ep54uXEN@I;PzgWIl;n9EsJ{10v2"
    "bwV_{aQg?g^<Vs<cJ69#m~SNeiybR$$W3jTfKtz6&qr-omsm>yoW7T&<($%J4xw24E;PZl?Z2IS~Fqg*uQ}rzfI>}rIQF^!s"
    "&Gs032jy&L1D9oTUs><ShW-6X_|vn;@*Vd>z5EZ2ypXf?!K27Z21(dX1VtZFRpd02*`(O-b41OzgGn;Llb#8w*9O%&i@GY05"
    "u7=+UXGr<6NsT%L~nDkWvCqXoFs^~`{#ZxI5>i*~@YQopRb_1sru56D?_a^ZD1w*==ec~dV3kMO*2s7Y@A^+__H;s4D!Z6y~"
    "s?-4G9&nN=fgCqojXR<~z(JH$ta=*6S^=o7<rUVeLdqwc}XS>>NF7mtOnqIYR!Qml`$cZDeHKq?<9q1H!m@AruPyUXG?8zCI"
    "CM}`t*BjAaVlbL({Uto?D>9qMZMx^Mw>vA_ME~eBFq+#_xONdJ%gXxUbn|YD<1==D5(1^`D)q7~NoVRC5|0L$iIoLN+3e9Uc"
    "v)V<a(&RxE72u>CO%7UZbdIhP1qc|#?*)hFXN1TkYD=xE5f37&O>#{Ghr5Q#^&CAt)e8ro=5T^mU~IG3&w+eCX2wR_+>-DRw"
    "PWZC%8SG0HNQf^^R@q4(u$fn4$_282WEK&$M%Noz4AL32<CXqsEN5m;DDiNoE@7bec)>=>URnI21bj<r0E2m)6rxN1iIx4gV"
    "I3x}si~LwhKP;NJz5F|e>&VFP71sU46?JK!LQ2(M*Yea1e9h)OaPw19$A6hUSaM^pvkrERy+j0@_6eou>X>E1ySs=dn%&plw"
    "x3XozY`__85F0(w6MyF~YaY677mg%m5VVm3B2ar)u2I6i~=p&LW`b<hbMKXjoQZ&Ax9_UJ=uHWO2yQcc_mB#LYG22+Ck_7b0"
    "dWuM0Jmq%-^^*`jgU>5Rxj5l7oiJ46*~Z9MwH<W>j76TeicY8&BYrmVZw5frCPbF~@2h5$wn=70+FH!*Ucz?Zb)|$D;cpr;x"
    "d#BxUAa6-)5<KCc=bK+jDL;#xLsJg@^b?xQfvxE6=k7a_>I2>2d3#RY+(lHTr+CL<u~L04OPhI++R;EHu0gURG%+0=y+$tOI"
    "%Z1zPrUE4sKS^_qa}C6WS!sdt>nK#EPf89K0{5g8=g*L}zre7o4Gsvu&L_v8qwycA?3(3BF$|LEK`L=sO4<zMC1ebba78(1="
    "NeAB^B-tcmd~ZD~i;z%RV(Nde@z?V!ff0!B0rL*N0K1Oz6#K1fO!OBrP*<|0+|H|ZIQ8k@KhEg{R;zYW^xH{`khkQ4fahIOG"
    "eFdGbX9Sn)>e#Wv{V1>fJ@boUh7*N`(3pH@QEG+3e-i$f|KRP$~h1iWyP}2j-{?e^r&iZ9zBmtfA*nH>s`W&ll8++7Qw;HZi"
    "I9#7x0-Gn2?2pjztJYnfl&%>oAVum~6{G;6BcTN~RX#L>7<51huBzR1nX;mJ^U!2v=}RzHx*vh%Q*!4!-Jz<d($2t=*G1^W9"
    ">P{DBdSw7{P{Kdwr`SDfw{R_Ipza)KjUm%<P^+R^oqZ&T!G6ULU*gAkLqe)Z{tFHP0}->>jSv%4&M`e3W|OZk47e|T!XFfMC"
    "{GF@e%pAG>7G1@{js(P!$WwyPh8}J&zg7(7=qn`bj!TA`ZR7#Rj;By!<}VEGe8O((THR>{kH!^1Ip1{8$)juoYGGXfh}}LlH"
    "EB1RgK(xiZ8HVT+<}jDOW<-JZHy+T5N&xF_UhCf;TCbLga6h!LKNi$i-CUJB|ZVJ+DxoNL$_x!0h^SEu4=xhZm>Kma)C*AD^"
    "<sTY^AEGJfwVMr<(aRkFLAn3gq==H~Lb|zPAfACkiTL&jid-D3jDbU2H9|g$`qf+|{SdclFY-{8z+tyQLdjuoCfx@|fW^yrD"
    "&n3^Q@iK-Ch3AaBCL|FJxj`63u?bsZ23Z2|gc^)PyAK|3S<qigeJA_lEgQ;z(r9L_d8=&U2EukR*{)*fAA%B-MI@3maH>>ge"
    "gS+boM6AZr$Y}L9JM+Rdo1iYLUK{comx355Y01_zktI@x>BhrS=G<e8OlLV<}TO;xJ!jP#GiBv!fNq<fvu&yjv)8V>q>WmsA"
    "l|)N8U~RwQ)(Z@%VW+Umi#RqletjA)bIpIs^b#H3PRp!I^4<k~*aK`;yv#{%ThyOHk1BLPiYG#xne~=@su?(-Ckr`LqvWq3+"
    "CD>K|~LyroJN)P6$07|BufK$q+!pMFCl3?&Evd_@)7I2rJY?FYvIkGO#Jt`AA@{a-7$T(mA`W+8VkHu4`#Pcg#(?N2}WLjTz"
    "TKi^WmR%EcRaA42Ah>_#1nO&leq{+NSJp7qOrlxIA{cT(vh&%5^CB)RiAc@kX5nkCMvG9A3Ivju1KzRvRhzX0s%oLZf6yFlA"
    "HOZx=jXlnOy>BBvZi}}`)H(Mnlp6+i=jp`8Obvba{JZYgVP}+fEgysh57hwaVOdwVkG-y(In*ZY=&){#O4Iwqg!x}a3i2V@c"
    "tgQu9hza@M7&Qcn{>*`fmWp7o{tkehr-t5>+Q-M9EKhn=`R|5AHJY`(5j)V1~#3>%-zQU7z`6q7gBIfc%rd{){M;?eGc?g(w"
    "{S@l+)E_*DSaK4usv&iJlXYB}pVmF^Xfw-5q7i0ud488!mU=_|eUykKgI-^)$tL#GR10;uoZD4Cak6BLE1IY0y7v_($o?h!g"
    "GR{B|47-;iZVl$V1C5Zde_atvjXtCXO^Q0vNVaG&-o<0cJ!XX}>>%81jT>n*uK&UYp8|8NqjDTL9w0~op!l>Pw7%Gni0!MWp"
    "11ZI9uw4GhFwHQW+5`2*d1=8UaBXN+g1^=BpFyIQOm&s>bds<=G;x&f@*a_bBP%y4TWCT5%5oRGJ6;8zKzeVF7J5a_hGTtFk"
    "ezN^#b#!&8N3~BRxI1!@;3qzPLmKmP$VJw5e$X(AOtCM~xGwGkpXC?UcJ{-62n)RQNZ?QMDHK7y53~?axr9;QgNpiwzXq{8_"
    "@6|&gmr0q;@1z>ob<Pf+7h;c2-Db<54-64oR&im!|b@uDi+~!=tzG`Klg|61vHui1OXFV*1x`?x-umKCC_cdxC|J4E87tx0Z"
    "s0a$?rCcd<l)m&O`TerK+@~%RKL^1Ia%8WO+nk@2%jP+Acfz?zvm6x_x)nmsB$koPKf=`Wm}s+w2QV)*XfYBB67!=VF`Y?Tc"
    "1GAIi1H8~go*^^S8N)5w0`Ie;m`G)wm2C>ddFo0E{=;zW}!PN84UU39U;F0P(E$$2{KdGQ1@as^0)0JVXu=A}{20H|b6-w|j"
    "U;v0y3ViKb|m#w-(g{i*DSUpPlcfRRsIC<%tUMS;a9a|LL;`y`qD_er>!`V>evlA@<1fc%NR~u@{imRMR%Az<<p4c#p3P2q}"
    "VTQtZ$<%?L#kXlcF8SG+m{<Z^^7nDD0}RzUqe!_wTD>Q$c1m}4dj3b<S3gA2es2#Y5{h((AR#Rcl7b*DEiF>g-LZfY(v5VNq"
    ";z+u<kH>UvBbW^^ZEW0FTc;seV=okEAH84bFC%*y1q=~^<^*Cjgyo_zuVA89lUYFEUfXFwDE!o+*NM?zolt1xM5}TN&_63JL"
    "h(MH)TY<cRjG|D|-uO!=GAi<7!bPZ2_xZu1*iwmWrnAZ&YS>@~198K+*a4KXr=l3w#$(k#X8#Ge-KoA1<7`-%oU9be2zIEIe"
    "1vJN~QZ)b!%L9G%aYddB|rbHwpxpRF=U=$^5w%qrZYVEw$C#Rrm<{Rq}z|7Z0jl`*IzCI(+j8n4$~?4?eW@yZG716YBN+i%U"
    "w=6!a>S``qc;XKE`rW*`6aQbX{X#p+~v*&MU!h6~?<^y&yk<N*|5-<rl*msVR5ie`mj19G2o)P8*_NJgOK_3u9b-XDQ5;4Pz"
    "hSC19Ib5;a*e|;^J@@}K@p^H5YO%{Jzo=FJZ6_peQ=tr3^zw06a^zRqR$DK!XPnT7F*uaZL#adr0okJOhVTI=QOt3(cGblWk"
    "8PK6MT;r0oK6YNNiMDQ<M<dAy{N`T7Slk^`u?Qngdb=4cruO6`1S7lEq7YE+n-}d?5PMtf+n+hUJS-)V@{f35|1qrjA;`1Sa"
    "`Jvb->Lwbi~{AsS^G+dry@Ke{Ggq`#Qaq;<%zE<YA|SAm=XvD6L=TJczRwi3sS1m%k(Yo;2i)C}o?r>Zo#WRL9~?PrQ{Q@Kq"
    "vKoMuj5&KliQas!6NM}j^qeV`>@`>Ta={K_RuOTb_2kop6BLG8R4r%tcMsXPecFFb|)Rb_JP9e?ja*oDG-V2;H@U|od2nSUY"
    "^oiZWo`2}1I8^W>lqK})JkN%nQA5%i~=EjpNm|-1Ldapv1*k7WyC>$i;uuRoI*lxVf1e@jNJB``{r8jx0AzXoW2}J8l5?4`m"
    "1jG90n&Vay&szK6Fnly7ym-X%%sqmK!!SOVPyh#mqU`lNSMNKY-oD@TjDTv&I_77ne$BIi;c+4fS6cA1K9H0w98z(d<wKCu7"
    "B&3&`;$RQCX7<*&0CgK<#02Kr*9}<0~|8nh{aOFQ&ivbA{t(J&>}PLNgob}zRQw9Qx@%ic^awG;j+5I)Xlt--XN2vF>jpUL?"
    "gVYNK7U)U^X%T3Ym+az(7{L?E^Vb$zu37+$T{0`MYWK5%6mNU*mJt4LFz1Jz?l7O|`DAc_360R!<b)EMB`VwEB9%+{G{=)qh"
    "{v1+$R);o(yzQ^VE}cVw&s*GoRR%I#=BZ}-PK9e}0!k*+(vRC=K0-PogC&XFQE1Qt5}Fxsx-^mtrx+}+hx>El8SR9`WbJ$iv"
    "<=o}(l<Vt$_vDowHcsZ7sbGtUg22Oai+fDbPP>Or?Elg{PXHcp@i%7L+2vZcvcm@+;x~2%fuLY96Yr)6FJB^-whB=evTG~_*"
    "ZTsrA&fH`kW4)gG_p00=hNpq!5mCS63`H;N3?KPX`<R;{JZ!Ki`%Rk|i(r`P=T4`-kL2VGvK<ormlWK&Bq62(b}hMDM;Bf5U"
    "%MEbemzI~M=nlIS*VB63vsq0g73spR}vmSPwyq~TTh}w#r{`sl}(Rxkxi)kj*e5(M%B~n_f_&Ii37CkzA{eB3;fujMA0=ZIR"
    "PMa%qCu5fk!IUU=B>mqQ;tnpxLx7{h<Ljr6STqy8Cbc|NT0BfF^xc4+NtfA3Ik3R`V~y>;c`q=e5B?K<FMpIk_30D%o^U(C("
    "y{ioRtinql5=*f%x~cDccK4|l^_z%#>xDp`%Zz)0K&3jWuh%G&OQy92LZ2kQ4$-r&BI=<xY+{Jff1@&sjDQYS{JB;`$&;@OK"
    "@Y33omgxujWov(#ft%;84JA$9m-U(>QvjsmwaE<va3KvtVv5!a6+cCy|SoLKP#t+25qvd+DBQ?Tu_<iE=k^x_2*6v5R<pJ_P"
    "1quhNL`QEGoJc|S{t+^+2s@meP*S0=tVgamOgN{ln#IRp7+mR)XVN?nIOU@1h4!?VJe`~V_x~#mO3{0eH;7VTw6_}8ycN3dP"
    "p%H67lO!YidxR!@<n~hc#FV(c|V8zizaezCt?D2nXmG`i4;MMQ%K=r`Z!EUSv-T|W#0v@VSsl!-q>5A#OXt4$JfcNXbSbzzL"
    "$%vpCvV4<_;*`y2`B4&3Dq}s9t<IF3B-yj(735V=(KCr&@QR#>u>^{B;OWXp@qDw~5yE-#=9*>mHH#CI3#KEbKQO@x#VKmPK"
    "fa^#&gM?-x^usi#~pm+?A9YHc!$XAX;FP7<wBt+G&c6km?V^bAKhOvtuq6u3!qu3*la`|;FemEy2KCXfXxyDntD(%U2PuB5I"
    "t))8nP{F2yaSd;7d@k^8h=?(FeA_)^6kCmLN3eVT9sJvR&3U&V3w?01s`9{(6X78Cjhv1|%pC2}vKY7)8Xlz?trUYy46B{@0"
    "FbGd=-erV`@f^r4y3DX&5TqZmZO``D<hgCv3itF&^rnShP86)-*O3$UKAMF|z)_8PAV^DbLjLJJz_Tdja2Cdx%)>D&-V(|8E"
    "viPb6Q-(52A>4}$-N&@N7dR_Vh^t}O8Yo&W-5RX+R^*AZs6~kn4JjSKrgV({Pw=g_hInq=R~<Z&q2Pg|C0(d`w0EixwdZNec"
    "-eH$m{$%J2b}f!%4)W1vgJ<<~MqY-calh0jR_RJ+I#BB8GPQw1~Hg9rv#C!Xj0SV#l*~Yt7uOjhM+llIyqeJyuM<*ww9<(L#"
    "RN|KW<_KH*-eiQOE7h(3<(4boTEmp=8L!i%004_gO^2>qXO2^_JqelD|MWo!x8ONJj)+zu>}cneJZc<3`AtO#>RAJLxsFtC("
    "yz9`2V?&Iv2D2X!`i(X|i{nIK7zU8p~-63n4E`I>UmCsKgO^iIfL>DRFnXIjwyTaz_1bEX&_CL&O^#!pauI3acu&x{yifv#t"
    "p3?1`E%>n>gmNG{R_T$FUo0{Fp3v7VTDHtVMziuU3Tb<jxA>Krm8dmz)$n7wQu>WSjx7^MpK(q0mi*e@SJl{5nzQ%y=%v*T<"
    "}#3tfUyrg=f({-a;7ICn!@@!$Gyu?TA)UN@MUHIFZ9T7U+8D`hXxDWBYEA=#9SNysI!xm?|=0D^8Xp7;Fqiyd-`F%XyPil@>"
    "rf}IEO03uIlv|4m-ioq$ZDKRZM9LBO+PgkL}N$hLaz&n^1gR2qLlmu8x8|w0%1L!kmy3fP~29m$s+RC>l^!%=m^X@9<vE2}P"
    "*`h1D^3(dPXx*(F=C(YSuQefNH_F>Kn|bpEIW$>z?;&UN?x^8$j5e@_{ElK71>2eQNX&LqGnp$-)yWc#HW<&D&*N<`73e`!0"
    "Sras+{FTd;QJEV-Zwd=2-3v12>C7n-_@YiT>+F%CU@L#M-Iu<&|$3EJOSWIk1l#&XVPohUYT9E-<Y-3u~;=jo=$iKoo@<M$|"
    "n^|Y}U=t%ef6k#%aBNqZSvX*RBXKA&`H=17VjXs%7+^q@hx>oK`>DZCC72S^n!4!sVcE$w0#0NtnZWphL1NA1A}iK$VlE;SH"
    ")h-tXL6Y9y!_n=;yOT;-OUFiO{6$UOoW7z7y?mLD^`7(pJ#rJchREB>7WD*7Zmi1pS@O94dy?TvXA{I{5PTdCVkL;>->Gm?d"
    "#!FYYsiO&Q6Ddb;V$4$0gQR?x+e_4y8iP?24FK?$xS7ifRYMXdzjd80T7c`gr12Zo5Hg?B4@R6_3xZpIG|uVq)C>{LMsyWJ#"
    "_Vk`H@lh-`aF8D%j{C$^tI-do(HR3celB2%@x;p<R>R%^)fzwiEHP6WI|FvZ+tO4!hDEbA=d?6rGuKNC`ngZ4%WAg0t+>f)S"
    "Y|KfNN6N+PnoXCoxVud|1$vTV9;*9>iGcdzA>Te^$TVrH+o)bVxn4FEcSJZ*#Ga6^pi-BRP8qmc)KHxf8yfvII{azGWsG=<("
    "qXDPSNA4{%a3UY|!|cd7bo`3z-Fp4}DqBMrtEceeHlr2pLvnbWS(%v@LJ}si!$@{veYW+3)bB~}37(kgEDHWX$0~hO?3BPj2"
    "V1pCc=n~XQi%|1pOnU!u+h`8H0gh8X^=<XL~ZnOU{v)?)Px4zU&uAt^VQv$|Gt_;QfN96hkM^mCd|}aL=syTcNMCO@-5dsbx"
    "AHDO2Ib|W~O^bDWz!UM$O^V5ZPf3TvJ8pGs&&U=IU_}mHB1!zGghKyG?EDR)1fT!lspD$1?8*b5#+69cP6qs_`K5g-w0b?5p"
    "X4o8%m7pKu8JFAm^mhj|*N#AKGrdo#vmPQvT1(uE@izxw6zK(wH*M<T^&4%5jDVU3cXPS8CC!_i;1b?e8M1#ashp5!osdgAL"
    "B%TTr%6ZoVP$oK#4Z)=R33X7>3W%q*BQ}FsHBSyxwDIN-KwS(?{ahMA3FqajAwsvZioy`Rz!;7R8AWz(fC)AO^H#~W7*XTYa"
    "JhVqc{z5!pxz#+)P;<Zgtny*|M0}@PGAC)Sk7ab-voNW%wv?2-SM=?qNGONi;Zg6GTWo;FV&#i<<nE;W&FABH_itchOisjdw"
    "dEw+e@RmZ9X&%!QHYO>jk^NF3R>(O6R)=x6l+dt=%s~Vvc|j#t3^TZ%<^zW^{aNQ5kv#KuqwI#I)?P$2dX-UvModz#LJL---"
    "j$0UQta|<CYx?6eyn;YCKR`=DrXm26EgLPL(*U88-RlB>2O8v$fNA<$!G4(y3vm9v|sMo)4y7COK2bm)ABwwBNHaRS#<TpRN"
    "z6xbmIYMx+LoToH}^K`M`xgZg^E8~nE~`|Qw+&lMA2E*7f<dp&)povAUsR~Sz<F&OVuR0et>YeYiJPU4`jO%n*nD+a@8o!$-"
    "U!-{{3^5fCHT6sf8CW=pqp&ul3i=4xl;7TI;-U~6{>Hp>b_g(W&_Vc!!mk9{LQqz)~^ycDyj)!eFE<zEck!qR<s`&~p0S<S2"
    "CA`V1YfhGfj)2T%GMey8WXHW$x%=c$R+*xuU`)L*`jf;1g^aDfqV`uf4D07H&=o0EdbOVJuQV86tF2%cR!Bb>R=x0q)5Kn+m"
    "o4~wCa$pfAqQ30NfszXev1}!`K{)2?c+o)^UvL9qT4OryXP~p?Qfh|zb{pcOa6mBH$1UJe;MA^j#_lxQ9_A&!tN7Nbm+tRbg"
    "KK@JLqW-AwT!BDl^V}<jj%I78_6hOp43U`zTMn{idjiU{sv+JzrhUCR{%m6Nn)xfpg<?<VdcpyG@>8F{~*TEk<6h??1YM88="
    "|3^Xrj`XWkw0Ld1v8S5}l}>EXG9BpHShJxm6wC&`d`JjjlKv%pmj41)O5o4W30?jB8nhednFVce^Sn>YkQkuVC{0BMC%%WP8"
    "drm4K*?v!3<SvF*v6DeY(STwOLU&&Wv2gxzEr|;nYCl465iy_bNr8nt<$Zav792NV2A0Z0Rd}9>*S+b2m2hQcU_VL!I8DV$G"
    "`Cjq}O^2;wCahTb^w_rqGs`lTT=ZFHA%y4hvFC*MS#0~HB+UR~#+8Lj7DnR2rEN+UUi6<_Xqj)$`jD~eqPS~8qhInrfA60%c"
    "%P4nnGC+uU+a(G>&!*_Iwz98J3St^qeX2;_M{ECW?(Fsjwm5tr+nBsYQ<*jey#I^`B|j-b5)Wsbeb(wdk#6-R;n>1ak>;b{F"
    "@hcZP>1S&!no)?qcS23yQwOT>v+y*xIMIr2e2}exh&=lV^?y--vFPyj&X}>h{P)i4lxM@kzMHv~J{}kEFg_sYl0!3W$H*EVe"
    "R9%!1RD>DolT;@G6lpkY(w1n)ZC=~R9!!+eu?Wrla4eR6!Ku*&1e)GMQr{oC(Kji@?ORy`9}w%MYJ(>EMD%KCRp$;)Rf;Zo^"
    "(e)-C9NU1$(@JKE6lYmDna?MKfj~G{ecePuz+{XzwqQ)Y*x3Zp((J_N$2r`$@Lzc^XRj8uzE7O%fu*c4mliM?=$R!j}1;h@N"
    "4VX~ElWU6m!TIExes2zAM$#0>=|w?&N_O_<!j|`8X~9`X66#YGDkR*y$p1oyz69gNWGapzr0SK(7n_`l7WDBBUn4rMU-}!~O"
    "vv!QDqgPf@qL3WnWaDNC+muAY#BUsboguJ%*byp%(W_Qd}v$%dB?Sz4z9Ys%!g8tmrBN?FNOVa+YL}FM)^4vvb02c@`0@DmG"
    "X;sA~?B|)%SEiXw^^Y{}>d|MXxGGdCQ!#6{<o?w%~YwZr*qUx#Pq?m)w9+fQVBs<>tEHit-6_Kg(SbLCo!beZ&32U^7YqE3*"
    "|s>D_<#tcEJA<Wtd*kGC3~C^>S0Dis0RWPsW^O$g>Y5M~8uP^FF{b0k{}MIHQ6ZeNxPrfN#83yRKGiFC%l{{l=o_Lj|e_IDh"
    "bespm-p#>GKhWQ>)bs0>?O{}RIYQI|fY<W-`EQdd5)6*WEqpx*E;n`$^C*qHgYb?fw+t0h^CE3_vgzT!^K`79iPDW{TlJ5IM"
    "#rAZ2dT_-p;q%)xzt~&`X!j<}`^gQ_{GS_o?I=@;DYYU%Z+APcc?<ARCC~e4I0^-lcXZVBVY8F%qI}MYqaISVk*8yQ$c5}*S"
    "m?UQYa-u8e$2E*>baN2S*ln2_Jx%ahwx`$)4krxN_XL_>~W1;zz*G;1AqBK@88(>RJFgcjeYm(l^(C-;WSQnqPdN&xo00f?H"
    "f?(u=KRH^C=`ryI6IxIqJ5h7J3_bW)7%3dO_}AxR?3AatapV&y}H8g^YG~qq$2H>N{FXEeZwxgU^wed;IsJf_LUWjbUaYzL2"
    "Svcbrn5TGv>aEL&l^#QSO*DRW63GasZeqqxp$q!#?%2`3}oMQHE67N^e;oVr8uO}sGt)5)u)1t-E_ifWXmilZ0BfW`@LoR_Q"
    "gG5$iJpNt|@(oFfpX0x2S^Y^3j9z2`Dup=`blCLrQH&KtTqSlmDZ_i_fEKeyy>td|lR6zZoKHE4S)ei_60&810m?WN~>c2ex"
    "sq!9cxf!wV_~Y1PF0R3oIR3t^7@+8Q8umHA@%)4@Zu%FWW{^bLe_CEsG;!Vq1)m&?O8!D6DFHYhrIDzDFyG;*-AT!<H5=*z;"
    "kx*vyn}PB=hH$r`pu|zoDH!wZ>$AP{~d?v=oU*y(6S=169cCg)SgZ$pDy9~As(Nx(j>|yV-G*N=QA4}cfp4Q%Q%$nl?c#NEm"
    "Yx(AAA_+$}l06+gSwOl*P-awcc80`jHEi8#hTadLUf3_I&;~!yn5rt*(uv+w$jjCT#zhZg}h=eaf$0BXkHXhgQVVe5Dy@++1"
    "WRQPFz8`|RN3OQB|HmMTd?WD(1-=Pp`jWfmU6hRbL5JL6Zo5@*fd4et$q%_HoQ+-wc~n86l(nS@lZn%+Te{`eN)E`IUM*u{i"
    "xDb<avb4O*H<m0W`=roNfu9;#=KuD$SDe<*1-{tx9A4;O$On-Lszr$fxvi(nZkpCYZiuE?|eOJ(%Y$YD!Y7uILeufH#LQF*h"
    "niFHq`z4)bH=h54prGq|G2r*VY7r>!CZe!C?(|9&-w7-sd)>e*Dp!f$P{s51V^=>zo>#i1(5G;O;Lw<pWz!H3Y(Mw;gy{e=%"
    "iO5Ji^2jCv|A-7IKJz^Nxpr+`N_%K<L;AAS=&@4*LE5o!B(D{FoWN4h{rVo#m8zM+xyg?qErPM_m-b9p0fsxf0PJD=?)J@5A"
    "yi}DE-wb)jfEDjkha<YjzdRFzk-~s$5hw_K%(_yJ-By&~;M`CbI?3oSd`C6?}b`-tzr>hpnMRe)1p-RR92*M&)?V&L?O^AeD"
    "(U(j4lHnivQqZ>40rH^g&4d^6sS;T=tS!@l`h<z>I%2WLyH_acJrKdNLO;zRMb))+OX1%avVNQfrNDWnu}<=LTErtAX#RaZH"
    "ru>7Qq6E2cA@yVHh8LyM^)1CN-58<l(6-}0pOp3xW<Ty2S@0cSs97trGw@jk$TR$3=c6I9D0zO|?J5YcV-gW)F-}sJ4z&o6Q"
    "ki>M&s-F8TzJ?xh1NFj5Jv|vcR{5Oh>S(|4OSTm3uP%R^PBK3_d9Zqzn!usz_7C`}>0;tj=)UQ+vci#$ZeK0j-bPkS*8hYgx"
    "}o?piQRno@W<@Uz3h-5VicmhigUx<TDlhiP@xNf6?rrvz-JsD{zgFdEm$=&#~v-ZNW6T#hrrNd8r?z3{)@RZiUnGC2cu618t"
    "ygO`LW~sCIhE9Xg`rd2wmSiqg%z7j<c@tNW4CreU%o*`y#)RZ%G1#AFan?pKVH@+Z#5k0RR~uBlx8DOx))K;e1T@gaf=hgF!"
    "=d;}vV}7Oa3Sc1D3o&JJ$WrVTw4f}91BPe2+CO7vS40k7<P=uounk$EcGvOWr2w`MmO(s*lpj|c#{GY;`o0I(u!@~Cd;vGq)"
    "o`TZtae<k{c0P)vVbRbIhVt4Km<z?)5n%4Bs7o(Am{V}u^Dtfbe;u1BK8#dr_=#>xvK=f<QV2t*@*8Z4HjAwrWqD2X8apIWx"
    "rQSUa6F&N`k(<REZHf^~*4bN9bnP(&z{k|q;2A*0&X_EXCN=Q7e|R%{gEIHeoBqscE}wv$FO>**yqHw5>b`g{LpCNfJO#!AH"
    "B7f}10?;?oac)1!}BJb;=%wxA%O+10FkD%kL5;%qY~N&q3t9=FBd-xF+pO-s?g1-J0=WBW<jaYv@iJucQz@>I>7>br2boRh7"
    "nQXt@cJ#YRSfR*4QKd<CvfR+<|lVB@RR3Sw=acXdrQMtlTXJy^6CDeDj|-_@Mm%E?hB^k(?&cWPM-K;pRQ&`p|)f5VC({L%>"
    "-oQZY^i`}-c#>neYvpBim2XK0VQqB8Uf8vqX2o?7>uNSuRKil;B~An&YbV_+mp6OKW+Kk=c_tXcW9<tjuGws$moBu!6@DeGG"
    "t&+Nw2=xda0Q9OVOc1V8nTQm6hHqAUEB5LAj3Oy^<qH+~;X}7m*Xv*z>uGtt&9v^o);79yO2l&X2)a^T~2=lc1)3V{rQRO*-"
    "8o_<ba;%tuPv9650QmR}#FU(!j1WwJ26VI7&ers2NHeMm5ipj=MrjY;F=w23%zhhC?@vIf5KkK{wqX%_4i0@7`ct(n@{Nohs"
    "NiwsmQjLevU-!_-p<@U!^|d8B6lhtBN!*O8~w-8G!fgW)bpGgUt+N0#}vSZBT1lu7yHH;Z1gj(*I$@ds5;B!;e862!lh~ur7"
    "X0~YW2(VgRIWLg+!7wSBY*p^qoJ!!jC03T+rbFa0B3jS0n3Kw+q}#c1#<2@qffcBpAK#eeuEI8lt`G=rad{hY`nbJ19o!oMU"
    "O!k^=x=;D5^<i4_SWteKAVkA4mLv{b5w@Mt#r3%J(d`TR!qtRxee^o`UO;X&-7!67VNVP6CQgvFj#YDc9pJ;=FbRw2VtLU7-"
    "q@aP|`y=LQr;@eCux*83!pw*6-`J&ff@R}c`HDPQTtSSBHCv@n{SX$1f(S^KWPNp5z>KLWiPj8iyg&#e8=zELkbmT)G&9*F?"
    "hdIFivErOJxX)P&jsTosKY=3%H}ST$KO`~CILruN{@HgeF9c^oco>8k@yiWlB1!afBOF4XSYfq|{!X6m5eaCsDFCmcvNn?CG"
    "Y#W@z4G#Hq)rj4=*1^^Uk$v&r7BvK9_wDS!gyf>7R~1PfC{ul{O<xw-m^2_!I0hFLCO9o5n4t2E@qQ=qMY9jTFsmupaw{TM)"
    "^N0y$RmlB$qyw{?$|IyW$Qdo!bT6*ldz5BQ1*%srnfY;OFsF;^@Vhhywa;%+d+;wG_0}@4r<{fnZ(vZ&DWeBTrY?jSCN|&~N"
    "<79}ay1|B^=mF3}<s$AeaddtR=_#GrdR>MC$ED;iI-^2%jA%=YowtzJdRuLnm~pAXKp5OJKYaz+I2c;;Ij=TGi8gwpJ1-<lS"
    "|XMFu%z2{iVOePcJqG{nVI@lIsq8<mW93}jS1TtSF5BS8+j6(2!|MvjX{~nMq9+t{)v3cH<dX{aZh5Imz56qpl%AXlm8})N;"
    "y^S_~9GZcEsPTEi&YEhPWn4e8nsMUK5<Q?^oy`Z)V!Ty8+He^A#1zKS-#>2@WW;{{gc+&-Fw;!k#>T;X{YE;5*+LjNyn^R%3"
    "?R<F9yNl->6}CUE`0)*9cizCf(!uny|Iq#W#mjl$3+{m_-{>};G+a86n)ljc30V)x&f_61mOAe|6t*e_jB`?)r;H(1Cc>HWj"
    "%s^g;^3kR%&gAdnDi$mCg(T5abazj9f@P6(J<X_(m;inHNs|zGA|0P2>m{c=~&uwSg{`OdaRM5Bz`sXEzXZ`K&9(eCkgk8XD"
    "TSq&&-ox~RJAOaZ68-|qMJ_Vz{-dGci9fM}ulWP!on@(WTP+hGvDWP~(?+!oVAf}61_Im)>*_I<AdKiS(?yrH9$5fk$@GB%c"
    "WcCI;CsGoop6EM1v<8_u(Fur};5A!xL$-7^MKcxTcG`QU>Dl@t|m?dj`_*Z47QYrT1nf=9>)Um*`&4IX>`}=!cyVA0Gd@h)~"
    "p59XF=&nZ~rFWeZnS+DFW?AcFwA21{|3Dm*@#$K38Xp0Diml%)c$Y$*`ieL`uEm{}nL9)HvVuO0@8X|$N$Y#(gUHZO%-c(-{"
    "^t3p$aU8vA3lAFR&_K@IA4c=^%Z~aU2(6*x_E@$#_4pRm#}170_ul}7-6o59r20ihosc40|%kArds&k_QBy8^x$}QzM1z*IK"
    "jx~&eW!;Ct^zz_D}Hp{&Y!nTAH;G7gk8GpL~&e$xw`ffV8r*a&gn5g1B?aT(1;-Z$HY6`K)Py@anXt)l}qShT*-{%x<TG$QU"
    "%PuXPO07Eazm?tEb*5nyAZvT-b#*SfY;+sXEp+}yjU)v$Lp9rE}#nb#(st>vbJceexrf84U`B{zM5492re*Jry~ZE({IDE{;"
    "OKnaIITXVj32TwP5EYv$}4zjgg411%hMNkM0%~e}yLp6lbk|_61C#y<(OFeJTlruk|><eVWHDJ&Y(hE53_Ieqj?+x3f56_Qa"
    "y5u?*IqRd@EXWS8C`C%5yU5%w^=isKALxU=oNV`WfqZwbfheAT9S-C=oP&BbV?Ev-w@UX4tFca#zA{SCvHzvxwi!2#vcP&jP"
    "haXKt};Fx@lf9vD#1x$<z~IqRBt(7Gpti*`<gJqtLdx0`);oN+An&o#HyYWy^O<-H1g#rf2QVl(7={5Li@W8D@wxQ=g?AJrn"
    "089V0GYAajM5r{nloJJ}Zk>RXKX2Gi{)CrEVLGwf?08EKQwg#}op8aB;g{bdhi7*Q~KjJf6@PO%vK|Iv<HK4CgnA_z>;oc{w"
    "w;OVw~f>4qTq8Acj~&q|B`FAD=61&?6n`{;fAm5H7jBEoU7RwHtzGj{)JB4i2p?ylMD-F$yG$hM^@^6-X9y*Lt_iyPs^gW=o"
    "+J#+J=Qv4?8$I>i}n<Vdp4iCFs3w@i7ER4r13+J1$-9Z9PX-6u2Aj(bhqH`(0Yw@w~A?WcTTCeu}od@M*z<DnvWb%AEh1Vu+"
    "dtx?5QP|9Rcf6aiZ+^G4^rjZ$cC5F(l)dWwZ6hKTH@DjLvQD*m-1hbR0&skduJ)md;UbT&`*Q{wq2}J-(<7qdnyxO@j(HC(!"
    "duGH%e1QhV3P5%PdEO2_}u7hRjFR0HC|_DIQA?TSAnlxptd?|e8huWcV^q#$eTD3LiruVXC4K<bHd#kyo6e^Gk)J^{e0qXWv"
    "WQSqU8<jON%G}ZH(e)gq3L6<$iK6g-3B*zr~hKEzkaNsL4y1U<JN1K6H<0c04;B8kz?V?|6weuV$TXrgkzVQ5Xp~$9t!}H{="
    "42<<{ee!Gyy(m(-S&sA>ygC0=5+5vh6y++@QS)m!?VCx}+R1kZ;!b4`Ym8plIS{y9ekM6(J<@&0Z|pZcR#Y0br*(*6TAxk#h"
    "z%E_d(1b(>>T~><>vQ&bek6ULl7v?(ZYt70UF0T+mVZ^hDBoFgf@a%KHPj|{UbI?P!!p{Zsl(R50uW&B2@vc9ys&hCei!RG%"
    "SU4)$Os%jzCjI=>@yS9JDW=6@8P4|+L8ZmNgoVdYPQ0Y`Y5fgC1Y2eAmVATd(z|oJcMgAf>uJHlJcSyZhF;2^n+=y;3QpBcP"
    "xBo9x&)bMu*vPbYjAI>$h5|Cc6>mV8&bVK!OF*YcSERwfJ2-xS0u~ySe>h6Q-PgKpx+$vPtV!i@?x$`Xy+nLZuW&>)NQWrtE"
    "w_2ScA7BDK%Hhvlk@4K?pv#6eh;YPq7c4t+CQJTW)Di@jUCFb}P8XazCs*9zF~pFxCKeEuyyV9sT!wHzuNPJKDF-qi(GnXU3"
    "rL9S^{3vP2vD2N?>tS#HrCA0Mw08%hy@v@~5#Yv))*WFxlGGHH}@fekQDgFN0&|H>xzHrkhy=A9g4p@pR_-F)xKA|z^#`nNr"
    "oCFHcH>W*+A&W6c?Y@TAasvGe`7q_hJ<Ff5s#7;=P5S}O{3~~s&ez;!N?tIrIs(nzMYz8t^@c`Q4co{Ff`?}6tcTed;xpqUX"
    ")jXZrAJr&}()u3s<K6sp9zy0XEAyfE5h9P}Yi%u&yPb~^N5YLYbR~~{gz{R9axd}E<HHXvc>iSoTrMXdZnRVp;c2i}&o;*%O"
    "f%on^$Ob@5ZD-NDAbru^!&-tsrnvOC}iY)yGiJE!}9`P%EtKs(I+)s!g(`%NJEAZc^+Rm_ibUW7le^m=5AzZT*?tEZpSu67J"
    "jGIuBJR1&^Nk!sbEuem~8f*@(RhLksJQ2*tQA-rTax-5E**L#r^n)fIPN43dFyeohdIx?rkSVkgApGI3TLdBw<5rhj*CrgU%"
    "70caNP%{Kz&98_}{ul_LU!=AspWr!%*WONw*&vF<H%LLwJrwc2o+QPaDmukdQ7z^jka_$8?GqS)km7t4Kmm{HBM2lsQ<L=)F"
    "lf%e&wVa1ZZA#5#Qtm{^vIduF)oA$ET($dN(g^R65Fcm5`pZ1VS-d!CI7nL@cYe?FpOGNpXMO*t&Q(j5uaWOZ~9xXLDhR^aO"
    "hL*a5<jP)sSG$xmU*Z_WyEx{*wo_UeWmg6{O!9oVo40B0A4=q`=I+5IPBtlLYrU_~%$9snf6{?ba#*Epa-Hw5=z%oTtXx&ox"
    "I=9UN=ts)%;-a|zhcSczhv%4>b92GwT-3(E_N)X`%6pct7E%wD;gnoy!TfwGB~<@!K|utX0tEnM`WqDE6PPk7w-)9wO>+0*k"
    "C5K4fr!H2;<vxA4-L!lejJN#HEeEt!}08J9s7r1Xq3^qqbnq85#Vxjp004nkM3odC(zdM8Z%as-tBf0CR}qjlQ~bUZpv!4Yn"
    "`{XEh?wcwW0)S;kL`KS{$hO<l`!_H1e?V5dAwgwm^YmuJqOzR|CHsm7~+{+s;yNS}lF#1F3*!AmyU7amu)mJl0##*3A-z7B1"
    "p&4%D1%ES9vZ{75H|L#6LgF7uiV%B`NBDe4ws&xXTkeVy_w#+6$&_HucPgB+!CG#gIY^X@KK_qC%A!M*JBpJ7_<?2}RxOK;q"
    "K_DW0skCoj+^9@OejS#i9{-&Ujoi5?%!t!uh~24x*%-eouEuI!V1lqR_V2QFz_IC%XD{qotb4-AEvCVdcCcIiYbe!QYc^AEk"
    "TyT+<#bpLg*ngv*s7Vg=5$h)MDxiw2-LqkTAV*WJ?^;_BgIR3iF<c6rJ>KAN|E*H-eb@Q0f~=}^=1_En0-$Fsy2wNcG<hp;+"
    "LMb7dV8j3V#?t^$VR3PI!M**Lk7s*`OIixo_2G&1pKq<>Z97hK!nRI+~WID6R@1kH)@LDFB|AHy$+%p5F$izaSTgz4_=l*6*"
    "``2@hr}UCCkm@uA$RFY<LBl)l(bU<h=nZtm%_A7o2-Q{DFpTjUgtr#heK?t==XqYhMAKu6B+$c?}|t1#ekfG){xq=e&SErbn"
    "cG>EN%pgft7R@bSm<m4gG?R+aQy;J0iwPWR(1s1?<GDNg&?Gfp;^RFG+yO|ZjdUknrr`dD`WFS)2=(%m;y93CfFFQ}%vlagB"
    "psO_eku0vIS$daiNvv7^)z`wn<#=iF-)ybYC;D~=+2s~5Ck|Z2(XJ}%MS<Sh(a}o9edel@G)3XtuDTUJ3{MZ-3|WfTJZny8R"
    "X=pEFxo_p36Go36%>~zP=?!lkzS-4VF!^ybzM@6G;A8)hdAy{{(Aq0@W$!6kHCI$rDx;e>B_}~BJaaOH1@t#kd%hLmy^yFVC"
    "$i55F7p)Xzyqivvk@W_rGTjxSucH7C+w_j_Hq~Z;W5@xZI;XW#;CdYC0QW(#2@CfR@@NYu>uu66ktcFVxxDc^otyO>5iWw<d"
    "9#Dirg+X1z7w7u4EEu)zQ&z?;hp=9q2J8L*K2T381p$x^y2S3UJS?ON;7!@D4Cnl&ChwZpk;uV%P6r45Cn%aU6@TSP>-q32Q"
    "kwrBmJ_m;Db0DawG0mWn<E5X)fv8@X-fIi)mqnA_iJ~FWDM}C@n@Vd{<=|+rVL;Om**VSyDVB*4#HSzAaEL+&1>kAnapLC4G"
    ")3qVa(TmMf{_PY8&-z90tw3p@5O|&@9Yd#t@CrCx_`LNIq^T9xE<hak_O&OJxYYmQ7y_T?yE~{{KQh`I&kZRWjDONHNBr~p*"
    "Wv-}cx{~x&WDWN2QT?Nt}NH*EXpnyok0L7AO_7)FQSNt5U_k}Mq|kS)rc_awv!pC(`XP{`>SxFbokO@Fek?EACjnAnV!(AJ8"
    "acvkL#<$Q(^(f0-M@J8v&Q2gWI}1RMC@A^7ru+0K#vkf!+1zHmv$#<6}rvlAwZa?%|N0a*=x1S}*Eg+<~T<cY7pNb{`@NCb6"
    ";ab5(`ATSh5-wogd~q&3*t3??y$#8JzgwZ3)ZvgJ|}|8%ksUu;4G;l6yE*dO(hqy^XYu!RXXxd+&#VKbWOZ2k3;hi;=L8K;S"
    "y&O%UwP(3M2Px~Ii*NM`t>jekJjH|Z{tW75$mMI8Jn(7{|=7&K*P1WA57?YF<1djZoPusb@$pv@N1hV)Aa8jRa(=vPRCMD<&"
    "Mm2s`<6<36IF<7q*fgDxaA7YPk%q2Q9KT@?CQYAiJ!|6u2XsxTktTvtM7aEvaMb%|6?Gkqapfik(*(Zg_>5l$ooU~^`LZr}X"
    "|n;3du+|f_zLAP8XNS)uRTcc9?`2{hS^+PXTcdCtnTWY$s1n4lA2$@{z0=SulBqBwa0CwYz$>&f>n#ZD1n=2q)&B>zBrtRUY"
    "=*lC-a<v<qV-L(QjQM0vqz3EoN&tIXR9|4JIW}KHFPbwf-%?)=T%1754C;$;u}1B9_3}E`1Ej6-Gx#rv<rmQ&t`qxq8RZytT"
    "1$pY5+k=?t4bR~FGI)#2YiE>Oxg>J2A9TaOTlX3HLWhw1}Q1qDr@EM~toyQtH0rd$kUViO^*vXGH;?lR^uuZM^x1q<PVUG_8"
    "YoE%!I!+nS})NNRU=G@B5TI8bIFhWS3sk)@TyUQ3$@Wdyx(=CBbUtuZy#&*A?wn2TL+ps586k1Tf2-63_Alj=hcn!4q@;_Wm"
    "ln{KWU5{|U@|ME#Ss~^ydM*Tb7BdGV><Tqgx-%S>g|IgCr3g6vDZ1;n9}a5to2s*0*LhzELY|~9w2#MbO#*r~Jh~XUDC&zD_"
    "0%$r(Fo2Fz8~jUEn7X~RaSFVt4%?#b+P;UPpVLpVpcO9!3Ef}v;@8&HG$dTCqHa%3Gx!^d)lq6V=+ufP<C-Ef>g6PCk(p!fs"
    "1_!BkN2=U~I0|=6H^u<7*o*B6355543aIZ+v0|Jcmm9|DwJmBhr8tf$*uTXysjWRMF`+EdGn`gW7a=)Yt=Zi;nD#X}VVp@^I"
    "HLTwPN7ob?DN<}&S7Br$f#qvyIG2CFUYvN;$cN!t<I5GuC~d_}-0FnG$I?zTnjaI(^F=hVsvviy3ywzb{;oPM*rQ~nR+rZTJ"
    "fn$l^{YLKYexh<f29wioc9a>A>*{FcbQ##QYky2mrNe3s@HAPSN*K5Go0=!qaevxB`#xL<|^C^2z1)s5Osbp^R$)LfTP?SHM"
    "LTi<y!kmu7ZnYgY^ED;Nn|bD-4Jn<fQAp(IF3Io}O#&OS+EbBTZ2@%__yq8Mr5&z$3E?{^?<9M1+>T1g)e6pFo%us;iFWPCZ"
    "+?foY=gZ&Y#!Rg2qT$@R0{DZpp~b8k=m~9dGx2K)Sl%4oTeF_3L|M9ldZP)o166r@(5AgG;E;B4;_Fo>9;gxuX>$!6XJ|6dE"
    "Z${9Vdinvl1R<BDRSWu<CqY@H`(b#UE#@TR}YK)YZ8A+e_iV;_{ovDoI-m$+yP&P^-67PFmVdP!16Fw6Ab-JKN~r%9Brivt-"
    "tpsA8bhu3l3BoDh{Lfj%pbDGmS`C1Q2k_@{v5&WhFy?~-eFVtl;h6pbz5d@%F6GZ4##%SKv8X6*}bf~iISFx)Rq2Dv-r)dU-"
    "|u*_MiRV|a!#joxR-t)KdU_3D{ot!Ppy<W5XFUs8$6!M-G$r*vDevqIxCI9(~<%NzHYgYEyHgLaTV~h9{XoHW3*X548Vpq(#"
    "vV8X&ET8~Ee7doz>3afoZ|@dE1A}Am#u*X9us&P&X3cpgsIIBw;oOu<Gq6C`lF`fxvQuDPSwG54Nj@?<L<ArWj6u9d=VbB8$"
    "xI3_5xx?M&Vq%@&QnO;)0!cF?;PuXxp$j~lc83mp7&DUmgc~0A}<kxfZ3MjJJnGD0^hIccYqJ!SZDq#eBkjTijUM&BYJ2e1l"
    "MF<H-kQ?r+zz)$=ePzVGRUVjmIraB9AvT)g2z~uYlOg-(KTnKwHR8sa{a9J3I@qt<z*Q?NDn5EFv!nkLAv-9sn+Z%ckj6QUi"
    "SltQ32`e6r*!gz_^{=MtIM#aNn^CIGa(9a35!84q5th$m+R1eY+{`e}KxK=3Iv6@#lc0h5*v2Ba$pyVU<hSIp$3>iKWOa67J"
    "{&`?aNP9&fWO%=e)YCF<b1zZ=l(;-J%Gc=N+>`7c^YqNTQme}fa4vW^`3fI$bTJUS^L_ryqTp9fO&3J80w$Zl$;Dh@csm)Ce"
    "@yioR>J&vDChMNmh$%<kaqQ#TN3D17j0f<b=sPwow|OAo?C3#ra>~xh$w`id3;6u#w!HMm!Nnz)m+P{aeX9}B>W_3W^8UDvz"
    "$HTPENHA?OnU2VbJ^n$_kAemT>p5ktS(xkeyjHu$jyS)t$GQOqUyfm8U$_+mr(MstcwfBWeGRX5X+@v_8+}f`TOmo#Y-eFdF"
    "|kfJjvxsN*R47H^kfyC{1f+uQ*Qkr+@CNix$ID0pz!&W7PVbp<P00^Yg@u1ID#OJDp4E9mj`{4?DKh@UrExK!p^1V)fgz{zh"
    "+3CMH>Ln3>wwGh@15bc+1m_nociLv2QCsJZr=GU5LCZZD8N=YZC$^b(Qi-M6~@0E8+q`%fL3f%KJs1;sLl3a9aj|7~#G#etf"
    "w!}iOd{SxZ}FH_jvFTPYdY%?L@MmX(HJ9+BQRhi-bzB#2y{Ri)s1OWQy(h_2-d^7zgB)rx`rx%5!)(3-sE7f=RcE1RM_G5bT"
    "_Gbz@R<7Z5AH^NZOO-r1yUnhhWjMk5{rTwikhBYk%|-&}bYU-|J1p0GPjY_y9MiMx@f7Ddvn^S+W+QM^;!Hw*Ox7NU^*kN4g"
    "^{?q=#g~sx;p_L-&m2KASwk?!<N>}cA7^icT8>94Co%dFS#sxl`hJSri(0t{8y)3ZO(oEl-(D97o6v(dq=yH!HJF=oSO$efj"
    "WL^0(55~0y+LdyXCAmxcGqZ8OVu5Am(gyBZWcj$X3dh#If+YyK-VVP)HR>EK)}?4SoBHNj`~-v#jw*pnku!QHMYM$!DA*#rx"
    "S)@Wuj7;eYr1>z=^~IX!NNz>IomuCYWb8~>Y>*E&@Cbv-Boc@wg~W+fvitga5{6FNj}UztzKaVPWIux_Wir0GDsY@j3g;LHS"
    "5{(Bg66Y!-5T#1{-Qp$j@C_WV*v4Hej(Efyq{diVCj*$U|0ZGs>(yGS{>3Usqm->rXFYrM-!m%1n@2)Dr40C9Aq*|ojS*(&@"
    "N{r6Uz7G`{b5C(ylQsdNSpt1CGJ86aC;z@uzx8noc4-j?lIXB)<p~7-aGh*1U3~h{Sl8a(9(3on1**OpN}|3jzGM0X?v}TNp"
    "zQB-Vu?7i959vEeOU6GnB8o;>VBJ_LhS`xSQ(IqgXv<p{Riq@mMDUYMnc_gUUCk|LXCR!Rc1)LS$NL(_xI<DXSdrJ18>||wQ"
    "J<=scC3vrjuXs;Z>}t<;c$vA-3_ax_~Ay^J54B@x$FU?_$!=-HJhh1hc{I(_TuOy*EFtZ^3Y)i$VH0R%4~ja<8&-&919pbGb"
    "LQMkx1XTd-j|KJ>KauUctJrIm>)!;OZYEt5gFxSvD!Cq}ga0<htiAhtj{1Z}2u>}JC;$Z?a^61x5J)mcWn<GCA?ky_Q}*ccS"
    "GU)vEu*{HS|(XjrKB9$;6{Z0_^<Qbz4y4{NlHqcjq5!)DSsgNA6w(Q`CDf8Y$ww9YL3*LK&?GY!Y?>CkQ5YP&KYbKrv@y8&9"
    "F@}FHk<`pWr24`j0VC`kk$g8^#%C|g<922Q8ZW3$A@XlNyQZ-!GY6;#f{xRaTB*O+<&;J;lSb)<yhT>R?ZdZPvkAH%N#-_<s"
    "{y2*Q0+i;U=1$_y3YtajmGwp`#uY_!+Lgn5g%a>T4wW-{451r4VZHhwZ(c<sTK;54JiH0*Sdaff&R=>?M6ct;A49iwOfr%Sx"
    "0wE_yYYX1uF&D7`$!z-Cj}IMn8SJbFLAm`Q-C;FcCSIOior?Xw>?}pO1<xgJ~}N7#+`65n8G%jYV+@j(9JqjM#F;L9TBvlx7"
    "fKF{uJK3jr_oLvPO)Nw>ZGX%p&jtOH+?51~?e{)<DL1vzvGOXNPXBkjk%ceXMp&<<dfdR+SDGoC5ny${0zPQ7)*Oi|o!|1Ke"
    "~WPApr*VEy5rg*x`rVQxvSb9!-p$=RJPm)qxIf7FwmoB_mUB0R~NBTxcNN76Qm%$5m@lN0CQVktGL(9vXFaxZZ6{{-;$uNWU"
    "qN4Io{>v6-$8rzq;{4bN3D@@mg9iHv_{tBgBv4{AL|4nHhJ;g9Gd+uW5wNWr4|yDhe!puG)^M=52g90gOafsjpVNBJ%+NJN_"
    "`o!8*V4J0&z@5DYblN~(aS9dv;aQO;7mMK0J&>`QiF*1>Tq3#&1b*t*vj$174!;?v#`-F2m=~!jazT?^^(O)Ql6pf1a~cwl*"
    "<kbw%-?%Voe$Nv#oyr7}mIT6bIGoIUa@Tz8`$Q)|zN=Y?K*SFXMtfR9t0vgY?SAbzHa3(^*2$O@+tU#PFO2Uu-6j>c6l>pXN"
    "&a3biwgG#(9??)Q7=gYt2U7R_?0xvAyB!NK{<a#DTjT5*vg&fR_e)X$1=^UZ|EslbO>ui2~SR8Du?Vt=B$%+bT;F{xacxT~3"
    "~K3k{cfjA~pD+@ldcoyxNKF}c<fnM166RCBE6Z02Phr!`UvH9{20~0&OdAH&NifEgT^DX{XvQ5+0%?s5s3Zbw;0sT^Z09EK5"
    "9!S~3X6*{Hpbi>gJA<G~Bbi64fD;FZlRbFX#<!%W5D3nzH<}z-cM;V_A`smB@bi4IrULWpY}OyzuT>`^_uWyYm?%4wg)u)#C"
    "Ph}t*&24J&yy@loi|HAb?P-<t+>-u&G1%M)pU(K@l%7-ev(b=Lk%1^day(k@6q>W#b_1HnCac?UktV5<qoH!xiYgLK75uuj)"
    "gQj4#yryvO)iada*cHZIOK3e4WO`3omPd{jo5}25lGLt5L!8Vz;eC)8rqhSUgW}vqqGFmdy*NNH?>4*+31kVgnt8OjObT?r8"
    "$Kk2<}<9jzP3Sb2Iggu54b_5Of!bdSn95%ldA1~h#5z$9xzDk_C%-+`@yl*43!5{JuC{-dHGEtNci=>1#$G&O&+bfh-_*G>$"
    "?_yEG??RI)2&QV-y8M{`kb+i6*p+;HSY>StNMvduAIpGkN@C{Wt3ML=@^Ee{C%YoS4Ew5`4qck^l)Jk=8^7An%3J&2!p}{YW"
    "SEkhDK(Lr^Z)=L>?G@)y(R~OW+2>^zeMZpG*4?%tUGsY*2|wm0Tr&-+XjjJ{X}CD$Qi<+EW}kncJHAdXf$FE5?fpJqSkUPo7"
    ">GVNuzbsoYdl|LWxw3)lCX>5zPGzwyg8>{s`L7|>7l_+{+jhskqWhqov1S;dOYAfA6d7@aPS!ViZ8J0bDv&e51PAvcF}x>B{"
    "=$@!G`t!=C+8p&?rJh6|xjQJIQEXT1|1ZH>?y7e97T9j@(<j`iS~0F@{dTQBdcrK4?hh$VBYMk2+k%d@surzK5i^p47^>lJu"
    "&Vn9$*|M3}G*nk3!A8JK6*S1$g7##-0L@yOHo*S7X0N%c@LK9h{OIk_1au@+p8Av#Qvis`3${AS~CZg)Ce)++vCb;-P9{Pvf"
    "$ccS%o+n8IPS>JK%Vaqmx?W?2aYi}qc!d#U_BeeV&vSI-BhR4R26oj+UIPFcIdg(+E^G=U>?JT#p(y!-OH$U6@`Kzp<!O8`*"
    "2^w>!H=V?7vHD$5E|uqp>x&@w%PUA}N;Cf@SE<`yF5>}JsR*;qfEWDBUNXm4Md~F4*S*I{X+mTnKiWrMa#m+{6`p(+*aDu{L"
    "G>XZ8?rTQC`-%BbIUSih+OR~d7zO6k=|YKwrbvRbNdGomxUwTn_Z%>gE65}Yi|)2w*5@R;G*R(C80T?mZ(oOJ2KUmLGN*-w$"
    "`d%@@7Edk80uCj!>M&agkpTx{r@`v%v5UbTpOp624&97?qTywRXq5>{(Q2JS|08N5E6g79Gv#%9GUsxBm6+{&rjUA?(ypinz"
    "J7nYEM&A*IDPU({zD?5?&d(B?d25cn5I)ZqAYFAfSmU>t((!*>EIP~V2e!Y<B2=^}A=i}y%9;cuZ*JJYpR&@V15lpB!C8yg1"
    "~cN`{*<$K*uA+AR&r0TL{D5jiL*qxWuc3IH^D9({fYk@-fAu7K=jkH=HE%z3D8EXs!j5l|(Bb=F;I~h_)(TsmI!uZNfhDi*U"
    "7V1lX3Vr{FB$>=}c*OvaX_Umf_0y*6kp8%y*0zZhr`j4q?3CGGGY}Am$7wh^IFagm8r0csw?RAvDDKCp_Z<<Cd>r^h9;{#&i"
    "Q#(rPlraQ#jE}Fi5j{}XB%Cp;{_f61<)W|&?m$xW%tzC$1I&qs=%Y(UbXH%i+{ktv#E9N_0ua*R#xuXH)-LSs;h@vl@k05#P"
    "pu7dkhe^(?DBswD>3{w(#-wtJ>z49fZ#{9joQ0jjeZMnx?6n-(B6@>Q#Z**Nnhg*OS8o4f1?kc{=%hmE9?Ag0@Sk6uEY1Q(x"
    "{he3dPnOQTq4S7wHRoR<-<`kG(*%)Zhq%2AK(-H_{z!L|CvXSOg>LmgX#{5r;VfdvGgcS{IsJ-@zw%EHL}rXR<2Y<bW5OJ`Q"
    "A)gUH&_31q3c?Y^QYL;fm*4DXrAiow;i`Sj=Y?YmmkmulYe86raJ3^SFCxY@=#$>A56sr)TYzT&qk+T)Aqhc{((-AVw+AC8I"
    "RM#vV8a6g5(1?0Ea6NlLVuVS|(KVGEhqVNm=PS8P6Zi8Q+NA*8+}y$gP}}%J6|ZXbArHf+?2XQcjHh|-!z9zqEfbHA9wF-nS"
    "w^ZrSK=>R`Ua3D6Lh~_>`q8YzJ!d#A;Q)b1&vvC8z#dtu<14ZC-4Dpozkb5{PBc(uI*EZFb#cH_PHu6O8PipB#p4Yzdt-6@a"
    "t?nClhE|p(&+62FU9m>!z+72w%+@N*?c92gU5Celky;Ga03T4hXp{TDf`!J@a9(c0q9#kI5VMsvQ<nZoE2eiGW9COYt{gxhy"
    "&*xGmUCc@ctj=4FksvR=x{Jzg_`R9i37o!kW>snqKAomOEhHd{1(U(3-T3xm_iC)o)Oe*S?=T2HWiy$H{kEwC#;R!QcuFcZG"
    "K_zJ!HJCW-z{!5AHez`dC;p*}3_>OV<QRsxiVYfD97lx%MzY?3A%+&hWFy^vr|KwuNw~m$zbik$HpmRUJKuIMIQHp=bzwwz`"
    "P_)SVjYh%7cUJ~oclQPhrHdQG2%=idI{DI_xy53&-rIrJ|JTm7|1;hGf2Hn9rPPq)N;!+WBB!B5&JrPqSqFzCMyQO@U5pO6H"
    "{>+j5|YDW&Zkx6ki&9Zjw{13wl;IvX7+jeJU+jC|A6mr_v^>^<Gt%~UDxaNe7>H~?YeeTzxMuNeDw1ayBsQQLh)c?6GM7o+="
    "vJ#=$n`cE3U%8F0$1-dcJP*;Vb>9&0rYFtH?e_nr3%NNDq25w9zzQ<E&Tnk9))KUo=E<97(LF(MY&9>M(Mkd1XCY@%^NwaQb"
    "8Vefp2eD}zIVH)R?tEa<IpqtSSYOUI6<yz?}DJA(Wnef|~*WH0Imx@qGikrCneH!kJ-oJUOJ9;bHOkJBUqn%JYP$l&JkBlxZ"
    "SR#YjD##>*FHAC+yz=|jFU17<GNYNF)%#BGKIuLbi?4EAC@yG0z<Tze{b)1O!SMAmEhKpg*vAw;v-CA8~#CfgXUu$~&&t}yP"
    "-wj&wc57(RcdRsJ$#;G>PC_q!Hl}kC-UbQAt?Rt6a>TCSw?iJYG(~=m30zQ9Ye8^NtqAAC?J5myZNTfatd7;y&~gePgmTp_t"
    "yaOIv*mh<(!(cdZM|$losF-{6W6U9w)W`B=4B|=&z~uSjGpMcE>KcBvtp2om>%yO*_N}@Rg5c$S&2Hs4Oeej*m%|N49NSuY>"
    "Wfj5TUVlVf_m6Hqs9F)uZ+S8py<(MdsEDX|3a3w^LuPQDXzEi3FQKy4DkoOa`~2IS&E#ko{ny7Ftzx{*_C_0K1%d+wvhtB#w"
    "!Adc{6W{_P-2kIv^cCFe(z8*?)cU@~s>OV8XSL<{?mSC_Dt#`<nH%os95_a1(#a9Db?z=uA%i`mdxPug>P|EKTNc%bTq|2Xs"
    ";iS-;T!P9uZ7w%rmsBwI*@AUAM-ii62=KP?>vDclagqWJ6&{$;xORaPGa^2KComKs{fuAG@K4i2|(ZramPd$ecYA+F2cR8`s"
    "bg0+rA5Vw)Et<B2i<Niv_OEvyds-MlT_GiELL=+5jzEG1EggmFUYgEGJ=hm7|5qozc>=n1?#G9bXX&{PZ%c-JGsX`JeXhLSh"
    "B`0k10-J>2Y!bEXxyvXY3Jx(Ge063Ey_+_nZL%e-<LMQ0xDp2N)FKNqgZCPl$6x5JwwHI7rEr9rcw^D$lOY`T|yRTlmJx_$Y"
    "R(0rAWc<_|6{8SMrI=AIy^cw62|iw{qsQeWD?x3cg#%wT$+^*coZ+t{sTuGok=dKHzg}IsmHr`s(UySwBsWj;a{1+lf+a{o-"
    "^_7Uld?MJeWt17+Qi{&216Ui+)IL*>IMLLrTg2Y4NSZsmb*3pCuSx`eNHaOkNKtMgVGWuDCEmjmzs2x)=ysI>qiXugcutZzs"
    "VbH@Dq{aKsbCe^$PR3{EI-p6~tyjbk0MzQjP9$miSfm<Oc<Be+O)<?05`Mo&%%v;qar3F-0w(wVj>B>-c$e~>clEQ+}Iu02}"
    "U<=ImzfpC9>7;A89mD_FoarIz9g}AP-W{-qGsl2+(POf8rG|>^j%!7Pu=PTjGjPBn?>|x8xxBB^aN+yyE8e{e>CmZ4PN=Vxo"
    "Pigpxl4Hc(@L6?%E>)FSp87%x#UWZfnO6}ZC>wu|D@9;93&Uq)PNYVR@=DqR2?*nCsI!&L%6Aa=iBPYPoN8;vu7_aES1?<>8"
    "tJ!ITkq82z!0*u0?l7C4F6l>pdFT!I6Z{XF{l##5G~4Dwm_5zUhK+q#E4}aznkRf3qw1O-;Iz{dsDP1W#gfEUy=H;J9+=rMv"
    "gOw5!eoR`zI*olvlK&uDJfenu<R_}YVg>tUuXs8$orWFuyM0WWw>X9@{cR`eg;N<BYTx7ttmP73)k&%S_c;YY7^r4Tc`z`Gq"
    "7vB!;CkUwH5%C^5U<lkK|z)~{xAgx|d;sYDVQm}n6N|-CwC;2f7|J#N_kCcDS>DG&2&EACX-u-QHH2Y+-V05fjM(6$vBKr40"
    "JVS<xrR2zbd4iQ`OTPCa@yL{?*W0idG+ng+;OUO6RpZQ+Oxw`DrM%axTFsxF{58BhM+%!b-OFydRtK30B0|gO14b>*B_>V;5"
    "rzP!NCXN36#L9RIu}pkTu}onU9JUqx_}ZvC(8l^GNH$r?PzU2P;lv}Ix3?`uzDu-0r$0TZ^@8S<kHE|RxtKOic$h8YIA#Ehm"
    "KK;^8hI9xjdqGYZ(t%``7grdxajk)rO(Z1^?4z^H-WL9eYhrT2ya6V<`#TcCz;g?417Cz;D*-^BCfvw1OkA`_mtXAT0>Ipv-"
    "~h*C;tXRYTI)3&l$Kw{)AAP0kiGeLFbya%@4^T`0U$coU9-8*zUepRXfFt(1t!O{k|R$+&urjXfrTO%MzD7QI%-J9~Ce>g}G"
    "O3<%NV_!ZF;e}3AcH!-@7LdLDpw>D$?cn{~WQ}L;(pcngagmY8%wWPxpWZ5Z1PvFCG|6<;fQrVraFDs{G>r>Oym1DN%SElb&"
    "OMvTLi)=S0tuJvnoKfL@zS~joy3Kwpr!mAO9^dDGp@_F6J*!MK=9O`{v<v0ksJks^g<gjA=@|7ugdv>Sl<qL2GW(T3T1||Bm"
    "#_uAKY!N7@Qm%(I|+>Di8X%Cd7lqs^&w8=_5l2RG1u4Q`7E;-mC<>lbaAmB7aG+yG(q)g!O<uU^)`0pckPjDI>f+qFoe^7i`"
    "?$<9HpF<Y_wesuO(^i2&|%_qGLFrN3^LX-OOjtlk~?qW0g(;Bdh##(%K8REjE6w8_tyOzGSpEi?3j;o=%3$XFmx9v<kdd$5I"
    "~2k|K6S-d{n?v!&pOXv3EIH2({I4oF7%KMn;~&xU^4bcNJGql16NN%GXDlgi!un(5ru)^T60rk}f&+}R2!p?_|+;6e#KxU6#"
    "&oz)9R$_~h!5ll39pV*$cXORp$+JWC*Bf*kTu9}}pg;Kp|yU^#i;;vWBA3kFIgb*^9MkgBn+|#(H^J-8~g{)H_r@<bZnv<hS"
    "*kXm2>9##Cvdz-)SC3(PO8z=5Gb$x>@j=3x?`Ho;s>RNEwxcEk%tbAN_PE~SY|*^%5#yP~sE!`)^f0l^3y<P_-Uog{kNU&m*"
    "@sSNU5g}X3Zmn2hm;?>q4DSFuEz$_xRRPJf>%(w=9KJId@B;pLSkhTIuf(8iIA1$;FmMiffLiKOpkJe-D=^B6bK>ba_9tMA6"
    "KCtN1yJIoLCfpJcT3_Q%XB^*e;W>;+i1p;@w7F=j2lV+`+1vF~R(VEi_YMbb=C2@sftGFOo<PM!4EDBEL%?txWdS<C?awp5L"
    "Dywh&yQA2ivM)XsQ6pq1I_yte*i0yzLUrzCnCuy+iep1wol0~jHi51kS)Dau)PS=!7nS<=CrTcXJ5jN-a;35`%>qSnmTWD=E"
    "k$FSvR+^^HU?j_+6Iaps-t#;?@NAr!+M+~5dh<|3R<NvBQSP5I5_XyI>q5CZQ5k(_DFOSg>_=s07MHl5e5Ro6@3vd2%tbwd)"
    "<HKpAnABA7zWdmWjC)2&dNcbE#J6GK<(&_#XVpR)eVh4~*0!l~hP57KEm&)_x1V26lH9~>Cpac`3>;&|4ZYr%RpQJ4<M8aqH"
    "qjIjaWzX{-y&}xAGc1NW1)2%en$DtM0nYaI|EFOUTND>nt(wNsDX*xKaX~PKsMp~@I>Q@aop?Ihf39%Ku13__xCpp7OU~A%("
    "ld_@TIrkoaH0?H{SGK%<c<h#994@<}-?Cz6rKBOsv$>Pri~kivfDI(oyEaf5Jw$8^dYe1}wmVITUe>4ph+%U#)!RjHSJO(wa"
    "V>P}H<X9VzZBku`s;N6IB@xcM@n;P%cjb?fIe5-!~?`(jsf#41Ft(=JO#C)t2?f)+Jcvsf26;ajLRMQuBRyOU#qLZ3Wv0JWA"
    "y&u+!F?F%EDi<B|us8n|w8wt>?Tfyp~D*_zB;Up@*%}(Uy)fMsR>FA&=PSstDo1*$>z9OK6^uHZ~l8NRq<n7X5)OlaYv;GZ+"
    "5Pp>DGs`=7Fl*6{j(Y=|v?oQx*)>tBuJ$GYmK@ex8F6lI?k0}5u@bBug@m^CbPrIl4_dtPO}|1Tk^+g;I1cetysR2vEnT(?3"
    "B}aXj)|9PCS4tCGLRh22P;Iq9s`TvoulI(bwM?Q_4A**yVJ_FaYv?N>?GHhc5$1l)Aq1izUcA%8WSMX>r55;CXHD=<Z<V%e2"
    "=#}e<5U;Qo*2+n;~}U5iXlt*F0Lt$i@m09KCsal%}dGUQW%j4>M%f0}^SPYlMUiHRM$2K<p$NwZO>DR;?uJi^I~Hhh;8S4|;"
    "Rg1FL*`@>nF8M>&6x;#T5V6>j{4SIqptEM*ok(W$BR>eHbQS&wr3xQ!ht(O!80%~$2McoDN4=Z30WuzpjtMRHz8T?ekkNV;O"
    "XLcVi(c@j#kL={t8I$~U0`YTA`k?e4OYYP<7dcS^vWBJId)!X|4xu#`r!(PYAJ9}vmDBub;_>U^Jk`_O|kBma@{OpM?NHVZa"
    "g0L+0S?^EJe!p^Lih@n*C2M;fOfEjv5D_toj7Lt#wq=gOkQEy;j||inx2AITElcn{>#pDo5y%nBTk-&vs}kg09Bu+jWh^`n<"
    "E`ZjNRiup*}5L2d6VtUD;I+%Rb+JkEHDxJH~w!t<@+pe=n4salK=9n%+Ji*+1i@bBZljfK>wvsby88012f01fY9)l6@>VNt`"
    "$|)?t=<mbuHN#%$BDfHZ3SdcWJ{K!FLyHa5H;o_O3ah`ELvcqPld!&U{u?%<32#BDR==!8D(f?Qgtn#(mKxD%O1z-O5F@Z&X"
    "O4#S|P*D=J2W4g_Q>u*j*Yvlm`Y)FPh{-tjdr=2|}b?*ubM;_>6CHaDCF1Sc!%S18UmF`8NH66AqI{g9G;#Ep917D5jj9;Am"
    "|GuOlVNLC1(*;~u+iDwVS<3EV=1*~AbfUA1gkyEn$Su&!2&Kd}QGw{fMcw_oNJpK<!=kv?sNx^!w)nL6+<N;niX=9@{2F=_f"
    "BqVD8<#IGwNGKsnRl&|4!fdCR=6}~$cpFD|lRgL7o9=uE6&;XB-^bHxAd!}_=7^NiIyl)y7bIeoheo6C5#&YUa;w0=n^xvH1"
    "~=&4ds0o^=TE>o*$ygUkMO>UVER-O6%}_-GU-U1sh@ciT}5ml@WW7*&uS3~MmF3a2>6IFoR?9qm6cWhp*U0O#emUziU+(U!m"
    "JH-7<?ekR3Hf~=@=R$7U55y)Nf3N$D5vN+V|xjI04FXR{<faVgn~8c!et)@=TCOoHXW#kdR*R&NZ^&za1Sht2L!OE9D%lx<a"
    "4X>~66LWsrzsfbM#Ab#={kSU0r!$zt=BBSy<eF)8<9C>ddN_UuX!?|Q>SpTlt2h$Ol&-@&qJGeEJuh0=L#3EK2%<)OmEAQjM"
    "kPj*A3`RpoS1s0|{60<e3E(YG;7_XtpR^4}Y$2+JDo0*OKo11RXr=+QKb1kJ)j5VHnJ{l;L5BEnt)TCfA#vt^(InUVDtarZ8"
    "<DO!t)z@~r5(dMEP(UeRM7Qq)vSPY(U#<TM4(Ow&#7b6Ii2?5Zr##H6zn7;8*Rp;Ek8T0|JV#Z*$$VBq%q=f9HT69%S&qk&;"
    "_Axw4>G{-d(6F~+}+)8s)GUk>Dn!pc~T)~tq(}g3x&a3V^xKVK(qU#3;-kk*zx0GGBpk{nF+S`Ha0{0d(NCa8(5jJ#o%v{X="
    "fCsBsD$ReP|2$h<igtePOvzotD9}Mu_2LByYV`UBOkd?s8!>tTlG0tj%T<o+n5O3C-lziU8&PT(|Twg9hiZhprKTp?QG9m6?"
    "w-&6l_?E~F2@ZKa0C!zlK=NwCxs%go8n&h{w$25`T>zrU;8PX_L&SRfy#sXzd=6cJ-U=)7=ND^SXoVkJ8WbyfjMvpLkfwM_l"
    "hHN#OHjKHPg2&&{VH;OcOELhJ*nVg-0!AypBV|-56oCl!T5CSA`<im(RHBnZdJM7yhP5b=^&Ek!Q+m=O&l3k(sE2sP8ZBhzp"
    "tnG@;gmK0lij`T$!JTDX+DV4!_sR`}NWNlv*oSj5+mOI=m;Co4LLQEFLC_^~a9d)z`Mc`_W&BZ^!5`Dx4p*;sY_o@DG!%$8D"
    "m)_!Bzj*d2}iki{*-KiOBngyw}}L}s94T0w{C5NEO<N^fa{yYWM^+U0*#qK?5@06_$uLs3O6^1!g?#nYYbbgv#9W>TmSY}UK"
    "kz6xeRQ*j7xRnr4Z{#fKQT=inG^G8w&|t`tSYo;C`MYG>mz=E#3rooG~&m%Knz7F1gV#S>jZ@L6TUBjg8gCU@)3Pnhcva8vf"
    "tQ-0*4&tZ-mLMnJ1=b@pSyTBF7eBueXSn<~rLT3NN0zJIl4;zb(ccP1ehnOH0q{!&dIRs8M@5di67Gw&<FXJJ51CYo&h=4a<"
    "2*Uc~Eefw(EW2j?zlj)lUR}=R-71`4M&fTs<)!CbI0T|!?mg*|MIL*%z17LP=uJf!%Z5gcGz2vZ?lM`7}I_MTa3fmg8{aiz3"
    "Wy5nI5&zrBBZ~hmGrET-L>vTKn0<*u-`cf9qq#=`D%u}sioBBl-Cwa60p<t{@*Ngh7f1zPCa9!v1%iVL+g1f+t%}HXWJkH?L"
    "qH;O(jsw6i-!c}#8RLj^Yb0v+W~~40TLO*|E@b2XZl#2Pq?iDS^|q*jdM`ZZp`5O-(*KBuE0we>DB*Z&_g@_D-fJp`{^+$gw"
    "6XsW~bn2<1tat^yO98H-KdTUNkwr#*M{zX{r4PP>k&_!o_hm1_uY1gSHGB$m_tco@R7l2gj)}Wf9poZ{E}z0~1qLXq=tCC}t"
    "&zzHSaP)VZVb6or-(i3{t#oD+I09T*p^5WNAm{$C>jh6_^>{<qiv8~?`tOI&)!5bWY*EF>Is3_P~;z{=d-titrxv;P3H+34K"
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
