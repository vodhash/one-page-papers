## Introduction

### Abstract

This document proposes a standard for 64-byte Schnorr signatures over the elliptic curve <i>secp256k1</i>.

### Copyright

This document is licensed under the 2-clause BSD license.

<div class="bsd"><p><b>BSD 2-Clause License.</b> Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:</p><p>1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.</p><p>2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.</p><p>THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.</p></div>

### Motivation

Bitcoin has traditionally used ECDSA signatures over the secp256k1 curve with SHA256 hashes for authenticating transactions. These are standardized, but have a number of downsides compared to Schnorr signatures over the same curve:

- <b>Provable security</b>: Schnorr signatures are provably secure. In more detail, they are <i>strongly unforgeable under chosen message attack (SUF-CMA)</i>[^1] in the random oracle model assuming the hardness of the elliptic curve discrete logarithm problem (ECDLP) and in the generic group model assuming variants of preimage and second preimage resistance of the used hash function[^2]. In contrast, the best known results for the provable security of ECDSA rely on stronger assumptions.
- <b>Non-malleability</b>: The SUF-CMA security of Schnorr signatures implies that they are non-malleable. On the other hand, ECDSA signatures are inherently malleable[^3]; a third party without access to the secret key can alter an existing valid signature for a given public key and message into another signature that is valid for the same key and message. This issue is discussed in BIP62 and BIP146.
- <b>Linearity</b>: Schnorr signatures provide a simple and efficient method that enables multiple collaborating parties to produce a signature that is valid for the sum of their public keys. This is the building block for various higher-level constructions that improve efficiency and privacy, such as multisignatures and others (see Applications below).

For all these advantages, there are virtually no disadvantages, apart from not being standardized. This document seeks to change that. As we propose a new standard, a number of improvements not specific to Schnorr signatures can be made:

- <b>Signature encoding</b>: Instead of using DER-encoding for signatures (which are variable size, and up to 72 bytes), we can use a simple fixed 64-byte format.
- <b>Public key encoding</b>: Instead of using <i>compressed</i> 33-byte encodings of elliptic curve points which are common in Bitcoin today, public keys in this proposal are encoded as 32 bytes.
- <b>Batch verification</b>: The specific formulation of ECDSA signatures that is standardized cannot be verified more efficiently in batch compared to individually, unless additional witness data is added. Changing the signature scheme offers an opportunity to address this.
- <b>Completely specified</b>: To be safe for usage in consensus systems, the verification algorithm must be completely specified at the byte level. This guarantees that nobody can construct a signature that is valid to some verifiers but not all. This is traditionally not a requirement for digital signature schemes, and the lack of exact specification for the DER parsing of ECDSA signatures has caused problems for Bitcoin in the past, needing BIP66 to address it. In this document we aim to meet this property by design. For batch verification, which is inherently non-deterministic as the verifier can choose their batches, this property implies that the outcome of verification may only differ from individual verifications with negligible probability, even to an attacker who intentionally tries to make batch- and non-batch verification differ.

By reusing the same curve and hash function as Bitcoin uses for ECDSA, we are able to retain existing mechanisms for choosing secret and public keys, and we avoid introducing new assumptions about the security of elliptic curves and hash functions.

## Description

We first build up the algebraic formulation of the signature scheme by going through the design choices. Afterwards, we specify the exact encodings and operations.

### Design

<b>Schnorr signature variant</b> Elliptic Curve Schnorr signatures for message <i>m</i> and public key <i>P</i> generally involve a point <i>R</i>, integers <i>e</i> and <i>s</i> picked by the signer, and the base point <i>G</i> which satisfy <i>e = hash(R || m)</i> and <i>s<span class="op">⋅</span>G = R + e<span class="op">⋅</span>P</i>. Two formulations exist, depending on whether the signer reveals <i>e</i> or <i>R</i>:

1. Signatures are pairs <i>(e, s)</i> that satisfy <i>e = hash(s<span class="op">⋅</span>G - e<span class="op">⋅</span>P || m)</i>. This variant avoids minor complexity introduced by the encoding of the point <i>R</i> in the signature (see paragraphs "Encoding R and public key point P" and "Implicit Y coordinates" further below in this subsection). Moreover, revealing <i>e</i> instead of <i>R</i> allows for potentially shorter signatures: Whereas an encoding of <i>R</i> inherently needs about 32 bytes, the hash <i>e</i> can be tuned to be shorter than 32 bytes, and a short hash of only 16 bytes suffices to provide SUF-CMA security at the target security level of 128 bits. However, a major drawback of this optimization is that finding collisions in a short hash function is easy. This complicates the implementation of secure signing protocols in scenarios in which a group of mutually distrusting signers work together to produce a single joint signature (see Applications below). In these scenarios, which are not captured by the SUF-CMA model due its assumption of a single honest signer, a promising attack strategy for malicious co-signers is to find a collision in the hash function in order to obtain a valid signature on a message that an honest co-signer did not intend to sign.
2. Signatures are pairs <i>(R, s)</i> that satisfy <i>s<span class="op">⋅</span>G = R + hash(R || m)<span class="op">⋅</span>P</i>. This supports batch verification, as there are no elliptic curve operations inside the hashes. Batch verification enables significant speedups.[^4]

Since we would like to avoid the fragility that comes with short hashes, the <i>e</i> variant does not provide significant advantages. We choose the <i>R</i>-option, which supports batch verification.

<b>Key prefixing</b> Using the verification rule above directly makes Schnorr signatures vulnerable to "related-key attacks" in which a third party can convert a signature <i>(R, s)</i> for public key <i>P</i> into a signature <i>(R, s + a<span class="op">⋅</span>hash(R || m))</i> for public key <i>P + a<span class="op">⋅</span>G</i> and the same message <i>m</i>, for any given additive tweak <i>a</i> to the signing key. This would render signatures insecure when keys are generated using BIP32's unhardened derivation and other methods that rely on additive tweaks to existing keys such as Taproot.

To protect against these attacks, we choose <i>key prefixed</i>[^5] Schnorr signatures which means that the public key is prefixed to the message in the challenge hash input. This changes the equation to <i>s<span class="op">⋅</span>G = R + hash(R || P || m)<span class="op">⋅</span>P</i>. It can be shown that key prefixing protects against related-key attacks with additive tweaks. In general, key prefixing increases robustness in multi-user settings, e.g., it seems to be a requirement for proving multiparty signing protocols (such as MuSig, MuSig2, and FROST) secure (see Applications below).

We note that key prefixing is not strictly necessary for transaction signatures as used in Bitcoin currently, because signed transactions indirectly commit to the public keys already, i.e., <i>m</i> contains a commitment to <i>pk</i>. However, this indirect commitment should not be relied upon because it may change with proposals such as SIGHASH_NOINPUT (BIP118), and would render the signature scheme unsuitable for other purposes than signing transactions, e.g., signing ordinary messages.

<b>Encoding R and public key point P</b> There exist several possibilities for encoding elliptic curve points:

1. Encoding the full X and Y coordinates of <i>P</i> and <i>R</i>, resulting in a 64-byte public key and a 96-byte signature.
2. Encoding the full X coordinate and one bit of the Y coordinate to determine one of the two possible Y coordinates. This would result in 33-byte public keys and 65-byte signatures.
3. Encoding only the X coordinate, resulting in 32-byte public keys and 64-byte signatures.

Using the first option would be slightly more efficient for verification (around 10%), but we prioritize compactness, and therefore choose option 3.

<b>Implicit Y coordinates</b> In order to support efficient verification and batch verification, the Y coordinate of <i>P</i> and of <i>R</i> cannot be ambiguous (every valid X coordinate has two possible Y coordinates). We have a choice between several options for symmetry breaking:

1. Implicitly choosing the Y coordinate that is in the lower half.
2. Implicitly choosing the Y coordinate that is even[^6].
3. Implicitly choosing the Y coordinate that is a quadratic residue (i.e. has a square root modulo <i>p</i>).

The second option offers the greatest compatibility with existing key generation systems, where the standard 33-byte compressed public key format consists of a byte indicating the oddness of the Y coordinate, plus the full X coordinate. To avoid gratuitous incompatibilities, we pick that option for <i>P</i>, and thus our X-only public keys become equivalent to a compressed public key that is the X-only key prefixed by the byte 0x02. For consistency, the same is done for <i>R</i>[^7].

Despite halving the size of the set of valid public keys, implicit Y coordinates are not a reduction in security. Informally, if a fast algorithm existed to compute the discrete logarithm of an X-only public key, then it could also be used to compute the discrete logarithm of a full public key: apply it to the X coordinate, and then optionally negate the result. This shows that breaking an X-only public key can be at most a small constant term faster than breaking a full one.[^8].

<b>Tagged Hashes</b> Cryptographic hash functions are used for multiple purposes in the specification below and in Bitcoin in general. To make sure hashes used in one context can't be reinterpreted in another one, hash functions can be tweaked with a context-dependent tag name, in such a way that collisions across contexts can be assumed to be infeasible. Such collisions obviously can not be ruled out completely, but only for schemes using tagging with a unique name. As for other schemes collisions are at least less likely with tagging than without.

For example, without tagged hashing a BIP340 signature could also be valid for a signature scheme where the only difference is that the arguments to the hash function are reordered. Worse, if the BIP340 nonce derivation function was copied or independently created, then the nonce could be accidentally reused in the other scheme leaking the secret key.

This proposal suggests to include the tag by prefixing the hashed data with <i>SHA256(tag) || SHA256(tag)</i>. Because this is a 64-byte long context-specific constant and the <i>SHA256</i> block size is also 64 bytes, optimized implementations are possible (identical to SHA256 itself, but with a modified initial state). Using SHA256 of the tag name itself is reasonably simple and efficient for implementations that don't choose to use the optimization. In general, tags can be arbitrary byte arrays, but are suggested to be textual descriptions in UTF-8 encoding.

<b>Final scheme</b> As a result, our final scheme ends up using public key <i>pk</i> which is the X coordinate of a point <i>P</i> on the curve whose Y coordinate is even and signatures <i>(r,s)</i> where <i>r</i> is the X coordinate of a point <i>R</i> whose Y coordinate is even. The signature satisfies <i>s<span class="op">⋅</span>G = R + tagged_hash(r || pk || m)<span class="op">⋅</span>P</i>.

### Specification

The following conventions are used, with constants as defined for secp256k1. We note that adapting this specification to other elliptic curves is not straightforward and can result in an insecure scheme[^9].

- Lowercase variables represent integers or byte arrays. <ul><li>The constant <i>p</i> refers to the field size, <i>0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F</i>.</li><li>The constant <i>n</i> refers to the curve order, <i>0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141</i>.</li></ul>
- Uppercase variables refer to points on the curve with equation <i>y<sup>2</sup> = x<sup>3</sup> + 7</i> over the integers modulo <i>p</i>. <ul><li><i>is_infinite(P)</i> returns whether or not <i>P</i> is the point at infinity.</li><li><i>x(P)</i> and <i>y(P)</i> are integers in the range <i>0..p-1</i> and refer to the X and Y coordinates of a point <i>P</i> (assuming it is not infinity).</li><li>The constant <i>G</i> refers to the base point, for which <i>x(G) = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798</i> and <i>y(G) = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8</i>.</li><li>Addition of points refers to the usual elliptic curve group operation.</li><li>Multiplication (<span class="op">⋅</span>) of an integer and a point refers to the repeated application of the group operation.</li></ul>
- Functions and operations: <ul><li><i>||</i> refers to byte array concatenation.</li><li>The function <i>x[i:j]</i>, where <i>x</i> is a byte array and <i>i, j <span class="op">≥</span> 0</i>, returns a <i>(j - i)</i>-byte array with a copy of the <i>i</i>-th byte (inclusive) to the <i>j</i>-th byte (exclusive) of <i>x</i>.</li><li>The function <i>bytes(x)</i>, where <i>x</i> is an integer, returns the 32-byte encoding of <i>x</i>, most significant byte first.</li><li>The function <i>bytes(P)</i>, where <i>P</i> is a point, returns <i>bytes(x(P))</i>.</li><li>The function <i>int(x)</i>, where <i>x</i> is a 32-byte array, returns the 256-bit unsigned integer whose most significant byte first encoding is <i>x</i>.</li><li>The function <i>has_even_y(P)</i>, where <i>P</i> is a point for which <i>not is_infinite(P)</i>, returns <i>y(P) mod 2 = 0</i>.</li><li>The function <i>lift_x(x)</i>, where <i>x</i> is a 256-bit unsigned integer, returns the point <i>P</i> for which <i>x(P) = x</i>[^10] and <i>has_even_y(P)</i>, or fails if <i>x</i> is greater than <i>p-1</i> or no such point exists. The function <i>lift_x(x)</i> is equivalent to the following pseudocode:<ul><li>Fail if <i>x <span class="op">≥</span> p</i>.</li><li>Let <i>c = x<sup>3</sup> + 7 mod p</i>.</li><li>Let <i>y = c<sup>(p+1)/4</sup> mod p</i>.</li><li>Fail if <i>c \(\neq\) y<sup>2</sup> mod p</i>.</li><li>Return the unique point <i>P</i> such that <i>x(P) = x</i> and <i>y(P) = y</i> if <i>y mod 2 = 0</i> or <i>y(P) = p-y</i> otherwise.</li></ul></li><li>The function <i>hash<sub>name</sub>(x)</i> where <i>x</i> is a byte array returns the 32-byte hash <i>SHA256(SHA256(tag) || SHA256(tag) || x)</i>, where <i>tag</i> is the UTF-8 encoding of <i>name</i>.</li></ul>

#### Public Key Generation

Input:

- The secret key <i>sk</i>: a 32-byte array, freshly generated uniformly at random

The algorithm <i>PubKey(sk)</i> is defined as:

- Let <i>d' = int(sk)</i>.
- Fail if <i>d' = 0</i> or <i>d' <span class="op">≥</span> n</i>.
- Return <i>bytes(d'<span class="op">⋅</span>G)</i>.

Note that we use a very different public key format (32 bytes) than the ones used by existing systems (which typically use elliptic curve points as public keys, or 33-byte or 65-byte encodings of them). A side effect is that <i>PubKey(sk) = PubKey(bytes(n - int(sk))</i>, so every public key has two corresponding secret keys.

#### Public Key Conversion

As an alternative to generating keys randomly, it is also possible and safe to repurpose existing key generation algorithms for ECDSA in a compatible way. The secret keys constructed by such an algorithm can be used as <i>sk</i> directly. The public keys constructed by such an algorithm (assuming they use the 33-byte compressed encoding) need to be converted by dropping the first byte. Specifically, BIP32 and schemes built on top of it remain usable.

#### Default Signing

Input:

- The secret key <i>sk</i>: a 32-byte array
- The message <i>m</i>: a byte array
- Auxiliary random data <i>a</i>: a 32-byte array

The algorithm <i>Sign(sk, m)</i> is defined as:

- Let <i>d' = int(sk)</i>
- Fail if <i>d' = 0</i> or <i>d' <span class="op">≥</span> n</i>
- Let <i>P = d'<span class="op">⋅</span>G</i>
- Let <i>d = d' </i> if <i>has_even_y(P)</i>, otherwise let <i>d = n - d' </i>.
- Let <i>t</i> be the byte-wise xor of <i>bytes(d)</i> and <i>hash<sub>BIP0340/aux</sub>(a)</i>[^11].
- Let <i>rand = hash<sub>BIP0340/nonce</sub>(t || bytes(P) || m)</i>[^12].
- Let <i>k' = int(rand) mod n</i>[^13].
- Fail if <i>k' = 0</i>.
- Let <i>R = k'<span class="op">⋅</span>G</i>.
- Let <i>k = k' </i> if <i>has_even_y(R)</i>, otherwise let <i>k = n - k' </i>.
- Let <i>e = int(hash<sub>BIP0340/challenge</sub>(bytes(R) || bytes(P) || m)) mod n</i>.
- Let <i>sig = bytes(R) || bytes((k + ed) mod n)</i>.
- If <i>Verify(bytes(P), m, sig)</i> (see below) returns failure, abort[^14].
- Return the signature <i>sig</i>.

The auxiliary random data should be set to fresh randomness generated at signing time, resulting in what is called a <i>synthetic nonce</i>. Using 32 bytes of randomness is optimal. If obtaining randomness is expensive, 16 random bytes can be padded with 16 null bytes to obtain a 32-byte array. If randomness is not available at all at signing time, a simple counter wide enough to not repeat in practice (e.g., 64 bits or wider) and padded with null bytes to a 32 byte-array can be used, or even the constant array with 32 null bytes. Using any non-repeating value increases protection against fault injection attacks. Using unpredictable randomness additionally increases protection against other side-channel attacks, and is <b>recommended whenever available</b>. Note that while this means the resulting nonce is not deterministic, the randomness is only supplemental to security. The normal security properties (excluding side-channel attacks) do not depend on the quality of the signing-time RNG.

#### Alternative Signing

It should be noted that various alternative signing algorithms can be used to produce equally valid signatures. The 32-byte <i>rand</i> value may be generated in other ways, producing a different but still valid signature (in other words, this is not a <i>unique</i> signature scheme). <b>No matter which method is used to generate the <i>rand</i> value, the value must be a fresh uniformly random 32-byte string which is not even partially predictable for the attacker.</b> For nonces without randomness, this implies that the same inputs must not be presented in another context. This can be most reliably accomplished by not reusing the same private key across different signing schemes. For example, if the <i>rand</i> value was computed as per RFC6979 and the same secret key is used in deterministic ECDSA with RFC6979, the signatures can leak the secret key through nonce reuse.

<b>Nonce exfiltration protection</b> It is possible to strengthen the nonce generation algorithm using a second device. In this case, the second device contributes randomness which the actual signer provably incorporates into its nonce. This prevents certain attacks where the signer's device is compromised and intentionally tries to leak the secret key through its nonce selection.

<b>Multisignatures</b> This signature scheme is compatible with various types of multisignature and threshold schemes such as MuSig2, where a single public key requires holders of multiple secret keys to participate in signing (see Applications below). <b>It is important to note that multisignature signing schemes in general are insecure with the <i>rand</i> generation from the default signing algorithm above (or any other deterministic method).</b>

<b>Precomputed public key data</b> For many uses, the compressed 33-byte encoding of the public key corresponding to the secret key may already be known, making it easy to evaluate <i>has_even_y(P)</i> and <i>bytes(P)</i>. As such, having signers supply this directly may be more efficient than recalculating the public key from the secret key. However, if this optimization is used and additionally the signature verification at the end of the signing algorithm is dropped for increased efficiency, signers must ensure the public key is correctly calculated and not taken from untrusted sources.

#### Verification

Input:

- The public key <i>pk</i>: a 32-byte array
- The message <i>m</i>: a byte array
- A signature <i>sig</i>: a 64-byte array

The algorithm <i>Verify(pk, m, sig)</i> is defined as:

- Let <i>P = lift_x(int(pk))</i>; fail if that fails.
- Let <i>r = int(sig[0:32])</i>; fail if <i>r <span class="op">≥</span> p</i>.
- Let <i>s = int(sig[32:64])</i>; fail if <i>s <span class="op">≥</span> n</i>.
- Let <i>e = int(hash<sub>BIP0340/challenge</sub>(bytes(r) || bytes(P) || m)) mod n</i>.
- Let <i>R = s<span class="op">⋅</span>G - e<span class="op">⋅</span>P</i>.
- Fail if <i>is_infinite(R)</i>.
- Fail if <i>not has_even_y(R)</i>.
- Fail if <i>x(R) \(\neq\) r</i>.
- Return success iff no failure occurred before reaching this point.

For every valid secret key <i>sk</i> and message <i>m</i>, <i>Verify(PubKey(sk),m,Sign(sk,m))</i> will succeed.

Note that the correctness of verification relies on the fact that <i>lift_x</i> always returns a point with an even Y coordinate. A hypothetical verification algorithm that treats points as public keys, and takes the point <i>P</i> directly as input would fail any time a point with odd Y is used. While it is possible to correct for this by negating points with odd Y coordinate before further processing, this would result in a scheme where every (message, signature) pair is valid for two public keys (a type of malleability that exists for ECDSA as well, but we don't wish to retain). We avoid these problems by treating just the X coordinate as public key.

#### Batch Verification

Input:

- The number <i>u</i> of signatures
- The public keys <i>pk<sub>1..u</sub></i>: <i>u</i> 32-byte arrays
- The messages <i>m<sub>1..u</sub></i>: <i>u</i> byte arrays
- The signatures <i>sig<sub>1..u</sub></i>: <i>u</i> 64-byte arrays

The algorithm <i>BatchVerify(pk<sub>1..u</sub>, m<sub>1..u</sub>, sig<sub>1..u</sub>)</i> is defined as:

- Generate <i>u-1</i> random integers <i>a<sub>2...u</sub></i> in the range <i>1...n-1</i>. They are generated deterministically using a CSPRNG seeded by a cryptographic hash of all inputs of the algorithm, i.e. <i>seed = seed_hash(pk<sub>1</sub>..pk<sub>u</sub> || m<sub>1</sub>..m<sub>u</sub> || sig<sub>1</sub>..sig<sub>u</sub> )</i>. A safe choice is to instantiate <i>seed_hash</i> with SHA256 and use ChaCha20 with key <i>seed</i> as a CSPRNG to generate 256-bit integers, skipping integers not in the range <i>1...n-1</i>.
- For <i>i = 1 .. u</i>: <ul><li>Let <i>P<sub>i</sub> = lift_x(int(pk<sub>i</sub>))</i>; fail if it fails.</li><li>Let <i>r<sub>i</sub> = int(sig<sub>i</sub>[0:32])</i>; fail if <i>r<sub>i</sub> <span class="op">≥</span> p</i>.</li><li>Let <i>s<sub>i</sub> = int(sig<sub>i</sub>[32:64])</i>; fail if <i>s<sub>i</sub> <span class="op">≥</span> n</i>.</li><li>Let <i>e<sub>i</sub> = int(hash<sub>BIP0340/challenge</sub>(bytes(r<sub>i</sub>) || bytes(P<sub>i</sub>) || m<sub>i</sub>)) mod n</i>.</li><li>Let <i>R<sub>i</sub> = lift_x(r<sub>i</sub>)</i>; fail if <i>lift_x(r<sub>i</sub>)</i> fails.</li></ul>
- Fail if <i>(s<sub>1</sub> + a<sub>2</sub>s<sub>2</sub> + ... + a<sub>u</sub>s<sub>u</sub>)<span class="op">⋅</span>G \(\neq\) R<sub>1</sub> + a<sub>2</sub><span class="op">⋅</span>R<sub>2</sub> + ... + a<sub>u</sub><span class="op">⋅</span>R<sub>u</sub> + e<sub>1</sub><span class="op">⋅</span>P<sub>1</sub> + (a<sub>2</sub>e<sub>2</sub>)<span class="op">⋅</span>P<sub>2</sub> + ... + (a<sub>u</sub>e<sub>u</sub>)<span class="op">⋅</span>P<sub>u</sub></i>.
- Return success iff no failure occurred before reaching this point.

If all individual signatures are valid (i.e., <i>Verify</i> would return success for them), <i>BatchVerify</i> will always return success. If at least one signature is invalid, <i>BatchVerify</i> will return success with at most a negligible probability.

### Usage Considerations

#### Messages of Arbitrary Size

The signature scheme specified in this BIP accepts byte strings of arbitrary size as input messages.[^15] It is understood that implementations may reject messages which are too large in their environment or application context, e.g., messages which exceed predefined buffers or would otherwise cause resource exhaustion.

Earlier revisions of this BIP required messages to be exactly 32 bytes. This restriction puts a burden on callers who typically need to perform pre-hashing of the actual input message by feeding it through SHA256 (or another collision-resistant cryptographic hash function) to create a 32-byte digest which can be passed to signing or verification (as for example done in BIP341.)

Since pre-hashing may not always be desirable, e.g., when actual messages are shorter than 32 bytes,[^16] the restriction to 32-byte messages has been lifted. We note that pre-hashing is recommended for performance reasons in applications that deal with large messages. If large messages are not pre-hashed, the algorithms of the signature scheme will perform more hashing internally. In particular, the signing algorithm needs two sequential hashing passes over the message, which means that the full message must necessarily be kept in memory during signing, and large messages entail a runtime penalty.[^17]

#### Domain Separation

It is good cryptographic practice to use a key pair only for a single purpose. Nevertheless, there may be situations in which it may be desirable to use the same key pair in multiple contexts, i.e., to sign different types of messages within the same application or even messages in entirely different applications (e.g., a secret key may be used to sign Bitcoin transactions as well plain text messages).

As a consequence, applications should ensure that a signed application message intended for one context is never deemed valid in a different context (e.g., a signed plain text message should never be misinterpreted as a signed Bitcoin transaction, because this could cause unintended loss of funds). This is called "domain separation" and it is typically realized by partitioning the message space. Even if key pairs are intended to be used only within a single context, domain separation is a good idea because it makes it easy to add more contexts later.

As a best practice, we recommend applications to use exactly one of the following methods to pre-process application messages before passing it to the signature scheme:

- Either, pre-hash the application message using <i>hash<sub>name</sub></i>, where <i>name</i> identifies the context uniquely (e.g., "foo-app/signed-bar"),
- or prefix the actual message with a 33-byte string that identifies the context uniquely (e.g., the UTF-8 encoding of "foo-app/signed-bar", padded with null bytes to 33 bytes).

As the two pre-processing methods yield different message sizes (32 bytes vs. at least 33 bytes), there is no risk of collision between them.

## Applications

There are several interesting applications beyond simple signatures. While recent academic papers claim that they are also possible with ECDSA, consensus support for Schnorr signature verification would significantly simplify the constructions.

### Multisignatures and Threshold Signatures

By means of an interactive scheme such as MuSig2 (BIP327), participants can aggregate their public keys into a single public key which they can jointly sign for. This allows <i>n</i>-of-<i>n</i> multisignatures which, from a verifier's perspective, are no different from ordinary signatures, giving improved privacy and efficiency versus <i>CHECKMULTISIG</i> or other means.

Moreover, Schnorr signatures are compatible with distributed key generation, which enables interactive threshold signatures schemes, e.g., the schemes by Stinson and Strobl (2001), by Gennaro, Jarecki, Krawczyk, and Rabin (2007), or the FROST scheme including its variants such as FROST3. These protocols make it possible to realize <i>k</i>-of-<i>n</i> threshold signatures, which ensure that any subset of size <i>k</i> of the set of <i>n</i> signers can sign but no subset of size less than <i>k</i> can produce a valid Schnorr signature.

### Adaptor Signatures

Adaptor signatures can be produced by a signer by offsetting his public nonce <i>R</i> with a known point <i>T = t<span class="op">⋅</span>G</i>, but not offsetting the signature's <i>s</i> value. A correct signature (or partial signature, as individual signers' contributions to a multisignature are called) on the same message with same nonce will then be equal to the adaptor signature offset by <i>t</i>, meaning that learning <i>t</i> is equivalent to learning a correct signature. This can be used to enable atomic swaps or even general payment channels in which the atomicity of disjoint transactions is ensured using the signatures themselves, rather than Bitcoin script support. The resulting transactions will appear to verifiers to be no different from ordinary single-signer transactions, except perhaps for the inclusion of locktime refund logic.

Adaptor signatures, beyond the efficiency and privacy benefits of encoding script semantics into constant-sized signatures, have additional benefits over traditional hash-based payment channels. Specifically, the secret values <i>t</i> may be reblinded between hops, allowing long chains of transactions to be made atomic while even the participants cannot identify which transactions are part of the chain. Also, because the secret values are chosen at signing time, rather than key generation time, existing outputs may be repurposed for different applications without recourse to the blockchain, even multiple times.

### Blind Signatures

A blind signature protocol is an interactive protocol that enables a signer to sign a message at the behest of another party without learning any information about the signed message or the signature. Schnorr signatures admit a very simple blind signature scheme which is however insecure because it's vulnerable to Wagner's attack. Known mitigations are to let the signer abort a signing session with a certain probability, which can be proven secure under non-standard cryptographic assumptions, or to use zero-knowledge proofs.

Blind Schnorr signatures could for example be used in Partially Blind Atomic Swaps, a construction to enable transferring of coins, mediated by an untrusted escrow agent, without connecting the transactors in the public blockchain transaction graph.

## Test Vectors and Reference Code

For development and testing purposes, we provide a collection of test vectors in CSV format, a naive, highly inefficient, and non-constant time pure Python 3.7 reference implementation of the signing and verification algorithm as well as the script used to generate the test vectors under the BSD-2-Clause License, or the MIT License, or CC0 1.0, at your choice. The reference implementation is for demonstration purposes only and not to be used in production environments.

## Changelog

To help implementers understand updates to this BIP, we keep a list of substantial changes.

- 2022-08: Fix function signature of lift_x in reference code
- 2023-04: Allow messages of arbitrary size
- 2024-05: Update "Applications" section with more recent references
- 2025-04: Change license of test vectors and code

## Acknowledgements

This document is the result of many discussions around Schnorr based signatures over the years, and had input from Johnson Lau, Greg Maxwell, Andrew Poelstra, Rusty Russell, and Anthony Towns. The authors further wish to thank all those who provided valuable feedback and reviews, including the participants of the structured reviews.

[^1]: Informally, this means that without knowledge of the secret key but given valid signatures of arbitrary messages, it is not possible to come up with further valid signatures.

[^2]: A detailed security proof in the random oracle model, which essentially restates the original security proof by Pointcheval and Stern more explicitly, can be found in a paper by Kiltz, Masny and Pan. All these security proofs assume a variant of Schnorr signatures that use <i>(e,s)</i> instead of <i>(R,s)</i> (see Design above). Since we use a unique encoding of <i>R</i>, there is an efficiently computable bijection that maps <i>(R,s)</i> to <i>(e,s)</i>, which allows to convert a successful SUF-CMA attacker for the <i>(e,s)</i> variant to a successful SUF-CMA attacker for the <i>(R,s)</i> variant (and vice-versa). Furthermore, the proofs consider a variant of Schnorr signatures without key prefixing (see Design above), but it can be verified that the proofs are also correct for the variant with key prefixing. As a result, all the aforementioned security proofs apply to the variant of Schnorr signatures proposed in this document.

[^3]: If <i>(r,s)</i> is a valid ECDSA signature for a given message and key, then <i>(r,n-s)</i> is also valid for the same message and key. If ECDSA is restricted to only permit one of the two variants (as Bitcoin does through a policy rule on the network), it can be proven non-malleable under stronger than usual assumptions.

[^4]: The speedup that results from batch verification can be demonstrated with the cryptography library libsecp256k1.

[^5]: A limitation of committing to the public key (rather than to a short hash of it, or not at all) is that it removes the ability for public key recovery or verifying signatures against a short public key hash. These constructions are generally incompatible with batch verification.

[^6]: Since <i>p</i> is odd, negation modulo <i>p</i> will map even numbers to odd numbers and the other way around. This means that for a valid X coordinate, one of the corresponding Y coordinates will be even, and the other will be odd.

[^7]: An earlier version of this draft used the third option instead, based on a belief that this would in general trade signing efficiency for verification efficiency. When using Jacobian coordinates, a common optimization in ECC implementations, it is possible to determine if a Y coordinate is a quadratic residue by computing the Legendre symbol, without converting to affine coordinates first (which needs a modular inversion). As modular inverses and Legendre symbols have similar performance in practice, this trade-off is not worth it.

[^8]: This can be formalized by a simple reduction that reduces an attack on Schnorr signatures with implicit Y coordinates to an attack to Schnorr signatures with explicit Y coordinates. The reduction works by reencoding public keys and negating the result of the hash function, which is modeled as random oracle, whenever the challenge public key has an explicit Y coordinate that is odd. A proof sketch can be found here.

[^9]: Among other pitfalls, using the specification with a curve whose order is not close to the size of the range of the nonce derivation function is insecure.

[^10]: Given a candidate X coordinate <i>x</i> in the range <i>0..p-1</i>, there exist either exactly two or exactly zero valid Y coordinates. If no valid Y coordinate exists, then <i>x</i> is not a valid X coordinate either, i.e., no point <i>P</i> exists for which <i>x(P) = x</i>. The valid Y coordinates for a given candidate <i>x</i> are the square roots of <i>c = x<sup>3</sup> + 7 mod p</i> and they can be computed as <i>y = <span class="op">±</span>c<sup>(p+1)/4</sup> mod p</i> (see Quadratic residue) if they exist, which can be checked by squaring and comparing with <i>c</i>.

[^11]: The auxiliary random data is hashed (with a unique tag) as a precaution against situations where the randomness may be correlated with the private key itself. It is xored with the private key (rather than combined with it in a hash) to reduce the number of operations exposed to the actual secret key.

[^12]: Including the public key as input to the nonce hash helps ensure the robustness of the signing algorithm by preventing leakage of the secret key if the calculation of the public key <i>P</i> is performed incorrectly or maliciously, for example if it is left to the caller for performance reasons.

[^13]: Note that in general, taking a uniformly random 256-bit integer modulo the curve order will produce an unacceptably biased result. However, for the secp256k1 curve, the order is sufficiently close to <i>2<sup>256</sup></i> that this bias is not observable (<i>1 - n / 2<sup>256</sup></i> is around <i>1.27 * 2<sup>-128</sup></i>).

[^14]: Verifying the signature before leaving the signer prevents random or attacker provoked computation errors. This prevents publishing invalid signatures which may leak information about the secret key. It is recommended, but can be omitted if the computation cost is prohibitive.

[^15]: In theory, the message size is restricted due to the fact that SHA256 accepts byte strings only up to size of 2^61-1 bytes.

[^16]: Another reason to omit pre-hashing is to protect against certain types of cryptanalytic advances against the hash function used for pre-hashing: If pre-hashing is used, an attacker that can find collisions in the pre-hashing function can necessarily forge signatures under chosen-message attacks. If pre-hashing is not used, an attacker that can find collisions in SHA256 (as used inside the signature scheme) may not be able to forge signatures. However, this seeming advantage is mostly irrelevant in the context of Bitcoin, which already relies on collision resistance of SHA256 in other places, e.g., for transaction hashes.

[^17]: Typically, messages of 56 bytes or longer enjoy a performance benefit from pre-hashing, assuming the speed of SHA256 inside the signing algorithm matches that of the pre-hashing done by the calling application.
