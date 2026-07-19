import type { FusionOpsLens } from './FusionRail'

/** Search params for `/dashboard/fusion` (Mission Control). */
export type FusionMissionSearch = {
  lens: FusionOpsLens | undefined
}

export function fusionMissionSearch(lens?: FusionOpsLens): FusionMissionSearch {
  if (!lens || lens === 'canvas') return { lens: undefined }
  return { lens }
}

/** Default search when navigating to fusion child routes (inherits parent search). */
export function fusionChildSearch(lens?: FusionOpsLens): FusionMissionSearch {
  return fusionMissionSearch(lens)
}

export function fusionLensFromSearch(lens?: FusionOpsLens): FusionOpsLens {
  if (lens === 'queue' || lens === 'collect' || lens === 'brief') return lens
  return 'canvas'
}

export type FusionOpsLensRoute =
  | { to: '/dashboard/fusion'; search: FusionMissionSearch }
  | {
      to: '/dashboard/fusion/investigation/$caseRef'
      params: { caseRef: string }
      search: FusionMissionSearch
    }

/** Declarative target for Ops Deck Canvas / Queue / Collect / Brief links. */
export function fusionOpsLensRoute(
  lens: FusionOpsLens,
  caseRef?: string | null
): FusionOpsLensRoute {
  const search = fusionMissionSearch(lens === 'canvas' ? undefined : lens)

  if (caseRef && (lens === 'canvas' || lens === 'queue' || lens === 'collect' || lens === 'brief')) {
    return {
      to: '/dashboard/fusion/investigation/$caseRef',
      params: { caseRef },
      search,
    }
  }

  return {
    to: '/dashboard/fusion',
    search: lens === 'canvas' ? fusionMissionSearch() : search,
  }
}
