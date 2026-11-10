---
title: "LND: Malformed Channel Announcement Gossip Stall"
date: 2026-09-24 10:30:00 +0530
categories: [Lightning, Security]
tags: [lnd, deadlock, bolt7, fuzzing, smite]
description: Technical analysis of a gossip stall in LND triggered by malformed channel announcements.
image:
  path: /assets/img/lnd-malformed-channel-announcement-gossip-stall.png
  alt: Malformed channel announcements stalling an LND node's gossiper
disclosure:
  affected: "v0.19.0 through v0.20.0"
  fixed: v0.20.1
  fixed_url: https://github.com/lightningnetwork/lnd/releases/tag/v0.20.1-beta
  impact: Remote gossip stall
---

LND _v0.19.0_ through _v0.20.0_ can send two validation results for a gossip message on a channel that has room for only one.
The goroutine processing the message blocks forever and never releases its slot in the gossiper's validation barrier, which limits in-flight gossip processing to 1,000 messages.
An attacker that sends **1,000** such announcements occupies every slot, causing the node to stop processing gossip entirely, effectively cutting it off from the routing network.
LND keeps running but hangs on graceful shutdown, so the operator must kill it to recover, and the attack can be easily repeated after it restarts.

Upgrade to [LND v0.20.1](https://github.com/lightningnetwork/lnd/releases/tag/v0.20.1-beta) or later.

## Background

Nodes learn the channel graph from [BOLT 7](https://github.com/lightning/bolts/blob/152897261850d93c4f4597f39cf22d7d22d6ede6/07-routing-gossip.md) gossip.
A `channel_announcement` identifies a channel by its `short_channel_id` and names its two endpoints, `node_id_1` and `node_id_2`.

LND processes each incoming gossip message in its own goroutine.
Before starting one, the gossiper's `ValidationBarrier` reserves one of [1,000 slots](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/gossiper.go#L602) and records which messages depend on which, e.g. a `channel_update` waits for its `channel_announcement`.
A `channel_announcement` is registered under three keys: its `short_channel_id`, `node_id_1`, and `node_id_2`.

Each message also carries an error channel, a Go channel for its processing result.
For messages from peers, [`ProcessRemoteAnnouncement`](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/gossiper.go#L883) creates it with a buffer of one, and nothing reads from it.

## The vulnerability

LND v0.19.0 through v0.20.0 process each gossip message and then notify its dependent jobs in [`handleNetworkMessages`](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/gossiper.go#L1629-L1687):

```go
func (d *AuthenticatedGossiper) handleNetworkMessages(ctx context.Context,
	nMsg *networkMsg, deDuped *deDupedAnnouncements, jobID JobID) {
	// ... mark the goroutine done on return.
	defer d.finalizeGossipProcessing(ctx, "processing", nMsg, &jobID)
	// ... wait for this message's parent jobs to finish.
	newAnns, allow := d.processNetworkAnnouncement(ctx, nMsg)
	// ... log the processing result.
	err = d.vb.SignalDependents(nMsg.msg, jobID)
	if err != nil {
		// ... log the error.
		nMsg.err <- err

		return
	}
	// ... queue newAnns for broadcast.
}
```

For a `channel_announcement`, `processNetworkAnnouncement` calls [`handleChanAnnouncement`](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/gossiper.go#L2679-L3110), which sends exactly one result on the `nMsg.err` channel, such as the error when the announcement [fails validation](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/gossiper.go#L2783-L2799).
That result fills the channel's buffer.
If `SignalDependents` then fails, its error is a second send on `nMsg.err`, which blocks forever because nothing reads from the channel.

`SignalDependents` fails when `node_id_1 == node_id_2`.
It [removes the job under each of the three keys](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/validation_barrier.go#L428-L445), but with equal node IDs the job was registered under only two.
The removal under `node_id_1` deletes the node ID's entry, so the removal under `node_id_2` [finds nothing and returns an error](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/validation_barrier.go#L377-L383).

Because the goroutine never returns, the deferred `finalizeGossipProcessing` never [calls `CompleteJob`](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/gossiper.go#L1702), so its validation barrier slot is never released.
Once all 1,000 slots have leaked, the gossiper's main loop blocks forever in [`InitJobDependencies`](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/validation_barrier.go#L100-L110) waiting for a free slot.

## The attack

An attacker connects to the victim LND node, completes the BOLT 8 handshake, and exchanges `init` messages.
The attacker then sends 1,000 `channel_announcement` messages with `node_id_1 == node_id_2` and at least one other invalid field, such as `bitcoin_key_1`, so no real channel is needed.
Each message uses a different `short_channel_id` and node ID, so LND's [reject cache](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/gossiper.go#L1554-L1564) does not drop it and no other in-flight job [keeps its node ID's entry alive](https://github.com/lightningnetwork/lnd/blob/eaa7bcf67ad1ed9884ca6aad3931c2b9dc81bbeb/discovery/validation_barrier.go#L114-L123).

Each message leaks a validation barrier slot, and once all 1,000 have leaked, the gossiper stops processing gossip from every peer.

### Observed impact

From then on, anything that hands the gossiper an announcement or update blocks:

- The graph goes stale and the node's channels become effectively private, so it can no longer find routes or forward payments.
- Each peer connection freezes once its `Brontide` gossip queue fills (~50 messages), then times out.
- The funding manager hangs announcing new channels, so channel opens never complete.
- `ChanStatusManager` hangs, so channels can't be enabled or disabled and force closes hang.
- Graceful shutdown hangs.

A restart clears the stall, but the attacker can easily repeat the attack.
LND still handles on-chain events, including expiring HTLCs, so funds are not at risk.

## The fix

[PR #10540](https://github.com/lightningnetwork/lnd/pull/10540), merged 2026-02-04 and backported to v0.20.1 in [PR #10554](https://github.com/lightningnetwork/lnd/pull/10554), gives `ProcessRemoteAnnouncement`'s error channel [a buffer of two](https://github.com/lightningnetwork/lnd/blob/f9e3825601755701a1d5887d7ea0289776544d7f/discovery/gossiper.go#L890).
The second send from `SignalDependents` now fits in the buffer instead of blocking, so the goroutine returns and releases its validation barrier slot.

See also [Lightning Labs' advisory](https://security.lightning.engineering/2026/09/21/lnd-gossip-validation-barrier-stall.html).

## Discovery

[Matt](https://github.com/morehouse) and I independently found the double send on the error channel, with different fuzzers.

Matt found it with smite as a hang on shutdown and fixed it in [PR #10540](https://github.com/lightningnetwork/lnd/pull/10540).

I found it with the gossip fuzz target later proposed in [PR #10605](https://github.com/lightningnetwork/lnd/pull/10605), realized that each stuck goroutine also leaks a validation barrier slot, and reported the resulting gossiper stall privately to Lightning Labs so the fix would be backported.

### Timeline

- **2026-02-02:** [PR #10540](https://github.com/lightningnetwork/lnd/pull/10540) opened to fix the shutdown hang found by smite.
- **2026-02-03:** Nishant found the same bug with the gossip fuzz target.
- **2026-02-04:** Fix merged as PR #10540.
- **2026-02-05:** Gossiper stall reported privately to Lightning Labs, who agreed to backport the fix.
- **2026-02-06:** Backport merged as [PR #10554](https://github.com/lightningnetwork/lnd/pull/10554).
- **2026-02-12:** [LND v0.20.1](https://github.com/lightningnetwork/lnd/releases/tag/v0.20.1-beta) released with the fix.
- **2026-09-21:** [Public disclosure](https://security.lightning.engineering/2026/09/21/lnd-gossip-validation-barrier-stall.html) by Lightning Labs.
- **2026-09-24:** Public disclosure.

## Takeaways

- **Upgrade to LND v0.20.1 or later.**
- **Treat hangs as security bugs.**
  A stuck goroutine can hold shared resources that peers can exhaust.
