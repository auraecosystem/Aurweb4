from fastapi import APIRouter, Request
from fastapi.responses import Response
from feedgen.feed import FeedGenerator

from aurweb import db, filters, models
from aurweb.models import Package, PackageBase, PackageComment
from aurweb.packages.util import get_pkg_or_base

router = APIRouter()


def make_rss_feed(request: Request, packages: list):
    """Create an RSS Feed string for some packages.

    :param request: A FastAPI request
    :param packages: A list of packages to add to the RSS feed
    :return: RSS Feed string
    """

    feed = FeedGenerator()
    feed.title("AUR Newest Packages")
    feed.description("The latest and greatest packages in the AUR")
    base = f"{request.url.scheme}://{request.url.netloc}"
    feed.link(href=base, rel="alternate")
    feed.link(href=f"{base}/rss", rel="self")
    feed.image(
        title="AUR Newest Packages",
        url=f"{base}/static/css/archnavbar/aurlogo.png",
        link=base,
        description="AUR Newest Packages Feed",
    )

    for pkg in packages:
        entry = feed.add_entry(order="append")
        entry.title(pkg.Name)
        entry.link(href=f"{base}/packages/{pkg.Name}", rel="alternate")
        entry.description(pkg.Description or str())
        dt = filters.timestamp_to_datetime(pkg.Timestamp)
        dt = filters.as_timezone(dt, request.user.Timezone)
        entry.pubDate(dt.strftime("%Y-%m-%d %H:%M:%S%z"))
        entry.guid(f"{pkg.Name}-{pkg.Timestamp}")

    return feed.rss_str()


def make_rss_feed_comments(request: Request, pkgbase: PackageBase, comments: list):
    """Create an RSS Feed string for some packages.

    :param request: A FastAPI request
    :param comments: A list of comments to add the to RSS feed
    :return: RSS Feed string
    """

    feed = FeedGenerator()
    feed.title(f"AUR Newest Comments for {pkgbase.Name}")
    feed.description(f"The 10 latest comments on {pkgbase.Name}")
    base = f"{request.url.scheme}://{request.url.netloc}"
    feed.link(href=base, rel="alternate")
    feed.link(href=f"{base}/rss/comments/{pkgbase.Name}", rel="self")
    feed.image(
        title=f"AUR Newest Comments for {pkgbase.Name}",
        url=f"{base}/static/css/archnavbar/aurlogo.png",
        link=base,
        description=f"The 10 latest comments on {pkgbase.Name}",
    )

    for comment in comments:
        entry = feed.add_entry(order="append")
        entry.title(comment.Comments[:60])
        entry.link(
            href=f"{base}/packages/{pkgbase.Name}#comment-{comment.ID}", rel="alternate"
        )
        entry.description(comment.Comments)
        dt = filters.timestamp_to_datetime(comment.CommentTS)
        dt = filters.as_timezone(dt, request.user.Timezone)
        entry.pubDate(dt.strftime("%Y-%m-%d %H:%M:%S%z"))
        entry.pubDate()
        entry.guid(f"{pkgbase.Name}-{comment.ID}")

    return feed.rss_str()


@router.get("/rss/comments/{package_name}")
async def comments(request: Request, package_name: str):
    pkg = get_pkg_or_base(package_name, models.Package)
    pkgbase = pkg.PackageBase
    comments = pkgbase.comments.order_by(PackageComment.CommentTS.desc()).limit(10)

    feed = make_rss_feed_comments(request, pkgbase, comments.all())
    response = Response(feed, media_type="application/rss+xml")

    return response


@router.get("/rss/")
async def rss(request: Request):
    packages = (
        db.query(Package)
        .join(PackageBase)
        .order_by(PackageBase.SubmittedTS.desc())
        .limit(100)
        .with_entities(
            Package.Name,
            Package.Description,
            PackageBase.SubmittedTS.label("Timestamp"),
        )
    )

    feed = make_rss_feed(request, packages)
    response = Response(feed, media_type="application/rss+xml")

    return response


@router.get("/rss/modified")
async def rss_modified(request: Request):
    packages = (
        db.query(Package)
        .join(PackageBase)
        .order_by(PackageBase.ModifiedTS.desc())
        .limit(100)
        .with_entities(
            Package.Name,
            Package.Description,
            PackageBase.ModifiedTS.label("Timestamp"),
        )
    )

    feed = make_rss_feed(request, packages)
    response = Response(feed, media_type="application/rss+xml")

    return response
