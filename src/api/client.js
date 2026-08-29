/**
 * API client for the Kopargaon CRPP backend.
 *
 * Everything the UI knows about the server lives here. Two things in this file
 * are load-bearing beyond "call fetch":
 *
 * 1. Errors carry their HTTP status. A 404 from `/api/triage/today` means "no
 *    plan has been issued for today yet" -- a normal state the dashboard should
 *    render as an invitation to run triage, not as a failure. A 500 or a
 *    dropped connection is a real error. A page cannot tell those apart from
 *    an error message alone, so `ApiError` exposes `status`.
 * 2. Image bytes are not JSON. `mediaURL()` builds a plain absolute URL for
 *    `<img src>`; it deliberately does not go through `fetchAPI`, which parses
 *    every response as JSON.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export { API_BASE_URL };

/**
 * An HTTP error that still knows what the server said.
 *
 * `message` is unchanged from the previous behaviour (`detail` when FastAPI
 * sent one, otherwise `HTTP <status>: <text>`), so existing catch blocks that
 * only read `.message` keep working. `status` is 0 when the request never
 * reached the server -- a distinction the dashboard needs, because "the backend
 * is not running" and "the backend said no" call for different words on screen.
 */
export class ApiError extends Error {
  constructor(message, { status = 0, detail = null, payload = null, endpoint = '' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.payload = payload;
    this.endpoint = endpoint;
  }

  get isNotFound() {
    return this.status === 404;
  }

  get isOffline() {
    return this.status === 0;
  }
}

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  const config = {
    headers: {
      'Accept': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  // Add auth token if available
  const token = localStorage.getItem('token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    config.headers['Content-Type'] = 'application/json';
    if (options.body && typeof options.body === 'object') {
      config.body = JSON.stringify(options.body);
    }
  }

  let response;
  try {
    response = await fetch(url, config);
  } catch (error) {
    // fetch only rejects when the request never completed: server down, DNS,
    // CORS preflight refused. Surfaced as status 0 so callers can say so.
    const err = new ApiError(
      `Cannot reach the backend at ${API_BASE_URL}. Is it running?`,
      { status: 0, detail: error.message, endpoint },
    );
    console.error('API Error:', err);
    throw err;
  }

  // A 204, or an error page from a proxy, is not JSON. Parsing must not be the
  // thing that decides whether the call succeeded.
  let data = null;
  const raw = await response.text();
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const detail = data && typeof data.detail !== 'undefined' ? data.detail : null;
    const message = typeof detail === 'string' && detail
      ? detail
      : `HTTP ${response.status}: ${response.statusText}`;
    const err = new ApiError(message, {
      status: response.status, detail, payload: data, endpoint,
    });
    console.error('API Error:', err);
    throw err;
  }

  return data;
}

/**
 * Run a call that is allowed to have no answer yet, and say which it was.
 *
 * Resolves to `{ found: true, data }` or `{ found: false, reason }`. Use it for
 * the handful of endpoints where 404 is a state rather than a fault -- today's
 * manifest before triage has run, an explanation for a ticket that was never
 * scored. Any other failure still throws.
 */
export async function tolerate404(call) {
  try {
    return { found: true, data: await call(), reason: null };
  } catch (error) {
    if (error instanceof ApiError && error.isNotFound) {
      return { found: false, data: null, reason: error.message };
    }
    throw error;
  }
}

/** Drop null/undefined/'' before building a query string, so `?ward_id=` never
 *  reaches the server as an empty filter that matches nothing. */
function qs(params = {}) {
  const clean = {};
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== '') clean[k] = v;
  }
  const s = new URLSearchParams(clean).toString();
  return s ? `?${s}` : '';
}

/**
 * Ticket API endpoints
 */
export const ticketsAPI = {
  /**
   * Submit a new grievance ticket with photo
   */
  submit: async (formData) => {
    return fetchAPI('/api/tickets/submit', {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * Get list of tickets
   */
  list: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return fetchAPI(`/api/tickets/list?${queryString}`);
  },

  /**
   * Get single ticket details
   */
  get: async (id) => {
    return fetchAPI(`/api/tickets/${id}`);
  },

  /** Tickets ready to be scored, with the reason any of them is not. */
  queue: async (wardId = null) => {
    return fetchAPI(`/api/tickets/queue${qs({ ward_id: wardId })}`);
  },

  /** Ward master data plus a coverage report naming what is still unentered. */
  wards: async (includeInactive = false) => {
    return fetchAPI(`/api/tickets/wards${qs({ include_inactive: includeInactive })}`);
  },

  /** Create or update one ward. Every field is optional: partial truth beats
   *  invention, and the response reports what is still missing. */
  saveWard: async (wardId, payload) => {
    return fetchAPI(`/api/tickets/wards/${wardId}`, { method: 'PUT', body: payload });
  },

  /**
   * Replace estimated cost lines with figures an officer measured.
   * Accepts any of: runtime_vehicle_cost, runtime_labour_cost,
   * runtime_material_cost, other_cost, crew_hours,
   * equipment_hours ({ machineCode: hours }), note.
   * This is what moves a ticket from COST_INCOMPLETE to COST_COMPLETE.
   */
  updateCost: async (id, payload) => {
    return fetchAPI(`/api/tickets/${id}/cost`, { method: 'POST', body: payload });
  },

  /** Escalating conditions, only ever set by a human who checked:
   *  blocks_major_road, access_isolated, critical_facility_isolated, note. */
  confirmConditions: async (id, payload) => {
    return fetchAPI(`/api/tickets/${id}/conditions`, { method: 'POST', body: payload });
  },

  /** Move a ticket's status. Illegal transitions come back as a 400 naming the
   *  moves that were allowed, so the UI can show them rather than guess. */
  setStatus: async (id, status, note = null) => {
    return fetchAPI(`/api/tickets/${id}/status`, {
      method: 'POST', body: { status, ...(note ? { note } : {}) },
    });
  },

  /** Undo a duplicate merge an officer disagrees with. */
  unmerge: async (id) => {
    return fetchAPI(`/api/tickets/${id}/unmerge`, { method: 'POST' });
  },

  /** Re-derive one ticket's criteria after its inputs changed. */
  rescore: async (id) => {
    return fetchAPI(`/api/tickets/${id}/rescore`, { method: 'POST' });
  },
};

/**
 * Triage API endpoints
 */
export const triageAPI = {
  /**
   * Run triage with budget and workforce constraints
   */
  run: async (dailyBudget, dailyWorkforce, wardId = null) => {
    const body = {
      daily_budget: dailyBudget,
      daily_workforce: dailyWorkforce,
    };
    if (wardId) body.ward_id = wardId;

    return fetchAPI('/api/triage/run', {
      method: 'POST',
      body,
    });
  },

  /**
   * Get today's dispatch manifest
   */
  getToday: async () => {
    return fetchAPI('/api/triage/today');
  },

  /**
   * Get dispatch manifest for specific date
   */
  getManifest: async (date) => {
    return fetchAPI(`/api/triage/manifest/${date}`);
  },

  /**
   * Get tickets sorted by priority
   */
  getPriorities: async (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return fetchAPI(`/api/triage/priorities?${queryString}`);
  },

  /**
   * Compute a plan and write nothing.
   *
   * The point of this is to let an officer try "what if the budget were
   * 40,000?" without leaving a manifest behind that claims to be the day's
   * dispatch order. The response is shaped exactly like a real run and carries
   * `dry_run: true` and `persisted: false`.
   */
  dryRun: async (dailyBudget, dailyWorkforce, options = {}) => {
    return fetchAPI('/api/triage/run', {
      method: 'POST',
      body: {
        daily_budget: dailyBudget,
        daily_workforce: dailyWorkforce,
        dry_run: true,
        ...options,
      },
    });
  },

  /**
   * Full-control run. Omit daily_budget/daily_workforce to use the capacity a
   * named officer stored through `setCapacity`, which is the attributable path;
   * the manifest records which of the two it used.
   * Accepts: daily_budget, daily_workforce, ward_id, dispatch_date, dry_run,
   * solver ('dp' | 'cpsat').
   */
  runWith: async (body = {}) => {
    return fetchAPI('/api/triage/run', { method: 'POST', body });
  },

  /** Past manifests, newest first. */
  getManifests: async (params = {}) => {
    return fetchAPI(`/api/triage/manifests${qs(params)}`);
  },

  /** One manifest by its own id, rather than by date. */
  getManifestById: async (manifestId) => {
    return fetchAPI(`/api/triage/manifest-by-id/${manifestId}`);
  },

  /**
   * Today's budget and crew-hours, and whether a human signed for them.
   * `capacity_verified` false means the figures are a configured default that
   * the council never confirmed -- the UI should say so rather than present a
   * guess as a fact.
   */
  getCapacity: async (params = {}) => {
    return fetchAPI(`/api/triage/capacity${qs(params)}`);
  },

  /** Record real constraints. `verified_by` is the officer's name and is what
   *  turns `capacity_verified` true in every manifest built on top of it. */
  setCapacity: async (payload) => {
    return fetchAPI('/api/triage/capacity', { method: 'PUT', body: payload });
  },
};

/**
 * Why a ticket scored what it scored.
 *
 * The attribution here is exact rather than illustrative: the per-criterion
 * contributions sum to the closeness coefficient, so a figure on screen can be
 * defended line by line in a council meeting.
 */
export const explainAPI = {
  /** One ticket's score, its drivers, and the sentences that describe them. */
  ticket: async (ticketId, params = {}) => {
    return fetchAPI(`/api/explain/${ticketId}${qs(params)}`);
  },

  /** Plain-language version for the person who filed the report.
   *  `lang` is 'en' or 'mr'; Marathi text is machine-drafted and is stamped
   *  as pending council review, which the UI must display. */
  citizen: async (ticketId, lang = 'en', runId = null) => {
    return fetchAPI(`/api/explain/${ticketId}/citizen${qs({ lang, run_id: runId })}`);
  },

  /** Every score this ticket has ever had, and what changed between them. */
  history: async (ticketId) => {
    return fetchAPI(`/api/explain/${ticketId}/history`);
  },

  /** A whole prioritisation run, reviewable ticket by ticket. */
  run: async (runId, params = {}) => {
    return fetchAPI(`/api/explain/run/${runId}${qs(params)}`);
  },

  /** Run-level SHAP attribution across the scored set. */
  runShap: async (runId) => {
    return fetchAPI(`/api/explain/run/${runId}/shap`);
  },
};

/**
 * Citizen photographs, and the visual evidence behind a duplicate merge.
 *
 * "pHash distance 2 at 12 m, therefore one ticket instead of three" is a claim.
 * Two photographs side by side is the proof, which is the only reason these
 * endpoints exist.
 */
export const mediaAPI = {
  /** Every image on one ticket, each with the hash it produced. An empty list
   *  is a valid answer -- a report from somebody without a camera is still a
   *  report -- so do not treat `count: 0` as an error. */
  forTicket: async (ticketId) => {
    return fetchAPI(`/api/media/ticket/${ticketId}`);
  },

  /**
   * Thumbnails for a whole table in one request.
   *
   * Resolves to `{ tickets: { [ticketId]: [mediaRow, ...] }, count, requested }`.
   * A ticket with no photograph is *absent* from `tickets`, not present with an
   * empty array -- so `index.tickets[id]?.[0]` is the whole lookup, and a miss
   * means "draw the category icon", never "something failed".
   *
   * Pass an array of ids. Omit it to get the most recent images overall.
   */
  index: async (ticketIds = null, limit = 400) => {
    const ids = Array.isArray(ticketIds) ? ticketIds.filter(Boolean).join(',') : ticketIds;
    return fetchAPI(`/api/media/index${qs({ ticket_ids: ids, limit })}`);
  },

  /** Surviving tickets that absorbed at least one other report, ordered by how
   *  many were folded in. */
  clusters: async (limit = 20) => {
    return fetchAPI(`/api/media/clusters${qs({ limit })}`);
  },

  /**
   * One merge with its evidence. Accepts either end of the link: hand it a
   * duplicate's id and it resolves to the surviving parent, so a citizen
   * following up on their own reference number sees the cluster an officer sees
   * rather than a dead end.
   *
   * Each member carries a `match` block -- basis, hash distance, metres apart,
   * text similarity, and the sentence the matcher wrote *at the time*. It is
   * read from storage, never recomputed, because the officer defending last
   * week's merge needs the numbers that were actually used.
   */
  cluster: async (ticketId) => {
    return fetchAPI(`/api/media/cluster/${ticketId}`);
  },
};

/**
 * Absolute URL for an image, for use directly in `<img src>`.
 *
 * Deliberately not routed through `fetchAPI`: that parses every response as
 * JSON, and these are JPEG bytes. Returns null for a missing id so a caller can
 * write `src={mediaURL(m?.id) ?? undefined}` without a guard.
 *
 * Check the media row's `available` flag before rendering. When it is false the
 * file is genuinely not there and this URL will 404; show the row's
 * `unavailable_reason` instead of a broken-image icon.
 */
export function mediaURL(mediaId) {
  return mediaId ? `${API_BASE_URL}/api/media/${mediaId}/file` : null;
}

/**
 * Fuzzy-AHP criteria weights.
 *
 * `derive` runs the Saaty consistency check and refuses to activate weights
 * whose consistency ratio is 0.10 or worse. A rejected set is not a bug to be
 * worked around -- it means the pairwise judgements contradict each other and
 * the panel needs to revisit them, which is what the response explains.
 */
export const weightsAPI = {
  /** The linguistic comparison scale, for building the judgement form. */
  scale: async () => fetchAPI('/api/weights/scale'),

  /** The weights currently in force, with the reasoning behind them. */
  active: async () => fetchAPI('/api/weights/active'),

  /** Every version ever derived. The table is append-only: a weight set that
   *  produced a manifest is never edited or deleted. */
  versions: async (limit = 50) => fetchAPI(`/api/weights/versions${qs({ limit })}`),

  version: async (version) => fetchAPI(`/api/weights/versions/${version}`),

  /** What changed between two versions, criterion by criterion. */
  compare: async (fromVersion, toVersion) => {
    return fetchAPI(`/api/weights/compare${qs({
      from_version: fromVersion, to_version: toVersion,
    })}`);
  },

  /** Check a set of comparisons without storing anything -- the honest way to
   *  show a live consistency ratio while the panel is still arguing. */
  preview: async (comparisons, options = {}) => {
    return fetchAPI('/api/weights/preview', {
      method: 'POST', body: { comparisons, ...options },
    });
  },

  /** Derive and (by default) adopt a new version. Pass `{ activate: false }`
   *  to store it without putting it in force. */
  derive: async (comparisons, options = {}) => {
    return fetchAPI('/api/weights/derive', {
      method: 'POST', body: { comparisons, ...options },
    });
  },

  activate: async (version) => {
    return fetchAPI(`/api/weights/versions/${version}/activate`, { method: 'POST' });
  },
};

/**
 * Health check
 */
export const healthAPI = {
  check: async () => {
    return fetchAPI('/health');
  },

  /** Tunables the UI may display. Never contains secrets. */
  config: async () => {
    return fetchAPI('/api/config');
  },
};

export default {
  tickets: ticketsAPI,
  triage: triageAPI,
  explain: explainAPI,
  media: mediaAPI,
  weights: weightsAPI,
  health: healthAPI,
  mediaURL,
  tolerate404,
  ApiError,
};
