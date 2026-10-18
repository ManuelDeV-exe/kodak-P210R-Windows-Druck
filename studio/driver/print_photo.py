"""Experimental P210R transfer v2.3. Protocol inferred from user's HCI capture."""
import argparse
import datetime
import json
import time
from pathlib import Path

HELLO = bytes.fromhex('6401000000000000')
FOLLOW = bytes.fromhex('0201250000000000')
START_CAPTURE = bytes.fromhex('050100000000000c000d9d490000000000000000')
READY = bytes.fromhex('0700000000000000')
POLL = bytes.fromhex('0300000000000000')
WINDOW_PREFIX = bytes.fromhex('09000000')
WINDOW = 32768


def make_header(jpeg_size, mode):
    if mode == 'captured':
        return START_CAPTURE
    if jpeg_size >= 2**32:
        raise ValueError('JPEG too large for 32-bit header')
    # Hypothesis: capture bytes 8..11 are total JPEG byte count.
    # NOT verified: original header 892233 vs 892562 extracted JPEG bytes.
    return START_CAPTURE[:8] + jpeg_size.to_bytes(4, 'big') + START_CAPTURE[12:]


def image_packet(jpeg, offset, size):
    if not 0 <= offset < len(jpeg) or not 0 < size <= WINDOW or offset + size > len(jpeg):
        raise ValueError(f'Invalid image packet offset={offset}, size={size}')
    # Original HCI: final segment prefix 09 00 00 00 00 00 1e 92 for 7826 bytes.
    return WINDOW_PREFIX + size.to_bytes(4, 'big') + jpeg[offset:offset+size]


def packetize(jpeg):
    return [image_packet(jpeg, i, min(WINDOW, len(jpeg)-i))
            for i in range(0, len(jpeg), WINDOW)]


def read_exact(ser, count, timeout, events, stage):
    buf = bytearray()
    deadline = time.monotonic() + timeout
    while len(buf) < count and time.monotonic() < deadline:
        chunk = ser.read(min(count - len(buf), max(1, ser.in_waiting)))
        if chunk:
            buf.extend(chunk)
            events.append({'stage': stage, 'hex': chunk.hex(), 'length': len(chunk)})
    return bytes(buf)


def progress(response):
    if len(response) == 16 and response[:8] == bytes.fromhex('0800000000000008'):
        return int.from_bytes(response[8:12], 'big'), int.from_bytes(response[12:16], 'big')
    return None


def main():
    ap = argparse.ArgumentParser(description='KODAK P210R experimental print v2.3')
    ap.add_argument('--port', default='COM5')
    ap.add_argument('--image', default='testfoto.jpg')
    ap.add_argument('--send', action='store_true', help='Send print data to hardware, no additional confirmation')
    ap.add_argument('--header-mode', choices=['image-size', 'captured'], default='image-size')
    ap.add_argument('--observe-seconds', type=int, default=60, help='Passive status monitoring after transfer')
    ap.add_argument('--poll', action='store_true', help='Send observed status query 03 during post-transfer phase')
    ap.add_argument('--chunk-size', type=int, default=650)
    ap.add_argument('--report', default='photo_print_report_v2_3.json')
    a = ap.parse_args()
    if not 32 <= a.chunk_size <= 650:
        ap.error('chunk-size must be between 32 and 650')
    jpeg = Path(a.image).read_bytes()
    if not (jpeg.startswith(b'\xff\xd8') and jpeg.endswith(b'\xff\xd9')):
        ap.error('Image must be a complete JPEG')
    header = make_header(len(jpeg), a.header_mode)
    windows = packetize(jpeg)
    report = {'version': '2.3', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'port': a.port, 'image': a.image, 'jpeg_bytes': len(jpeg),
              'header_mode': a.header_mode, 'header_hex': header.hex(),
              'header_value': int.from_bytes(header[8:12], 'big'),
              'capture_header_value': 892233,
              'capture_extracted_jpeg_bytes': 892562,
              'capture_discrepancy_bytes': 329,
              'header_hypothesis_unverified': True,
              'windows': [{'jpeg_bytes': len(w)-8, 'wire_bytes': len(w)} for w in windows],
              'sent': [], 'events': [], 'ack_offsets': [], 'ack_details': [], 'image_bytes_sent': 0, 'unique_bytes_covered': 0, 'transfers': [],
              'final_response_hex': '', 'post_transfer_responses': [], 'error': None, 'result': 'dry_run'}
    def save():
        Path(a.report).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('KODAK P210R v2.3 | JPEG:', len(jpeg), '| windows:', len(windows))
    print('Header:', header.hex(' '), '| mode:', a.header_mode)
    print('WARNING: Header size hypothesis is NOT proven by the original capture (329-byte discrepancy).')
    print('v2.3: variable-length final segment; follow printer-requested offsets (max one overlap).')
    if not a.send:
        save()
        print('Dry run only. To send, add --send. Report:', a.report)
        return
    try:
        import serial
        with serial.Serial(a.port, 115200, timeout=.1, write_timeout=15) as ser:
            def send(data, stage):
                count = ser.write(data)
                ser.flush()
                if count != len(data):
                    raise IOError(f'Partial write at {stage}: {count}/{len(data)}')
                if stage != 'image':
                    report['sent'].append({'stage': stage, 'hex': data.hex(), 'bytes': count})
            def expect(data, prefix, stage):
                if not data.startswith(prefix):
                    raise RuntimeError(f'{stage}: unexpected response {data.hex()}')
            initial = read_exact(ser, 8, 8, report['events'], 'initial')
            expect(initial, bytes.fromhex('6400000000000000'), 'initial')
            send(HELLO, 'hello')
            expect(read_exact(ser, 40, 15, report['events'], 'hello_response'), bytes.fromhex('02056234'), 'hello')
            send(FOLLOW, 'follow')
            expect(read_exact(ser, 9, 15, report['events'], 'follow_response'), bytes.fromhex('040102'), 'follow')
            send(header, 'start')
            expect(read_exact(ser, 8, 15, report['events'], 'start_response'), bytes.fromhex('010501'), 'start')
            send(READY, 'ready')
            first = read_exact(ser, 16, 15, report['events'], 'ready_response')
            if progress(first) is None or progress(first)[0] != 0:
                raise RuntimeError('Invalid ready status: ' + first.hex())
            # Flow control: the printer ACK advertises the NEXT offset and number of bytes.
            # The original trace uses 0x8000 for full blocks and 0x1e92 for a 7826-byte
            # final block. Previous versions incorrectly sent 0x8000 for the final segment.
            # An unusual ACK (228464, 22304) requests a 912-byte overlap with our
            # earlier sequential packets. Replay that offset only once, with hard limits.
            offset, request_size = 0, WINDOW
            unique_end = 0
            covered_ranges = []
            saw_overlap = False
            max_segments = (len(jpeg) + WINDOW - 1) // WINDOW + 2
            for i in range(max_segments):
                if offset >= len(jpeg):
                    break
                if request_size <= 0 or request_size > WINDOW:
                    raise RuntimeError(f'Invalid device request size: {request_size}')
                packet_size = min(request_size, len(jpeg)-offset)
                if packet_size != request_size:
                    raise RuntimeError(f'Device requested bytes beyond JPEG end: {offset}+{request_size}>{len(jpeg)}')
                packet = image_packet(jpeg, offset, packet_size)
                if offset < unique_end:
                    if saw_overlap or (unique_end - offset) > WINDOW:
                        raise RuntimeError(f'Repeated or excessive overlap: {offset} < {unique_end}')
                    saw_overlap = True
                transfer = {'segment': i+1, 'offset': offset, 'size': packet_size,
                            'prefix': packet[:8].hex(), 'overlap_bytes': max(0, unique_end-offset)}
                report['transfers'].append(transfer)
                for pos in range(0, len(packet), a.chunk_size):
                    send(packet[pos:pos+a.chunk_size], 'image')
                covered_ranges.append((offset, offset+packet_size))
                unique_end = max(unique_end, offset+packet_size)
                report['image_bytes_sent'] += packet_size
                report['unique_bytes_covered'] = unique_end
                print(f'Segment {i+1}: offset={offset} length={packet_size} '
                      f'covered={unique_end}/{len(jpeg)}')
                if unique_end >= len(jpeg):
                    # Original capture transitions to 04 03 status; no final 08 ACK.
                    break
                response = read_exact(ser, 16, 15, report['events'], f'ack_{i+1}')
                result = progress(response)
                if result is None:
                    raise RuntimeError(f'Missing transfer ACK after segment {i+1}: {response.hex()}')
                next_offset, next_size = result
                report['ack_offsets'].append(next_offset)
                detail = {'segment': i+1, 'offset': next_offset,
                          'second_value': next_size, 'bytes_sent': report['image_bytes_sent'],
                          'jpeg_size': len(jpeg), 'offset_plus_second': next_offset + next_size,
                          'matches_jpeg_size': next_offset + next_size == len(jpeg)}
                report['ack_details'].append(detail)
                print('ACK next request:', detail)
                if next_offset > unique_end or next_offset < max(0, unique_end-WINDOW):
                    raise RuntimeError(f'Unexpected ACK offset: {next_offset} after {unique_end}')
                if next_offset == offset and next_size == request_size:
                    raise RuntimeError('Printer repeated the same request; stopping safely')
                if next_offset < unique_end:
                    report['nonstandard_ack_accepted'] = detail
                offset, request_size = next_offset, next_size
            else:
                raise RuntimeError('Excessive number of image segments')
            if unique_end != len(jpeg):
                raise RuntimeError(f'JPEG coverage incomplete: {unique_end}/{len(jpeg)}')
            # Capture shows that after the final image segment, status 04 03 01 01
            # and eventually 04 06 may arrive. These can be asynchronous.
            # Never interpret a missing final 08 ACK as permission to send more bytes.
            report['result'] = 'all_data_sent_waiting_for_printer'
            report['post_transfer_observation'] = []
            deadline = time.monotonic() + a.observe_seconds
            last_poll = time.monotonic()
            buffer = bytearray()
            while time.monotonic() < deadline:
                chunk = ser.read(max(1, min(ser.in_waiting, 512)))
                if chunk:
                    buffer.extend(chunk)
                    report['events'].append({'stage': 'post_transfer_raw', 'hex': chunk.hex(), 'length': len(chunk)})
                    # Serial port is a byte stream; don't assume read() aligns to messages.
                    while len(buffer) >= 8:
                        if buffer[0] == 4 and buffer[1] == 6:
                            packet = bytes(buffer[:8]); del buffer[:8]
                            report['post_transfer_observation'].append({'type': 'capture_completion_marker', 'hex': packet.hex()})
                            report['result'] = 'capture_completion_marker_seen_print_unverified'
                            break
                        if buffer[0] == 4 and buffer[1] == 3:
                            if len(buffer) < 16: break
                            packet = bytes(buffer[:16]); del buffer[:16]
                            report['post_transfer_observation'].append({'type': 'printing_status', 'hex': packet.hex()})
                            continue
                        if buffer[0] == 8:
                            if len(buffer) < 16: break
                            packet = bytes(buffer[:16]); del buffer[:16]
                            report['post_transfer_observation'].append({'type': 'transfer_status', 'hex': packet.hex(), 'progress': progress(packet)})
                            continue
                        # Unknown frame: preserve in raw log and resynchronize one byte.
                        del buffer[0]
                    if report['result'] == 'capture_completion_marker_seen_print_unverified':
                        break
                if a.poll and time.monotonic() - last_poll >= 3:
                    send(POLL, 'status_poll')
                    last_poll = time.monotonic()
            report['unparsed_post_transfer_hex'] = bytes(buffer).hex()
            report['observed_seconds'] = a.observe_seconds
    except Exception as exc:
        report['error'] = repr(exc)
        report['result'] = 'error'
        print('STOP:', exc)
    finally:
        save()
        print('Report:', a.report, '| result:', report['result'])

if __name__ == '__main__':
    main()