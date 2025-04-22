# Compatibility Matrix

This document outlines the compatibility between different components of the system and external dependencies.

## Corgi Recommender Service Compatibility

| Component | Status | Notes |
|-----------|--------|-------|
| **Standalone Operation** | ✅ Full | Corgi can run completely independently |
| **Any Mastodon Client** | ✅ Compatible | Will work with any client that uses Mastodon API |
| **SQLite Database** | ✅ Required | Core data storage |
| **Python 3.8+** | ✅ Required | Python 3.10+ recommended |
| **Flask** | ✅ Required | Web framework for API |

## Elk Integration Compatibility

| Elk Version | Status | Notes |
|-------------|--------|-------|
| **Elk v0.16.0** | ✅ Compatible | Fully tested |
| **Elk v0.15.x** | ⚠️ Partial | Basic functionality works, may have UI issues |
| **Elk v0.14.x and earlier** | ❌ Incompatible | Not tested, likely incompatible |

## Script Dependencies

| Script | Docker Required | Elk Required | Other Requirements |
|--------|----------------|--------------|---------------------|
| `scripts/start_corgi.sh` | ❌ No | ❌ No | Python 3.8+, Flask |
| `scripts/stop_corgi.sh` | ❌ No | ❌ No | None |
| `scripts/start_elk_with_corgi.sh` | ❌ No | ✅ Yes | Node.js, npm |
| `scripts/docker_start_corgi.sh` | ✅ Yes | ❌ No | None |

## Browser Injection Compatibility

| Browser | Status | Notes |
|---------|--------|-------|
| **Chrome/Edge** | ✅ Compatible | Best with User JavaScript extension |
| **Firefox** | ✅ Compatible | Best with Tampermonkey/Greasemonkey |
| **Safari** | ⚠️ Partial | Limited extension support |

## Environment Requirements

| Feature | Requirement |
|---------|-------------|
| **HTTPS Support** | OpenSSL for certificate generation |
| **Docker Deployment** | Docker Engine 20.10+ |
| **Development Mode** | Node.js 16+, npm 7+ for Elk |
| **Production Deployment** | Reverse proxy (Nginx/Apache) recommended |

## Operating System Compatibility

| OS | Status | Notes |
|------|--------|-------|
| **macOS** | ✅ Tested | Primary development platform |
| **Linux** | ✅ Compatible | Recommended for production |
| **Windows** | ⚠️ Limited | Untested, may work with WSL2 |