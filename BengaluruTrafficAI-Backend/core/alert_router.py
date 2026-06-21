"""
BengaluruTrafficAI — Alert Routing & Rule Engine
Post-processing: severity triage, alert routing, escalation logic

Routes violations based on:
- Severity level (1-5)
- Confidence threshold
- Violation type priority
- Repeat offender detection
- Time-based rules (peak hours, school zones)
"""

import logging
from datetime import datetime, time as dt_time
from typing import Optional, List, Dict
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger("alert_router")


class AlertPriority(str, Enum):
    CRITICAL = "critical"  # Immediate enforcement
    HIGH     = "high"      # Review within 1 hour
    MEDIUM   = "medium"    # Review within 4 hours
    LOW      = "low"       # Batch review
    INFO     = "info"      # Analytics only


class AlertChannel(str, Enum):
    ENFORCEMENT_DASHBOARD = "enforcement_dashboard"
    SMS_ALERT             = "sms_alert"
    EMAIL_REPORT          = "email_report"
    MOBILE_APP            = "mobile_app"
    ANALYTICS_ONLY        = "analytics_only"


@dataclass
class RoutingRule:
    """A single routing rule"""
    name: str
    condition: callable  # Function that evaluates violation
    priority: AlertPriority
    channels: List[AlertChannel]
    auto_approve: bool = False
    enabled: bool = True


@dataclass
class AlertAction:
    """Output of routing decision"""
    priority: AlertPriority
    channels: List[AlertChannel]
    auto_approve: bool
    escalate: bool = False
    reason: str = ""


class RuleEngine:
    """
    Rule-based alert routing engine.
    
    Usage:
        engine = RuleEngine()
        action = engine.evaluate(violation_event)
        if action.auto_approve:
            approve_immediately()
    """
    
    def __init__(self):
        self.rules: List[RoutingRule] = []
        self.repeat_offender_db: Dict[str, int] = {}  # plate_number -> count
        self._load_default_rules()
        logger.info(f"RuleEngine initialized with {len(self.rules)} rules")
    
    def _load_default_rules(self):
        """Load default routing rules"""
        
        # Rule 1: Critical - High severity + high confidence
        self.rules.append(RoutingRule(
            name="critical_high_confidence",
            condition=lambda v: v.get("severity", 0) >= 4 and v.get("confidence", 0) >= 0.90,
            priority=AlertPriority.CRITICAL,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
                AlertChannel.MOBILE_APP,
            ],
            auto_approve=True,
        ))
        
        # Rule 2: Critical - Red light violation
        self.rules.append(RoutingRule(
            name="red_light_violation",
            condition=lambda v: v.get("violation_type") == "red_light_violation" and v.get("confidence", 0) >= 0.85,
            priority=AlertPriority.CRITICAL,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
                AlertChannel.SMS_ALERT,
            ],
            auto_approve=True,
        ))
        
        # Rule 3: Critical - Wrong side driving
        self.rules.append(RoutingRule(
            name="wrong_side_driving",
            condition=lambda v: v.get("violation_type") == "wrong_side" and v.get("confidence", 0) >= 0.80,
            priority=AlertPriority.CRITICAL,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
                AlertChannel.SMS_ALERT,
            ],
            auto_approve=True,
        ))
        
        # Rule 4: High - Helmet violation with high confidence
        self.rules.append(RoutingRule(
            name="no_helmet_high_conf",
            condition=lambda v: v.get("violation_type") == "no_helmet" and v.get("confidence", 0) >= 0.85,
            priority=AlertPriority.HIGH,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
                AlertChannel.EMAIL_REPORT,
            ],
            auto_approve=True,
        ))
        
        # Rule 5: High - Triple riding
        self.rules.append(RoutingRule(
            name="triple_riding",
            condition=lambda v: v.get("violation_type") == "triple_riding" and v.get("confidence", 0) >= 0.80,
            priority=AlertPriority.HIGH,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
            ],
            auto_approve=False,
        ))
        
        # Rule 6: Medium - Seatbelt violation
        self.rules.append(RoutingRule(
            name="no_seatbelt",
            condition=lambda v: v.get("violation_type") == "no_seatbelt" and v.get("confidence", 0) >= 0.70,
            priority=AlertPriority.MEDIUM,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
            ],
            auto_approve=False,
        ))
        
        # Rule 7: Medium - Stop line violation
        self.rules.append(RoutingRule(
            name="stop_line",
            condition=lambda v: v.get("violation_type") == "stop_line_violation",
            priority=AlertPriority.MEDIUM,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
            ],
            auto_approve=False,
        ))
        
        # Rule 8: Low - Illegal parking (long dwell time)
        self.rules.append(RoutingRule(
            name="illegal_parking",
            condition=lambda v: v.get("violation_type") == "illegal_parking",
            priority=AlertPriority.LOW,
            channels=[
                AlertChannel.EMAIL_REPORT,
                AlertChannel.ANALYTICS_ONLY,
            ],
            auto_approve=False,
        ))
        
        # Rule 9: Peak hours - escalate all violations
        self.rules.append(RoutingRule(
            name="peak_hours_escalation",
            condition=lambda v: self._is_peak_hours() and v.get("severity", 0) >= 3,
            priority=AlertPriority.HIGH,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
                AlertChannel.MOBILE_APP,
            ],
            auto_approve=False,
        ))
        
        # Rule 10: Repeat offender escalation
        self.rules.append(RoutingRule(
            name="repeat_offender",
            condition=lambda v: self._is_repeat_offender(v.get("plate_number")),
            priority=AlertPriority.CRITICAL,
            channels=[
                AlertChannel.ENFORCEMENT_DASHBOARD,
                AlertChannel.SMS_ALERT,
            ],
            auto_approve=True,
        ))
    
    def evaluate(self, violation: dict) -> AlertAction:
        """
        Evaluate a violation against all rules.
        Returns the highest priority action that matches.
        """
        matched_rules = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                if rule.condition(violation):
                    matched_rules.append(rule)
                    logger.debug(f"Rule matched: {rule.name} | violation={violation.get('event_id')}")
            except Exception as e:
                logger.error(f"Rule evaluation error: {rule.name} | {e}")
        
        # If no rules match, use default
        if not matched_rules:
            return self._default_action(violation)
        
        # Return highest priority rule
        priority_order = {
            AlertPriority.CRITICAL: 0,
            AlertPriority.HIGH: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.LOW: 3,
            AlertPriority.INFO: 4,
        }
        
        best_rule = min(matched_rules, key=lambda r: priority_order[r.priority])
        
        # Check for repeat offender escalation
        escalate = self._should_escalate(violation)
        
        return AlertAction(
            priority=best_rule.priority,
            channels=best_rule.channels,
            auto_approve=best_rule.auto_approve,
            escalate=escalate,
            reason=f"Matched rule: {best_rule.name}",
        )
    
    def _default_action(self, violation: dict) -> AlertAction:
        """Default action when no rules match"""
        confidence = violation.get("confidence", 0)
        severity = violation.get("severity", 0)
        
        # High confidence + moderate severity → auto-approve
        if confidence >= 0.92 and severity >= 3:
            return AlertAction(
                priority=AlertPriority.HIGH,
                channels=[AlertChannel.ENFORCEMENT_DASHBOARD],
                auto_approve=True,
                reason="Default: high confidence + severity",
            )
        
        # Moderate confidence → manual review
        if confidence >= 0.70:
            return AlertAction(
                priority=AlertPriority.MEDIUM,
                channels=[AlertChannel.ENFORCEMENT_DASHBOARD],
                auto_approve=False,
                reason="Default: manual review required",
            )
        
        # Low confidence → analytics only
        return AlertAction(
            priority=AlertPriority.INFO,
            channels=[AlertChannel.ANALYTICS_ONLY],
            auto_approve=False,
            reason="Default: low confidence",
        )
    
    def _is_peak_hours(self) -> bool:
        """Check if current time is during peak traffic hours"""
        now = datetime.now().time()
        
        # Morning peak: 8:00 - 10:30
        morning_peak = dt_time(8, 0) <= now <= dt_time(10, 30)
        
        # Evening peak: 17:30 - 20:00
        evening_peak = dt_time(17, 30) <= now <= dt_time(20, 0)
        
        return morning_peak or evening_peak
    
    def _is_repeat_offender(self, plate_number: Optional[str]) -> bool:
        """Check if vehicle is a repeat offender (3+ violations)"""
        if not plate_number:
            return False
        
        count = self.repeat_offender_db.get(plate_number, 0)
        return count >= 3
    
    def _should_escalate(self, violation: dict) -> bool:
        """Determine if violation should be escalated"""
        # Escalate high severity violations during peak hours
        if self._is_peak_hours() and violation.get("severity", 0) >= 4:
            return True
        
        # Escalate repeat offenders
        if self._is_repeat_offender(violation.get("plate_number")):
            return True
        
        return False
    
    def record_violation(self, plate_number: Optional[str]):
        """Record violation for repeat offender tracking"""
        if not plate_number:
            return
        
        self.repeat_offender_db[plate_number] = \
            self.repeat_offender_db.get(plate_number, 0) + 1
        
        count = self.repeat_offender_db[plate_number]
        if count >= 3:
            logger.warning(f"Repeat offender detected: {plate_number} ({count} violations)")
    
    def add_custom_rule(self, rule: RoutingRule):
        """Add a custom routing rule"""
        self.rules.append(rule)
        logger.info(f"Added custom rule: {rule.name}")
    
    def disable_rule(self, rule_name: str):
        """Disable a specific rule"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info(f"Disabled rule: {rule_name}")
                return
        logger.warning(f"Rule not found: {rule_name}")
    
    def get_statistics(self) -> dict:
        """Get routing statistics"""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "repeat_offenders": len([v for v in self.repeat_offender_db.values() if v >= 3]),
            "total_tracked_vehicles": len(self.repeat_offender_db),
        }
