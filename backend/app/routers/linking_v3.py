from fastapi import APIRouter, HTTPException, Query

from entity_linkingv3 import LinkingV3Service, ServiceError
from ..schemas.linking_v3 import ApplyRequest, InitRunRequest, PairDecisionRequest, ResetRequest

router = APIRouter(prefix="/api/linking/v3", tags=["linking_v3"])
service = LinkingV3Service()


def _to_http(exc: ServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("/init")
def init_run(req: InitRunRequest):
    try:
        return service.prepare_run(
            input_dir=req.input_dir,
            score_threshold=req.score_threshold,
            limit=req.limit,
            collection_name=req.collection_name,
        )
    except ServiceError as exc:
        raise _to_http(exc)


@router.get("/state")
def get_state():
    return service.get_run_state()


@router.get("/pairs")
def list_pairs(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
):
    try:
        return service.list_pairs(offset=offset, limit=limit)
    except ServiceError as exc:
        raise _to_http(exc)


@router.get("/pairs/{pair_id}")
def get_pair(pair_id: int):
    try:
        return service.get_pair(pair_id)
    except ServiceError as exc:
        raise _to_http(exc)


@router.post("/pairs/{pair_id}/decision")
def decide_pair(pair_id: int, req: PairDecisionRequest):
    try:
        return service.review_pair(
            pair_id,
            decision=req.decision,
            canonical_id=req.canonical_id,
            merged_properties=req.merged_properties,
        )
    except ServiceError as exc:
        raise _to_http(exc)


@router.post("/apply")
def apply_and_rewrite(req: ApplyRequest):
    try:
        return service.apply_and_rewrite(output_dir=req.output_dir)
    except ServiceError as exc:
        raise _to_http(exc)


@router.post("/reset")
def reset(req: ResetRequest):
    try:
        return service.reset(drop_collection=req.drop_collection)
    except ServiceError as exc:
        raise _to_http(exc)
