#!/usr/bin/env python3
"""抖音运营数据指标计算。

用法：
  python calc_metrics.py --plays 1000 --likes 35 --comments 2 --shares 1 --favorites 6
  python calc_metrics.py --plays 1000 --likes 35 --like-good 3 --like-great 5 --swipe-healthy 55 --swipe 48.5

只做确定性计算，不接触账号、不编造数据；输入数据须来自创作者中心真实页面。
"""
import argparse
import json


def pct(part, whole):
    """返回百分比数值，whole 为 0 时返回 None，避免除零。"""
    if not whole:
        return None
    return round(part / whole * 100, 2)


def judge_like(like_rate, good=3.0, great=5.0):
    if like_rate is None:
        return "无数据"
    if like_rate >= great:
        return "优质"
    if like_rate >= good:
        return "合格"
    return "不合格"


def judge_swipe(swipe_rate, healthy=55.0):
    if swipe_rate is None:
        return "无数据"
    return "健康" if swipe_rate < healthy else "偏高"


def calc(plays, likes, comments, shares, favorites):
    return {
        "like_rate": pct(likes, plays),
        "comment_rate": pct(comments, plays),
        "share_rate": pct(shares, plays),
        "favorite_rate": pct(favorites, plays),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plays", type=int, required=True)
    ap.add_argument("--likes", type=int, default=0)
    ap.add_argument("--comments", type=int, default=0)
    ap.add_argument("--shares", type=int, default=0)
    ap.add_argument("--favorites", type=int, default=0)
    ap.add_argument("--swipe", type=float, default=None, help="划走率/2秒跳出率(%%)，页面直接给出")
    ap.add_argument("--like-good", type=float, default=3.0)
    ap.add_argument("--like-great", type=float, default=5.0)
    ap.add_argument("--swipe-healthy", type=float, default=55.0)
    args = ap.parse_args()

    rates = calc(args.plays, args.likes, args.comments, args.shares, args.favorites)
    rates["like_judgement"] = judge_like(rates["like_rate"], args.like_good, args.like_great)
    rates["swipe_judgement"] = judge_swipe(args.swipe, args.swipe_healthy)
    print(json.dumps(rates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
