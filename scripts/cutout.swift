// Writes a grayscale person mask (white = subject) for a portrait photo using
// macOS's built-in Vision person segmentation, so no model download is needed.
//
//     swift scripts/cutout.swift source/avatar.jpg source/mask.png
import AppKit
import CoreImage
import Vision

let args = CommandLine.arguments
guard args.count == 3 else {
    FileHandle.standardError.write("usage: swift cutout.swift <photo> <mask.png>\n".data(using: .utf8)!)
    exit(2)
}

let input = URL(fileURLWithPath: args[1])
guard let image = CIImage(contentsOf: input) else { fatalError("cannot read \(input.path)") }

let request = VNGeneratePersonSegmentationRequest()
request.qualityLevel = .accurate
request.outputPixelFormat = kCVPixelFormatType_OneComponent8
try VNImageRequestHandler(ciImage: image).perform([request])
guard let buffer = request.results?.first?.pixelBuffer else { fatalError("no person found") }

// The mask comes back at a lower resolution; scale it to the photo's size.
var mask = CIImage(cvPixelBuffer: buffer)
mask = mask.transformed(by: CGAffineTransform(
    scaleX: image.extent.width / mask.extent.width,
    y: image.extent.height / mask.extent.height))

let context = CIContext()
guard let cg = context.createCGImage(mask, from: image.extent) else { fatalError("render failed") }
let png = NSBitmapImageRep(cgImage: cg).representation(using: .png, properties: [:])!
try png.write(to: URL(fileURLWithPath: args[2]))
print("wrote \(args[2])")
