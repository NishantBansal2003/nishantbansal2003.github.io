---
title: "LND: Zero-Timestamp Gossip DoS"
date: 2026-06-18 10:30:00 +0530
categories: [lightning]
tags: [lightning, security, dos, lnd, fuzzing]
description: Technical analysis of a zero-timestamp channel update DoS vulnerability in LND.
image: ../assets/img/lnd-zero-timestamp-dos.png
---

LND versions before _v0.20.1_ are vulnerable to a DoS issue where a specially crafted `channel_update` message can crash a node. Operators should upgrade promptly to avoid service disruption. The issue is fixed in [v0.20.1](https://github.com/lightningnetwork/lnd/releases/tag/v0.20.1-beta) and later.

## Vulnerability

The Lightning Network uses [gossip messages](https://github.com/lightning/bolts/blob/master/07-routing-gossip.md) to maintain a distributed view of the network graph. Nodes exchange `channel_announcement`, `node_announcement`, and `channel_update` messages to advertise channels and routing policies. Before accepting `node_announcement` and `channel_update` messages, a Lightning node must first know and validate the corresponding `channel_announcement`.

After validation, `channel_update` messages are propagated throughout the network. In LND, this propagation is handled by a gossip rebroadcast pipeline that uses a de-duplication cache to avoid repeatedly forwarding identical updates. When a new update arrives, its timestamp is compared against any previously stored update for the same channel and direction. Newer updates replace older ones, while older updates are discarded. The implementation of this logic prior to _v0.20.1_ can be found in [`deDupedAnnouncements.addMsg`](https://github.com/lightningnetwork/lnd/blob/91423ee5198e116b210f7f1c2e8b506d5ab28266/discovery/gossiper.go#L1133-L1189).

The bug stems from how updates with a timestamp of 0 are handled. When a zero-timestamp `channel_update` is received for the first time, no cache entry exists and `oldTimestamp` remains initialized to 0. As a result, the code incorrectly treats the update as a previously seen message and enters the duplicate-message path: [`deDupedAnnouncements.addMsg.duplicate-update`](https://github.com/lightningnetwork/lnd/blob/91423ee5198e116b210f7f1c2e8b506d5ab28266/discovery/gossiper.go#L1183-L1188).

However, because no previous entry existed, `mws.senders` was never initialized. Attempting to write to this nil map triggers a runtime panic that terminates the LND daemon, resulting in a complete loss of node availability until it is restarted.

## DoS Attack

As discussed in the previous section, the panic is triggered only after a `channel_update` has passed validation and entered LND's gossip rebroadcast pipeline. Because gossip messages are authenticated, an attacker cannot simply modify an existing message; doing so would invalidate its signature and cause it to be rejected before reaching the vulnerable code path.

To exploit the bug, the attacker must generate a validly signed `channel_update` with a timestamp of 0.

### Method 1: Advertise a Real Channel

The simplest approach is to open a public Lightning channel and advertise it normally. When broadcasting the corresponding `channel_update`, the attacker sets the timestamp to 0. A vulnerable LND node will accept the update and eventually trigger the panic.

#### Attack Cost

This approach requires opening and eventually closing a public Lightning channel, incurring the associated on-chain fees. Furthermore, once the victim has processed the malicious update and restarted, the same update may be rejected as stale gossip, requiring a new channel to repeat the attack.

### Method 2: Advertise a Synthetic Channel

A more efficient approach avoids opening a Lightning channel altogether. The attacker creates a funding transaction paying to a _2-of-2 P2WSH_ output controlled entirely by keys they own. After the funding transaction confirms, the attacker has sufficient information to construct a valid `channel_announcement` for a channel that does not correspond to any running Lightning node.

Once the victim accepts the announcement, the attacker sends a corresponding zero-timestamp `channel_update`, triggering the panic. Because both channel endpoints are attacker-controlled, multiple valid updates can be generated using different node identities without incurring channel-closing costs.

#### Attack Cost

This method requires only a funding transaction and its associated confirmation fees. Additional announcements can be created from newly funded outputs, keeping the cost of repeated exploitation relatively low.

## Fix

BOLT 7 specifies that the sender of a `channel_update` _MUST set `timestamp` to greater than 0_, but does not explicitly define how receiving nodes should handle violations of this requirement. Due to this ambiguity, LND implicitly assumed that timestamps would always be valid.

The fix rejects zero-timestamp updates early in the validation phase, so they never reach the gossip rebroadcast pipeline, fully mitigating the DoS condition. It can be found in [AuthenticatedGossiper.handleChanUpdate](https://github.com/lightningnetwork/lnd/blob/6b27461f001a9dbc547f707d5c5e05b55137f741/discovery/gossiper.go#L3173-L3192).

## Discovery

The vulnerability was discovered while developing a gossip-discovery state-machine fuzz target for LND, designed to exercise the gossip subsystem with both valid and malformed messages to ensure that the implementation handled them safely.

Given that Lightning gossip messages are widely propagated and inexpensive to generate, the subsystem represents a high-value attack surface. During fuzzing, a specific message sequence triggered a panic in LND's discovery subsystem, leading to the identification of a zero-timestamp `channel_update` vulnerability.

The fuzz target used for discovery is available in the associated [pull request](https://github.com/lightningnetwork/lnd/pull/10605).

### Timeline

- **2025-12-15:** Vulnerability discovered during fuzzing of the gossip-discovery state machine.
- **2025-12-17:** Independently confirmed by [Matt](https://github.com/morehouse) using an attack program.
- **2025-12-18:** Privately disclosed to the LND security mailing list.
- **2026-01-12:** Fix [merged](https://github.com/lightningnetwork/lnd/pull/10469) into LND.
- **2026-02-12:** LND _v0.20.1_ released with the fix.
- **2026-06-16:** [Gijs](https://github.com/gijswijs) confirms that the vulnerability can be disclosed publicly.
- **2026-06-18:** Public disclosure of the vulnerability.

## Remarks

- This issue highlights the value of state-machine fuzzing in Lightning implementations, as protocol transition bugs are often missed by fuzzers focused only on message parsing.
- The lack of an explicit requirement for handling invalid protocol message fields in the BOLT specification can lead to inconsistent implementations. Explicitly defining rejection behavior, or enforcing defensive validation in implementations, would help prevent similar issues.
