::: wide

::: image bernoulli-diagram.png width=66% on_light=multiply on_dark=invert

:::

## <span class="sc">Note G.</span>—Page 689.

It is desirable to guard against the possibility of exaggerated ideas that might arise as to the powers of the Analytical Engine. In considering any new subject, there is frequently a tendency, first, to *overrate* what we find to be already interesting or remarkable; and, secondly, by a sort of natural reaction, to *undervalue* the true state of the case, when we do discover that our notions have surpassed those that were really tenable.

The Analytical Engine has no pretensions whatever to *originate* any thing. It can do whatever *we know how to order it* to perform. It can *follow* analysis; but it has no power of *anticipating* any analytical relations or truths. Its province is to assist us in making *available* what we are already acquainted with. This it is calculated to effect primarily and chiefly of course, through its executive faculties; but it is likely to exert an *indirect* and reciprocal influence on science itself in another manner. For, in so distributing and combining the truths and the formulæ of analysis, that they may become most easily and rapidly amenable to the mechanical combinations of the engine, the relations and the nature of many subjects in that science are necessarily thrown into new lights, and more profoundly investigated. This is a decidedly indirect, and a somewhat *speculative*, consequence of such an invention. It is however pretty evident, on general principles, that in devising for mathematical truths a new form in which to record and throw themselves out for actual use, views are likely to be induced, which should again react on the more theoretical phase of the subject. There are in all extensions of human power, or additions to human knowledge, various *collateral* influences, besides the main and primary object attained.

To return to the executive faculties of this engine: the question must arise in every mind, are they *really* even able to *follow* analysis in its whole extent? No reply, entirely satisfactory to all minds, can be given to this query, excepting the actual existence of the engine, and actual experience of its practical results. We will however sum up for each reader's consideration the chief elements with which the engine works:—

1. It performs the four operations of simple arithmetic upon any numbers whatever.
2. By means of certain artifices and arrangements (upon which we cannot enter within the restricted space which such a publication as the present may admit of), there is no limit either to the *magnitude* of the *numbers* used, or to the *number* of *quantities* (either variables or constants) that may be employed.
3. It can combine these numbers and these quantities either algebraically or arithmetically, in relations unlimited as to variety, extent, or complexity.
4. It uses algebraic *signs* according to their proper laws, and developes the logical consequences of these laws.
5. It can arbitrarily substitute any formula for any other; effacing the first from the columns on which it is represented, and making the second appear in its stead.
6. It can provide for singular values. Its power of doing this is referred to in M. Menabrea's memoir, page 685, where he mentions the passage of values through zero and infinity. The practicability of causing it arbitrarily to change its processes at any moment, on the occurrence of any specified contingency (of which its substitution of \((\frac{1}{2}\cos.\overline{n+1}~\theta+\frac{1}{2}\cos.\overline{n-1}~\theta)\) for \((\cos.n\theta.\cos.\theta)\) explained in Note E., is in some degree an illustration), at once secures this point.

The subject of integration and of differentiation demands some notice. The engine can effect these processes in either of two ways:—

First. We may order it, by means of the Operation and of the Variable-cards, to go through the various steps by which the required *limit* can be worked out for whatever function is under consideration.

Secondly. It may (if we know the form of the limit for the function in question) effect the integration or differentiation by direct[^1] substitution. We remarked in Note B., that any *set* of columns on which numbers are inscribed, represents merely a *general* function of the several quantities, until the special function have been impressed by means of the Operation and Variable-cards. Consequently, if instead of requiring the value of the function, we require that of its integral, or of its differential coefficient, we have merely to order whatever particular combination of the ingredient quantities may constitute that integral or that coefficient. In \(ax^n\), for instance, instead of the quantities

$$
\underbrace{\begin{array}{ccc}\mathbf{V}_0&\mathbf{V}_1&\mathbf{V}_2\\[0.3em]\boxed{\vphantom{\dfrac{a}{a}}\;a\;}&\boxed{\vphantom{\dfrac{a}{a}}\;n\;}&\boxed{\vphantom{\dfrac{a}{a}}\;x\;}\end{array}}_{\displaystyle ax^n}\quad\begin{array}{c}\mathbf{V}_3\\[0.3em]\boxed{\vphantom{\dfrac{a}{a}}\;ax^n\;}\end{array}
$$

being ordered to appear on \(\mathrm{V}_3\) in the combination \(ax^n\), they would be ordered to appear in that of

$$
anx^{n-1}.
$$

They would then stand thus:—

$$
\underbrace{\begin{array}{ccc}\mathbf{V}_0&\mathbf{V}_1&\mathbf{V}_2\\[0.3em]\boxed{\vphantom{\dfrac{a}{a}}\;a\;}&\boxed{\vphantom{\dfrac{a}{a}}\;n\;}&\boxed{\vphantom{\dfrac{a}{a}}\;x\;}\end{array}}_{\displaystyle anx^{n-1}}\quad\begin{array}{c}\mathbf{V}_3\\[0.3em]\boxed{\vphantom{\dfrac{a}{a}}\;anx^{n-1}\;}\end{array}
$$

Similarly, we might have \(\frac{a}{n}x^{(n+1)}\), the integral of \(ax_n\).

An interesting example for following out the processes of the engine would be such a form as

$$
\int\frac{x^n\;dx}{\sqrt{a^2-x^2}},
$$

or any other cases of integration by successive reductions, where an integral which contains an operation repeated \(n\) times can be made to depend upon another which contains the same \(n-1\) or \(n-2\) times, and so on until by continued reduction we arrive at a certain *ultimate* form, whose value has then to be determined.

The methods in Arbogast's *Calcul des Dérivations* are peculiarly fitted for the notation and the processes of the engine. Likewise the whole of the Combinatorial Analysis, which consists first in a purely numerical calculation of indices, and secondly in the distribution and combination of the quantities according to laws prescribed by these indices.

We will terminate these Notes by following up in detail the steps through which the engine could compute the Numbers of Bernoulli, this being (in the form in which we shall deduce it) a rather complicated example of its powers. The simplest manner of computing these numbers would be from the direct expansion of

$$
\frac{x}{\epsilon^x-1}=\frac{1}{1+\dfrac{x}{2}+\dfrac{x^2}{2.3}+\dfrac{x^3}{2.3.4}+\&\text{c.}}\tag{1.}
$$

which is in fact a particular case of the development of

$$
\frac{a+bx+cx^2+\&\text{c.}}{a'+b'x+c'x^2+\&\text{c.}}
$$

mentioned in Note E. Or again, we might compute them from the well-known form

$$
\mathrm{B}_{2n-1}=2\,.\,\frac{1.2.3\ldots.2n}{(2\pi)^{2n}}\,.\left\{1+\frac{1}{2^{2n}}+\frac{1}{3^{2n}}+\ldots\right\}\tag{2.}
$$

or from the form

$$
\mathrm{B}_{2n-1}=\frac{\pm2n}{(2^{2n}-1)2^{n-1}}\left\{\begin{aligned}&\frac{1}{2}n^{2n-1}\\&-(n-1)^{2n-1}\left\{1+\frac{1}{2}\cdot\frac{2n}{1}\right\}\\&+(n-2)^{2n-1}\left\{1+\frac{2n}{1}+\frac{1}{2}\cdot\frac{2n.(2n-1}{1.2}\right\}\\&-(n-3)^{2n-1}\left\{\begin{aligned}&1+\frac{2n}{1}+\frac{2n.2n-1}{1.2}+\\&\qquad+\frac{1}{2}\cdot\frac{2n.(2n-1).(2n-2)}{1.2.3}\end{aligned}\right\}\\&+\ldots\qquad\ldots\qquad\ldots\qquad\ldots\end{aligned}\right\}\tag{3.}
$$

or from many others. As however our object is not simplicity or facility of computation, but the illustration of the powers of the engine, we prefer selecting the formula below, marked (8.). This is derived in the following manner:—

If in the equation

$$
\frac{x}{\epsilon^x-1}=1-\frac{x}{2}+\mathrm{B}_1\frac{x^2}{2}+\mathrm{B}_3\frac{x^4}{2.3.4}+\mathrm{B}_5\frac{x^6}{2.3.4.5.6}+\ldots.\tag{4.}
$$

(in which \(\mathrm{B}_1\), \(\mathrm{B}_3\)…, &c. are the Numbers of Bernoulli), we expand the denominator of the first side in powers of \(x\), and then divide both numerator and denominator by \(x\), we shall derive

$$
1=\left(1-\frac{x}{2}+\mathrm{B}_1\frac{x^2}{2}+\mathrm{B}_3\frac{x^4}{2.3.4}+\ldots\right)\left(1+\frac{x}{2}+\frac{x^2}{2.3}+\frac{x^3}{2.3.4}\ldots\right)\tag{5.}
$$

If this latter multiplication be actually performed, we shall have a series of the general form

$$
1+\mathrm{D}_1x+\mathrm{D}_2x^2+\mathrm{D}_3x^3+\ldots\ldots\ldots\ldots\ldots.\tag{6.}
$$

in which we see, first, that all the coefficients of the powers of \(x\) are severally equal to zero; and secondly, that the general form for \(\mathrm{D}_{2n}\) the co-efficient of the \(2n+1\)th *term*, (that is of \(x^{2n}\) any *even* power of \(x\)), is the following:—

$$
\left.\begin{aligned}&\frac{1}{2.3\ldots2n+1}-\frac{1}{2}\cdot\frac{1}{2.3..2n}+\frac{\mathrm{B}_1}{2}\cdot\frac{1}{2.3..2n-1}+\frac{\mathrm{B}_3}{2.3.4}\cdot\frac{1}{2.3..2n-3}+\\&\qquad+\frac{\mathrm{B}_5}{2.3.4.5.6}\cdot\frac{1}{2.3\ldots2n-5}+\ldots+\frac{\mathrm{B}_{2n-1}}{2.3\ldots2n}\cdot1=0\end{aligned}\right\}\tag{7.}
$$

Multiplying every term by (\(2.3\ldots2n\)), we have

$$
\left.\begin{aligned}0=-&\frac{1}{2}\cdot\frac{2n-1}{2n+1}+\mathrm{B}_1\left(\frac{2n}{2}\right)+\mathrm{B}_3\left(\frac{2n.2n-1.2n-2}{2.3.4}\right)+\\&+\mathrm{B}_5\left(\frac{2n.2n-1\ldots\ldots\ldots2n-4}{2.3.4.5.6}\right)+\ldots.+\mathrm{B}_{2n-1}\end{aligned}\right\}\tag{8.}
$$

which it may be convenient to write under the general form:—

$$
0=\mathrm{A}_0+\mathrm{A}_1\mathrm{B}_1+\mathrm{A}_3\mathrm{B}_3+\mathrm{A}_5\mathrm{B}_5+\ldots+\mathrm{B}_{2n-1}\ldots\ldots.\tag{9.}
$$

\(\mathrm{A}_1\), \(\mathrm{A}_3\), &c. being those functions of \(n\) which respectively belong to \(\mathrm{B}_1\), \(\mathrm{B}_3\), &c.

We might have derived a form nearly similar to (8.), from \(\mathrm{D}_{2n-1}\) the coefficient of any *odd* power of \(x\) in (6.); but the general form is a little different for the coefficients of the *odd* powers, and not quite so convenient.

On examining (7.) and (8.), we perceive that, when these formulæ are isolated from (6.) whence they are derived, and considered in themselves separately and independently, \(n\) may be any whole number whatever; although when (7.) occurs *as one of the* \(\mathrm{D}\)'s in (6.), it is obvious that \(n\) is then not arbitrary, but is always a certain function of the *distance of that* \(\mathrm{D}\) *from the beginning*. If that distance be \(=d\), then

<div class="centred">

\(2n+1=d\), and \(n=\dfrac{d-1}{2}\) (for any *even* power of \(x\).)

</div>

<div class="centred">

\(2n=d\), and \(n=\dfrac{d}{2}\) (for any *odd* power of \(x\).)

</div>

It is with the *independent* formula (8.) that we have to do. Therefore it must be remembered that the conditions for the value of \(n\) are now modified, and that \(n\) is a perfectly *arbitrary* whole number. This circumstance, combined with the fact (which we may easily perceive) that whatever \(n\) is, every term of (8.) after the \((n+1)\)th is \(=0\), and that the (\(n+1\))th term itself is always \(=\mathrm{B}_{2n-1}\cdot\frac{1}{1}=\mathrm{B}_{2n-1}\), enables us to find the value (either numerical or algebraical) of any \(n\)th Number of Bernoulli \(\mathrm{B}_{2n-1}\), *in terms of all the preceding ones*, if we but know the values of \(\mathrm{B}_1\), \(\mathrm{B}_3\ldots \mathrm{B}_{2n-3}\). We append to this Note a Diagram and Table, containing the details of the computation for \(\mathrm{B}_7\), (\(\mathrm{B}_1\), \(\mathrm{B}_3\), \(\mathrm{B}_5\) being supposed given).

On attentively considering (8.), we shall likewise perceive that we may derive from it the numerical value of *every* Number of Bernoulli in succession, from the very beginning, *ad infinitum*, by the following series of computations:—

1st Series.—Let \(n=1\), and calculate (8.) for this value of \(n\). The result is \(\mathrm{B}_1\).

2nd Series.—Let \(n=2\). Calculate (8.) for this value of \(n\), substituting the value of \(\mathrm{B}_1\) just obtained. The result is \(\mathrm{B}_3\).

3rd Series.—Let \(n=3\). Calculate (8.) for this value of \(n\), substituting the values of \(\mathrm{B}_1\), \(\mathrm{B}_3\) before obtained. The result is \(\mathrm{B}_5\). And so on, to any extent.

The diagram[^2] represents the columns of the engine when just prepared for computing \(\mathrm{B}_{2n-1}\), (in the case of \(n=4\)); while the table beneath them presents a complete simultaneous view of all the successive changes which these columns then severally pass through in order to perform the computation. (The reader is referred to Note D, for explanations respecting the nature and notation of such tables.)

Six numerical *data* are in this case necessary for making the requisite combinations. These data are 1, 2, \(n(=4)\), \(\mathrm{B}_1\), \(\mathrm{B}_3\), \(\mathrm{B}_5\). Were \(n=5\), the additional datum \(\mathrm{B}_7\) would be needed. Were \(n=6\), the datum \(\mathrm{B}_9\) would be needed; and so on. Thus the actual *number of data* needed will always be \(n+2\), for \(n=n\); and out of these \(n+2\) data, (\(\overline{n+2}-3\)) of them are successive Numbers of Bernoulli. The reason why the Bernoulli Numbers used as data, are nevertheless placed on *Result*-columns in the diagram, is because they may properly be supposed to have been previously computed in succession by the *engine* itself; under which circumstances each \(\mathrm{B}\) will appear as a *result*, previous to being used as a *datum* for computing the succeeding \(\mathrm{B}\). Here then is an instance (of the kind alluded to in Note D.) of the same Variables filling more than one office in turn. It is true that if we consider our computation of \(\mathrm{B}_7\) as a perfectly *isolated* calculation, we may conclude \(\mathrm{B}_1\), \(\mathrm{B}_3\), \(\mathrm{B}_5\) to have been arbitrarily placed on the columns; and it would then perhaps be more consistent to put them on \(\mathrm{V}_4\), \(\mathrm{V}_5\), \(\mathrm{V}_6\) as data and not results. But we are not taking this view. On the contrary, we suppose the engine to be *in the course of* computing the Numbers to an indefinite extent, from the very beginning; and that we merely single out, by way of example, *one amongst* the successive but distinct series' of computations it is thus performing. Where the \(\mathrm{B}\)'s are fractional, it must be understood that they are computed and appear in the notation of *decimal* fractions. Indeed this is a circumstance that should be noticed with reference to all calculations. In any of the examples already given in the translation and in the Notes, some of the *data*, or of the temporary or permanent results, might be fractional, quite as probably as whole numbers. But the arrangements are so made, that the nature of the processes would be the same as for whole numbers.

In the above table and diagram we are not considering the *signs* of any of the \(\mathrm{B}\)'s, merely their numerical magnitude. The engine would bring out the sign for each of them correctly of course, but we cannot enter on *every* additional detail of this kind, as we might wish to do. The circles for the signs are therefore intentionally left blank in the diagram.

Operation-cards 1, 2, 3, 4, 5, 6 prepare \(-\frac{1}{2}\cdot\frac{2n-1}{2n+1}\). Thus, Card 1 multiplies *two* into \(n\), and the three *Receiving* Variable-cards belonging respectively to \(\mathrm{V}_4\), \(\mathrm{V}_5\), \(\mathrm{V}_6\), allow the result \(2n\) to be placed on each of these latter columns (this being a case in which a triple receipt of the result is needed for subsequent purposes); we see that the upper indices of the two Variables used, during Operation 1, remain unaltered.

We shall not go through the details of every operation singly, since the table and diagram sufficiently indicate them; we shall merely notice some few peculiar cases.

By Operation 6, a *positive* quantity is turned into a *negative* quantity, by simply subtracting the quantity from a column which has only zero upon it. (The sign at the top of \(\mathrm{V}_8\) would become—during this process.)

Operation 7 will be unintelligible, unless it be remembered that if we were calculating for \(n=1\) instead of \(n=4\), Operation 6 would have completed the computation of \(\mathrm{B}_1\) itself; in which case the engine, instead of continuing its processes, would have to put \(\mathrm{B}_1\) on \(\mathrm{V}_{21}\); and then either to stop altogether, or to begin Operations 1, 2.…7 all over again for value of \(n(=2)\), in order to enter on the computation of \(\mathrm{B}_3\); (having hovever taken care, previous to this recommencement, to make the number on \(\mathrm{V}_3\) equal to *two*, by the addition of unity to the former \(n=1\) on that column). Now Operation 7 must either bring out a result equal to zero (if \(n=1\)); or a result *greater* than *zero*, as in the present case; and the engine follows the one or the other of the two courses just explained, contingently on the one or the other result of Operation 7. In order fully to perceive the necessity of this *experimental* operation, it is important to keep in mind what was pointed out, that we are not treating a perfectly isolated and independent computation, but one out of a series of antecedent and prospective computations.

Cards 8, 9, 10 produce \(-\frac{1}{2}\cdot\frac{2n-1}{2n+1}+\mathrm{B}_1\frac{2n}{2}\). In Operation 9 we see an example of an upper index which again becomes a value after having passed from preceding values to zero. \(\mathrm{V}_{11}\) has sucessively been \({}^0\mathrm{V}_{11}\), \({}^1\mathrm{V}_{11}\), \({}^2\mathrm{V}_{11}\), \({}^0\mathrm{V}_{11}\), \({}^3\mathrm{V}_{11}\); and, from the nature of the office which \(\mathrm{V}_{11}\) performs in the calculation, its index will continue to go through further changes of the same description, which, if examined, will be found to be regular and periodic.

Card 12 has to perform the same office as Card 7 did in the preceding section; since, if \(n\) had been \(=2\), the 11th operation would have completed the computation of \(\mathrm{B}_3\).

Cards 13 to 20 make \(\mathrm{A}_3\). Since \(\mathrm{A}_{2n-1}\) always consists of \(2n-1\) factors, \(\mathrm{A}_3\) has three factors; and it will be seen that Cards 13, 14, 15, 16 make the second of these factors, and then multiply it with the first; and that 17, 18, 19, 20 make the third factor, and then multiply this with the product of the two former factors.

Card 23 has the office of Cards 11 and 7 to perform, since if \(n\) were \(=3\), the 21st and 22nd operations would complete the computation of \(\mathrm{B}_5\). As our case is \(\mathrm{B}_7\), the computation will continue one more stage; and we must now direct attention to the fact, that in order to compute \(\mathrm{A}_7\) it is merely necessary precisely to repeat the group of Operations 13 to 20; and then, in order to complete the computation of \(\mathrm{B}_7\), to repeat Operations 21, 22.

It will be perceived that every unit added to \(n\) in \(\mathrm{B}_{2n-1}\), entails an additional repetition of operations (13…23) for the computation of \(\mathrm{B}_{2n-1}\). Not only are all the *operations* precisely the same however for every such repetition, but they require to be respectively supplied with numbers from the very *same pairs of columns*; with only the one exception of Operation 21, which will of course need \(\mathrm{B}_5\) (from \(\mathrm{V}_{23}\)) instead of \(\mathrm{B}_3\) (from \(\mathrm{V}_{22}\)). This identity in the *columns* which supply the requisite numbers, must not be confounded with identity in the *values* those columns have upon them and give out to the mill. Most of those values undergo alterations during a performance of the operations (13.…23), and consequently the columns present a new set of values for the *next* performance of (13….23) to work on.

At the termination of the *repetition* of operations (13…23) in computing \(\mathrm{B}_7\), the alterations in the values on the Variables are, that

$$
\begin{aligned}\mathbf{V}_6&=2n-4\text{ instead of }2n-2.\\\mathbf{V}_7&=6\ldots\ldots\ldots\ldots4.\\\mathbf{V}_{10}&=0\ldots\ldots\ldots\ldots1.\\\mathbf{V}_{13}&=\mathrm{A}_0+\mathrm{A}_1\mathrm{B}_1+\mathrm{A}_3\mathrm{B}_3+\mathrm{A}_5\mathrm{B}_5\text{ instead of }\mathrm{A}_0+\mathrm{A}_1\mathrm{B}_1+\mathrm{A}_3\mathrm{B}_3\end{aligned}
$$

In this state the only remaining processes are first: to transfer the value which is on \(\mathrm{V}_{13}\), to \(\mathrm{V}_{24}\); and secondly to reduce \(\mathrm{V}_6\), \(\mathrm{V}_7\), \(\mathrm{V}_{13}\) to zero, and to add[^3] *one* to \(\mathrm{V}_3\), in order that the engine may be ready to commence computing \(\mathrm{B}_9\). Operations 24 and 25 accomplish these purposes. It may be thought anomalous that Operation 25 is represented as leaving the upper index of \(\mathrm{V}_3\) still = unity. But it must be remembered that these indices always begin anew for a separate calculation, and that Operation 25 places upon \(\mathrm{V}_3\) the *first* value *for the new calculation*.

It should be remarked, that when the group (13…23) is *repeated*, changes occur in some of the upper indices during the course of the repetition: for example, \({}^3\mathrm{V}_6\) would become \({}^4\mathrm{V}_6\) and \({}^5\mathrm{V}_6\).

We thus see that when \(n=1\), nine Operation-cards are used; that when \(n=2\), fourteen Operation-cards are used; and that when \(n>2\), twenty-five Operation-cards are used; but that no *more* are needed, however great \(n\) may be; and not only this, but that these same twenty-five cards suffice for the successive computation of all the Numbers from \(\mathrm{B}_1\) to \(\mathrm{B}_{2n-1}\) inclusive. With respect to the number of *Variable*-cards, it will be remembered, from the explanations in previous Notes, that an average of three such cards to each *operation* (not however to each Operation-*card*) is the estimate. According to this the computation of \(\mathrm{B}_1\) will require twenty-seven Variable-cards; \(\mathrm{B}_3\) forty-two such cards; \(\mathrm{B}_5\) seventy-five; and for every succeeding \(\mathrm{B}\) after \(\mathrm{B}_5\), there would be thirty-three additional Variable-cards (since each repetition of the group (13…23) adds eleven to the number of operations required for computing the previous \(\mathrm{B}\)). But we must now explain, that whenever there is a *cycle of operations*, and if these merely require to be supplied with numbers *from the same pairs of columns* and likewise each operation to place its *result* on the *same* column for every repetition of the whole group, the process then admits of a *cycle of Variable-cards* for effecting its purposes. There is obviously much more symmetry and simplicity in the arrangements, when cases do admit of repeating the Variable as well as the Operation-cards. Our present example is of this nature. The only exception to a *perfect identity* in *all* the processes and columns used, for every repetition of Operations (13…23) is, that Operation 21 always requires one of its factors from a new column, and Operation 24 always puts its result on a new column. But as these variations follow the same law at each repetition, (Operation 21 always requiring its factor from a column *one* in advance of that which it used the previous time, and Operation 24 always putting its result on the column *one* in advance of that which received the previous result), they are easily provided for in arranging the recurring group (or cycle) of Variable-cards.

We may here remark that the average estimate of three Variable-cards coming into use to each operation, is not to be taken as an absolutely and literally correct amount for all cases and circumstances. Many special circumstances, either in the nature of a problem, or in the arrangements of the engine under certain contingencies, influence and modify this average to a greater or less extent. But it is a very safe and correct *general* rule to go upon. In the preceding case it will give us seventy-five Variable-cards as the total number which will be necessary for computing any \(\mathrm{B}\) after \(\mathrm{B}_3\). This is very nearly the precise amount really used, but we cannot here enter into the minutiæ of the few particular circumstances which occur in this example (as indeed at some one stage or other of probably most computations) to modify slightly this number.

It will be obvious that the very *same* seventy-five Variable-cards may be repeated for the computation of every succeeding Number, just on the same principle as admits of the repetition of the thirty-three Variable-cards of Operations (13…23) in the computation of any *one* Number. Thus there will be a *cycle of a cycle* of Variable-cards.

If we now apply the notation for cycles, as explained in Note E, we may express the operations for computing the Numbers of Bernoulli in the following manner:—

<div class="cycles">

(1…7), (24, 25)<span class="lead"></span><span class="b">gives \(\mathrm{B}_1\)</span><span class="k">= 1st number;</span><span class="v">(\(n\) being = 1).</span>

(1…7), (8…12), (24, 25)<span class="lead"></span><span class="b">\(\mathrm{B}_3\)</span><span class="k">= 2nd <span class="dd">.....</span>;</span><span class="v">(\(n\) <span class="dd">....</span> = 2).</span>

(1…7), (8…12), (13…23), (24, 25)<span class="lead"></span><span class="b">\(\mathrm{B}_5\)</span><span class="k">= 3rd <span class="dd">.....</span>;</span><span class="v">(\(n\) <span class="dd">....</span> = 3).</span>

(1…7), (8…12), 2(13…23), (24, 25)<span class="lead"></span><span class="b">\(\mathrm{B}_7\)</span><span class="k">= 4th <span class="dd">.....</span>;</span><span class="v">(\(n\) <span class="dd">....</span> = 4).</span>

<p class="dotline"></p>

<p class="dotline"></p>

(1…7),(8…12),\(\Sigma(+1)^{n-2}\)(13…23),(24, 25)<span class="lead"></span><span class="b">\(\mathrm{B}_{2n-1}\)</span><span class="k">= \(n\)th <span class="dd">.....</span>;</span><span class="v">(\(n\) <span class="dd">....</span> = \(n\)).</span>

</div>

Again,

$$
(1\ldots7),(24,25),\underset{\text{limits 1 to }n}{\Sigma(+1)^n}\left\{(1\ldots7),(8\ldots12),\underset{\text{limits 0 to }(n+2)}{\Sigma(n+2)(13\ldots23)},(24,25)\right\}
$$

represents the total operations for computing every number in succession, from \(\mathrm{B}_1\) to \(\mathrm{B}_{2n-1}\) inclusive.

In this formula we see a *varying cycle* of the *first* order, and an ordinary cycle of the *second* order. The latter cycle in this case includes in it the varying cycle.

On inspecting the ten Working-Variables of the diagram, it will be perceived, that although the *value* on any one of them (excepting \(\mathrm{V}_4\) and \(\mathrm{V}_5\)) goes through a series of changes, the *office* which each performs is in this calculation *fixed* and *invariable*. Thus \(\mathrm{V}_6\) always prepares the *numerators* of the factors of any \(\mathrm{A}\); \(\mathrm{V}_7\) the *denominators*. \(\mathrm{V}_8\) always receives the \((2n-3)\)th factor of \(\mathrm{A}_{2n-1}\), and \(\mathrm{V}_9\) the \((2n-1)\)th. \(\mathrm{V}_{10}\) always decides which of two courses the succeeding processes are to follow, by feeling for the value of \(n\) through means of a subtraction; and so on; but we shall not enumerate further. It is desirable in all calculations, so to arrange the processes, that the *offices* performed by the Variables may be as uniform and fixed as possible.

Supposing that it was desired not only to tabulate \(\mathrm{B}_1\), \(\mathrm{B}_3\), &c., but \(\mathrm{A}_0\), \(\mathrm{A}_1\), &c.; we have only then to appoint another series of Variables, \(\mathrm{V}_{41}\), \(\mathrm{V}_{42}\), &c., for receiving these latter results as they are successively produced upon \(\mathrm{V}_{11}\). Or again, we may, instead of this, or in addition to this second series of results, wish to tabulate the value of each successive *total* term of the series (8), viz: \(\mathrm{A}_0\), \(\mathrm{A}_1\mathrm{B}_1\), \(\mathrm{A}_3\mathrm{B}_3\), &c. We have then merely to multiply each \(\mathrm{B}\) with each corresponding \(\mathrm{A}\), as produced; and to place these successive products on Result-columns appointed for the purpose.

The formula (8.) is interesting in another point of view. It is one particular case of the general Integral of the following Equation of Mixed Differences:—

$$
\frac{d^2}{dx^2}\left(z_{n+1}x^{2n+2}\right)=(2n+1)(2n+2)z^nx^{2n}
$$

for certain special suppositions respecting \(z\), \(x\) and \(n\).

The *general* integral itself is of the form,

$$
z_n=f(n)\cdot x+f_1(n)+f_2(n)\cdot x^{-1}.+f_3(n)\cdot x^{-3}+\ldots
$$

and it is worthy of remark, that the engine might (in a manner more or less similar to the preceding) calculate the value of this formula upon most *other* hypotheses for the functions in the integral, with as much, or (in many cases) with more, ease than it can formula (8.).

<p class="sig">A. L. L.</p>

[^1]: The engine cannot of course compute limits for perfectly *simple* and *uncompounded* functions, except in this manner. It is obvious that it has no power of representing or of manipulating with any but *finite* increments or decrements; and consequently that wherever the computation of limits (or of any other functions) depends upon the *direct* introduction of quantities which either increase or decrease *indefinitely*, we are absolutely beyond the sphere of its powers. Its nature and arrangements are remarkably adapted for taking into account all *finite* increments or decrements (however small or large), and for developing the true and logical modifications of form or value dependent upon differences of this nature. The engine may indeed be considered as including the whole Calculus of Finite Differences; many of whose theorems would be especially and beautifully fitted for development by its processes, and would offer peculiarly interesting considerations. We may mention, as an example, the calculation of the Numbers of Bernoulli by means of the *Differences of Nothing*.

[^2]: See the diagram at the end of these Notes.

[^3]: It is interesting to observe, that so complicated a case as this calculation of the Bernoullian Numbers, nevertheless, presents a remarkable simplicity in one respect; viz., that during the processes for the computation of *millions* of these Numbers, no other arbitrary modification would be requisite in the arrangements, excepting the above simple and uniform provision for causing one of the data periodically to receive the finite increment unity.
