# GSM SMS Gateway - TEST (Current Development)

🧪 **This is a TEST version for active development and experimentation.**

This folder contains the current development version of the addon, based on v2.5.0. Use this for testing new features and debugging without affecting the stable release version.

## Purpose

- Experimentation with new features
- Debug logging and diagnostics
- Testing network type detection methods
- Can be updated frequently without version bumps

## Differences from Production

- Additional debug logging enabled
- Experimental features may be unstable
- Version suffix: `-test`
- Slug: `gsm_sms_gateway_test_current`

## Usage

Install this alongside or instead of the production addon for testing purposes. Make sure to stop the production addon first to avoid device conflicts.

## Current Experiments

- Network type detection via Gammu API introspection
- Debug logging for GetNetworkInfo() fields
- Testing AT command passthrough methods
