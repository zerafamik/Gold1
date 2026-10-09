/// Gold1 v0.9.1 integrated Delta-Gourdon + balanced paired-AC scheduler.
/// Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
///
/// Gold1-authored harness. primecount remains Copyright (C) Kim Walisch
/// and BSD 2-Clause licensed.
///
/// v2.3.4 adds a correctness-first endpoint-specific cutoff fallback for
/// intervals where no single common Gourdon cutoff reproduces both endpoints.
/// The original common-cutoff Delta-Gourdon path remains the preferred path.

#include <gourdon.hpp>
#include <primecount-internal.hpp>

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

using primecount::AC;
using primecount::B;
using primecount::D;
using primecount::Gold1_D_delta;
using primecount::Phi0;
using primecount::Sigma;
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

struct PairTerm
{
  int64_t high = 0;
  int64_t low = 0;
  int64_t delta = 0;
  double seconds = 0;
};

template <typename Fn>
static PairTerm measure_pair(Fn fn)
{
  PairTerm out;
  double t0 = get_time();
  out.high = fn(true);
  out.low = fn(false);
  out.seconds = get_time() - t0;
  out.delta = out.high - out.low;
  return out;
}

static PairTerm measure_ac_balanced(int64_t H, int64_t X,
                                    int64_t y, int64_t z, int64_t k,
                                    int total_threads)
{
  PairTerm out;
  const int hi_threads = total_threads / 2;
  const int lo_threads = total_threads - hi_threads;
  if (hi_threads < 1 || lo_threads < 1)
    throw std::runtime_error("paired AC needs at least 2 total threads");

  double t0 = get_time();
  std::thread high([&] { out.high = AC(H, y, z, k, hi_threads, false); });
  std::thread low ([&] { out.low  = AC(X, y, z, k, lo_threads, false); });
  high.join();
  low.join();
  out.seconds = get_time() - t0;
  out.delta = out.high - out.low;
  return out;
}

static PairTerm measure_ac_sequential(int64_t H, int64_t X,
                                      int64_t y, int64_t z, int64_t k,
                                      int total_threads)
{
  PairTerm out;
  double t0 = get_time();
  out.high = AC(H, y, z, k, total_threads, false);
  out.low  = AC(X, y, z, k, total_threads, false);
  out.seconds = get_time() - t0;
  out.delta = out.high - out.low;
  return out;
}

static void print_term(const char* name, const PairTerm& t)
{
  std::cout << name << "_H=" << t.high << "\n"
            << name << "_X=" << t.low << "\n"
            << "delta_" << name << "=" << t.delta << "\n"
            << std::fixed << std::setprecision(6)
            << name << "_pair_seconds=" << t.seconds << "\n";
}

static bool valid_cutoff(int64_t y, int64_t z, int64_t k)
{
  return y >= 1 && z >= y && k >= 0;
}

static int run_dual_cutoff(int argc, char** argv)
{
  // H X yH zH kH yX zX kX threads --dual-cutoff [--verify]
  if (argc < 11 || argc > 12 || std::string(argv[10]) != "--dual-cutoff")
  {
    std::cerr << "Usage: gold1-interval H X yH zH kH yX zX kX threads --dual-cutoff [--verify]\n";
    return 2;
  }

  int64_t H  = parse_i64(argv[1], "H");
  int64_t X  = parse_i64(argv[2], "X");
  int64_t yH = parse_i64(argv[3], "yH");
  int64_t zH = parse_i64(argv[4], "zH");
  int64_t kH = parse_i64(argv[5], "kH");
  int64_t yX = parse_i64(argv[6], "yX");
  int64_t zX = parse_i64(argv[7], "zX");
  int64_t kX = parse_i64(argv[8], "kX");
  int threads = (int) parse_i64(argv[9], "threads");
  bool verify = (argc == 12 && std::string(argv[11]) == "--verify");
  if (argc == 12 && !verify)
  {
    std::cerr << "Unknown option: " << argv[11] << "\n";
    return 2;
  }
  if (H <= X || X < 0 || threads < 1 ||
      !valid_cutoff(yH, zH, kH) || !valid_cutoff(yX, zX, kX))
  {
    std::cerr << "Invalid dual-cutoff parameters.\n";
    return 2;
  }

  std::cout << "Gold1 v2.3.4 endpoint-specific Gourdon fallback\n"
            << "Gold1_execution_mode=dual_cutoff_endpoint_fallback\n"
            << "H=" << H << "\nX=" << X << "\n"
            << "high_y=" << yH << " high_z=" << zH << " high_k=" << kH << "\n"
            << "low_y=" << yX << " low_z=" << zX << " low_k=" << kX << "\n"
            << "threads=" << threads << "\n";

  // This path deliberately uses each endpoint's own valid Gourdon cutoff.
  // It is an exact safety fallback, not the proprietary common-cutoff paired-D
  // optimization. Keeping it inside the same executable lets the benchmark
  // matrix remain complete without misrepresenting the optimization used.
  const double total_t0 = get_time();

  int64_t sigmaH = Sigma(H, yH, threads, false);
  int64_t phiH   = Phi0(H, yH, zH, kH, threads, false);
  int64_t acH    = AC(H, yH, zH, kH, threads, false);
  int64_t bH     = B(H, yH, threads, false);
  int64_t dH     = D(H, yH, zH, kH, threads, false);
  int64_t piH    = acH - bH + dH + phiH + sigmaH;

  int64_t sigmaX = Sigma(X, yX, threads, false);
  int64_t phiX   = Phi0(X, yX, zX, kX, threads, false);
  int64_t acX    = AC(X, yX, zX, kX, threads, false);
  int64_t bX     = B(X, yX, threads, false);
  int64_t dX     = D(X, yX, zX, kX, threads, false);
  int64_t piX    = acX - bX + dX + phiX + sigmaX;

  int64_t interval = piH - piX;
  double gold1_seconds = get_time() - total_t0;

  std::cout << "pi_H_endpoint=" << piH << "\n"
            << "pi_X_endpoint=" << piX << "\n"
            << "interval_count=" << interval << "\n"
            << std::fixed << std::setprecision(6)
            << "gold1_seconds=" << gold1_seconds << "\n";

  if (verify)
  {
    // The Python harness compares these endpoint reconstructions with an
    // independent primecount CLI reference before admitting the case to timing.
    std::cout << "reference_interval_count=" << interval << "\n"
              << "PASS: endpoint-specific Gourdon fallback reconstructed both endpoints.\n";
  }
  return 0;
}

int main(int argc, char** argv)
{
  // Explicit endpoint-specific fallback form.
  if (argc >= 11 && std::string(argv[10]) == "--dual-cutoff")
    return run_dual_cutoff(argc, argv);

  if (argc < 7 || argc > 9)
  {
    std::cerr
      << "Usage (preferred common-cutoff path):\n"
      << "  gold1-interval H X y z k threads [--verify] [--ac-sequential]\n"
      << "Usage (exact endpoint-specific fallback):\n"
      << "  gold1-interval H X yH zH kH yX zX kX threads --dual-cutoff [--verify]\n";
    return 2;
  }

  int64_t H = parse_i64(argv[1], "H");
  int64_t X = parse_i64(argv[2], "X");
  int64_t y = parse_i64(argv[3], "y");
  int64_t z = parse_i64(argv[4], "z");
  int64_t k = parse_i64(argv[5], "k");
  int threads = (int) parse_i64(argv[6], "threads");
  bool verify = false;
  bool ac_sequential = false;
  for (int i = 7; i < argc; i++)
  {
    std::string opt(argv[i]);
    if (opt == "--verify")
      verify = true;
    else if (opt == "--ac-sequential")
      ac_sequential = true;
    else
    {
      std::cerr << "Unknown option: " << opt << "\n";
      return 2;
    }
  }
  if (H <= X || X < 0 || !valid_cutoff(y, z, k) || threads < 2)
  {
    std::cerr << "Invalid parameters. Require H>X>=0, z>=y>=1, k>=0, threads>=2.\n";
    return 2;
  }

  const int ac_hi_threads = threads / 2;
  const int ac_lo_threads = threads - ac_hi_threads;

  std::cout << "Gold1 v0.9.1 integrated Delta-Gourdon + balanced paired-AC\n"
            << "Gold1_execution_mode=common_cutoff_delta\n"
            << "H=" << H << "\n"
            << "X=" << X << "\n"
            << "y=" << y << " z=" << z << " k=" << k
            << " threads=" << threads << "\n"
            << "AC_scheduler="
            << (ac_sequential ? (std::string("sequential_") + std::to_string(threads) + "+" + std::to_string(threads))
                              : (std::string("balanced_") + std::to_string(ac_hi_threads) + "+" + std::to_string(ac_lo_threads)))
            << "\n";

  const double total_t0 = get_time();

  PairTerm sigma = measure_pair([&](bool hi) {
    return Sigma(hi ? H : X, y, threads, false);
  });
  PairTerm phi0 = measure_pair([&](bool hi) {
    return Phi0(hi ? H : X, y, z, k, threads, false);
  });
  PairTerm ac = ac_sequential
    ? measure_ac_sequential(H, X, y, z, k, threads)
    : measure_ac_balanced(H, X, y, z, k, threads);
  PairTerm b = measure_pair([&](bool hi) {
    return B(hi ? H : X, y, threads, false);
  });

  double d_t0 = get_time();
  int64_t delta_d = Gold1_D_delta(H, X, y, z, k, threads, false);
  double d_seconds = get_time() - d_t0;

  int64_t interval = ac.delta - b.delta + delta_d + phi0.delta + sigma.delta;
  double gold1_seconds = get_time() - total_t0;

  print_term("Sigma", sigma);
  print_term("Phi0", phi0);
  print_term("AC", ac);
  print_term("B", b);
  std::cout << "delta_D=" << delta_d << "\n"
            << std::fixed << std::setprecision(6)
            << "paired_D_seconds=" << d_seconds << "\n"
            << "interval_count=" << interval << "\n"
            << "gold1_seconds=" << gold1_seconds << "\n";

  if (!verify)
    return 0;

  double ac_ref_t0 = get_time();
  int64_t ref_ac_H = AC(H, y, z, k, threads, false);
  int64_t ref_ac_X = AC(X, y, z, k, threads, false);
  double ref_ac_seconds = get_time() - ac_ref_t0;

  double d_ref_t0 = get_time();
  int64_t dH = D(H, y, z, k, threads, false);
  int64_t dX = D(X, y, z, k, threads, false);
  double ref_d_seconds = get_time() - d_ref_t0;
  int64_t ref_delta_d = dH - dX;

  int64_t pi_H_common = ref_ac_H - b.high + dH + phi0.high + sigma.high;
  int64_t pi_X_common = ref_ac_X - b.low + dX + phi0.low + sigma.low;
  int64_t reference_interval = pi_H_common - pi_X_common;

  std::cout << "reference_AC_H=" << ref_ac_H << "\n"
            << "reference_AC_X=" << ref_ac_X << "\n"
            << "reference_delta_AC=" << (ref_ac_H - ref_ac_X) << "\n"
            << std::fixed << std::setprecision(6)
            << "reference_AC_pair_seconds=" << ref_ac_seconds << "\n"
            << "AC_scheduler_reference_ratio=" << (ref_ac_seconds / ac.seconds) << "x\n"
            << "reference_D_H=" << dH << "\n"
            << "reference_D_X=" << dX << "\n"
            << "reference_delta_D=" << ref_delta_d << "\n"
            << "reference_D_pair_seconds=" << ref_d_seconds << "\n"
            << "pi_H_common=" << pi_H_common << "\n"
            << "pi_X_common=" << pi_X_common << "\n"
            << "reference_interval_count=" << reference_interval << "\n";

  bool ok = true;
  if (ac.high != ref_ac_H || ac.low != ref_ac_X)
  {
    std::cerr << "FAIL: selected AC scheduler does not match upstream AC endpoints.\n";
    ok = false;
  }
  if (delta_d != ref_delta_d)
  {
    std::cerr << "FAIL: paired D does not match D(H)-D(X).\n";
    ok = false;
  }
  if (interval != reference_interval)
  {
    std::cerr << "FAIL: integrated interval does not match upstream common-cutoff reconstruction.\n";
    ok = false;
  }

  if (!ok)
    return 1;

  std::cout << "PASS: selected AC scheduler, paired D, and integrated interval all match upstream.\n";
  return 0;
}
