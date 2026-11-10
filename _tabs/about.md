---
# the default layout is 'page'
icon: fas fa-info-circle
order: 4
---

I'm **Nishant Bansal**, a Bitcoin Lightning Network security researcher supported by a [Spiral](https://spiral.xyz/grants/) grant.
I look for bugs that let a malicious peer crash a node or steal its funds in LND, Core Lightning, Eclair and LDK, and disclose them privately.
Writeups appear here once a fix has shipped and disclosure is cleared.

## How I find them

- **Fuzzing**: stateful, differential and snapshot fuzzing, through fuzz targets I've written for each implementation, [bitcoinfuzz](https://github.com/bitcoinfuzz/bitcoinfuzz), and [Smite](https://github.com/lnfuzz/smite)
- **LLM-assisted variant analysis** with the [lnfuzz](https://lnfuzz.org) team, hunting for relatives of bugs the fuzzers find
- **Manual review** of the code paths a malicious peer can reach

Other bugs I've reported are tracked at [lnfuzz.org/bugs](https://lnfuzz.org/bugs/).
I've talked about this work on the Bitcoin Optech Podcast ([#411](https://bitcoinops.org/en/podcast/2026/06/30/), [#429](https://bitcoinops.org/en/podcast/2026/11/03/)).

## Contact

Email me at [nishant.bansal.282003@gmail.com](mailto:nishant.bansal.282003@gmail.com).
For anything sensitive, please encrypt with my PGP key:

```bash
gpg --keyserver keyserver.ubuntu.com --recv-keys "FD65 585F E02B 7813 55D0 2BC6 EAE2 9219 8F6C 5B98"
```
