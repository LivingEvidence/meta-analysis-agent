/**
 * D3.js Interactive Visualization Renderers for Meta-Analysis Results.
 *
 * Renders forest plots, funnel plots, sensitivity (leave-one-out) plots,
 * and summary tables from the final.json data contract.
 */

const Visualizations = {
    _tooltip: null,

    /**
     * Main entry point: render all outcome visualizations.
     */
    renderAll(finalJson) {
        const visPanel = document.getElementById('vis-panel');
        visPanel.classList.remove('hidden');

        // Build outcome tabs
        const tabs = document.getElementById('vis-tabs');
        tabs.innerHTML = '';
        finalJson.outcomes.forEach((outcome, i) => {
            const btn = document.createElement('button');
            btn.textContent = outcome.outcome_name;
            btn.title = outcome.full_name;
            btn.onclick = () => this._selectOutcomeTab(outcome, i, finalJson);
            tabs.appendChild(btn);
        });

        // Show first outcome
        if (finalJson.outcomes.length > 0) {
            this._selectOutcomeTab(finalJson.outcomes[0], 0, finalJson);
        }

        // Close button
        document.getElementById('btn-close-vis').onclick = () => {
            visPanel.classList.add('hidden');
        };
    },

    _selectOutcomeTab(outcome, index, finalJson) {
        // Highlight active tab
        const tabs = document.getElementById('vis-tabs').children;
        for (let t of tabs) t.classList.remove('active');
        tabs[index].classList.add('active');

        // Build sub-tabs
        const subTabs = document.getElementById('vis-sub-tabs');
        subTabs.innerHTML = '';
        const views = ['Forest Plot', 'Funnel Plot', 'Sensitivity', 'Summary'];
        views.forEach((name, i) => {
            const btn = document.createElement('button');
            btn.textContent = name;
            btn.onclick = () => this._selectSubTab(outcome, name, i);
            subTabs.appendChild(btn);
        });

        // Default to forest plot
        this._selectSubTab(outcome, 'Forest Plot', 0);
    },

    _selectSubTab(outcome, viewName, index) {
        const subTabs = document.getElementById('vis-sub-tabs').children;
        for (let t of subTabs) t.classList.remove('active');
        subTabs[index].classList.add('active');

        const container = document.getElementById('vis-content');
        container.innerHTML = '';

        switch (viewName) {
            case 'Forest Plot':
                this.renderForestPlot(container, outcome);
                break;
            case 'Funnel Plot':
                this.renderFunnelPlot(container, outcome);
                break;
            case 'Sensitivity':
                this.renderSensitivityPlot(container, outcome);
                break;
            case 'Summary':
                this.renderSummary(container, outcome);
                break;
        }
    },

    // ============================
    // Forest Plot
    // ============================
    renderForestPlot(container, outcome) {
        const studies = outcome.studies || [];
        const pooled = outcome.pooled_random;
        const het = outcome.heterogeneity;
        const isRatio = outcome.is_ratio;

        if (studies.length === 0) {
            container.innerHTML = '<p class="text-muted">No study data available.</p>';
            return;
        }

        const margin = { top: 50, right: 180, bottom: 60, left: 200 };
        const rowHeight = 28;
        const width = Math.max(container.clientWidth - 20, 600);
        const height = margin.top + (studies.length + 2) * rowHeight + margin.bottom;

        const svg = d3.select(container)
            .append('svg')
            .attr('class', 'forest-plot')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
        const plotWidth = width - margin.left - margin.right;

        // X scale
        const allEffects = studies.map(s => [s.ci_lower, s.ci_upper]).flat()
            .concat([pooled.ci_lower, pooled.ci_upper]);
        let xDomain;
        if (isRatio) {
            const logVals = allEffects.filter(v => v > 0).map(v => Math.log(v));
            const pad = (Math.max(...logVals) - Math.min(...logVals)) * 0.15;
            xDomain = [Math.exp(Math.min(...logVals) - pad), Math.exp(Math.max(...logVals) + pad)];
        } else {
            const pad = (Math.max(...allEffects) - Math.min(...allEffects)) * 0.15;
            xDomain = [Math.min(...allEffects) - pad, Math.max(...allEffects) + pad];
        }

        const xScale = isRatio
            ? d3.scaleLog().domain(xDomain).range([0, plotWidth]).clamp(true)
            : d3.scaleLinear().domain(xDomain).range([0, plotWidth]);

        // Y positions
        const yPos = (i) => i * rowHeight;

        // Null reference line
        const nullVal = isRatio ? 1 : 0;
        g.append('line')
            .attr('class', 'null-line')
            .attr('x1', xScale(nullVal)).attr('x2', xScale(nullVal))
            .attr('y1', -10).attr('y2', (studies.length + 1) * rowHeight);

        // Header row
        g.append('text').attr('class', 'header-label')
            .attr('x', -margin.left + 10).attr('y', -25)
            .text('Study');
        g.append('text').attr('class', 'header-label')
            .attr('x', plotWidth / 2).attr('y', -25)
            .attr('text-anchor', 'middle')
            .text(`${outcome.measure} (95% CI)`);
        g.append('text').attr('class', 'header-label')
            .attr('x', plotWidth + 10).attr('y', -25)
            .text('Effect [95% CI]');
        g.append('text').attr('class', 'header-label')
            .attr('x', plotWidth + 155).attr('y', -25)
            .text('W');

        // Max weight for sizing
        const maxWeight = Math.max(...studies.map(s => s.weight), 1);

        // Studies
        studies.forEach((study, i) => {
            const y = yPos(i);

            // Study label
            g.append('text')
                .attr('class', 'study-label')
                .attr('x', -margin.left + 10)
                .attr('y', y + 4)
                .text(study.study);

            // CI line
            const x1 = xScale(Math.max(study.ci_lower, xDomain[0]));
            const x2 = xScale(Math.min(study.ci_upper, xDomain[1]));
            g.append('line')
                .attr('class', 'ci-line')
                .attr('x1', x1).attr('x2', x2)
                .attr('y1', y).attr('y2', y);

            // Point estimate (square sized by weight)
            const size = Math.max(4, Math.min(14, (study.weight / maxWeight) * 14));
            g.append('rect')
                .attr('class', 'point-estimate')
                .attr('x', xScale(study.effect) - size / 2)
                .attr('y', y - size / 2)
                .attr('width', size).attr('height', size)
                .on('mouseover', (event) => this._showTooltip(event, this._studyTooltip(study, outcome)))
                .on('mouseout', () => this._hideTooltip());

            // Effect text
            g.append('text')
                .attr('class', 'effect-text')
                .attr('x', plotWidth + 10)
                .attr('y', y + 4)
                .text(`${study.effect.toFixed(2)} [${study.ci_lower.toFixed(2)}, ${study.ci_upper.toFixed(2)}]`);

            // Weight
            g.append('text')
                .attr('class', 'weight-text')
                .attr('x', plotWidth + 165)
                .attr('y', y + 4)
                .text(`${study.weight.toFixed(1)}%`);
        });

        // Pooled estimate (diamond)
        const pooledY = yPos(studies.length) + rowHeight * 0.5;
        const diamondHalf = 8;
        const px = xScale(pooled.effect);
        const pLeft = xScale(pooled.ci_lower);
        const pRight = xScale(pooled.ci_upper);

        g.append('polygon')
            .attr('class', 'pooled-diamond')
            .attr('points', `${pLeft},${pooledY} ${px},${pooledY - diamondHalf} ${pRight},${pooledY} ${px},${pooledY + diamondHalf}`);

        g.append('text')
            .attr('class', 'study-label')
            .attr('x', -margin.left + 10)
            .attr('y', pooledY + 4)
            .style('font-weight', '700')
            .text('Random-effects model');

        g.append('text')
            .attr('class', 'effect-text')
            .attr('x', plotWidth + 10)
            .attr('y', pooledY + 4)
            .style('font-weight', '600')
            .text(`${pooled.effect.toFixed(2)} [${pooled.ci_lower.toFixed(2)}, ${pooled.ci_upper.toFixed(2)}]`);

        // Prediction interval
        if (het && het.prediction_lower != null && het.prediction_upper != null) {
            g.append('line')
                .attr('class', 'prediction-line')
                .attr('x1', xScale(het.prediction_lower))
                .attr('x2', xScale(het.prediction_upper))
                .attr('y1', pooledY + 12)
                .attr('y2', pooledY + 12);
        }

        // X axis
        const xAxis = isRatio
            ? d3.axisBottom(xScale).tickValues(this._logTicks(xDomain)).tickFormat(d3.format('.2f'))
            : d3.axisBottom(xScale).ticks(6);

        g.append('g')
            .attr('transform', `translate(0,${(studies.length + 1.5) * rowHeight})`)
            .call(xAxis);

        // Axis label
        g.append('text')
            .attr('class', 'axis-label')
            .attr('x', plotWidth / 2)
            .attr('y', (studies.length + 2.5) * rowHeight)
            .attr('text-anchor', 'middle')
            .text(isRatio ? `${outcome.measure} (log scale)` : outcome.measure);

        // Heterogeneity annotation
        if (het) {
            g.append('text')
                .attr('class', 'axis-label')
                .attr('x', 0)
                .attr('y', (studies.length + 2.5) * rowHeight)
                .text(`I\u00B2=${het.i2.toFixed(1)}%, \u03C4\u00B2=${het.tau2.toFixed(4)}, p=${het.q_pvalue.toFixed(3)}`);
        }
    },

    // ============================
    // Funnel Plot
    // ============================
    renderFunnelPlot(container, outcome) {
        const studies = outcome.studies || [];
        const pooled = outcome.pooled_random;
        const isRatio = outcome.is_ratio;

        if (studies.length === 0) {
            container.innerHTML = '<p class="text-muted">No study data available.</p>';
            return;
        }

        const margin = { top: 30, right: 40, bottom: 60, left: 70 };
        const width = Math.max(container.clientWidth - 20, 400);
        const height = 400;

        const svg = d3.select(container)
            .append('svg')
            .attr('class', 'funnel-plot')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;

        // Compute SE for each study
        const data = studies.map(s => {
            let se = s.se;
            if (!se && s.ci_lower && s.ci_upper) {
                if (isRatio) {
                    se = (Math.log(s.ci_upper) - Math.log(s.ci_lower)) / (2 * 1.96);
                } else {
                    se = (s.ci_upper - s.ci_lower) / (2 * 1.96);
                }
            }
            const effect = isRatio ? Math.log(s.effect) : s.effect;
            return { ...s, se: Math.abs(se || 0.1), logEffect: effect };
        });

        const pooledEffect = isRatio ? Math.log(pooled.effect) : pooled.effect;

        // Scales
        const effectExtent = d3.extent(data, d => d.logEffect);
        const effectPad = (effectExtent[1] - effectExtent[0]) * 0.3 || 0.5;
        const xScale = d3.scaleLinear()
            .domain([effectExtent[0] - effectPad, effectExtent[1] + effectPad])
            .range([0, plotWidth]);

        const maxSE = d3.max(data, d => d.se) * 1.1;
        const yScale = d3.scaleLinear()
            .domain([0, maxSE])
            .range([0, plotHeight]);

        // Funnel shape
        const funnelPoints = [
            [xScale(pooledEffect), yScale(0)],
            [xScale(pooledEffect - 1.96 * maxSE), yScale(maxSE)],
            [xScale(pooledEffect + 1.96 * maxSE), yScale(maxSE)],
        ];
        g.append('polygon')
            .attr('points', funnelPoints.map(p => p.join(',')).join(' '))
            .attr('fill', '#f0f4ff')
            .attr('stroke', '#ddd')
            .attr('stroke-dasharray', '4,3');

        // Pooled effect line
        g.append('line')
            .attr('class', 'pooled-line')
            .attr('x1', xScale(pooledEffect)).attr('x2', xScale(pooledEffect))
            .attr('y1', 0).attr('y2', plotHeight);

        // Study points
        g.selectAll('.study-point')
            .data(data)
            .enter()
            .append('circle')
            .attr('class', 'study-point')
            .attr('cx', d => xScale(d.logEffect))
            .attr('cy', d => yScale(d.se))
            .attr('r', 5)
            .on('mouseover', (event, d) => this._showTooltip(event, this._studyTooltip(d, outcome)))
            .on('mouseout', () => this._hideTooltip());

        // Axes
        g.append('g')
            .attr('transform', `translate(0,${plotHeight})`)
            .call(d3.axisBottom(xScale).ticks(6));

        g.append('g')
            .call(d3.axisLeft(yScale).ticks(5));

        // Labels
        svg.append('text')
            .attr('x', margin.left + plotWidth / 2)
            .attr('y', height - 10)
            .attr('text-anchor', 'middle')
            .attr('class', 'axis-label')
            .text(isRatio ? `log(${outcome.measure})` : outcome.measure);

        svg.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -(margin.top + plotHeight / 2))
            .attr('y', 18)
            .attr('text-anchor', 'middle')
            .attr('class', 'axis-label')
            .text('Standard Error');
    },

    // ============================
    // Sensitivity (Leave-One-Out) Plot
    // ============================
    renderSensitivityPlot(container, outcome) {
        const loo = outcome.leave_one_out || [];
        const pooled = outcome.pooled_random;
        const isRatio = outcome.is_ratio;

        if (loo.length === 0) {
            container.innerHTML = '<p class="text-muted">No leave-one-out data available.</p>';
            return;
        }

        const margin = { top: 40, right: 120, bottom: 50, left: 200 };
        const rowHeight = 28;
        const width = Math.max(container.clientWidth - 20, 500);
        const height = margin.top + (loo.length + 1) * rowHeight + margin.bottom;

        const svg = d3.select(container)
            .append('svg')
            .attr('class', 'sensitivity-plot')
            .attr('width', width)
            .attr('height', height);

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
        const plotWidth = width - margin.left - margin.right;

        // X scale
        const allVals = loo.map(l => [l.ci_lower, l.ci_upper]).flat()
            .concat([pooled.ci_lower, pooled.ci_upper]);
        const pad = (Math.max(...allVals) - Math.min(...allVals)) * 0.15;
        const xScale = d3.scaleLinear()
            .domain([Math.min(...allVals) - pad, Math.max(...allVals) + pad])
            .range([0, plotWidth]);

        const nullVal = isRatio ? 1 : 0;
        const yPos = (i) => i * rowHeight;

        // Null line
        g.append('line')
            .attr('class', 'null-line')
            .attr('x1', xScale(nullVal)).attr('x2', xScale(nullVal))
            .attr('y1', -10).attr('y2', (loo.length + 0.5) * rowHeight);

        // Overall pooled line
        g.append('line')
            .attr('class', 'overall-line')
            .attr('x1', xScale(pooled.effect)).attr('x2', xScale(pooled.effect))
            .attr('y1', -10).attr('y2', (loo.length + 0.5) * rowHeight);

        // Header
        g.append('text').attr('class', 'header-label')
            .attr('x', -margin.left + 10).attr('y', -15)
            .text('Omitting study');
        g.append('text').attr('class', 'header-label')
            .attr('x', plotWidth / 2).attr('y', -15)
            .attr('text-anchor', 'middle')
            .text(`${outcome.measure} (95% CI)`);

        // LOO entries
        loo.forEach((entry, i) => {
            const y = yPos(i);

            // Label
            g.append('text')
                .attr('class', 'study-label')
                .attr('x', -margin.left + 10)
                .attr('y', y + 4)
                .text(entry.excluded_study);

            // CI line
            g.append('line')
                .attr('class', 'ci-line')
                .attr('x1', xScale(entry.ci_lower)).attr('x2', xScale(entry.ci_upper))
                .attr('y1', y).attr('y2', y);

            // Point
            g.append('circle')
                .attr('cx', xScale(entry.effect))
                .attr('cy', y)
                .attr('r', 4)
                .attr('fill', 'var(--primary-blue)')
                .on('mouseover', (event) => {
                    this._showTooltip(event,
                        `Omitting: ${entry.excluded_study}<br>` +
                        `Effect: ${entry.effect.toFixed(3)}<br>` +
                        `95% CI: [${entry.ci_lower.toFixed(3)}, ${entry.ci_upper.toFixed(3)}]`
                    );
                })
                .on('mouseout', () => this._hideTooltip());

            // Effect text
            g.append('text')
                .attr('class', 'effect-text')
                .attr('x', plotWidth + 10)
                .attr('y', y + 4)
                .text(`${entry.effect.toFixed(2)} [${entry.ci_lower.toFixed(2)}, ${entry.ci_upper.toFixed(2)}]`);
        });

        // X axis
        g.append('g')
            .attr('transform', `translate(0,${(loo.length + 0.5) * rowHeight})`)
            .call(d3.axisBottom(xScale).ticks(6));
    },

    // ============================
    // Summary Table
    // ============================
    renderSummary(container, outcome) {
        const pooled = outcome.pooled_random;
        const fixed = outcome.pooled_fixed;
        const het = outcome.heterogeneity;
        const bias = outcome.publication_bias;

        const pClass = (p) => p < 0.05 ? 'stat-significant' : 'stat-not-significant';
        const hetClass = (i2) => i2 < 25 ? 'het-low' : (i2 < 75 ? 'het-moderate' : 'het-high');
        const hetLabel = (i2) => i2 < 25 ? 'Low' : (i2 < 50 ? 'Moderate' : (i2 < 75 ? 'Substantial' : 'Considerable'));

        let html = `<h3 style="margin-bottom:12px">${outcome.full_name} (${outcome.measure})</h3>`;
        html += '<table class="summary-table">';

        // Pooled estimates
        html += '<tr><th colspan="2">Pooled Estimates</th></tr>';
        html += `<tr><td>Random-effects</td><td>
            <strong>${pooled.effect.toFixed(3)}</strong>
            [${pooled.ci_lower.toFixed(3)}, ${pooled.ci_upper.toFixed(3)}],
            <span class="${pClass(pooled.p_value)}">p = ${pooled.p_value < 0.001 ? '< 0.001' : pooled.p_value.toFixed(3)}</span>
        </td></tr>`;
        if (fixed) {
            html += `<tr><td>Fixed-effect</td><td>
                ${fixed.effect.toFixed(3)}
                [${fixed.ci_lower.toFixed(3)}, ${fixed.ci_upper.toFixed(3)}],
                <span class="${pClass(fixed.p_value)}">p = ${fixed.p_value < 0.001 ? '< 0.001' : fixed.p_value.toFixed(3)}</span>
            </td></tr>`;
        }

        // Heterogeneity
        if (het) {
            html += '<tr><th colspan="2">Heterogeneity</th></tr>';
            html += `<tr><td>I\u00B2</td><td><span class="${hetClass(het.i2)}">${het.i2.toFixed(1)}% (${hetLabel(het.i2)})</span></td></tr>`;
            html += `<tr><td>\u03C4\u00B2</td><td>${het.tau2.toFixed(4)}</td></tr>`;
            html += `<tr><td>Q statistic</td><td>${het.q_statistic.toFixed(2)} (df=${het.q_df}), p = ${het.q_pvalue.toFixed(3)}</td></tr>`;
            if (het.prediction_lower != null) {
                html += `<tr><td>Prediction interval</td><td>[${het.prediction_lower.toFixed(3)}, ${het.prediction_upper.toFixed(3)}]</td></tr>`;
            }
        }

        // Publication bias
        if (bias) {
            html += '<tr><th colspan="2">Publication Bias</th></tr>';
            if (bias.statistic != null) {
                html += `<tr><td>${bias.method}'s test</td><td>t = ${bias.statistic.toFixed(3)},
                    <span class="${bias.p_value < 0.1 ? 'stat-significant' : 'stat-not-significant'}">
                    p = ${bias.p_value.toFixed(3)}</span></td></tr>`;
            }
            if (bias.note) {
                html += `<tr><td colspan="2" class="text-muted">${bias.note}</td></tr>`;
            }
        }

        // Study info
        html += '<tr><th colspan="2">Study Information</th></tr>';
        html += `<tr><td>Number of studies</td><td>${outcome.n_studies}</td></tr>`;
        html += `<tr><td>Effect measure</td><td>${outcome.measure} (${outcome.is_ratio ? 'ratio' : 'absolute'} scale)</td></tr>`;
        html += `<tr><td>Data type</td><td>${outcome.data_type === 'pre' ? 'Pre-calculated' : 'Raw event counts'}</td></tr>`;

        html += '</table>';

        // Interpretation
        if (outcome.interpretation) {
            html += `<div style="margin-top:16px;padding:12px 16px;background:var(--bg-primary);border-radius:var(--radius-sm);border-left:3px solid var(--primary-light)">
                <strong>Interpretation:</strong> ${outcome.interpretation}
            </div>`;
        }

        container.innerHTML = html;
    },

    // ============================
    // Helpers
    // ============================

    _showTooltip(event, html) {
        if (!this._tooltip) {
            this._tooltip = document.createElement('div');
            this._tooltip.className = 'vis-tooltip';
            document.body.appendChild(this._tooltip);
        }
        this._tooltip.innerHTML = html;
        this._tooltip.style.display = 'block';
        this._tooltip.style.left = (event.pageX + 12) + 'px';
        this._tooltip.style.top = (event.pageY - 10) + 'px';
    },

    _hideTooltip() {
        if (this._tooltip) {
            this._tooltip.style.display = 'none';
        }
    },

    _studyTooltip(study, outcome) {
        let html = `<strong>${study.study}</strong><br>`;
        html += `${outcome.measure}: ${study.effect.toFixed(3)}<br>`;
        html += `95% CI: [${study.ci_lower.toFixed(3)}, ${study.ci_upper.toFixed(3)}]<br>`;
        html += `Weight: ${study.weight.toFixed(1)}%`;
        if (study.se) html += `<br>SE: ${study.se.toFixed(4)}`;
        return html;
    },

    _logTicks(domain) {
        const ticks = [];
        const values = [0.1, 0.2, 0.3, 0.5, 0.7, 1, 1.5, 2, 3, 5, 10];
        values.forEach(v => {
            if (v >= domain[0] && v <= domain[1]) ticks.push(v);
        });
        if (ticks.length < 3) {
            // Generate more ticks if range is narrow
            const step = (domain[1] - domain[0]) / 5;
            for (let v = domain[0]; v <= domain[1]; v += step) {
                ticks.push(Math.round(v * 100) / 100);
            }
        }
        return ticks;
    }
};
