## 3.4 The State

Internally, the algorithms for the AES block ciphers are performed on a two-dimensional (four-by-four) array of bytes called the <i>state</i>. In the state array, denoted by <span class="nw">\(s\),</span> each individual byte has two indices: a row index \(r\) in the range \(0 \le r < 4\) and a column index \(c\) in the range <span class="nw">\(0 \le c < 4\).</span> An individual byte of the state is denoted by either \(s_{r,c}\) or <span class="nw">\(s[r,c]\).</span>

In the specifications for the AES block cipher algorithms in Section 5, the first step is to copy the input array of bytes \(\mathit{in}_0,\ \mathit{in}_1,\ \ldots,\ \mathit{in}_{15}\) to the state array \(s\) as follows:

$$s[r,c] = \mathit{in}[r+4c] \quad \text{for } 0 \le r < 4 \text{ and } 0 \le c < 4. \tag{3.6}$$

A sequence of transformations is then applied to the state array, after which its final value is copied to the output array of bytes \(\mathit{out}_0,\ \mathit{out}_1,\ \ldots,\ \mathit{out}_{15}\) as follows:

$$\mathit{out}[r+4c] = s[r,c] \quad \text{for } 0 \le r < 4 \text{ and } 0 \le c < 4. \tag{3.7}$$

The correspondence between the indices of the input and output with the indices of the state array is illustrated in Fig. 1.

::: figure state

<span class="cap">Figure 1. State array input and output</span>

## 3.5 Arrays of Words

A <i>word</i> is a sequence of four bytes; a block consists of four words. The four columns of state array \(s\) are interpreted as an array \(v\) of four words as follows, in the notation of Fig. 1:

$$\small v_0 = \begin{pmatrix}s_{0,0}\\s_{1,0}\\s_{2,0}\\s_{3,0}\end{pmatrix},\quad v_1 = \begin{pmatrix}s_{0,1}\\s_{1,1}\\s_{2,1}\\s_{3,1}\end{pmatrix},\quad v_2 = \begin{pmatrix}s_{0,2}\\s_{1,2}\\s_{2,2}\\s_{3,2}\end{pmatrix},\quad v_3 = \begin{pmatrix}s_{0,3}\\s_{1,3}\\s_{2,3}\\s_{3,3}\end{pmatrix}. \tag{3.8}$$

Thus, the column index \(c\) of \(s\) becomes the index for <span class="nw">\(v\),</span> and the row index \(r\) of \(s\) becomes the index for the four bytes in each word.

Given a one-dimensional array \(u\) of words, \(u[i]\) denotes the word that is indexed by <span class="nw">\(i\),</span> and the sequence of four words \(u[i], u[i+1], u[i+2], u[i+3]\) is denoted by <span class="nw">\(u[i..i+3]\).</span>

## 4.2 Multiplication in GF(2<sup>8</sup>)

The symbol \(\bullet\) denotes multiplication in <span class="nw">\(\mathrm{GF}\big(2^8\big)\).</span> Conceptually, this multiplication is defined on two bytes in two steps: 1) the two polynomials that represent the bytes are multiplied as polynomials, and 2) the resulting polynomial is reduced modulo the following fixed polynomial:

$$m(x) = x^8 + x^4 + x^3 + x + 1. \tag{4.3}$$

Within both steps, the individual coefficients of the polynomials are reduced modulo 2.

Thus, if \(b(x)\) and \(c(x)\) represent bytes \(b\) and <span class="nw">\(c\),</span> then \(b \bullet c\) is represented by the following modular reduction of their product as polynomials:

$$b(x)c(x) \quad \bmod m(x). \tag{4.4}$$

The modular reduction by \(m(x)\) may be applied to intermediate steps in the calculation of <span class="nw">\(b(x)c(x)\);</span> consequently, it is useful to consider the special case that \(c(x) = x\) (i.e., <span class="nw">\(c = \{\texttt{02}\}\)).</span> In particular, the product \(b \bullet \{\texttt{02}\}\) can be expressed as a function of <span class="nw">\(b\),</span> denoted by <span class="sc">xTimes</span><span class="nw">\((b)\),</span> as follows:

$$
\small \text{{\footnotesize X}T{\footnotesize IMES}}(b) = \begin{cases}
\{b_6\; b_5\; b_4\; b_3\; b_2\; b_1\; b_0\; 0\} & \text{if } b_7 = 0\\
\{b_6\; b_5\; b_4\; b_3\; b_2\; b_1\; b_0\; 0\} \oplus \{0\;0\;0\;1\;1\;0\;1\;1\} & \text{if } b_7 = 1.
\end{cases} \tag{4.5}
$$

Multiplication by higher powers of \(x\) (such as <span class="nw">\(\{\texttt{04}\}\),</span> <span class="nw">\(\{\texttt{08}\}\),</span> and <span class="nw">\(\{\texttt{10}\}\))</span> can be implemented by the repeated application of <span class="sc">xTimes</span>(). For example, let <span class="nw">\(b = \{\texttt{57}\}\):</span>

$$
\begin{aligned}
\{\texttt{57}\} \bullet \{\texttt{01}\} &= \{\texttt{57}\}\\
\{\texttt{57}\} \bullet \{\texttt{02}\} &= \text{{\footnotesize X}T{\footnotesize IMES}}(\{\texttt{57}\}) = \{\texttt{ae}\}\\
\{\texttt{57}\} \bullet \{\texttt{04}\} &= \text{{\footnotesize X}T{\footnotesize IMES}}(\{\texttt{ae}\}) = \{\texttt{47}\}\\
\{\texttt{57}\} \bullet \{\texttt{08}\} &= \text{{\footnotesize X}T{\footnotesize IMES}}(\{\texttt{47}\}) = \{\texttt{8e}\}\\
\{\texttt{57}\} \bullet \{\texttt{10}\} &= \text{{\footnotesize X}T{\footnotesize IMES}}(\{\texttt{8e}\}) = \{\texttt{07}\}\\
\{\texttt{57}\} \bullet \{\texttt{20}\} &= \text{{\footnotesize X}T{\footnotesize IMES}}(\{\texttt{07}\}) = \{\texttt{0e}\}\\
\{\texttt{57}\} \bullet \{\texttt{40}\} &= \text{{\footnotesize X}T{\footnotesize IMES}}(\{\texttt{0e}\}) = \{\texttt{1c}\}\\
\{\texttt{57}\} \bullet \{\texttt{80}\} &= \text{{\footnotesize X}T{\footnotesize IMES}}(\{\texttt{1c}\}) = \{\texttt{38}\}.
\end{aligned} \tag{4.6}
$$

These products facilitate the computation of any multiple of <span class="nw">\(\{\texttt{57}\}\).</span> For example, because \(\{\texttt{13}\} = \{\texttt{10}\} \oplus \{\texttt{02}\} \oplus \{\texttt{01}\}\), it follows that

$$
\begin{aligned}\{\texttt{57}\} \bullet \{\texttt{13}\} &= \{\texttt{57}\} \bullet (\{\texttt{01}\} \oplus \{\texttt{02}\} \oplus \{\texttt{10}\})\\ &= \{\texttt{57}\} \oplus \{\texttt{ae}\} \oplus \{\texttt{07}\}\\ &= \{\texttt{fe}\}.\end{aligned} \tag{4.7}
$$

## 5. Algorithm Specifications

The general function for executing AES-128, AES-192, or AES-256 is denoted by <span class="sc">Cipher</span>(); its inverse is denoted by <span class="sc">InvCipher</span>().[^2]

The core of the algorithms for <span class="sc">Cipher</span>() and <span class="sc">InvCipher</span>() is a sequence of fixed transformations of the state called a <i>round</i>. Each round requires an additional input called the <i>round key</i>; the round key is a block that is usually represented as a sequence of four words (i.e., 16 bytes).

An expansion routine, denoted by <span class="sc">KeyExpansion</span>(), takes the block cipher key as input and generates the round keys as output. In particular, the input to <span class="sc">KeyExpansion</span>() is represented as an array of words, denoted by <i>key</i>, and the output is an expanded array of words, denoted by <i>w</i>, called the <i>key schedule</i>.

The block ciphers AES-128, AES-192, and AES-256 differ in three respects: 1) the length of the key; 2) the number of rounds, which determines the size of the required key schedule; and 3) the specification of the recursion within <span class="sc">KeyExpansion</span>(). For each algorithm, the number of rounds is denoted by <i>Nr</i>, and the number of words of the key is denoted by <i>Nk</i>. (The number of words in the state is denoted by <i>Nb</i> for Rijndael in general; in this Standard, <span class="nw">\(\mathit{Nb} = 4\).)</span> The specific values of <i>Nk</i>, <i>Nb</i>, and <i>Nr</i> are given in Table 3. No other configurations of Rijndael conform to this Standard.

For implementation issues relating to the key length, block size, and number of rounds, see Section 6.3.

<span class="cap"><b>Table 3. Key-Block-Round Combinations</b></span>

<table class="t3"><tr><td></td><th colspan="2">Key length</th><th colspan="2">Block size</th><th>Number of rounds</th></tr><tr class="u"><td></td><td><i>Nk</i></td><td>(in bits)</td><td><i>Nb</i></td><td>(in bits)</td><td><i>Nr</i></td></tr><tr><th>AES-128</th><td>4</td><td>128</td><td>4</td><td>128</td><td>10</td></tr><tr><th>AES-192</th><td>6</td><td>192</td><td>4</td><td>128</td><td>12</td></tr><tr><th>AES-256</th><td>8</td><td>256</td><td>4</td><td>128</td><td>14</td></tr></table>

The three inputs to <span class="sc">Cipher</span>() are: 1) the data input <i>in</i>, which is a block represented as a linear array of 16 bytes; 2) the number of rounds <i>Nr</i> for the instance; and 3) the round keys. Thus,

$$
\small\begin{aligned}
\text{AES-128}(\mathit{in},\mathit{key}) &= \text{C{\footnotesize IPHER}}(\mathit{in},10,\text{K{\footnotesize EY}E{\footnotesize XPANSION}}(\mathit{key}))\\
\text{AES-192}(\mathit{in},\mathit{key}) &= \text{C{\footnotesize IPHER}}(\mathit{in},12,\text{K{\footnotesize EY}E{\footnotesize XPANSION}}(\mathit{key}))\\
\text{AES-256}(\mathit{in},\mathit{key}) &= \text{C{\footnotesize IPHER}}(\mathit{in},14,\text{K{\footnotesize EY}E{\footnotesize XPANSION}}(\mathit{key})).
\end{aligned} \tag{5.1}
$$

The inverse permutations are defined by replacing <span class="sc">Cipher</span>() with <span class="sc">InvCipher</span>() in Eq. 5.1.

[^2]: Informally, these functions are sometimes called “encryption” and “decryption,” but neutral terminology is appropriate because there are other applications of block ciphers besides encryption.

The specifications of <span class="sc">Cipher</span>(), <span class="sc">KeyExpansion</span>(), and <span class="sc">InvCipher</span>() are given in Sections 5.1, 5.2, and 5.3, respectively.

## 5.1 <span class="sc">Cipher</span>()

The rounds in the specification of <span class="sc">Cipher</span>() are composed of the following four byte-oriented transformations on the state:

- <span class="sc">SubBytes</span>() applies a substitution table (S-box) to each byte.
- <span class="sc">ShiftRows</span>() shifts rows of the state array by different offsets.
- <span class="sc">MixColumns</span>() mixes the data within each column of the state array.
- <span class="sc">AddRoundKey</span>() combines a round key with the state.

The four transformations are specified in Sections 5.1.1–5.1.4. In those specifications, the transformed bit, byte, or block is denoted by appending the symbol \({}'\) as a superscript on the original variable \(\big(\text{i.e., by } b_i',\ b',\ s_{i,j}',\ \text{or } s'\big)\).

The round keys for <span class="sc">AddRoundKey</span>() are generated by <span class="sc">KeyExpansion</span>(), which is specified in Section 5.2. In particular, the key schedule is represented as an array \(w\) of \(4 * (\mathit{Nr}+1)\) words.

<span class="sc">Cipher</span>() is specified in the pseudocode in Alg. 1.

<span class="ah"><b>Algorithm 1</b> Pseudocode for <span class="sc">Cipher</span>()</span>

<span class="ln">1:</span><span class="i0"></span>\(\textbf{procedure}\ \text{C{\footnotesize IPHER}}(\mathit{in},\mathit{Nr},w)\)

<span class="ln">2:</span><span class="i1"></span>\(\mathit{state} \leftarrow \mathit{in}\)<span class="cm">\(\triangleright\) See Sec. 3.4</span>

<span class="ln">3:</span><span class="i1"></span>\(\mathit{state} \leftarrow \text{A{\footnotesize DD}R{\footnotesize OUND}K{\footnotesize EY}}(\mathit{state},w[0..3])\)<span class="cm">\(\triangleright\) See Sec. 5.1.4</span>

<span class="ln">4:</span><span class="i1"></span>\(\textbf{for}\ \mathit{round}\ \textbf{from}\ 1\ \textbf{to}\ \mathit{Nr}-1\ \textbf{do}\)

<span class="ln">5:</span><span class="i2"></span>\(\mathit{state} \leftarrow \text{S{\footnotesize UB}B{\footnotesize YTES}}(\mathit{state})\)<span class="cm">\(\triangleright\) See Sec. 5.1.1</span>

<span class="ln">6:</span><span class="i2"></span>\(\mathit{state} \leftarrow \text{S{\footnotesize HIFT}R{\footnotesize OWS}}(\mathit{state})\)<span class="cm">\(\triangleright\) See Sec. 5.1.2</span>

<span class="ln">7:</span><span class="i2"></span>\(\mathit{state} \leftarrow \text{M{\footnotesize IX}C{\footnotesize OLUMNS}}(\mathit{state})\)<span class="cm">\(\triangleright\) See Sec. 5.1.3</span>

<span class="ln">8:</span><span class="i2"></span>\(\mathit{state} \leftarrow \text{A{\footnotesize DD}R{\footnotesize OUND}K{\footnotesize EY}}(\mathit{state},w[4*\mathit{round}..4*\mathit{round}+3])\)

<span class="ln">9:</span><span class="i1"></span>\(\textbf{end for}\)

<span class="ln">10:</span><span class="i1"></span>\(\mathit{state} \leftarrow \text{S{\footnotesize UB}B{\footnotesize YTES}}(\mathit{state})\)

<span class="ln">11:</span><span class="i1"></span>\(\mathit{state} \leftarrow \text{S{\footnotesize HIFT}R{\footnotesize OWS}}(\mathit{state})\)

<span class="ln">12:</span><span class="i1"></span>\(\mathit{state} \leftarrow \text{A{\footnotesize DD}R{\footnotesize OUND}K{\footnotesize EY}}(\mathit{state},w[4*\mathit{Nr}..4*\mathit{Nr}+3])\)

<span class="ln">13:</span><span class="i1"></span>\(\textbf{return}\ \mathit{state}\)<span class="cm">\(\triangleright\) See Sec. 3.4</span>

<span class="ln">14:</span><span class="i0"></span>\(\textbf{end procedure}\)

The first step (Line 2) is to copy the input into the state array using the conventions from Sec. 3.4. After an initial round key addition (Line 3), the state array is transformed by <i>Nr</i> applications of the round function (Lines 4–12); the final round (Lines 10–12) differs in that the <span class="sc">MixColumns</span>() transformation is omitted. The final state is then returned as the output (Line 13), as described in Section 3.4.

### 5.1.1 <span class="sc">SubBytes</span>()

<span class="sc">SubBytes</span>() is an invertible, non-linear transformation of the state in which a substitution table, called an S-box, is applied independently to each byte in the state. The AES S-box is denoted by <span class="sc">SBox</span>().

Let \(b\) denote an input byte to <span class="sc">SBox</span>(), and let \(c\) denote the constant byte <span class="nw">\(\{\texttt{01100011}\}\).</span> The output byte \(b' = \text{SB{\footnotesize OX}}(b)\) is constructed by composing the following two transformations:

<span class="in1"></span>1. Define an intermediate value <span class="nw">\(\tilde b\),</span> as follows, where \(b^{-1}\) is the multiplicative inverse of <span class="nw">\(b\),</span> as described in Section 4.4:

$$\tilde b = \begin{cases} \{\texttt{00}\} & \text{if } b = \{\texttt{00}\}\\ b^{-1} & \text{if } b \ne \{\texttt{00}\}. \end{cases} \tag{5.2}$$

<span class="in1"></span>2. Apply the following affine transformation of the bits of \(\tilde b\) to produce the bits of <span class="nw">\(b'\):</span>

$$\small b_i' = \tilde b_i \oplus \tilde b_{(i+4) \bmod 8} \oplus \tilde b_{(i+5) \bmod 8} \oplus \tilde b_{(i+6) \bmod 8} \oplus \tilde b_{(i+7) \bmod 8} \oplus c_i. \tag{5.3}$$

The matrix form of Eq. (5.3) is given by Eq. (5.4) below:

$$\begin{bmatrix}b_0'\\b_1'\\b_2'\\b_3'\\b_4'\\b_5'\\b_6'\\b_7'\end{bmatrix} = \begin{bmatrix}1 & 0 & 0 & 0 & 1 & 1 & 1 & 1\\1 & 1 & 0 & 0 & 0 & 1 & 1 & 1\\1 & 1 & 1 & 0 & 0 & 0 & 1 & 1\\1 & 1 & 1 & 1 & 0 & 0 & 0 & 1\\1 & 1 & 1 & 1 & 1 & 0 & 0 & 0\\0 & 1 & 1 & 1 & 1 & 1 & 0 & 0\\0 & 0 & 1 & 1 & 1 & 1 & 1 & 0\\0 & 0 & 0 & 1 & 1 & 1 & 1 & 1\end{bmatrix}\begin{bmatrix}\tilde b_0\\\tilde b_1\\\tilde b_2\\\tilde b_3\\\tilde b_4\\\tilde b_5\\\tilde b_6\\\tilde b_7\end{bmatrix} + \begin{bmatrix}1\\1\\0\\0\\0\\1\\1\\0\end{bmatrix}. \tag{5.4}$$

Figure 2 illustrates how <span class="sc">SubBytes</span>() transforms the state.

::: figure subbytes

<span class="cap">Figure 2. Illustration of <span class="sc">SubBytes</span>()</span>

The AES S-box is presented in hexadecimal form in Table 4. For example, if <span class="nw">\(s_{r,c} = \{\texttt{53}\}\),</span> then the substitution value would be determined by the intersection of the row with index ‘5’ and the column with index ‘3’ in Table 4, so that <span class="nw">\(s_{r,c}' = \{\texttt{ed}\}\).</span>

<span class="cap"><b>Table 4. <span class="sc">SBox</span>(): substitution values for the byte <code>xy</code> (in hexadecimal format)</b></span>

<table class="sbox"><tr><td></td><td></td><th class="yx" colspan="16"><code>y</code></th></tr><tr><td></td><td></td><th>0</th><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>6</th><th>7</th><th>8</th><th>9</th><th>a</th><th>b</th><th>c</th><th>d</th><th>e</th><th>f</th></tr><tr><th class="yx" rowspan="16"><code>x</code></th><th>0</th><td>63</td><td>7c</td><td>77</td><td>7b</td><td>f2</td><td>6b</td><td>6f</td><td>c5</td><td>30</td><td>01</td><td>67</td><td>2b</td><td>fe</td><td>d7</td><td>ab</td><td>76</td></tr><tr><th>1</th><td>ca</td><td>82</td><td>c9</td><td>7d</td><td>fa</td><td>59</td><td>47</td><td>f0</td><td>ad</td><td>d4</td><td>a2</td><td>af</td><td>9c</td><td>a4</td><td>72</td><td>c0</td></tr><tr><th>2</th><td>b7</td><td>fd</td><td>93</td><td>26</td><td>36</td><td>3f</td><td>f7</td><td>cc</td><td>34</td><td>a5</td><td>e5</td><td>f1</td><td>71</td><td>d8</td><td>31</td><td>15</td></tr><tr><th>3</th><td>04</td><td>c7</td><td>23</td><td>c3</td><td>18</td><td>96</td><td>05</td><td>9a</td><td>07</td><td>12</td><td>80</td><td>e2</td><td>eb</td><td>27</td><td>b2</td><td>75</td></tr><tr><th>4</th><td>09</td><td>83</td><td>2c</td><td>1a</td><td>1b</td><td>6e</td><td>5a</td><td>a0</td><td>52</td><td>3b</td><td>d6</td><td>b3</td><td>29</td><td>e3</td><td>2f</td><td>84</td></tr><tr><th>5</th><td>53</td><td>d1</td><td>00</td><td>ed</td><td>20</td><td>fc</td><td>b1</td><td>5b</td><td>6a</td><td>cb</td><td>be</td><td>39</td><td>4a</td><td>4c</td><td>58</td><td>cf</td></tr><tr><th>6</th><td>d0</td><td>ef</td><td>aa</td><td>fb</td><td>43</td><td>4d</td><td>33</td><td>85</td><td>45</td><td>f9</td><td>02</td><td>7f</td><td>50</td><td>3c</td><td>9f</td><td>a8</td></tr><tr><th>7</th><td>51</td><td>a3</td><td>40</td><td>8f</td><td>92</td><td>9d</td><td>38</td><td>f5</td><td>bc</td><td>b6</td><td>da</td><td>21</td><td>10</td><td>ff</td><td>f3</td><td>d2</td></tr><tr><th>8</th><td>cd</td><td>0c</td><td>13</td><td>ec</td><td>5f</td><td>97</td><td>44</td><td>17</td><td>c4</td><td>a7</td><td>7e</td><td>3d</td><td>64</td><td>5d</td><td>19</td><td>73</td></tr><tr><th>9</th><td>60</td><td>81</td><td>4f</td><td>dc</td><td>22</td><td>2a</td><td>90</td><td>88</td><td>46</td><td>ee</td><td>b8</td><td>14</td><td>de</td><td>5e</td><td>0b</td><td>db</td></tr><tr><th>a</th><td>e0</td><td>32</td><td>3a</td><td>0a</td><td>49</td><td>06</td><td>24</td><td>5c</td><td>c2</td><td>d3</td><td>ac</td><td>62</td><td>91</td><td>95</td><td>e4</td><td>79</td></tr><tr><th>b</th><td>e7</td><td>c8</td><td>37</td><td>6d</td><td>8d</td><td>d5</td><td>4e</td><td>a9</td><td>6c</td><td>56</td><td>f4</td><td>ea</td><td>65</td><td>7a</td><td>ae</td><td>08</td></tr><tr><th>c</th><td>ba</td><td>78</td><td>25</td><td>2e</td><td>1c</td><td>a6</td><td>b4</td><td>c6</td><td>e8</td><td>dd</td><td>74</td><td>1f</td><td>4b</td><td>bd</td><td>8b</td><td>8a</td></tr><tr><th>d</th><td>70</td><td>3e</td><td>b5</td><td>66</td><td>48</td><td>03</td><td>f6</td><td>0e</td><td>61</td><td>35</td><td>57</td><td>b9</td><td>86</td><td>c1</td><td>1d</td><td>9e</td></tr><tr><th>e</th><td>e1</td><td>f8</td><td>98</td><td>11</td><td>69</td><td>d9</td><td>8e</td><td>94</td><td>9b</td><td>1e</td><td>87</td><td>e9</td><td>ce</td><td>55</td><td>28</td><td>df</td></tr><tr><th>f</th><td>8c</td><td>a1</td><td>89</td><td>0d</td><td>bf</td><td>e6</td><td>42</td><td>68</td><td>41</td><td>99</td><td>2d</td><td>0f</td><td>b0</td><td>54</td><td>bb</td><td>16</td></tr></table>

### 5.1.2 <span class="sc">ShiftRows</span>()

<span class="sc">ShiftRows</span>() is a transformation of the state in which the bytes in the last three rows of the state are cyclically shifted. The number of positions by which the bytes are shifted depends on the row index <i>r</i>, as follows:

$$s_{r,c}' = s_{r,(c+r) \bmod 4} \quad \text{for } 0 \le r < 4 \text{ and } 0 \le c < 4. \tag{5.5}$$

<span class="sc">ShiftRows</span>() is illustrated in Figure 3. In that representation of the state, the effect is to move each byte by <i>r</i> positions to the left in the row, cycling the left-most <i>r</i> bytes around to the right end of the row. The first row, where <span class="nw">\(r = 0\),</span> is unchanged.

::: figure shiftrows

<span class="cap">Figure 3. Illustration of <span class="sc">ShiftRows</span>()</span>

### 5.1.3 <span class="sc">MixColumns</span>()

<span class="sc">MixColumns</span>() is a transformation of the state that multiplies each of the four columns of the state by a single fixed matrix, as described in Section 4.3, with its entries taken from the following word:

$$[a_0,a_1,a_2,a_3] = [\{\texttt{02}\},\{\texttt{01}\},\{\texttt{01}\},\{\texttt{03}\}]. \tag{5.6}$$

Thus,

$$\begin{bmatrix}s_{0,c}'\\s_{1,c}'\\s_{2,c}'\\s_{3,c}'\end{bmatrix} = \begin{bmatrix}\texttt{02} & \texttt{03} & \texttt{01} & \texttt{01}\\\texttt{01} & \texttt{02} & \texttt{03} & \texttt{01}\\\texttt{01} & \texttt{01} & \texttt{02} & \texttt{03}\\\texttt{03} & \texttt{01} & \texttt{01} & \texttt{02}\end{bmatrix}\begin{bmatrix}s_{0,c}\\s_{1,c}\\s_{2,c}\\s_{3,c}\end{bmatrix} \quad \text{for } 0 \le c < 4, \tag{5.7}$$

so that the individual output bytes are defined as follows:

$$
\begin{aligned}
s_{0,c}' &= (\{\texttt{02}\} \bullet s_{0,c}) \oplus (\{\texttt{03}\} \bullet s_{1,c}) \oplus s_{2,c} \oplus s_{3,c}\\
s_{1,c}' &= s_{0,c} \oplus (\{\texttt{02}\} \bullet s_{1,c}) \oplus (\{\texttt{03}\} \bullet s_{2,c}) \oplus s_{3,c}\\
s_{2,c}' &= s_{0,c} \oplus s_{1,c} \oplus (\{\texttt{02}\} \bullet s_{2,c}) \oplus (\{\texttt{03}\} \bullet s_{3,c})\\
s_{3,c}' &= (\{\texttt{03}\} \bullet s_{0,c}) \oplus s_{1,c} \oplus s_{2,c} \oplus (\{\texttt{02}\} \bullet s_{3,c}).
\end{aligned} \tag{5.8}
$$

Figure 4 illustrates <span class="sc">MixColumns</span>().

::: figure mixcolumns

<span class="cap">Figure 4. Illustration of <span class="sc">MixColumns</span>()</span>

### 5.1.4 <span class="sc">AddRoundKey</span>()

<span class="sc">AddRoundKey</span>() is a transformation of the state in which a round key is combined with the state by applying the bitwise XOR operation. In particular, each round key consists of four words from the key schedule (described in Section 5.2), each of which is combined with a column of the state as follows:

$$\small [s_{0,c}', s_{1,c}', s_{2,c}', s_{3,c}'] = [s_{0,c}, s_{1,c}, s_{2,c}, s_{3,c}] \oplus [w_{(4*\mathit{round}+c)}] \quad \text{for } 0 \le c < 4 \tag{5.9}$$

where <i>round</i> is a value in the range \(0 \le \mathit{round} \le \mathit{Nr}\), and \(w[i]\) is the array of key schedule words described in Section 5.2. In the specification of <span class="sc">Cipher</span>(), <span class="sc">AddRoundKey</span>() is invoked \(\mathit{Nr}+1\) times — once prior to the first application of the round function (see Alg. 1) and once within each of the <i>Nr</i> rounds, when \(1 \le \mathit{round} \le \mathit{Nr}\).

The action of this transformation is illustrated in Fig. 5, where <span class="nw">\(l = 4 * \mathit{round}\).</span> The byte address within words of the key schedule was described in Sec. 3.5.

::: figure addroundkey

<span class="cap">Figure 5. Illustration of <span class="sc">AddRoundKey</span>()</span>

## 5.2 <span class="sc">KeyExpansion</span>()

<span class="sc">KeyExpansion</span>() is a routine that is applied to the key to generate \(4 * (\mathit{Nr}+1)\) words. Thus, four words are generated for each of the \(\mathit{Nr}+1\) applications of <span class="sc">AddRoundKey</span>() within the specification of <span class="sc">Cipher</span>(), as described in Section 5.1.4. The output of the routine consists of a linear array of words, denoted by <span class="nw">\(w[i]\),</span> where \(i\) is in the range <span class="nw">\(0 \le i < 4 * (\mathit{Nr}+1)\).</span>

<span class="sc">KeyExpansion</span>() invokes 10 fixed words denoted by \(\mathit{Rcon}[j]\) for <span class="nw">\(1 \le j \le 10\).</span> These 10 words are called the <i>round constants</i>. For AES-128, a distinct round constant is called in the generation of each of the 10 round keys. For AES-192 and AES-256, the key expansion routine calls the first eight and seven of these same constants, respectively. The values of \(\mathit{Rcon}[j]\) are given in hexadecimal notation in Table 5:

<span class="cap"><b>Table 5. Round constants</b></span>

<table class="t5"><tr><th><i>j</i></th><th><i>Rcon</i>[<i>j</i>]</th><th><i>j</i></th><th><i>Rcon</i>[<i>j</i>]</th></tr><tr><td>1</td><td><code>[01,00,00,00]</code></td><td>6</td><td><code>[20,00,00,00]</code></td></tr><tr><td>2</td><td><code>[02,00,00,00]</code></td><td>7</td><td><code>[40,00,00,00]</code></td></tr><tr><td>3</td><td><code>[04,00,00,00]</code></td><td>8</td><td><code>[80,00,00,00]</code></td></tr><tr><td>4</td><td><code>[08,00,00,00]</code></td><td>9</td><td><code>[1b,00,00,00]</code></td></tr><tr><td>5</td><td><code>[10,00,00,00]</code></td><td>10</td><td><code>[36,00,00,00]</code></td></tr></table>

The value of the left-most byte of \(\mathit{Rcon}[j]\) in polynomial form is <span class="nw">\(x^{j-1}\).</span> Note that for <span class="nw">\(j > 0\),</span> these bytes may be generated by successively applying <span class="sc">xTimes</span>() to the byte represented by \(x^{j-1}\) (see Eq. 4.5).

Two transformations on words are called within <span class="sc">KeyExpansion</span>(): <span class="sc">RotWord</span>() and <span class="sc">SubWord</span>(). Given an input word represented as a sequence \([a_0,a_1,a_2,a_3]\) of four bytes,

$$\text{R{\footnotesize OT}W{\footnotesize ORD}}([a_0,a_1,a_2,a_3]) = [a_1,a_2,a_3,a_0], \tag{5.10}$$

and

$$\small \text{S{\footnotesize UB}W{\footnotesize ORD}}([a_0,\ldots,a_3]) = [\text{SB{\footnotesize OX}}(a_0),\text{SB{\footnotesize OX}}(a_1),\text{SB{\footnotesize OX}}(a_2),\text{SB{\footnotesize OX}}(a_3)]. \tag{5.11}$$

The expansion of the key proceeds according to the pseudocode in Alg. 2. The first <i>Nk</i> words of the expanded key are the key itself. Every subsequent word \(w[i]\) is generated recursively from the preceding word, <span class="nw">\(w[i-1]\),</span> and the word <i>Nk</i> positions earlier, <span class="nw">\(w[i-\mathit{Nk}]\),</span> as follows:

- If \(i\) is a multiple of <i>Nk</i>, then \(w[i] = w[i-\mathit{Nk}] \oplus \text{S{\footnotesize UB}W{\footnotesize ORD}}(\text{R{\footnotesize OT}W{\footnotesize ORD}}(w[i-1])) \oplus \mathit{Rcon}[i/\mathit{Nk}]\).
- For AES-256, if \(i+4\) is a multiple of 8, then \(w[i] = w[i-\mathit{Nk}] \oplus \text{S{\footnotesize UB}W{\footnotesize ORD}}(w[i-1])\).
- For all other cases, \(w[i] = w[i-\mathit{Nk}] \oplus w[i-1]\).

<span class="ah"><b>Algorithm 2</b> Pseudocode for <span class="sc">KeyExpansion</span>()</span>

<span class="ln">1:</span><span class="i0"></span>\(\textbf{procedure}\ \text{K{\footnotesize EY}E{\footnotesize XPANSION}}(\mathit{key})\)

<span class="ln">2:</span><span class="i1"></span>\(i \leftarrow 0\)

<span class="ln">3:</span><span class="i1"></span>\(\textbf{while}\ i \le \mathit{Nk}-1\ \textbf{do}\)

<span class="ln">4:</span><span class="i2"></span>\(w[i] \leftarrow \mathit{key}[4*i..4*i+3]\)

<span class="ln">5:</span><span class="i2"></span>\(i \leftarrow i+1\)

<span class="ln">6:</span><span class="i1"></span>\(\textbf{end while}\)<span class="cm">\(\triangleright\) When the loop concludes, \(i = \mathit{Nk}\).</span>

<span class="ln">7:</span><span class="i1"></span>\(\textbf{while}\ i \le 4*\mathit{Nr}+3\ \textbf{do}\)

<span class="ln">8:</span><span class="i2"></span>\(\mathit{temp} \leftarrow w[i-1]\)

<span class="ln">9:</span><span class="i2"></span>\(\textbf{if}\ i \bmod \mathit{Nk} = 0\ \textbf{then}\)

<span class="ln">10:</span><span class="i3"></span>\(\mathit{temp} \leftarrow \text{S{\footnotesize UB}W{\footnotesize ORD}}(\text{R{\footnotesize OT}W{\footnotesize ORD}}(\mathit{temp})) \oplus \mathit{Rcon}[i/\mathit{Nk}]\)

<span class="ln">11:</span><span class="i2"></span>\(\textbf{else if}\ \mathit{Nk} > 6\ \textbf{and}\ i \bmod \mathit{Nk} = 4\ \textbf{then}\)

<span class="ln">12:</span><span class="i3"></span>\(\mathit{temp} \leftarrow \text{S{\footnotesize UB}W{\footnotesize ORD}}(\mathit{temp})\)

<span class="ln">13:</span><span class="i2"></span>\(\textbf{end if}\)

<span class="ln">14:</span><span class="i2"></span>\(w[i] \leftarrow w[i-\mathit{Nk}] \oplus \mathit{temp}\)

<span class="ln">15:</span><span class="i2"></span>\(i \leftarrow i+1\)

<span class="ln">16:</span><span class="i1"></span>\(\textbf{end while}\)

<span class="ln">17:</span><span class="i1"></span>\(\textbf{return}\ w\)

<span class="ln">18:</span><span class="i0"></span>\(\textbf{end procedure}\)
