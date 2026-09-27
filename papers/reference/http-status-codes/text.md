::: wide

<div class="intro"><div>

<p class="lead">The status code of a response is a three-digit integer code that describes the result of the request and the semantics of the response, including whether the request was successful and what content is enclosed (if any). All valid status codes are within the range of 100 to 599, inclusive.</p>

<p>The first digit of the status code defines the class of response. The last two digits do not have any categorization role. There are five values for the first digit:</p>

<ul class="classes"><li><b>1xx (Informational)</b>: The request was received, continuing process</li><li><b>2xx (Successful)</b>: The request was successfully received, understood, and accepted</li><li><b>3xx (Redirection)</b>: Further action needs to be taken in order to complete the request</li><li><b>4xx (Client Error)</b>: The request contains bad syntax or cannot be fulfilled</li><li><b>5xx (Server Error)</b>: The server failed to fulfill an apparently valid request</li></ul>

</div><div>

<p>HTTP status codes are extensible. A client is not required to understand the meaning of all registered status codes, though such understanding is obviously desirable. However, a client MUST understand the class of any status code, as indicated by the first digit, and treat an unrecognized status code as being equivalent to the x00 status code of that class.</p>

<p>The status codes listed below are defined in this specification. The reason phrases listed here are only recommendations -- they can be replaced by local equivalents or left out altogether without affecting the protocol.</p>

</div></div>

:::

## Informational 1xx

<p class="clead">The 1xx (Informational) class of status code indicates an interim response for communicating connection status or request progress prior to completing the requested action and sending a final response.</p>

<div class="sc"><b>100</b> <span class="rp">Continue</span> <span class="ref">15.2.1</span><span class="def">The 100 (Continue) status code indicates that the initial part of a request has been received and has not yet been rejected by the server.</span></div>

<div class="sc"><b>101</b> <span class="rp">Switching Protocols</span> <span class="ref">15.2.2</span><span class="def">The 101 (Switching Protocols) status code indicates that the server understands and is willing to comply with the client's request, via the Upgrade header field (Section 7.8), for a change in the application protocol being used on this connection.</span></div>

<div class="sc x"><b>102</b> <span class="rp">Processing</span> <span class="ref">RFC 2518</span></div>

<div class="sc x"><b>103</b> <span class="rp">Early Hints</span> <span class="ref">RFC 8297</span></div>

<div class="sc x"><b>104</b> <span class="rp">Upload Resumption Supported</span> <span class="ref">draft-ietf-httpbis-resumable-upload-05</span><span class="def">TEMPORARY - registered 2024-11-13, extension registered 2025-09-15, expires 2026-11-13</span></div>

<div class="sc un"><b>105-199</b> <span class="rp">Unassigned</span></div>

## Successful 2xx

<p class="clead">The 2xx (Successful) class of status code indicates that the client's request was successfully received, understood, and accepted.</p>

<div class="sc"><b>200</b> <span class="rp">OK</span> <span class="ref">15.3.1</span><span class="def">The 200 (OK) status code indicates that the request has succeeded.</span></div>

<div class="sc"><b>201</b> <span class="rp">Created</span> <span class="ref">15.3.2</span><span class="def">The 201 (Created) status code indicates that the request has been fulfilled and has resulted in one or more new resources being created.</span></div>

<div class="sc"><b>202</b> <span class="rp">Accepted</span> <span class="ref">15.3.3</span><span class="def">The 202 (Accepted) status code indicates that the request has been accepted for processing, but the processing has not been completed.</span></div>

<div class="sc"><b>203</b> <span class="rp">Non-Authoritative Information</span> <span class="ref">15.3.4</span><span class="def">The 203 (Non-Authoritative Information) status code indicates that the request was successful but the enclosed content has been modified from that of the origin server's 200 (OK) response by a transforming proxy (Section 7.7).</span></div>

<div class="sc"><b>204</b> <span class="rp">No Content</span> <span class="ref">15.3.5</span><span class="def">The 204 (No Content) status code indicates that the server has successfully fulfilled the request and that there is no additional content to send in the response content.</span></div>

<div class="sc"><b>205</b> <span class="rp">Reset Content</span> <span class="ref">15.3.6</span><span class="def">The 205 (Reset Content) status code indicates that the server has fulfilled the request and desires that the user agent reset the "document view", which caused the request to be sent, to its original state as received from the origin server.</span></div>

<div class="sc"><b>206</b> <span class="rp">Partial Content</span> <span class="ref">15.3.7</span><span class="def">The 206 (Partial Content) status code indicates that the server is successfully fulfilling a range request for the target resource by transferring one or more parts of the selected representation.</span></div>

<div class="sc x"><b>207</b> <span class="rp">Multi-Status</span> <span class="ref">RFC 4918</span></div>

<div class="sc x"><b>208</b> <span class="rp">Already Reported</span> <span class="ref">RFC 5842</span></div>

<div class="sc un"><b>209-225</b> <span class="rp">Unassigned</span></div>

<div class="sc x"><b>226</b> <span class="rp">IM Used</span> <span class="ref">RFC 3229</span></div>

<div class="sc un"><b>227-299</b> <span class="rp">Unassigned</span></div>

## Redirection 3xx

<p class="clead">The 3xx (Redirection) class of status code indicates that further action needs to be taken by the user agent in order to fulfill the request.</p>

<div class="sc"><b>300</b> <span class="rp">Multiple Choices</span> <span class="ref">15.4.1</span><span class="def">The 300 (Multiple Choices) status code indicates that the target resource has more than one representation, each with its own more specific identifier, and information about the alternatives is being provided so that the user (or user agent) can select a preferred representation by redirecting its request to one or more of those identifiers.</span></div>

<div class="sc"><b>301</b> <span class="rp">Moved Permanently</span> <span class="ref">15.4.2</span><span class="def">The 301 (Moved Permanently) status code indicates that the target resource has been assigned a new permanent URI and any future references to this resource ought to use one of the enclosed URIs.</span></div>

<div class="sc"><b>302</b> <span class="rp">Found</span> <span class="ref">15.4.3</span><span class="def">The 302 (Found) status code indicates that the target resource resides temporarily under a different URI.</span></div>

<div class="sc"><b>303</b> <span class="rp">See Other</span> <span class="ref">15.4.4</span><span class="def">The 303 (See Other) status code indicates that the server is redirecting the user agent to a different resource, as indicated by a URI in the Location header field, which is intended to provide an indirect response to the original request.</span></div>

<div class="sc"><b>304</b> <span class="rp">Not Modified</span> <span class="ref">15.4.5</span><span class="def">The 304 (Not Modified) status code indicates that a conditional GET or HEAD request has been received and would have resulted in a 200 (OK) response if it were not for the fact that the condition evaluated to false.</span></div>

<div class="sc"><b>305</b> <span class="rp">Use Proxy</span> <span class="ref">15.4.6</span><span class="def">The 305 (Use Proxy) status code was defined in a previous version of this specification and is now deprecated (Appendix B of [RFC7231]).</span></div>

<div class="sc"><b>306</b> <span class="rp">(Unused)</span> <span class="ref">15.4.7</span><span class="def">The 306 status code was defined in a previous version of this specification, is no longer used, and the code is reserved.</span></div>

<div class="sc"><b>307</b> <span class="rp">Temporary Redirect</span> <span class="ref">15.4.8</span><span class="def">The 307 (Temporary Redirect) status code indicates that the target resource resides temporarily under a different URI and the user agent MUST NOT change the request method if it performs an automatic redirection to that URI.</span></div>

<div class="sc"><b>308</b> <span class="rp">Permanent Redirect</span> <span class="ref">15.4.9</span><span class="def">The 308 (Permanent Redirect) status code indicates that the target resource has been assigned a new permanent URI and any future references to this resource ought to use one of the enclosed URIs.</span></div>

<div class="sc un"><b>309-399</b> <span class="rp">Unassigned</span></div>

## Client Error 4xx

<p class="clead">The 4xx (Client Error) class of status code indicates that the client seems to have erred.</p>

<div class="sc"><b>400</b> <span class="rp">Bad Request</span> <span class="ref">15.5.1</span><span class="def">The 400 (Bad Request) status code indicates that the server cannot or will not process the request due to something that is perceived to be a client error (e.g., malformed request syntax, invalid request message framing, or deceptive request routing).</span></div>

<div class="sc"><b>401</b> <span class="rp">Unauthorized</span> <span class="ref">15.5.2</span><span class="def">The 401 (Unauthorized) status code indicates that the request has not been applied because it lacks valid authentication credentials for the target resource.</span></div>

<div class="sc"><b>402</b> <span class="rp">Payment Required</span> <span class="ref">15.5.3</span><span class="def">The 402 (Payment Required) status code is reserved for future use.</span></div>

<div class="sc"><b>403</b> <span class="rp">Forbidden</span> <span class="ref">15.5.4</span><span class="def">The 403 (Forbidden) status code indicates that the server understood the request but refuses to fulfill it.</span></div>

<div class="sc"><b>404</b> <span class="rp">Not Found</span> <span class="ref">15.5.5</span><span class="def">The 404 (Not Found) status code indicates that the origin server did not find a current representation for the target resource or is not willing to disclose that one exists.</span></div>

<div class="sc"><b>405</b> <span class="rp">Method Not Allowed</span> <span class="ref">15.5.6</span><span class="def">The 405 (Method Not Allowed) status code indicates that the method received in the request-line is known by the origin server but not supported by the target resource.</span></div>

<div class="sc"><b>406</b> <span class="rp">Not Acceptable</span> <span class="ref">15.5.7</span><span class="def">The 406 (Not Acceptable) status code indicates that the target resource does not have a current representation that would be acceptable to the user agent, according to the proactive negotiation header fields received in the request (Section 12.1), and the server is unwilling to supply a default representation.</span></div>

<div class="sc"><b>407</b> <span class="rp">Proxy Authentication Required</span> <span class="ref">15.5.8</span><span class="def">The 407 (Proxy Authentication Required) status code is similar to 401 (Unauthorized), but it indicates that the client needs to authenticate itself in order to use a proxy for this request.</span></div>

<div class="sc"><b>408</b> <span class="rp">Request Timeout</span> <span class="ref">15.5.9</span><span class="def">The 408 (Request Timeout) status code indicates that the server did not receive a complete request message within the time that it was prepared to wait.</span></div>

<div class="sc"><b>409</b> <span class="rp">Conflict</span> <span class="ref">15.5.10</span><span class="def">The 409 (Conflict) status code indicates that the request could not be completed due to a conflict with the current state of the target resource.</span></div>

<div class="sc"><b>410</b> <span class="rp">Gone</span> <span class="ref">15.5.11</span><span class="def">The 410 (Gone) status code indicates that access to the target resource is no longer available at the origin server and that this condition is likely to be permanent.</span></div>

<div class="sc"><b>411</b> <span class="rp">Length Required</span> <span class="ref">15.5.12</span><span class="def">The 411 (Length Required) status code indicates that the server refuses to accept the request without a defined Content-Length (Section 8.6).</span></div>

<div class="sc"><b>412</b> <span class="rp">Precondition Failed</span> <span class="ref">15.5.13</span><span class="def">The 412 (Precondition Failed) status code indicates that one or more conditions given in the request header fields evaluated to false when tested on the server (Section 13).</span></div>

<div class="sc"><b>413</b> <span class="rp">Content Too Large</span> <span class="ref">15.5.14</span><span class="def">The 413 (Content Too Large) status code indicates that the server is refusing to process a request because the request content is larger than the server is willing or able to process.</span></div>

<div class="sc"><b>414</b> <span class="rp">URI Too Long</span> <span class="ref">15.5.15</span><span class="def">The 414 (URI Too Long) status code indicates that the server is refusing to service the request because the target URI is longer than the server is willing to interpret.</span></div>

<div class="sc"><b>415</b> <span class="rp">Unsupported Media Type</span> <span class="ref">15.5.16</span><span class="def">The 415 (Unsupported Media Type) status code indicates that the origin server is refusing to service the request because the content is in a format not supported by this method on the target resource.</span></div>

<div class="sc"><b>416</b> <span class="rp">Range Not Satisfiable</span> <span class="ref">15.5.17</span><span class="def">The 416 (Range Not Satisfiable) status code indicates that the set of ranges in the request's Range header field (Section 14.2) has been rejected either because none of the requested ranges are satisfiable or because the client has requested an excessive number of small or overlapping ranges (a potential denial of service attack).</span></div>

<div class="sc"><b>417</b> <span class="rp">Expectation Failed</span> <span class="ref">15.5.18</span><span class="def">The 417 (Expectation Failed) status code indicates that the expectation given in the request's Expect header field (Section 10.1.1) could not be met by at least one of the inbound servers.</span></div>

<div class="sc"><b>418</b> <span class="rp">(Unused)</span> <span class="ref">15.5.19</span><span class="def">[RFC2324] was an April 1 RFC that lampooned the various ways HTTP was abused; one such abuse was the definition of an application-specific 418 status code, which has been deployed as a joke often enough for the code to be unusable for any future use.</span></div>

<div class="sc un"><b>419-420</b> <span class="rp">Unassigned</span></div>

<div class="sc"><b>421</b> <span class="rp">Misdirected Request</span> <span class="ref">15.5.20</span><span class="def">The 421 (Misdirected Request) status code indicates that the request was directed at a server that is unable or unwilling to produce an authoritative response for the target URI.</span></div>

<div class="sc"><b>422</b> <span class="rp">Unprocessable Content</span> <span class="ref">15.5.21</span><span class="def">The 422 (Unprocessable Content) status code indicates that the server understands the content type of the request content (hence a 415 (Unsupported Media Type) status code is inappropriate), and the syntax of the request content is correct, but it was unable to process the contained instructions.</span></div>

<div class="sc x"><b>423</b> <span class="rp">Locked</span> <span class="ref">RFC 4918</span></div>

<div class="sc x"><b>424</b> <span class="rp">Failed Dependency</span> <span class="ref">RFC 4918</span></div>

<div class="sc x"><b>425</b> <span class="rp">Too Early</span> <span class="ref">RFC 8470</span></div>

<div class="sc"><b>426</b> <span class="rp">Upgrade Required</span> <span class="ref">15.5.22</span><span class="def">The 426 (Upgrade Required) status code indicates that the server refuses to perform the request using the current protocol but might be willing to do so after the client upgrades to a different protocol.</span></div>

<div class="sc un"><b>427</b> <span class="rp">Unassigned</span></div>

<div class="sc x"><b>428</b> <span class="rp">Precondition Required</span> <span class="ref">RFC 6585</span></div>

<div class="sc x"><b>429</b> <span class="rp">Too Many Requests</span> <span class="ref">RFC 6585</span></div>

<div class="sc un"><b>430</b> <span class="rp">Unassigned</span></div>

<div class="sc x"><b>431</b> <span class="rp">Request Header Fields Too Large</span> <span class="ref">RFC 6585</span></div>

<div class="sc un"><b>432-450</b> <span class="rp">Unassigned</span></div>

<div class="sc x"><b>451</b> <span class="rp">Unavailable For Legal Reasons</span> <span class="ref">RFC 7725</span></div>

<div class="sc un"><b>452-499</b> <span class="rp">Unassigned</span></div>

## Server Error 5xx

<p class="clead">The 5xx (Server Error) class of status code indicates that the server is aware that it has erred or is incapable of performing the requested method.</p>

<div class="sc"><b>500</b> <span class="rp">Internal Server Error</span> <span class="ref">15.6.1</span><span class="def">The 500 (Internal Server Error) status code indicates that the server encountered an unexpected condition that prevented it from fulfilling the request.</span></div>

<div class="sc"><b>501</b> <span class="rp">Not Implemented</span> <span class="ref">15.6.2</span><span class="def">The 501 (Not Implemented) status code indicates that the server does not support the functionality required to fulfill the request.</span></div>

<div class="sc"><b>502</b> <span class="rp">Bad Gateway</span> <span class="ref">15.6.3</span><span class="def">The 502 (Bad Gateway) status code indicates that the server, while acting as a gateway or proxy, received an invalid response from an inbound server it accessed while attempting to fulfill the request.</span></div>

<div class="sc"><b>503</b> <span class="rp">Service Unavailable</span> <span class="ref">15.6.4</span><span class="def">The 503 (Service Unavailable) status code indicates that the server is currently unable to handle the request due to a temporary overload or scheduled maintenance, which will likely be alleviated after some delay.</span></div>

<div class="sc"><b>504</b> <span class="rp">Gateway Timeout</span> <span class="ref">15.6.5</span><span class="def">The 504 (Gateway Timeout) status code indicates that the server, while acting as a gateway or proxy, did not receive a timely response from an upstream server it needed to access in order to complete the request.</span></div>

<div class="sc"><b>505</b> <span class="rp">HTTP Version Not Supported</span> <span class="ref">15.6.6</span><span class="def">The 505 (HTTP Version Not Supported) status code indicates that the server does not support, or refuses to support, the major version of HTTP that was used in the request message.</span></div>

<div class="sc x"><b>506</b> <span class="rp">Variant Also Negotiates</span> <span class="ref">RFC 2295</span></div>

<div class="sc x"><b>507</b> <span class="rp">Insufficient Storage</span> <span class="ref">RFC 4918</span></div>

<div class="sc x"><b>508</b> <span class="rp">Loop Detected</span> <span class="ref">RFC 5842</span></div>

<div class="sc un"><b>509</b> <span class="rp">Unassigned</span></div>

<div class="sc x"><b>510</b> <span class="rp">Not Extended</span> <span class="ref">RFC 2774 · Status change of HTTP experiments to Historic</span><span class="def">OBSOLETED</span></div>

<div class="sc x"><b>511</b> <span class="rp">Network Authentication Required</span> <span class="ref">RFC 6585</span></div>

<div class="sc un"><b>512-599</b> <span class="rp">Unassigned</span></div>
