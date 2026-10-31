# Narayan Scanner — native Android
Independent Kotlin / Jetpack Compose app. Existing Streamlit files are unchanged.

## Implemented
- Native dark Material 3 layout: four market OPEN/digit cards, two digit selectors,
  four buy targets and two sell-short targets.
- NIFTY options, current expiry selector, previous/nearest/next matching digit strikes,
  both CALL and PUT. Duplicate selected contracts are combined.
- LTP inclusive target ±10%; BUY contract open strictly > target ×1.10;
  SELL_SHORT contract open strictly < target ×0.90. Decimal boundary calculations.
- Best Buy and Best Sell Short immutable locally saved records: contract, expiry,
  target, opening premium, matched premium and exchange timestamp.
  Duplicate same-day contract/direction/target records are suppressed.
- Angel One SmartAPI login with manually entered Authenticator OTP. First-time API key,
  client ID and PIN setup is encrypted using Android Keystore AES-GCM.
  JWT/feed tokens persist encrypted. OTP and TOTP seed are never persisted.
- Reopen resumes and validates an unexpired broker session. Broker rejection, expiry
  or explicit logout requires another OTP. Expiry is capped at broker midnight session policy.
- WebSocket Quote mode, binary decoder based on official Angel One Python SDK,
  heartbeat and bounded reconnect. All received ticks are considered for signals.
  Screen updates coalesce to a 50 ms target without full-page reload.
- Old-session or more-than-15-second-old quotes are shown as last available and cannot
  create new signals. One initial REST snapshot per newly selected token supplies last available prices when the market is closed; these snapshots cannot create locked signals. No REST polling loop, no order placement, no demo data.
- Credential backup and cleartext network traffic disabled.

## Build
JDK 17, Android SDK 35, Gradle 8.11.1.
Open this android directory in Android Studio, or run:
    gradle testDebugUnitTest assembleDebug
CI in .github/workflows/android-preview.yml publishes a debug APK artifact.
The artifact is a development build; inspect the actual CI result before claiming it builds.

## Remaining validation
Real broker authentication and exchange-session quote behavior need on-device testing
using the user's own credentials. Broker header/network requirements may affect login.
Credentials must be entered only in the installed app, never in repository files.
No claim of measured live latency or device visual QA has been made.
Signals run only while the app is in the foreground; no background monitoring service.
