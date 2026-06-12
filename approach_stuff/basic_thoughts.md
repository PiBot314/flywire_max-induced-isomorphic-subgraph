Looking at the flywire connectome datsets, they correspond to:
    Female Adult Fly Brain
    Female Adult Fly Brain and Nerve Cord
    Male Adult Fly Nerve Cord
    Male Adult Fly Right Optic Lobe
    Male Adult Fly CNS

Also small side note, the google sign in page of flywire, when providing permissions doesn't link to any privacy policy or tos of flywire. might want to update that.

Looking at the names, I would estimate that
    - FAFB and BANC would likely share high similarities (one being a subset of the other), I do not know how much similarity between male and female flys but I also estimate , so I will prioritize checking the FAFB and BANC. I'll check to see if Male and Female neuron wise are similar/same.
    - MANC, MAOL and MCNS will be very similar because central nervous system, nerve cord and optic lobe should all be considered.
On checking they are [TODO]

Plan (conceptual)

- Prepare datasets: load the five edge lists, normalize neuron identifiers, and record presence/absence per dataset. [edgelists to presence matrices]
- Build graphs: convert each edge list to an unweighted directed graph representation.
- Filter candidates: compute simple node invariants (in/out degree, degree signatures, local motifs) to prune unlikely matches across datasets.
- Seed-and-extend: find small isomorphic seed subgraphs (pairs/triples) and grow them (greedy method) while making sure that they're isomorphic graphs.
- Maximize N: iterate over dataset triples and use the seed growth plus backtracking to maximize the common induced subgraph size.
- Validate & export: verify exact induced-isomorphism, export the matched neuron triples as CSV, and prepare visualizations and a short biological summary.


//LEGACY FROM A PREVIOUS ATTEMPT
In summary.txt it says that there are a maximum of 5289 shared neurons across all edgelists.
On doing a simple Ctrl+F in my presence matrix and searching for 1,1,1 and found 5289 possibilities!
Then checking for a more specific result (0,0,1,1,1) for a trio and ALL of them mapped to MANC, MAOL and MCNS. So the highest amount of shared neurons in 3 edgelists is the male trio