import React from 'react';
import { Box, Typography, Paper, Alert, AlertTitle, Divider, Chip } from '@mui/material';
import { Warning, CheckCircle, Error, Info } from '@mui/icons-material';

interface BudgetBreakdownProps {
  budgetBreakdown: {
    flights: number;
    accommodation: number;
    food_and_activities: number;
    total_estimated: number;
    currency: string;
    budget_level?: string;
    is_within_budget?: boolean;
    variance_percentage?: number;
    total_budget?: number;
    budget_disclaimer?: {
      severity: 'info' | 'warning' | 'error';
      message: string;
      details: string[];
      component_breakdown?: Array<{
        component: string;
        allocated: number;
        actual: number;
        variance: number;
        variance_pct: number;
        over_budget: boolean;
      }>;
    };
    daily_breakdown?: Array<{
      day: number;
      title: string;
      estimated_cost: number;
    }>;
  };
  noFlights?: boolean;
  noHotels?: boolean;
}

const BudgetBreakdown: React.FC<BudgetBreakdownProps> = ({ 
  budgetBreakdown, 
  noFlights = false, 
  noHotels = false 
}) => {
  const formatCurrency = (amount: number, currency: string) => {
    if (amount === 0) return null;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const getStatusIcon = (severity?: string) => {
    switch (severity) {
      case 'error':
        return <Error color="error" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'info':
        return <Info color="info" />;
      default:
        return <CheckCircle color="success" />;
    }
  };

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'success';
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 3, mt: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
        Budget Breakdown
      </Typography>

      {/* Budget Status Alert */}
      {budgetBreakdown.budget_disclaimer && (
        <Alert 
          severity={getSeverityColor(budgetBreakdown.budget_disclaimer.severity) as any}
          icon={getStatusIcon(budgetBreakdown.budget_disclaimer.severity)}
          sx={{ mb: 2 }}
        >
          <AlertTitle>{budgetBreakdown.budget_disclaimer.message}</AlertTitle>
          <Box component="ul" sx={{ mt: 1, pl: 2 }}>
            {budgetBreakdown.budget_disclaimer.details.map((detail, idx) => (
              <li key={idx}>
                <Typography variant="body2">{detail}</Typography>
              </li>
            ))}
          </Box>
        </Alert>
      )}

      {/* Budget Overview */}
      {budgetBreakdown.total_budget && (
        <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Your Budget:
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {formatCurrency(budgetBreakdown.total_budget, budgetBreakdown.currency)}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary">
              Estimated Total:
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {formatCurrency(budgetBreakdown.total_estimated, budgetBreakdown.currency)}
            </Typography>
          </Box>
          {budgetBreakdown.variance_percentage !== undefined && (
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Variance:
              </Typography>
              <Chip 
                label={`${budgetBreakdown.variance_percentage > 0 ? '+' : ''}${budgetBreakdown.variance_percentage.toFixed(1)}%`}
                size="small"
                color={
                  budgetBreakdown.variance_percentage > 20 ? 'error' :
                  budgetBreakdown.variance_percentage > 10 ? 'warning' :
                  'success'
                }
              />
            </Box>
          )}
        </Box>
      )}

      <Divider sx={{ my: 2 }} />

      {/* Cost Components */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Flights */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body1">Flights</Typography>
          {noFlights || budgetBreakdown.flights === 0 ? (
            <Chip label="Not available" size="small" color="default" />
          ) : (
            <Typography variant="body1" fontWeight={600}>
              {formatCurrency(budgetBreakdown.flights, budgetBreakdown.currency)}
            </Typography>
          )}
        </Box>

        {/* Accommodation */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body1">Accommodation</Typography>
          {noHotels || budgetBreakdown.accommodation === 0 ? (
            <Chip label="Not available" size="small" color="default" />
          ) : (
            <Typography variant="body1" fontWeight={600}>
              {formatCurrency(budgetBreakdown.accommodation, budgetBreakdown.currency)}
            </Typography>
          )}
        </Box>

        {/* Food & Activities */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body1">Food & Activities</Typography>
          {budgetBreakdown.food_and_activities === 0 ? (
            <Chip label="Not available" size="small" color="default" />
          ) : (
            <Typography variant="body1" fontWeight={600}>
              {formatCurrency(budgetBreakdown.food_and_activities, budgetBreakdown.currency)}
            </Typography>
          )}
        </Box>

        <Divider />

        {/* Total */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Total Estimated</Typography>
          <Typography variant="h6" fontWeight={700} color="primary">
            {formatCurrency(budgetBreakdown.total_estimated, budgetBreakdown.currency)}
          </Typography>
        </Box>
      </Box>

      {/* Daily Breakdown */}
      {budgetBreakdown.daily_breakdown && budgetBreakdown.daily_breakdown.length > 0 && (
        <>
          <Divider sx={{ my: 3 }} />
          <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
            Daily Cost Breakdown
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 2 }}>
            {budgetBreakdown.daily_breakdown.map((day) => (
              <Box 
                key={day.day} 
                sx={{ 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  p: 1,
                  bgcolor: 'grey.50',
                  borderRadius: 1
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  Day {day.day}: {day.title}
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {formatCurrency(day.estimated_cost, budgetBreakdown.currency)}
                </Typography>
              </Box>
            ))}
          </Box>
        </>
      )}

      {/* Info Note */}
      {(noFlights || noHotels) && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            {noFlights && noHotels 
              ? "Flight and hotel options are currently unavailable. Budget estimates are based on typical costs for this destination."
              : noFlights 
              ? "Flight options are currently unavailable. Budget estimate includes typical flight costs."
              : "Hotel options are currently unavailable. Consider booking directly or adjusting your budget allocation."}
          </Typography>
        </Alert>
      )}
    </Paper>
  );
};

export default BudgetBreakdown;
