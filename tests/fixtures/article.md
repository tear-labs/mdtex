---
title: Naked Von Neumann: VN Entropy is Better and Faster for JEPA | Tear Labs
h1: Naked Von Neumann: VN Entropy is Better and Faster for JEPA
description: A controlled objective swap: replacing SIGReg with von Neumann entropy trains 3–6× faster and yields stronger frozen image representations.
og_title: Naked Von Neumann: VN Entropy is Better and Faster for JEPA
og_description: 3–6× fewer epochs, 2.15–4.62× less GPU time, higher on all eight frozen image readouts.
deck: Switching SigReg for Von Neumann Entropy regularization speeds up training by 3-6x and ends up higher on image tasks
authors: Lev Stambler
affiliation_name: Tear Labs
affiliation_url: https://tearlabs.ai/
published: July 27, 2026
canonical_url: https://research.tearlabs.ai/__naked-vn/
citation_title: Naked Von Neumann: VN Entropy is Better and Faster for JEPA
citation_author: Stambler, Lev
citation_publication_date: 2026/07/27
citation_pdf_url: https://research.tearlabs.ai/__naked-vn/naked-vn.pdf
citation_arxiv_id:
abstract: Joint-embedding predictive architectures avoid representational collapse through a regularizer; LeJEPA's SIGReg pushes projected features toward an isotropic Gaussian. In a controlled objective swap that keeps the encoder, MLP projector, augmentations, optimizer, and evaluations fixed, we replace SIGReg with a von Neumann entropy term over the normalized embeddings' Gram matrix plus pairwise view alignment. On CIFAR-10/ResNet-18 the VN objective reaches every shared frozen-accuracy threshold in 3–6× fewer epochs and 2.15–4.62× less GPU time, and finishes higher on all five frozen readouts; on Imagenette/ViT-S it is higher on all three (+13.1 ridge points). Cheap screens on tabular, audio, and video data show VN winning each main readout. A projector ablation shows the MLP projector remains important for transfer. The objective family is I-VNE+/VNE's; the contribution is the controlled head-to-head against SIGReg measured as time-to-quality.
---

{{toc}}

## Introduction {#introduction}

Joint-embedding predictive architectures (JEPA)[@14][@15] are a form of self-supervised learning (SSL) which aim to learn a representation of its inputs without __any__ labeling. Rather than labels, JEPA simply requires multiple augmented views of each piece of data in the dataset.<sup class="fn"><a href="#fn-1">†</a></sup>
The goal is to learn a useful (and implicit) representation of the data.

Alignment alone is insufficient to learn a good representation. A model can cheat by mapping every input to one point: thus all augmented points share the same representation.
Thus, in LeJEPA[@1] and similar works[@5][@6][@7] SIGReg (or some other regularizer) is added which pushes the projected features towards an isotropic Gaussian (or some other geometry).

We focus in on the regularizer in this note though we also explore other simplifications to the JEPA objective.
Keeping the same encoder, MLP projector, augmentations, optimizer, and evaluations, we swap out the SIGReg auxiliary loss term for a von Neumann (VN) entropy loss which maximizes the spectral entropy of the normalized embeddings' Gram matrix:

$$\underbrace{(1 - \lambda)\, \mathcal{L}_{\mathrm{inv}} + \lambda \, T_{\mathrm{EP}}}_{\text{SIGReg (LeJEPA)}} \quad\longrightarrow\quad \underbrace{\mathbb{E}_{i<j}\!\left[\, 1 - \cos(u_i, u_j) \,\right] - \beta \, \frac{S(\rho)}{\log r}}_{\text{VN (this note)}}$$

The objective is not new (I-VNE+ 2022[@2], VNE CVPR 2023[@3]), and I-VNE+ already trained it non-contrastively — positive pairs only, no negatives. What is new, as far as the author is aware, is the head-to-head against SIGReg on a modern JEPA substrate: matched protocols, separately tuned, measured as time-to-quality. Concurrent JEPA work varies the target distribution[@16] rather than swapping in a spectral objective, and no VN-versus-SIGReg comparison appears in the literature to date.

Findings:

- CIFAR-10 / ResNet-18<sup class="fn"><a href="#fn-3">§</a></sup>: VN hits every shared frozen-accuracy threshold in 3–6× fewer epochs, 2.15–4.62× less GPU time.
- Final frozen readouts: VN higher on all five CIFAR readouts and all three Imagenette / ViT-S readouts (+13.1 ridge points there). 8/8 overall.
- Outside images (tabular, audio, video): VN wins each main readout, but SIGReg wins kNN on tabular and audio. Cheap screens, one seed for tabular — boundary evidence only.
- The "naked" variant drops the MLP projector entirely. VN still trains, but loses ~4 points on CIFAR-10 and 12.5–15.6 points on CIFAR-100 transfer, so the projector stays in the main recipe (Figure 9, appendix).

<p class="footnote" id="fn-1">† One can argue the augmentation function is still a supervised signal: it is chosen conditional on the data, encoding what should not matter about each input.</p>

<p class="footnote" id="fn-3">§ CIFAR-10[@17] is the standard small-image benchmark: 60,000 32×32 color photos in 10 classes (airplane, car, bird, …), 50k train / 10k test. CIFAR-100 is its companion set with 100 finer-grained classes; "CIFAR-100 transfer" trains readouts on CIFAR-100 labels over features that were learned on CIFAR-10 — a test of whether the features generalize beyond their pretraining distribution. ResNet-18[@18] is a standard small convolutional encoder (~11M parameters).</p>

## VN Entropy Objective {#objective}

Both arms share the pipeline in Figure 1. Only the loss on the projector outputs differs.

{{fig-1}}

VN: stack the ℓ2-normalized projector outputs as rows of $U$, form the trace-normalized Gram matrix, maximize its entropy alongside view alignment<sup class="fn"><a href="#fn-2">‡</a></sup>:

$$\rho = \frac{UU^{\top}}{\operatorname{Tr}(UU^{\top})}, \qquad S(\rho) = -\operatorname{Tr}(\rho \log \rho) = -\sum_k \lambda_k \log \lambda_k$$

$$\mathcal{L}_{\mathrm{VN}} = \mathbb{E}_{i<j}\!\left[\, 1 - \cos(u_i, u_j) \,\right] - \beta \, \frac{S(\rho)}{\log r}$$

- Maximizing $S(\rho)$ pushes the nonzero eigenvalues toward uniform.
- Collapse puts all spectral mass in one eigenvalue, so the entropy gradient opposes it directly.
- $\exp S(\rho)$ is the effective rank[@4]: how many dimensions the representation uses. It is the main diagnostic in the geometry section.

SIGReg[@1] instead matches the raw embedding distribution to an isotropic Gaussian, testing random 1-D projections through characteristic functions:

$$\mathcal{L}_{\mathrm{SIGReg}} = (1 - \lambda)\, \mathcal{L}_{\mathrm{inv}} + \lambda \, T_{\mathrm{EP}}$$

$T_{\mathrm{EP}}$ is a sliced normality test (Epps–Pulley): draw random unit directions $a$, project the embeddings $z_j$ onto each, and compare the projection's empirical characteristic function against the standard normal's:

$$T_{\mathrm{EP}} = \mathbb{E}_{a}\!\left[ \int \big|\, \hat{\varphi}_{a}(t) - e^{-t^{2}/2} \big|^{2}\, w(t)\, dt \right], \qquad \hat{\varphi}_{a}(t) = \tfrac{1}{n} \textstyle\sum_{j} e^{\, i t\, a^{\top} z_{j}}$$

The lower card of Figure 1 shows the picture: each direction gives a 1-D histogram of projections, and SIGReg penalizes its distance from $N(0, 1)$.

Note that the VN constraint is in some sense "weaker." SIGReg specifies a target set of distributions while VN simply says that the spectral energy of the Gram matrix must be spread out. A VN win means the stronger target isn't needed in these settings, not that SIGReg's theory is wrong.

<div class="compare-wrap">
  <table class="compare">
    <thead><tr><th></th><th class="vn-head">VN entropy</th><th class="sig-head">SIGReg</th></tr></thead>
    <tbody>
      <tr><th>What is shaped</th><td>Eigenvalues of the trace-normalized Gram matrix</td><td>Distributions of random 1-D projections</td></tr>
      <tr><th>Desired state</th><td>Flat nonzero spectrum: second-order isotropy</td><td>Isotropic Gaussian, beyond covariance</td></tr>
      <tr><th>Information used</th><td>Second-order spectrum</td><td>Characteristic-function discrepancies</td></tr>
      <tr><th>Implementation cost</th><td>Eigendecomposition per batch</td><td>Number and quality of random slices</td></tr>
    </tbody>
  </table>
</div>

Figure 2 shows the mechanism: spread the vectors and the spectrum flattens, raising effective rank.

{{fig-2}}

Prior work: this is the I-VNE+[@2] / VNE[@3] objective family ($UU^{\top}$ and the feature covariance share nonzero eigenvalues). Related second-order anti-collapse methods: whitening[@5], Barlow Twins[@6], VICReg[@7], dimensional-collapse analysis[@8], maximum entropy coding[@9], the Vendi score[@10], matrix information theory[@11]. VN trains on the rank diagnostic itself.

<p class="footnote" id="fn-2">‡ Backprop through <code>torch.linalg.eigvalsh</code> uses a closed-form backward, not the solver: Hellmann–Feynman gives $\partial \lambda_i / \partial A = q_i q_i^{\top}$, hence $\partial L / \partial A = Q\, \mathrm{diag}(\partial L / \partial \lambda)\, Q^{\top}$. Eigengap factors $1/(\lambda_i - \lambda_j)$ only enter eigen<em>vector</em> derivatives, so a spectral function like $S(\rho)$ stays differentiable at crossings; near-zero eigenvalues are clamped before the $\log$.</p>

## Faster {#faster}

Setup: CIFAR-10 / ResNet-18, three seeds per arm, 120 epochs. Frozen checkpoints at 11 epochs, evaluated with a ridge probe and a parameter-free cosine kNN.<sup class="fn"><a href="#fn-4">‖</a></sup> Each arm tuned separately.

{{fig-3}}

- Epoch-1 ridge accuracy: VN 58.0 vs 46.0.
- VN passes SIGReg's final 120-epoch accuracy by epoch 20.
- All 24 paired threshold crossings favor VN: 3–6× in epochs, 2.15–4.62× in GPU seconds. A VN epoch costs ~31% more GPU time (the eigendecomposition).

{{fig-4}}

{{fig-5}}

Caveat: all numbers are frozen-checkpoint evaluations. Online probes can behave differently; we don't report them.

<p class="footnote" id="fn-4">‖ Every readout keeps the encoder frozen and attaches the simplest possible classifier to its features. Ridge: a closed-form linear classifier with ℓ2 regularization. Linear probe: a linear classifier trained by gradient descent. kNN: label each test image by the majority vote of its k = 20 nearest training features under cosine similarity — no trained parameters at all, so it cannot flatter weak features through probe tuning. "Hitting a frozen-accuracy threshold" means a readout reaching a given accuracy.</p>

## Stronger {#stronger}

Final frozen readouts (Figure 6):

- CIFAR-10: ridge 91.1 vs 86.0, linear probe 92.1 vs 87.8, kNN 88.9 vs 84.4.
- CIFAR-100 transfer: kNN 39.0 vs 32.1, probe 46.0 vs 41.7.
- Imagenette / ViT-S<sup class="fn"><a href="#fn-5">¶</a></sup>: ridge 86.2 vs 73.1; both CIFAR-100 transfer readouts also higher.

{{fig-6}}

Non-image screens (Table 1)<sup class="fn"><a href="#fn-6">††</a></sup>: VN wins the main readout in all three domains; SIGReg wins kNN on CoverType and Speech Commands. Minimal tuning, one seed for CoverType.

{{table-1}}

<p class="footnote" id="fn-5">¶ Imagenette[@19]: a 10-class subset of ImageNet (~13k higher-resolution photos of easily distinguished classes) curated by fast.ai. ViT-S[@20] is a small Vision Transformer (~22M parameters) — a second encoder family, checking the result is not ResNet-specific.</p>

<p class="footnote" id="fn-6">†† CoverType[@21]: predict a forest's cover type (7 classes) from 54 cartographic features — a standard tabular benchmark, trained SCARF-style[@22] with random feature corruption as the augmentation. Speech Commands[@23]: one-second audio clips of 35 spoken keywords. UCF101[@24]: ~13k short video clips spanning 101 human actions.</p>

## Geometry {#geometry}

{{fig-7}}

Measured PCA of frozen backbone features (Figure 7):

- Full-space 1-NN: VN 72.7 vs 66.3.
- VN's top two components explain less variance (8.8% vs 12.8%): the information sits in more dimensions, so 2-D plots undersell it.

Projector spectra from a separate audit (Figure 8a, 1,024 test images): VN effective rank 326.4 ± 2.3 of 512; SIGReg 38.9 ± 0.3.

{{fig-8}}

Panel b tracks backbone effective rank during training, under two definitions:

- Raw covariance: SIGReg falls to ~4 while its accuracy rises (a few directions carry nearly all variance); VN grows to 163.
- ℓ2-normalized features first: SIGReg 77, VN 178.

Both are shown because they disagree about SIGReg. Either way VN is much higher-rank. This is correlation with frozen accuracy, not a causal claim.

## Discussion {#discussion}

Why wasn't this already known? Mostly chronology: I-VNE+/VNE (2022–23)[@2][@3] predate SIGReg (Nov 2025)[@1], and LeJEPA doesn't cite VNE. Beyond timing, VNE's ImageNet-1k result was mid-table (72.1 vs 74.3 for BYOL[@12], 75.3 for SwAV[@13]), the entropy sign is task-dependent (VNE also reports settings where reducing entropy helps), and a spectral loss needs an eigendecomposition where SIGReg is linear-time and distributed-friendly. SSL papers also report endpoint accuracy at fixed budgets, so time-to-quality — where VN's advantage is largest — mostly went unmeasured.

This note does not establish superiority across domains, scales, batch sizes, or distributed regimes (the largest run is a ViT-S on Imagenette). It does not make spectrum matching equivalent to Gaussian matching, and the objective itself is I-VNE+/VNE's, not ours. Whether the eigendecomposition stays cheap and stable at LeJEPA scale is the next experiment.

What holds: under matched, separately tuned protocols, swapping SIGReg for VN entropy trains 3–6× faster and produces better frozen representations in both image settings tested.

## Appendix {#appendix}

**Protocol.** CIFAR-10 / ResNet-18: 120 epochs, batch 512, three seeds per arm, two global and six local crops, frozen evaluation at 11 checkpoints (ridge, full linear probe, cosine kNN-20, CIFAR-100 transfer probes at selected checkpoints). Imagenette / ViT-S: same conventions, three seeds. Tuned settings: SIGReg lr 0.001, λ 0.02; VN lr 0.01. GPU seconds measured per epoch on the training device.

**Projector ablation (the "naked" in the title).** VN keeps training with the MLP projector removed — the loss runs directly on backbone features. Quality drops though (Figure 9): ~4 points in-domain (p100 85.9 vs 90.2, kNN 83.1 vs 87.1) and far more on transfer (CIFAR-100 kNN 36.3 vs 48.8, probe 42.6 vs 58.2). The projector looks like part of the generalizing substrate, not an artifact, so it stays in the recipe for both arms.

{{fig-9}}

**Data.** Every number and figure on this page is read from `data/results.json`, generated from the committed per-run CSVs. The build fails if headline claims drift from the raw data.

{{provenance}}

**Citing this note.** Code and data: [github.com/tear-labs/nakedvn-experiments](https://github.com/tear-labs/nakedvn-experiments). A PDF snapshot is on arXiv; this page is the primary version.

<pre class="bibtex"><code>@misc{stambler2026nakedvn,
  title         = {Naked Von Neumann: VN Entropy is Better and Faster for JEPA},
  author        = {Stambler, Lev},
  year          = {2026},
  month         = {July},
  institution   = {Tear Labs},
  url           = {https://research.tearlabs.ai/__naked-vn/},
  note          = {arXiv ID pending}
}</code></pre>

## References {#references}

1. Balestriero, R. and LeCun, Y. [LeJEPA: Provable and Scalable Self-Supervised Learning Without the Heuristics](https://arxiv.org/abs/2511.08544). arXiv:2511.08544, 2025.
2. Kim, J. and Rhee, W. [Mutual Information Estimation as a Difference of Entropies for Unsupervised Representation Learning](https://openreview.net/forum?id=J7FaSJw-xCM) (I-VNE+). OpenReview, 2022 (withdrawn ICLR submission).
3. Kim, J., Kang, S., Hwang, D., Shin, J., and Rhee, W. [VNE: An Effective Method for Improving Deep Representation by Manipulating Eigenvalue Distribution](https://openaccess.thecvf.com/content/CVPR2023/html/Kim_VNE_An_Effective_Method_for_Improving_Deep_Representation_by_Manipulating_CVPR_2023_paper.html). CVPR 2023. [Code](https://github.com/jaeill/CVPR23-VNE).
4. Garrido, Q., Balestriero, R., Najman, L., and LeCun, Y. [RankMe: Assessing the Downstream Performance of Pretrained Self-Supervised Representations by Their Rank](https://arxiv.org/abs/2210.02885). ICML 2023.
5. Ermolov, A., Siarohin, A., Sangineto, E., and Sebe, N. [Whitening for Self-Supervised Representation Learning](https://proceedings.mlr.press/v139/ermolov21a.html). ICML 2021.
6. Zbontar, J., Jing, L., Misra, I., LeCun, Y., and Deny, S. [Barlow Twins: Self-Supervised Learning via Redundancy Reduction](https://proceedings.mlr.press/v139/zbontar21a.html). ICML 2021.
7. Bardes, A., Ponce, J., and LeCun, Y. [VICReg: Variance-Invariance-Covariance Regularization for Self-Supervised Learning](https://openreview.net/forum?id=xm6YD62D1Ub). ICLR 2022.
8. Jing, L., Vincent, P., LeCun, Y., and Tian, Y. [Understanding Dimensional Collapse in Contrastive Self-Supervised Learning](https://arxiv.org/abs/2110.09348). ICLR 2022.
9. Liu, X., Wang, Z., Li, Y., and Wang, S. [Self-Supervised Learning via Maximum Entropy Coding](https://proceedings.neurips.cc/paper_files/paper/2022/hash/dc709714c52b35f2f34aca2a92b06bc8-Abstract-Conference.html). NeurIPS 2022.
10. Friedman, D. and Dieng, A.&nbsp;B. [The Vendi Score: A Diversity Evaluation Metric for Machine Learning](https://arxiv.org/abs/2210.02410). TMLR 2023.
11. Zhang, Y., Tan, Z., Yang, J., Huang, W., and Yuan, Y. [Matrix Information Theory for Self-Supervised Learning](https://arxiv.org/abs/2305.17326). arXiv:2305.17326, 2023.
12. Grill, J.-B., et&nbsp;al. [Bootstrap Your Own Latent: A New Approach to Self-Supervised Learning](https://arxiv.org/abs/2006.07733). NeurIPS 2020.
13. Caron, M., Misra, I., Mairal, J., Goyal, P., Bojanowski, P., and Joulin, A. [Unsupervised Learning of Visual Features by Contrasting Cluster Assignments](https://arxiv.org/abs/2006.09882). NeurIPS 2020.
14. LeCun, Y. [A Path Towards Autonomous Machine Intelligence](https://openreview.net/forum?id=BZ5a1r-kVsf). OpenReview, 2022.
15. Assran, M., Duval, Q., Misra, I., Bojanowski, P., Vincent, P., Rabbat, M., LeCun, Y., and Ballas, N. [Self-Supervised Learning from Images with a Joint-Embedding Predictive Architecture](https://arxiv.org/abs/2301.08243) (I-JEPA). CVPR 2023.
16. Kuang, Y., Dagade, Y., Rudner, T.&nbsp;G.&nbsp;J., Balestriero, R., and LeCun, Y. [Rectified LpJEPA: Joint-Embedding Predictive Architectures with Sparse and Maximum-Entropy Representations](https://arxiv.org/abs/2602.01456). arXiv:2602.01456, 2026.
17. Krizhevsky, A. [Learning Multiple Layers of Features from Tiny Images](https://www.cs.toronto.edu/~kriz/learning-features-2009-TR.pdf). Technical report, University of Toronto, 2009.
18. He, K., Zhang, X., Ren, S., and Sun, J. [Deep Residual Learning for Image Recognition](https://arxiv.org/abs/1512.03385). CVPR 2016.
19. Howard, J. [Imagenette](https://github.com/fastai/imagenette). fast.ai dataset release, 2019.
20. Dosovitskiy, A., et&nbsp;al. [An Image is Worth 16×16 Words: Transformers for Image Recognition at Scale](https://arxiv.org/abs/2010.11929). ICLR 2021.
21. Blackard, J.&nbsp;A. and Dean, D.&nbsp;J. [Comparative accuracies of artificial neural networks and discriminant analysis in predicting forest cover types from cartographic variables](https://archive.ics.uci.edu/dataset/31/covertype). Computers and Electronics in Agriculture, 1999.
22. Bahri, D., Jiang, H., Tay, Y., and Metzler, D. [SCARF: Self-Supervised Contrastive Learning using Random Feature Corruption](https://arxiv.org/abs/2106.15147). ICLR 2022.
23. Warden, P. [Speech Commands: A Dataset for Limited-Vocabulary Speech Recognition](https://arxiv.org/abs/1804.03209). arXiv:1804.03209, 2018.
24. Soomro, K., Zamir, A.&nbsp;R., and Shah, M. [UCF101: A Dataset of 101 Human Actions Classes From Videos in The Wild](https://arxiv.org/abs/1212.0402). arXiv:1212.0402, 2012.
