from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Role = Literal["admin", "analyst", "reviewer", "viewer"]
Strategy = Literal["single_view", "tta4"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginIn(Strict):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserIn(LoginIn):
    password: str = Field(min_length=12, max_length=200)


class ProjectIn(Strict):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)


class ProjectUpdate(ProjectIn):
    archived: bool = False


class MemberIn(Strict):
    username: str = Field(min_length=1, max_length=80)
    role: Role


class TaskIn(Strict):
    image_id: str
    mode: Literal["historical_replay", "live_inference"] = "historical_replay"
    model_version: Literal["long_bce_lovasz"] = "long_bce_lovasz"
    strategy: Strategy = "tta4"


class ImportMetadata(Strict):
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mask_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    model_version: str = Field(min_length=1, max_length=120)
    strategy: Strategy
    preprocess_version: str = Field(min_length=1, max_length=120)
    threshold: float = 0
    source: str = Field(min_length=1, max_length=500)


class Annotation(Strict):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[tuple[float, float]] = Field(min_length=4, max_length=2000)
    note: str = Field(default="", max_length=1000)


class ReviewIn(Strict):
    base_revision: int = Field(ge=0)
    decision: Literal["confirmed", "returned", "needs_investigation"]
    note: str = Field(min_length=1, max_length=5000)
    annotations: list[Annotation] = Field(default_factory=list, max_length=100)


class ReportIn(Strict):
    prediction_id: str
    review_revision: int = Field(ge=0)


class UserOut(BaseModel):
    id: str
    username: str
    is_admin: bool


class LoginOut(BaseModel):
    user: UserOut
    csrf_token: str


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    archived: bool
    is_demo: bool
    role: Role
    image_count: int
    queued_count: int
    pending_review_count: int
    created_at: float


class CaptureLocation(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    crs: Literal['EPSG:4326'] = 'EPSG:4326'
    kind: Literal['camera_position'] = 'camera_position'
    source: str


class ImageOut(BaseModel):
    id: str
    project_id: str
    name: str
    sample_id: str | None
    split: str
    input_sha256: str
    width: int
    height: int
    display_asset_id: str
    thumbnail_asset_id: str
    label_asset_id: str | None
    coordinate_mode: str
    acquired_at: str | None
    location: CaptureLocation | None = None
    native_size: tuple[int, int] | None = None
    available_strategies: list[str]
    created_at: float


class TaskOut(BaseModel):
    id: str
    project_id: str
    image_id: str
    status: str
    config: dict
    logs: list[dict]
    error: dict | None
    attempt: int
    parent_id: str | None
    prediction_id: str | None
    created_at: float
    finished_at: float | None


class ReviewOut(BaseModel):
    id: str
    revision: int
    decision: str
    note: str
    annotations: list[Annotation]
    created_at: float
    author: str


class MetricsOut(BaseModel):
    pred_pixels: int
    valid_pixels: int
    coverage_percent: float
    scene_threshold_percent: float
    scene_screen_positive: bool
    validity_source: Literal["label_non_255", "full_image"]
    coverage_definition: str
    area_m2: None


class EvaluationOut(BaseModel):
    tp: int
    fp: int
    fn: int
    gt_pixels: int
    iou: float | None
    precision: float | None
    recall: float | None
    gt_coverage_percent: float
    coverage_error_pp: float
    null_reason: str


class PredictionContract(BaseModel):
    prediction_id: str
    image_id: str
    source_mode: Literal["historical_replay", "manual_import", "live_inference"]
    model_version: str
    strategy: Strategy
    threshold: float
    preprocess_version: str
    width: int
    height: int
    coordinate_mode: Literal["pixel"]
    pixel_origin: Literal["top_left"]
    pixel_center: tuple[float, float]
    mask_asset_id: str
    input_sha256: str
    mask_sha256: str
    source_mask_sha256: str
    validity_source: str
    created_at: str
    split: str
    sample_id: str | None
    model_verified: bool
    delta_sha256: str | None
    runtime: dict
    external_source: str | None
    cache_reused: bool


class PredictionOut(BaseModel):
    id: str
    task_id: str
    image_id: str
    project_id: str
    contract: PredictionContract
    metrics: MetricsOut
    evaluation: EvaluationOut | None
    mask_asset_id: str
    overlay_asset_id: str
    layer_asset_id: str
    difference_asset_id: str | None
    gt_layer_asset_id: str | None
    review_revision: int
    reviews: list[ReviewOut]
    created_at: float


class ReportOut(BaseModel):
    id: str
    prediction_id: str
    project_id: str
    status: str
    snapshot: dict
    files: dict[str, str]
    error: str | None
    created_at: float
