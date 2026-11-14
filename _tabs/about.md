---
# the default layout is 'page'
icon: fas fa-info-circle
order: 4
---

I'm **Nishant Bansal**, a Bitcoin Lightning Network security researcher.

I find bugs that let a malicious peer crash a node or steal its funds in Lightning implementations (LND, Core Lightning, Eclair and LDK).
I report them privately and write them up here once the disclosure period ends.

To find them, I mostly use:

- Fuzzing, with [smite](https://github.com/lnfuzz/smite), [bitcoinfuzz](https://github.com/bitcoinfuzz/bitcoinfuzz) and my own fuzz targets
- LLM-assisted searches for variants of known bugs, with the [lnfuzz](https://lnfuzz.org) team
- Manual code review

See also [other bugs I've reported](https://lnfuzz.org/bugs/) and my talks on the [Bitcoin Optech Podcast](https://bitcoinops.org/en/podcast/).

## Contact

Email me at [nishant.bansal.282003@gmail.com](mailto:nishant.bansal.282003@gmail.com).
For anything sensitive, please encrypt with my PGP key:

```bash
gpg --keyserver keyserver.ubuntu.com --recv-keys "FD65 585F E02B 7813 55D0 2BC6 EAE2 9219 8F6C 5B98"
```
