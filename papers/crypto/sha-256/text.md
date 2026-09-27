## 2.2.1 Parameters

The following parameters are used in the secure hash algorithm specifications in this Standard.

<span class="sym">\(a, b, c, \ldots, h\)</span>Working variables that are the \(w\)-bit words used in the computation of the hash values, \(H^{(i)}\).

<span class="sym">\(H^{(i)}\)</span>The <i>i</i><sup>th</sup> hash value. \(H^{(0)}\) is the <i>initial</i> hash value; \(H^{(N)}\) is the <i>final</i> hash value and is used to determine the message digest.

<span class="sym">\(H_j^{(i)}\)</span>The <i>j</i><sup>th</sup> word of the <i>i</i><sup>th</sup> hash value, where \(H_0^{(i)}\) is the left-most word of hash value \(i\).

<span class="sym">\(K_t\)</span>Constant value to be used for the iteration \(t\) of the hash computation.

<span class="sym">\(k\)</span>Number of zeroes appended to a message during the padding step.

<span class="sym">\(\ell\)</span>Length of the message, \(M\), in bits.

<span class="sym">\(m\)</span>Number of bits in a message block, \(M^{(i)}\).

<span class="sym">\(M\)</span>Message to be hashed.

<span class="sym">\(M^{(i)}\)</span>Message block \(i\), with a size of \(m\) bits.

<span class="sym">\(M_j^{(i)}\)</span>The <i>j</i><sup>th</sup> word of the <i>i</i><sup>th</sup> message block, where \(M_0^{(i)}\) is the left-most word of message block \(i\).

<span class="sym">\(n\)</span>Number of bits to be rotated or shifted when a word is operated upon.

<span class="sym">\(N\)</span>Number of blocks in the padded message.

<span class="sym">\(T\)</span>Temporary \(w\)-bit word used in the hash computation.

<span class="sym">\(w\)</span>Number of bits in a word.

<span class="sym">\(W_t\)</span>The <i>t</i><sup>th</sup> \(w\)-bit word of the message schedule.

## 2.2.2 Symbols and Operations

The following symbols are used in the secure hash algorithm specifications; each operates on \(w\)-bit words.

<span class="sym">\(\wedge\)</span>Bitwise AND operation.

<span class="sym">\(\vee\)</span>Bitwise OR (“inclusive-OR”) operation.

<span class="sym">\(\oplus\)</span>Bitwise XOR (“exclusive-OR”) operation.

<span class="sym">\(\neg\)</span>Bitwise complement operation.

<span class="sym">\(+\)</span>Addition modulo \(2^w\).

<span class="sym">\(\ll\)</span>Left-shift operation, where \(x \ll n\) is obtained by discarding the left-most \(n\) bits of the word \(x\) and then padding the result with \(n\) zeroes on the right.

<span class="sym">\(\gg\)</span>Right-shift operation, where \(x \gg n\) is obtained by discarding the right-most \(n\) bits of the word \(x\) and then padding the result with \(n\) zeroes on the left.

The following operations are used in the secure hash algorithm specifications:

<span class="sym">\(\boldsymbol{\mathit{ROTL}^{\,n}(x)}\)</span>The <i>rotate left</i> (circular left shift) operation, where \(x\) is a \(w\)-bit word and \(n\) is an integer with \(0 \le n < w\), is defined by \(\mathit{ROTL}^{\,n}(x)=(x \ll n) \vee (x \gg w - n)\).

<span class="sym">\(\boldsymbol{\mathit{ROTR}^{\,n}(x)}\)</span>The <i>rotate right</i> (circular right shift) operation, where \(x\) is a \(w\)-bit word and \(n\) is an integer with \(0 \le n < w\), is defined by \(\mathit{ROTR}^{\,n}(x)=(x \gg n) \vee (x \ll w - n)\).

<span class="sym">\(\boldsymbol{\mathit{SHR}^{\,n}(x)}\)</span>The right shift operation, where \(x\) is a \(w\)-bit word and \(n\) is an integer with \(0 \le n < w\), is defined by \(\mathit{SHR}^{\,n}(x)=x \gg n\).

## 4.1.2 SHA-224 and SHA-256 Functions

SHA-224 and SHA-256 both use six logical functions, where <i>each function operates on 32-bit words</i>, which are represented as \(x\), \(y\), and \(z\). The result of each function is a new 32-bit word.

$$
\begin{aligned}
\mathit{Ch}(x,y,z) &= (x\wedge y)\oplus(\neg x\wedge z) && (4.2)\\
\mathit{Maj}(x,y,z) &= (x\wedge y)\oplus(x\wedge z)\oplus(y\wedge z) && (4.3)\\[.6em]
\textstyle\sum\nolimits_0^{\{256\}}(x) &= \mathit{ROTR}^{\,2}(x)\oplus \mathit{ROTR}^{\,13}(x)\oplus \mathit{ROTR}^{\,22}(x) && (4.4)\\
\textstyle\sum\nolimits_1^{\{256\}}(x) &= \mathit{ROTR}^{\,6}(x)\oplus \mathit{ROTR}^{\,11}(x)\oplus \mathit{ROTR}^{\,25}(x) && (4.5)\\
\sigma_0^{\{256\}}(x) &= \mathit{ROTR}^{\,7}(x)\oplus \mathit{ROTR}^{\,18}(x)\oplus \mathit{SHR}^{\,3}(x) && (4.6)\\
\sigma_1^{\{256\}}(x) &= \mathit{ROTR}^{\,17}(x)\oplus \mathit{ROTR}^{\,19}(x)\oplus \mathit{SHR}^{\,10}(x) && (4.7)
\end{aligned}
$$

## 4.2.2 SHA-224 and SHA-256 Constants

SHA-224 and SHA-256 use the same sequence of sixty-four constant 32-bit words, \(K_0^{\{256\}}, K_1^{\{256\}}, \ldots, K_{63}^{\{256\}}\). These words represent the first thirty-two bits of the fractional parts of the cube roots of the first sixty-four prime numbers. In hex, these constant words are (from left to right)

<div class="consts"><span>428a2f98</span><span>71374491</span><span>b5c0fbcf</span><span>e9b5dba5</span><span>3956c25b</span><span>59f111f1</span><span>923f82a4</span><span>ab1c5ed5</span><span>d807aa98</span><span>12835b01</span><span>243185be</span><span>550c7dc3</span><span>72be5d74</span><span>80deb1fe</span><span>9bdc06a7</span><span>c19bf174</span><span>e49b69c1</span><span>efbe4786</span><span>0fc19dc6</span><span>240ca1cc</span><span>2de92c6f</span><span>4a7484aa</span><span>5cb0a9dc</span><span>76f988da</span><span>983e5152</span><span>a831c66d</span><span>b00327c8</span><span>bf597fc7</span><span>c6e00bf3</span><span>d5a79147</span><span>06ca6351</span><span>14292967</span><span>27b70a85</span><span>2e1b2138</span><span>4d2c6dfc</span><span>53380d13</span><span>650a7354</span><span>766a0abb</span><span>81c2c92e</span><span>92722c85</span><span>a2bfe8a1</span><span>a81a664b</span><span>c24b8b70</span><span>c76c51a3</span><span>d192e819</span><span>d6990624</span><span>f40e3585</span><span>106aa070</span><span>19a4c116</span><span>1e376c08</span><span>2748774c</span><span>34b0bcb5</span><span>391c0cb3</span><span>4ed8aa4a</span><span>5b9cca4f</span><span>682e6ff3</span><span>748f82ee</span><span>78a5636f</span><span>84c87814</span><span>8cc70208</span><span>90befffa</span><span>a4506ceb</span><span>bef9a3f7</span><span>c67178f2</span></div>

## 5.1.1 SHA-1, SHA-224 and SHA-256

Suppose that the length of the message, \(M\), is \(\ell\) bits. Append the bit “<code>1</code>” to the end of the message, followed by \(k\) zero bits, where \(k\) is the smallest, non-negative solution to the equation \(\ell + 1 + k \equiv 448 \bmod 512\). Then append the 64-bit block that is equal to the number \(\ell\) expressed using a binary representation. For example, the (8-bit ASCII) message “<b>abc</b>” has length \(8 \times 3 = 24\), so the message is padded with a one bit, then \(448 - (24 + 1) = 423\) zero bits, and then the message length, to become the 512-bit padded message

$$
\underbrace{\texttt{01100001}}_{\text{“a”}}\;\;
\underbrace{\texttt{01100010}}_{\text{“b”}}\;\;
\underbrace{\texttt{01100011}}_{\text{“c”}}\;\;
\texttt{1}\;\;
\overbrace{\texttt{00…00}}^{423}\;\;
\overbrace{\texttt{00…0}\underbrace{\texttt{11000}}_{\ell\,=\,24}}^{64}
$$

The length of the padded message should now be a multiple of 512 bits.

## 5.2.1 SHA-1, SHA-224 and SHA-256

For SHA-1, SHA-224 and SHA-256, the message and its padding are parsed into \(N\) 512-bit blocks, \(M^{(1)}, M^{(2)}, \ldots, M^{(N)}\). Since the 512 bits of the input block may be expressed as sixteen 32-bit words, the first 32 bits of message block \(i\) are denoted \(M_0^{(i)}\), the next 32 bits are \(M_1^{(i)}\), and so on up to \(M_{15}^{(i)}\).

## 5.3.3 SHA-256

For SHA-256, the initial hash value, \(H^{(0)}\), shall consist of the following eight 32-bit words, in hex:

$$
\begin{aligned}
H_0^{(0)} &= \texttt{6a09e667}\\
H_1^{(0)} &= \texttt{bb67ae85}\\
H_2^{(0)} &= \texttt{3c6ef372}\\
H_3^{(0)} &= \texttt{a54ff53a}\\
H_4^{(0)} &= \texttt{510e527f}\\
H_5^{(0)} &= \texttt{9b05688c}\\
H_6^{(0)} &= \texttt{1f83d9ab}\\
H_7^{(0)} &= \texttt{5be0cd19}
\end{aligned}
$$

These words were obtained by taking the first thirty-two bits of the fractional parts of the square roots of the first eight prime numbers.

## 6.2 SHA-256

SHA-256 may be used to hash a message, \(M\), having a length of \(\ell\) bits, where \(0 \le \ell < 2^{64}\). The algorithm uses 1) a message schedule of sixty-four 32-bit words, 2) eight working variables of 32 bits each, and 3) a hash value of eight 32-bit words. The final result of SHA-256 is a 256-bit message digest.

The words of the message schedule are labeled \(W_0, W_1, \ldots, W_{63}\). The eight working variables are labeled \(\boldsymbol{a}\), \(\boldsymbol{b}\), \(\boldsymbol{c}\), \(\boldsymbol{d}\), \(\boldsymbol{e}\), \(\boldsymbol{f}\), \(\boldsymbol{g}\), and \(\boldsymbol{h}\). The words of the hash value are labeled \(H_0^{(i)}, H_1^{(i)}, \ldots, H_7^{(i)}\), which will hold the initial hash value, \(H^{(0)}\), replaced by each successive intermediate hash value (after each message block is processed), \(H^{(i)}\), and ending with the final hash value, \(H^{(N)}\). SHA-256 also uses two temporary words, \(T_1\) and \(T_2\).

## 6.2.1 SHA-256 Preprocessing

1. Set the initial hash value, \(H^{(0)}\), as specified in Sec. 5.3.3.
2. The message is padded and parsed as specified in Section 5.

## 6.2.2 SHA-256 Hash Computation

The SHA-256 hash computation uses functions and constants previously defined in Sec. 4.1.2 and Sec. 4.2.2, respectively. Addition (+) is performed modulo \(2^{32}\).

Each message block, \(M^{(1)}, M^{(2)}, \ldots, M^{(N)}\), is processed in order, using the following steps:

<span class="in0"></span>For \(i\)=1 to \(N\):

<span class="in0"></span>{

<span class="in1"></span>1. Prepare the message schedule, \(\{W_t\}\):

$$
\small W_t=\begin{cases}
M_t^{(i)} & \hspace{-.5em}0\le t\le 15\\[.4em]
\sigma_1^{\{256\}}(W_{t-2})+W_{t-7}+\sigma_0^{\{256\}}(W_{t-15})+W_{t-16} & \hspace{-.5em}16\le t\le 63
\end{cases}
$$

<span class="in1"></span>2. Initialize the eight working variables, \(\boldsymbol{a}\), \(\boldsymbol{b}\), \(\boldsymbol{c}\), \(\boldsymbol{d}\), \(\boldsymbol{e}\), \(\boldsymbol{f}\), \(\boldsymbol{g}\), and <span class="nw">\(\boldsymbol{h}\),</span> with the (<i>i</i>-1)<sup>st</sup> hash value:

$$
\begin{aligned}
a &= H_0^{(i-1)}\\
b &= H_1^{(i-1)}\\
c &= H_2^{(i-1)}\\
d &= H_3^{(i-1)}\\
e &= H_4^{(i-1)}\\
f &= H_5^{(i-1)}\\
g &= H_6^{(i-1)}\\
h &= H_7^{(i-1)}
\end{aligned}
$$

<span class="in1"></span>3. For \(t\)=0 to 63:

$$
\begin{array}{l}
\{\\
\quad T_1 = h + \textstyle\sum\nolimits_1^{\{256\}}(e) + \mathit{Ch}(e,f,g) + K_t^{\{256\}} + W_t\\
\quad T_2 = \textstyle\sum\nolimits_0^{\{256\}}(a) + \mathit{Maj}(a,b,c)\\
\quad h = g\\
\quad g = f\\
\quad f = e\\
\quad e = d + T_1\\
\quad d = c\\
\quad c = b\\
\quad b = a\\
\quad a = T_1 + T_2\\
\}
\end{array}
$$

<span class="in1"></span>4. Compute the <i>i</i><sup>th</sup> intermediate hash value \(H^{(i)}\):

$$
\begin{aligned}
H_0^{(i)} &= a + H_0^{(i-1)}\\
H_1^{(i)} &= b + H_1^{(i-1)}\\
H_2^{(i)} &= c + H_2^{(i-1)}\\
H_3^{(i)} &= d + H_3^{(i-1)}\\
H_4^{(i)} &= e + H_4^{(i-1)}\\
H_5^{(i)} &= f + H_5^{(i-1)}\\
H_6^{(i)} &= g + H_6^{(i-1)}\\
H_7^{(i)} &= h + H_7^{(i-1)}
\end{aligned}
$$

<span class="in0"></span>}

After repeating steps one through four a total of \(N\) times (i.e., after processing \(M^{(N)}\)), the resulting 256-bit message digest of the message, \(M\), is

$$H_0^{(N)} \,\|\, H_1^{(N)} \,\|\, H_2^{(N)} \,\|\, H_3^{(N)} \,\|\, H_4^{(N)} \,\|\, H_5^{(N)} \,\|\, H_6^{(N)} \,\|\, H_7^{(N)}$$
