---
title: Summer of Bitcoin
date: 2025-08-20 10:30:00 +0530
categories: [Mentorship]
tags: [open-source, fuzzing]
description: Summer of Bitcoin 2025 final report on building a continuous fuzzing solution for LND.
image: ../assets/img/post-1.png
---

## Title
[Continuous Fuzzing for LND](https://github.com/go-continuous-fuzz/go-continuous-fuzz)

## Problem Statement
Modern Go projects lack a robust, low-maintenance solution for continuous fuzzing. Although tools like ClusterFuzzLite are widely used, their declining maintenance and reliance on LibFuzzer instead of Go's native fuzzing engine introduce friction for developers.

As a result, teams often need to manually manage fuzz targets, execute long-running tests, and maintain corpora. This leads to outdated fuzzing setups that miss critical edge cases. In security-sensitive systems such as Bitcoin Core and the Lightning Network (LND), even a small bug can put significant user funds at risk. Continuous fuzzing is therefore essential to ensure long-term security and reliability.

## Current State of the Project
So far, the project includes the following capabilities:

1. **Automatic Fuzz Target Detection:** Scans the repository and identifies all available fuzz targets.
2. **Concurrent Fuzzing:** Runs multiple fuzzing workers concurrently, with the default set to one CPU core.
3. **Customizable Execution:** Configure the duration and target package for fuzzing with config variables.
4. **Corpus Persistence:** Saves the input corpus for each fuzz target to a specified AWS S3 bucket, ensuring that test cases are preserved for future runs.
5. **Crash Reporting:** Automatically open a GitHub issue on crash, including the error logs and failing input data.
6. **Coverage Reports:** Saves the generated coverage reports for each fuzz target to the specified AWS S3 bucket, enabling coverage history comparison to help improve fuzz targets.
7. **Corpus Minimization:** Periodically remove inputs that do not improve or reduce coverage to prevent corpus bloat.
8. **Automatic Issue Closure:** Automatically closes GitHub issues for a fuzz target when the crash is no longer reproducible.

## Future Work
Most planned features are complete, with the following enhancement currently under review:

- **Kubernetes mode of fuzzing:** Support for running fuzzing workers as Kubernetes jobs, where each worker spawns pods to fuzz individual targets. This allows better scalability and removes CPU limitations for parallel fuzzing [PR #44](https://github.com/go-continuous-fuzz/go-continuous-fuzz/pull/44).

## Benefits and Impact of the Project
This project delivers significant value for security-critical systems like Bitcoin, where failures can have serious financial and network consequences.

By automating fuzzing, crash detection, and GitHub issue management, developers no longer need to manually run long fuzzing campaigns. Instead, fuzzing becomes a continuous background process that integrates seamlessly with existing open-source workflows.

Daily coverage reports are published to an S3-backed static site, giving developers clear visibility into untested areas of the codebase. This continuous feedback loop helps progressively harden Bitcoin and Lightning implementations by catching edge cases early.

Ultimately, the project improves the security, reliability, and trustworthiness of Bitcoin's base and second-layer infrastructure while lowering the barrier to adopting continuous fuzzing.

## Conclusion
Working on this project was both enriching and technically diverse. While I did not directly modify Bitcoin or Lightning codebases, my work focused on strengthening the tooling that protects the broader ecosystem.

Before selection, I explored Bitcoin's fundamentals, including mining, protocol design, and historical details such as the genesis block. I also studied the Lightning Network while evaluating potential contributions to LND and CLN.

During the project, I gained hands-on experience with Docker APIs, AWS and its SDK, GitHub APIs, Kubernetes, and AWS S3. I also developed a deeper understanding of fuzzing and testing using Go's native tooling.

Equally important was the community support — from early discussions to weekly meetings and code reviews with mentors. Their feedback played a crucial role in shaping both the project and my growth.

Overall, this experience strengthened my technical skills and reinforced the value of collaboration in open-source development.
