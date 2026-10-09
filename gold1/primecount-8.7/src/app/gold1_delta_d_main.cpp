/// Gold1 v0.7.1 paired-D validation/benchmark harness.
/// Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
/// Links against a patched primecount v8.7 tree.

#include <gourdon.hpp>
#include <primecount-internal.hpp>

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

using primecount::D;
using primecount::Gold1_D_delta;
using primecount::get_time;

static int64_t parse_i64(const char* s, const char* name)
{
  try
  {
    std::size_t pos = 0;
    std::string str(s);
    long long v = std::stoll(str, &pos, 10);
    if (pos != str.size())
      throw std::invalid_argument("trailing characters");
    return (int64_t) v;
  }
  catch (const std::exception& e)
  {
    std::cerr << "Invalid " << name << ": " << s << " (" << e.what() << ")\n";
    std::exit(2);
  }
}

int main(int argc, char** argv)
{
  if (argc < 7 || argc > 8)
  {
    std::cerr
      << "Usage: gold1-delta-d H X y z k threads [--verify]\n"
      << "Example:\n"
      << "  gold1-delta-d 1000000100000000000 999999999999999999 "
         "32221967 32221967 8 12 --verify\n";
    return 2;
  }

  int64_t H = parse_i64(argv[1], "H");
  int64_t X = parse_i64(argv[2], "X");
  int64_t y = parse_i64(argv[3], "y");
  int64_t z = parse_i64(argv[4], "z");
  int64_t k = parse_i64(argv[5], "k");
  int threads = (int) parse_i64(argv[6], "threads");
  bool verify = argc == 8 && std::string(argv[7]) == "--verify";

  if (argc == 8 && !verify)
  {
    std::cerr << "Unknown option: " << argv[7] << "\n";
    return 2;
  }

  std::cout << "Gold1 v0.7.1 paired-D thin-interval fix\n"
            << "H=" << H << "\n"
            << "X=" << X << "\n"
            << "y=" << y << " z=" << z << " k=" << k
            << " threads=" << threads << "\n";

  double t0 = get_time();
  int64_t delta = Gold1_D_delta(H, X, y, z, k, threads, false);
  double paired_seconds = get_time() - t0;

  std::cout << "delta_D=" << delta << "\n"
            << std::fixed << std::setprecision(6)
            << "paired_seconds=" << paired_seconds << "\n";

  if (!verify)
    return 0;

  t0 = get_time();
  int64_t dH = D(H, y, z, k, threads, false);
  double ref_H_seconds = get_time() - t0;

  t0 = get_time();
  int64_t dX = D(X, y, z, k, threads, false);
  double ref_X_seconds = get_time() - t0;

  int64_t ref_delta = dH - dX;
  double ref_seconds = ref_H_seconds + ref_X_seconds;

  std::cout << "reference_D_H=" << dH << "\n"
            << "reference_D_X=" << dX << "\n"
            << "reference_delta_D=" << ref_delta << "\n"
            << "reference_H_seconds=" << ref_H_seconds << "\n"
            << "reference_X_seconds=" << ref_X_seconds << "\n"
            << "reference_pair_seconds=" << ref_seconds << "\n";

  if (paired_seconds > 0)
    std::cout << "D_pair_speedup=" << (ref_seconds / paired_seconds) << "x\n";

  if (delta != ref_delta)
  {
    std::cerr << "FAIL: paired delta does not match D(H)-D(X).\n";
    return 1;
  }

  std::cout << "PASS: paired delta exactly matches D(H)-D(X).\n";
  return 0;
}
