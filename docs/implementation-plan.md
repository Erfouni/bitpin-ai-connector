# Bitpin AI Connector Implementation Plan

> Execution: superpowers:executing-plans inline; final independent code review.

**Goal:** A separate, deployable MCP bridge with an interactive Linux installer.
**Architecture:** SDK MCP server → validated service → Bitpin REST client, with persistent order journal and OAuth provider.
**Tech stack:** Python 3.12, mcp 1.30.0, HTTPX, Pydantic, SQLite, Docker Compose, Caddy.
**Spec:** [design.md](design.md)

## Global constraints
- No AI Trader imports, credentials, schedules or trading strategy.
- Remote HTTPS and mandatory authentication; single account per deployment.
- Decimal strings and no automatic write retries; uncertain writes remain unresolved.
- Persian RTL responsive authorization page; actual browser inspection required.

## Review focus
- Concurrency/restart/replayed identifiers must never duplicate orders.
- Token refresh outages must not exhaust exchange's daily auth limit.
- OAuth grants cannot be replayed, escalated or used at another resource.
- Candle resolution/gaps/unfinished bars must not silently distort indicators.
- Installer reruns must preserve existing secrets and trading state.

## Tasks
1. [x] Write failing HTTP-boundary and model tests; implement config, exact values, Bitpin auth/reads and SQLite storage; run focused tests.
2. [x] Write failing persistent/concurrent order tests; implement validation, preview, placement, reconciliation, cancellation and analysis; run suite.
3. [x] Write failing authorization and MCP tests; implement OAuth, MCP tools, resources, prompts and web consent; run suite and rendered UI inspection.
4. [x] Implement interactive setup, compose/TLS, CLI, examples, Persian README, CI; run installer/config and protocol smoke checks.
5. [x] Independent review, resolve findings, run full checks, commit and push the new private repository; record verified results and remaining live-deployment checks in verification.md.

User refinements included: default Mizito-style secret URL with optional OAuth, plus public
outbound IPv4/IPv6 discovery before key entry and an explicit Bitpin IP-allowlist step.
Initial implementation published in commit a1f0850. See Actions for Linux CI results.
