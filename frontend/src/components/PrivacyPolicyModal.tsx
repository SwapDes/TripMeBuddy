import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  Divider,
} from '@mui/material';
import SecurityIcon from '@mui/icons-material/Security';

interface PrivacyPolicyModalProps {
  open: boolean;
  onClose: () => void;
}

const PrivacyPolicyModal: React.FC<PrivacyPolicyModalProps> = ({ open, onClose }) => {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      scroll="paper"
    >
      <DialogTitle>
        <Typography variant="h5" component="div" fontWeight="bold">
          Privacy Policy
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Last Updated: February 15, 2026
        </Typography>
      </DialogTitle>

      <DialogContent dividers>
        {/* Critical Disclaimer */}
        <Alert severity="info" icon={<SecurityIcon />} sx={{ mb: 3 }}>
          <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
            Educational Project Notice
          </Typography>
          <Typography variant="body2">
            TripMeBuddy is a <strong>learning and upskilling project</strong>, not a commercial product. While we implement 
            industry-standard security practices, data protection measures, and follow GDPR-aligned principles, this is an 
            educational demonstration platform. Users should not share highly sensitive personal information.
          </Typography>
        </Alert>

        {/* Introduction */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            1. Introduction
          </Typography>
          <Typography variant="body2" paragraph>
            This Privacy Policy describes how TripMeBuddy ("we", "our", "the Platform") collects, uses, stores, and protects 
            your personal information when you use our AI-powered travel planning service.
          </Typography>
          <Typography variant="body2" paragraph>
            We are committed to protecting your privacy and implementing security best practices, including cloud security 
            standards, data encryption, and compliance-oriented data governance principles applicable across multiple geographies 
            including GDPR (EU), CCPA (California), and similar frameworks.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Information We Collect */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            2. Information We Collect
          </Typography>
          
          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            2.1 Account Information
          </Typography>
          <Typography variant="body2" paragraph>
            When you create an account, we collect:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2">Email address (via Keycloak authentication)</Typography></li>
            <li><Typography variant="body2">Username/display name</Typography></li>
            <li><Typography variant="body2">Authentication tokens and session data</Typography></li>
          </ul>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            2.2 Travel Planning Information
          </Typography>
          <Typography variant="body2" paragraph>
            When you use our service, we collect:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2">Travel preferences (destinations, dates, budget, number of travelers)</Typography></li>
            <li><Typography variant="body2">Search queries and trip planning requests</Typography></li>
            <li><Typography variant="body2">Saved trips and itineraries</Typography></li>
            <li><Typography variant="body2">User notes and preferences</Typography></li>
          </ul>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            2.3 Usage Data
          </Typography>
          <Typography variant="body2" paragraph>
            We automatically collect:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2">Log data (IP addresses, browser type, access times)</Typography></li>
            <li><Typography variant="body2">Device information</Typography></li>
            <li><Typography variant="body2">Platform usage patterns and interactions</Typography></li>
            <li><Typography variant="body2">API request/response metadata</Typography></li>
          </ul>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            2.4 AI Interaction Data
          </Typography>
          <Typography variant="body2" paragraph>
            When you interact with our AI features:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2">Natural language queries submitted to AI models</Typography></li>
            <li><Typography variant="body2">AI-generated trip recommendations and itineraries</Typography></li>
            <li><Typography variant="body2">Feedback on AI suggestions (if provided)</Typography></li>
          </ul>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* How We Use Information */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            3. How We Use Your Information
          </Typography>
          <Typography variant="body2" paragraph>
            We use collected information to:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2">Provide AI-powered travel planning recommendations</Typography></li>
            <li><Typography variant="body2">Maintain your account and authenticate users</Typography></li>
            <li><Typography variant="body2">Process trip planning requests and generate itineraries</Typography></li>
            <li><Typography variant="body2">Improve the platform and AI model performance</Typography></li>
            <li><Typography variant="body2">Ensure security and prevent fraud or abuse</Typography></li>
            <li><Typography variant="body2">Comply with legal obligations</Typography></li>
            <li><Typography variant="body2">Demonstrate technical capabilities for educational purposes</Typography></li>
          </ul>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Third-Party Services */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            4. Third-Party Services and Data Sharing
          </Typography>
          <Typography variant="body2" paragraph>
            We integrate with the following third-party services:
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            4.1 Authentication - Keycloak
          </Typography>
          <Typography variant="body2" paragraph>
            User authentication is handled by Keycloak (open-source identity management). Authentication data is processed 
            according to OAuth 2.0 and OpenID Connect standards.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            4.2 Travel Data - Amadeus API
          </Typography>
          <Typography variant="body2" paragraph>
            Flight and hotel search queries are sent to Amadeus Self-Service APIs. Search parameters (destinations, dates, 
            traveler count) are shared but not linked to your identity. See Amadeus Privacy Policy for details.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            4.3 AI Services - Google Gemini AI
          </Typography>
          <Typography variant="body2" paragraph>
            Destination research queries are processed by Google Gemini AI. Natural language queries about travel preferences 
            are sent to Google's AI services. See Google's AI/ML Privacy Policy for details.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            4.4 Cloud Infrastructure - AWS
          </Typography>
          <Typography variant="body2" paragraph>
            All data is hosted on Amazon Web Services (AWS) cloud infrastructure in compliance with AWS security standards. 
            We utilize AWS services including ECS, RDS, ElastiCache, and CloudFront.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Data Security */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            5. Data Security Measures
          </Typography>
          <Typography variant="body2" paragraph>
            We implement industry-standard security practices:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2"><strong>Encryption in Transit:</strong> All data transmitted via HTTPS/TLS</Typography></li>
            <li><Typography variant="body2"><strong>Encryption at Rest:</strong> Database and storage encryption enabled</Typography></li>
            <li><Typography variant="body2"><strong>Authentication:</strong> OAuth 2.0 with JWT tokens via Keycloak</Typography></li>
            <li><Typography variant="body2"><strong>Network Security:</strong> VPC isolation, security groups, and firewalls</Typography></li>
            <li><Typography variant="body2"><strong>Access Control:</strong> Role-based access control (RBAC)</Typography></li>
            <li><Typography variant="body2"><strong>Session Management:</strong> Redis-based secure session handling</Typography></li>
            <li><Typography variant="body2"><strong>AWS Best Practices:</strong> Following AWS Well-Architected Framework security pillar</Typography></li>
          </ul>
          <Typography variant="body2" paragraph sx={{ mt: 2 }}>
            <strong>Limitation:</strong> Despite these measures, as an educational project, we cannot guarantee enterprise-grade 
            security. No system is completely secure. You should not store highly sensitive personal or financial information.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Data Retention */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            6. Data Retention
          </Typography>
          <Typography variant="body2" paragraph>
            We retain your data:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2">Account data: Until account deletion requested</Typography></li>
            <li><Typography variant="body2">Trip planning data: Indefinitely unless deleted by user</Typography></li>
            <li><Typography variant="body2">Log data: 90 days for security and debugging purposes</Typography></li>
            <li><Typography variant="body2">Session data: 24 hours after session expiration</Typography></li>
          </ul>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* User Rights */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            7. Your Rights and Choices
          </Typography>
          <Typography variant="body2" paragraph>
            You have the right to:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2"><strong>Access:</strong> Request a copy of your personal data</Typography></li>
            <li><Typography variant="body2"><strong>Correction:</strong> Update or correct inaccurate information</Typography></li>
            <li><Typography variant="body2"><strong>Deletion:</strong> Request deletion of your account and associated data</Typography></li>
            <li><Typography variant="body2"><strong>Data Portability:</strong> Request your data in a portable format</Typography></li>
            <li><Typography variant="body2"><strong>Objection:</strong> Object to certain data processing activities</Typography></li>
            <li><Typography variant="body2"><strong>Withdrawal:</strong> Withdraw consent for data processing</Typography></li>
          </ul>
          <Typography variant="body2" paragraph sx={{ mt: 2 }}>
            To exercise these rights, contact the project maintainers through the provided channels.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* International Data Transfers */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            8. International Data Transfers
          </Typography>
          <Typography variant="body2" paragraph>
            Your data may be transferred to and processed in countries outside your residence. We follow data protection 
            principles aligned with GDPR, CCPA, and similar frameworks. AWS infrastructure complies with international 
            data transfer requirements.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Children's Privacy */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            9. Children's Privacy
          </Typography>
          <Typography variant="body2" paragraph>
            TripMeBuddy is not intended for users under 18 years of age. We do not knowingly collect personal information 
            from minors. If we become aware of such collection, we will delete the information promptly.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Cookies and Tracking */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            10. Cookies and Tracking Technologies
          </Typography>
          <Typography variant="body2" paragraph>
            We use:
          </Typography>
          <ul style={{ marginLeft: '20px', marginTop: '8px', marginBottom: '8px' }}>
            <li><Typography variant="body2"><strong>Essential Cookies:</strong> For authentication and session management</Typography></li>
            <li><Typography variant="body2"><strong>Functional Cookies:</strong> To remember preferences and settings</Typography></li>
            <li><Typography variant="body2"><strong>Analytics:</strong> Minimal usage analytics for platform improvement</Typography></li>
          </ul>
          <Typography variant="body2" paragraph>
            We do not use third-party advertising cookies or trackers.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Data Breach Notification */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            11. Data Breach Notification
          </Typography>
          <Typography variant="body2" paragraph>
            In the event of a data breach affecting your personal information, we will notify affected users and relevant 
            authorities as required by applicable laws, typically within 72 hours of discovery.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Geographic-Specific Rights */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            12. Geographic-Specific Privacy Rights
          </Typography>
          
          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            12.1 European Union (GDPR)
          </Typography>
          <Typography variant="body2" paragraph>
            EU residents have additional rights under GDPR including the right to lodge complaints with supervisory authorities.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            12.2 California (CCPA)
          </Typography>
          <Typography variant="body2" paragraph>
            California residents have rights to know what personal information is collected and request deletion. We do not 
            sell personal information.
          </Typography>

          <Typography variant="subtitle2" fontWeight="bold" gutterBottom sx={{ mt: 2 }}>
            12.3 Other Jurisdictions
          </Typography>
          <Typography variant="body2" paragraph>
            We strive to comply with privacy laws applicable in your jurisdiction. Contact us for jurisdiction-specific inquiries.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Changes to Privacy Policy */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            13. Changes to This Privacy Policy
          </Typography>
          <Typography variant="body2" paragraph>
            We may update this Privacy Policy periodically. We will notify users of material changes via email or platform 
            notification. Continued use after changes constitutes acceptance.
          </Typography>
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Contact Information */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight="bold">
            14. Contact Information
          </Typography>
          <Typography variant="body2" paragraph>
            For privacy-related questions, data access requests, or to exercise your rights, please contact the project 
            maintainers through the GitHub repository or provided contact channels.
          </Typography>
        </Box>

        <Alert severity="warning" sx={{ mt: 3 }}>
          <Typography variant="body2">
            <strong>Educational Project Reminder:</strong> While we implement security and privacy best practices following 
            industry standards and compliance frameworks, this is a demonstration platform. Exercise caution with sensitive 
            personal information. Always verify data handling practices before sharing confidential details.
          </Typography>
        </Alert>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained" color="primary">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PrivacyPolicyModal;
