import { useEffect, useRef, useState } from "react";

import "./App.css";

const configuredApiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const apiBase = configuredApiBase.replace(/\/$/, "").endsWith("/api/v1")
  ? configuredApiBase.replace(/\/$/, "")
  : `${configuredApiBase.replace(/\/$/, "")}/api/v1`;
const types = ["wall", "window", "balcony", "pillar", "parapet", "gate", "roof_edge"] as const;
type RegionType = (typeof types)[number];
const typeLabels: Record<RegionType, string> = { wall: "Wall", window: "Window", balcony: "Balcony", pillar: "Pillar / Column", parapet: "Parapet Wall", gate: "Gate Area", roof_edge: "Roof Edge" };
type Region = { id: string; region_type: RegionType; polygon: number[][]; area_pixels: number; review_status: string; geometry_metadata: Record<string, unknown> };
type RegionSet = { id: string; image_id: string; status: string; regions: Region[]; revision_number: number };
type Material = { id: string; name: string; category: string; versions: MaterialVersion[] };
type MaterialVersion = { id: string; unit: string; coverage_per_unit: string | null; pack_size: string | null; material_rate: string; labor_rate: string; wastage_percentage: string; specification: { compatible_surface_types?: string[]; swatch?: string } };
type Estimate = { id: string; currency?: string; assumptions?: Record<string, unknown>; material_total: string; labor_total: string; grand_total: string; lines: EstimateLine[] };
type EstimateLine = { id: string; region_id: string; category: string; description: string; quantity: string; unit: string; material_cost: string; labor_cost: string; rate_snapshot: { material_rate: string; labor_rate: string; wastage_percentage?: string; packs?: number | null } };
type RenderResult = { id: string; status: string; provider: string; provider_metadata: Record<string, unknown>; output_asset_id: string | null };
type ImageState = { image_id: string; project_id?: string; width: number; height: number };

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = options?.body instanceof FormData ? { ...(options.headers ?? {}) } : { "Content-Type": "application/json", ...(options?.headers ?? {}) };
  const response = await fetch(`${apiBase}${path}`, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error?.message ?? "Request failed");
  return body as T;
}

export function App() {
  const [step, setStep] = useState(0);
  const [projectName, setProjectName] = useState("My exterior renovation");
  const [projectId, setProjectId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [image, setImage] = useState<ImageState | null>(null);
  const [regions, setRegions] = useState<RegionSet | null>(null);
  const [designId, setDesignId] = useState("");
  const [materials, setMaterials] = useState<Material[]>([]);
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [areas, setAreas] = useState<Record<string, string>>({});
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [renderResult, setRenderResult] = useState<RenderResult | null>(null);
  const [reportId, setReportId] = useState("");
  const [reportError, setReportError] = useState("");
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [draftPoints, setDraftPoints] = useState<number[][]>([]);
  const [regionType, setRegionType] = useState<RegionType>("wall");
  const [drawing, setDrawing] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const approvalInFlight = useRef(false);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function chooseFile(next: File | undefined) {
    if (!next) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(next.type)) return setMessage("Choose a JPEG, PNG, or WEBP image.");
    if (next.size > 10 * 1024 * 1024) return setMessage("Images must be smaller than 10 MB.");
    setFile(next); setPreview(URL.createObjectURL(next)); setMessage("");
  }

  async function startUpload() {
    if (!file) return setMessage("Choose an exterior image first.");
    setBusy(true); setMessage("");
    try {
      const project = projectId ? { id: projectId } : await api<{ id: string }>("/projects", { method: "POST", body: JSON.stringify({ name: projectName }) });
      setProjectId(project.id);
      const form = new FormData(); form.append("file", file);
      const uploaded = await api<ImageState>(`/projects/${project.id}/images`, { method: "POST", body: form });
      setImage(uploaded); setStep(1);
    } catch (error) { console.error(error); setMessage("Unable to upload the image. Please try again."); }
    finally { setBusy(false); }
  }

  async function continueToRegions() {
    if (!image) return setMessage("Upload an image before continuing.");
    setBusy(true); setMessage("");
    try { setRegions(await api<RegionSet>(`/images/${image.image_id}/analysis`, { method: "POST" })); setStep(2); }
    catch (error) { console.error(error); setMessage("Unable to load regions. Please try again."); }
    finally { setBusy(false); }
  }

  function startNewRegion() { setSelectedRegion(null); setDraftPoints([]); setDrawing(false); setMessage(""); }
  function startPolygon() { if (regions?.status !== "approved") { setSelectedRegion(null); setDraftPoints([]); setDrawing(true); setMessage(""); } }

  function addCanvasPoint(event: React.MouseEvent<SVGSVGElement>) {
    if (!drawing || !image) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(image.width, ((event.clientX - rect.left) / rect.width) * image.width));
    const y = Math.max(0, Math.min(image.height, ((event.clientY - rect.top) / rect.height) * image.height));
    setDraftPoints((points) => [...points, [x, y]]);
  }

  async function savePolygon() {
    if (!regions || draftPoints.length < 3) return setMessage("Add at least three points before saving the region.");
    setBusy(true);
    try {
      const created = await api<Region>(`/region-sets/${regions.id}/regions`, { method: "POST", body: JSON.stringify({ region_type: regionType, polygon: draftPoints }) });
      setRegions({ ...regions, regions: [...regions.regions, created] }); setSelectedRegion(created.id); setDraftPoints([]); setDrawing(false); setMessage("");
    } catch (error) { console.error(error); setMessage("Unable to save region. Please try again."); }
    finally { setBusy(false); }
  }

  async function saveSelectedType() {
    if (!selectedRegion || !regions || regions.status === "approved") return;
    setBusy(true);
    try {
      const updated = await api<Region>(`/regions/${selectedRegion}`, { method: "PATCH", body: JSON.stringify({ region_type: regionType }) });
      setRegions({ ...regions, regions: regions.regions.map((region) => region.id === updated.id ? updated : region) }); setMessage("");
    } catch (error) { console.error(error); setMessage("Unable to update region. Please try again."); }
    finally { setBusy(false); }
  }

  async function deleteSelectedRegion() {
    if (!selectedRegion || !regions || regions.status === "approved") return;
    setBusy(true);
    try {
      await api<{ deleted: boolean }>(`/regions/${selectedRegion}`, { method: "DELETE" });
      setRegions({ ...regions, regions: regions.regions.filter((region) => region.id !== selectedRegion) }); setSelectedRegion(null); setMessage("");
    } catch (error) { console.error(error); setMessage("Unable to delete region. Please try again."); }
    finally { setBusy(false); }
  }

  async function approveRegions() {
    if (!regions || regions.regions.length === 0) return setMessage("Create at least one region before continuing.");
    if (approvalInFlight.current) return;
    approvalInFlight.current = true;
    setBusy(true);
    try {
      const result = await api<{ region_set: RegionSet; design_revision_id: string }>(`/region-sets/${regions.id}/approve`, { method: "POST" });
      setRegions(result.region_set); setDesignId(result.design_revision_id); setStep(3); setMessage("");
    } catch (error) { console.error(error); setMessage("Unable to approve regions. Please try again."); }
    finally { approvalInFlight.current = false; setBusy(false); }
  }

  async function loadMaterials() {
    setBusy(true);
    try { setMaterials(await api<Material[]>("/materials")); setStep(4); setMessage(""); }
    catch (error) { console.error(error); setMessage("Unable to load materials. Please try again."); }
    finally { setBusy(false); }
  }

  async function assign(regionId: string, versionId: string) {
    if (!designId) return setMessage("Approve regions before assigning materials.");
    try {
      await api(`/design-revisions/${designId}/assignments`, { method: "POST", body: JSON.stringify({ region_id: regionId, material_version_id: versionId }) });
      setAssignments((current) => ({ ...current, [regionId]: versionId })); setMessage("");
    } catch (error) { console.error(error); setMessage("Unable to assign material. Please try again."); }
  }

  const assigned = Boolean(regions?.regions.length && regions.regions.every((region) => assignments[region.id]));
  const measurementsReady = assigned && Boolean(regions?.regions.every((region) => Number(areas[region.id]) > 0));

  async function renderPreview() {
    if (!designId) return setMessage("Approve regions before generating a preview.");
    setBusy(true);
    try { setRenderResult(await api<RenderResult>(`/design-revisions/${designId}/render`, { method: "POST" })); setMessage(""); }
    catch (error) { console.error(error); setRenderResult(null); setMessage("Preview unavailable. The original image remains available as a fallback."); }
    finally { setBusy(false); }
  }

  async function calculateEstimate() {
    if (!designId || !regions || !measurementsReady) return setMessage("Assign every region and enter an area before calculating.");
    setBusy(true);
    try {
      const measurement = await api<{ id: string }>(`/design-revisions/${designId}/measurements`, { method: "POST", body: JSON.stringify({ entries: regions.regions.map((region) => ({ region_id: region.id, manual_area_sqft: areas[region.id] })) }) });
      setEstimate(await api<Estimate>(`/design-revisions/${designId}/estimates`, { method: "POST", body: JSON.stringify({ measurement_revision_id: measurement.id }) })); setMessage("");
    } catch (error) { console.error(error); setMessage("Unable to calculate the estimate. Please check the measurements."); }
    finally { setBusy(false); }
  }

  async function generateReport() {
    if (!estimate) return setMessage("Calculate an estimate before generating the report.");
    setBusy(true);
    try { const result = await api<{ report_asset_id: string }>(`/estimates/${estimate.id}/report`, { method: "POST" }); setReportId(result.report_asset_id); setReportError(""); setStep(7); }
    catch (error) { console.error(error); setReportError("PDF generation was unavailable. The estimate data remains available below."); setStep(7); }
    finally { setBusy(false); }
  }

  async function changeRate(line: EstimateLine, field: "material_rate" | "labor_rate", value: string) {
    if (!estimate) return;
    const rates = estimate.lines.map((item) => ({ line_id: item.id, material_rate: item.id === line.id && field === "material_rate" ? value : item.rate_snapshot.material_rate, labor_rate: item.id === line.id && field === "labor_rate" ? value : item.rate_snapshot.labor_rate }));
    try { setEstimate(await api<Estimate>(`/estimates/${estimate.id}/rates`, { method: "PATCH", body: JSON.stringify(rates) })); }
    catch (error) { console.error(error); setMessage("Unable to update rates. Please try again."); }
  }

  function startNewProject() {
    setStep(0); setProjectId(""); setFile(null); setPreview(null); setImage(null); setRegions(null); setDesignId(""); setMaterials([]); setAssignments({}); setAreas({}); setEstimate(null); setRenderResult(null); setReportId(""); setReportError(""); setSelectedRegion(null); setDraftPoints([]); setDrawing(false); setMessage("");
  }

  const previewUrl = renderResult?.output_asset_id ? `${apiBase}/assets/${renderResult.output_asset_id}` : preview;
  const stepNames = ["Upload", "Validation", "Regions", "Review", "Materials", "Preview", "Estimate", "Report"];
  const nav = (back: (() => void) | null, next: (() => void) | null, nextLabel: string, disabled = false) => <div className="workflow-nav">{back ? <button onClick={back}>← Back</button> : <span />}{next ? <button className="primary" onClick={next} disabled={disabled}>{nextLabel} →</button> : <span />}</div>;

  return <main className="workflow-shell">
    <header className="workflow-header"><div><p className="eyebrow">EXTERIOR RENOVATION / PROTOTYPE</p><h1>House renovation studio</h1></div><div className="stepper">{stepNames.map((name, index) => <button className={index === step ? "active" : index < step ? "done" : ""} key={name} onClick={() => index < step && setStep(index)}>{index + 1}. {name}</button>)}</div></header>
    {message && <div className="notice" role="status">{message}</div>}
    {step === 0 && <section className="card intro-card"><p className="eyebrow">01 / START A PROJECT</p><h2>Upload the house you want to rethink.</h2><label>Project name<input value={projectName} onChange={(event) => setProjectName(event.target.value)} /></label><button className="dropzone" onClick={() => inputRef.current?.click()}><b>↑</b><strong>{file?.name ?? "Choose an exterior image"}</strong><span>JPEG, PNG, or WEBP · up to 10 MB</span></button><input ref={inputRef} className="hidden" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseFile(event.target.files?.[0])} /><button className="primary" disabled={!file || busy} onClick={startUpload}>{busy ? "Uploading…" : "Upload and validate"}</button></section>}
    {step === 1 && image && <section className="card"><p className="eyebrow">02 / VALIDATION</p><h2>Image ready for review</h2><img className="hero-image" src={preview ?? ""} alt="Uploaded house" /><p>{image.width} × {image.height}px · original preserved · canonical RGB processing copy created</p>{nav(() => setStep(0), continueToRegions, busy ? "Loading regions…" : "Continue to Regions", busy)}</section>}
    {step === 2 && regions && image && <section className="card wide-card"><p className="eyebrow">03 / REGION REVIEW</p><h2>Trace and refine the building.</h2><div className="editor-layout"><div><div className="image-editor" style={{ transform: `scale(${zoom})` }}><img src={preview ?? ""} alt="House with editable regions" /><svg viewBox={`0 0 ${image.width} ${image.height}`} onClick={addCanvasPoint}>{regions.regions.map((region) => <polygon key={region.id} points={region.polygon.map((point) => point.join(",")).join(" ")} className={selectedRegion === region.id ? "selected-region" : "region-line"} onClick={(event) => { event.stopPropagation(); setSelectedRegion(region.id); setRegionType(region.region_type); setDrawing(false); }} />)}{draftPoints.length > 0 && <polyline points={draftPoints.map((point) => point.join(",")).join(" ")} className="draft-line" />}</svg></div><p className="muted">{drawing ? `Click points on the image (${draftPoints.length} selected).` : "Choose New region, then Add polygon to start drawing."}</p></div><aside className="editor-tools"><label>Component type<select value={regionType} onChange={(event) => setRegionType(event.target.value as RegionType)}>{types.map((type) => <option value={type} key={type}>{typeLabels[type]}</option>)}</select></label><div className="region-actions"><button onClick={startNewRegion} disabled={busy || regions.status === "approved"}>New region</button><button onClick={startPolygon} disabled={busy || regions.status === "approved"}>Add polygon</button><button onClick={savePolygon} disabled={busy || regions.status === "approved" || !drawing || draftPoints.length < 3}>Save region</button><button onClick={saveSelectedType} disabled={busy || !selectedRegion || regions.status === "approved"}>Save selected type</button><button onClick={deleteSelectedRegion} disabled={busy || !selectedRegion || regions.status === "approved"}>Delete selected</button></div><label>Zoom<input type="range" min="0.7" max="2" step="0.1" value={zoom} onChange={(event) => setZoom(Number(event.target.value))} /></label><div className="region-list"><strong>{regions.regions.length} region{regions.regions.length === 1 ? "" : "s"}</strong>{regions.regions.length === 0 && <span className="muted">No proposals yet. Create one manually.</span>}{regions.regions.map((region) => <button className="region-row" key={region.id} onClick={() => { setSelectedRegion(region.id); setRegionType(region.region_type); setDrawing(false); }}><span>{typeLabels[region.region_type]}</span><small>{region.review_status}</small></button>)}</div><button className="primary" onClick={approveRegions} disabled={busy || regions.regions.length === 0}>{busy ? "Saving…" : "Approve Regions / Continue"}</button></aside></div>{nav(() => setStep(1), approveRegions, "Approve Regions / Continue", busy || regions.regions.length === 0)}</section>}
    {step === 3 && <section className="card"><p className="eyebrow">04 / APPROVED REGIONS</p><h2>Regions are ready for materials.</h2><p>{regions?.regions.length ?? 0} approved regions can now receive different finishes.</p>{nav(() => setStep(2), loadMaterials, busy ? "Loading materials…" : "Continue to Materials", busy)}</section>}
    {step === 4 && regions && <section className="card wide-card"><p className="eyebrow">05 / MATERIALS</p><h2>Assign a finish to every approved region.</h2><div className="assignment-list">{regions.regions.map((region) => <div className="assignment" key={region.id}><div><b>{typeLabels[region.region_type]}</b><span>{region.area_pixels} px²</span></div><select value={assignments[region.id] ?? ""} onChange={(event) => assign(region.id, event.target.value)}><option value="">Choose compatible material</option>{materials.flatMap((material) => material.versions.map((version) => ({ material, version }))).filter(({ version }) => (version.specification.compatible_surface_types ?? []).includes(region.region_type)).map(({ material, version }) => <option value={version.id} key={version.id}>{material.name}</option>)}</select></div>)}</div><p className="muted">Assign one compatible material to each region to continue.</p>{nav(() => setStep(3), () => setStep(5), "Continue to Preview", !assigned)}</section>}
    {step === 5 && regions && <section className="card wide-card"><p className="eyebrow">06 / RENOVATION PREVIEW</p><h2>Preview the selected finishes.</h2><div className="preview-grid"><div><img className="hero-image" src={previewUrl ?? ""} alt={renderResult ? "Renovation preview" : "Original house fallback"} /></div><div><p className="status">{renderResult ? `Preview status: ${renderResult.status}` : "Preview unavailable: showing the original image."}</p><button className="primary" onClick={renderPreview} disabled={busy}>{busy ? "Generating…" : "Generate Renovation Preview"}</button><p className="muted">AI rendering is optional. The deterministic estimate does not depend on this preview.</p><div className="measurement-list">{regions.regions.map((region) => <label key={region.id}>{typeLabels[region.region_type]} area (sq ft)<input type="number" min="0" value={areas[region.id] ?? ""} onChange={(event) => setAreas((current) => ({ ...current, [region.id]: event.target.value }))} placeholder="Required" /></label>)}</div></div></div>{nav(() => setStep(4), () => setStep(6), "Continue to Estimate", !measurementsReady)}</section>}
    {step === 6 && <section className="card wide-card"><p className="eyebrow">07 / ESTIMATE</p><h2>{estimate ? "Advisory renovation estimate." : "Calculate the renovation estimate."}</h2>{!estimate && <><p>Review your measurements, then calculate deterministic quantities and costs.</p><button className="primary" onClick={calculateEstimate} disabled={busy || !measurementsReady}>{busy ? "Calculating…" : "Calculate Estimate"}</button></>}{estimate && <><table><thead><tr><th>Component / material</th><th>Quantity</th><th>Wastage</th><th>Material cost</th><th>Labor cost</th></tr></thead><tbody>{estimate.lines.map((line) => <tr key={line.id}><td>{line.description}</td><td>{line.quantity} {line.unit}</td><td>{line.rate_snapshot.wastage_percentage ?? "-"}%</td><td><input className="rate" value={line.rate_snapshot.material_rate} onChange={(event) => changeRate(line, "material_rate", event.target.value)} /> · {line.material_cost}</td><td><input className="rate" value={line.rate_snapshot.labor_rate} onChange={(event) => changeRate(line, "labor_rate", event.target.value)} /> · {line.labor_cost}</td></tr>)}</tbody></table><div className="totals"><b>Materials {estimate.currency ?? "USD"} {estimate.material_total}</b><b>Labor {estimate.currency ?? "USD"} {estimate.labor_total}</b><strong>Grand total {estimate.currency ?? "USD"} {estimate.grand_total}</strong></div><button className="primary" onClick={generateReport} disabled={busy}>{busy ? "Generating…" : "Continue to Report / Generate PDF"}</button></>}{nav(() => setStep(5), null, "", !estimate)}</section>}
    {step === 7 && estimate && <section className="card wide-card"><p className="eyebrow">08 / REPORT</p><h2>Renovation report</h2>{reportError && <div className="notice">{reportError}</div>}<div className="report-grid"><img className="hero-image" src={preview ?? ""} alt="Original house" /><div><p>Original image, region assignments, measurements, quantities, rates, costs, assumptions, and advisory totals are included.</p><p className="muted">This estimate is approximate and non-binding. Measurements are not survey-grade.</p>{reportId && <a className="primary link-button" href={`${apiBase}/assets/${reportId}`} target="_blank" rel="noreferrer">Download Report</a>}</div></div>{nav(() => setStep(6), startNewProject, "Start New Project")}</section>}
  </main>;
}
