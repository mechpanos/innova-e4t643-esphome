// -----------------------------------------------------------------------------
// fancoil_decode.h - decoder for the white COMM wire (main board -> touch display)
// of an Innova fan coil with the E4T643 on-board control.
//
// READ ONLY. It never drives a line.
//
// Plain C++ with no ESPHome dependency, so the same code can be run on a PC against
// captured logs (tools/test_decoder.py). parse() is a line-by-line port of
// tools/fcwave.py parse(); if one changes the other must change, and the test checks it.
//
// What it knows (docs/PROTOCOL.md) - bit 0 = first bit after the sync, 0 = lit:
//   0-6 tenths digit, 7 heating symbol, 8-14 units digit, 16-22 tens digit (segments g f e d c b a)
//   24-27 fan speed auto/night/low/high, 28 cooling symbol, 36: 0 = room temperature, 1 = setpoint
//   The tail after the 56 bits carries the key being touched.
// What it does NOT know: the rule of the check bits (39-54). That is why an image is only
// accepted after it arrives identical 3 times in a row (the board repeats it 31 times a second).
// -----------------------------------------------------------------------------
#pragma once
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <cmath>

namespace fancoil {

static const double TICK = 15.89;   // us
static const int NDATA = 56;
static const size_t MAXEL = 128;    // a burst with more elements than this is not a frame

// -- ONE FRAME ----------------------------------------------------------------
struct Frame {
  bool ok{false};
  uint8_t pre{0};          // pre-pulse in ticks (0, 2 or 3)
  uint64_t bits{0};        // weight 1<<k = value of line bit k (1 = not lit)
  bool tail_idle{false};   // idle tail
  bool tail_ok{false};     // the 16 tail ticks were found
  uint16_t tail{0};        // the 16 ticks after the first high pulse of the tail, tick 1 = MSB
};

inline bool one_tick(double d) { return 0.6 * TICK <= d && d <= 1.45 * TICK; }
inline double absd(int32_t v) { return v < 0 ? -(double) v : (double) v; }

// b: durations in us, positive = high, negative = low - EXACTLY as "Received Raw" prints them.
// (ESPHome's on_raw passes one extra element at the end, the idle gap; the caller drops it.)
inline Frame parse(const int32_t *b, size_t n) {
  Frame f;
  if (n < 20 || n > MAXEL || b[0] > 0) return f;
  double edges[MAXEL + 1];
  double t = 0;
  edges[0] = 0;
  for (size_t i = 0; i < n; i++) { t += absd(b[i]); edges[i + 1] = t; }
  if (t < 900 || t > 2200) return f;

  // anchor at the start of the burst: [pre-pulse L2/L3, H1] + sync L1 H1 L1 H1 L1 H1 L1 H(>=1)
  size_t start;
  double a0 = absd(b[0]);
  if (one_tick(a0)) { start = 0; f.pre = 0; }
  else if (1.55 * TICK <= a0 && a0 <= 3.5 * TICK && one_tick(absd(b[1]))) { start = 2; f.pre = (uint8_t) lround(a0 / TICK); }
  else return f;
  for (size_t k = start; k < start + 7; k++) if (!one_tick(absd(b[k]))) return f;
  double last = absd(b[start + 7]);
  if (last < 0.6 * TICK) return f;
  double t0 = one_tick(last) ? edges[start + 8] : edges[start + 7] + TICK;
  double extra = (edges[n] - t0) / TICK - NDATA;
  if (extra < 24 || extra > 48) return f;

  uint64_t bits = (1ULL << NDATA) - 1;
  size_t i = start + 7;
  while (i < n) {
    long a = lround((edges[i] - t0) / TICK), e = lround((edges[i + 1] - t0) / TICK);
    if (a >= NDATA) break;
    if (b[i] < 0)
      for (long k = (a > 0 ? a : 0); k < (e < NDATA ? e : NDATA); k++) bits &= ~(1ULL << k);
    i++;
  }
  f.bits = bits;
  f.ok = true;

  // -- TAIL --
  // idle: the burst ends with H1 L13 H6 L5 (the L13 slips by +-1)
  auto rt = [&](size_t k) { return lround(absd(b[k]) / TICK); };
  if (b[n - 4] > 0 && rt(n - 4) == 1 && b[n - 3] < 0 && rt(n - 3) >= 12 && rt(n - 3) <= 14 &&
      b[n - 2] > 0 && rt(n - 2) == 6 && b[n - 1] < 0 && rt(n - 1) == 5)
    f.tail_idle = true;
  // the 16 ticks: after the first long low period (>= 4.5 ticks) that follows the data,
  // skipping the first tick (the first high pulse) - same as tools/keys.py
  double data_end = (f.pre ? f.pre + 1 : 0) + 8 + NDATA, tot = 0;
  for (size_t k = 0; k < n; k++) {
    tot += absd(b[k]) / TICK;
    if (tot > data_end + 0.5 && b[k] < 0 && absd(b[k]) / TICK >= 4.5) {
      // "continuation" after the 16 ticks: rest_h = leading ones, rest_l = zeros right after them
      uint32_t acc = 0; int have = 0, rest_h = 0, rest_l = 0, phase = 0; bool skipped = false;
      for (size_t j = k + 1; j < n; j++) {
        long w = rt(j);
        for (long q = 0; q < w; q++) {
          if (!skipped) { skipped = true; continue; }
          if (have < 16) { acc = (acc << 1) | (b[j] > 0 ? 1 : 0); have++; continue; }
          if (phase == 0) { if (b[j] > 0) rest_h++; else { phase = 1; rest_l++; } }
          else if (phase == 1) { if (b[j] < 0) rest_l++; else phase = 2; }
        }
      }
      if (have == 16) {
        f.tail_ok = true; f.tail = (uint16_t) acc;
        if (acc == 0x2000 && rest_h == 6 && rest_l >= 5) f.tail_idle = true;
      }
      break;
    }
  }
  return f;
}

// -- DICTIONARIES ---------------------------------------------------------------
enum Key : uint8_t { KEY_NONE, KEY_AUTO, KEY_NIGHT, KEY_LOW, KEY_HIGH, KEY_MODE, KEY_PLUS, KEY_MINUS, KEY_UNKNOWN };
inline Key key_of(uint16_t tail) {
  switch (tail) {   // docs/PROTOCOL.md - 7 of the 8 keys the manual mentions
    case 0x3000: return KEY_AUTO;    // 0011 0000 0000 0000
    case 0x2800: return KEY_NIGHT;   // 0010 1000 0000 0000
    case 0x2400: return KEY_LOW;     // 0010 0100 0000 0000
    case 0x2200: return KEY_HIGH;    // 0010 0010 0000 0000
    case 0x2080: return KEY_MODE;    // 0010 0000 1000 0000
    case 0x2050: return KEY_PLUS;    // 0010 0000 0101 0000
    case 0x2038: return KEY_MINUS;   // 0010 0000 0011 1000
    default: return KEY_UNKNOWN;
  }
}
inline const char *key_name(Key k) {
  switch (k) {
    case KEY_NONE: return "none";
    case KEY_AUTO: return "fan auto";
    case KEY_NIGHT: return "fan night";
    case KEY_LOW: return "fan low";
    case KEY_HIGH: return "fan high";
    case KEY_MODE: return "mode (heat/cool)";
    case KEY_PLUS: return "+";
    case KEY_MINUS: return "-";
    default: return "unknown";
  }
}

enum Speed : uint8_t { SPEED_UNKNOWN, SPEED_AUTO, SPEED_NIGHT, SPEED_LOW, SPEED_HIGH };
inline const char *speed_name(Speed s) {
  switch (s) {
    case SPEED_AUTO: return "auto";
    case SPEED_NIGHT: return "night";
    case SPEED_LOW: return "low";
    case SPEED_HIGH: return "high";
    default: return "unknown";
  }
}

enum Sym : uint8_t { SYM_OFF, SYM_ON, SYM_BLINK };
inline const char *sym_name(Sym s) { return s == SYM_ON ? "on" : s == SYM_BLINK ? "blinking" : "off"; }

enum Mode : uint8_t { MODE_UNKNOWN, MODE_HEAT, MODE_COOL, MODE_BOTH };
inline const char *mode_name(Mode m) {
  switch (m) {
    case MODE_HEAT: return "heating";
    case MODE_COOL: return "cooling";
    case MODE_BOTH: return "both symbols";   // the manual describes this for automatic changeover; never captured
    default: return "unknown";
  }
}

// 7-segment digit: mask with weight 1<<i for position i (0=g 1=f 2=e 3=d 4=c 5=b 6=a) when lit.
// Returns 0-9, 10 for blank, -1 for an unknown shape.
inline int digit_at(uint64_t bits, int base) {
  uint8_t m = 0;
  for (int i = 0; i < 7; i++) if (!((bits >> (base + i)) & 1)) m |= (1 << i);
  switch (m) {
    case 0x7E: return 0; case 0x30: return 1; case 0x6D: return 2; case 0x79: return 3; case 0x33: return 4;
    case 0x5B: return 5; case 0x5F: return 6; case 0x70: return 7; case 0x7F: return 8; case 0x7B: return 9;
    case 0x00: return 10;
    default: return -1;
  }
}
inline bool bit_at(uint64_t bits, int k) { return (bits >> k) & 1; }
// the 7 bytes as the docs write them (bit 0 = MSB of the first byte)
inline void hex_of(uint64_t bits, char *out /* >= 21 */) {
  for (int by = 0; by < 7; by++) {
    unsigned v = 0;
    for (int i = 0; i < 8; i++) v = (v << 1) | (unsigned) bit_at(bits, by * 8 + i);
    snprintf(out + by * 3, 4, "%02X ", v);
  }
  out[20] = 0;
}

// -- A SYMBOL THAT MAY BLINK ----------------------------------------------------
// A symbol blinks 0.5 s / 0.5 s while the unit waits for suitable water. To avoid publishing
// twice a second, the state (off / on / blinking) is published once it has been stable for 0.7 s.
struct SymTrack {
  bool init{false}, lit{false}, blinking{false}, valid{false}, changed{false};
  uint32_t last_toggle{0}, cand_since{0};
  Sym cand{SYM_OFF}, pub{SYM_OFF};
  void update(bool now_lit, uint32_t now) {
    if (!init) { init = true; lit = now_lit; last_toggle = now - 60000; cand = lit ? SYM_ON : SYM_OFF; cand_since = now; }
    else if (now_lit != lit) { if (now - last_toggle < 800) blinking = true; last_toggle = now; lit = now_lit; }
    if (blinking && now - last_toggle > 1200) blinking = false;
    Sym s = blinking ? SYM_BLINK : (lit ? SYM_ON : SYM_OFF);
    if (s != cand) { cand = s; cand_since = now; }
    if ((!valid || cand != pub) && now - cand_since >= 700) { pub = cand; valid = true; changed = true; }
  }
  bool active() const { return valid && pub != SYM_OFF; }
};

// -- STATE TRACKING -------------------------------------------------------------
// Call feed() for every burst. After each call, every *_changed flag that is true must be
// published by the caller; clear_changes() resets them.
struct Tracker {
  static const uint64_t MASK55 = (1ULL << 55) - 1;   // the tail covers the 56th bit in ~1% of the frames

  // counters
  uint32_t frames{0}, rejected{0}, bad_digits{0}, odd_bits{0};
  uint32_t last_frame_ms{0}; bool any_frame{false};

  // accepted image
  uint64_t img{0}; bool img_valid{false}, img_changed{false};
  uint64_t cand_img{0}; uint8_t cand_n{0};

  // fields
  float room{NAN}; bool room_changed{false};
  float setpoint{NAN}; bool setpoint_changed{false};
  Speed speed{SPEED_UNKNOWN}; bool speed_valid{false}, speed_changed{false};
  bool screen_setpoint{false}, screen_valid{false}, screen_changed{false};
  SymTrack heat, cool;
  Mode mode{MODE_UNKNOWN}, mode_cand{MODE_UNKNOWN}; uint32_t mode_since{0}; bool mode_changed{false};

  // key
  Key key{KEY_NONE}; uint16_t key_code{0}; bool key_changed{false};
  uint16_t cand_tail{0}; bool cand_idle{true}; uint8_t cand_tail_n{0};

  void clear_changes() {
    img_changed = room_changed = setpoint_changed = speed_changed = screen_changed = mode_changed = key_changed = false;
    heat.changed = cool.changed = false;
  }

  void feed(const int32_t *b, size_t n, uint32_t now) {
    Frame f = parse(b, n);
    if (!f.ok) { if (n >= 20) rejected++; return; }
    frames++; last_frame_ms = now; any_frame = true;

    // 1) image: identical 3 times in a row
    uint64_t d = f.bits & MASK55;
    if (d == cand_img && cand_n) { if (cand_n < 255) cand_n++; } else { cand_img = d; cand_n = 1; }
    if (cand_n == 3 && (!img_valid || d != img)) { img = d; img_valid = true; img_changed = true; decode_image_(); }

    // 2) symbols and mode: run on every frame so that their timers advance
    if (img_valid) {
      heat.update(!bit_at(img, 7), now);
      cool.update(!bit_at(img, 28), now);
      Mode m = heat.active() && cool.active() ? MODE_BOTH : heat.active() ? MODE_HEAT : cool.active() ? MODE_COOL : MODE_UNKNOWN;
      if (m != mode_cand) { mode_cand = m; mode_since = now; }
      // "no symbol" does not change the mode: keep the last one that was shown
      if (mode_cand != MODE_UNKNOWN && mode_cand != mode && now - mode_since >= 1000) { mode = mode_cand; mode_changed = true; }
    }

    // 3) key: the same tail 3 times in a row
    bool idle = f.tail_idle || !f.tail_ok;   // a tail that could not be read does not count as a key
    uint16_t code = idle ? 0 : f.tail;
    if (cand_tail_n && idle == cand_idle && code == cand_tail) { if (cand_tail_n < 255) cand_tail_n++; }
    else { cand_idle = idle; cand_tail = code; cand_tail_n = 1; }
    if (cand_tail_n == 3) {
      Key k = idle ? KEY_NONE : key_of(code);
      if (k != key || (k == KEY_UNKNOWN && code != key_code)) { key = k; key_code = code; key_changed = true; }
    }
  }

 protected:
  void decode_image_() {
    // constant bits: 15, 23 = 1; 29-31 = 010; 32-35 = 0000; 37 = 0; 38 = not(36)
    bool odd = !bit_at(img, 15) || !bit_at(img, 23) || bit_at(img, 29) || !bit_at(img, 30) || bit_at(img, 31) ||
               bit_at(img, 32) || bit_at(img, 33) || bit_at(img, 34) || bit_at(img, 35) || bit_at(img, 37) ||
               (bit_at(img, 38) == bit_at(img, 36));
    if (odd) odd_bits++;

    bool sp = bit_at(img, 36);
    if (!screen_valid || sp != screen_setpoint) { screen_setpoint = sp; screen_valid = true; screen_changed = true; }

    int te = digit_at(img, 16), un = digit_at(img, 8), dc = digit_at(img, 0);
    if (te < 0 || un < 0 || un > 9 || dc < 0 || dc > 9) bad_digits++;
    else {
      float v = (te == 10 ? 0 : te) * 10 + un + dc / 10.0f;
      if (sp) { if (!(v == setpoint)) { setpoint = v; setpoint_changed = true; } }
      else { if (!(v == room)) { room = v; room_changed = true; } }
    }

    unsigned s4 = ((unsigned) bit_at(img, 24) << 3) | ((unsigned) bit_at(img, 25) << 2) | ((unsigned) bit_at(img, 26) << 1) | (unsigned) bit_at(img, 27);
    Speed s = s4 == 0x7 ? SPEED_AUTO : s4 == 0xB ? SPEED_NIGHT : s4 == 0xD ? SPEED_LOW : s4 == 0xE ? SPEED_HIGH : SPEED_UNKNOWN;
    if (!speed_valid || s != speed) { speed = s; speed_valid = true; speed_changed = true; }
  }
};

inline Tracker &tracker() { static Tracker t; return t; }

}  // namespace fancoil

// -- ESP32 ONLY -------------------------------------------------------------------
#ifdef USE_ESP32
#include <cstring>
#include <cstdlib>
#include "esp_heap_caps.h"
#include "esphome/core/log.h"
#include "esphome/core/hal.h"
namespace fancoil {
// Prints a burst EXACTLY like ESPHome's "dump: raw", so that the tools (fcwave.load_bursts)
// read logs of this firmware the same way as logs of raw_capture.yaml.
// The tag tells the lines apart: "remote.raw" = white wire (as always), "remote.yellow" = yellow wire.
inline void log_raw_tag(const char *TAG, const int32_t *b, size_t n) {
  char buf[256];
  int pos = snprintf(buf, sizeof(buf), "Received Raw: ");
  for (size_t i = 0; i < n; i++) {
    char one[16];
    int w = snprintf(one, sizeof(one), i + 1 < n ? "%d, " : "%d", (int) b[i]);
    if (pos + w >= (int) sizeof(buf) - 1) { ESP_LOGI(TAG, "%s", buf); pos = snprintf(buf, sizeof(buf), "  "); }
    memcpy(buf + pos, one, w + 1);
    pos += w;
  }
  if (pos) ESP_LOGI(TAG, "%s", buf);
}
inline void log_raw(const int32_t *b, size_t n) { log_raw_tag("remote.raw", b, n); }
inline uint32_t &yellow_bursts() { static uint32_t n = 0; return n; }

// -- RECORDING TO MEMORY ----------------------------------------------------------
// Printing both wires live does not fit in the log stream (over a slow link only 18-25 of the 31 lines/s of the
// white wire arrived). Here the bursts are written to RAM with no printing at all and printed AFTERWARDS, at a
// rate the stream can carry. Each burst keeps a sequence number and the time the loop received it (us from the
// start of the recording).
//
// Memory: a 6-byte header per burst (channel, count, 4 bytes of time) + values of variable length:
//   1 byte for -64...63 us (95% of the yellow wire, 83% of the white), 2 bytes for +-16383 us.  ~3.7 kB/s for both wires.
//
// Printing (tag "rec"), several bursts per line, separated by "|":
//   <seq> <W|Y> <us>:v,v,v|<seq> <W|Y> <us>:v,v,...      W = white, Y = yellow; lower case w/y = continuation of the same burst
struct Recorder {
  uint8_t *buf{nullptr};
  size_t cap{0}, len{0}, pos{0};
  bool recording{false}, dumping{false}, state_changed{false};
  uint32_t t0_us{0}, dur_ms{0}, t0_ms{0}, n_w{0}, n_y{0}, seq{0}, took_ms{0};
  char state[64]{"idle"};
  void set_state_(const char *fmt, unsigned a = 0, unsigned b = 0) { snprintf(state, sizeof(state), fmt, a, b); state_changed = true; }

  // The button: starts a recording; if one is running, stops it and prints what it has.
  void toggle(uint32_t ms) {
    if (recording) { stop("stopped by the button"); return; }
    if (dumping) { ESP_LOGW("rec", "still printing the previous recording"); return; }
    size_t big = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT);
    size_t bytes = big > 44000 ? big - 24000 : 0;            // leave room for WiFi and the API
    if (bytes > 130000) bytes = 130000;
    if (bytes < 20000) { ESP_LOGE("rec", "no memory (largest free block %u)", (unsigned) big); set_state_("failed: no memory"); return; }
    buf = (uint8_t *) malloc(bytes);
    if (!buf) { ESP_LOGE("rec", "could not allocate %u bytes", (unsigned) bytes); set_state_("failed: no memory"); return; }
    cap = bytes; len = pos = 0; n_w = n_y = seq = 0; dur_ms = ms; t0_us = micros(); t0_ms = millis(); recording = true;
    unsigned fits = (unsigned) (cap / 3700);
    ESP_LOGI("rec", "START %u ms, memory %u bytes (largest free block %u), fits about %u s", (unsigned) ms, (unsigned) cap, (unsigned) big, fits);
    set_state_("RECORDING - up to %u s", fits < ms / 1000 ? fits : (unsigned) (ms / 1000));
  }
  void add(uint8_t ch, const int32_t *b, size_t n) {
    if (!recording) return;
    if (millis() - t0_ms > dur_ms) { stop("time up"); return; }
    if (n > 200) n = 200;
    if (len + 6 + 2 * n > cap) { stop("MEMORY FULL"); return; }
    uint32_t t = micros() - t0_us;
    buf[len++] = ch; buf[len++] = (uint8_t) n;
    buf[len++] = t & 0xFF; buf[len++] = (t >> 8) & 0xFF; buf[len++] = (t >> 16) & 0xFF; buf[len++] = (t >> 24) & 0xFF;
    for (size_t i = 0; i < n; i++) {
      int32_t v = b[i]; if (v > 16383) v = 16383; if (v < -16383) v = -16383;
      if (v >= -64 && v <= 63) buf[len++] = (uint8_t) (v & 0x7F);
      else { buf[len++] = (uint8_t) (0x80 | ((v >> 8) & 0x7F)); buf[len++] = (uint8_t) (v & 0xFF); }
    }
    if (ch == 1) n_w++; else n_y++;
  }
  void stop(const char *why) {
    recording = false; dumping = true; pos = 0; took_ms = millis() - t0_ms;
    ESP_LOGI("rec", "END (%s) after %u ms: white %u bursts, yellow %u bursts, %u bytes", why, (unsigned) took_ms, (unsigned) n_w, (unsigned) n_y, (unsigned) len);
    set_state_("printing %u s of recording...", (unsigned) ((took_ms + 500) / 1000));
  }
  // Called every 100 ms; prints up to max_chars characters and returns.
  void dump_some(int max_chars) {
    if (recording && millis() - t0_ms > dur_ms + 500) stop("time up, no bursts");
    if (!dumping) return;
    int budget = max_chars;
    char line[420]; int p = 0;
    auto flush = [&]() { if (p) { ESP_LOGI("rec", "%s", line); budget -= p + 40; p = 0; } };
    while (pos < len && budget > 0) {
      uint8_t ch = buf[pos]; size_t n = buf[pos + 1];
      uint32_t t = (uint32_t) buf[pos + 2] | ((uint32_t) buf[pos + 3] << 8) | ((uint32_t) buf[pos + 4] << 16) | ((uint32_t) buf[pos + 5] << 24);
      size_t q = pos + 6;
      if (p > 300) flush();
      p += snprintf(line + p, sizeof(line) - p, "%s%u %c %u:", p ? "|" : "", (unsigned) seq, ch == 1 ? 'W' : 'Y', (unsigned) t);
      for (size_t i = 0; i < n; i++) {
        int v;
        if (buf[q] & 0x80) { v = ((buf[q] & 0x7F) << 8) | buf[q + 1]; if (v & 0x4000) v -= 0x8000; q += 2; }
        else { v = buf[q] & 0x7F; if (v & 0x40) v -= 0x80; q += 1; }
        if (p > (int) sizeof(line) - 24) { flush(); p = snprintf(line, sizeof(line), "%u %c %u:", (unsigned) seq, ch == 1 ? 'w' : 'y', (unsigned) t); }
        p += snprintf(line + p, sizeof(line) - p, i + 1 < n ? "%d," : "%d", v);
      }
      seq++; pos = q;
    }
    flush();
    if (pos >= len) {
      dumping = false; free(buf); buf = nullptr;
      ESP_LOGI("rec", "DONE %u bursts", (unsigned) seq);
      set_state_("done: %u bursts in %u s", (unsigned) seq, (unsigned) ((took_ms + 500) / 1000));
    }
  }
};
inline Recorder &recorder() { static Recorder r; return r; }
}  // namespace fancoil
#endif
