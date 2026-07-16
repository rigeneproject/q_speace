# Network Geometry of the Drosophila Brain

**Authors:** Bendegúz Sulyok¹, Sámuel G. Balogh², Gergely Palla³,¹,*

¹ Dept. of Biological Physics, Eötvös Loránd University, H-1117 Budapest, Pázmány P. stny. 1/A, Hungary.
² Faculty of Electrical Engineering, Mathematics and Computer Science, Delft University of Technology, 2600 GA Delft, The Netherlands.
³ Semmelweis University, Faculty of Health and Public Administration, Health Services Management Training Centre, H-1125, Kútvolhyi út 2, Budapest, Hungary.

*gergely.palla@emk.semmelweis.hu

**arXiv:2602.16417v1 [physics.soc-ph] 18 Feb 2026**

---

## Abstract

The recent reconstruction of the Drosophila brain provides a neural network of unprecedented size and level of details. In this work, we study the geometrical properties of this system by applying network embedding techniques to the graph of synaptic connections. Since previous analysis have revealed an inhomogeneous degree distribution, we first employ a hyperbolic embedding approach that maps the neural network onto a point cloud in the two-dimensional hyperbolic space. In general, hyperbolic embedding methods exploit the exponentially growing volume of hyperbolic space with increasing distance from the origin, allowing for an approximately uniform spatial distribution of nodes even in scale-free, small-world networks. By evaluating multiple embedding quality metrics, we find that the network structure is well captured by the resulting two-dimensional hyperbolic embedding, and in fact is more congruent with this representation than with the original neuron coordinates in three-dimensional Euclidean space. In order to examine the network geometry in a broader context, we also apply the well-known Euclidean network embedding approach Node2vec, where the dimension of the embedding space, d can be set arbitrarily. In 3 dimensions, the Euclidean embedding of the network yields lower quality scores compared to the original neuron coordinates. However, as a function of the embedding dimension the scores show an improving tendency, surpassing the level of the 2d hyperbolic embedding roughly at d = 16, and reaching a maximum around d = 64. Since network embeddings can serve as valuable inputs for a variety of downstream machine learning tasks, our results offer new perspectives on the structure and representation of this recently revealed and biologically significant neural network.

---

## Introduction

Over the past two decades, network-based approaches have emerged as a powerful framework for describing and analysing complex systems. By representing interactions among system components as graphs, this perspective has revealed universal organizing principles across domains ranging from technology and society to biology. Among these systems, neural networks, encoding the connections between neurons of living organisms, have always been of central interest, providing information on the structural organization and functional dynamics of the nervous system. 

A widely known example is the neural network of the *Caenorhabditis elegans* worm, consisting of roughly 300-400 neurons (depending on the sex of the animal) with about 5,000-7,000 connections. A considerably larger network was reconstructed for the larva of the Drosophila, spanning between 3,016 neurons via roughly 5 × 10⁵ synapses. However, both of these networks are dwarfed by the recent reconstruction of the brain of adult female *Drosophila melanogaster*, which contains 139,255 neurons linked by 5 × 10⁷ chemical synapses. Given that flies are capable of navigating over distances, show signs of long-term memories, engage in social interactions, and exhibit a wiring diagram between brain regions similar to that of mammals, research on the fly brain offers insights that extend beyond a mere increase in neural network scale.

The fundamental network characteristics of this fascinating system have already been examined, uncovering a scale-free degree distribution and a distinct rich-club organisation, in which highly central neurons (hubs) are densely interconnected. In addition, specific neuronal subsets were identified that may act as signal integrators or broadcasters. In the present study, we augment these results through the use of network embeddings, aimed at arranging the neurons in metric spaces solely based on the structure of the connections. 

In general, network embedding techniques provide an important alternative to traditional network measures for gaining information on various properties of the analysed network. When transforming a network into a point cloud in a metric space, the original graph structure becomes encoded in the relative coordinates of the nodes, as, for example, tightly knit communities in the network are usually mapped onto compact and dense point clusters. The node coordinates also offer utility in several areas, including the prediction of missing links, assisting in navigation over the network, and serving as input for further machine learning tasks such as node classification, community finding, etc. Moreover, as demonstrated in previous works, access to node coordinates can significantly aid in identifying nodes which contribute to shortest paths, especially in partially incomplete networks.

Although embedding nodes into the Euclidean space might seem as an intuitive choice, the hyperbolic approach provides a compelling alternative with distinct advantages. Crucially, while Euclidean algorithms often require high-dimensional embeddings, hyperbolic approaches can achieve good quality embeddings in just two dimensions. This is because the exponential volume growth of hyperbolic spheres provides greater flexibility in node placement compared to the power-law growth of Euclidean spheres.

Nevertheless, most of the hyperbolic embedding methods cannot be scaled up to networks as large as the wiring diagram of the *Drosophila melanogaster* brain because of their substantial computational demands. As a result, a hyperbolic map of this system has remained unavailable so far. To overcome this limitation, we adopt the recently introduced **Cluster-Level Optimised Vertex Embedding (CLOVE)** method, which simultaneously delivers high embedding quality while maintaining exceptional computational efficiency. By avoiding the computational bottlenecks of alternative approaches, CLOVE makes it possible to construct a faithful hyperbolic embedding of the *Drosophila melanogaster* brain connectome. In parallel, we examine Euclidean embeddings produced by the similarly efficient **Node2vec** algorithm.

---

## Results

### Embedding Visualizations

First, we embedded the *Drosophila melanogaster* connectome into the native disk representation of two-dimensional hyperbolic space using CLOVE. To still uncover the role of the dimensionality of the underlying metric space, we also generated comparative Euclidean embeddings using Node2vec in several dimensions ranging from 2 to 512.

In the obtained embeddings:
- The original 3D Euclidean coordinates provide a 2D projection showing the brain's large-scale organization
- The hyperbolic embedding (2D native disk representation) is much more spacious, allowing for display of links without compromising visibility
- High degree nodes (hubs) are placed closer to the centre of the native disk
- Small degree nodes are pushed towards the disk periphery
- Separation between highlighted neuron super classes is preserved by the angular arrangement of nodes
- The 64D Euclidean embedding obtained with Node2vec also shows well-separated classes when projected to 2D using UMAP

### Embedding Quality Measures

Multiple quality metrics were used to evaluate the embeddings:

#### Greedy Routing Based Metrics

**Greedy Routing Success Rate (GR):** Measures the fraction of packets that successfully reach their target using a myopic path-finding strategy.

**Greedy Routing Score (GRS):** Accounts not only for whether a path is successful, but also for its length, weighting successful paths by the ratio between shortest-path length and actual greedy path length.

**Greedy Routing Efficiency (GRE):** Places emphasis on geometric efficiency, rewarding paths that closely approximate the shortest possible routes in the network.

#### Mapping Accuracy (MA)

Defined as the Spearman rank correlation between topological shortest-path distances and geodesic distances in the embedding space:

$$MA = \rho[R[TSP], R[GEOM]]$$

where R denotes the rank operator and ρ the Pearson correlation.

#### Edge Prediction Metrics

**EPAUC:** Area Under the ROC Curve for edge prediction

**EPP:** Edge Prediction Precision (average precision)

**EPR20 and EPR5:** Proportion of positive edges recovered within the top 20% and 5% of ranked evaluation sets

### Low-Dimensional Embedding Quality Results

| Metric | Real 3D | Node2vec 2D | Node2vec 3D | CLOVE (Hyperbolic) |
|--------|---------|------------|------------|-------------------|
| MA | 0.363 | 0.364 | 0.476 | 0.528 |
| GR | 0.075 | 0.030 | 0.061 | 0.553 |
| GRS | 0.048 | 0.023 | 0.047 | 0.390 |
| GRE | 0.050 | 0.026 | 0.046 | 0.160 |
| EPAUC | 0.862 | 0.853 | 0.920 | 0.960 |
| EPP | 0.849 | 0.809 | 0.902 | 0.964 |
| EPR20 | 0.904 | 0.832 | 0.934 | 0.996 |
| EPR5 | 0.968 | 0.898 | 0.959 | 1.000 |

**Key Findings:**

The 2D hyperbolic embedding obtained with CLOVE achieves higher scores than the low-dimensional Euclidean embeddings across all evaluated quality metrics. Moreover, all scores for the 2D hyperbolic embedding consistently surpass those of the real physical 3D arrangement. The difference is particularly large for scores related to greedy navigation (GR, GRS, GRE), showing that the hyperbolic map is substantially more navigable than low-dimensional Euclidean representations.

### High-Dimensional Node2vec Results

Quality scores for Euclidean embeddings improve as a function of dimension, reaching a peak, then decline for very high dimensions:

| Dimension | MA | GR | GRS | GRE | EPAUC | EPP | EPR20 | EPR5 |
|-----------|----|----|-----|-----|-------|-----|-------|------|
| 4D | 0.500 | 0.142 | 0.102 | 0.098 | 0.947 | 0.938 | 0.967 | 0.982 |
| 8D | 0.613 | 0.438 | 0.322 | 0.256 | 0.986 | 0.982 | 0.991 | 0.993 |
| 16D | 0.653 | 0.629 | 0.484 | 0.323 | 0.993 | 0.990 | 0.995 | 0.997 |
| 32D | 0.660 | 0.767 | 0.609 | 0.352 | 0.995 | 0.994 | 0.997 | 0.998 |
| 64D | 0.642 | 0.847 | 0.687 | 0.349 | 0.996 | 0.995 | 0.998 | 0.999 |
| 128D | 0.554 | 0.859 | 0.709 | 0.327 | 0.996 | 0.995 | 0.998 | 0.999 |
| 256D | 0.422 | 0.759 | 0.629 | 0.269 | 0.994 | 0.992 | 0.996 | 0.997 |
| 512D | 0.165 | 0.493 | 0.407 | 0.169 | 0.987 | 0.981 | 0.988 | 0.987 |

When compared with the scores achieved by the 2D hyperbolic embedding, for most quality indicators the CLOVE result is surpassed somewhere between d = 8 and d = 16. However, for link prediction metrics (EPR20 and EPR5), CLOVE maintains competitive performance even against very high-dimensional Node2vec embeddings.

---

## Discussion

Investigating the organisational principles and functional dynamics of biological neural networks is central to unravelling the fundamental mechanisms of information processing and adaptive behaviour. Prior studies have suggested that the brain's wiring can exhibit various signatures consistent with hyperbolic geometry. Analyses of the human brain's functional architecture also reveal a hierarchically modular structure, a feature that naturally emerges in hyperbolic networks.

Brain regions coordinate through a highly hierarchical, chain-like arrangement of clustered anatomical zones. Individual neurons, with their branching axons and dendrites, resemble trees that collectively form a vast neural forest. Given that hyperbolic space is fundamentally a continuous representation of tree structures, it serves as an ideal geometric model for this network.

The analysis of neural connection navigability across various species showed a striking difference between navigability properties of mammalian and non-mammalian species, implying the inability of Euclidean distances to fully explain the structural organization of their neural connectomes. In contrast, hyperbolic space provided almost perfectly navigable maps for these connectomes for all species, showing that hyperbolic distances are exceptionally congruent with the structure of brain networks.

### Key Findings from This Study

A detailed analysis of embedding quality scores revealed that:

1. The 2D hyperbolic embedding (obtained via CLOVE) **outperforms both the original physical 3D arrangement of neurons and the 2D or 3D Euclidean embeddings** across all metrics

2. When examining higher-dimensional Euclidean embeddings, quality scores increase rapidly as a function of dimension, surpassing the hyperbolic baseline at approximately d = 8

3. These scores peak between d = 32 and d = 128, depending on the metric, before starting to decline in very high-dimensional regimes

4. While absolute highest scores are achieved with medium-to-high dimensional Euclidean embeddings, comparing embeddings across vastly different dimensions is nuanced

5. The organization of neural connectivity in the *Drosophila melanogaster* brain is **significantly more congruent with hyperbolic geometry** than Euclidean geometry in low-dimensional (2D or 3D) spaces

These findings corroborate previous research on the hyperbolic nature of neural networks, reinforcing the view that this geometry offers a natural framework for capturing their hierarchical and modular organization.

---

## Methods and Data

### Embedding Quality Scores

#### Greedy Routing Based Metrics

**Greedy routing** is a myopic path-finding strategy in which a packet is sent from a source node to a target node, making decisions based solely on local information.

**Greedy Routing Success Rate:**
$$GR = \frac{1}{N(N-1)} \sum_{s \in V} \sum_{t \in V, t \neq s} \delta_{s \to t}$$

where δ_{s→t} = 1 if greedy routing from source s to target t is successful, otherwise 0.

**Greedy Routing Score:**
$$GRS = \frac{1}{N(N-1)} \sum_{s \in N} \sum_{t \in N, t \neq s} \frac{\ell^{TSP}_{s \to t}}{\ell^{GR}_{s \to t}}$$

where ℓ^{TSP}_{s→t} and ℓ^{GR}_{s→t} denote the topological and greedy path lengths respectively.

**Greedy Routing Efficiency:**
$$GR = \frac{1}{N(N-1)} \sum_{s \in N} \sum_{t \in N, t \neq s} \frac{\Delta^{GEOM}_{s \to t}}{\Delta^{GR}_{s \to t}}$$

where Δ^{GEOM}_{s→t} is the geodesic distance and Δ^{GR}_{s→t} is the total geometric path length.

#### Mapping Accuracy

$$MA = \rho[R[TSP], R[GEOM]]$$

where R denotes the rank operator, ρ the standard Pearson correlation, TSP and GEOM are arrays containing topological and geometrical distances of node pairs.

#### Edge Prediction

An important property of high-quality embeddings is that they assign direct neighbours close to each other. An evaluation set S is constructed consisting of positive edges E⁺ (actual links) and negative edges E⁻ (non-existent links).

**EPAUC:** Area Under the ROC Curve - the probability that a randomly chosen positive edge is ranked higher than a randomly chosen negative edge.

**EPP (Average Precision):** Weighted mean of precisions at each threshold.

**EPRk:** Proportion of positive edges recovered within the top k% of the ranked set.

### Flywire Dataset

The study relied on the FlyWire FAFB dataset, a dense, whole-brain electron microscopy (EM) reconstruction of a female adult *Drosophila melanogaster* brain. The dataset provides:

- Detailed morphological reconstructions of individual neurons
- Precise annotations of synaptic contacts
- A directed, weighted network capturing connectivity at single-synapse resolution
- Hierarchical neuron cell-type annotations

**Data Cleaning:**

- Original dataset: 134,181 neurons connected by 3,869,878 synapses
- After removing multi-edges and disconnected neurons: 132,483 nodes and 2,509,503 edges

### Neuron Super-Classes

| Super-Class | Count | Percentage |
|------------|-------|-----------|
| Optic Neurons | 76,765 | 57.94% |
| Central Neurons | 32,298 | 24.38% |
| Sensory Neurons | 11,415 | 8.62% |
| Visual Projection Neurons | 8,046 | 6.07% |
| Ascending Neurons | 1,989 | 1.50% |
| Descending Neurons | 1,276 | 0.96% |
| Visual Centrifugal | 519 | 0.39% |
| Motor Neurons | 106 | 0.08% |
| Endocrine Neurons | 69 | 0.05% |
| **Total** | **132,483** | **100.0%** |

**Super-Class Descriptions:**

- **Central:** Local interneurons that act as the brain's internal wiring, completely contained within the central brain complex
- **Ascending:** Bottom-up inputs from the ventral nerve cord carrying sensory feedback
- **Descending:** Top-down outputs directing body movement
- **Motor:** Neurons bypassing the nerve cord and sending axons directly to muscles
- **Optic:** Local processing neurons confined to visual centers
- **Visual Projection:** Output of the eyes carrying processed visual features
- **Visual Centrifugal:** Feedback loop carrying signals back to optic lobes
- **Sensory:** Primary input neurons from external sensors

### Embedding Methods

#### CLOVE (Cluster-Level Optimised Vertex Embedding)

CLOVE maps nodes of a given graph into 2-dimensional hyperbolic space by:

1. **Constructing a multi-level angular arrangement** of communities and sub-communities refined recursively to individual nodes
2. **Assigning angular coordinates** following iterative hierarchical modular structure
3. **Assigning radial coordinates** using the Popularity-Similarity Optimization (PSO) model

**Angular Assignment Process:**

At the top level (l = 0), communities are extracted using modularity-based detection (Leiden by default). The weight between communities is:

$$W_{ij} = \exp\left(\frac{2E_l C_{ij}}{K_i K_j}\right) + 1$$

where E_l is the total number of edges, K_i and K_j are intra-community edge counts, and C_ij is the number of edges connecting communities.

A minimal-weight Hamiltonian cycle determines the angular ordering of top-level communities. Each community t^{(0)}_i is assigned a circular sector proportional to the number of nodes:

$$\left[\Phi^{(0)}_{i,start}, \Phi^{(0)}_{i,end}\right] = \left[2\pi \sum_{j=1}^{i-1} \frac{n^{(0)}_j}{N}, 2\pi \sum_{j=1}^{i} \frac{n^{(0)}_j}{N}\right]$$

**Radial Assignment:**

The i-th node is assigned a radial coordinate:

$$r_i = \frac{2}{\zeta} \ln\left(\frac{N}{i}\right)$$

with ζ = 1 for the native disk representation.

The **time complexity** of CLOVE is bounded above by O(N^{2c+1}) where b(N) ~ N^c with 0 < c < 1, demonstrating linear to quadratic scaling in practice.

#### Node2vec

Node2vec maps nodes into d-dimensional Euclidean space while preserving structural properties. The method:

1. **Generates multiple truncated random walks** following network edges
2. **Treats node sequences** analogously to sentences in natural language processing
3. **Adopts Word2vec methodology** where nodes appearing in similar contexts are embedded close together
4. **Uses biased random walks** interpolating between local and global network exploration

Transition probabilities are controlled by parameters p (return parameter) and q (in-out parameter):

$$\alpha_{pq}(t,x) = \begin{cases}
\frac{1}{p} & \text{if } x = t \\
1 & \text{if } x \text{ is a common neighbour of } t \text{ and } v \\
\frac{1}{q} & \text{otherwise}
\end{cases}$$

The **computational complexity** is O(E + N · d · ω²), where ω denotes the context window size.

---

## Data and Code Availability

- **Data:** All data used is publicly available from https://flywire.ai/
- **Code:** 
  - CLOVE Python implementation: http://github.com/samu32ELTE/hypCLOVE
  - Node2vec: https://pypi.org/project/node2vec/

---

## Acknowledgements

This project has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement no. 101021607 and was partially supported by the Data-Driven Health Division of National Laboratory for Health Security, Health Services Management Training Centre, Semmelweis University, Budapest, Hungary.

---

## Author Contributions

- **G. Palla:** Developed the concept of the study
- **B. Sulyok and S. G. Balogh:** Implemented the methods
- **B. Sulyok:** Carried out numerical simulations and data analysis, prepared figures
- **All authors:** Participated in writing and contributed to interpretations of results

---

## References

[1] Albert, R. & Barabási, A.-L. Statistical mechanics of complex networks. *Rev. Mod. Phys.* 74, 47–97 (2002).

[2] Mendes, J. F. F. & Dorogovtsev, S. N. Evolution of Networks: From Biological Nets to the Internet and WWW (Oxford Univ. Press, Oxford, 2003).

[3] Newman, M. E. J., Barabási, A.-L. & Watts, D. J. (eds) *The Structure and Dynamics of Networks* (Princeton University Press, Princeton and Oxford, 2006).

[4] Holme, P. & Saramäki, J. Temporal networks. *Physics Reports* 519, 97–125 (2012).

[5] Barrat, A., Barthelemy, M. & Vespignani, A. *Dynamical processes on complex networks* (Cambridge University Press, Cambridge, 2008).

[6] White, J. G., Southgate, E., Thomson, J. N. & Brenner, S. The structure of the nervous system of the nematode *caenorhabditis elegans*. *Philos Trans R Soc Lond B Biol Sci.* 314, 1–340 (1986).

[7] Cook, S. J. et al. Whole-animal connectomes of both *caenorhabditis elegans* sexes. *Nature* 571, 63–71 (2019).

[8] Winding, M. et al. The connectome of an insect brain. *Science* 379, eadd9330 (2023).

[9] Dorkenwald, S. et al. Neuronal wiring diagram of an adult brain. *Nature* 634, 124–138 (2024).

[10] Lin, A. et al. Network statistics of the whole-brain connectome of *drosophila*. *Nature* 634, 153–165 (2024).

[11] E., F. Y. Flexible navigational computations in the *drosophila* central complex. *Current opinion in neurobiology* 73, 102514 (2022).

[12] Cognigni, P., Felsenberg, J. & Waddell, S. Do the right thing: neural network mechanisms of memory formation, expression and update in *drosophila*. *Current opinion in neurobiology* 49, 51–58 (2018).

[13] Coen, P. et al. Dynamic sensory cues shape song structure in *drosophila*. *Nature* 507, 233–237 (2014).

[14] Farris, S. M. Are mushroom bodies cerebellum-like structures? *Arthropod Structure & Development* 40, 368–379 (2011).

[15] Borst, A. & Helmstaedter, M. Common circuit design in fly and mammalian motion vision. *Nature Neuroscience* 18, 1067–1076 (2015).

[16] Goyal, P. & Ferrara, E. Graph embedding techniques, applications, and performance: A survey. *Knowledge-Based Systems* 151, 78–94 (2018).

[17] Zhang, Y.-J., Yang, K.-C. & Radicchi, F. Systematic comparison of graph embedding methods in practical tasks. *Phys. Rev. E* 104, 044315 (2021).

[18] Yang, C., Shi, C., Liu, Z., Tu, C. & Sun, M. *Network Embedding* Synthesis Lectures on Artificial Intelligence and Machine Learning (Springer Cham, 2022).

[19] Baptista, A., Sánchez-García, R. J., Baudot, A. & Bianconi, G. Zoo guide to network embedding. *Journal of Physics: Complexity* 4, 042001 (2023).

[20] Kitsak, M. et al. Finding shortest and nearly shortest path nodes in large substantially incomplete networks by hyperbolic mapping. *Nature Communications* 14, 186 (2023).

[21] Qiu, Z., Balogh, S. G., Liu, X., Van Mieghem, P. & Kitsak, M. Geometric organization and inference of shortest path nodes in soft random geometric graphs. *arXiv preprint arXiv:2602.04507* (2026).

[22] Bogună, M. et al. Network geometry. *Nature Reviews Physics* 3, 114–135 (2021).

[23] Krioukov, D., Papadopoulos, F., Kitsak, M., Vahdat, A. & Bogună, M. Hyperbolic geometry of complex networks. *Phys. Rev. E* 82, 036106 (2010).

[24] Bogună, M., Papadopoulos, F. & Krioukov, D. Sustaining the internet with hyperbolic mapping. *Nat. Commun.* 1, 62 (2010).

[25] Papadopoulos, F., Psomas, C. & Krioukov, D. Network mapping by replaying hyperbolic growth. *IEEE/ACM Transactions on Networking* 23, 198–211 (2015).

[26-60] [Additional references omitted for brevity - see original document]

[61] Papadopoulos, F., Kitsak, M., Serrano, M. A., Bogună, M. & Krioukov, D. Popularity versus similarity in growing networks. *Nature* 489, 537 (2012).

[62] Kovács, B., Balogh, S. G. & Palla, G. Generalised popularity-similarity optimisation model for growing hyperbolic networks beyond two dimensions. *Sci. Rep.* 12, 968 (2022).

[63] Mikolov, T., Chen, K., Corrado, G. & Dean, J. Efficient estimation of word representations in vector space. *arXiv preprint arXiv:1301.3781* (2013).
