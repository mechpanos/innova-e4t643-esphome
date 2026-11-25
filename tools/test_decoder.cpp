// test_decoder.cpp - runs the firmware decoder (esphome/fancoil_decode.h) on a PC.
// Called by test_decoder.py. Input (stdin), one burst per line:  <ms> <v1> <v2> ...
// Output:  F <ms> <ok> <pre> <56 bits> <idle|-|16 tail bits>     for every burst
//          E <ms> <what changed>                                 for every publication of the Tracker
#include "fancoil_decode.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <string>
#include <iostream>
#include <sstream>

int main() {
  fancoil::Tracker tr;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream is(line);
    long long ms; is >> ms;
    std::vector<int32_t> b; long v;
    while (is >> v) b.push_back((int32_t) v);
    if (b.empty()) continue;
    fancoil::Frame f = fancoil::parse(b.data(), b.size());
    char bits[57]; for (int k = 0; k < 56; k++) bits[k] = fancoil::bit_at(f.bits, k) ? '1' : '0'; bits[56] = 0;
    char tail[17] = "-";
    if (f.ok && f.tail_idle) strcpy(tail, "idle");
    else if (f.ok && f.tail_ok) { for (int k = 0; k < 16; k++) tail[k] = (f.tail >> (15 - k)) & 1 ? '1' : '0'; tail[16] = 0; }
    printf("F %lld %d %d %s %s\n", ms, f.ok ? 1 : 0, f.pre, f.ok ? bits : "-", tail);

    tr.feed(b.data(), b.size(), (uint32_t) ms);
    if (tr.img_changed) { char h[24]; fancoil::hex_of(tr.img, h); printf("E %lld image %s\n", ms, h); }
    if (tr.room_changed) printf("E %lld room %.1f\n", ms, tr.room);
    if (tr.setpoint_changed) printf("E %lld setpoint %.1f\n", ms, tr.setpoint);
    if (tr.speed_changed) printf("E %lld fan %s\n", ms, fancoil::speed_name(tr.speed));
    if (tr.screen_changed) printf("E %lld screen-shows %s\n", ms, tr.screen_setpoint ? "setpoint" : "room");
    if (tr.heat.changed) printf("E %lld heating-symbol %s\n", ms, fancoil::sym_name(tr.heat.pub));
    if (tr.cool.changed) printf("E %lld cooling-symbol %s\n", ms, fancoil::sym_name(tr.cool.pub));
    if (tr.mode_changed) printf("E %lld mode %s\n", ms, fancoil::mode_name(tr.mode));
    if (tr.key_changed) {
      if (tr.key == fancoil::KEY_UNKNOWN) printf("E %lld key unknown-%04X\n", ms, tr.key_code);
      else printf("E %lld key %s\n", ms, fancoil::key_name(tr.key));
    }
    tr.clear_changes();
  }
  printf("S frames=%u rejected=%u bad_digits=%u odd_bits=%u\n", tr.frames, tr.rejected, tr.bad_digits, tr.odd_bits);
  return 0;
}
