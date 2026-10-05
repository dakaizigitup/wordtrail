import UIKit

enum WordtrailTheme: String, CaseIterable, Identifiable {
    case jade, lavender, night
    var id: String { rawValue }
    var title: String { switch self { case .jade: "青绿"; case .lavender: "粉紫"; case .night: "深色" } }
    static var current: WordtrailTheme { WordtrailTheme(rawValue: UserDefaults.standard.string(forKey: "theme") ?? "jade") ?? .jade }
}

struct WordtrailPalette {
    let theme: WordtrailTheme
    let background, surface, key, function, accent, ink, muted, line, soft, fresh, onAccent: UIColor
    init(theme: WordtrailTheme) {
        self.theme = theme
        let values: [UInt32]
        switch theme {
        case .jade: values = [0xEEF4EF,0xFBFEFB,0xFEFFFD,0xDDE9E0,0x2C684D,0x24392D,0x738577,0xD7E4DA,0xE0EFE3,0xB46528,0xFFFFFF]
        case .lavender: values = [0xF4EFF7,0xFFFCFF,0xFFFCFF,0xE7DEF0,0x78568F,0x382C43,0x80738C,0xE3D9EA,0xEDE2F4,0xAD652E,0xFFFFFF]
        case .night: values = [0x18231F,0x22312A,0x2C3B33,0x394A40,0xA9D4B5,0xECF3ED,0xAFBFB3,0x3C4C42,0x304A39,0xEDB883,0x193724]
        }
        let colors = values.map { UIColor(red: CGFloat(($0 >> 16) & 255)/255, green: CGFloat(($0 >> 8) & 255)/255, blue: CGFloat($0 & 255)/255, alpha: 1) }
        background=colors[0];surface=colors[1];key=colors[2];function=colors[3];accent=colors[4];ink=colors[5];muted=colors[6];line=colors[7];soft=colors[8];fresh=colors[9];onAccent=colors[10]
    }
}
