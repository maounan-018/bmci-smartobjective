// types.js — Constantes et types du domaine (converti depuis types.ts).
//
// En JavaScript, seuls les "enum" ont une existence à l'exécution : `UserRole`
// devient donc un objet constant. Les anciennes interfaces TypeScript sont
// conservées en commentaires JSDoc (@typedef) pour la documentation et
// l'autocomplétion des éditeurs — elles n'ont aucun effet à l'exécution.

export const UserRole = {
  COLLAB: 'COLLAB',
  MANAGER: 'MANAGER',
  HR: 'HR',
};

/**
 * @typedef {Object} User
 * @property {string} id
 * @property {string} name
 * @property {string} email
 * @property {string} role            // une valeur de UserRole
 * @property {string} [team]
 * @property {string} [entity]
 * @property {string} [manager_id]
 */

/**
 * @typedef {Object} SmartAnalysis
 * @property {boolean} S
 * @property {boolean} M
 * @property {boolean} A
 * @property {boolean} R
 * @property {boolean} T
 * @property {boolean} overall
 * @property {number} confidence
 * @property {Array<{letter:string, problem:string, fix:string}>} issues
 * @property {string} rewrite_fr
 * @property {string} rewrite_en
 */

/**
 * @typedef {Object} AlignmentAnalysis
 * @property {number} alignment_score
 * @property {Array<{objective_id:string, score:number, reason:string}>} top_matches
 * @property {string[]} gaps
 */

/**
 * @typedef {Object} Objective
 * @property {string} id
 * @property {string} user_id
 * @property {string} title
 * @property {string} description
 * @property {string} status          // 'draft' | 'analyzed' | 'validated'
 * @property {string} progress        // 'not_started' | 'in_progress' | 'completed' | 'on_hold'
 * @property {SmartAnalysis} [smartAnalysis]
 * @property {AlignmentAnalysis} [alignmentAnalysis]
 * @property {string} createdAt
 */
