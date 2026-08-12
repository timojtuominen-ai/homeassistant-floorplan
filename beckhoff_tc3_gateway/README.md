# Beckhoff TC3 Gateway TEST

TwinCAT 3 / CX9240 test gateway for Kotiautomaatio_TC3 v0.22.

Default configuration uses `test_mode: true`, so MQTT Discovery entities are published with `tc3_test_...` object IDs and do not replace the existing CX5010 gateway entities.

Initial table-test scope includes selected lights, temperatures, motion/door/fire sensors, kitchen hood control, car heating and extra yard lights. Expand the entity map after the CX9240 ADS path is verified.

For the current CX9240 table test use:

- PLC IP: `192.168.1.171`
- PLC AMS Net ID: `5.179.194.231.1.1`
- PLC ADS port: `851`
- `test_mode: true`

Keep the existing `beckhoff_ads_gateway` add-on running during this test.
