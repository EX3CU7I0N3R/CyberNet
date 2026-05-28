import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class VictimDetails:
    """Represents victim system details"""
    def __init__(self, ip: str, mac: str, name: str, os: str = None, port: int = None):
        self.ip = ip
        self.mac = mac
        self.name = name
        self.os = os
        self.port = port
    
    def to_dict(self) -> Dict:
        return {
            'ip': self.ip,
            'mac': self.mac,
            'name': self.name,
            'os': self.os,
            'port': self.port
        }
    
    def __repr__(self) -> str:
        return f"VictimDetails(ip={self.ip}, mac={self.mac}, name={self.name})"


class AttackDetails:
    """Represents attack system details"""
    def __init__(self, ip: str, mac: str = None, name: str = None, port: int = None, 
                 attack_type: str = None, confidence: float = 0.0):
        self.ip = ip
        self.mac = mac
        self.name = name
        self.port = port
        self.attack_type = attack_type
        self.confidence = confidence
    
    def to_dict(self) -> Dict:
        return {
            'ip': self.ip,
            'mac': self.mac,
            'name': self.name,
            'port': self.port,
            'attack_type': self.attack_type,
            'confidence': self.confidence
        }
    
    def __repr__(self) -> str:
        return f"AttackDetails(ip={self.ip}, attack_type={self.attack_type}, confidence={self.confidence})"


class RATDetectionModel:
    """RAT (Remote Access Trojan) Detection Model"""
    
    def __init__(self):
        self.victim = None
        self.attacker = None
        self.transactions = pd.DataFrame()
        self.detection_threshold = 0.6
    
    def detect_rat(self, victim_ip: str, victim_mac: str, victim_name: str, 
                   attacker_ip: str, transactions: pd.DataFrame, 
                   os: str = None, victim_port: int = None, 
                   attacker_port: int = None, attack_type: str = 'RAT') -> Tuple[bool, float]:
        """
        Detect RAT activity between victim and attacker
        
        Args:
            victim_ip: IP address of victim
            victim_mac: MAC address of victim
            victim_name: Hostname/name of victim
            attacker_ip: IP address of attacker
            transactions: DataFrame with network transactions
            os: Operating system of victim
            victim_port: Port on victim system
            attacker_port: Port on attacker system
            attack_type: Type of attack detected
        
        Returns:
            Tuple of (is_rat_detected, confidence_score)
        """
        self.victim = VictimDetails(victim_ip, victim_mac, victim_name, os, victim_port)
        self.attacker = AttackDetails(attacker_ip, port=attacker_port, attack_type=attack_type)
        
        # Filter relevant transactions
        self.transactions = self._filter_transactions(transactions, victim_ip, attacker_ip)
        
        # Calculate confidence score based on transaction patterns
        confidence = self._calculate_confidence(self.transactions)
        
        is_detected = confidence >= self.detection_threshold
        return is_detected, confidence
    
    def _filter_transactions(self, transactions: pd.DataFrame, 
                            victim_ip: str, attacker_ip: str) -> pd.DataFrame:
        """Filter transactions between victim and attacker"""
        filtered = transactions[
            ((transactions['src_ip'] == victim_ip) & (transactions['dst_ip'] == attacker_ip)) |
            ((transactions['src_ip'] == attacker_ip) & (transactions['dst_ip'] == victim_ip))
        ]
        return filtered
    
    def _calculate_confidence(self, transactions: pd.DataFrame) -> float:
        """Calculate confidence score based on transaction patterns"""
        if transactions.empty:
            return 0.0
        
        score = 0.0
        
        # Check for persistent connections
        if len(transactions) > 5:
            score += 0.3
        
        # Check for unusual ports
        if 'dst_port' in transactions.columns:
            unusual_ports = [4444, 5555, 8888, 1337, 31337, 6667, 27374, 12345]
            port_count = transactions[transactions['dst_port'].isin(unusual_ports)].shape[0]
            if port_count > 0:
                score += 0.4
        
        # Check for data exfiltration patterns
        if 'bytes_sent' in transactions.columns:
            large_transfers = transactions[transactions['bytes_sent'] > 1000000].shape[0]
            if large_transfers > 0:
                score += 0.3
        
        return min(score, 1.0)
    
    def get_victim_details(self) -> Optional[Dict]:
        """Return victim details as dictionary"""
        if self.victim is None:
            return None
        return self.victim.to_dict()
    
    def get_attacker_details(self) -> Optional[Dict]:
        """Return attacker/attack system details as dictionary"""
        if self.attacker is None:
            return None
        return self.attacker.to_dict()
    
    def get_relevant_transactions(self) -> List[Dict]:
        """Return all relevant transactions between victim and attacker"""
        if self.transactions.empty:
            return []
        return self.transactions.to_dict('records')
    
    def get_detection_summary(self) -> Dict:
        """Get complete detection summary"""
        return {
            'victim': self.get_victim_details(),
            'attacker': self.get_attacker_details(),
            'transaction_count': len(self.transactions),
            'transactions': self.get_relevant_transactions(),
            'detection_timestamp': datetime.now().isoformat()
        }
