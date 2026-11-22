# Grilla app protocol notes

These notes come from static analysis of the Grilla Grills Android app, version
2.0.5 (`com.grillaapp`, version code 2000015). The app is React Native with a
Hermes bytecode bundle. It was decompiled with hermes-dec 0.1.8 and the code
was read, never run.

The APK came from APKPure, and its signature was not verified. Nothing below
has been tested against a real grill unless a line says so.

## Transport (already used by aiogrilla)

- Login goes through the Cognito user pool, which issues IAM credentials. The
  app then connects to AWS IoT MQTT over WSS.
- The app and aiogrilla share one MQTT client id per account: the identity UUID.

## MQTT topics (app config)

| Name | Topic |
|---|---|
| grillState | `grilla/{device-id}/grill_state` |
| heartbeat | `topic/client/{device-id}/heartbeat` |
| command | `topic/client/{device-id}/command` |
| shadow | `$aws/things/{device-id}/shadow/update` |

`{device-id}` is the grill's `topicId`.

Other values in the app config:

| Setting | Value |
|---|---|
| `DEVICE_HB_INTERVAL` | 15000 ms |
| `GRILL_STATE_UPDATE_DELAY` | 2000 ms |
| Grill target temperature | 180–500 °F |
| Probe target temperature | 100–225 °F |

## Heartbeat: why Home Assistant drops the grill

- Every 15 s the app publishes `{"timestamp": <epoch milliseconds>}` to each
  grill's heartbeat topic.
- The original Silverbac only publishes `grill_state` while those heartbeats
  arrive. aiogrilla only subscribes. Once the app closes, the grill goes quiet,
  and aiogrilla's 300 s silence watchdog marks it unavailable.
- Real-world check: opening the app brought the grill back in Home Assistant
  immediately.
- Fix: publish the same heartbeat every 15 s while connected. This needs IoT
  publish permission for the identity, which the app has with the same
  credentials, so it is expected to work (not yet tested).

## Power off

The app sends a REST call through the AWS Amplify API named `PowerDown`:

```
POST https://ttl0nzlbek.execute-api.us-east-2.amazonaws.com/default/
Authorization: Bearer <Cognito ID token>
Content-Type: application/json

{"grill_id": "<topicId>"}
```

- The app calls this from its power toggle whenever the grill reports
  `iot.isGrillPowerOn`, without checking the model.
- It is not confirmed that the cloud accepts this for legacy grills.

## Power on

- The app treats `chimp`, `silverbac` and `grilla` (the original models) as
  legacy (`isLegacy`). For legacy models, the power toggle does nothing while
  the grill is off. **There is no remote power-on for the original Silverbac.**
- Non-legacy models use a two-step flow:
  1. The user ticks a safety acknowledgement. The app then calls
     `POST https://f85r6frpgd.execute-api.us-east-2.amazonaws.com/default/confirmstart`
     with a Bearer ID token and the body
     `{identity, grillName, grillModel, grillLocation, grillSn}`. The response
     contains an `authorization` value.
  2. `publishPower` publishes `{"cmd": "power", "data": "on", "authorization": <value>}`
     over MQTT, probably on the command topic (not confirmed).

## Target temperature

- The app publishes setpoints through `publish*` helpers. The device shadow
  topic is the likely route, with fields such as `desired_temp`,
  `desired_probe_temp` and `desired_probe2_temp`.
- **Not yet traced.** Next step: read the publish helpers around `publishPower`
  in the decompiled bundle and confirm the topic and payload before
  implementing.

## Second probe detection (for upstream #37)

- The app's `hasSecondProbe(model)` returns true only when the model's
  `grillCard.cardType === 'three-readings'`.
- Known model ids: `silverbac20`, `silverbacxl`, `chimp20`, `pieRo`, `mammoth`,
  `grilla`, `silverbac`, `chimp`, `kong`, `unknown`.
- The integration can follow the same rule and skip the probe 2 entities when
  the model has no second probe.

## Other REST APIs seen

| Name | URL | Notes |
|---|---|---|
| GrillsByOwnerApi | `https://v3v2ce8vjg.execute-api.us-east-2.amazonaws.com/default` | |
| StartConfirmation | `https://f85r6frpgd.execute-api.us-east-2.amazonaws.com/default` | Used for power on, above. |
| PowerDown | `https://ttl0nzlbek.execute-api.us-east-2.amazonaws.com/default` | |
