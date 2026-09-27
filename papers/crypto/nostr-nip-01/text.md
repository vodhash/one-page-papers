This NIP defines the basic protocol that should be implemented by everybody. New NIPs may add new optional (or mandatory) fields and messages and features to the structures and flows described here.

## Events and signatures

Each user has a keypair. Signatures, public key, and encodings are done according to the Schnorr signatures standard for the curve `secp256k1`.

The only object type that exists is the `event`, which has the following format on the wire:

<pre class="code nip"><span class="l">{</span><span class="l">  "id": &lt;32-bytes lowercase hex-encoded sha256 of the serialized event data&gt;,</span><span class="l">  "pubkey": &lt;32-bytes lowercase hex-encoded public key of the event creator&gt;,</span><span class="l">  "created_at": &lt;unix timestamp in seconds&gt;,</span><span class="l">  "kind": &lt;integer between 0 and 65535&gt;,</span><span class="l">  "tags": [</span><span class="l">    [&lt;arbitrary string&gt;...],</span><span class="l">    // ...</span><span class="l">  ],</span><span class="l">  "content": &lt;arbitrary string&gt;,</span><span class="l">  "sig": &lt;64-bytes lowercase hex of the signature of the sha256 hash of the serialized event data, which is the same as the "id" field&gt;</span><span class="l">}</span></pre>

To obtain the `event.id`, we `sha256` the serialized event. The serialization is done over the UTF-8 JSON-serialized string (which is described below) of the following structure:

<pre class="code nip"><span class="l">[</span><span class="l">  0,</span><span class="l">  &lt;pubkey, as a lowercase hex string&gt;,</span><span class="l">  &lt;created_at, as a number&gt;,</span><span class="l">  &lt;kind, as a number&gt;,</span><span class="l">  &lt;tags, as an array of arrays of non-null strings&gt;,</span><span class="l">  &lt;content, as a string&gt;</span><span class="l">]</span></pre>

To prevent implementation differences from creating a different event ID for the same event, the following rules MUST be followed while serializing:

<ul><li>UTF-8 should be used for encoding.</li><li>Whitespace, line breaks or other unnecessary formatting should not be included in the output JSON.</li><li>The following characters in the content field must be escaped as shown, and all other characters must be included verbatim:<ul><li>A line break (<code>0x0A</code>), use <code>\n</code></li><li>A double quote (<code>0x22</code>), use <code>\&quot;</code></li><li>A backslash (<code>0x5C</code>), use <code>\\</code></li><li>A carriage return (<code>0x0D</code>), use <code>\r</code></li><li>A tab character (<code>0x09</code>), use <code>\t</code></li><li>A backspace, (<code>0x08</code>), use <code>\b</code></li><li>A form feed, (<code>0x0C</code>), use <code>\f</code></li></ul></li></ul>

### Tags

Each tag is an array of one or more strings, with some conventions around them. Take a look at the example below:

<pre class="code nip"><span class="l">{</span><span class="l">  "tags": [</span><span class="l">    ["e", "5c83da77af1dec6d7289834998ad7aafbd9e2191396d75ec3cc27f5a77226f36", "wss://nostr.example.com"],</span><span class="l">    ["p", "f7234bd4c1394dda46d09f35bd384dd30cc552ad5541990f98844fb06676e9ca"],</span><span class="l">    ["a", "30023:f7234bd4c1394dda46d09f35bd384dd30cc552ad5541990f98844fb06676e9ca:abcd", "wss://nostr.example.com"],</span><span class="l">    ["alt", "reply"],</span><span class="l">    // ...</span><span class="l">  ],</span><span class="l">  // ...</span><span class="l">}</span></pre>

The first element of the tag array is referred to as the tag *name* or *key* and the second as the tag *value*. So we can safely say that the event above has an `e` tag set to `"5c83da77af1dec6d7289834998ad7aafbd9e2191396d75ec3cc27f5a77226f36"`, an `alt` tag set to `"reply"` and so on. All elements after the second do not have a conventional name.

This NIP defines 3 standard tags that can be used across all event kinds with the same meaning. They are as follows:

<ul><li>The <code>e</code> tag, used to refer to an event: <code>[&quot;e&quot;, &lt;32-bytes lowercase hex of the id of another event&gt;, &lt;recommended relay URL, optional&gt;, &lt;32-bytes lowercase hex of the author&#x27;s pubkey, optional&gt;]</code></li><li>The <code>p</code> tag, used to refer to another user: <code>[&quot;p&quot;, &lt;32-bytes lowercase hex of a pubkey&gt;, &lt;recommended relay URL, optional&gt;]</code></li><li>The <code>a</code> tag, used to refer to an addressable or replaceable event<ul><li>for an addressable event: <code>[&quot;a&quot;, &quot;&lt;kind integer&gt;:&lt;32-bytes lowercase hex of a pubkey&gt;:&lt;d tag value&gt;&quot;, &lt;recommended relay URL, optional&gt;]</code></li><li>for a normal replaceable event: <code>[&quot;a&quot;, &quot;&lt;kind integer&gt;:&lt;32-bytes lowercase hex of a pubkey&gt;:&quot;, &lt;recommended relay URL, optional&gt;]</code> (note: include the trailing colon)</li></ul></li></ul>

As a convention, all single-letter (only english alphabet letters: a-z, A-Z) key tags are expected to be indexed by relays, such that it is possible, for example, to query or subscribe to events that reference the event `"5c83da77af1dec6d7289834998ad7aafbd9e2191396d75ec3cc27f5a77226f36"` by using the `{"#e": ["5c83da77af1dec6d7289834998ad7aafbd9e2191396d75ec3cc27f5a77226f36"]}` filter. Only the first value in any given tag is indexed.

### Kinds

Kinds specify how clients should interpret the meaning of each event and the other fields of each event (e.g. an `"r"` tag may have a meaning in an event of kind 1 and an entirely different meaning in an event of kind 10002). Each NIP may define the meaning of a set of kinds that weren't defined elsewhere. NIP-10, for instance, specifies the `kind:1` text note for social media applications.

This NIP defines one basic kind:

<ul><li><code>0</code>: <b>user metadata</b>: the <code>content</code> is set to a stringified JSON object <code>{name: &lt;nickname or full name&gt;, about: &lt;short bio&gt;, picture: &lt;url of the image&gt;}</code> describing the user who created the event. Extra metadata fields may be set. A relay may delete older events once it gets a new one for the same pubkey.</li></ul>

And also a convention for kind ranges that allow for easier experimentation and flexibility of relay implementation:

<ul><li>for kind <code>n</code> such that <code>1000 &lt;= n &lt; 10000 || 4 &lt;= n &lt; 45 || n == 1 || n == 2</code>, events are <b>regular</b>, which means they’re all expected to be stored by relays.</li><li>for kind <code>n</code> such that <code>10000 &lt;= n &lt; 20000 || n == 0 || n == 3</code>, events are <b>replaceable</b>, which means that, for each combination of <code>pubkey</code> and <code>kind</code>, only the latest event MUST be stored by relays, older versions MAY be discarded.</li><li>for kind <code>n</code> such that <code>20000 &lt;= n &lt; 30000</code>, events are <b>ephemeral</b>, which means they are not expected to be stored by relays.</li><li>for kind <code>n</code> such that <code>30000 &lt;= n &lt; 40000</code>, events are <b>addressable</b> by their <code>kind</code>, <code>pubkey</code> and <code>d</code> tag value -- which means that, for each combination of <code>kind</code>, <code>pubkey</code> and the <code>d</code> tag value, only the latest event MUST be stored by relays, older versions MAY be discarded.</li></ul>

In case of replaceable events with the same timestamp, the event with the lowest id (first in lexical order) should be retained, and the other discarded.

When answering to `REQ` messages for replaceable events such as `{"kinds":[0],"authors":[<hex-key>]}`, even if the relay has more than one version stored, it SHOULD return just the latest one.

These are just conventions and relay implementations may differ.

## Communication between clients and relays

Relays expose a websocket endpoint to which clients can connect. Clients SHOULD open a single websocket connection to each relay and use it for all their subscriptions. Relays MAY limit number of connections from specific IP/client/etc.

Relays MUST only accept connections to a single endpoint when additional path segments do not influence its behavior.

### From client to relay: sending events and creating subscriptions

Clients can send 3 types of messages, which must be JSON arrays, according to the following patterns:

<ul><li><code>[&quot;EVENT&quot;, &lt;event JSON as defined above&gt;]</code>, used to publish events.</li><li><code>[&quot;REQ&quot;, &lt;subscription_id&gt;, &lt;filters1&gt;, &lt;filters2&gt;, ...]</code>, used to request events and subscribe to new updates.</li><li><code>[&quot;CLOSE&quot;, &lt;subscription_id&gt;]</code>, used to stop previous subscriptions.</li></ul>

`<subscription_id>` is an arbitrary, non-empty string of max length 64 chars. It represents a subscription per connection. Relays MUST manage `<subscription_id>`s independently for each WebSocket connection. `<subscription_id>`s are not guaranteed to be globally unique.

`<filtersX>` is a JSON object that determines what events will be sent in that subscription, it can have the following attributes:

<pre class="code nip"><span class="l">{</span><span class="l">  "ids": &lt;a list of event ids&gt;,</span><span class="l">  "authors": &lt;a list of lowercase pubkeys, the pubkey of an event must be one of these&gt;,</span><span class="l">  "kinds": &lt;a list of a kind numbers&gt;,</span><span class="l">  "#&lt;single-letter (a-zA-Z)&gt;": &lt;a list of tag values, for #e — a list of event ids, for #p — a list of pubkeys, etc.&gt;,</span><span class="l">  "since": &lt;an integer unix timestamp in seconds. Events must have a created_at &gt;= to this to pass&gt;,</span><span class="l">  "until": &lt;an integer unix timestamp in seconds. Events must have a created_at &lt;= to this to pass&gt;,</span><span class="l">  "limit": &lt;maximum number of events relays SHOULD return in the initial query&gt;</span><span class="l">}</span></pre>

Upon receiving a `REQ` message, the relay SHOULD return events that match the filter. Any new events it receives SHOULD be sent to that same websocket until the connection is closed, a `CLOSE` event is received with the same `<subscription_id>`, or a new `REQ` is sent using the same `<subscription_id>` (in which case a new subscription is created, replacing the old one).

Filter attributes containing lists (`ids`, `authors`, `kinds` and tag filters like `#e`) are JSON arrays with one or more values. At least one of the arrays' values must match the relevant field in an event for the condition to be considered a match. For scalar event attributes such as `authors` and `kind`, the attribute from the event must be contained in the filter list. In the case of tag attributes such as `#e`, for which an event may have multiple values, the event and filter condition values must have at least one item in common.

The `ids`, `authors`, `#e` and `#p` filter lists MUST contain exact 64-character lowercase hex values.

The `since` and `until` properties can be used to specify the time range of events returned in the subscription. If a filter includes the `since` property, events with `created_at` greater than or equal to `since` are considered to match the filter. The `until` property is similar except that `created_at` must be less than or equal to `until`. In short, an event matches a filter if `since <= created_at <= until` holds.

All conditions of a filter that are specified must match for an event for it to pass the filter, i.e., multiple conditions are interpreted as `&&` conditions.

A `REQ` message may contain multiple filters. In this case, events that match any of the filters are to be returned, i.e., multiple filters are to be interpreted as `||` conditions.

The `limit` property of a filter is only valid for the initial query and MUST be ignored afterwards. When `limit: n` is present it is assumed that the events returned in the initial query will be the last `n` events ordered by the `created_at`. Newer events should appear first, and in the case of ties the event with the lowest id (first in lexical order) should be first. Relays SHOULD use the `limit` value to guide how many events are returned in the initial response. Returning fewer events is acceptable, but returning (much) more should be avoided to prevent overwhelming clients.

When `limit` is zero, the relay MUST NOT return stored events for that filter. After the initial queries for all filters are complete, the relay MUST send `EOSE` and MUST keep the subscription active for newly received matching events.

### From relay to client: sending events and notices

Relays can send 5 types of messages, which must also be JSON arrays, according to the following patterns:

<ul><li><code>[&quot;EVENT&quot;, &lt;subscription_id&gt;, &lt;event JSON as defined above&gt;]</code>, used to send events requested by clients.</li><li><code>[&quot;OK&quot;, &lt;event_id&gt;, &lt;true|false&gt;, &lt;message&gt;]</code>, used to indicate acceptance or denial of an <code>EVENT</code> message.</li><li><code>[&quot;EOSE&quot;, &lt;subscription_id&gt;]</code>, used to indicate the <i>end of stored events</i> and the beginning of events newly received in real-time.</li><li><code>[&quot;CLOSED&quot;, &lt;subscription_id&gt;, &lt;message&gt;]</code>, used to indicate that a subscription was ended on the server side.</li><li><code>[&quot;NOTICE&quot;, &lt;message&gt;]</code>, used to send human-readable error messages or other things to clients.</li></ul>

This NIP defines no rules for how `NOTICE` messages should be sent or treated.

<ul><li><code>EVENT</code> messages MUST be sent only with a subscription ID related to a subscription previously initiated by the client (using the <code>REQ</code> message above).</li><li><code>OK</code> messages MUST be sent in response to <code>EVENT</code> messages received from clients, they must have the 3rd parameter set to <code>true</code> when an event has been accepted by the relay, <code>false</code> otherwise. The 4th parameter MUST always be present, but MAY be an empty string when the 3rd is <code>true</code>, otherwise it MUST be a string formed by a machine-readable single-word prefix followed by a <code>:</code> and then a human-readable message. Some examples:<ul><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, true, &quot;&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, true, &quot;pow: difficulty 25&gt;=24&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, true, &quot;duplicate: already have this event&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, false, &quot;blocked: you are banned from posting here&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, false, &quot;blocked: please register your pubkey at https://my-expensive-relay.example.com&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, false, &quot;rate-limited: slow down there chief&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, false, &quot;invalid: event creation date is too far off from the current time&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, false, &quot;pow: difficulty 26 is less than 30&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, false, &quot;restricted: not allowed to write.&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, false, &quot;error: could not connect to the database&quot;]</code></li><li><code>[&quot;OK&quot;, &quot;b1a649ebe8...&quot;, false, &quot;mute: no one was listening to your ephemeral event and it wasn&#x27;t handled in any way, it was ignored&quot;]</code></li></ul></li><li><code>CLOSED</code> messages MUST be sent in response to a <code>REQ</code> when the relay refuses to fulfill it. It can also be sent when a relay decides to kill a subscription on its side before a client has disconnected or sent a <code>CLOSE</code>. This message uses the same pattern of <code>OK</code> messages with the machine-readable prefix and human-readable message. Some examples:<ul><li><code>[&quot;CLOSED&quot;, &quot;sub1&quot;, &quot;unsupported: filter contains unknown elements&quot;]</code></li><li><code>[&quot;CLOSED&quot;, &quot;sub1&quot;, &quot;error: could not connect to the database&quot;]</code></li><li><code>[&quot;CLOSED&quot;, &quot;sub1&quot;, &quot;error: shutting down idle subscription&quot;]</code></li></ul></li><li>The standardized machine-readable prefixes for <code>OK</code> and <code>CLOSED</code> are: <code>duplicate</code>, <code>pow</code>, <code>blocked</code>, <code>rate-limited</code>, <code>invalid</code>, <code>restricted</code>, <code>mute</code> and <code>error</code> for when none of that fits.</li></ul>
