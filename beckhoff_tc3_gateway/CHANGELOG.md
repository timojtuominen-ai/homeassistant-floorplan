# Changelog

## 0.1.2
- Remove the redundant explicit `pyads.add_route()` call on Linux; `pyads.Connection(..., ip_address)` creates the client route when opened.
- Keep the configured local AMS Net ID initialization before opening the PLC connection.
- Add a short TCP 48898 reachability probe so network-level failures are visible immediately in the add-on log.
- Set the bench-test defaults to the current CX9240 address `192.168.1.171` and AMS Net ID `5.179.194.231.1.1`.
