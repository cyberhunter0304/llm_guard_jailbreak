import React, { memo, useMemo } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

/**
 * CustomTooltip Component - Enhanced tooltip for charts
 */
const CustomTooltip = memo(({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: 'white',
        padding: '12px',
        border: '2px solid #e5e7eb',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
      }}>
        <p style={{ margin: 0, fontWeight: 600, color: '#1f2937' }}>
          {payload[0].name}: {payload[0].value}
        </p>
        <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#6b7280' }}>
          Click to filter
        </p>
      </div>
    );
  }
  return null;
});

CustomTooltip.displayName = 'CustomTooltip';

/**
 * ThreatDistributionChart Component - Pie chart of threat distribution
 */
const ThreatDistributionChart = memo(({ data, onDataClick }) => {
  const filteredData = useMemo(() => data.filter(item => item.value > 0), [data]);

  if (filteredData.length === 0) {
    return <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>No threat data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={filteredData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, value }) => value > 0 ? `${name}: ${value}` : ''}
          outerRadius={100}
          dataKey="value"
          onClick={onDataClick}
          cursor="pointer"
        >
          {filteredData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
});

ThreatDistributionChart.displayName = 'ThreatDistributionChart';

/**
 * TimelineChart Component - Area chart of activity over time
 */
const TimelineChart = memo(({ data }) => {
  if (!data || data.length === 0) {
    return <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>No timeline data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="date" 
          tick={{ fontSize: 11 }}
          angle={-45}
          textAnchor="end"
          height={60}
          interval={0}
        />
        <YAxis />
        <Tooltip />
        <Legend />
        <Area type="monotone" dataKey="sessions" stackId="1" stroke="#3b82f6" fill="#3b82f6" name="Sessions" />
        <Area type="monotone" dataKey="threats" stackId="1" stroke="#ef4444" fill="#ef4444" name="Threats" />
      </AreaChart>
    </ResponsiveContainer>
  );
});

TimelineChart.displayName = 'TimelineChart';

/**
 * ThreatTypeChart Component - Bar chart of threat types
 */
const ThreatTypeChart = memo(({ data, onDataClick }) => {
  const filteredData = useMemo(() => data.filter(item => item.count > 0), [data]);

  if (filteredData.length === 0) {
    return <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>No threat type data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={filteredData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Bar dataKey="count" name="Detections" onClick={onDataClick} cursor="pointer">
          {filteredData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
});

ThreatTypeChart.displayName = 'ThreatTypeChart';

/**
 * TopThreateningChart Component - Horizontal bar chart of most threatening sessions
 */
const TopThreateningChart = memo(({ data, onDataClick }) => {
  if (!data || data.length === 0) {
    return <div style={{ textAlign: 'center', padding: '20px', color: '#6b7280' }}>No threatening sessions</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis dataKey="id" type="category" width={100} tick={{ fontSize: 11 }} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="threats" fill="#ef4444" name="Total Threats" onClick={onDataClick} cursor="pointer" />
      </BarChart>
    </ResponsiveContainer>
  );
});

TopThreateningChart.displayName = 'TopThreateningChart';

/**
 * ChartContainer Component - Container for any chart with title
 */
const ChartContainer = memo(({ title, children }) => {
  return (
    <div className="chart-container">
      <div className="chart-title">{title}</div>
      {children}
    </div>
  );
});

ChartContainer.displayName = 'ChartContainer';

export { 
  CustomTooltip, 
  ThreatDistributionChart, 
  TimelineChart, 
  ThreatTypeChart, 
  TopThreateningChart,
  ChartContainer 
};
