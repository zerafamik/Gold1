///
/// @file D_delta_gold1.cpp
/// @brief Gold1 experimental paired-endpoint D-delta kernel.
///
/// This file is derived from primecount v8.7 src/gourdon/D.cpp.
/// Upstream copyright (C) 2026 Kim Walisch <kim.walisch@gmail.com>.
/// primecount is distributed under the BSD 2-Clause License.
///
/// Gold1 experimental modifications Copyright (C) 2026 [YOUR LEGAL NAME].
/// All rights reserved for the Gold1-authored modifications.
/// Upstream primecount portions remain under the BSD 2-Clause License.
///
/// Purpose:
///   Compute D(H,y,z,k) - D(X,y,z,k) while sharing the factor table,
///   pi table, primes, segmented sieve traversal, phi trajectory and
///   candidate filtering between two nearby endpoints H > X.
///
/// Correctness comes before speed in this prototype. The original D()
/// remains untouched and is used by the benchmark executable as the
/// reference implementation.
///

#include "FactorTableD.hpp"

#include <primecount.hpp>
#include <primecount-internal.hpp>
#include <macros.hpp>
#include <PiTable.hpp>
#include <sieve/Sieve.hpp>
#include <LoadBalancerS2.hpp>
#include <fast_div.hpp>
#include <phi_vector.hpp>
#include <gourdon.hpp>
#include <imath.hpp>
#include <min.hpp>

#include <stdint.h>
#include <algorithm>
#include <cmath>

namespace {

using namespace primecount;

struct LeafRange
{
  int64_t lo = 0; // exclusive index
  int64_t hi = -1; // inclusive index
  bool stop = true;
};

template <typename T, typename FactorTable>
LeafRange squarefree_range(T x,
                           int64_t prime,
                           int64_t low1,
                           int64_t high,
                           int64_t z)
{
  LeafRange r;
  T xp = x / prime;
  int64_t xp_low = min(fast_div(xp, low1), z);
  int64_t xp_high = min(fast_div(xp, high), z);
  int64_t min_m = max(xp_high, z / prime);
  int64_t max_m = min(fast_div(xp, prime * prime), xp_low);

  if (prime >= max_m)
    return r;

  r.lo = FactorTable::to_index(min_m);
  r.hi = FactorTable::to_index(max_m);
  r.stop = false;
  return r;
}

template <typename T, typename Primes>
LeafRange two_prime_range(T x,
                          int64_t prime,
                          int64_t low1,
                          int64_t high,
                          int64_t y,
                          const PiTable& pi,
                          const Primes& primes)
{
  LeafRange r;
  T xp = x / prime;
  int64_t xp_low = min(fast_div(xp, low1), y);
  int64_t xp_high = min(fast_div(xp, high), y);
  int64_t min_m = max(xp_high, prime);
  int64_t max_m = min(fast_div(xp, prime * prime), xp_low);
  int64_t l = pi[max_m];

  if (prime >= primes[l])
    return r;

  r.lo = pi[min_m];
  r.hi = l;
  r.stop = false;
  return r;
}

template <typename T, typename Primes, typename FactorTable>
int64_t paired_squarefree_delta(T H,
                                T X,
                                bool active_H,
                                bool active_X,
                                int64_t b,
                                int64_t prime,
                                int64_t low,
                                int64_t low1,
                                int64_t high_H,
                                int64_t high_X,
                                int64_t z,
                                const FactorTable& factor,
                                Sieve& sieve,
                                int64_t phi_b,
                                bool& stop_H,
                                bool& stop_X)
{
  LeafRange rh;
  LeafRange rx;

  if (active_H)
  {
    rh = squarefree_range<T, FactorTable>(H, prime, low1, high_H, z);
    stop_H = rh.stop;
  }

  if (active_X)
  {
    rx = squarefree_range<T, FactorTable>(X, prime, low1, high_X, z);
    stop_X = rx.stop;
  }

  if ((!active_H || stop_H) && (!active_X || stop_X))
    return 0;

  const auto* factor_table = factor.data();
  int64_t encoded_prime = FactorTable::encode(b);

  int64_t union_hi = -1;
  int64_t union_lo = INT64_MAX;
  if (active_H && !stop_H)
  {
    union_hi = max(union_hi, rh.hi);
    union_lo = min(union_lo, rh.lo);
  }
  if (active_X && !stop_X)
  {
    union_hi = max(union_hi, rx.hi);
    union_lo = min(union_lo, rx.lo);
  }

  if (union_hi <= union_lo)
    return 0;

  T xp_H = active_H && !stop_H ? H / prime : 0;
  T xp_X = active_X && !stop_X ? X / prime : 0;
  int64_t delta = 0;

  // Filter the union once. On the overlap, phi_b cancels exactly.
  for (int64_t idx = union_hi; idx > union_lo; --idx)
  {
    if (factor_table[idx] <= encoded_prime)
      continue;

    bool in_H = active_H && !stop_H && idx <= rh.hi && idx > rh.lo;
    bool in_X = active_X && !stop_X && idx <= rx.hi && idx > rx.lo;
    if (!in_H && !in_X)
      continue;

    int64_t m = factor.to_number(idx);
    int64_t mu = factor.mu(idx);

    if (in_H && in_X)
    {
      int64_t qH = fast_div64(xp_H, m);
      int64_t qX = fast_div64(xp_X, m);
      if (qH == qX)
        continue;

      // IMPORTANT: Sieve::count(stop) is stateful and requires each stop
      // to be >= the previous stop. Since H > X, qH >= qX; calling the
      // H prefix first and then the X prefix is illegal in Release builds
      // and collapses the shared-leaf delta toward zero. Count the thin
      // interval (qX, qH] directly instead. This overload is stateless.
      ASSERT(qH >= qX);
      uint64_t start = uint64_t((qX - low) + 1);
      uint64_t stop = uint64_t(qH - low);
      int64_t count_delta = (int64_t) sieve.count(start, stop);
      delta -= mu * count_delta;
    }
    else if (in_H)
    {
      int64_t qH = fast_div64(xp_H, m);
      int64_t count_H = sieve.count(qH - low);
      delta -= mu * (phi_b + count_H);
    }
    else
    {
      int64_t qX = fast_div64(xp_X, m);
      int64_t count_X = sieve.count(qX - low);
      // delta = D(H) - D(X), while D's squarefree leaf is -mu*phi.
      delta += mu * (phi_b + count_X);
    }
  }

  return delta;
}

template <typename T, typename Primes>
int64_t paired_two_prime_delta(T H,
                               T X,
                               bool active_H,
                               bool active_X,
                               int64_t prime,
                               int64_t low,
                               int64_t low1,
                               int64_t high_H,
                               int64_t high_X,
                               int64_t y,
                               const PiTable& pi,
                               const Primes& primes,
                               Sieve& sieve,
                               int64_t phi_b,
                               bool& stop_H,
                               bool& stop_X)
{
  LeafRange rh;
  LeafRange rx;

  if (active_H)
  {
    rh = two_prime_range(H, prime, low1, high_H, y, pi, primes);
    stop_H = rh.stop;
  }

  if (active_X)
  {
    rx = two_prime_range(X, prime, low1, high_X, y, pi, primes);
    stop_X = rx.stop;
  }

  if ((!active_H || stop_H) && (!active_X || stop_X))
    return 0;

  int64_t union_hi = -1;
  int64_t union_lo = INT64_MAX;
  if (active_H && !stop_H)
  {
    union_hi = max(union_hi, rh.hi);
    union_lo = min(union_lo, rh.lo);
  }
  if (active_X && !stop_X)
  {
    union_hi = max(union_hi, rx.hi);
    union_lo = min(union_lo, rx.lo);
  }

  if (union_hi <= union_lo)
    return 0;

  T xp_H = active_H && !stop_H ? H / prime : 0;
  T xp_X = active_X && !stop_X ? X / prime : 0;
  int64_t delta = 0;

  for (int64_t l = union_hi; l > union_lo; --l)
  {
    bool in_H = active_H && !stop_H && l <= rh.hi && l > rh.lo;
    bool in_X = active_X && !stop_X && l <= rx.hi && l > rx.lo;
    if (!in_H && !in_X)
      continue;

    int64_t q = primes[l];

    if (in_H && in_X)
    {
      int64_t qp_H = fast_div64(xp_H, q);
      int64_t qp_X = fast_div64(xp_X, q);
      if (qp_H == qp_X)
        continue;

      // Same monotonic-prefix issue as the square-free path above.
      // Directly count the live entries in (qp_X, qp_H].
      ASSERT(qp_H >= qp_X);
      uint64_t start = uint64_t((qp_X - low) + 1);
      uint64_t stop = uint64_t(qp_H - low);
      int64_t count_delta = (int64_t) sieve.count(start, stop);
      delta += count_delta;
    }
    else if (in_H)
    {
      int64_t qp_H = fast_div64(xp_H, q);
      int64_t count_H = sieve.count(qp_H - low);
      delta += phi_b + count_H;
    }
    else
    {
      int64_t qp_X = fast_div64(xp_X, q);
      int64_t count_X = sieve.count(qp_X - low);
      delta -= phi_b + count_X;
    }
  }

  return delta;
}

template <typename T, typename Primes, typename FactorTable>
int64_t D_delta_thread(T H,
                       T X,
                       int64_t x_star_H,
                       int64_t x_star_X,
                       int64_t xz_H,
                       int64_t xz_X,
                       int64_t y,
                       int64_t z,
                       int64_t k,
                       const Primes& primes,
                       const PiTable& pi,
                       const FactorTable& factor,
                       ThreadData& thread)
{
  int64_t low = thread.low;
  int64_t low1 = max(low, 1);
  int64_t segments = thread.segments;
  int64_t segment_size = thread.segment_size;
  int64_t chunk_end = low + segment_size * segments;
  int64_t limit_H = min(chunk_end, xz_H);
  int64_t limit_X = min(chunk_end, xz_X);
  bool chunk_H = low < limit_H;
  bool chunk_X = low < limit_X;

  if (!chunk_H && !chunk_X)
    return 0;

  int64_t min_b_H = INT64_MAX, max_b_H = -1;
  int64_t min_b_X = INT64_MAX, max_b_X = -1;

  if (chunk_H)
  {
    max_b_H = pi[min3(isqrt(H / low1), isqrt(limit_H), x_star_H)];
    min_b_H = pi[min(xz_H / limit_H, x_star_H)];
    min_b_H = max(k, min_b_H) + 1;
  }

  if (chunk_X)
  {
    max_b_X = pi[min3(isqrt(X / low1), isqrt(limit_X), x_star_X)];
    min_b_X = pi[min(xz_X / limit_X, x_star_X)];
    min_b_X = max(k, min_b_X) + 1;
  }

  int64_t min_b = min(min_b_H, min_b_X);
  int64_t max_b = max(max_b_H, max_b_X);
  if (min_b > max_b)
    return 0;

  int64_t pi_sqrtz = pi[isqrt(z)];
  Vector<int64_t> phi = phi_vector(low, max_b, primes, pi);
  Sieve sieve(low, segment_size, max_b);
  thread.init_time = get_time();
  int64_t delta = 0;

  for (; low < limit_H; low += segment_size)
  {
    int64_t high_H = min(low + segment_size, limit_H);
    bool seg_X = low < limit_X;
    int64_t high_X = seg_X ? min(low + segment_size, limit_X) : low;
    low1 = max(low, 1);

    sieve.pre_sieve(primes, min_b - 1, low, high_H);
    sieve.init_counter(low, high_H);

    bool done_H = !chunk_H;
    bool done_X = !seg_X;
    int64_t b = min_b;

    for (int64_t last = min(pi_sqrtz, max_b); b <= last; ++b)
    {
      int64_t prime = primes[b];
      bool active_H = !done_H && b >= min_b_H && b <= max_b_H;
      bool active_X = !done_X && b >= min_b_X && b <= max_b_X;
      bool stop_H = false;
      bool stop_X = false;

      delta += paired_squarefree_delta<T, Primes, FactorTable>(
          H, X, active_H, active_X, b, prime, low, low1,
          high_H, high_X, z, factor, sieve, phi[b], stop_H, stop_X);

      if (active_H && stop_H)
        done_H = true;
      if (active_X && stop_X)
        done_X = true;

      if (done_H && done_X)
        goto next_segment;

      phi[b] += sieve.get_total_count();
      sieve.cross_off_count(prime, b);
    }

    for (; b <= max_b; ++b)
    {
      int64_t prime = primes[b];
      bool active_H = !done_H && b >= min_b_H && b <= max_b_H;
      bool active_X = !done_X && b >= min_b_X && b <= max_b_X;
      bool stop_H = false;
      bool stop_X = false;

      delta += paired_two_prime_delta(
          H, X, active_H, active_X, prime, low, low1,
          high_H, high_X, y, pi, primes, sieve, phi[b], stop_H, stop_X);

      if (active_H && stop_H)
        done_H = true;
      if (active_X && stop_X)
        done_X = true;

      if (done_H && done_X)
        goto next_segment;

      phi[b] += sieve.get_total_count();
      sieve.cross_off_count(prime, b);
    }

    next_segment:;
  }

  return delta;
}

template <typename T, typename Primes, typename FactorTable>
int64_t D_delta_OpenMP(T H,
                       T X,
                       int64_t y,
                       int64_t z,
                       int64_t k,
                       const PiTable& pi,
                       const Primes& primes,
                       const FactorTable& factor,
                       int threads,
                       bool is_print)
{
  int64_t xz_H = H / z;
  int64_t xz_X = X / z;
  int64_t x_star_H = get_x_star_gourdon(H, y);
  int64_t x_star_X = get_x_star_gourdon(X, y);

  int64_t thread_threshold = 1 << 20;
  int max_threads = (int) std::pow(xz_H, 1 / 3.7);
  threads = std::min(threads, max_threads);
  threads = ideal_num_threads(xz_H, threads, thread_threshold);

  INDETERMINATE LoadBalancerS2 loadBalancer(H, y, xz_H, threads, is_print);
  int64_t delta = 0;

  #pragma omp parallel num_threads(threads) reduction(+: delta)
  {
    ThreadData thread;
    while (loadBalancer.get_work(thread))
    {
      thread.start_time = get_time();
      thread.sum = D_delta_thread<T>(H, X, x_star_H, x_star_X,
                                     xz_H, xz_X, y, z, k,
                                     primes, pi, factor, thread);
      thread.stop_time = get_time();
      delta += thread.sum;
    }
  }

  return delta;
}

} // namespace

namespace primecount {

int64_t Gold1_D_delta(int64_t H,
                      int64_t X,
                      int64_t y,
                      int64_t z,
                      int64_t k,
                      int threads,
                      bool is_print)
{
  if (H < X)
    std::swap(H, X);
  if (X < 0 || y < 1 || z < y || threads < 1)
    throw primecount_error("Gold1_D_delta: invalid arguments");

  FactorTableD<uint16_t> factor(y, z, threads);
  PiTable pi(y, threads);
  auto primes = pi.get_primes<uint32_t>(y, threads);

  return D_delta_OpenMP<uint64_t>((uint64_t) H, (uint64_t) X,
                                  y, z, k, pi, primes, factor,
                                  threads, is_print);
}

} // namespace primecount
