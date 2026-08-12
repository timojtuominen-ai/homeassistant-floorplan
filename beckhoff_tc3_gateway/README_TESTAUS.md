# Beckhoff TC3 Gateway TEST v0.1

Tämä add-on on tarkoitettu Kotiautomaatio_TC3 v0.22:n CX9240-pöytätestiin.

## Turvallinen rinnakkaistestaus

Oletus `test_mode: true` julkaisee kaikki uuden gatewayn MQTT Discovery -entiteetit `tc3_test_...`-nimillä. Nykyinen CX5010-gateway voi olla samaan aikaan käytössä.

## CX9240:n nykyiset pöytätestiasetukset

- PLC IP: `192.168.1.171`
- PLC AMS Net ID: `5.179.194.231.1.1`
- PLC ADS port: `851`
- local AMS Net ID: pidä Raspberry Pi:n nykyisenä AMS Net ID:nä
- `test_mode: true`

## Testijärjestys

1. Varmista TwinCATissa, että `GVL_HA.xOnline = TRUE`.
2. Lisää Raspberry Pi:n ADS-route CX9240:een tarvittaessa.
3. Käynnistä tämä add-on Home Assistantissa.
4. Tarkista lokista, että ADS-yhteys muodostuu porttiin 851 ja `GVL_HA.xOnline=True`.
5. Tarkista, että HA:han syntyy `tc3_test_...`-entiteettejä.
6. Testaa yksi valo ja yksi sensori ennen laajempaa testausta.

Älä vaihda `test_mode: false` ennen varsinaista tuotantovaihtoa ja vanhan CX5010-gatewayn pysäyttämistä.
