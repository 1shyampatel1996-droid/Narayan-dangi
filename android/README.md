# Narayan Scanner — Android foundation
Native Kotlin / Jetpack Compose starter. This is an offline UI and rule-engine milestone, not a connected trading app.
The current Streamlit app is unchanged.

## Implemented
- Dark Material 3 phone layout, four index OPEN cards, two digit selectors.
- Four buy targets and two sell-short targets; persisted locally.
- Exact decimal rules: LTP in inclusive target ±10%; BUY open strictly > target ×1.10; SELL_SHORT open strictly < target ×0.90.
- Contract-specific open, separate CALL/PUT identity, expiry and session date.
- Best Buy / Best Sell Short local immutable history with deduplication.
- Explicit demo mode. Simulated prices are never labelled live and are never saved as real signals.
- Local records survive restart; Android backup disabled.

## Build
Use JDK 17, Android SDK 35, Gradle 8.11.1. Open this android directory in Android Studio,
or run gradle testDebugUnitTest assembleDebug.
A Gradle wrapper is not bundled. No APK has yet been compiled or device-tested in this workspace.

## Pending
Angel One authentication, secure credential handling, instrument master integration,
WebSocket binary decoder, automatic reconnection and per-contract stale/session validation.
The onQuote method is the integration boundary; call it on the main thread only after validating
that a quote is authentic, current-session, correctly scaled and fresh.
No broker credentials are embedded, and no order placement is implemented.
Before release: verified build, emulator visual QA, device installation, live market latency test.

## Confirmed login requirement
Google Authenticator OTP once per Indian calendar day after successful broker verification. Resume a valid, securely stored broker session during that day without prompting again, including after process restart. Expiry, revocation, explicit logout or a new Indian calendar day requires authentication again. SessionPolicy implements this decision only; authentication UI and encrypted token storage are still pending. The OTP itself must not be saved.
