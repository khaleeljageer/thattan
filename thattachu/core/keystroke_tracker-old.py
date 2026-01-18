#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tamil99 Keystroke Tracker
Tracks individual keystrokes for Tamil99 keyboard learning
"""

from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Optional


@dataclass
class StrokeData:
    """Data class to store individual keystroke information"""
    key: str
    expected_key: str
    is_correct: bool
    response_time: float  # in milliseconds
    timestamp: datetime


class Tamil99KeyboardLayout:
    """
    Tamil99 keyboard layout mapping
    Based on official Tamil99 standard: https://help.keyman.com/keyboard/ekwtamil99uni/2.0.5/ekwtamil99uni
    
    Typing follows consonant-vowel pattern. Characters are typed as:
    - Consonant + vowel key = consonant-vowel combination (e.g., கா = hq)
    - Consonant + f = consonant with pulli (e.g., க் = hf)
    - Consonant + same consonant = pulli on first (e.g., க்க = hh)
    """
    
    # Tamil99 layout mapping (key -> Tamil character for standalone display)
    # Note: Most Tamil characters are combinations typed with multiple keys
    LAYOUT = {
        # Vowels (standalone)
        'a': 'அ', 'q': 'ஆ', 's': 'இ', 'w': 'ஈ',
        'd': 'உ', 'e': 'ஊ', 'g': 'எ', 't': 'ஏ',
        'r': 'ஐ', 'c': 'ஒ', 'x': 'ஓ', 'z': 'ஔ',
        
        # Consonants
        'h': 'க', 'j': 'ப', 'k': 'ம', 'l': 'த', ';': 'ந',
        'v': 'வ', 'b': 'ங', 'n': 'ல', 'm': 'ர',
        '[': 'ச', ']': 'ஞ', '/': 'ழ', 'y': 'ள', 'u': 'ற',
        'i': 'ன', 'o': 'ட', 'p': 'ண', "'": 'ய',
        
        # Pulli (dead consonant marker)
        'f': '்',
        
        # Grantha consonants (with Shift)
        'Q': 'ஸ', 'W': 'ஷ', 'E': 'ஜ', 'R': 'ஹ', 'Y': 'க்ஷ',
        
        # Special characters
        'A': 'ஃ',  # Aytham
        'T': 'ஶ்ரீ',  # Sri (also 'S' can be ஸ்ரீ)
        'S': 'ஸ்ரீ',  # Sri
    }
    
    # Reverse mapping: Tamil character -> keystroke sequence
    # Based on official Tamil99 m17n file mappings - embedded directly in code
    # This comprehensive mapping includes all Tamil characters and their keystroke sequences
    CHAR_TO_KEYSTROKES: Dict[str, str] = {
        # ===== Standalone Vowels =====
        'அ': 'a', 'ஆ': 'q', 'இ': 's', 'ஈ': 'w',
        'உ': 'd', 'ஊ': 'e', 'எ': 'g', 'ஏ': 't',
        'ஐ': 'r', 'ஒ': 'c', 'ஓ': 'x', 'ஔ': 'z',
        
        # ===== Consonants (with implicit அ) =====
        'க': 'h', 'ப': 'j', 'ம': 'k', 'த': 'l', 'ந': ';',
        'வ': 'v', 'ய': "'", 'ல': 'n', 'ர': 'm',
        'ங': 'b', 'ஞ': ']', 'ச': '[', 'ழ': '/',
        'ள': 'y', 'ற': 'u', 'ன': 'i', 'ட': 'o', 'ண': 'p',
        
        # ===== Consonants with Pulli (dead consonants) =====
        'க்': 'hf', 'ப்': 'jf', 'ம்': 'kf', 'த்': 'lf', 'ந்': ';f',
        'வ்': 'vf', 'ய்': "'f", 'ல்': 'nf', 'ர்': 'mf',
        'ங்': 'bf', 'ஞ்': ']f', 'ச்': '[f', 'ழ்': '/f',
        'ள்': 'yf', 'ற்': 'uf', 'ன்': 'if', 'ட்': 'of', 'ண்': 'pf',
        
        # ===== Consonant + அ (explicit) =====
        # Note: These are the same as above but with explicit 'a' - using shorter form
        # 'க': 'ha', 'ப': 'ja', etc. - but 'h' is preferred
        
        # ===== Consonant-Vowel Combinations with க =====
        'கா': 'hq', 'கி': 'hs', 'கீ': 'hw', 'கு': 'hd', 'கூ': 'he',
        'கெ': 'hg', 'கே': 'ht', 'கை': 'hr', 'கொ': 'hc', 'கோ': 'hx', 'கௌ': 'hz',
        
        # ===== Consonant-Vowel Combinations with ப =====
        'பா': 'jq', 'பி': 'js', 'பீ': 'jw', 'பு': 'jd', 'பூ': 'je',
        'பெ': 'jg', 'பே': 'jt', 'பை': 'jr', 'பொ': 'jc', 'போ': 'jx', 'பௌ': 'jz',
        
        # ===== Consonant-Vowel Combinations with ம =====
        'மா': 'kq', 'மி': 'ks', 'மீ': 'kw', 'மு': 'kd', 'மூ': 'ke',
        'மெ': 'kg', 'மே': 'kt', 'மை': 'kr', 'மொ': 'kc', 'மோ': 'kx', 'மௌ': 'kz',
        
        # ===== Consonant-Vowel Combinations with த =====
        'தா': 'lq', 'தி': 'ls', 'தீ': 'lw', 'து': 'ld', 'தூ': 'le',
        'தெ': 'lg', 'தே': 'lt', 'தை': 'lr', 'தொ': 'lc', 'தோ': 'lx', 'தௌ': 'lz',
        
        # ===== Consonant-Vowel Combinations with ந =====
        'நா': ';q', 'நி': ';s', 'நீ': ';w', 'நு': ';d', 'நூ': ';e',
        'நெ': ';g', 'நே': ';t', 'நை': ';r', 'நொ': ';c', 'நோ': ';x', 'நௌ': ';z',
        
        # ===== Consonant-Vowel Combinations with வ =====
        'வா': 'vq', 'வி': 'vs', 'வீ': 'vw', 'வு': 'vd', 'வூ': 've',
        'வெ': 'vg', 'வே': 'vt', 'வை': 'vr', 'வொ': 'vc', 'வோ': 'vx', 'வௌ': 'vz',
        
        # ===== Consonant-Vowel Combinations with ய =====
        'யா': "'q", 'யி': "'s", 'யீ': "'w", 'யு': "'d", 'யூ': "'e",
        'யெ': "'g", 'யே': "'t", 'யை': "'r", 'யொ': "'c", 'யோ': "'x", 'யௌ': "'z",
        
        # ===== Consonant-Vowel Combinations with ல =====
        'லா': 'nq', 'லி': 'ns', 'லீ': 'nw', 'லு': 'nd', 'லூ': 'ne',
        'லெ': 'ng', 'லே': 'nt', 'லை': 'nr', 'லொ': 'nc', 'லோ': 'nx', 'லௌ': 'nz',
        
        # ===== Consonant-Vowel Combinations with ர =====
        'ரா': 'mq', 'ரி': 'ms', 'ரீ': 'mw', 'ரு': 'md', 'ரூ': 'me',
        'ரெ': 'mg', 'ரே': 'mt', 'ரை': 'mr', 'ரொ': 'mc', 'ரோ': 'mx', 'ரௌ': 'mz',
        
        # ===== Consonant-Vowel Combinations with ங =====
        'ஙா': 'bq', 'ஙி': 'bs', 'ஙீ': 'bw', 'ஙு': 'bd', 'ஙூ': 'be',
        'ஙெ': 'bg', 'ஙே': 'bt', 'ஙை': 'br', 'ஙொ': 'bc', 'ஙோ': 'bx', 'ஙௌ': 'bz',
        
        # ===== Consonant-Vowel Combinations with ஞ =====
        'ஞா': ']q', 'ஞி': ']s', 'ஞீ': ']w', 'ஞு': ']d', 'ஞூ': ']e',
        'ஞெ': ']g', 'ஞே': ']t', 'ஞை': ']r', 'ஞொ': ']c', 'ஞோ': ']x', 'ஞௌ': ']z',
        
        # ===== Consonant-Vowel Combinations with ச =====
        'சா': '[q', 'சி': '[s', 'சீ': '[w', 'சு': '[d', 'சூ': '[e',
        'செ': '[g', 'சே': '[t', 'சை': '[r', 'சொ': '[c', 'சோ': '[x', 'சௌ': '[z',
        
        # ===== Consonant-Vowel Combinations with ழ =====
        'ழா': '/q', 'ழி': '/s', 'ழீ': '/w', 'ழு': '/d', 'ழூ': '/e',
        'ழெ': '/g', 'ழே': '/t', 'ழை': '/r', 'ழொ': '/c', 'ழோ': '/x', 'ழௌ': '/z',
        
        # ===== Consonant-Vowel Combinations with ள =====
        'ளா': 'yq', 'ளி': 'ys', 'ளீ': 'yw', 'ளு': 'yd', 'ளூ': 'ye',
        'ளெ': 'yg', 'ளே': 'yt', 'ளை': 'yr', 'ளொ': 'yc', 'ளோ': 'yx', 'ளௌ': 'yz',
        
        # ===== Consonant-Vowel Combinations with ற =====
        'றா': 'uq', 'றி': 'us', 'றீ': 'uw', 'று': 'ud', 'றூ': 'ue',
        'றெ': 'ug', 'றே': 'ut', 'றை': 'ur', 'றொ': 'uc', 'றோ': 'ux', 'றௌ': 'uz',
        
        # ===== Consonant-Vowel Combinations with ன =====
        'னா': 'iq', 'னி': 'is', 'னீ': 'iw', 'னு': 'id', 'னூ': 'ie',
        'னெ': 'ig', 'னே': 'it', 'னை': 'ir', 'னொ': 'ic', 'னோ': 'ix', 'னௌ': 'iz',
        
        # ===== Consonant-Vowel Combinations with ட =====
        'டா': 'oq', 'டி': 'os', 'டீ': 'ow', 'டு': 'od', 'டூ': 'oe',
        'டெ': 'og', 'டே': 'ot', 'டை': 'or', 'டொ': 'oc', 'டோ': 'ox', 'டௌ': 'oz',
        
        # ===== Consonant-Vowel Combinations with ண =====
        'ணா': 'pq', 'ணி': 'ps', 'ணீ': 'pw', 'ணு': 'pd', 'ணூ': 'pe',
        'ணெ': 'pg', 'ணே': 'pt', 'ணை': 'pr', 'ணொ': 'pc', 'ணோ': 'px', 'ணௌ': 'pz',
        
        # ===== Double Consonants (with automatic pulli) =====
        'க்க': 'hh', 'ங்க': 'bh', 'ஞ்ச': '][', 'ண்ட': 'po', 'ம்ப': 'kj',
        'ந்த': ';l', 'ன்ற': 'iu',
        
        # ===== Grantha Consonants =====
        'ஸ': 'Q', 'ஷ': 'W', 'ஜ': 'E', 'ஹ': 'R', 'ஶ': 'U',
        'க்ஷ': 'T', 'ஶ்ரீ': 'Y',
        
        # Grantha with pulli
        'ஸ்': 'Qf', 'ஷ்': 'Wf', 'ஜ்': 'Ef', 'ஹ்': 'Rf', 'ஶ்': 'Uf',
        'க்ஷ்': 'Tf',
        
        # Grantha with vowels (examples - all follow same pattern)
        'ஸா': 'Qq', 'ஸி': 'Qs', 'ஸீ': 'Qw', 'ஸு': 'Qd', 'ஸூ': 'Qe',
        'ஸெ': 'Qg', 'ஸே': 'Qt', 'ஸை': 'Qr', 'ஸொ': 'Qc', 'ஸோ': 'Qx', 'ஸௌ': 'Qz',
        
        'ஷா': 'Wq', 'ஷி': 'Ws', 'ஷீ': 'Ww', 'ஷு': 'Wd', 'ஷூ': 'We',
        'ஷெ': 'Wg', 'ஷே': 'Wt', 'ஷை': 'Wr', 'ஷொ': 'Wc', 'ஷோ': 'Wx', 'ஷௌ': 'Wz',
        
        'ஜா': 'Eq', 'ஜி': 'Es', 'ஜீ': 'Ew', 'ஜு': 'Ed', 'ஜூ': 'Ee',
        'ஜெ': 'Eg', 'ஜே': 'Et', 'ஜை': 'Er', 'ஜொ': 'Ec', 'ஜோ': 'Ex', 'ஜௌ': 'Ez',
        
        'ஹா': 'Rq', 'ஹி': 'Rs', 'ஹீ': 'Rw', 'ஹு': 'Rd', 'ஹூ': 'Re',
        'ஹெ': 'Rg', 'ஹே': 'Rt', 'ஹை': 'Rr', 'ஹொ': 'Rc', 'ஹோ': 'Rx', 'ஹௌ': 'Rz',
        
        'க்ஷா': 'Tq', 'க்ஷி': 'Ts', 'க்ஷீ': 'Tw', 'க்ஷு': 'Td', 'க்ஷூ': 'Te',
        'க்ஷெ': 'Tg', 'க்ஷே': 'Tt', 'க்ஷை': 'Tr', 'க்ஷொ': 'Tc', 'க்ஷோ': 'Tx', 'க்ஷௌ': 'Tz',
        
        # ===== Pulli mark (standalone) =====
        '்': 'f',
        
        # ===== Aytham =====
        'ஃ': 'F',
        
        # ===== Vowel signs (diacritics) =====
        'ா': '^q', 'ி': '^s', 'ீ': '^w', 'ு': '^d', 'ூ': '^e',
        'ெ': '^g', 'ே': '^t', 'ை': '^r', 'ொ': '^C', 'ோ': '^x', 'ௌ': '^z',
        
        # ===== Tamil Numerals =====
        '௧': '^#1', '௨': '^#2', '௩': '^#3', '௪': '^#4', '௫': '^#5',
        '௬': '^#6', '௭': '^#7', '௮': '^#8', '௯': '^#9', '௦': '^#0',
        
        # ===== Special Symbols =====
        '௹': 'A',  # Rupee
        '௺': 'S',  # Numeral
        '௸': 'D',  # etc
        '௱': 'L',  # 
        '௳': 'Z',  # day
        '௴': 'X',  # month
        '௵': 'C',  # year
        '௶': 'V',  # debit
        '௷': 'B',  # credit
        'ௐ': 'N',  # Om
    }
    
    # Consonant base keys (for generating combinations)
    # Based on m17n file: h=க, b=ங, [=ச, ]=ஞ, o=ட, p=ண, l=த, ;=ந, j=ப, k=ம, '=ய, m=ர, n=ல, v=வ, /=ழ, y=ள, u=ற, i=ன
    CONSONANT_KEYS = {
        'க': 'h', 'ப': 'j', 'ம': 'k', 'த': 'l', 'ந': ';',
        'வ': 'v', 'ய': "'", 'ல': 'n', 'ர': 'm',
        'ங': 'b', 'ஞ': ']', 'ச': '[', 'ழ': '/',
        'ள': 'y', 'ற': 'u', 'ன': 'i', 'ட': 'o', 'ண': 'p',
        # Grantha consonants
        'ஸ': 'Q', 'ஷ': 'W', 'ஜ': 'E', 'ஹ': 'R', 'ஶ': 'U',
    }
    
    # Vowel sign keys (for generating combinations)
    # Based on m17n file: ^q=ா, ^s=ி, ^w=ீ, ^d=ு, ^e=ூ, ^g=ெ, ^t=ே, ^r=ை, ^C=ொ, ^x=ோ, ^z=ௌ
    VOWEL_SIGN_KEYS = {
        'ா': 'q',   # aa (^q)
        'ி': 's',   # i (^s)
        'ீ': 'w',   # ii (^w)
        'ு': 'd',   # u (^d)
        'ூ': 'e',   # uu (^e)
        'ெ': 'g',   # e (^g)
        'ே': 't',   # ee (^t)
        'ை': 'r',   # ai (^r)
        'ொ': 'C',   # o (^C)
        'ோ': 'x',   # oo (^x)
        'ௌ': 'z',   # au (^z)
    }
    
    @classmethod
    def _generate_consonant_vowel_combination(cls, consonant: str, vowel_sign: str) -> Optional[str]:
        """
        Generate keystroke sequence for consonant-vowel combination.
        Returns None if not a valid combination.
        
        Example: கா = hq, கி = hs, etc.
        """
        cons_key = cls.CONSONANT_KEYS.get(consonant)
        vowel_key = cls.VOWEL_SIGN_KEYS.get(vowel_sign)
        
        if cons_key and vowel_key:
            return cons_key + vowel_key
        return None
    
    
    @classmethod
    def get_keystroke_sequence(cls, tamil_text: str) -> List[tuple[str, bool]]:
        """
        Convert Tamil text to keystroke sequence.
        Returns list of (key, needs_shift) tuples.
        
        Handles:
        - Standalone characters (vowels, consonants)
        - Consonant-vowel combinations (e.g., கா = hq, டு = od)
        - Consonants with pulli (e.g., க் = hf)
        - Multi-character sequences
        - Tamil numerals and special characters
        """
        
        sequence = []
        i = 0
        while i < len(tamil_text):
            char = tamil_text[i]
            
            if char == ' ':
                sequence.append(('Space', False))
                i += 1
            # First, check for combined characters (consonant + vowel sign)
            # This handles cases like "டு" which should be "od", not "o" + "^d"
            elif i + 1 < len(tamil_text):
                combined = char + tamil_text[i + 1]
                if combined in cls.CHAR_TO_KEYSTROKES:
                    # Found a combined character (e.g., "டு" = "od")
                    key_seq = cls.CHAR_TO_KEYSTROKES[combined]
                    # Process the key sequence
                    for k in key_seq:
                        is_upper = k.isupper()
                        sequence.append((k.upper(), is_upper))
                    i += 2
                    continue
                # Combined not found, fall through to check single character
            # Check if current character is in mapping
            if char in cls.CHAR_TO_KEYSTROKES:
                key_seq = cls.CHAR_TO_KEYSTROKES[char]
                # Process each key in the sequence
                # Handle special prefixes like ^, ^#
                if key_seq.startswith('^#'):
                    # Tamil numeral: ^#1 -> press ^ then # then 1
                    sequence.append(('^', False))
                    sequence.append(('#', False))
                    if len(key_seq) > 2:
                        num_key = key_seq[2]
                        sequence.append((num_key.upper(), False))
                elif key_seq.startswith('^'):
                    # Vowel sign: ^q -> press ^ then q
                    # But note: standalone vowel signs are rare - usually they're combined with consonants
                    sequence.append(('^', False))
                    if len(key_seq) > 1:
                        vowel_key = key_seq[1]
                        is_upper = vowel_key.isupper()
                        sequence.append((vowel_key.upper(), is_upper))
                else:
                    # Regular sequence: process each key
                    for k in key_seq:
                        is_upper = k.isupper()
                        sequence.append((k.upper(), is_upper))
                i += 1
            else:
                # Fallback for unmapped characters
                if char.isalpha():
                    sequence.append((char.upper(), char.isupper()))
                else:
                    sequence.append((char, False))
                i += 1
        
        return sequence
    
    @classmethod
    def get_key_for_char(cls, char: str) -> Optional[str]:
        """Get the primary key for a Tamil character"""
        if char in cls.CHAR_TO_KEYSTROKES:
            key_seq = cls.CHAR_TO_KEYSTROKES[char]
            if key_seq.startswith('^#'):
                # Tamil numeral: return the number key
                return key_seq[2].upper() if len(key_seq) > 2 else None
            elif key_seq.startswith('^'):
                # Vowel sign: return the vowel key after ^
                return key_seq[1].upper() if len(key_seq) > 1 else None
            # Regular sequence: return first key
            return key_seq[0].upper() if key_seq else None
        return None


class KeystrokeTracker:
    """Main tracker class for Tamil99 keyboard learning"""
    
    def __init__(self):
        self.layout = Tamil99KeyboardLayout()
        self.session_start = datetime.now()
        self.strokes: List[StrokeData] = []
        self.last_stroke_time = self.session_start
        
        # Statistics tracking
        self.stats = {
            'total_strokes': 0,
            'correct_strokes': 0,
            'incorrect_strokes': 0,
            'accuracy': 0.0,
            'character_accuracy': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'key_accuracy': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'common_mistakes': Counter(),
            'response_times': [],
        }
        
        # Learning progress
        self.mastery_levels = defaultdict(int)  # Character -> mastery level (0-100)
    
    def record_stroke(self, pressed_key: str, expected_key: str, 
                     response_time: Optional[float] = None) -> Dict:
        """
        Record a single keystroke
        
        Args:
            pressed_key: The key the user actually pressed
            expected_key: The key they should have pressed
            response_time: Time taken to press the key (ms). If None, calculated from last stroke
            
        Returns:
            Dictionary with immediate feedback
        """
        if response_time is None:
            now = datetime.now()
            response_time = (now - self.last_stroke_time).total_seconds() * 1000
            self.last_stroke_time = now
        
        is_correct = (pressed_key.lower() == expected_key.lower())
        
        stroke = StrokeData(
            key=pressed_key,
            expected_key=expected_key,
            is_correct=is_correct,
            response_time=response_time,
            timestamp=datetime.now()
        )
        
        self.strokes.append(stroke)
        
        # Update statistics
        self.stats['total_strokes'] += 1
        if is_correct:
            self.stats['correct_strokes'] += 1
        else:
            self.stats['incorrect_strokes'] += 1
            mistake = f"{expected_key} → {pressed_key}"
            self.stats['common_mistakes'][mistake] += 1
        
        # Track key-specific accuracy
        self.stats['key_accuracy'][expected_key]['total'] += 1
        if is_correct:
            self.stats['key_accuracy'][expected_key]['correct'] += 1
        
        # Track response time
        self.stats['response_times'].append(response_time)
        
        # Calculate current accuracy
        self.stats['accuracy'] = (
            self.stats['correct_strokes'] / self.stats['total_strokes'] * 100
            if self.stats['total_strokes'] > 0 else 0
        )
        
        return {
            'is_correct': is_correct,
            'expected': expected_key,
            'pressed': pressed_key,
            'accuracy': round(self.stats['accuracy'], 2),
        }
    
    def get_session_summary(self) -> Dict:
        """Get comprehensive session summary"""
        duration = (datetime.now() - self.session_start).total_seconds()
        
        # Calculate average response time
        avg_response = (
            sum(self.stats['response_times']) / len(self.stats['response_times'])
            if self.stats['response_times'] else 0
        )
        
        # Calculate typing speed (strokes per minute)
        speed = (
            self.stats['total_strokes'] / (duration / 60)
            if duration > 0 else 0
        )
        
        return {
            'session_duration': round(duration / 60, 2),  # minutes
            'total_strokes': self.stats['total_strokes'],
            'correct_strokes': self.stats['correct_strokes'],
            'incorrect_strokes': self.stats['incorrect_strokes'],
            'overall_accuracy': round(self.stats['accuracy'], 2),
            'typing_speed': round(speed, 2),  # strokes per minute
            'average_response_time': round(avg_response, 2),  # ms
        }
    
    def reset_session(self):
        """Reset the current session"""
        self.session_start = datetime.now()
        self.last_stroke_time = self.session_start
        self.strokes = []
        self.stats = {
            'total_strokes': 0,
            'correct_strokes': 0,
            'incorrect_strokes': 0,
            'accuracy': 0.0,
            'character_accuracy': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'key_accuracy': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'common_mistakes': Counter(),
            'response_times': [],
        }
