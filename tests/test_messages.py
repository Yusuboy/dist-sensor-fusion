from proto.messages import SensorUpdate, to_json, from_json

def test_sensor_update_roundtrip():
    msg = SensorUpdate(node_id="A", value=25.0, timestamp=123.45)
    data = to_json(msg)
    restored = from_json(SensorUpdate, data)
    assert restored == msg
