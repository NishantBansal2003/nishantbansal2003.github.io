---
title: "CLN: Reused Funding Outpoint DoS"
date: 2026-11-10 10:30:00 +0530
categories: [Lightning, Security]
tags: [cln, dos, bolt2, fuzzing, smite]
description: Technical analysis of a reused funding outpoint DoS vulnerability in CLN.
image:
  path: /assets/img/cln-reused-funding-outpoint-dos.png
  alt: Two channels opened on the same funding outpoint crashing a CLN node
disclosure:
  affected: "v0.12.0 through v26.06.2"
  fixed: v26.06.6
  fixed_url: https://github.com/ElementsProject/lightning/releases/tag/v26.06.6
  impact: Remote node crash
---

Core Lightning _v0.12.0_ through _v26.06.2_ accept a `funding_created` that reuses the funding outpoint of an existing channel.
Since a v1 `channel_id` is derived from the funding outpoint, two channels opened on the same outpoint share a `channel_id`.
On reconnect, CLN hands its connection daemon a subdaemon for each channel, but the daemon looks them up by `channel_id` and finds the first one both times, so the second trips an assertion that crashes the whole node.
The outpoint never has to exist on chain, so the attack is **free**, and the attacker can crash the node again by reconnecting after **every restart**.

Upgrade to [Core Lightning v26.06.6](https://github.com/ElementsProject/lightning/releases/tag/v26.06.6) or later.

## Background

The opener of a v1 channel names the funding outpoint in `funding_created`, and the _fundee_ answers with `funding_signed` before the funding transaction is broadcast.
Both sides then identify the channel by a `channel_id` that BOLT 2 [derives](https://github.com/lightning/bolts/blob/191462825ae341f0a27098765c075f01ca9bc6c2/02-peer-protocol.md?plain=1#L62-L64) by XORing the funding output index into the funding txid, so two channels on the same outpoint share a `channel_id`.

Core Lightning runs each channel in its own subdaemon, `channeld`, and its `connectd` daemon routes each peer message to the subdaemon for its `channel_id`.
When a peer reconnects, `lightningd` starts a fresh subdaemon for each channel and hands it to `connectd`.

## The vulnerability

When CLN v26.06.2 is the fundee and receives `funding_created`, [`opening_fundee_finished()`](https://github.com/ElementsProject/lightning/blob/15a66cbc052f08c83daa8105bbe87d240e5c4980/lightningd/opening_control.c#L476-L581) derives the `channel_id` and saves the channel without looking for an existing channel on the same outpoint:

```c
static void opening_fundee_finished(struct subd *openingd,
				    const u8 *reply,
				    const int *fds,
				    struct uncommitted_channel *uc)
{
	/* ... parse openingd's reply. */

	derive_channel_id(&cid, &funding);

	/* old_remote_per_commit not valid yet, copy valid one. */
	channel_info.old_remote_per_commit = channel_info.remote_per_commit;

	/* Consumes uc */
	channel = wallet_commit_channel(ld, uc,
					&cid,
					remote_commit,
					&remote_commit_sig,
					&funding,
					funding_sats,
					push,
					channel_flags,
					&channel_info,
					feerate,
					local_upfront_shutdown_script,
					remote_upfront_shutdown_script,
					type,
					NULL,
					false);
	/* ... handle failure, watch the funding tx, notify plugins. */

	/* On to normal operation (frees if it fails!) */
	if (peer_start_channeld(channel, peer_fd, fwd_msg, false))
		tal_free(uc);
	return;

failed:
	tal_free(uc);
}
```

`fwd_msg` is the `funding_signed`, which `channeld` sends on startup.
The database doesn't catch the duplicate either, since it keys channels by an auto-incrementing ID.
So a peer that runs the funding flow twice with the same outpoint gets `funding_signed` both times, leaving the victim with two channels that share a `channel_id`.

The rest of CLN assumes `channel_id`s are unique.
Both [`find_channel_by_id()`](https://github.com/ElementsProject/lightning/blob/15a66cbc052f08c83daa8105bbe87d240e5c4980/lightningd/channel.c#L870-L880) in `lightningd` and [`find_subd()`](https://github.com/ElementsProject/lightning/blob/15a66cbc052f08c83daa8105bbe87d240e5c4980/connectd/multiplex.c#L63-L86) in `connectd` return the first match, so the second channel can never be found by its `channel_id`.

### Reconnecting crashes `connectd`

When the peer reconnects, `lightningd` [loops over its channels](https://github.com/ElementsProject/lightning/blob/15a66cbc052f08c83daa8105bbe87d240e5c4980/lightningd/peer_control.c#L1567-L1582) and hands `connectd` a subdaemon for each one, identified only by `channel_id`.
[`peer_connect_subd()`](https://github.com/ElementsProject/lightning/blob/15a66cbc052f08c83daa8105bbe87d240e5c4980/connectd/multiplex.c#L1685-L1736) handles each request:

```c
void peer_connect_subd(struct daemon *daemon, const u8 *msg, int fd)
{
	/* ... parse the request and look up the peer. */

	/* If peer said something, we created this and queued msg. */
	subd = find_subd(peer, &channel_id);
	if (!subd) {
		subd = new_subd(peer, &channel_id);
		/* Implies lightningd is ready for another peer. */
		release_one_waiting_connection(peer->daemon,
					       tal_fmt(tmpctx, "%s given a subd",
						       fmt_node_id(tmpctx, &id)));
	}

	assert(!subd->conn);

	/* This sets subd->conn inside subd_conn_init, and reparents subd! */
	io_new_conn(peer, fd, subd_conn_init, subd);
}
```

The first request finds or creates the subdaemon for that `channel_id` and gives it the connection.
The second request carries the same `channel_id`, so `find_subd()` returns that same subdaemon, which already has a connection, and `assert(!subd->conn)` fails.
`connectd` aborts, and because `lightningd` [treats that as fatal](https://github.com/ElementsProject/lightning/blob/15a66cbc052f08c83daa8105bbe87d240e5c4980/lightningd/subd.c#L663-L669), the whole node goes down.
Both channels are still in the database after a restart, so the next reconnect crashes the node again.

The assertion was [added](https://github.com/ElementsProject/lightning/commit/41b379ed897ad24bf2d68ce022eb15339e430761) in v0.12.0, when `lightningd` began handing connections to `connectd` per channel.
Releases before v0.12.0 also lack the outpoint check but don't crash, because their `connectd` [ignored](https://github.com/ElementsProject/lightning/blob/c9587ab17b58b8d3c1b03f009580e14f261fa8e1/connectd/multiplex.c#L491-L515) a request for a `channel_id` it already had a subdaemon for.

## The attack

An attacker completes the BOLT 8 handshake and `init` exchange as an ordinary peer.
It then runs the v1 funding flow twice, naming the same outpoint in both `funding_created` messages and receiving `funding_signed` each time.
The outpoint never has to exist on chain, so the attack costs nothing.
Finally, the attacker disconnects and reconnects, and the request for the second channel trips the assertion in `connectd`.

### Observed impact

The node goes down on the first reconnect and again on every reconnect after a restart, so the attacker can keep it offline at no further cost.
While it is down, the node can't watch the chain, so it can miss a peer broadcasting a revoked commitment or an HTLC it must claim before it expires, putting funds in its other channels at risk.

## The fix

[PR #9318](https://github.com/ElementsProject/lightning/pull/9318), merged 2026-07-16 and released in v26.06.6, makes two changes.
First, [`opening_fundee_finished()`](https://github.com/ElementsProject/lightning/blob/c7a013c821432d598a1dee39714ad667fffcdd73/lightningd/opening_control.c#L476-L590) now checks the funding outpoint against the peer's other channels and, on a match, disconnects before the channel is stored or `funding_signed` is sent:

```c
static void opening_fundee_finished(struct subd *openingd,
				    const u8 *reply,
				    const int *fds,
				    struct uncommitted_channel *uc)
{
	/* ... parse openingd's reply. */

	derive_channel_id(&cid, &funding);

	/* A funding outpoint funds at most one channel; don't accept a second
	 * channel reusing one we already have.  Drop the connection so the
	 * peer's open fails cleanly instead of waiting for funding_signed. */
	if (find_channel_by_funding_outpoint(uc->peer, &funding)) {
		force_peer_disconnect(ld, uc->peer,
				      "Funding outpoint already in use");
		return;
	}

	/* ... commit the channel and start channeld. */
}
```

Second, [`peer_connect_subd()`](https://github.com/ElementsProject/lightning/blob/c7a013c821432d598a1dee39714ad667fffcdd73/connectd/multiplex.c#L1735-L1741) no longer asserts when a subdaemon already has a connection, but keeps the existing connection and closes the new one, so nodes that already stored duplicate channels don't crash on reconnect.

The outpoint check still lets through a different outpoint whose XOR gives the same `channel_id`, so commit [`7c6926c`](https://github.com/ElementsProject/lightning/commit/7c6926c16f2b9bbdcd45e36b62e8dfcb09865b15), released in [v26.06.8](https://github.com/ElementsProject/lightning/releases/tag/v26.06.8), closes that gap by refusing any new channel whose `channel_id` is already used by another live or closed channel.

## Discovery

While fuzzing CLN's funding flow, smite flagged that CLN would answer a `funding_created` reusing another channel's funding outpoint with `funding_signed`.
At first this looked like a spec violation with no security impact, so it was reported publicly as [issue #9274](https://github.com/ElementsProject/lightning/issues/9274).
Further investigation surfaced the crash on reconnect, which was reported privately, and experiments confirmed that reconnecting after every restart crashes the node again.

### Timeline

- **2026-07-03:** Duplicate funding outpoint reported publicly as a spec violation in [issue #9274](https://github.com/ElementsProject/lightning/issues/9274).
- **2026-07-08:** Crash on reconnect reported privately to Core Lightning.
- **2026-07-14:** Core Lightning acknowledged the report and began working on a fix.
- **2026-07-16:** Fix merged as [PR #9318](https://github.com/ElementsProject/lightning/pull/9318).
- **2026-07-20:** [Core Lightning v26.06.6](https://github.com/ElementsProject/lightning/releases/tag/v26.06.6) released with the fix.
- **2026-10-23:** Core Lightning approved public disclosure.
- **2026-11-10:** Public disclosure.

## Takeaways

- **Upgrade to the latest Core Lightning release, currently v26.06.10.**
  Vulnerabilities are being found faster than ever, and older releases quickly fall behind on fixes.
- **Never assert on state a peer can influence.**
  A peer that can break an assertion can crash the node, so any case that isn't provably impossible must be handled gracefully.
