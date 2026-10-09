/// Gold1 v0.9 paired-AC scheduler prototype.
/// Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
///
/// This Gold1-authored harness measures a strict 12-thread-budget experiment:
/// AC(H) and AC(X) are evaluated concurrently using separate thread budgets.
/// The arithmetic remains upstream primecount v8.7 AC; this prototype tests
/// whether endpoint concurrency removes wall-clock time before a deeper
/// shared-segment AC kernel is attempted.
///
/// primecount remains Copyright (C) Kim Walisch and BSD 2-Clause licensed.

#include <gourdon.hpp>
#include <primecount-internal.hpp>

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

using primecount::AC;
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
  if (argc < 9 || argc > 10)
  {
    std::cerr
      << "Usage: gold1-delta-ac-sched H X y z k hi_threads lo_threads total_threads [--verify]\n"
      << "Example:\n"
      << "  gold1-delta-ac-sched 1000000100000000000 999999999999999999 "
         "32221967 32221967 8 6 6 12 --verify\n";
    return 2;
  }

  int64_t H = parse_i64(argv[1], "H");
  int64_t X = parse_i64(argv[2], "X");
  int64_t y = parse_i64(argv[3], "y");
  int64_t z = parse_i64(argv[4], "z");
  int64_t k = parse_i64(argv[5], "k");
  int hi_threads = (int) parse_i64(argv[6], "hi_threads");
  int lo_threads = (int) parse_i64(argv[7], "lo_threads");
  int total_threads = (int) parse_i64(argv[8], "total_threads");
  bool verify = argc == 10 && std::string(argv[9]) == "--verify";

  if (argc == 10 && !verify)
  {
    std::cerr << "Unknown option: " << argv[9] << "\n";
    return 2;
  }
  if (H <= X || X < 0 || y < 1 || z < y || k < 0 ||
      hi_threads < 1 || lo_threads < 1 || total_threads < 1 ||
      hi_threads + lo_threads > total_threads)
  {
    std::cerr << "Invalid parameters; require H>X>=0, z>=y>=1, k>=0, "
                 "threads>=1 and hi_threads+lo_threads<=total_threads.\n";
    return 2;
  }

  std::cout << "Gold1 v0.9 paired-AC scheduler prototype\n"
            << "H=" << H << "\n"
            << "X=" << X << "\n"
            << "y=" << y << " z=" << z << " k=" << k << "\n"
            << "hi_threads=" << hi_threads
            << " lo_threads=" << lo_threads
            << " total_thread_budget=" << total_threads << "\n";

  int64_t acH = 0;
  int64_t acX = 0;
  double t0 = get_time();
  std::thread high([&] { acH = AC(H, y, z, k, hi_threads, false); });
  std::thread low ([&] { acX = AC(X, y, z, k, lo_threads, false); });
  high.join();
  low.join();
  double concurrent_seconds = get_time() - t0;
  int64_t delta = acH - acX;

  std::cout << "AC_H=" << acH << "\n"
            << "AC_X=" << acX << "\n"
            << "delta_AC=" << delta << "\n"
            << std::fixed << std::setprecision(6)
            << "concurrent_AC_seconds=" << concurrent_seconds << "\n";

  if (!verify)
    return 0;

  double r0 = get_time();
  int64_t refH = AC(H, y, z, k, total_threads, false);
  int64_t refX = AC(X, y, z, k, total_threads, false);
  double reference_seconds = get_time() - r0;
  int64_t ref_delta = refH - refX;

  std::cout << "reference_AC_H=" << refH << "\n"
            << "reference_AC_X=" << refX << "\n"
            << "reference_delta_AC=" << ref_delta << "\n"
            << std::fixed << std::setprecision(6)
            << "reference_AC_pair_seconds=" << reference_seconds << "\n"
            << "AC_scheduler_speedup=" << (reference_seconds / concurrent_seconds) << "x\n";

  if (acH != refH || acX != refX || delta != ref_delta)
  {
    std::cerr << "FAIL: concurrent AC endpoints do not match upstream sequential AC.\n";
    return 1;
  }

  std::cout << "PASS: concurrent AC endpoints exactly match upstream AC(H) and AC(X).\n";
  return 0;
}
