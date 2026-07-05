# Security Policy

## Scope and status

`decision-runtime` is an **experimental** agent-runtime library that routes
actions through the `decision-os-min` kernel. It is hardened in code
(thread-safe, crashing tools contained + supervised, structured logging) but is
**not a production-ready system**: it runs single-process, has **no real
isolation** (the sandbox is a stub), no durability, no distribution, and has not
had an independent security audit. See `PRODUCTION_READINESS.md` for the exact
gap list.

Do not rely on this runtime as a security or isolation boundary. The runtime
never decides — the kernel does; the runtime only routes and supervises.

## Supported versions

This is pre-1.0, experimental software. Only the latest commit on the default
branch receives security fixes. There are no long-term-support branches.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** — do not open a public
issue for anything exploitable.

- Preferred: open a private report via GitHub Security Advisories
  ("Report a vulnerability" under the repository's **Security** tab).
- Alternatively, email the maintainer: **nikzadpars@gmail.com**.

Please include:

- a description of the issue and the affected component/file,
- reproduction steps or a proof of concept,
- the impact you believe it has, and
- any suggested remediation.

## Disclosure process

- We aim to acknowledge a report within **7 days**.
- We aim to provide an initial assessment (accepted / needs-info / not-a-vuln)
  within **30 days**.
- We follow **coordinated disclosure**: please give us a reasonable window to
  ship a fix before any public disclosure. We will credit reporters who wish to
  be credited.

## No bounty

There is no paid bug-bounty program. Reports are handled on a best-effort basis
by the maintainer.
