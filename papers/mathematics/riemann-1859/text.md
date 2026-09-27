Meinen Dank für die Auszeichnung, welche mir die Akademie durch die Aufnahme unter ihre Correspondenten hat zu Theil werden lassen, glaube ich am besten dadurch zu erkennen zu geben, dass ich von der hiedurch erhaltenen Erlaubniss baldigst Gebrauch mache durch Mittheilung einer Untersuchung über die Häufigkeit der Primzahlen; ein Gegenstand, welcher durch das Interesse, welches <span class="sp">Gauss</span> und <span class="sp">Dirichlet</span> demselben längere Zeit geschenkt haben, einer solchen Mittheilung vielleicht nicht ganz unwerth erscheint.

Bei dieser Untersuchung diente mir als Ausgangspunkt die von <span class="sp">Euler</span> gemachte Bemerkung, dass das Product

$$
\prod\frac1{1-\dfrac1{p^s}}=\sum\frac1{n^s},
$$

wenn für \(p\) alle Primzahlen, für \(n\) alle ganzen Zahlen gesetzt werden. Die Function der complexen Veränderlichen \(s\), welche durch diese beiden Ausdrücke, so lange sie convergiren, dargestellt wird, bezeichne ich durch \(\zeta(s)\). Beide convergiren nur, so lange der reelle Theil von \(s\) grösser als 1 ist; es lässt sich indess leicht ein immer gültig bleibender Ausdruck der Function finden. Durch Anwendung der Gleichung

$$
\int_0^\infty e^{-nx}x^{s-1}dx=\frac{\Pi(s-1)}{n^s}
$$

erhält man zunächst

$$
\Pi(s-1)\,\zeta(s)=\int_0^\infty\frac{x^{s-1}dx}{e^x-1}.
$$

Betrachtet man nun das Integral

$$
\int\frac{(-x)^{s-1}dx}{e^x-1},
$$

von \(+\infty\) bis \(+\infty\) positiv um ein Grössengebiet erstreckt, welches den Werth 0, aber keinen andern Unstetigkeitswerth der Function unter dem Integralzeichen im Innern enthält, so ergiebt sich dieses leicht als gleich

$$
(e^{-\pi si}-e^{\pi si})\int_0^\infty\frac{x^{s-1}dx}{e^x-1},
$$

vorausgesetzt, dass in der vieldeutigen Function \((-x)^{s-1}=e^{(s-1)\log(-x)}\) der Logarithmus von \(-x\) so bestimmt worden ist, dass er für ein negatives \(x\) reell wird. Man hat daher

$$
2\sin\pi s\,\Pi(s-1)\,\zeta(s)=i\int_\infty^\infty\frac{(-x)^{s-1}dx}{e^x-1},
$$

das Integral in der eben angegebenen Bedeutung verstanden.

Diese Gleichung giebt nun den Werth der Function \(\zeta(s)\) für jedes beliebige complexe \(s\) und zeigt, dass sie einwerthig und für alle endlichen Werthe von \(s\), ausser 1, endlich ist, so wie auch, dass sie verschwindet, wenn \(s\) gleich einer negativen geraden Zahl ist.

Wenn der reelle Theil von \(s\) negativ ist, kann das Integral, statt positiv um das oben angegebene Grössengebiet, auch negativ um das Grössengebiet welches sämmtliche übrigen complexen Grössen enthält erstreckt werden, da das Integral durch Werthe mit unendlich grossem Modul dann unendlich klein ist. Im Innern dieses Grössengebiets aber wird die Function unter dem Integralzeichen nur unstetig, wenn \(x\) gleich einem ganzen Vielfachen von \(\pm2\pi i\) wird und das Integral ist daher gleich der Summe der Integrale negativ um diese Werthe genommen. Das Integral um den Werth \(n2\pi i\) aber ist \(=(-n2\pi i)^{s-1}(-2\pi i)\); man erhält daher

$$
2\sin\pi s\,\Pi(s-1)\,\zeta(s)=(2\pi)^s\sum n^{s-1}\bigl((-i)^{s-1}+i^{s-1}\bigr),
$$

also eine Relation zwischen \(\zeta(s)\) und \(\zeta(1-s)\), welche sich mit Benutzung bekannter Eigenschaften der Function \(\Pi\) auch so ausdrücken lässt:

$$
\Pi\left(\frac s2-1\right)\pi^{-\frac s2}\zeta(s)
$$

bleibt ungeändert, wenn \(s\) in \(1-s\) verwandelt wird.

Diese Eigenschaft der Function veranlasste mich statt \(\Pi(s-1)\) das Integral \(\Pi\left(\frac s2-1\right)\) in dem allgemeinen Gliede der Reihe \(\sum\frac1{n^s}\) einzuführen, wodurch man einen sehr bequemen Ausdruck der Function \(\zeta(s)\) erhält. In der That hat man

$$
\frac1{n^s}\,\Pi\left(\frac s2-1\right)\pi^{-\frac s2}=\int_0^\infty e^{-nn\pi x}x^{\frac s2-1}dx,
$$

also, wenn man

$$
\sum_1^\infty e^{-nn\pi x}=\psi(x)
$$

setzt,

$$
\Pi\left(\frac s2-1\right)\pi^{-\frac s2}\zeta(s)=\int_0^\infty\psi(x)x^{\frac s2-1}dx,
$$

oder da \(2\psi(x)+1=x^{-\frac12}\left(2\psi\left(\frac1x\right)+1\right)\), (Jacobi. Fund. S. 184)

$$
\begin{aligned}\Pi\left(\frac s2-1\right)\pi^{-\frac s2}\zeta(s)&=\int_1^\infty(x)\psi x^{\frac s2-1}dx+\int_0^1\psi\left(\frac1x\right)x^{\frac s2-\frac32}dx\\
&\quad+\frac12\int_0^1\left(x^{\frac s2-\frac32}-x^{\frac s2-1}\right)dx\\
&=\frac1{s(s-1)}+\int_1^\infty\psi(x)\left(x^{\frac s2-1}+x^{-\frac12-\frac s2}\right)dx.\end{aligned}
$$

Ich setze nun \(s=\tfrac12+ti\) und

$$
\Pi\left(\frac s2\right)(s-1)\pi^{-\frac s2}\zeta(s)=\xi(t),
$$

so dass

$$
\xi(t)=\frac12-\left(tt+\frac14\right)\int_1^\infty\psi(x)x^{-\frac34}\cos\left(\tfrac12t\log x\right)dx
$$

oder auch

$$
\xi(t)=4\int_1^\infty\frac{d\left(x^\frac32\psi'(x)\right)}{dx}x^{-\frac14}\cos\left(\tfrac12t\log x\right)dx.
$$

Diese Function ist für alle endlichen Werthe von \(t\) endlich, und lässt sich nach Potenzen von \(tt\) in eine sehr schnell convergirende Reihe entwickeln. Da für einen Werth von \(s\), dessen reeller Bestandtheil grösser als 1 ist, \(\log\zeta(s)=-\sum\log(1-p^{-s})\) endlich bleibt und von den Logarithmen der übrigen Factoren von \(\xi(t)\) dasselbe gilt, so kann die Function \(\xi(t)\) nur verschwinden, wenn der imaginäre Theil von \(t\) zwischen \(\tfrac12i\) und \(-\tfrac12i\) liegt. Die Anzahl der Wurzeln von \(\xi(t)=0\), deren reeller Theil zwischen 0 und \(T\) liegt, ist etwa \(=\tfrac T{2\pi}\log\tfrac T{2\pi}-\tfrac T{2\pi}\); denn das Integral \(\textstyle\int d\log\xi(t)\) positiv um den Inbegriff der Werthe von \(t\) erstreckt, deren imaginärer Theil zwischen \(\tfrac12i\) und \(-\tfrac12i\) und deren reeller Theil zwischen 0 und \(T\) liegt, ist, (bis auf einen Bruchtheil von der Ordnung der Grösse \(\tfrac1T\)) gleich \((T\log\tfrac T{2\pi}-T)i\); dieses Integral aber ist gleich der Anzahl der in diesem Gebiet liegenden Wurzeln von \(\xi(t)=0\), multiplicirt mit \(2\pi i\). Man findet nun in der That etwa so viel reelle Wurzeln innerhalb dieser Grenzen, und es ist sehr wahrscheinlich, dass alle Wurzeln reell sind. Hievon wäre allerdings ein strenger Beweis zu wünschen; ich habe indess die Aufsuchung desselben, nach einigen flüchtigen vergeblichen Versuchen vorläufig bei Seite gelassen, da er für den nächsten Zweck meiner Untersuchung entbehrlich schien.

Bezeichnet man durch \(\alpha\) jede Wurzel der Gleichung \(\xi(\alpha)=0\), so kann man \(\log\xi(t)\) durch

$$
\sum\log\left(1-\frac{tt}{\alpha\alpha}\right)+\log\xi(0)
$$

ausdrücken; denn da die Dichtigkeit der Wurzeln von der Grösse \(t\) mit \(t\) nur wie \(\log\frac t{2\pi}\) wächst, so convergirt dieser Ausdruck und wird für ein unendliches \(t\) nur unendlich wie \(t\log t\); er unterscheidet sich also von \(\log\xi(t)\) um eine Function von \(tt\), die für ein endliches \(t\) stetig und endlich bleibt und mit \(tt\) dividirt für ein unendliches \(t\) unendlich klein wird. Dieser Unterschied ist folglich eine Constante, deren Werth durch Einsetzung von \(t=0\) bestimmt werden kann.

Mit diesen Hülfsmitteln lässt sich nun die Anzahl der Primzahlen, die kleiner als \(x\) sind, bestimmen.

Es sei \(F(x)\), wenn \(x\) nicht gerade einer Primzahl gleich ist, gleich dieser Anzahl, wenn aber \(x\) eine Primzahl ist, um \(\tfrac12\) grösser, so dass für ein \(x\), bei welchem \(F(x)\) sich sprungweise ändert,

$$
F(x)=\frac{F(x+0)+F(x-0)}2.
$$

Ersetzt man nun in

$$
\log\zeta(s)=-\sum\log(1-p^{-s})=\sum p^{-s}+\tfrac12\sum p^{-2s}+\tfrac13\sum p^{-3s}+\ldots
$$

$$
p^{-s}\text{ durch }s\int_p^\infty x^{-s-1}dx,\;\;p^{-2s}\text{ durch }s\int_{p^2}^\infty x^{-s-1}dx,\;\ldots,
$$

so erhält man

$$
\frac{\log\zeta(s)}s=\int_1^\infty f(x)x^{-s-1}dx,
$$

wenn man

$$
F(x)+\tfrac12F(x^\frac12)+\tfrac13F(x^\frac13)+\ldots
$$

durch \(f(x)\) bezeichnet.

Diese Gleichung ist gültig für jeden complexen Werth \(a+bi\) von \(s\), wenn \(a>1\). Wenn aber in diesem Umfange die Gleichung

$$
g(s)=\int_0^\infty h(x)x^{-s}d\log x
$$

gilt, so kann man mit Hülfe des Fourier’schen Satzes die Function \(h\) durch die Function \(g\) ausdrücken. Die Gleichung zerfällt, wenn \(h(x)\) reell ist und

$$
g(a+bi)=g_1(b)+ig_2(b),
$$

in die beiden folgenden

$$
\begin{aligned}g_1(b)&=\int_0^\infty h(x)x^{-a}\cos(b\log x)\,d\log x,\\
ig_2(b)&=-i\int_0^\infty h(x)x^{-a}\sin(b\log x)\,d\log x.\end{aligned}
$$

Wenn man beide Gleichungen mit \(\bigl(\cos(b\log y)+i\sin(b\log y)\bigr)db\) multiplicirt und von \(-\infty\) bis \(\infty\) integrirt, so erhält man in beiden auf der rechten Seite nach dem Fourier’schen Satze \(\pi h(y)y^{-a}\), also, wenn man beide Gleichungen addirt und mit \(iy^a\) multiplicirt

$$
2\pi i\,h(y)=\int_{a-\infty i}^{a+\infty i}g(s)y^sds,
$$

worin die Integration so auszuführen ist, dass der reelle Theil von \(s\) constant bleibt.

Das Integral stellt für einen Werth von \(y\), bei welchem eine sprungweise Änderung der Function \(h(y)\) stattfindet, den Mittelwerth aus den Werthen der Function \(h\) zu beiden Seiten des Sprunges dar. Bei der hier vorausgesetzten Bestimmungsweise der Function \(f(x)\) besitzt diese dieselbe Eigenschaft, und man hat daher völlig allgemein

$$
f(y)=\frac1{2\pi i}\int_{a-\infty i}^{a+\infty i}\frac{\log\zeta(s)}sy^sds.
$$

Für \(\log\zeta\) kann man nun den früher gefundenen Ausdruck

$$
\frac s2\log\pi-\log(s-1)-\log\Pi\frac s2+\log\left(1+\frac{(s-\frac12)^2}{\alpha\alpha}\right)+\log\xi(0)
$$

substituiren; die Integrale der einzelnen Glieder dieses Ausdrucks würden aber dann in’s Unendliche ausgedehnt nicht convergiren, weshalb es zweckmässig ist, die Gleichung vorher durch partielle Integration in

$$
f(x)=-\frac1{2\pi i}\frac1{\log x}\int_{a-\infty i}^{a+\infty i}\frac{d\frac{\log\zeta(s)}s}{ds}x^sds
$$

umzuformen.

Da

$$
-\log\Pi\frac s2=\lim\left(\sum_{n=1}^{n=m}\log\left(1+\frac s{2n}\right)-\frac s2\log m\right),\;\text{für }m=\infty,
$$

also

$$
-\frac{d\frac1s\log\Pi\frac s2}{ds}=\sum_1^\infty\frac{d\frac1s\log\left(1+\frac s{2n}\right)}{ds},
$$

so erhalten dann sämmtliche Glieder des Ausdrucks für \(f(x)\) mit Ausnahme von

$$
\frac1{2\pi i}\frac1{\log x}\int_{a-\infty i}^{a+\infty i}\frac1{ss}\log\xi(0)\,x^sds=\log\xi(0)
$$

die Form

$$
\pm\frac1{2\pi i}\frac1{\log x}\int_{a-\infty i}^{a+\infty i}\frac{d\left(\frac1s\log\left(1-\frac s\beta\right)\right)}{ds}x^sds.
$$

Nun ist aber

$$
\frac{d\left(\frac1s\log\left(1-\frac s\beta\right)\right)}{d\beta}=\frac1{(\beta-s)\beta}
$$

und, wenn der reelle Theil von \(s\) grösser als der reelle Theil von \(\beta\) ist,

$$
\begin{aligned}\frac1{2\pi i}\int_{a-\infty i}^{a+\infty i}\frac{x^sds}{(\beta-s)\beta}=\frac{x^\beta}\beta&=\int_\infty^x x^{\beta-1}dx,\\
\text{oder }&=\int_0^x x^{\beta-1}dx,\end{aligned}
$$

je nachdem der reelle Theil von \(\beta\) negativ oder positiv ist. Man hat daher

$$
\begin{aligned}&\frac1{2\pi i}\frac1{\log x}\int_{a-\infty i}^{a+\infty i}\frac{d\left(\frac1s\log\left(1-\frac s\beta\right)\right)}{ds}x^sds\\
&=-\frac1{2\pi i}\int\limits_{a-\infty i}^{a+\infty i}\frac1s\log\left(1-\frac s\beta\right)x^sds\\
&=\int_\infty^x\frac{x^{\beta-1}}{\log x}dx+\text{const. im ersten}\\
\text{und }&=\int_0^x\frac{x^{\beta-1}}{\log x}dx+\text{const. im zweiten Falle.}\end{aligned}
$$

Im ersten Falle bestimmt sich die Integrationsconstante, wenn man den reellen Theil von \(\beta\) negativ unendlich werden lässt; im zweiten Falle erhält das Integral von 0 bis \(x\) um \(2\pi i\) verschiedene Werthe, je nachdem die Integration durch complexe Werthe mit positiven oder negativen Arcus geschieht, und wird, auf jenem Wege genommen, unendlich klein, wenn der Coefficient von \(i\) in dem Werthe von \(\beta\) positiv unendlich wird, auf letzterem aber, wenn dieser Coefficient negativ unendlich wird. Hieraus ergiebt sich, wie auf der linken Seite \(\log(1-\tfrac s\beta)\) zu bestimmen ist, damit die Integrationsconstante wegfällt.

Durch Einsetzung dieser Werthe in den Ausdruck für \(f(x)\) erhält man

$$
\begin{aligned}f(x)=Li(x)&-\sum\nolimits^\alpha\left(Li\left(x^{\frac12+\alpha i}\right)+Li\left(x^{\frac12-\alpha i}\right)\right)\\
&+\int_x^\infty\frac1{x^2-1}\frac{dx}{x\log x}+\log\xi(0),\end{aligned}
$$

wenn in \(\sum^\alpha\) für \(\alpha\) sämmtliche positiven (oder einen positiven reellen Theil enthaltenden) Wurzeln der Gleichung \(\xi(\alpha)=0\), ihrer Grösse nach geordnet, gesetzt werden. Es lässt sich, mit Hülfe einer genaueren Discussion der Function \(\xi\), leicht zeigen, dass bei dieser Anordnung der Werth der Reihe

$$
\sum\left(Li\left(x^{\frac12+\alpha i}\right)+Li\left(x^{\frac12-\alpha i}\right)\right)\log x
$$

mit dem Grenzwerth, gegen welchen

$$
\frac1{2\pi i}\int_{a-bi}^{a+bi}\frac{d\frac1s\sum\log\left(1+\frac{\left(s-\frac12\right)^2}{\alpha\alpha}\right)}{ds}x^sds
$$

bei unaufhörlichem Wachsen der Grösse \(b\) convergirt, übereinstimmt; durch veränderte Anordnung aber würde sie jeden beliebigen reellen Werth erhalten können.

Aus \(f(x)\) findet sich \(F(x)\) mittelst der durch Umkehrung der Relation

$$
f(x)=\sum\frac1nF\left(x^\frac1n\right)
$$

sich ergebenden Gleichung

$$
F(x)=\sum(-1)^\mu\frac1mf\left(x^\frac1m\right),
$$

worin für \(m\) der Reihe nach die durch kein Quadrat ausser 1 theilbaren Zahlen zu setzen sind und \(\mu\) die Anzahl der Primfactoren von \(m\) bezeichnet.

Beschränkt man \(\sum^\alpha\) auf eine endliche Zahl von Gliedern, so giebt die Derivirte des Ausdrucks für \(f(x)\) oder, bis auf einen mit wachsendem \(x\) sehr schnell abnehmenden Theil,

$$
\frac1{\log x}-2\sum\nolimits^\alpha\frac{\cos(\alpha\log x)x^{-\frac12}}{\log x}
$$

einen angenäherten Ausdruck für die Dichtigkeit der Primzahlen + der halben Dichtigkeit der Primzahlquadrate \(+\tfrac13\) von der Dichtigkeit der Primzahlcuben u. s. w. von der Grösse \(x\).

Die bekannte Näherungsformel \(F(x)=Li(x)\) ist also nur bis auf Grössen von der Ordnung der Grösse \(x^\frac12\) richtig und giebt einen etwas zu grossen Werth; denn die nicht periodischen Glieder in dem Ausdrucke von \(F(x)\) sind, von Grössen, die mit \(x\) nicht in’s Unendliche wachsen, abgesehen:

$$
\begin{gathered}Li(x)-\frac12Li\left(x^\frac12\right)-\frac13Li\left(x^\frac13\right)-\frac15Li\left(x^\frac15\right)+\frac16Li\left(x^\frac16\right)\\
-\frac17Li\left(x^\frac17\right)+\ldots\end{gathered}
$$

In der That hat sich bei der von <span class="sp">Gauss</span> und <span class="sp">Goldschmidt</span> vorgenommenen und bis zu \(x=\) drei Millionen fortgesetzten Vergleichung von \(Li(x)\) mit der Anzahl der Primzahlen unter \(x\) diese Anzahl schon vom ersten Hunderttausend an stets kleiner als \(Li(x)\) ergeben, und zwar wächst die Differenz unter manchen Schwankungen allmählich mit \(x\). Aber auch die von den periodischen Gliedern abhängige stellenweise Verdichtung und Verdünnung der Primzahlen hat schon bei den Zählungen die Aufmerksamkeit erregt, ohne dass jedoch hierin eine Gesetzmässigkeit bemerkt worden wäre. Bei einer etwaigen neuen Zählung würde es interessant sein, den Einfluss der einzelnen in dem Ausdrucke für die Dichtigkeit der Primzahlen enthaltenen periodischen Glieder zu verfolgen. Einen regelmässigeren Gang als \(F(x)\) würde die Function \(f(x)\) zeigen, welche sich schon im ersten Hundert sehr deutlich als mit \(Li(x)+\log\xi(0)\) im Mittel übereinstimmend erkennen lässt.
