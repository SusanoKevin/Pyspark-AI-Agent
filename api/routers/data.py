from fastapi import APIRouter, Depends, HTTPException, Request, Response

from api.deps import get_current_user, get_store
from src.security import UserContext


def _call(fn):
    try:
        return fn()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        if "pyspark" in type(e).__module__:
            raise HTTPException(status_code=503, detail=f"Spark unavailable: {e}")
        raise

router = APIRouter()


def _parse_segments(segments_str: str) -> list[str] | None:
    segments = [s.strip() for s in segments_str.split(",") if s.strip()]
    return segments or None


@router.get("/summary")
def summary(request: Request, response: Response, _: UserContext = Depends(get_current_user)):
    response.headers["Cache-Control"] = "private, max-age=300"
    return _call(lambda: get_store(request).summary())


@router.get("/alerts")
def alerts(
    request: Request,
    response: Response,
    threshold: float = 75.0,
    segments: str = "",
    date_from: str = "",
    date_to: str = "",
    _: UserContext = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
    store = get_store(request)
    df = _call(lambda: store.get_threshold_alerts(
        threshold=threshold,
        segments=_parse_segments(segments),
        date_from=date_from or None,
        date_to=date_to or None,
    ))
    return [] if df.empty else df.to_dict(orient="records")


@router.get("/stats")
def stats(
    request: Request,
    response: Response,
    group_by: str = "",
    period: str = "all",
    segments: str = "",
    date_from: str = "",
    date_to: str = "",
    _: UserContext = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
    store = get_store(request)
    df = _call(lambda: store.compute_stats(
        group_by=group_by,
        period=period,
        segments=_parse_segments(segments),
        date_from=date_from or None,
        date_to=date_to or None,
    ))
    return [] if df.empty else df.to_dict(orient="records")


@router.get("/trends")
def trends(
    request: Request,
    response: Response,
    segments: str = "",
    _: UserContext = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
    store = get_store(request)
    segs = _parse_segments(segments)
    current  = _call(lambda: store.compute_stats(group_by="week", period="last_30_days",  segments=segs))
    previous = _call(lambda: store.compute_stats(group_by="week", period="prior_30_days", segments=segs))
    return {
        "current":  [] if current.empty  else current.to_dict(orient="records"),
        "previous": [] if previous.empty else previous.to_dict(orient="records"),
    }


@router.get("/sparklines")
def sparklines(
    request: Request,
    response: Response,
    ids: str,
    _: UserContext = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
    store    = get_store(request)
    safe_ids = [x.strip() for x in ids.split(",") if 0 < len(x.strip()) <= 50]
    if not safe_ids:
        return {}
    return _call(lambda: store.entity_weekly_rates(safe_ids))
